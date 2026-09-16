---
domain: "计算机知识"
type: "course"
stage: 3
aliases:
  - "SQL注入"
  - "SQLi"
prerequisites:
  - "[[计算机知识/Kali/03-Web与API安全/01-Web测试模型与手工基线|Web测试模型与手工基线]]"
  - "[[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curlHTTPie与接口重放]]"
  - "[[计算机知识/Kali/01-系统与网络基础/08-BashPython与可复核自动化|BashPython与可复核自动化]]"
sources:
  - "https://github.com/sqlmapproject/sqlmap/wiki/Techniques"
  - "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
  - "https://github.com/sqlmapproject/sqlmap/wiki/Usage"
  - "https://docs.python.org/3/library/sqlite3.html"
content_status: "usable"
evidence_status: "partial"
---

# SQL注入原理与sqlmap限界验证

**先修关系：** [[计算机知识/Kali/03-Web与API安全/01-Web测试模型与手工基线|Web测试模型与手工基线]]；[[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curlHTTPie与接口重放]]；[[计算机知识/Kali/01-系统与网络基础/08-BashPython与可复核自动化|BashPython与可复核自动化]]。

## 根因是数据变成了查询语法

SQL 注入发生在不可信输入跨越了数据库查询的语法边界。危险不在于某个引号字符“天生恶意”，而在于程序把输入拼进查询文本，让数据库把它当成结构执行。参数化查询把查询结构与值分开，是主要防护机制之一。[^s1]

假设只有两行教学记录：Alice 和 Bob。下面只演示查询构造形态，不连接真实数据库：

```python
# 错误形态：name 被拼入 SQL 结构
sql = "SELECT name FROM users WHERE name = '" + name + "'"
# 正确形态：SQLite 用占位符绑定值
rows = connection.execute(
    "SELECT name FROM users WHERE name = ?", (name,)
).fetchall()
```

输入 `Alice` 时两种写法可能表现相同；输入 `' OR '1'='1` 时，拼接形态可能改变 WHERE 逻辑，而参数化形态会把整段作为普通名字查询。这是 [[计算机知识/Kali/07-综合实验/04-实验CWeb请求与访问控制|附带离线实验]] 的主要反例，数据完全合成且不持久化。

## 用中间步骤解释“数据变成了语法”

附带内存 SQLite 的错误实现原本构造 `WHERE name = '输入值'`。输入 Alice 时，数据库比较名字是否等于 Alice。实验中的固定教学字符串 ` ' OR '1'='1 ` 去掉两端展示用空格后，会使最终条件包含 `name = '' OR '1'='1'`。对表中每一行，右侧比较都为真，OR 条件因此为真，结果不再限于一个名字。

参数化版本先固定 SQL 的语法结构，再将完整输入作为一个值绑定。引号与 OR 留在那个值内部，不再变成 SQL 运算。这个例子只查询两行合成人名，不连接实际业务数据库，也不证明其他数据库、编码或驱动具有完全相同行为。完整源码与实际预期见 [[计算机知识/Kali/07-综合实验/09-实验代码合同与复现|原实验代码合同]]。

## 不同观测方式及其代价

报错、布尔差异、时间差异和集合查询差异是不同的观测通道。服务器错误不独自证明注入；布尔差异可能来自输入验证或业务分支；时间差异可能来自负载、缓存或网络抖动。尤其不能仅凭一次慢响应推断可控延时。

先建立正常请求与预期输出，再在自建靶场中验证“改变查询语法”这一机制。验证目标应是最小必要证据，不需要读取整库、写文件、操作系统命令或持久化。

## 检测方式本质上是在构造不同的观测通道

sqlmap 的布尔、时间、错误信息和结果回显等方式，区别在于查询行为怎样影响外部可观察量；多语句能力则涉及数据库与驱动是否接受额外语句，不能与“返回内容可见”混为一谈。一个通道不可用，不代表其他通道一定不存在；但存在候选差异也不等于已证明查询语法被改变。[^v5-sqlmap-tech]

用一个不包含攻击载荷的原创模型理解：令 $Q$ 表示数据库相关条件，$C$ 表示缓存、会话、网络和服务器负载，观察结果为 $Y=g(Q,C)$。比较两个请求得到不同 $Y$，只有在 $C$ 的变化得到控制、并有机制证据支持时，才可将差异归因到 $Q$。时间更长也可能来自排队、重试和缓存未命中；响应变短可能只是登录过期。

因此，工具的比较器是一个分类器，而不是直接读取数据库内部真值的窗口。应检查稳定基线、正常正反对照、当前身份、重复观察与后端证据；不以一次延迟或一个错误词定案。这里深化的是判读原理，不新增提取数据、负载构造或绕过方法。

## sqlmap 如何进入工作流

sqlmap 自动构造与比较测试请求，很多选项会提高请求量或能力。`--level` 与 `--risk` 不是可信度百分比；即使最低设置也不代表没有副作用。[^s2]

先查帮助并明确参数位置：

```bash
sqlmap --version
sqlmap -hh
```

以下是**扩展练习模板**，只用于另行搭建、可恢复且你拥有的本机 SQL 注入靶场。**本包的 8000 静态服务没有数据库接口，不能用它完成 sqlmap 检测。**

```bash
# 可选；先确认 8081 确实是你自己的专用教学应用
# timeout --signal=INT 60s sqlmap \
#   -u 'http://127.0.0.1:8081/item?id=1' -p id \
#   --batch --level=1 --risk=1 --technique=B \
#   --threads=1 --delay=1 --timeout=5 --retries=0
```

`-p id` 限定被测参数，`--technique=B` 限定布尔型观察，线程、延迟与外层超时共同限制实验规模。中断可能留下日志或会话缓存；复测应区分复用旧结果与重新检测。禁止把这个模板换成第三方目标然后自动执行。

## sqlmap 的检测状态不能脱离当前会话

修复复测应使用新的、单独命名的输出目录，并记录目标版本、测试参数、会话和请求。工具可能复用保存的会话证据；`--flush-session` 会改变该目标的会话缓存，执行前必须保存原始证据，不能把清理当成无副作用动作。`--fresh-queries` 与完全重新进行全部检测也不是同义。[^v2-sqlmap]

时间差异可能来自排队、网络抖动、缓存未命中或应用限流；布尔响应差异也可能来自会话失效和动态页面。先验证基线稳定、设计交替对照、记录异常原因。这里只补充证据解释，不增加读取敏感数据、系统命令或高强度时间负载的步骤。

## 修复不是“过滤几个字符”

数据库驱动的绑定参数负责值；表名、列名等标识符通常不能按同样方式绑定，需要固定映射或白名单。ORM 也可能通过原始查询接口重新引入拼接。防护还包括最小数据库权限、关闭不需要的功能与合理错误处理。

转义的正确性依赖数据库、字符集、上下文与模式，不能把通用 `replace("'", "")` 当成安全数据库接口。藏起错误消息减少暴露，但不修复查询构造。

## 修复合同不能只写“换成 ORM”

绑定通常用于数据值，不能把任意表名、列名、排序方向都当值参数替代。需要动态列时由有限枚举映射到开发者定义的标识符。ORM 的原始 SQL 接口、动态存储过程和字符串拼接仍应审阅；存储过程这个名字本身不是安全性质。[^v2-sqli]

修复测试至少包含正常 Alice/Bob、没有匹配结果、含合法引号的人名、空值/类型错误政策以及已知教学反例。若通过拒绝所有带引号姓名来让测试“安全”，可能是在破坏输入合同而非正确隔离语法。参数化也不能取代对象授权和数据库最小权限。

## 参数化固定的是语法角色，不是自动完成所有业务约束

值参数与表名、列名、排序方向等语法元素属于不同角色；普通值绑定不能自动把任意输入变成安全标识符。无法绑定的语法选择，应由受控映射或查询重设计决定；ORM 或存储过程内部若重新拼接动态语句，仍需检查边界。[^v5-sql-params]

原创反例：某接口正确绑定了对象编号，因此没有把编号当成 SQL 语法；但查询没有包含当前租户限制，仍可能返回其他租户对象。这是授权缺陷，不是参数化失败。另一种情况是所有文本都作为值绑定，但业务要求的金额范围未验证，依然会出现业务错误。语法安全、对象授权、业务合法性和数据库最小权限是并列层次，不是一个“安全查询”开关。

将这四层接到 [[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|对象授权]] 与 [[计算机知识/Kali/04-服务身份与主机评估/09-数据库服务与最小权限审计|数据库角色和行级策略]]，才能解释为何“sqlmap 没报问题”不足以完成数据库安全评估。

## 将数据库权限纳入影响分析

同一种输入拼接错误，在只读教学账户与高权限业务账户下的潜在影响不同。应独立检查账户可访问的库、schema、表、函数和管理能力，再提出最小必要修复。进一步见 [[计算机知识/Kali/04-服务身份与主机评估/09-数据库服务与最小权限审计|数据库服务与权限]]。

## 验证与自检

修复后同时测试普通名字、带引号的合法名字、原反例与未知名字。不能为了挡住反例把所有带引号的正常输入拒绝，然后宣布参数化已实现。

自检：sqlmap 没发现问题，是否证明所有查询都参数化？不能；认证、参数位置、请求状态、覆盖和工具观测能力都有限。源码审阅、单元测试与限界黑盒实验应形成互补证据。

## 来源与核验范围

[^v5-sqlmap-tech]: [sqlmap：Techniques](https://github.com/sqlmapproject/sqlmap/wiki/Techniques)；定位：SQL 检测观测类别；仅引用本页讨论的既有机制，不据网页推断 Kali 打包版本。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-sql-params]: [OWASP：SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)；定位：Prepared Statements；Allow-list Input Validation。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [OWASP：SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)；定位：Prepared Statements / Allow-list Validation。网页读取：2026-09-05。
[^s2]: [sqlmap 上游 Usage Wiki](https://github.com/sqlmapproject/sqlmap/wiki/Usage)；定位：Target / Detection / Injection / General。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

补充核查：[Python参数绑定接口](https://docs.python.org/3/library/sqlite3.html)，定位：SQL placeholders / connect / optional module；网页读取 2026-09-05。这支持对应接口/机制，不替代本机运行验证。

[^v2-sqli]: [OWASP：SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)；定位：Prepared Statements / Allow-list / Least Privilege。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-sqlmap]: [sqlmap：Usage](https://github.com/sqlmapproject/sqlmap/wiki/Usage)；定位：Detection / Session / --output-dir / --flush-session。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]