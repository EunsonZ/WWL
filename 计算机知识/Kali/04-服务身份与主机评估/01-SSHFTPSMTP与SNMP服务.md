---
domain: "计算机知识"
type: "course"
stage: 4
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]"
  - "[[计算机知识/Kali/03-Web与API安全/10-TLS证书与服务配置评估|TLS证书与服务配置评估]]"
  - "[[计算机知识/Kali/00-导航与方法/02-授权范围与风险分级|授权范围与风险分级]]"
sources:
  - "https://man.openbsd.org/sshd_config"
  - "https://man.openbsd.org/ssh"
  - "https://www.kali.org/tools/swaks/"
  - "https://curl.se/docs/manpage.html"
  - "https://www.net-snmp.org/tutorial/tutorial-5/commands/snmpv3.html"
content_status: "usable"
evidence_status: "partial"
---

# SSHFTPSMTP与SNMP服务

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]；[[计算机知识/Kali/03-Web与API安全/10-TLS证书与服务配置评估|TLS证书与服务配置评估]]；[[计算机知识/Kali/00-导航与方法/02-授权范围与风险分级|授权范围与风险分级]]。

## 按协议语义读服务，而不是按端口背答案

SSH、FTP、SMTP 和 SNMP 各自维护不同的状态、认证与权限。Nmap 给出端口和服务候选后，下一步应使用对应客户端完成最小、只读且有授权的协议交流。网络可达不等于认证成功，认证成功不等于具有操作权限。

本页所有在线服务都属于另行搭建的扩展靶场；本包只附 HTTP 静态服务启动说明，不假定你的回环上已运行 SSH、邮件或 SNMP。

## SSH：主机身份先于用户认证

OpenSSH 的主机密钥帮助客户端识别服务器，用户认证验证访问者。两者失败需要不同处理。确认主机密钥指纹应通过独立可信渠道，而不是遇到变化就删除 known_hosts 条目。[^s1]

```bash
ssh -V
# 可选：labvm 是你已经核验主机密钥并配置的自建实验机别名
# ssh -v -o ConnectTimeout=5 labvm
```

`-v` 会显示协商与认证过程，日志可能包含账户名、路径和网络细节，分享前检查。先区分没有路由、连接被拒绝、主机密钥验证失败、认证失败和登录后的权限不足。不要用口令猜测去解决明显的路由问题。

SFTP 通过 SSH 提供文件传输；FTP 与 FTPS 是不同协议族。名字相近不代表使用相同端口、认证流程或加密边界。

## FTP / FTPS：控制与数据连接

FTP 的控制连接和数据传输连接分开，因此“能登录却不能列目录”可能是数据连接、防火墙或主动/被动模式问题。TLS 可用于保护 FTPS，但必须确认控制与数据通道的实际策略。仅听到 banner 不代表已经验证文件读取权限。

```bash
# 扩展模板：仅自建服务和专用测试账户；--user 只给用户名以交互方式输入密码
# curl --user labreader --list-only --max-time 5 ftp://127.0.0.1:2121/
```

这仍是认证活动并会产生日志。不要自动尝试匿名账户、写文件或遍历整个共享；授权明确允许后才能验证具体权限。生产数据用最小教学标记文件替代。

## SMTP：停在握手阶段

Swaks 适合逐阶段观察 SMTP；可以在 EHLO 后结束，避免真的发送邮件。[^s2]

```bash
swaks --help
# 扩展模板：2525 是你自己的教学 SMTP 服务
# swaks --server 127.0.0.1 --port 2525 --quit-after EHLO
```

EHLO 返回能力声明，不能独自证明邮件投递、认证或中继策略正确。开放中继验证可能使第三方收到邮件，应单独批准并仅使用自有测试地址；本包不提供对外投递流程。

STARTTLS 是协议中的升级步骤，不能因为能力列表出现该词就假定所有客户端都会强制使用或正确验证证书。TLS 分析见 [[计算机知识/Kali/03-Web与API安全/10-TLS证书与服务配置评估|证书与配置评估]]。

## SNMP：先理解对象与权限

SNMP 用对象标识符（OID）定位管理数据。GET 读取指定对象，WALK 通过一连串操作遍历子树；后者可能泄露更多拓扑或设备信息并产生大量请求。SNMPv1/v2c 的 community 不应当作安全的加密认证；需要保护管理平面，并按设备能力配置经过评估的 SNMPv3 安全策略。

`snmpget`、`snmpwalk`、`snmpbulkwalk` 应按已批准的单对象或子树使用。先查本机手册，显式设置超时、重试、版本与安全等级。不要把常见 community 字符串列表当成例行输入，也不要把认证口令写在命令行或分享笔记。

## 自检与迁移

SSH 连接成功但 SFTP 被拒绝，是否说明“认证绕过失败”？这不是准确表述；可能是子系统或账户权限配置不同，应分别描述连接、认证和授权层。

将每个服务的观察统一填写到 [[计算机知识/Kali/08-模板与速查/03-发现与复测模板|发现记录]]：协议、网络位置、身份、操作、最小响应与未验证内容。相同格式帮助跨工具比较，避免把所有失败压成“连接不上”。

## 把协议会话拆成状态机

一条连接通常经历解析名字、传输连接、协商能力、认证、授权操作、退出与清理。失败所在阶段决定下一步证据。SMTP 在 EHLO 后退出只验证能力交流，SSH 用户认证失败不能倒推主机密钥错误；FTP 登录成功也不证明数据通道成功。

为自建实验服务准备一张小表：预期身份、允许操作、拒绝操作、可能生成的日志、每次请求上限。选择无敏感内容的标记文件或单 OID，而不是先遍历再寻找可写进报告的东西。

## SSH 的三类密钥/凭据要分开

主机密钥识别服务器，用户公钥认证中的私钥证明用户持有相应秘密，连接中的会话密钥保护传输。用户私钥不应发送给服务器；服务器换主机密钥也不等于你的用户私钥必须改变。转发 agent 又是额外的信任委托，不因传输被 SSH 加密就自动安全。

服务端的有效策略可能由多个 `Match` 条件和配置片段共同决定。限制登录账户、认证方法、转发或子系统应按真实用途审阅，不能只 grep 一个主文件中的关键词。`ForceCommand` 与转发限制解决的能力范围也不同。[^v2-sshdconfig]

## FTPS 与 STARTTLS 的“是否强制”问题

能力声明支持 TLS、客户端请求升级、升级成功、服务器证书验证成功、后续敏感内容始终通过受保护通道，这是五个不同命题。若客户端允许失败后继续明文，会改变安全保证。FTP 数据通道与控制通道分开，观察其中一个不够代表另一个。

服务审阅应检查正常受保护连接可用、错误服务器身份被拒、禁止的明文认证不能继续。实际兼容性依双方实现，需要自有服务实测；本包没有预置这些在线服务，不填写推测的输出。

## SNMPv3 的三个安全等级并非三个版本

`noAuthNoPriv`、`authNoPriv`、`authPriv` 表达消息认证与隐私保护组合。SNMPv3 这个版本号本身不意味着启用了消息加密。还需要最小只读视图、用户权限和允许的管理网络；较旧官方教程中的算法示例不能当成当前算法推荐。[^v2-snmp]

给一个获批 OID 作 GET 与遍历整棵树的 WALK 有不同数据量和风险。超时可能来自 UDP 丢失、设备限流、错误安全参数或访问控制，不能自动解释为“不支持 SNMP”。重复请求之前先看服务端计数和预设预算。

## 来源与核验范围

[^s1]: [OpenSSH 官方：ssh(1)](https://man.openbsd.org/ssh)；定位：-L / -N / -D / host key checking。网页读取：2026-09-05。
[^s2]: [Kali 官方：swaks](https://www.kali.org/tools/swaks/)；定位：SMTP 阶段与 --quit-after。网页读取：2026-09-05。
[^s3]: [curl 官方命令手册](https://curl.se/docs/manpage.html)；定位：--connect-timeout / --max-time / --proxy / --resolve / --cacert。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

补充核查：[SNMPv3安全级别](https://www.net-snmp.org/tutorial/tutorial-5/commands/snmpv3.html)，定位：认证、隐私与安全级别；示例算法不可视为当前安全推荐；网页读取 2026-09-05。这支持对应接口/机制，不替代本机运行验证。

[^v2-sshdconfig]: [OpenSSH：sshd_config](https://man.openbsd.org/sshd_config)；定位：Match / AuthenticationMethods / AllowTcpForwarding / ForceCommand。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-snmp]: [Net-SNMP：SNMPv3](https://www.net-snmp.org/tutorial/tutorial-5/commands/snmpv3.html)；定位：noAuthNoPriv / authNoPriv / authPriv；不采纳旧示例算法作为推荐。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]