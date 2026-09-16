---
type: lesson
domain: computer-science
stage: 1
status: ready
difficulty: 进阶
estimated_minutes: 95
topics:
  - parsing
  - recursive-descent
  - pratt-parser
  - LL
  - LR
  - error-recovery
tags:
  - computer-science/compiler
  - computer-science/parsing
---

# 递归下降、Pratt、LL 与 LR 解析及错误恢复

## 本课目标

学完后，你应该能：

- 区分递归下降、Pratt、表驱动 LL 与 LR 的决策依据，而不是把它们当成四种互不相干的语法；
- 手算 `nullable`、FIRST、FOLLOW，并用它们解释一个 LL(1) 选择为什么确定或冲突；
- 读懂 LR item、closure、goto、shift、reduce 的含义，手工跟踪一段短输入；
- 设计 panic mode 与 error node 恢复，并明确证明解析循环不会卡在同一 token；
- 区分首要语法错误与恢复造成的次生错误，控制级联误报。

本课只写**伪代码**。解析器生成器、真实 AST 类型与测试输入进入 [[计算机知识/80-实践/08-编译原理/00-编译原理实践-MOC|编译原理实践]]，不要把这里的伪代码误当作某种语言可直接运行的实现。

## 先修

- [[计算机知识/70-编译原理/03-上下文无关文法AST-CST与歧义|上下文无关文法、AST、CST 与歧义]]：终结符、非终结符、产生式、派生与 AST；
- [[计算机知识/70-编译原理/02-词法分析正则自动机Unicode与源位置|词法分析、正则、自动机、Unicode 与源位置]]：token、词素、源位置与词法错误；
- [[计算机知识/50-数据结构与算法/03-栈队列双端队列与单调结构|栈、队列、双端队列与单调结构]]：显式栈和队列不变量。

## 直觉：解析器是在有限证据下决定“下一步归到哪里”

词法分析把字符流变成 token 流；解析器要根据文法，把 token 组织成 parse tree 或更紧凑的 AST。困难不在于“看见一个 `+` 就建加法节点”，而在于回答三个问题：

1. 当前 token 足以选择哪条产生式吗？
2. 运算符优先级、结合性或嵌套结构要求何时停止当前子表达式？
3. 输入已损坏时，丢弃哪些 token 才能继续，并且不会伪造几十条无意义错误？

递归下降和 LL 从“将要展开哪个非终结符”看输入；LR 从“已经识别的右部能否归约”看输入；Pratt 把表达式文法的优先级决策压缩为 binding power。它们的共同底线是：**每一次循环都必须消费输入、改变解析状态，或明确返回；恢复分支也不例外。**

## 1. 精确定义：从文法到选择证据

上下文无关文法写作 $G=(N,\Sigma,P,S)$：

- $N$：非终结符集合；
- $\Sigma$：终结符集合，也就是解析器看到的 token 类别；
- $P$：产生式集合；
- $S$：开始符号。

若 $A \Rightarrow^* \epsilon$，称 $A$ **nullable**。对符号串 $\alpha$：

- $FIRST(\alpha)$：从 $\alpha$ 派生出的串可能以哪些终结符开头；若可派生空串，也包含 $\epsilon$；
- $FOLLOW(A)$：某个从开始符号可达的句型中，可能紧跟在 $A$ 后的终结符；若 $A$ 可位于整句末尾，也包含输入结束符 `$`。

对产生式 `A → α`，LL(1) 的预测集合是：

```text
PREDICT(A → α) = FIRST(α) - {ε}
if α is nullable:
    PREDICT(A → α) also includes FOLLOW(A)
```

同一非终结符的不同产生式若预测集合相交，一个 token 就不能唯一决定选择，文法不是当前形式下的 LL(1)。这不等于该语言“无法解析”；可能需要左因子提取、消除左递归、更强的 LL(k)/LR 方法，或显式消歧规则。

## 2. FIRST/FOLLOW 手算：可空分支为什么要看后继

考虑语句列表：

```text
Program  → Stmts EOF
Stmts    → Stmt Stmts | ε
Stmt     → ID '=' NUM ';'
```

逐步计算：

1. `FIRST(Stmt) = {ID}`；
2. `Stmts → ε`，所以 `Stmts` nullable；
3. `FIRST(Stmts) = {ID, ε}`；
4. `Program → Stmts EOF`，因此 `FOLLOW(Stmts) = {EOF}`；
5. 第一条 `Stmts` 产生式的预测集合是 `{ID}`，空产生式的预测集合是 `{EOF}`，两者不相交。

于是表驱动选择可以写成：

| 栈顶非终结符 | lookahead=`ID` | lookahead=`EOF` |
| --- | --- | --- |
| `Stmts` | `Stmts → Stmt Stmts` | `Stmts → ε` |

**反例：**若再加入 `Stmts → ID ';'`，它与 `Stmts → Stmt Stmts` 的 FIRST 都含 `ID`，产生冲突。仅在实现里“把第一条放前面”没有解释语言语义，还可能让另一条永远不可达。

另一个常见冲突来自左递归：`Expr → Expr '+' Term | Term`。递归下降一进入 `Expr` 就再次调用 `Expr`，尚未消费 token，因而无限递归。可改写为：

```text
Expr     → Term ExprTail
ExprTail → '+' Term ExprTail | ε
```

这里改写保留了识别的串，但 AST 构造必须主动折叠成左结合，否则会意外得到右嵌套树。

## 3. 递归下降：控制流直接映射非终结符

递归下降通常让一个过程对应一个非终结符。对上面的 `Stmt`：

```text
parse_stmt():
    start = cursor
    name = expect(ID)
    expect('=')
    value = expect(NUM)
    semi = expect(';')
    return Assign(name, value, span(start, semi))
```

它的优势是控制流、AST 构造、上下文条件和诊断位置直观；代价是文法通常要适合自顶向下预测，公共前缀和左递归要处理。一个实用实现还要明确 `peek`、`consume`、`expect` 的契约：

- `peek` 不移动 cursor；
- 成功的 `consume/expect` 恰好消费一个 token；
- 失败的 `expect` 要么插入一个有位置的 missing token，要么消费/同步后返回 error node，不能静默留在原地；
- 每个过程都返回节点及覆盖的源区间，包括错误节点。

### 公共前缀与承诺点

例如：

```text
Decl → 'fn' ID '(' Params ')' Block
     | 'fn' ID '(' Params ')' ';'
```

在 `fn ID (` 后尚不能选择，两个分支共享长前缀。可以提取为：

```text
Decl     → 'fn' ID '(' Params ')' DeclEnd
DeclEnd  → Block | ';'
```

也可以先解析共同部分，到 `DeclEnd` 再根据 lookahead 决定。不要反复回溯整个文件；无界回溯会让时间和诊断位置难以预测。

## 4. Pratt 解析：用 binding power 收束表达式

表达式文法经常有很多优先级层。Pratt 解析器让 token 提供两类行为：

- **prefix/null denotation**：token 位于表达式开头时如何构造节点，例如字面量、名字、前缀负号、左括号；
- **infix/postfix/left denotation**：左侧已有表达式时，当前 token 如何把它扩展，例如二元运算、调用、下标。

核心循环是：只要下一个运算符的左 binding power 足够强，就把它接到当前左表达式上。

```text
parse_expr(min_bp):
    token = consume_one_or_report_missing_expression()
    left = parse_prefix(token)

    while next_token_can_continue_expression():
        (left_bp, right_bp) = binding_power(peek())
        if left_bp < min_bp:
            break
        operator = consume()
        right = parse_expr(right_bp)
        left = Binary(operator, left, right)
    return left
```

一种约定下，左结合 `+` 可取 `(10, 11)`，左结合 `*` 取 `(20, 21)`，右结合 `^` 取 `(30, 30)`。数值本身没有跨实现意义，只有相对大小和左右关系有意义。

### 手算 `a + b * c`

1. 以 `min_bp=0` 读取 `a`；看见 `+` 的左 binding power 10，继续；
2. 解析 `+` 的右侧时使用 `min_bp=11`，读取 `b`；
3. `*` 的左 binding power 20 ≥ 11，于是右侧扩成 `b * c`；
4. 返回外层，得到 `a + (b * c)`。

若把 `+` 与 `*` 的 binding power 设成同一级，就会丢失预期优先级。若右结合 `^` 错设为左结合，则 `a ^ b ^ c` 会被误建为 `(a ^ b) ^ c`。Pratt 不是“无需文法”，而是把一类表达式文法编码到 prefix/infix 规则与 binding power 中。

## 5. LL：从调用栈抽象为预测表

LL 表示从左到右读输入（第一个 L），构造最左派生（第二个 L）。LL(1) 用一个 lookahead 决定产生式。表驱动版本维护符号栈：

```text
stack = [EOF, Start]
while stack is not empty:
    top = pop(stack)
    if top is a terminal:
        match_or_recover(top, lookahead)
    else:
        production = table[top, lookahead]
        if production exists:
            push production.right_hand_side in reverse order
        else:
            recover_nonterminal(top, lookahead)
```

递归下降和 LL(1) 表驱动解析在能力上可非常接近：前者把表的选择写进控制流，后者把决策显式数据化。生成器更便于系统检查冲突；手写递归下降更便于语言特有诊断和 AST 构造。选择应由语法、团队可维护性与诊断目标决定。

## 6. LR item、closure、goto 与 shift/reduce

LR 从左到右读取输入，反向构造最右派生。它维护状态栈；状态代表“已经看到了哪些产生式前缀”。LR(0) item 是带点产生式：

```text
E → E '+' • T
```

含义是：`E '+'` 已识别，接下来期待一个 `T`。若点在非终结符前，`closure` 加入该非终结符所有“尚未读任何右部”的 item；`goto(I, X)` 把状态集 `I` 中点前是 `X` 的 item 越过 `X`，再取 closure。

对增广文法：

```text
S' → E
E  → E '+' T | T
T  → ID
```

初始 closure 至少包含：

```text
S' → • E
E  → • E '+' T
E  → • T
T  → • ID
```

读取 `ID` 是 **shift**：token 入栈并进入含 `T → ID •` 的状态。点到末尾表示右部完整，可以 **reduce**：弹出右部对应的栈项，把 `ID` 归约成 `T`，再根据新栈顶状态对 `T` 做 goto。随后还能把 `T` 归约成 `E`。

### 手工跟踪 `ID + ID`

忽略具体状态编号，只保留动作证据：

| 剩余输入 | 已识别概况 | 动作 |
| --- | --- | --- |
| `ID + ID $` | 空 | shift `ID` |
| `+ ID $` | `ID` | reduce `T → ID` |
| `+ ID $` | `T` | reduce `E → T` |
| `+ ID $` | `E` | shift `+` |
| `ID $` | `E +` | shift `ID` |
| `$` | `E + ID` | reduce `T → ID` |
| `$` | `E + T` | reduce `E → E + T` |
| `$` | `E` | accept |

当表项同时允许 shift 和 reduce，称 **shift/reduce conflict**；同时允许两个 reduce，称 **reduce/reduce conflict**。优先级声明可以解决某些表达式冲突，但它是额外语义规则，不应把意外歧义一律“默认 shift”后隐藏。

## 7. 一页比较：选择什么，凭什么选择

| 方法 | 主要视角 | 决策证据 | 擅长 | 典型风险 |
| --- | --- | --- | --- | --- |
| 手写递归下降 | 自顶向下 | lookahead 与显式控制流 | 可读 AST 构造、定制诊断 | 左递归、公共前缀、无界回溯 |
| Pratt | 表达式局部自顶向下 | prefix/infix 规则与 binding power | 多优先级、调用/下标/后缀 | 结合性数值写错、错误边界模糊 |
| 表驱动 LL(1) | 最左派生 | FIRST/FOLLOW 预测表 | 文法可检查、实现规则整齐 | 表冲突、文法改写影响树形 |
| LR 系列 | 自底向上 | item 集、状态栈、ACTION/GOTO | 更广文法、自然处理左递归 | 状态/冲突难手查、诊断需设计 |

一个编译器完全可以组合它们，例如外层声明使用递归下降，表达式使用 Pratt；或使用 LR 生成器解析全部语法，再由语义动作建 AST。组合时必须只有一个组件拥有当前 token cursor，边界契约要说明谁消费分隔符和 EOF。

## 8. 错误恢复：先保证进展，再追求“猜对用户意图”

只在第一个错误处终止实现简单，但编辑器中每次少打一个 `)` 都会失去整文件反馈。恢复的目标不是证明坏输入属于语言，而是：

1. 报告位置准确的首要错误；
2. 构造显式 error/missing node，保持 AST 基本形状；
3. 到达可信同步点继续；
4. 保证有限步内前进，不在同一 token 重复报错。

### panic mode

panic mode 丢弃 token，直到遇到同步集合中的 token。语句级同步集合常包含 `;`、`}`、`EOF` 或当前非终结符的 FOLLOW，但必须按上下文选择：表达式中的 `,`、`)` 可能是安全边界，在外层则不是。

```text
recover(expected, sync_set):
    report_once(current_span, expected)
    skipped = []

    if peek() is in sync_set:
        return Missing(expected, zero_width_span_here)

    while peek() not in sync_set and peek() != EOF:
        append(skipped, consume())

    if skipped is empty and peek() != EOF:
        append(skipped, consume())
    return ErrorNode(expected, skipped)
```

其中最后的防线表达**进展不变量**：一次失败恢复后，必须满足以下至少一项：

- cursor 增大；
- 栈高度或解析状态发生使相同分支不可再次进入的变化；
- 当前过程返回给调用者；
- 到达 EOF 并终止。

“报告错误然后 `continue`”若既不消费 token 也不改变状态，就是死循环。向调用者返回 missing node 时也要由调用点保证不会以完全相同状态再次请求同一节点。

### error node 与源区间

error node 不应假装是合法节点。它至少保留：期望类别、实际 token 或跳过区间、诊断 ID、源区间。后续名称和类型阶段遇到 error node 时可以返回“未知/错误”结果，避免把一个漏掉的 `)` 扩散成十个“未定义名称”或“类型不匹配”。

### 例子：`call(1, +, 3`

合理诊断顺序可能是：

1. 在 `+` 处报告“逗号后需要表达式”；把 `+` 收进一个 `ErrorExpr`，以 `,` 为同步点；
2. 继续解析 `3`；
3. 在表达式结束处报告“缺少 `)`”，插入零宽 `MissingToken`；
4. 返回一个含三个参数槽位的调用节点，其中第二个是 error node。

不合理做法是从 `+` 开始逐 token 报“不是表达式”，随后把 `3`、下一条语句和文件尾都当作同一个参数，产生级联误报。

## 9. 控制级联误报：诊断也是有依赖关系的输出

- **首要错误**：直接由输入与当前语法期望矛盾，例如缺少 `)`；
- **次生错误**：恢复选择或缺失节点导致的后续不一致，例如错误参数节点没有类型；
- **独立错误**：在可信同步点之后、与前一个错误无依赖的新错误。

实践中可采用：

- 同一源区间只发一个主诊断，其他信息作为 note；
- error node 在后续阶段传播 error type，不重复诊断；
- 只有在 `;`、`}`、声明起始 token 等强同步点后才重置信任；
- 设置全文件错误预算，超过预算后停止详细恢复；
- 测试诊断的数量、位置和恢复后的 AST，而不只测试“程序拒绝了坏输入”。

## 常见反例

1. **FIRST 只看产生式第一个符号。** 若第一个非终结符 nullable，还要继续看后续符号；否则预测集合缺项。
2. **FOLLOW 包含“文法文本中写在右边的字符”。** FOLLOW 来自可达句型与可空传播，不是简单字符串搜索。
3. **Pratt 数字越大就天然越正确。** 数字只表达相对约束；结合性要由左右 binding power 的关系确定。
4. **LR reduce 就是看到右部立即替换。** 是否 reduce 由状态与 lookahead 的 ACTION 决定；盲目局部匹配会选错 handle。
5. **恢复时一直插入缺失 token。** 若调用者状态不变，零消费插入会无限循环或生成无限节点。
6. **报错越多越友好。** 同一缺失分隔符引发的几十条次生错误会淹没根因。

## 练习

1. 对 `List → Item Rest`、`Rest → ',' Item Rest | ε`、`Item → ID`，手算每个非终结符的 nullable、FIRST、FOLLOW，并写出 `Rest` 的两个预测集合。
2. 说明 `Expr → Expr '*' Atom | Atom` 为什么让朴素递归下降不前进；改写文法，并说明如何保持左结合 AST。
3. 设 Pratt 中 `+` 为 `(10,11)`、`*` 为 `(20,21)`、`^` 为 `(30,30)`，手工画出 `a + b * c ^ d ^ e` 的树，并圈出右结合发生的位置。
4. 为文法 `S'→E`、`E→E+T|T`、`T→ID` 写出初始 LR item closure，并逐步解释 `ID+ID` 的每次 shift/reduce。
5. 为输入 `let x = f(1, , 3; let y = 4;` 设计同步集合与 error node。逐步记录 cursor，证明每次恢复都消费、改变状态或返回。
6. 写出一个会产生级联误报的恢复策略，再用“主诊断 + error node + 强同步点”改写它。

## 成功标准

- 我能用 nullable、FIRST、FOLLOW 而非直觉解释 LL(1) 表项和冲突；
- 我能说明递归下降、Pratt、LL、LR 的视角、状态与适用边界；
- 我能读懂带点产生式，并在短输入上正确区分 shift、reduce 与 accept；
- 我的恢复循环有可陈述、可检查的进展不变量，不会停在同一 token；
- 我能用 error node 和同步点保留后续结构，并抑制依赖于同一根因的级联误报。

---

**上一站**：[[计算机知识/70-编译原理/03-上下文无关文法AST-CST与歧义|上下文无关文法、AST、CST 与歧义]] · **下一站**：[[计算机知识/70-编译原理/05-作用域名称解析与符号表|作用域、名称解析与符号表]] · **返回**：[[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/19-从表达式到机器码的贯通推演|编译原理深化：从一条表达式贯通全部阶段]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/70-编译原理/10-系统课程/02-词法分析Token与错误定位|词法分析：最长匹配、位置追踪与可靠错误报告]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->

<!-- ROUND4 DEPTH LINKS -->
## 继续推演本页难点

[[计算机知识/70-编译原理/10-系统课程/09-从项目集到SLR分析表完整推演|归约之后为什么还要查 GOTO，不能只弹栈？]] 本专题补上完整状态构造、迭代过程或约束求解。

这不是替换本页：先掌握原理，再用补充页核对容易被一句话略过的条件。
<!-- END ROUND4 DEPTH LINKS -->

