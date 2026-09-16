---
课程: "TypeScript"
层级: "核心"
修订: "2026-09-06"
类型: "机制讲解与推演"
---

# 事件循环、Promise 与取消：顺序必须按任务推演

> **学习位置**：[[计算机知识/00-开始/课程地图/05-TypeScript-课程地图|TypeScript课程地图]] · **适用边界**：strict 模式；ES2022 运行语义；Node 与浏览器环境区分。

![事件循环、Promise 与取消：顺序必须按任务推演：结构示意](../../../_assets/diagrams/round3/event-loop.svg)

[PNG 备用图](../../../_assets/diagrams/round3/event-loop.png) · [可编辑图源](../../../_assets/diagrams/round3/event-loop.dot)

## 一段程序有两种顺序

```ts
const seen: string[] = [];
seen.push('A');
Promise.resolve().then(() => seen.push('B'));
seen.push('C');
// 当前同步栈完成时为 A,C；随后 Promise reaction 执行，加入 B。
```

同步语句先执行；Promise reaction 在相应的异步作业机制中运行。浏览器的任务、微任务与渲染时机，和 Node 的事件循环阶段、`process.nextTick` 等不是完全同一张顺序表。不要把一个宿主中观察到的 `setTimeout(0)` 与 I/O 回调顺序推广到所有环境。

`async` 函数返回 Promise，抛出的异常表现为拒绝；`await` 让当前异步函数的后续部分延后继续，不会阻塞整个线程。若在两次 await 之间执行很长的 CPU 循环，事件循环仍会被占住。并发处理不是无限创建 Promise，而是控制实际同时运行的工作。

## Promise 组合不等于任务管理

`Promise.all` 保持结果与输入顺序对应，在某项拒绝后整体拒绝，但不会自动取消已经启动的其他操作。`allSettled` 收集每项结果；`race` 取最先 settled 的结果；`any` 等待首个成功，全部失败才拒绝。必须根据业务失败模型选择，而不是为了代码短随手用 race。

```ts
async function both(): Promise<number[]> {
  const a = Promise.resolve(3);
  const b = Promise.resolve(5);
  return Promise.all([a, b]);
}
```

真实网络版本还需要检查 HTTP 状态；`fetch` 返回响应不表示业务成功，HTTP 4xx/5xx 通常需要自己判断。解析响应、验证数据和更新状态分别属于不同失败阶段。

## 超时与取消需要传递到实际操作

Promise 本身没有通用的强制停止协议。`AbortController` 发出协作式信号，由支持该信号的 API 决定如何响应。仅用 `Promise.race([request, timeout])` 能让等待者更早得到超时，却可能留下继续占用连接和内存的请求。超时定时器也应在完成后清除。

取消请求不证明服务器没有写入。为有副作用的操作设计幂等键、结果查询与重试预算；取消渲染更新只解决前端过时结果问题，不能替代后端事务。给组件或请求作用域一个清楚的清理点，注销事件监听、终止支持取消的工作，并观察可能的拒绝。

## 有界并发与背压

处理十万条任务时，先创建十万个 Promise 再用信号量，仍可能产生大量等待对象。固定工作者从迭代器或有界队列领取任务，才能把内存与并发量约束在设计范围内。约定一个工作失败时是停止领取、取消剩余工作、收集失败继续，还是整体回滚；这些策略影响结果语义。

Node stream 与 Web Streams 都围绕消费者速度设计背压，但 API 不相同。忽略写入端的背压信号会把缓冲变成无界积压。网络和文件流要定义最大消息大小、终止条件和错误传播。

## 练习与答案

用可控 Promise 而非真实计时器构造两项操作：一项失败，另一项记录完成。验证 `Promise.all` 的拒绝不等于第二项被取消。再为搜索建议设计“只显示最新请求”的版本号检查，解释为何它能抑制过时 UI，却不能节省已经开始的网络工作；要节约资源，还需要实际取消协议。


<!-- ROUND4 DEPTH LINKS -->
## 继续推演本页难点

[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/10-运行时边界状态机与取消安全|声明成某个类型，为什么不能让网络数据自动可信？]] 本专题补上静态类型结果与运行时行为的分别验证。

这不是替换本页：先掌握原理，再用补充页核对容易被一句话略过的条件。
<!-- END ROUND4 DEPTH LINKS -->

## 关联阅读

- [[计算机知识/10-编程语言/01-Python/10-系统课程/04-异步任务取消与结构化并发|异步任务、取消与结构化并发：谁负责等待谁]]
- [[计算机知识/35-计算机网络/10-系统课程/07-Socket分帧背压与排障|Socket 工程：分帧、背压、超时和可解释的失败]]
- [[计算机知识/10-编程语言/04-Rust/10-系统课程/06-异步Future与Pin|Future、取消与 Pin：理解暂停之后还活着什么]]

## 依据与继续查证

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [TypeScript TSConfig](https://www.typescriptlang.org/tsconfig/)
- [ECMAScript 2024（固定语言参考）](https://tc39.es/ecma262/2024/)

本页的例子、推演与练习为教学构造；语言契约、系统接口和版本相关结论应结合以上原始文档核对。

<!-- COURSE SEQUENCE -->
## 顺序导航与验证

[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/00-TypeScript系统课程索引|本课程总索引]] · [[计算机知识/_labs/round3/TS/TypeScript-实验说明|本课程实验]]

上一讲：[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/04-条件映射类型与声明文件|条件类型、映射类型与声明文件：类型级计算也需要规格]]

下一讲：[[计算机知识/10-编程语言/05-TypeScript/10-系统课程/06-模块构建测试与发布|模块、构建、测试与发布：开发环境成功不是部署成功]]
<!-- END COURSE SEQUENCE -->
