---
domain: "计算机知识"
type: "course"
stage: 3
prerequisites:
  - "[[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|认证会话越权与API测试]]"
  - "[[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]"
sources:
  - "https://docs.python.org/3.13/library/sqlite3.html"
  - "https://www.sqlite.org/lang_transaction.html"
  - "https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html"
  - "https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html"
  - "https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html"
content_status: "usable"
evidence_status: "partial"
---

# 现代 API、业务逻辑与并发边界

## 从一个端点转向一组状态转换

先修 [[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|认证与授权]] 和 [[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP 语义]]。本页研究“每个单独请求都看似合法，组合后为什么仍会违反合同”。工具入口依旧是 curl、Burp 和 ZAP，但业务规则必须由产品定义。

设报告状态只有 `draft → submitted → approved`。作者可编辑自己的草稿，提交后不可再改核心字段；同租户审核员可以审批非本人提交的报告；其他租户不能访问。把这些写成状态转换与拒绝条件，比仅记录“有提交按钮”更精确。

## GraphQL：一条 HTTP 请求可能调用许多解析器

查询描述希望得到的字段，由 resolver 取回数据。以下只是虚构 schema 的结构示例，不是本包可运行端点：

```graphql
query MyReport {
  report(id: 17) {
    id
    title
    status
  }
}
```

请求能通过语法和类型检查，不表示每个对象、嵌套关系或字段都被授权。应在实际取回数据的边界实施一致策略，并检查返回的字段投影。深度、字段数量、列表规模和后端扇出共同影响成本，HTTP 请求数不是充分的资源预算指标。[^v2-graphql]

在自有测试 schema 中用极少对象验证：本人摘要可读、跨租户不可读、私密字段按合同投影、未授权 mutation 不改变状态。不要用无限嵌套或大列表“验证”资源控制；源码审阅和明确有界的功能测试优先。关闭 introspection 可减少暴露，但不会修复 resolver 的授权缺陷。

## GraphQL成本：深度相同，工作量也可能相差很大

查询深度只描述嵌套层级，不能单独代表计算成本。列表长度、重复字段、解析器代价、批处理和缓存都会影响工作量；访问控制应落实到对象与字段，而不只是在进入 GraphQL 端点时检查登录。[^v5-graphql]

原创的简化计数：一次请求得到 1 个用户、其 10 份报告，以及每份报告 20 条评论。在不共享对象、每项恰好展开一次的模型下，返回对象数是 $1+10+10\times20=211$。如果报告上限改为 100，同样的嵌套深度就变成 $1+100+100\times20=2101$。这不是数据库查询次数：批加载可能合并查询，缓存可能消除部分工作，某个解析器也可能执行多次外部调用。

因此深度限制、列表上限、成本预算和运行超时分别控制不同量，不能相互替代。批处理与缓存还必须尊重身份边界：同一对象编号在不同租户下可能不同，同一对象的可见字段也可能随角色变化，详见 [[计算机知识/Kali/03-Web与API安全/13-HTTP中间层与消息解释#缓存键是对请求划分等价类|缓存键与等价类]]。

## WebSocket：握手成功不代表后续消息永久被授权

WebSocket 建立较长寿命的双向消息通道。需要验证握手时的身份与 Origin 策略，也要在后续每种业务消息上校验对象、动作和状态。会话退出、令牌过期或角色撤销后，已有连接如何失效必须有规则。消息大小、频率、格式与队列容量同样属于接口合同。[^v2-websocket]

测试用合成报告订阅：只订阅本人/被授予的对象，改变会话状态后观察是否继续收到内容，记录消息时间和连接 ID。仅抓到握手 101 不能证明整个消息生命周期安全；断网后的自动重连也要重新进入身份和订阅检查。

## 长连接上的身份不能冻结全部未来权限

WebSocket 握手时身份有效，不能推出连接存续期间每条消息都允许。对象归属、角色撤销、资源状态和订阅范围仍可能变化。应将连接身份、消息动作、目标对象和当前授权条件分开解释；重连后的消息重放则重新遇到上面的幂等与交付问题。这里是对既有认证模型的推演，不是本轮实现或测试了一个 WebSocket 服务。

## 并发：两个请求可能都通过同一个过时检查

用只剩一个教学名额的内存模型说明竞态：A 读到剩余 1，B 也读到 1；两者分别检查“大于零”后都提交成功。如果读、判定和更新不是一个受保护的原子操作，就可能产生两次成功。这里是确定性交错推演，不对线上系统发并发负载。[^v2-businesslogic]

“把读写放进事务”仍需要选择足够的隔离、锁或条件更新语义。设计目标可以是条件更新只允许一个成功、版本号不匹配拒绝，或数据库唯一性约束阻止重复接受。哪种方案合适取决于业务不变量，不由工具替你决定。

幂等键用于识别同一业务操作的重复提交，不是任意相同请求的全局通行证。它需要绑定主体、操作内容和合理生命周期，同键不同内容的行为要定义。网络超时后客户端无法知道操作是否已完成时，安全重试尤其依赖这些语义。

## 从检查一个布尔值到一次原子状态变更

继续报告案例。Alice 将报告 17 从 draft/0 提交成 submitted/1，Bob 再批准成 approved/2。数字是版本，不是 HTTP 状态码。一个完整写操作应同时满足：当前主体获授权、当前状态可转换、客户端期望版本相符、业务更新与必要审计/幂等记录一起提交。

下面是**概念 SQL 片段**，不是本页可单独执行的数据库初始化脚本；实际参数绑定与事务由实验 L 的源文件负责：

```sql
UPDATE reports
SET status = ?, version = version + 1
WHERE id = ? AND tenant = ? AND status = ? AND version = ?;
```

条件中的 tenant 限定对象范围，status 限定状态机，version 限定并发前提。影响行数为 0 表明这个操作没有命中全部条件，不等于对象一定不存在，也不一定只是版本过期。不能不检查 rowcount 就继续写“审批成功”的审计记录。

### 同一幂等键究竟绑定什么

实验 L 将键作用域设为 `(tenant, actor, key)`，再绑定 `(report_id, action, expected_version)`。同一键同一内容返回原有小结果，不重复更新或追加事件；同一键换内容明确冲突。同一个字符串在另一个主体名下不是同一请求，且仍须独立通过对象授权。

这里特意区分**历史响应**与**当前资源状态**。Alice 首次 submit 得到 submitted/1；Bob 后来 approve 到 approved/2。Alice 重放原 submit 键，应拿到首次结果并标明 replayed，而不是再次把状态改回 submitted。要查询当前资源应走单独的读取合同。保留原响应与查询现状是两种职责，不能混在一个“去重缓存”里。

### 事务解决了哪些问题，又没有解决哪些

本包选择 Python sqlite3 显式事务，`isolation_level=None` 后主动 `BEGIN IMMEDIATE`。它在开始阶段争取写事务；另一个写入者可能收到 SQLITE_BUSY。数据库忙不是授权拒绝，也不说明应用应无限自动重试。SQLite 的这一行为不能直接替代 PostgreSQL 或 MySQL 的隔离与锁实验。[^v3-sqltx][^v3-pysqlite]

业务更新、事件和幂等账本写入放在同一个事务，测试会人为令后两步失败，确认三者一起回滚。这验证当前数据库内的原子性，不保证外部邮件、消息队列或支付调用也能回滚。若业务包含外部副作用，需要另行设计提交后交付、重试与去重合同；本实验没有实现分布式 exactly-once。

并发演示采用两个连接和可重复的固定交错，不用海量并发压测。它证明一个特定锁冲突路径确实可观察，不声称覆盖所有调度、锁饥饿或生产吞吐问题。具体运行与失败注入见 [[计算机知识/Kali/07-综合实验/15-实验L事务幂等与并发控制|实验 L]]。

## 幂等效果、消息交付与响应重放不是同一个保证

原创的状态模型：客户端发送操作，服务端完成状态变更后，响应在途中丢失。此时客户端观察是“未知”，服务端状态却可能是“已提交”。客户端重试解决了交付不确定性，却可能造成重复效果；禁止重试又可能丢失尚未到达的操作。传输层确认也不能消除此处的应用歧义，参见 [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCP确认与业务提交]]。

幂等性约束重复操作的预期效果，不要求每次响应字节相同。去重键只能在它覆盖的身份、操作、参数、存储范围和保留期内发挥作用；同一个键配上不同请求内容必须有明确冲突政策。“恰好一次”必须说清范围：数据库中某行状态只变一次，不自动保证外部邮件、支付或另一个系统中的副作用也只执行一次。

本包实验 L 的事务把若干本地数据库变化放在同一个提交边界中，能够说明原子性和特定去重模型；不跨越到分布式提交、网络分区或所有故障恢复情形。理解这一边界，比给本地例子贴上“生产级”标签更重要。

## 分页、缓存与异步任务的边界

列表接口必须对每项或查询范围应用授权；只检查“能否调用 list”而不限制租户会漏掉对象边界。游标是分页状态，不是权限凭证。缓存键要包含会影响授权结果的身份/租户维度，或避免共享缓存私密结果。

异步导出需检查创建任务、读取进度、取得结果和结果过期四个阶段。创建时曾被允许不代表很久以后仍有下载权限。关联到 [[计算机知识/Kali/07-综合实验/12-实验I多租户字段与动作授权|实验 I]] 可先验证有限授权与状态规则，再迁移到真实框架。

## 自检与验收边界

为什么对象 ID 使用 UUID 仍要检查租户？因为不可猜测不等于被授权。为什么一次请求限流不足以描述 GraphQL 成本？因为内部可能触发多个对象解析和下游调用。为什么两次串行测试都成功不能排除竞态？因为错误可能仅在检查与更新交错时出现。

本包未运行 GraphQL/WebSocket 服务器和并发负载，相关内容为机制解释与测试设计。附带离线模型验证的是声明的有限合同，不替代具体数据库隔离级别、框架会话或浏览器行为的实测。

## 来源与核验范围

[^v5-graphql]: [OWASP — GraphQL Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html)；定位：查询成本、批处理、访问控制和资源限制。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v2-graphql]: [OWASP：GraphQL](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html)；定位：Access Control / Query Cost / Batching。本轮网页读取：2026-09-05。

[^v2-websocket]: [OWASP：WebSocket Security](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)；定位：Authentication and Authorization / Session Management / Origin。本轮网页读取：2026-09-05。

[^v2-businesslogic]: [OWASP：Business Logic Security](https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html)；定位：State / Race conditions / Integrity / Testing。本轮网页读取：2026-09-05。

来源支持对应机制和接口；案例为原创教学设计。命令除验收记录明确列为实测者外均为参考，不将文档读取等同于 Kali 实机验证。

[^v3-sqltx]: [SQLite：Transaction](https://www.sqlite.org/lang_transaction.html)；定位：DEFERRED / IMMEDIATE；SQLITE_BUSY；COMMIT / ROLLBACK。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

[^v3-pysqlite]: [Python 3.13：sqlite3](https://docs.python.org/3.13/library/sqlite3.html)；定位：Transaction control；isolation_level；execute parameter binding。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]