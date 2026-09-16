---
domain: "计算机知识"
type: "course"
stage: 3
aliases:
  - "XSS"
  - "CSRF"
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]"
  - "[[计算机知识/Kali/03-Web与API安全/01-Web测试模型与手工基线|Web测试模型与手工基线]]"
sources:
  - "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html"
  - "https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html"
  - "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html"
content_status: "usable"
evidence_status: "partial"
---

# XSSCSRF与浏览器安全边界

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]；[[计算机知识/Kali/03-Web与API安全/01-Web测试模型与手工基线|Web测试模型与手工基线]]。

## 两种问题跨越不同信任边界

跨站脚本（XSS）让不可信内容成为受信任页面上下文中的可执行代码；跨站请求伪造（CSRF）则利用浏览器的身份携带行为，让用户在未明确意图下触发服务端动作。XSS 关注“谁能运行代码”，CSRF 关注“谁能促成带身份的动作”。[^s1][^s2]

反射型、存储型和 DOM 型描述数据进入执行位置的路径，不代表严重性从低到高。后果取决于上下文、会话、页面能力和用户交互条件。

## 沿数据流追踪 source 与 sink

source 是不可信数据的入口，例如 URL、表单或服务器返回字段；sink 是最终解释该数据的位置。假设报告标题保存为 `<b>LAB</b>`：如果页面用 `textContent` 设置文本，读者应看到字面标签；如果放入 `innerHTML`，浏览器会按 HTML 解释。这个差异证明了解析上下文变化，尚未单独证明脚本能够执行。[^v2-xss]

正确审阅要列出每个转换步骤：解码、模板转义、拼接、DOM 插入。已经为 HTML 文本做过转义，不代表后来插入 JavaScript、样式或 URL 时仍安全。富文本净化应匹配所允许的标签和属性，并考虑后续 DOM 修改是否再次引入不可信内容。

## 输出编码必须与上下文对应

把名字显示为 HTML 文本，应按 HTML 文本上下文处理；把值放进属性、JavaScript 字符串或 URL，需要各自正确的编码与验证。某个编码器在一种上下文安全，不保证能随意跨上下文复用。

```html
<!-- 教学反例：如果 user_input 未经正确处理，文本边界可能被改变 -->
<div>USER_INPUT</div>
```

在自建教学页面中先用无执行效果的 `<b>LAB-MARKER</b>` 检查输入是否被当作 HTML，随后结合代码路径确认是否能到达危险执行位置。**HTML 被解释不自动等于已经证明 JavaScript 可执行**，必须保留这个限定。

现代框架的默认转义有帮助，但 `innerHTML`、模板绕过、原始 HTML 渲染与不安全 URL sink 可能绕开它。允许富文本时通常需要合适的净化器，而不是用正则删除 `<script>`。

## 编码、清洗与安全接收点的职责不同

编码把数据表示为目标语法中的字面内容；HTML 清洗在允许部分标记的需求下，按结构与政策删除或限制不允许的内容；安全接收点（safe sink）尽量不把输入送入可执行或标记解释上下文。这三者不能用一个“过滤函数”概括。OWASP 分别讨论 HTML、属性、JavaScript、CSS、URL 等上下文，并强调清洗后再修改内容可能破坏原保证。[^v5-xss-context]

原创例子：用户只是要显示商品名 `A & B`，把它写入普通文本节点，不需要把它解释成 HTML 文档片段。若业务确实允许富文本，则需求变成“保留哪些结构”，不能简单地把所有标记转成文字后宣称功能完整。再把一段经过 HTML 处理的文本嵌入另一个语言上下文，原来的安全论证也不自动迁移。

用函数关系说明这个跳步：处理 $E_A$ 只承诺适合上下文 A，不推出 $E_A(x)$ 适合上下文 B；若后续转换 $T$ 会改变结构，先清洗再转换得到 $T(S(x))$，也不自动具有原 $S$ 的安全性质。具体是否安全必须看转换与最终接收点，不能仅凭函数名称中有 escape 或 sanitize 判断。

## CSP 是减损控制，不是根因修复

内容安全策略（CSP）可限制脚本来源和执行条件，但政策的具体指令、nonce/hash、第三方脚本和旧代码都会影响效果。看到一个 `Content-Security-Policy` 首部不等于没有 XSS；没有该首部也不等于一定存在可执行注入。

`HttpOnly` 限制 Cookie 被脚本直接读取，但同源脚本可能仍能发起带会话请求。因此不应把“无法读 Cookie”写成“XSS 无影响”。应根据业务动作、数据访问和实际边界评估。

## 同源和同站不是一个边界

同源围绕 scheme、host、port；Cookie 的 SameSite 使用“站点”语义，不能仅用三个值是否完全相等代替。同一可注册域下的不同子域可能不是同源，却仍在同站关系内；现代 schemeful 规则还考虑协议。因此同站中的受控子域问题不能被 SameSite 一概消除。[^v2-csrf]

CSRF 测试逐项回答：认证材料是否自动附带；这个动作是否改变状态；跨站请求能否被浏览器构造；token 是否与会话绑定且服务端验证；Origin 检查对缺失或 `null` 值怎样处理。不能只做“删 token 后仍成功”一个测试就排除所有其他控制。

## CSRF 的成立条件

典型条件包括可被跨站发起的状态改变请求、浏览器自动附带认证材料，以及缺少有效的请求意图验证。防护组合可能涉及不可预测且正确绑定的 CSRF token、Origin/Referer 验证、SameSite Cookie 和高风险操作的再认证。[^s2]

CORS 通常限制跨源读取，不是通用的“禁止请求发送”机制；只依赖 CORS 防 CSRF 会混淆浏览器发送与读取两件事。使用 Bearer token 的 API 是否受同样风险影响，取决于令牌存储和附带方式，不能只凭“JSON API”排除问题。

## HTTP 工具与浏览器观察互补，不能互相代替

代理和重放工具能看到请求与响应，但最终 DOM、脚本创建的节点、运行时数据流及浏览器安全政策还需要相应浏览器观察。响应文本中出现输入，是数据反射的证据，不一定是执行证据；响应中没出现输入，也不能排除客户端从别处读取并写入危险接收点。

更完整的链路是“输入来源 → 转换 → 接收点 → 实际上下文 → 安全政策与影响”。它与 [[计算机知识/Kali/03-Web与API安全/13-HTTP中间层与消息解释|HTTP 消息解释]] 共享表示转换问题，但边界位于浏览器。另一方面，CSRF 关注带有既有身份的请求是否被不应授权的来源驱动，不要求把输入解释成脚本；即使两者都涉及浏览器，也不能用一个 XSS 测试替代 CSRF 判断。

## 安全的测试设计

用自建应用的两种站点上下文，执行无业务后果的教学状态改变，记录 Cookie 属性、请求 Origin、token 的绑定与失效。不要向真实用户投递测试链接，也不要用真实转账、短信或密码变更功能演示。

本包静态 HTTP 服务不包含登录或跨站动作；相应在线实验是扩展项，不假称已经完成。可以先在 [[计算机知识/Kali/07-综合实验/04-实验CWeb请求与访问控制|离线权限案例]] 中厘清“身份存在”与“请求意图/对象权限”的不同。

## 修复的正反对照

对 XSS，正常中文、符号和允许的富文本仍应按产品合同显示，危险上下文不得获得执行能力；对 CSRF，合法同站操作应成功，跨站缺少有效意图验证的操作应拒绝；对 CORS，允许的受信任源能读取被授权响应，不允许源不能因此读取身份数据。三组目标分别验收，不把其中一个首部的存在当作总证明。

具体浏览器策略与应用配置需要实际浏览器验证。本包离线字符串或授权函数测试不冒充浏览器实验，也不复制真实 Cookie 到脚本中。

## 自检

用户输入被 HTML 转义后能否直接拼进 JavaScript 字符串？不能，解析上下文不同。若应用所有 POST 都带一个固定 token 是否足够？不够，需评估不可预测性、会话绑定、验证位置与跨站读取可能性。

## 来源与核验范围

[^v5-xss-context]: [OWASP：Cross Site Scripting Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)；定位：Output Encoding；HTML Sanitization；Safe Sinks。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [OWASP：XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)；定位：上下文编码、危险 sink 与净化。网页读取：2026-09-05。
[^s2]: [OWASP：CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)；定位：CSRF tokens / SameSite / Origin checks。网页读取：2026-09-05。
[^s3]: [OWASP：Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)；定位：Cookie 属性、更新与失效。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-xss]: [OWASP：XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)；定位：Output Encoding / Safe Sinks / HTML Sanitization。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-csrf]: [OWASP：CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)；定位：SameSite / Origin / CSRF tokens。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]