---
type: lab
domain: computer-science
stage: 9
status: ready
difficulty: 进阶
estimated_minutes: 90
topics: [MiniLang, lexer, parser, type-checking, TAC, optimization, bytecode, VM]
tags: [computer-science/compiler, computer-science/minilang, computer-science/practice]
---

# MiniLang 端到端编译器

## 目标

这是一条小而真实的编译器纵切片：同一段源码依次经过 lexer、递归下降 parser、名称解析、类型检查、简化三地址 IR、常量折叠、基于 CFG 活跃性的死代码删除、栈式字节码，最后由 VM 执行。每层都是可导入、可打印、可断言的数据结构，不把中间阶段藏在一个只返回结果的黑箱里。

全课程地图在 [[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]。对照阅读的稳定课包括 [[计算机知识/70-编译原理/02-词法分析正则自动机Unicode与源位置|词法分析与源位置]]、[[计算机知识/70-编译原理/04-递归下降Pratt-LL与LR解析及错误恢复|递归下降与错误恢复]]、[[计算机知识/70-编译原理/05-作用域名称解析与符号表|作用域与名称解析]]、[[计算机知识/70-编译原理/06-类型系统约束求解泛型与语义检查|类型系统与语义检查]]、[[计算机知识/70-编译原理/07-中间表示Lowering与三地址码|中间表示与三地址码]]、[[计算机知识/70-编译原理/11-优化正确性语义保持与验证测试|优化正确性与验证测试]] 和 [[计算机知识/70-编译原理/16-解释器字节码VM-JIT与去优化|解释器、字节码 VM、JIT 与去优化]]。

## 语言与证据边界

MiniLang 故意只保留这些特性：

```text
program   := statement* EOF
statement := "let" IDENT ":" ("int" | "bool") "=" expression ";"
           | "if" "(" expression ")" "{" statement* "}"
             "else" "{" statement* "}"
           | "return" expression ";"
expression 支持整数、布尔、名字、括号、+ - * > ==
```

- `int` 采用有符号 i32 视图，加减乘在折叠和 VM 中都做 32-bit 模回绕。
- 声明是不可变的；为了让教学 IR 名字保持唯一，本切片拒绝嵌套重名声明。没有循环、函数、I/O、浮点、指针、并发、GC、原生码或生产 JIT。
- parser 拒绝首个不满足文法的 token，但没有实现 IDE 级多错误恢复；这是可见的功能边界，不是“语法分析已完整”。
- 常量折叠后先按控制流去掉不可达代码，再迭代活跃性 DCE；测试仅证明此语言子集的固定案例，不是形式等价证明。
- 所有实现只使用 Python 标准库，不读写文件、网络或系统配置。

## 流水线与可检查产物

| 阶段 | 入口 | 产物/失败 |
| --- | --- | --- |
| source → token | `lex` | 含 offset/line/column 的 `Token`；非法字符是 `lex` 诊断 |
| token → AST | `parse` | `Program/Let/If/Return/Binary`；期望 token 确定 |
| 名称解析 | `resolve_names` | 每个 use 指向声明 span；未定义/重复声明是 `name` 诊断 |
| 类型检查 | `type_check` | 符号类型表；初始器、运算符、分支条件是 `type` 诊断 |
| AST → TAC | `lower_to_ir` | 显式 temp、label、branch/jump/return |
| 优化 | `constant_fold` + `dead_code_eliminate` | 常量替换、常量分支、不可达删除、无用纯定义删除 |
| TAC → bytecode | `emit_bytecode` | 常量池、稳定 slot 序号、回填后 jump target |
| bytecode → result | `run_vm` | 栈式 VM 返回 `int/bool`；有 10,000 步预算保护 |

`compile_source` 保留 tokens、AST、绑定、原 IR、选中 IR、bytecode 和 result，测试因而能对阶段契约直接断言。可运行文件的逐字 code-sync 镜像在 [[计算机知识/80-实践/08-编译原理/09-MiniLang端到端编译器/源码与测试镜像|MiniLang 源码与测试镜像]]；规范执行源仍是同目录 `.py` 文件。

## 运行

```bash
python3 -m unittest -v test_minilang.py
python3 minilang.py
```

演示程序先计算 `2 + 3 * 4`，再根据 `x > 10` 选择分支。未优化 IR 同时含乘法、加法、比较和两条分支；优化后只保留跳到 `then0` 和 `return 15`。测试分别编译原 IR 与优化 IR 到字节码，并要求两个 VM 结果都是 15；这比只断言“优化后更短”更强。

总览使用同一个 `DEMO_SOURCE`，见 [[计算机知识/70-编译原理/19-从表达式到机器码的贯通推演|源码到VM的连续追踪]]。字面量先移除前导零，再以有效十进制位数和字典序比较2147483647，只有有界文本进入 `int`；不修改宿主全局转换上限。2147483648与4301个9应给lex:1:8位置化诊断，4301个0后跟1应得到1。新增回归与原功能测试入口保持可执行；本次接续只静态核对，当前候选测试为notrun，前作者的7项运行仅属于当时版本记录。

## 练习

1. 追踪 `DEMO_SOURCE` 中第三个 `x` 的 token span、AST `Name`、`Binding.declaration`、TAC operand 和 bytecode slot，把每步写成一行映射。
2. 把条件改成不能编译期求值的形式前，先设计“外部参数”的类型、IR 和 VM 契约；不要只在某一层硬编码。
3. 故意把 `constant_fold` 中 `mul` 改错，确认“优化前/后都返回 15”的等价测试失败；修复后再还原实验文件。
4. 为字节码增加独立 verifier：检查 opcode operand、jump target、stack depth 汇合和所有可达路径有返回，然后为每类错误写反例。
5. 新增运算符时，列出 lexer、parser 优先级、类型规则、TAC、折叠、bytecode、VM 和测试八个必改点，避免得到“能 parse 但不能执行”的半条流水线。

## 成功标准

- 当前有7项 unittest 测试定义，本候选运行状态为 `not_run`；未来完成运行后应全部通过，覆盖 token/AST/binding/type 中间结构、名称与类型诊断确定性、算术与 true/false 分支、优化前后等价、超长字面量边界及整个编译产物可重现。此前运行结果仅属于各自旧版本字节，不能作为本候选通过记录。
- `DEMO_SOURCE` 未优化与优化 VM 均返回 15，优化 IR 稳定为 `jump then0 / label then0 / return 15`。
- `return missing;` 稳定报 `name:1:8`，`let x: int = true;` 稳定报 `type:1:1`，诊断不依赖集合遍历顺序。
- 能分别指出每层产物和可能失败的阶段，不用“编译成功”代替 VM 执行、优化等价或生产编译器正确性的证据。

## 恢复

程序不会写入运行产物，所以普通运行无需清理。如果练习时修改了文件，只恢复本目录中你自己的实验 diff；不要使用会清理整个 Vault 或覆盖协作者修改的 Git 命令。

---

**上一站**：[[计算机知识/80-实践/08-编译原理/08-AI计算图Lowering融合与Shape特化/README|AI 计算图 Lowering、融合与 Shape 特化]] · **返回**：[[计算机知识/80-实践/08-编译原理/00-编译原理实践-MOC|编译原理实践 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/19-从表达式到机器码的贯通推演|编译原理深化：从一条表达式贯通全部阶段]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
