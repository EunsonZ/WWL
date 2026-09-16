---
domain: "计算机知识"
type: "course"
stage: 4
prerequisites:
  - "[[计算机知识/Kali/04-服务身份与主机评估/03-LDAPKerberos与AD基础|LDAPKerberos与AD基础]]"
  - "[[计算机知识/Kali/00-导航与方法/04-从观察到结论的安全方法|从观察到结论的安全方法]]"
sources:
  - "https://learn.microsoft.com/en-us/sysinternals/downloads/procmon"
  - "https://learn.microsoft.com/en-us/sysinternals/downloads/process-explorer"
  - "https://learn.microsoft.com/en-us/sysinternals/downloads/accesschk"
  - "https://learn.microsoft.com/en-us/windows/win32/secauthz/order-of-aces-in-a-dacl"
  - "https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object"
  - "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/whoami"
  - "https://learn.microsoft.com/en-us/sysinternals/downloads/autoruns"
  - "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-acl?view=powershell-7.5"
content_status: "usable"
evidence_status: "partial"
---

# Windows权限边界与本机审计

**先修关系：** [[计算机知识/Kali/04-服务身份与主机评估/03-LDAPKerberos与AD基础|LDAPKerberos与AD基础]]；[[计算机知识/Kali/00-导航与方法/04-从观察到结论的安全方法|从观察到结论的安全方法]]。

## 为什么 Kali 课程仍需理解 Windows 本机证据

外部扫描只能看见部分服务行为，补丁、账户令牌、服务 ACL 与计划任务需要本机授权证据补充。本章使用 Windows 自带工具与微软 Sysinternals 的只读工作流，不声称这些 PowerShell 命令应在 Kali Bash 中运行。

## 令牌与权限不等于一个用户名

```powershell
# 在你拥有且已授权的 Windows 实验机上执行
whoami /all
Get-Service | Select-Object Name, Status, StartType
Get-Process | Select-Object Id, ProcessName
```

`whoami /all` 显示当前安全上下文的用户、组与特权等。[^s1] 用户属于 Administrators、当前进程令牌具有哪些权利、UAC 提升状态与资源 ACL 是不同层次，不能仅凭组名推断当前进程可执行所有管理操作。

不在报告里公开真实 SID、账户清单和敏感进程参数。进程存在仅是当时快照，不等于它在整个调查时间窗中持续运行。

## DACL 与令牌共同参与访问检查

安全描述符中的 DACL 由访问控制项（ACE）组成，线程/进程令牌提供用户、组等安全上下文。访问检查处理具体请求权利，并考虑 ACE 顺序及继承等因素。因此不能把所有 ACL 压成一个“拒绝永远覆盖允许”的无条件口诀。空 DACL 与没有 DACL 的含义也不同，审阅和脚本解析时尤其不能混淆。[^v2-winaccesscheck]

对某教学文件，先写要检查的是读、写、删除还是修改权限，再核对当前有效令牌和相关 ACE。成为 Administrators 成员不保证当前未提升进程具有全部管理能力；拥有对象、具备某特权和具备某一访问权也不是同一件事。

## 用请求权利集合逐步读DACL

以下为原创简化模型，只讨论普通 allow/deny ACE、已经匹配的主体、明确请求的权利，不包含对象专用 ACE、条件 ACE、特殊特权及其他完整访问检查因素。设请求权利集合是 $Q=\{读,写\}$，第一条相关 allow 提供读，仍缺写；第二条相关 allow 提供写，两者共同覆盖全部请求，则该简化检查可通过并停止遍历，不再读取后续 ACE。如果遇到适用的拒绝项阻断所请求权利，就会拒绝；遍历结束仍未获得全部权利也会拒绝。实际顺序与令牌状态必须按 Windows 规则判断。[^v5-accesscheck]

这解释了为什么不能把“只读允许”解释成允许打开一个同时申请读写的句柄。只申请读可能成功，同时申请读写可能失败；失败不证明该账户连读权限也没有。工具应报告请求的具体访问掩码，而不只是“打开失败”。

ACE 顺序还关系到显式与继承条目的处理。系统有推荐的规范顺序，任意重排不是不改变语义的格式美化。空 DACL 与不存在 DACL 的意义相反，也不能在导出时都序列化成同一个“空”值。[^v5-ace-order][^v5-accesscheck]

## ACL、服务与计划任务

先针对一个已批准的教学目录使用 `Get-Acl` 或 `icacls` 读取权限，再结合父目录继承与实际对象所有者解释。不要执行重置 ACL 的命令来消除不理解的拒绝，也不要关闭 UAC 作为常规排错手段。

服务与任务的风险取决于执行账户、二进制与参数、文件/目录权限和触发条件。只读配置审阅已经能提出许多具体问题，无需启动远程命令或修改系统执行链。

```powershell
# 路径需换成你专门创建的教学目录；只读取 ACL
Get-Acl 'C:\KaliLab\Demo' | Format-List
Get-ScheduledTask | Select-Object TaskPath, TaskName, State
```

这些 cmdlet 的可用性依 Windows/PowerShell 版本与权限；未运行时不填写成功结果。本章未对不同 Windows 版本做兼容性测试。

## 服务二进制路径之外还要看什么

将服务配置分为执行账户、可执行文件路径、参数、工作目录、依赖/插件和文件夹权限；分别确认低权限账户可以改变哪些输入。路径带空格本身不是完整漏洞结论，必须结合引号解析、目录写权限和实际启动语义。

Process Monitor 的价值是观察程序实际打开了哪些文件/注册表项，但过滤后没显示某项可能是过滤条件遗漏。保存捕获窗口、过滤规则、丢失事件信息和原始记录位置，不把当前可见列表当成完整历史。

## Sysinternals 的互补观察

Process Explorer 帮助检查进程层次、句柄与模块，Process Monitor 记录文件/注册表等操作，Autoruns 检查多种自动启动位置。Autoruns 的官方文档还说明签名验证与过滤等能力。[^s2]

检测工具产生的数据可非常庞大，应先按特定进程与时间窗口过滤，保留过滤规则和原始证据位置。发现未签名文件只是线索；合法内部软件也可能未签名，签名存在也不自动保证行为安全。

工具与公共恶意样本查询服务的集成功能可能上传文件或哈希；上传前确认数据政策，不把“方便查一下”当成默认授权。

## 三个Sysinternals工具如何形成互补证据

AccessChk 用于检查账户对文件、注册表、服务等对象的访问，并可查看较完整的安全信息；Process Explorer 侧重进程、句柄和已加载模块的关联；Process Monitor 记录文件系统、注册表、进程和线程活动。[^v5-accesschk][^v5-procexp][^v5-procmon]

原创诊断链：服务启动失败，先确认运行身份及服务配置，再核对目标对象上的相应权限，最后观察实际失败的是哪次路径访问或注册表操作。不能把 AccessChk 对某文件的结论当成服务一定会打开该文件，也不能把 Process Monitor 观察到一次拒绝当成所有失败的共同根因。

当前进程令牌、正在模拟的线程身份与账户目录中的成员关系也应区分。用户相同不保证有效令牌相同；账户后来被移出某组，不足以单独描述一个既有进程此刻使用的令牌内容。最终判断以相关操作的实际上下文为准。本轮未在 Windows 运行这些工具。

## 对日志事件作时间与身份关联

对本机实验，用事件发生时间、记录编号、提供程序、进程/登录相关标识建立关联；同一个数字 ID 在不同日志提供程序下可能具有不同意义。成功登录、获得新令牌和某资源操作应分别核对，不从单一事件推出完整行为链。

连接到 [[计算机知识/Kali/06-取证逆向与检测/01-取证流程镜像与时间线|时间线方法]]：跨系统记录先处理时区、时钟偏差与采集延迟，再讨论先后因果。此处 PowerShell 与 Sysinternals 仅为 Windows 参考流程，本次未在 Windows 上执行。

## 日志与修复复测

使用 Event Viewer 或 `Get-WinEvent` 查询明确时间段和提供程序，避免全量导出含个人信息的日志。登录失败、服务启动失败和安全软件阻止记录需要结合上下文，事件 ID 本身不是完整事件解释。

修复后比对 ACL、任务/服务配置和正常用户行为。网络端复测再用 [[计算机知识/Kali/04-服务身份与主机评估/01-SSHFTPSMTP与SNMP服务|协议客户端]] 与 [[计算机知识/Kali/04-服务身份与主机评估/02-SMBNFS与目录共享|共享权限流程]]，把外部观察与本机证据对应起来。

## 自检

某服务二进制签名有效，但所在目录可被低权限用户替换文件，签名是否消除了风险？没有，签名只对被验证的内容提供相关证据；权限链和程序实际加载了哪个文件仍需检查。

## 来源与核验范围

[^v5-accesscheck]: [Microsoft — How AccessCheck Works](https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object)；定位：DACL、令牌和顺序访问检查。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-ace-order]: [Microsoft — Order of ACEs in a DACL](https://learn.microsoft.com/en-us/windows/win32/secauthz/order-of-aces-in-a-dacl)；定位：显式与继承ACE的优先顺序。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-accesschk]: [Microsoft Sysinternals — AccessChk](https://learn.microsoft.com/en-us/sysinternals/downloads/accesschk)；定位：对象访问、令牌与完整安全描述符显示。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-procexp]: [Microsoft Sysinternals — Process Explorer](https://learn.microsoft.com/en-us/sysinternals/downloads/process-explorer)；定位：进程、句柄与DLL观察。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-procmon]: [Microsoft Sysinternals — Process Monitor](https://learn.microsoft.com/en-us/sysinternals/downloads/procmon)；定位：文件系统、注册表、进程与线程活动。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Microsoft：whoami](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/whoami)；定位：/all /groups /priv。网页读取：2026-09-05。
[^s2]: [Microsoft Sysinternals：Autoruns](https://learn.microsoft.com/en-us/sysinternals/downloads/autoruns)；定位：自动启动项检查与签名选项。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

补充核查：[Get-Acl参数与对象](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-acl?view=powershell-7.5)，定位：读取 ACL 与权限对象；网页读取 2026-09-05。这支持对应接口/机制，不替代本机运行验证。

[^v2-winaccesscheck]: [Microsoft：How AccessCheck Works](https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object)；定位：Token / ACE ordering / null and empty DACL。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]