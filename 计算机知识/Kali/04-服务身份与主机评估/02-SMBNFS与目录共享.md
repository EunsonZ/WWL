---
domain: "计算机知识"
type: "course"
stage: 4
prerequisites:
  - "[[计算机知识/Kali/04-服务身份与主机评估/01-SSHFTPSMTP与SNMP服务|SSHFTPSMTP与SNMP服务]]"
  - "[[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|认证会话越权与API测试]]"
sources:
  - "https://manpages.debian.org/testing/nfs-kernel-server/exports.5.en.html"
  - "https://www.samba.org/samba/docs/current/man-html/smbclient.1.html"
  - "https://www.kali.org/tools/enum4linux-ng/"
  - "https://www.kali.org/tools/smbmap/"
  - "https://manpages.debian.org/testing/nfs-common/showmount.8.en.html"
content_status: "usable"
evidence_status: "partial"
---

# SMBNFS与目录共享

**先修关系：** [[计算机知识/Kali/04-服务身份与主机评估/01-SSHFTPSMTP与SNMP服务|SSHFTPSMTP与SNMP服务]]；[[计算机知识/Kali/03-Web与API安全/08-认证会话越权与API测试|认证会话越权与API测试]]。

## 共享名、会话权限与文件权限

SMB 为共享文件、命名管道等提供协议能力，NFS 提供另一种网络文件系统模型。能枚举共享名不意味着能读其中内容；能读某文件不意味着能写；某层允许也可能被文件系统 ACL 拒绝。

评估应使用专用测试账户与无敏感内容的标记文件，分别验证允许和拒绝情形。不要为了确认读权限下载整个共享，也不要默认做写入探测。

## smbclient：使用明确身份的只读操作

Samba 的 smbclient 可以列共享与进入特定共享，`-U` 指定用户时可交互输入密码。[^s1]

```bash
smbclient --help
# 扩展模板：127.0.0.1 上的 445 必须是你自建的教学 SMB
# smbclient -L //127.0.0.1 -U labreader
# smbclient //127.0.0.1/public-demo -U labreader -c 'ls'
```

`ls` 获取目录列表，也可能包含敏感文件名，仍需最小化保存。客户端协商 SMB 方言、服务器要求的签名/加密和账户策略会影响结果。不要为了“兼容”盲目启用 SMB1 或放宽客户端安全配置。

共享权限与 NTFS/底层文件系统权限共同决定结果。把某个列举结果中的 `READ` 当成对所有子目录的永久保证，是忽略 ACL 继承和逐对象差异。

## enum4linux-ng、SMBMap 与 RPC

enum4linux-ng 组织多种 SMB/RPC 查询并支持结构化输出；它不是单一的无副作用查询。[^s2] 执行前逐项审阅所启用的枚举内容，避免整套默认收集把不需要的用户、组、策略和共享都导出。

SMBMap 提供共享权限与内容相关能力，其中部分选项会涉及写入检查、下载或更强操作；先看 `smbmap --help`，不能把工具名字理解成“只画一张图”。[^s3] `rpcclient` 可进行 RPC 查询，当前账户能查到什么取决于服务端策略，不应把查询失败直接说成“没有用户/组”。

本课程把这些工具放在已授权配置核对层；涉及写权限时，由负责人准备一份可删除的教学标记文件并批准具体目录，不以覆盖现有文件验证。

## NFS：导出配置不是完整访问图

`showmount -e` 查询某些服务的导出信息，但 NFSv4-only 服务器可能不暴露相同的 MNT 服务，因此没有输出不能证明没有 NFS。[^s4]

```bash
# 扩展模板：仅对自建 NFS 实验机使用
# showmount -e 192.168.56.20
```

挂载会改变本机状态，还可能触发服务器访问与本地解析风险。本页不默认挂载未知共享；需要时限定只读、最小选项与隔离环境，并记录实际协商版本。UID/GID 映射、root squashing、身份机制和底层权限都可能影响结果。

## 数据最小化与复测

记录你使用哪个测试账户、访问哪个共享/文件、做什么操作以及预期。修复权限后应让原被拒用户重试，也让正常用户验证正常功能，防止通过“全部禁用共享”掩盖业务回归。

不要在报告里公开整个共享树、用户名列表或服务器机密路径。共享文件名本身也可能是敏感信息。

## 自检

匿名只能列出共享名，但下载测试文件失败，能否报告“匿名可读取所有文件”？不能。可以报告观察到的名称枚举，并单独说明内容读取未成功。结论必须匹配操作层级。

## 有效权限是多层条件的合成

使用同一个教学账户，依次区分：共享是否可见、能否连接该共享、能否列目录、能否读取指定文件。每一步需要上一层条件但不保证下一层成功。对另一个目录得到不同结果，可能来自继承、显式 ACL、服务端映射或底层权限，不应覆盖成一个“整机 READ”标签。[^v2-smbclient]

签名保护消息完整性与来源相关属性，加密保护内容机密性，身份认证建立主体，文件 ACL 判定操作。它们不是同义开关。协议方言相同也不说明这几项配置完全相同；报告必须记录实际协商和已验证的操作层。

## NFS 身份映射为什么容易造成误解

传统 AUTH_SYS 场景使用客户端提供的 UID/GID 等身份信息，服务端如何信任客户端与映射用户是重要前提。`root_squash` 通常把客户端 root 映射为匿名身份，但不意味着所有普通用户都被安全认证，也不意味着已经加密。`sec=` 等机制与导出权限是另一个维度。[^v2-nfsexports]

只读导出限制的是相应服务端文件写操作；客户端命令中声称只读，也需要核对实际挂载参数和服务端策略。导出到一个网段的含义是网络范围限制，不是逐个人身份授权。UID 名字在两台机器显示相同，仍应核对映射而非只看标签。

## 一组最小权限复测

准备 `public-demo/notice.txt` 和 `private-demo/notice.txt` 两份无敏感标记，负责人明确 labreader 应只读前者。记录列目录与读文件两类结果，再由被允许账户证明后者确实存在且可正常读。跨账户使用独立会话，不复用含上一次身份的客户端状态。

若需要验证写权限，另立一次带回滚的变更测试，不把创建临时文件伪装成纯读取；删除成功也要核实是否只删除自己创建的那份。这里默认不执行写入、下载整目录或匿名账户尝试。

## 来源与核验范围

[^s1]: [Samba 官方：smbclient](https://www.samba.org/samba/docs/current/man-html/smbclient.1.html)；定位：-L / -U / -c / 客户端操作。网页读取：2026-09-05。
[^s2]: [Kali 官方：enum4linux-ng](https://www.kali.org/tools/enum4linux-ng/)；定位：枚举功能与输出选项。网页读取：2026-09-05。
[^s3]: [Kali 官方：smbmap](https://www.kali.org/tools/smbmap/)；定位：权限映射和读写相关选项；不能假定默认只读。网页读取：2026-09-05。
[^s4]: [NFS showmount（Debian 手册）](https://manpages.debian.org/testing/nfs-common/showmount.8.en.html)；定位：-e 与 NFSv4 的可见性边界。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-smbclient]: [Samba：smbclient](https://www.samba.org/samba/docs/current/man-html/smbclient.1.html)；定位：Client protection / authentication / interactive commands。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-nfsexports]: [NFS exports(5)](https://manpages.debian.org/testing/nfs-kernel-server/exports.5.en.html)；定位：root_squash / sec / ro / UID mapping。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]