---
type: lesson
domain: computer-science
status: expanded
revision_date: 2026-09-06
tags: [computer-science, revision-2]
---

# TypeScript：先理解 JavaScript，再理解类型检查

> 阅读定位：严格类型检查；运行时语义属于 JavaScript，宿主 API 另行区分。返回 [[计算机知识/00-开始/课程地图/05-TypeScript-课程地图|TypeScript · 课程地图]]；全域入口 [[计算机知识/00-开始/全局导航/00-总学习地图|计算机知识库 · 总学习地图]]。

## 编译时类型与运行时值分两层

TypeScript 检查源代码中的类型关系，再生成 JavaScript；多数类型标注在输出中被擦除。JavaScript 引擎不会因为接口写了 `age:number` 就拒绝网络中的字符串。类型检查错误、JavaScript 异常、宿主 API 不存在是三个不同问题。

`number` 通常表示 IEEE 754 双精度浮点，安全整数范围有限；需要大整数时使用 bigint，但它不能随意与 number 混算，也不直接被普通 JSON 序列化。string、boolean、null、undefined、symbol、object 各有不同作用。`typeof null` 的结果是 `"object"`，验证对象时必须单独排除 null。

## 变量、对象与函数

`let` 允许重新绑定，`const` 禁止重新绑定，但不深度冻结对象。数组和对象赋值共享引用；展开语法通常浅拷贝。闭包捕获外层词法环境，箭头函数的 this 来自词法上下文，普通函数的 this 取决于调用方式等规则。把一个对象方法当独立回调传递，可能丢失调用者期待的 this。

这里计算一组同单位数值的算术平均值：`[2, 4, 6, 8]` 的总和是 20，除以 4 项得到 5；若输入用秒，结果也用秒，程序本身不能检查单位。先让这条输入经过校验再调用函数，不需要先学异步或其他语言。

### 保存并运行第一次完整调用

真源是 [[计算机知识/_labs/round3/TS/mean_entry.ts|mean_entry.ts]]。已有库文件时直接打开；自己键入时，把下面完整代码保存到该路径。`function` 定义可重复调用的操作，`return` 把结果交给调用者，`for...of` 逐项取值；`throw` 中止当前调用并跳到 `catch`，末尾的 `console.log` 显示结果。

<!-- code-sync: 计算机知识/_labs/round3/TS/mean_entry.ts -->
```typescript
function mean(values: readonly number[]): number | undefined {
  if (values.length === 0) return undefined;
  let total = 0;
  for (const value of values) {
    if (!Number.isFinite(value)) throw new Error("需要有限数字");
    total += value;
  }
  return total / values.length;
}

function parseFiniteNumbers(value: unknown): readonly number[] {
  if (!Array.isArray(value)) throw new Error("需要数组");
  const items: readonly unknown[] = value;
  const numbers: number[] = [];
  for (const item of items) {
    if (typeof item !== "number" || !Number.isFinite(item)) {
      throw new Error("每项都需要有限数字");
    }
    numbers.push(item);
  }
  return numbers;
}

const jsonText = '[2, 4, 6, 8]';
try {
  const externalValue: unknown = JSON.parse(jsonText);
  const values = parseFiniteNumbers(externalValue);
  const result = mean(values);
  console.log(result === undefined ? "没有平均值" : `平均值 = ${result}`);
} catch (error: unknown) {
  console.log(error instanceof Error ? `输入被拒绝：${error.message}` : "输入被拒绝");
}
```

先打开终端并进入你自己的 Vault 根目录（其下能看到 `计算机知识/`），检查已有工具：

```bash
node --version
tsc --version
```

本例用 Node 运行 JavaScript、用 TypeScript 的 `tsc` 先检查并生成它；需要 Node 与支持 ES2022 的 TypeScript。缺少 Node 时从 [Node 官方下载入口](https://nodejs.org/en/download) 选择当前平台，安装后重新打开终端检查 `node --version` 和 `npm --version`。已有 Node/npm、缺少 `tsc` 时，可在当前终端执行下面命令，将编译器与下载缓存放在库外临时目录；本次只把该目录加入当前终端的查找路径：

```bash
tool_dir="$(mktemp -d)"
npm install --prefix "$tool_dir" --cache "$tool_dir/npm-cache" --no-audit --no-fund typescript@7.0.2
export PATH="$tool_dir/node_modules/.bin:$PATH"
tsc --version
```

这里固定的是本次实际核对的编译器版本，下载需要网络。已有可用 `tsc` 可以直接使用。工具准备好后，在 Vault 根目录运行以下 macOS/Linux 命令：

```bash
build_dir="$(mktemp -d)"
tsc --strict --noUncheckedIndexedAccess --exactOptionalPropertyTypes --noEmitOnError --target ES2022 --module commonjs --lib ES2022,DOM --outDir "$build_dir" 计算机知识/_labs/round3/TS/mean_entry.ts
node "$build_dir/mean_entry.js"
```

第一条命令创建临时产物目录；`tsc` 成功后生成 `mean_entry.js`，`node` 执行它，输出 `平均值 = 5`。`--noEmitOnError` 在类型错误时不生成本次 JavaScript；编译报错时先修源码再运行，不能把旧产物当新结果。`DOM` 库在这里提供 `console` 的类型声明，不表示这个程序启动了浏览器。本页的这组命令只编译、运行这个首读文件；现有统一实验另见 [[计算机知识/_labs/round3/TS/TypeScript-实验说明|TypeScript 实验说明]]。

### 改一次输入，分清哪一层拒绝

`JSON.parse` 只检查 JSON 语法，它的返回值立即赋给 `unknown`，表示还不知道数据是什么。`Array.isArray` 检查外层形状，随后把数组元素视为 `unknown`；`typeof` 与 `Number.isFinite` 真正在运行时逐项检查。通过后才把数字放进新数组并交给 `mean`，没有用 `as number[]` 承诺未经验证的数据。返回新数组也避免继续依赖外部数组的可变别名；这里针对已解析 JSON，不是任意 getter/proxy 对象的隔离器。

只改 `jsonText` 那一行，保存、重新编译，再运行：

| 输入文本 | 预期输出 | 解释 |
| --- | --- | --- |
| `'[1, 2]'` | `平均值 = 1.5` | 除法保留小数，不是整数商。 |
| `'[]'` | `没有平均值` | 数组合法，但没有样本；`mean` 返回 `undefined`，不是 0。 |
| `'[2, "4", 6, 8]'` | `输入被拒绝：每项都需要有限数字` | JSON 合法，字符串不是数字；不自动转换。 |
| `'null'` | `输入被拒绝：需要数组` | JSON 合法，外层形状不符合本函数的输入。 |
| `'[1e400]'` | `输入被拒绝：每项都需要有限数字` | JSON 数字解析为非有限的 `Infinity`，仍要检查数值范围。 |

这几种文本都能通过 TypeScript 编译，运行结果却不同；静态类型检查不证明外部数据合法。`NaN` 与字面量 `Infinity` 本身不是合法 JSON，可在函数练习中直接构造并验证拒绝；JSON 语法错误会先由 `JSON.parse` 抛异常并进入同一 `catch`。

空输入通过联合类型表达缺少平均值。`readonly` 阻止经该类型视图修改数组，不是运行时冻结，也不证明其他别名不会修改它。即使每项有限，极端累加仍可能溢出或产生精度问题，本函数适合有界教学输入，生产应明确数值域和算法。

## 控制流与对象模型

严格相等通常避免宽松相等的隐式转换，但 NaN、自定义对象身份和浮点误差仍需明确。`??` 只处理 null/undefined，`||` 还把 0、空串等假值当成缺省。原型链决定属性查找，class 是构造对象与组织方法的语法，并不是 C++ 的对象布局模型。

异常会沿调用栈传播；Promise 中的失败进入拒绝状态，不能只在创建 Promise 的同步位置套 try/catch。模块的导入导出与脚本全局变量不同，ESM 和 CommonJS 还受宿主与配置影响。

## 练习

给 mean 测试空数组、零、负值、NaN、Infinity。解释 `number[]`、`readonly number[]` 与 `Object.freeze` 分别保证什么；将来自外部的值先当 unknown 校验，而不是直接写 `as number[]`。

## 把知识接起来

你现在能运行“文本解析 → 输入校验 → 均值 → 显示结果”。当数据从数字数组变成带字段的对象，或需要表达加载/成功/失败的不同状态时，接着读 [[计算机知识/10-编程语言/05-TypeScript/02-联合类型收窄与运行时验证|联合类型、收窄与输入边界]]；当输入来自网络、多个请求的返回次序可能不同，先读 [[计算机知识/10-编程语言/05-TypeScript/04-Promise事件循环并发与取消|事件循环、Promise、并发与取消]]；需要继续处理过期响应和可信状态时，按现有 [[计算机知识/10-编程语言/05-TypeScript/10-系统课程/10-运行时边界状态机与取消安全|运行时边界、状态机与取消安全]] 的先修入口深入。先完成当前调用与输入变式，再按问题选择后续语言机制。

[[计算机知识/10-编程语言/05-TypeScript/02-联合类型收窄与运行时验证|TypeScript：联合类型、收窄与输入边界]]；[[计算机知识/10-编程语言/05-TypeScript/04-Promise事件循环并发与取消|TypeScript：事件循环、Promise、并发与取消]]；[[计算机知识/10-编程语言/01-Python/15-对象协议描述符闭包与类型边界|Python 深化：名字、对象、协议与类型边界]]；[[计算机知识/30-计算机系统/21-逻辑电路整数运算与CPU性能推演|组成原理深化：从逻辑电路到 CPU 性能]]。

## 规范与进一步核对

参见 [[计算机知识/90-资源/10-本轮权威资料与版本边界#TypeScript|TypeScript原始资料]]。正文中的例题是本库的教学构造；一般模型不自动等于某一实现。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/10-编程语言/05-TypeScript/10-系统课程/01-JavaScript语义与类型边界|JavaScript 运行语义与 TypeScript 类型边界]]
- [[计算机知识/10-编程语言/05-TypeScript/10-系统课程/04-条件映射类型与声明文件|条件类型、映射类型与声明文件：类型级计算也需要规格]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
