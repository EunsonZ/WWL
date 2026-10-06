---
domain: "计算机知识"
type: "course"
stage: 4
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/05-进程服务日志与本机加固|进程服务日志与本机加固]]"
  - "[[计算机知识/Kali/01-系统与网络基础/04-Shell文件权限与文本处理|Shell文件权限与文本处理]]"
  - "[[计算机知识/Kali/00-导航与方法/04-从观察到结论的安全方法|从观察到结论的安全方法]]"
sources:
  - "https://man7.org/linux/man-pages/man5/acl.5.html"
  - "https://man7.org/linux/man-pages/man7/user_namespaces.7.html"
  - "https://manpages.debian.org/testing/acl/acl.5.en.html"
  - "https://man7.org/linux/man-pages/man7/capabilities.7.html"
  - "https://www.kali.org/tools/lynis/"
  - "https://manpages.debian.org/testing/coreutils/chmod.1.en.html"
  - "https://manpages.debian.org/testing/systemd/systemctl.1.en.html"
content_status: "usable"
evidence_status: "partial"
---

# Linux权限边界与配置审计

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/05-进程服务日志与本机加固|进程服务日志与本机加固]]；[[计算机知识/Kali/01-系统与网络基础/04-Shell文件权限与文本处理|Shell文件权限与文本处理]]；[[计算机知识/Kali/00-导航与方法/04-从观察到结论的安全方法|从观察到结论的安全方法]]。

## 本机审计围绕“谁能改变谁的执行条件”

Linux 权限审计不等于查一份提权命令表。核心是识别低权限主体是否能修改高权限进程会读取、执行或信任的对象，以及这些修改是否越过了预期权限边界。

先记录身份、组、服务、计划任务、文件权限、挂载与 capabilities，再提出假设。正常管理员配置也可能具有高权限能力，是否构成风险取决于分配对象和业务需求。

## 多层访问判断不能压成一个rwx字符串

| 观察工具或对象 | 主要说明什么 | 还不能排除什么 |
| --- | --- | --- |
| `id`、进程状态 | 当前身份、组或进程上下文 | 不同进程或服务使用另一身份 |
| `ls`、`stat`、`getfacl` | 文件模式、拥有者与 ACL | 上级目录、挂载和其他访问控制层 |
| `getcap`、进程能力信息 | 文件或进程的能力属性 | 能力集合转换与命名空间范围 |
| 路径各级目录、挂载信息 | 路径解析和文件系统约束 | 应用内部策略及安全模块决定 |
| 服务配置与实际打开记录 | 程序声明和运行时实际依赖 | 未触发分支和其他时刻的行为 |

既有 ACL 例子中，Bob 的命名用户项受 mask 约束，不能退回 other 获取额外权限。默认 ACL 是新对象创建时的输入，不是对全部后代不断施加的实时规则。[^v5-acl] 推理时先固定具体主体与操作，再逐层检查，不用“权限不够”遮掉不同阻断位置。

与 [[计算机知识/Kali/05-密码无线与专门领域/06-容器Kubernetes与IaC审计|容器隔离和控制面授权]] 比较时，保持这个层次：文件自主访问、进程特权、命名空间和集群 API 权限描述不同对象。

## ACL 的有效权限不是把所有允许项相加

ACL 是对象上的细粒度访问控制表。下面仅是**原创合成的 ACL 文本**，不是修改命令；假设文件拥有者是 Alice，Bob 不是拥有者，并且没有绕过普通自主访问控制的特权：

```text
user::rw-
user:bob:rw-
group::r--
mask::r--
other::rw-
```

Bob 匹配命名用户项，名义权限是 rw-，还需受 mask 的 r-- 限制，所以普通检查只允许读、不允许写。`other::rw-` 不会在这一匹配失败后成为补发写权限的后备通道。拥有者、命名用户、匹配组和 other 的选择有顺序，不能把所有行的权限无条件求并集。[^v3-acl]

mask 约束命名用户和组类条目，而非文件拥有者与 other。存在扩展 ACL mask 时，`ls -l` 的组权限位置对应 mask，不一定就是 `group::` 那一行的完整含义。只看一个 rwx 字符串可能误判有效权限；应结合 `getfacl` 输出中条目与 effective 注释，且不能忽略命令失败。

### 文件权限以外还可能在哪一层被拒绝

读取叶文件前，路径各级目录需要相应的搜索权限；实际写入还可能被只读挂载、强制访问控制或应用自身策略拒绝。这些层不是 ACL 的同义词，改变 ACL 不能自动修复另外的阻断。诊断时保持操作与主体固定，依次观察路径、对象、挂载与安全模块，不直接 `chmod -R 777` 扩大范围。

目录默认 ACL 影响新对象创建时的初始访问 ACL，不会把已存在子文件一律追溯改成新策略。创建调用给出的 mode 也参与初始权限形成。因此“父目录默认 ACL 看起来正确”不能替代核对实际生成文件。[^v3-acl]

本轮是基于手册的纸面推演，未在此容器创建系统用户或修改 ACL。把它迁移到 [[计算机知识/Kali/04-服务身份与主机评估/02-SMBNFS与目录共享|共享目录]] 时还需另加协议账户映射和服务侧规则，不能用本机 Bob 的有效权限代替远端 SMB 会话权限。

## capabilities 不是“比较小的 root”这么简单

Linux 将若干特权拆成能力位，并在进程/线程凭据、可执行文件与命名空间等机制中管理。有效、允许、继承、边界和 ambient 集合承担不同职责。只读 `getcap` 文件输出看到的是文件能力信息，不能直接替代运行中进程的实际能力。[^v2-capabilities]

`CAP_NET_RAW` 与原始套接字相关，`CAP_DAC_OVERRIDE` 与绕过部分自主访问控制相关，它们解决的权限条件不同。某位存在不自动证明可利用；要结合程序接受何输入、能力生效范围、命名空间、其他安全机制和实际操作判断。

## 能力集合为什么要分成多个集合

Linux capabilities 将传统特权拆成多个能力位，并为线程维护 permitted、effective、inheritable、bounding、ambient 等不同集合。它们分别参与当前可用能力、能力保有和执行新程序时的转换，不能把任意一行包含某能力名称都解释为“当前操作必然具备它”。文件能力还会参与 exec 规则。[^v5-capabilities]

直观上，effective 回答当前检查使用哪些能力，permitted 不是当前每一位都正在生效；bounding 约束某些获得能力的途径，不是对线程全部行为的万能总开关；inheritable 与 ambient 也不能仅凭名称理解成无条件跨程序继承。真正判断要组合当前集合、文件属性、执行方式和其他限制。这里保留概念层，完整转换公式应按对应内核手册逐项核对。

用户命名空间又给能力附加作用范围：在某个命名空间中拥有能力，不等于对初始命名空间的所有资源拥有相同权力。UID 0 是身份数值，还要看它在哪个命名空间及如何映射。[^v5-userns] 因此“容器里是 root，所以一定控制宿主机”和“用了命名空间，所以绝对安全”都是跳步。

## 只读基线

```bash
id
sudo -l
ss -lntup
systemctl list-timers --all --no-pager
findmnt
```

这些命令只用于你自己的系统或明确授权主机；输出可能包含组织敏感信息。`sudo -l` 显示授权规则，不等于执行了其中的命令，也不表明规则一定可被滥用。

限制文件搜索范围比扫描全盘更容易审阅：

```bash
# 仅检查已批准的本机软件目录，-xdev 不跨挂载点
find /usr/bin -xdev -type f -perm -4000 -print
getcap -r /usr/bin
```

SUID 位、capabilities 和服务账户分别是权限机制。发现某个 SUID 程序并不直接证明漏洞；必须核对其用途、来源、权限模型与安全实现。不要执行网上的利用片段来“试试看”。

## 目录与依赖链

即使可执行文件不可写，启动脚本、配置、插件目录、环境变量、相对路径和依赖搜索路径也可能影响程序行为。评估应画出实际加载链，再核对每个环节由谁可写。文件权限与目录可写性必须分别看。

计划任务与 systemd unit 的安全性涉及执行身份、WorkingDirectory、Environment、文件所有权与目标脚本。仅看任务名称不能证明没有风险。修改前保存配置与授权，后续先 `systemd-analyze verify` 等适合本机版本的检查，再在可恢复环境验证。

## 用一条服务加载链推演权限风险

设服务以专用高权限账户执行 `/opt/lab/run`，文件本身只允许管理员写。继续检查父目录、被加载配置、插件目录和启动环境：若低权限用户能替换某个实际被加载的输入，就可能影响高权限执行。这里是配置审阅假说，仍需确认程序是否真的加载该路径和如何解释内容。

只检查最终二进制会漏掉目录替换和依赖搜索路径；只检查目录可写又可能忽略程序采用固定句柄或拒绝不可信配置的防护。需要文件系统证据与运行时加载证据交叉，而不是任一单条件直接定罪。

## Lynis 与辅助枚举脚本

Lynis 通过审计检查生成建议和日志；分数或提示不能直接当作符合所有标准的证明。[^s1]

```bash
lynis --help
# 可选：你明确授权的本机审计，可能生成日志和读取配置
# sudo lynis audit system
```

LinPEAS 等枚举脚本会收集大量主机信息，其版本与行为必须逐项审阅；不默认运行下载来的脚本，更不把 `curl ... | sh` 当成安装习惯。本包只解释其定位，不附自动提权或秘密搜索工作流。

`chkrootkit`、`rkhunter` 等检测工具可提供线索，但签名/启发式告警不是入侵定论，未报警也不能证明系统未被入侵。需要日志、文件基线与独立取证交叉确认。

## 审计命令的失败必须进入记录

`getcap` 无输出可以是确实没发现文件能力，也可能因为搜索范围、权限或工具失败。保留标准错误和退出码；本轮已移除原例子中丢弃标准错误的重定向。`sudo -l` 可能触发认证和审计记录，不能把“只列规则”误写成没有任何系统活动。

扫描范围用获批目录而非整盘；权限修复用针对性的所有者/模式/ACL 变更，不以 `chmod -R 777` 或全局禁用强制访问控制解决困难。Lynis 分数变化只作为特定检查集的反馈，验收仍由明确安全合同与业务正常性决定。

## 修复与负面影响

最小权限、明确绝对路径、限制可写目录、分离账户、及时修补与审计是常见方向。不能通过删掉所有服务或更改全盘权限来“修好分数”；需保护业务合同并留下回滚点。

自检：某服务以 root 运行但从不接收外部输入，是否一定安全？不一定，输入可来自文件、IPC、依赖和本地低权限用户；同时高权限本身也不自动等于可利用漏洞。需要沿实际信任链分析。

## 来源与核验范围

[^v5-capabilities]: [Linux capabilities(7)](https://man7.org/linux/man-pages/man7/capabilities.7.html)；定位：线程能力集合、文件能力及 exec 转换。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-userns]: [Linux user_namespaces(7)](https://man7.org/linux/man-pages/man7/user_namespaces.7.html)；定位：用户ID映射、能力与命名空间范围。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-acl]: [Linux acl(5)](https://man7.org/linux/man-pages/man5/acl.5.html)；定位：ACCESS CHECK ALGORITHM、ACL_MASK、默认ACL。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Kali 官方：lynis](https://www.kali.org/tools/lynis/)；定位：audit system / 报告与日志。网页读取：2026-09-05。
[^s2]: [GNU chmod 手册（Debian 分发）](https://manpages.debian.org/testing/coreutils/chmod.1.en.html)；定位：符号模式与八进制模式。网页读取：2026-09-05。
[^s3]: [systemd systemctl 手册（Debian 分发）](https://manpages.debian.org/testing/systemd/systemctl.1.en.html)；定位：status / start / enable / is-active。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-capabilities]: [Linux capabilities(7)](https://man7.org/linux/man-pages/man7/capabilities.7.html)；定位：Capability sets / CAP_NET_RAW / CAP_DAC_OVERRIDE / namespaces。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-acl]: [Linux ACL 手册（Debian acl 项目分发）](https://manpages.debian.org/testing/acl/acl.5.en.html)；定位：ACL_MASK；ACCESS CHECK ALGORITHM；OBJECT CREATION；mode bits。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]