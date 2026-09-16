---
domain: "计算机知识"
type: "course"
stage: 3
aliases:
  - "Burp Suite"
  - "Burp代理"
prerequisites:
  - "[[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curlHTTPie与接口重放]]"
  - "[[计算机知识/Kali/03-Web与API安全/01-Web测试模型与手工基线|Web测试模型与手工基线]]"
sources:
  - "https://portswigger.net/burp/documentation/desktop/tools/sequencer/results"
  - "https://portswigger.net/burp/documentation/desktop/tools/intruder/configure-attack/attack-types"
  - "https://portswigger.net/burp/documentation/desktop/tools/repeater/http-messages"
  - "https://portswigger.net/burp/documentation/desktop/tools/repeater"
  - "https://portswigger.net/burp/documentation/desktop/getting-started"
  - "https://www.kali.org/tools/burpsuite/"
content_status: "usable"
evidence_status: "partial"
---

# BurpSuite工作流

**先修关系：** [[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curlHTTPie与接口重放]]；[[计算机知识/Kali/03-Web与API安全/01-Web测试模型与手工基线|Web测试模型与手工基线]]。

## 代理的价值是看见完整请求链

Burp Suite 把浏览器与服务器之间的请求置于可观察、可修改和可重放的工作流中。Proxy 负责流量经过与历史，Repeater 适合单个请求的受控比较，Decoder/Comparer 帮助编码与差异分析。自动化能力和项目功能可能因版本/授权版本而异，不能把某个付费功能写成所有安装都有。[^s1][^s2]

不要把 Burp 当作一个“按一下扫描就有结论”的按钮。本章的目标是独立重放同一请求，并解释只有一个输入变化时的差异。

## 组件分工：采集、变换、比较和统计不是同一种能力

| 组件 | 主要处理对象 | 结果能够直接支持什么 | 不能替代什么 |
| --- | --- | --- | --- |
| Proxy 与 HTTP history | 经由代理的交互及其记录 | 当前观察点看到了哪些消息 | 未经过代理的全局流量或全部业务覆盖 |
| Repeater | 人工控制的一次或少量重放 | 输入变化与响应差异的具体证据 | 并发系统的普遍保证 |
| Intruder | 已选位置和候选集合的系统组合 | 给定组合规则下的样本分布 | 漏洞真实性和完整输入空间覆盖 |
| Decoder / Comparer | 表示变换、文本或字节差异 | 编码层和差异位置 | 加密认证、差异的业务意义 |
| Sequencer | 选出的令牌样本 | 特定统计检验下的规律 | 生成器不可预测性的密码学证明 |
| Scanner（适用版本） | 可到达的请求与检测规则 | 规则支持的候选发现 | 身份范围、业务意图与最终人工确认 |

组件范围和可用性以对应版本与授权为准。工具名称相邻不代表证据可以直接互换：Decoder 能看到 JWT 内容，不等于验证签名；Comparer 标出字段变化，不等于证明越权。[^v5-burp-tools]

## 建立专用浏览器环境

显式启动 Burp 后，核对代理只绑定回环接口和预定端口，不使用所有接口监听。优先使用 Burp 的专用测试浏览器或独立浏览器配置文件，避免把个人邮件、密码管理器和日常会话流量导入项目。

将 `http://127.0.0.1:8000` 添加到本次目标范围，按当前版本界面配置范围过滤；过滤显示不等于网络层强制阻止越界，需要同时控制浏览器行为和工具自动功能。先对本包静态服务工作，不依赖 HTTPS 证书导入。

处理 HTTPS 时，代理通过受信任的教学 CA 在测试浏览器侧建立 TLS。信任范围应限制在专用测试配置；不要把代理根证书随意装入日常系统全局信任库。实验结束后清理测试配置与证书信任。

## Proxy → History → Repeater

打开 `/health`，确认 Proxy History 里出现了请求与响应。初学时 Intercept 开着会让浏览器停在等待状态：请求并不是“丢了”，而是尚未被转发。理解 Forward、Drop 与关闭拦截的区别，再进行修改。

把请求送入 Repeater，先原样发送一次；保存正常基线。随后只把路径改成 `/missing-lab-page`，观察状态、内容长度和响应体。静态服务应对不存在文件返回找不到，但具体首部与页面文本依 Python 版本而变化，不把本笔记当成逐字输出模板。

记录请求的 Host、方法、路径、Cookie/Authorization 是否存在和响应变化。检查“没有 Cookie 的请求成功”时，先确认目标原本是否就是公开资源；不能把所有公开内容都报告成认证绕过。

## 一次可审阅的 Repeater 操作顺序

以 `/health` 为例，先在独立测试浏览器打开一次，找到 Proxy HTTP history 中相应条目，检查主机、端口、协议与身份，再发送到 Repeater。给标签命名 `baseline-health`，发送原请求一次，保存基线；复制成第二标签，仅改为 `/missing-lab-page`，比较状态、首部和正文。最后回到原标签重发，确认服务状态没有在中间改变。Repeater 的请求历史用于检查“到底改了什么”，不能只截最后一张成功图片。[^v2-burprepeater]

跨两账户时分开浏览器配置或独立 Cookie 上下文，并在每次重放前核对脱敏后的身份标识。仅给标签起 Alice/Bob 名字并不会自动隔离 Cookie。不要让会话处理规则、自动重定向或扩展在你不知情时改写控制变量。

## 小样本比较先于自动化

Repeater 适合验证单个假设；Comparer 帮助比较响应，但动态时间戳、随机标记和压缩会引入噪声。可以先提取稳定业务字段，再比较完整内容，不能为了消除差异把真正的权限字段也删掉。

Intruder 用于按位置替换输入并批量发送请求。只有在有小字典、明确预算和可回滚目标时才使用；不要把用户名/密码列表导入生产登录页。教程里的高并发与无限重试不是必要操作。

Extensions 扩展可能接触完整请求与凭据；安装前审阅来源、权限和数据去向。本包不安装插件，也不依赖社区扩展。Collaborator 等外部交互检测会产生额外数据流与授权问题，本课程不默认启用。

## 用三次重放区分输入效应与环境漂移

在本包静态场景，先发 A：`/health`，再发 B：`/missing-lab-page`，最后原样再发 A。若两次 A 一致而 B 不同，路径变化是较合理的解释；若第二次 A 也失败，先调查服务状态、代理、限流或会话变化，不能只把 B 的差异归因于你改的路径。这是原创的 A–B–A 对照设计，不是自动漏洞判定器。

扩展到自建授权应用后，身份成为额外控制变量。A、B 分别从独立真实登录上下文取得，不手写一个主体字段冒充完成认证。每次请求记录“预期主体、实际采用的凭据引用、对象与动作”，其中凭据引用用受控证据编号而不是令牌正文。Repeater 的目标设置、自动长度更新与协议处理也可能改变请求，保存实际发出的表示，不能只看编辑框。[^v3-repeater]

### 读操作与写操作采用不同复测顺序

对只读请求可直接做 A–B–A，但对审批、提交、删除等动作，第一次 A 可能已经改变状态，第三次 A 不再处于相同前提。应在自建靶场重新构造独立对象、恢复受控快照，或显式测试幂等语义，并记录每轮初始版本。不要为了得到相同响应而反复向同一真实业务对象提交动作。

响应正文正常而审计事件重复，是与“界面是否成功”不同的问题。把请求、持久状态和事件数量串起来，才能判断一次重试有没有重复副作用。[[计算机知识/Kali/07-综合实验/12-实验I多租户字段与动作授权|实验 I]] 只提供授权判断模型；[[计算机知识/Kali/07-综合实验/15-实验L事务幂等与并发控制|实验 L]] 才实际检查状态、版本、事件和幂等账本。两种证据不可互换。

## 响应比较不是只比字节数

动态时间戳、请求 ID、CSRF token 和广告片段会使相同业务结果字节不同；固定错误模板会使完全不同原因的结果长度相同。先标出稳定业务字段，再做局部比较，并保留原响应供追溯。规范化规则必须在比较前确定，不能为得到预期结果而临时删掉不合意字段。

若接口按设计返回 404 隐藏对象存在性，关注是否泄露受保护字段及服务端实际行为，而非强求 403。对写入动作，用教学数据的前后状态和审计记录确认副作用；浏览器没显示变化并不证明后端未执行。

## Intruder的组合模式其实是四种实验设计

以下只用无敏感含义的颜色与尺寸字段解释组合数学，不提供认证尝试方案。设两个可替换位置，颜色候选有 3 项、尺寸候选有 4 项。

Sniper 对各位置轮流使用同一集合；若公共集合有 3 项、位置有 2 个，名义请求数为 $2\times3=6$。Battering ram 在所有位置同步放入同一个值，名义请求数为 3。Pitchfork 将不同集合按位置配对，本例按较短集合结束，共 3 组。Cluster bomb 取笛卡尔积，共 $3\times4=12$ 组。[^v5-intruder-types]

这些数量不含连接重试、重定向以及其他附加交互，也不代表生成结果都具有业务意义。若字段之间本来有对应关系，笛卡尔积会制造大量无效组合；若想知道两个字段的交互作用，只沿对角线配对又会遗漏情况。工具模式应服从要检验的假设，而不是追求最多请求。停止条件与影响约束沿用 [[计算机知识/Kali/00-导航与方法/02-授权范围与风险分级|授权与风险分级]]。

## Sequencer：统计上未发现规律，不等于无法预测

Sequencer 的分析依赖样本量、令牌提取位置、位或字符转换及检验设置。官方说明明确把统计结果视为指示性证据：确定性生成方式也可能呈现看似随机的输出，样本太少会削弱结论。[^v5-sequencer-results]

原创解释：假设某系统输出公开计数器经公开散列函数计算后的值。结果可能没有明显字符偏差，但知道计数器和算法的人仍可计算下一个值。统计检验问的是“样本是否表现出某些可检测结构”，不可预测性问的是“在给定攻击者知识后，下一值能否被有效预测”，条件不同。

不要把显著性水平 0.05 读成“令牌有 95% 概率安全”。作为独立检验的数学示例，20 次各有 5% 假阳性概率的独立检验，至少一次假阳性的概率是 $1-0.95^{20}\approx64.2\%$。这不是 Sequencer 内部聚合算法的复述，也不假定实际检验独立；它说明为什么必须理解多重比较和判定规则。更完整的生成与猜测模型见 [[计算机知识/Kali/05-密码无线与专门领域/01-哈希口令KDF与估算|熵、候选分布与攻击者知识]]。

## 常见卡点的分层诊断

“浏览器没网”先确认代理监听是否存在、端口是否冲突、请求是否卡在 Intercept；“HTTPS 报错”区分浏览器是否信任本次测试 CA、上游证书是否有问题，以及应用是否有固定证书策略。不要把同一 CA 安装到日常浏览器、系统全局和手机上作为默认排错。

“工具中出现范围外请求”先停，核查重定向、第三方静态资源和浏览器后台行为。Target scope 是筛选与工具范围配置的重要输入，不是操作系统级网络隔离；实验室网络边界仍要由 [[计算机知识/Kali/01-系统与网络基础/09-状态防火墙与网络命名空间|防火墙与命名空间]] 独立确认。

## 报告与清理

项目、请求历史和导出文件可能包含完整会话与敏感响应。保留私密原始证据与公开脱敏版本，并记录你删除了哪些字段。截图应保留请求条件、关键响应和时间线，而不是只截一个红色告警标题。

退出后确认代理端口已关闭，专用浏览器不再使用该代理。下一步把相同假设在 [[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|命令行客户端]] 中重现，能够减少“只有 GUI 才看见”的不可复核步骤。

## 自检

设置了 Target Scope 后，为什么仍需防止浏览器访问外部网址？范围通常影响工具过滤/自动化行为，不是对所有网络行为的绝对沙盒。实际限制要通过专用浏览器、网络隔离与显式目标共同实现。

## 来源与核验范围

[^v5-burp-tools]: [PortSwigger：Burp Suite tools](https://portswigger.net/burp/documentation/desktop/tools)；定位：Proxy / Repeater / Intruder / Logger / Inspector / Decoder / Comparer。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-intruder-types]: [PortSwigger — Burp Intruder attack types](https://portswigger.net/burp/documentation/desktop/tools/intruder/configure-attack/attack-types)；定位：Sniper、Battering ram、Pitchfork、Cluster bomb 的组合规则。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-sequencer-results]: [PortSwigger — Burp Sequencer analysis results](https://portswigger.net/burp/documentation/desktop/tools/sequencer/results)；定位：Reliability、Effective entropy 与样本条件。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [PortSwigger：Burp 入门](https://portswigger.net/burp/documentation/desktop/getting-started)；定位：浏览器、代理、手工测试工作流。网页读取：2026-09-05。
[^s2]: [Kali 官方：burpsuite](https://www.kali.org/tools/burpsuite/)；定位：工具定位与包说明。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-burprepeater]: [PortSwigger：Burp Repeater](https://portswigger.net/burp/documentation/desktop/tools/repeater)；定位：重发请求、历史与响应比较。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-repeater]: [PortSwigger：Repeater HTTP messages](https://portswigger.net/burp/documentation/desktop/tools/repeater/http-messages)；定位：目标配置；修改和重发 HTTP；请求与响应历史。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]