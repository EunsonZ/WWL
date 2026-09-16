---
domain: "计算机知识"
type: "lab"
stage: 3
prerequisites:
  - "[[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|离线实验准备与夹具说明]]"
  - "[[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|认证会话越权与API测试]]"
  - "[[计算机知识/Kali/03-Web与API安全/06-SQL注入原理与sqlmap限界验证|SQL注入原理与sqlmap限界验证]]"
  - "[[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curlHTTPie与接口重放]]"
sources:
  - "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html"
  - "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
content_status: "usable"
evidence_status: "partial"
---

# 实验CWeb请求与访问控制

**先修关系：** [[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|离线实验准备与夹具说明]]；[[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|认证会话越权与API测试]]；[[计算机知识/Kali/03-Web与API安全/06-SQL注入原理与sqlmap限界验证|SQL注入原理与sqlmap限界验证]]；[[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curlHTTPie与接口重放]]。

## 一个场景，三个不同的信任边界

Alice 拥有报告17，Bob 拥有报告18。我们分别研究请求表示、对象授权和 SQL 查询；**它们不是同一个 HTTP 应用**：请求表示使用可选静态服务，对象授权与 SQL 只在离线 Python 中演示。这种拆开方式便于隔离机制，但不能代替完整应用安全测试。[^s1][^s2]

## 先理解你发送的内容

按 [[计算机知识/Kali/07-综合实验/02-实验A从路由到HTTP与Nmap|实验 A]] 手动启动回环静态服务后，用 curl 请求 `/api/status.json`，再用 Burp Repeater 或 ZAP 代理重放相同 GET。记录 Host、路径、方法、状态码和响应体。停服务后清理代理设置，避免影响日常浏览器。抓到一个响应不意味着登录成功，因为此服务根本没有登录。

## 对象授权：改变对象，不改变身份

在 `$HOME/kali-lab/code` 中：

```bash
python3 - <<'PYCODE'
from offline_lab import can_read
for user, report in [('alice',17), ('bob',17), ('bob',18), ('mallory',17)]:
    print(user, report, can_read(user, report))
PYCODE
```

预期依次是 True、False、True、False。第二个调用是关键反例：对象存在，不代表请求者获准访问。第四个调用默认拒绝未知主体。函数对身份来源作了**已知身份的教学假设**，它本身不会验证口令、Cookie 或 JWT；真实服务必须从可信会话取得身份，而不能信任客户端传来的用户名。[^s1]

代码还拒绝字符串对象编号和 bool，避免 Python 中 `True` 属于整数子类造成意外通路。这个输入契约只针对玩具函数，不代表真实 HTTP 层不能解析数字字符串；真实解析应该在边界处明确完成并单独测试。

## SQL：改变数据是否能改变语法

```bash
python3 - <<'PYCODE'
from offline_lab import query_names, INJECTION
print('普通绑定：', query_names('alice'))
print('危险拼接：', query_names(INJECTION, parameterized=False))
print('参数绑定：', query_names(INJECTION))
PYCODE
```

预期普通绑定只返回 Alice，危险拼接返回 Alice 与 Bob，参数绑定返回空列表。SQL 演示输入是公开教学文本 `' OR '1'='1` 所表达的引号/条件组合；实际字符串也保存在源码 `INJECTION` 常量中。为何有差异，应回到 [[计算机知识/Kali/03-Web与API安全/06-SQL注入原理与sqlmap限界验证|语法与数据分离]] 逐步解释，而不是背诵一个字符串。[^s2]

本实验不读取系统文件、不联机、不导出真实数据库。故意错误的拼接分支标注为教学反例，不得提取到应用项目中。输入导致 SQL 语法错误时，代码抛异常；空结果与运行失败是不同结果。

## 迁移检验

解释：参数化查询是否自动阻止 Bob 读取 Alice 的记录？不能。它保护 SQL 语法边界，不自动加入对象授权条件。两类测试都通过才能支持各自较窄结论，仍不代表完整应用安全。将两项发现分别记录，并建立 [[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|身份]] 与 [[计算机知识/Kali/03-Web与API安全/06-SQL注入原理与sqlmap限界验证|注入]] 的交叉链接。

## v2 深化路径

完成本页 owner-only 的 v1 模型后，进入 [[计算机知识/Kali/07-综合实验/12-实验I多租户字段与动作授权|实验 I]]。I 使用独立 v2 身份与对象表，加入租户、动作、状态、字段投影；相同编号不表示两版的同一对象历史。

## 来源与核验范围

[^s1]: [OWASP：Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)；定位：Deny by Default / Validate Permissions on Every Request。网页读取：2026-09-05。
[^s2]: [OWASP：SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)；定位：Prepared Statements / Allow-list Validation。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]