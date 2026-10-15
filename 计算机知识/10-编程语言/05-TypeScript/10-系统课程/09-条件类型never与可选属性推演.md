---
课程: "TypeScript"
层级: "专题深化"
修订: "2026-09-06"
类型: "难点推演、反例与证据"
课程编号: "TS-09"
---

# 把类型运算当程序推演：分布式条件、never 与可选属性

> **本页要解决**：为什么 never extends U 的泛型结果会消失？
>
> **先修**：[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/03-泛型方差与API设计|泛型、方差与 API 设计：保留输入和输出的关系]]；[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/04-条件映射类型与声明文件|条件类型、映射类型与声明文件：类型级计算也需要规格]]。
>
> **阅读入口**：[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/00-TypeScript系统课程索引|本学科主索引]] · [[计算机知识/00-开始/全局导航/11-难点导读与研究证据|全局难点导读]]。

**版本、模型与证据边界**：启用 strict、noUncheckedIndexedAccess、exactOptionalPropertyTypes；运行时以 ES2022 与实际 Node/tsc 版本记录为准。

## 类型表达式也有求值规则

理解复杂 TypeScript 类型时，先把泛型实参代入，再问条件是否按联合成员分别执行。不要把编辑器显示结果当无法解释的魔法。以下以开启 `strict` 的编译项目为起点，同时单独开启 `exactOptionalPropertyTypes` 与 `noUncheckedIndexedAccess`；后两项不是只写 strict 就自动获得的全部保证。[^optional][^index]

## 分布式条件类型：遍历的是联合成员

```typescript
type Wrap<T> = T extends string ? { text: T } : { value: T };
type A = Wrap<"a" | 7>;
// { text: "a" } | { value: 7 }

type Whole<T> = [T] extends [string] ? true : false;
type B = Whole<"a" | 7>; // false
```

第一种检查位置直接是裸类型参数 T，因此对联合分发。第二种把 T 放入元组，检查“整个联合是否能赋给 string”，不逐项分发。括号 `(T)` 并不能像元组那样改变分发条件。[^conditional]

`Wrap<never>` 是 never，不是 `{ text: never }`。可把 never 理解为空的联合：没有成员可映射，结果仍为空。反之 `[never] extends [string]` 为 true，因为 never 可赋给 string。它们回答的是两个不同问题。

```typescript
type IsNever<T> = [T] extends [never] ? true : false;
type N1 = IsNever<never>;  // true
type N2 = IsNever<string>; // false
```

`any` 会让条件类型的结果出现特殊传播，不能用它测试与 unknown 相同的逻辑。unknown 要求使用前证明性质；any 可以跳过大量检查。对类型工具做测试时，普通类型、联合、never、unknown、any 应被当作不同边界用例。

## infer 不是全局搜索，它在指定结构里提取

```typescript
type Item<T> = T extends readonly (infer E)[] ? E : never;
type Return<T> = T extends (...args: never[]) => infer R ? R : never;
type I = Item<readonly [1, "x"]>; // 1 | "x"
```

第一项识别可只读数组结构，再从元素位置推断 E。这不代表“任何可迭代对象”都匹配，也不自动复制运行时迭代规则。函数的返回类型提取还要注意重载：对重载调用签名做这种推断时，通常基于最后一个签名，而不是给所有可能调用做重载决议。[^conditional]

类型工具需要声明合同：接受哪类输入，分布是否需要保留，失败返回 never 还是带错误标记的类型。过度嵌套递归类型还可能受到编译器实例化深度与性能限制；类型层面能表达不等于值得在公共 API 中无限堆叠。

## 可选属性与显式 undefined 不是同一件事

```typescript
type Settings = { theme?: "light" | "dark" };
const a: Settings = {};
const b: Settings = { theme: "dark" };
// exactOptionalPropertyTypes 开启时，下面应被拒绝：
// const c: Settings = { theme: undefined };
```

运行时，`"theme" in {}` 为 false，`"theme" in {theme:undefined}` 为 true。配置合并、补丁更新和序列化可能区分“未提供”与“明确设置”。exactOptionalPropertyTypes 使写入合同更贴近这个差别。读取可选属性仍可能得到 undefined；这个选项没有让缺失属性凭空存在。[^optional]

需要允许显式 undefined 时，声明 `theme?: "light" | "dark" | undefined`。而 `theme: "light" | "dark" | undefined` 要求键存在，只允许值为空。三种形式不能混为一谈。

## 索引签名承诺值类型，不证明键存在

```typescript
const counts: Record<string, number> = {};
const x = counts["missing"];
// 开启 noUncheckedIndexedAccess 后，x 为 number | undefined。
```

数组随机下标同理。即使 `i` 是 number，也不能推出 `i` 为合法整数、非负且小于长度。静态检查有时可理解元组固定位置或 for-of，但不会替你证明每个运行时索引范围。加上 `!` 只删掉类型中的不确定性，不产生检查。[^index]

这与 [[计算机知识/10-编程语言/03-C语言/10-系统课程/09-指针步长二维数组与接口形状|C 的数组形状合同]] 有共同点：一个表达式能写出来，不等于调用方容量和索引已经得到证明。区别是 TypeScript 的目标主要是发现程序错误，而不是在运行时建立内存隔离边界。

## readonly、as const 与 satisfies 各管一件事

readonly 是经某个类型视角不允许写；别的可变别名仍可能修改同一对象。`as const` 收窄字面量并形成只读属性/元组视角，不执行 `Object.freeze`。`satisfies` 检查表达式是否符合目标类型，同时保留较具体的推断结果，但也不会在运行时校验网络数据。

对象的“多余属性检查”也不是精确对象类型的一般定理。直接对象字面量可能因为多余字段被拒绝，而经过变量的结构赋值仍可接受额外字段。安全边界要用 [[计算机知识/10-编程语言/05-TypeScript/10-系统课程/10-运行时边界状态机与取消安全|运行时解析与授权]]，不是寄希望于编译器恰好拒绝一个字面量。

## 如何验证一段类型工具

本轮 TypeScript 实验同时包含正例和用 `@ts-expect-error` 标注的负例。负例必须真的产生错误；若以后配置变松、代码变得可接受，编译器会报告未使用的 expect-error。运行时测试则检查缺失键和显式 undefined 的差别。两类测试分开，避免“tsc 通过”被误报为运行时数据已经安全。

**自测**：`type F<T> = T extends never ? 1 : 2` 中 `F<never>` 是什么？never。`type G<T> = [T] extends [never] ? 1 : 2` 中 `G<never>` 才是 1。解释必须涉及分发，而不是死记两个结果。

[^conditional]: TypeScript 官方 [Conditional Types](https://www.typescriptlang.org/docs/handbook/2/conditional-types.html)，分发、infer 及重载签名推断；文档为滚动版本，本轮记录本地编译器版本。
[^optional]: TypeScript 官方 [exactOptionalPropertyTypes](https://www.typescriptlang.org/tsconfig/exactOptionalPropertyTypes.html)。
[^index]: TypeScript 官方 [noUncheckedIndexedAccess](https://www.typescriptlang.org/tsconfig/noUncheckedIndexedAccess.html)。

## 知识连接：下一步应追问什么

类型运算的量词和分配规则能帮助理解其他类型系统，但不会替网络数据执行校验。

[[计算机知识/10-编程语言/04-Rust/10-系统课程/09-借用检查中的量词方差与重借用|把借用检查翻译成约束：重借用、方差与生命周期量词]]：为什么能缩短共享引用，却不能把长期引用槽位当短期槽位？

[[计算机知识/10-编程语言/02-C++/10-系统课程/09-推导引用折叠与完美转发|把模板推导逐行算清：auto、decltype 与完美转发]]：T&& 何时是右值引用，何时是转发引用？

[[计算机知识/70-编译原理/10-系统课程/11-类型统一泛化与值限制|类型推断不是猜类型：统一、泛化与可变引用的反例]]：为什么 let 绑定可以多态，可变引用却不能随便泛化？

[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/10-运行时边界状态机与取消安全|从 unknown 到可信状态：校验、状态机与异步取消]]：声明成某个类型，为什么不能让网络数据自动可信？

## 本地核验与阅读顺序

[[计算机知识/_labs/round4/README|本轮实验：命令、检查范围与未执行项目]] 提供对应文件和记录。[[计算机知识/90-资源/维护/导入-com/_meta/round4/01-研究证据与版本边界|研究证据索引]] 区分规范、推演和实验；[[计算机知识/90-资源/维护/导入-com/_meta/round4/02-缺口回查与后续验证|仍需进一步验证的边界]] 不把概览或模型标成完整实现。

先完成主干，再按问题选择专题；不要求跳过第 1–8 讲。 下一专题：[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/10-运行时边界状态机与取消安全|从 unknown 到可信状态：校验、状态机与异步取消]]。
