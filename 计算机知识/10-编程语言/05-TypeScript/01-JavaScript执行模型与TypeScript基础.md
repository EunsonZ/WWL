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
```

空输入通过联合类型表达缺少平均值。`readonly` 阻止经该类型视图修改数组，不是运行时冻结，也不证明其他别名不会修改它。即使每项有限，极端累加仍可能溢出或产生精度问题，本函数适合有界教学输入，生产应明确数值域和算法。

## 控制流与对象模型

严格相等通常避免宽松相等的隐式转换，但 NaN、自定义对象身份和浮点误差仍需明确。`??` 只处理 null/undefined，`||` 还把 0、空串等假值当成缺省。原型链决定属性查找，class 是构造对象与组织方法的语法，并不是 C++ 的对象布局模型。

异常会沿调用栈传播；Promise 中的失败进入拒绝状态，不能只在创建 Promise 的同步位置套 try/catch。模块的导入导出与脚本全局变量不同，ESM 和 CommonJS 还受宿主与配置影响。

## 练习

给 mean 测试空数组、零、负值、NaN、Infinity。解释 `number[]`、`readonly number[]` 与 `Object.freeze` 分别保证什么；将来自外部的值先当 unknown 校验，而不是直接写 `as number[]`。

## 把知识接起来

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
