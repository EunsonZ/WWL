---
课程: "TypeScript"
层级: "核心"
修订: "2026-09-06"
类型: "机制讲解与推演"
---

# JavaScript 运行语义与 TypeScript 类型边界

> **学习位置**：[[计算机知识/00-开始/课程地图/05-TypeScript-课程地图|TypeScript课程地图]] · **适用边界**：strict 模式；ES2022 运行语义；Node 与浏览器环境区分。

## 先分清程序运行在哪里

TypeScript 主要在编译检查阶段描述 JavaScript 程序；接口、类型别名和大多数类型标注在输出中被擦除。运行时仍受 JavaScript 的值、对象、原型、异常和事件循环规则支配。`as User` 不会从服务器响应中生成或验证用户对象。

Node、浏览器和其他宿主提供不同全局 API。`lib: ["DOM"]` 让类型检查器认识 `document`，不会让 Node 凭空出现 DOM；`target` 决定部分语法输出，不能自动补全缺失的内建 API。编译目标、类型库、模块解析方式和真实运行环境应作为一组配置审查。

## 值的分类与常见反例

JavaScript 的 `number` 通常使用二进制双精度浮点；精确整数的安全范围由 `Number.MAX_SAFE_INTEGER` 等边界给出。`bigint` 表达任意精度整数，但不能随意与 `number` 混合算术，也不直接按默认 JSON 规则序列化。金额要先决定单位和舍入策略，而不是期待类型标注修复浮点误差。

`typeof null === 'object'` 是历史行为；数组也是对象。`NaN === NaN` 为假，判断使用 `Number.isNaN`，并用 `Number.isFinite` 验证有限数值。`===` 避免许多强制转换，但它不是深结构比较：两个内容相同的对象仍可能不相等。`Object.is` 对 NaN 和带符号零有不同规则，集合键还有自己的相等协议。

```ts
const a = { nested: { n: 1 } };
const b = { ...a };
b.nested.n = 9;
console.assert(a.nested.n === 9);
```

对象展开复制第一层属性值，内部对象仍共享。`const` 固定绑定，不冻结对象；`readonly` 主要约束经过某个静态类型的写操作，也不提供运行时深冻结。API 需要隔离时，应明确所有权、复制深度和序列化边界。

## 作用域、函数和 this

`let`、`const` 具有块级作用域，并存在初始化前不可访问的时间区域。闭包捕获变量绑定；异步回调何时读取变量要按实际执行顺序推演。箭头函数使用词法 `this`，普通函数的 `this` 依调用方式而定；把实例方法直接作为回调传递可能丢失接收者。`bind` 或明确的箭头包装能解决某些情况，但长期保存回调也可能延长对象生命周期。

类的实例方法通常位于原型上。TypeScript 的 `private` 与 JavaScript 的 `#field` 不是同一机制：前者的普通 private 字段主要是静态检查约束，后者有运行时私有名称语义。继承可复用实现，但组合更容易让测试替换外部依赖。

## 模块边界要与宿主一致

ESM 和 CommonJS 的加载、导出互操作及解析规则不同。为 Node 项目选择与部署方式相符的 `module`、`moduleResolution` 和 `package.json`；为打包器环境使用相应解析策略，不能为了消除报错随意改成另一个模式。`import type` 表明仅类型依赖，避免不必要的运行时导入。循环依赖可能使模块在未初始化完成时被访问，类型正确不能消除初始化顺序问题。

## 练习与答案

解释为什么 `const p: Readonly<{items: number[]}>` 不能重新赋值 `items`，但通常仍能执行 `p.items.push(1)`：只读约束在外层属性上，内部数组没有变成只读数组。再把后端返回的字符串强制断言为 `{id:number}`，查看输出 JavaScript，会发现验证并没有出现。正确修复是把输入作为 `unknown` 并解析，而不是追加一次断言。

## 关联阅读

- [[计算机知识/10-编程语言/05-TypeScript/10-系统课程/02-联合收窄与运行时验证|联合、收窄与运行时验证：把未知数据变成可信值]]
- [[计算机知识/10-编程语言/01-Python/10-系统课程/01-对象图复制与数值语义|对象图、复制与数值语义：把名字和对象分开]]

## 依据与继续查证

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [TypeScript TSConfig](https://www.typescriptlang.org/tsconfig/)
- [ECMAScript 2024（固定语言参考）](https://tc39.es/ecma262/2024/)

本页的例子、推演与练习为教学构造；语言契约、系统接口和版本相关结论应结合以上原始文档核对。

<!-- COURSE SEQUENCE -->
## 顺序导航与验证

[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/00-TypeScript系统课程索引|本课程总索引]] · [[计算机知识/_labs/round3/TS/TypeScript-实验说明|本课程实验]]

下一讲：[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/02-联合收窄与运行时验证|联合、收窄与运行时验证：把未知数据变成可信值]]
<!-- END COURSE SEQUENCE -->

<!-- ORIGINAL DEEP LINKS -->
## 与原有长篇专题衔接

- [[计算机知识/10-编程语言/05-TypeScript/03-泛型类型运算结构化兼容|03-泛型类型运算结构化兼容]]
- [[计算机知识/10-编程语言/05-TypeScript/02-联合类型收窄与运行时验证|02-联合类型收窄与运行时验证]]

新旧讲解采用的版本与模型可能不同，比较时先核对各自前提，不把教学简化当成实现细节。
<!-- END ORIGINAL DEEP LINKS -->
