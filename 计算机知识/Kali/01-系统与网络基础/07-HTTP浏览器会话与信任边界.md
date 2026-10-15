---
domain: "计算机知识"
type: "course"
stage: 1
aliases:
  - "HTTP基础"
  - "认证与授权"
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]"
sources:
  - "https://fetch.spec.whatwg.org/"
  - "https://developer.mozilla.org/en-US/docs/Glossary/Site"
  - "https://www.rfc-editor.org/rfc/rfc6454.html"
  - "https://www.rfc-editor.org/rfc/rfc9114.html"
  - "https://www.rfc-editor.org/rfc/rfc9113.html"
  - "https://www.rfc-editor.org/rfc/rfc9111.html"
  - "https://www.rfc-editor.org/rfc/rfc9110.html"
  - "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html"
  - "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html"
content_status: "usable"
evidence_status: "partial"
---

# HTTP浏览器会话与信任边界

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]。

## 请求到响应是一段有状态的计算

HTTP 是请求与响应协议。客户端发出方法、目标、字段和可选内容，服务端返回状态、字段和内容。协议本身提供消息语义，业务应用再赋予“登录”“查看账单”“删除文件”等含义。[^s1] 安全测试要同时理解这两层，否则容易把状态码当成最终结论。

```http
GET /api/reports/17 HTTP/1.1
Host: lab.test
Accept: application/json

```

空行标志首部结束。该示例没有携带真实凭据。`GET` 按语义应是安全方法，但实际应用可能错误地在 GET 中修改状态；测试时不能仅凭方法名假定“绝不产生副作用”。幂等表示重复请求的预期效果与一次相同，不等于没有副作用，也不等于每次返回字节完全一致。

## URL 的不同部分不等价

scheme 决定协议，host 和 port 确定连接目的，path 选择资源，query 传递参数；fragment 通常由客户端处理而不作为请求目标发给服务器。百分号编码、表单编码和 JSON 字符串转义处于不同解析层。二次解码、代理重写和路径规范化不一致，是很多安全边界问题的来源。

如果你在地址栏看见一个 `#fragment` 改变页面，不应立即假定服务器读到了 fragment；可能是浏览器端 JavaScript 在响应它。这种辨别会影响 [[计算机知识/Kali/03-Web与API安全/07-XSSCSRF与浏览器安全边界|DOM XSS]] 的分析。

## 方法、状态与重放风险的对应关系

安全方法的“安全”指客户端请求的预期语义不以改变资源状态为目标，不意味着没有日志等附带效果。幂等方法重复执行的预期资源效果相同；DELETE 可以是幂等的，但显然会删除资源。POST 通常不能默认重试，PUT 的幂等语义也不能修复错误的服务实现。[^v2-http]

状态码要保留请求语境：401 通常要求认证挑战；403 表示拒绝履行请求；404 可以用于隐藏资源存在性；409 表示与当前资源状态冲突；412 表示请求先决条件不成立。一个 `200` 登录页与一个 `200` 报告正文具有完全不同业务含义。不要只比较数字，还要比较内容类型、最终 URL、业务标记和账户状态。

重定向也会改变实验。303 通常引导后续检索，307/308 用于保留方法的重定向；历史兼容行为使 301/302 的处理还要看客户端。跟随重定向之前先看 `Location`，确认没有离开授权范围，并记录每一跳，而不是只保存最终响应。[^v2-http]

## 身份、会话与授权

认证回答“请求代表谁”，会话让多次请求关联到某个身份状态，授权回答“这个身份能对这个对象做什么”。三者都不能被“有一个 Cookie”替代。

会话 Cookie 可使用 `Secure`、`HttpOnly`、`SameSite` 等属性，分别约束某些传输或客户端访问行为；它们不能替代服务端的会话失效与权限检查。[^s2] `HttpOnly` 能限制 JavaScript 直接读取该 Cookie，但已在页面上下文执行的恶意脚本仍可能发起带凭据请求。

本课程统一使用两个测试用户 Alice 与 Bob，各自拥有一个报告对象。Alice 登录成功，只说明身份被确认；若 Alice 能读取 Bob 的报告，则问题在对象级授权。详见 [[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|双账户授权矩阵]]，并用 [[计算机知识/Kali/07-综合实验/04-实验CWeb请求与访问控制|离线权限案例]] 验证这个区别。

## 同源策略与 CORS

浏览器的源通常由 scheme、host、port 组成。同源策略限制不同源之间的某些读访问；CORS 允许服务器在一定条件下向浏览器声明跨源读取权限。它不是认证机制，也不是阻止所有跨站请求的防火墙。

一个请求能被浏览器发出，与它的响应能被攻击页面读到，是两件事。CSRF 正利用某些带凭据请求可被发起的条件；XSS 则可能把代码放进受信任源内部执行。不要把二者都归结为“输入没过滤”。

## 同源、同站、凭据与授权：四道不同的判断

**源（origin）**主要由 scheme、host、port 组成；**站点（site）**是另一种边界，在这里采用考虑 scheme 的站点模型，还涉及可注册域。不要用“同一个公司域名”替代协议定义，也不要把可注册域简化成固定取最后两段。[^v5-origin][^v5-site]

以 `https://app.lab.test` 为基准，`https://api.lab.test` 是跨源但同站；`https://app.lab.test:8443` 因端口不同而跨源，但在本例仍同站；`http://app.lab.test` 因 scheme 不同既跨源，也不满足这里采用的同站条件。这些是边界比较，不是在判定相应请求一定允许。

浏览器还要分别处理“是否发请求”“是否携带凭据”“脚本是否能读响应”。Cookie 的域、路径、Secure、SameSite 等约束与请求的 credentials 模式共同影响凭据发送；CORS 控制特定跨源读取，不等价于服务端对象授权。预检是部分请求的额外许可流程，不是所有跨源请求都会先预检。[^v5-fetch]

原创的推理题：页面脚本看不到响应，但服务端状态已改变，这不矛盾，因为执行动作与允许脚本读取是不同判定。相反，curl 能读到响应，也不能证明浏览器允许同样的脚本读取，因为命令行客户端不承担浏览器的同源策略。验证 CSRF、CORS 与越权时，必须说清究竟检验哪道边界，详见 [[计算机知识/Kali/03-Web与API安全/07-XSSCSRF与浏览器安全边界|浏览器威胁模型]] 和 [[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|对象授权]]。

## HTTP 版本变化后，哪些知识继续成立

HTTP/1.1 主要以文本形式表达起始行和首部；HTTP/2 以帧和流组织同一连接中的多路通信，并使用 `:method`、`:path`、`:authority` 等伪首部；HTTP/3 映射到 QUIC。认证、授权与资源语义没有因为协议更新就消失。[^v2-http2][^v2-http3]

因此，一条 TCP 连接不一定只对应一个并行请求；HTTP/3 又不能用“只抓 TCP 443”完整观察。Burp 中便于阅读的请求表示不一定逐字等于线上二进制帧。分析跨代理行为时应记录入口协议、后端协议及转换层，不把 GUI 展示文字当成原始字节证据。

> [!question] 迁移检查
> 把 curl 强制切到 HTTP/1.1 后问题消失，是否证明 HTTP/2 实现有漏洞？尚不能。协议变化也可能改变连接复用、代理路径或负载分配。需要隔离这些变量，并保留原始错误和协商证据。

## 从单个请求转向多组件解释

本页负责 HTTP 语义和浏览器边界；当疑问是“代理看到的和服务端为什么不同”，进入 [[计算机知识/Kali/03-Web与API安全/13-HTTP中间层与消息解释|HTTP中间层与消息解释]]。那里统一解释消息边界、版本转换、规范化和缓存等价类，避免在 Burp、抓包、SSRF 三处分别维护不同版本的完整推导。

## 缓存、代理与证据

反向代理、CDN 和缓存可能代替后端返回内容。响应时间变短可能来自缓存，状态变化可能来自限流，头字段里的 `Server` 也可能只指向前置层。测试必须记录代理配置、重定向、Cookie 状态以及是否复用连接。

`200 OK` 不保证业务成功：响应内容可能写着“权限不足”；`404` 不证明对象从不存在：应用可能故意隐藏无权访问的资源；`500` 不证明 SQL 注入：很多异常都会产生它。结论必须结合请求条件与内容差异。

## 缓存是另一位会“替你回答”的参与者

缓存指令与年龄计算统一见 [[#缓存判断要把存储许可、缓存键和新鲜度分开|缓存主解释]]；这里保留跨账户应用：Alice 得到 ETag 后的 304 是条件验证结果，没有新完整正文，不能记成“服务器向 Bob 返回报告”。身份、缓存键、请求字段与代理层分别记录，ETag 不是凭据。[^v2-httpcache] 业务条件见 [[计算机知识/Kali/03-Web与API安全/12-现代API业务逻辑与并发边界|业务与并发边界]]。

## 缓存判断要把存储许可、缓存键和新鲜度分开

先问响应能否被存储，再问当前请求能否复用它，最后问是否需要向源站验证。`no-store` 限制存储；不带字段参数的响应 `no-cache` 允许存储，但复用前需成功验证；`private` 面向共享缓存限制，不等于内容已经加密。以下只讨论普通指令语义，不覆盖全部扩展指令和组合覆盖规则。[^v3-cache]

缓存键至少围绕方法与目标 URI；`Vary` 会让指定请求头参与变体匹配。例如服务按语言返回不同内容，不能因为路径相同就把中文版本交给英文请求。私密响应是否共享又是独立授权问题：正确的语言变体不能修复错误的用户隔离。不要靠“URL 不好猜”保护能被共享缓存取回的对象。

### 带时间单位算一次可复用窗口

下面是原创数值例子，使用 RFC 9111 的 Age 计算框架。假设请求在 12:00:00 发出，12:00:02 收到响应；响应 `Date` 为 12:00:00，`Age: 20`，本地到 12:00:17 才再次使用它。所有时间来自已校准时钟，单位为秒。

表观年龄是 `max(0, 2)=2`；收到的 Age 加传输延迟为 `20+2=22`；取较大值得到收到时年龄 22；再加本地驻留时间 `17-2=15`，当前年龄为 37。若适用的新鲜寿命是 `max-age=60`，还剩 23 秒。它不是“收到后永远再给 60 秒”，也不是“Age 是服务器处理用时”。若还有 `no-cache`，即使年龄小于 60，也不能绕过验证要求。[^v3-cache]

现实中时钟误差、多级缓存、重验证和具体缓存策略都会增加条件。不要仅凭 `Age` 缺失就认定绝无缓存，也不要凭单次较快响应证明命中某个 CDN。

### 304 不是一次新的完整实体响应

带 `If-None-Match` 的请求可能获得 304，由客户端结合已有实体与更新元数据使用。只把这次空响应体保存下来，会丢失用户实际看到的内容；应记录请求条件、已有实体的来源和摘要、返回验证器及最终使用的表示。ETag 用于表示验证，不是数字签名或身份凭据。

因此“浏览器还显示旧权限内容”至少有两种假说：服务端仍然返回它，或客户端/中间缓存复用旧副本。用隔离身份、明确缓存条件和实际请求记录区分它们，再连接 [[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|会话撤销]] 与 [[计算机知识/Kali/03-Web与API安全/12-现代API业务逻辑与并发边界|异步导出和缓存权限]]。删除浏览器缓存可做诊断，但不代替服务端修复。

## 自检与后续

为什么“使用 HTTPS 就不会有越权”是错误的？HTTPS 保护传输边界，而越权发生在服务端把身份映射到对象权限时，两者处在不同层。下一步用 [[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curl 的可控请求]] 建立基线，再使用 [[计算机知识/Kali/03-Web与API安全/03-BurpSuite工作流|Burp]] 或 [[计算机知识/Kali/03-Web与API安全/04-ZAP代理与被动扫描|ZAP]] 观察浏览器真正发送了什么。

## 来源与核验范围

[^v5-origin]: [RFC 6454 — The Web Origin Concept](https://www.rfc-editor.org/rfc/rfc6454.html)；定位：§4–5：源的元组模型与同源比较。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-site]: [MDN — Site](https://developer.mozilla.org/en-US/docs/Glossary/Site)；定位：schemeful site 与 origin 的区别。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-fetch]: [WHATWG：Fetch Standard](https://fetch.spec.whatwg.org/)；定位：§3.3 CORS protocol；CORS-preflight fetch；credentials。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [IETF RFC 9110：HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)；定位：§9 Methods / §15 Status Codes。网页读取：2026-09-05。
[^s2]: [OWASP：Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)；定位：Cookie 属性、更新与失效。网页读取：2026-09-05。
[^s3]: [OWASP：Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)；定位：Deny by Default / Validate Permissions on Every Request。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-http]: [IETF RFC 9110：HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)；定位：§9 methods / §13 conditional requests / §15 status codes。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-httpcache]: [IETF RFC 9111：HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)；定位：§4 freshness / §5 Cache-Control and Vary。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-http2]: [IETF RFC 9113：HTTP/2](https://www.rfc-editor.org/rfc/rfc9113.html)；定位：§4 Frames / §5 Streams / §8 HTTP messages。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-http3]: [IETF RFC 9114：HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html)；定位：§2 protocol overview / §4 request mapping。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-cache]: [RFC 9111：HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)；定位：§2；§4.1；§4.2.3；§4.3；§5.2.2。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]