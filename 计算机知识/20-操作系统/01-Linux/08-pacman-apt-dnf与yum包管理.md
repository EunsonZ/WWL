---
type: lesson
domain: computer-science
stage: 8
status: ready
difficulty: 入门
estimated_minutes: 45
topics:
  - linux
  - package-management
  - repository
  - dependency
  - signature
  - transaction
  - pacman
  - apt
  - dnf
  - rpm
tags:
  - computer-science/linux
  - computer-science/package-management
---

# pacman、apt、dnf 与 yum 包管理

> [!abstract] 本课目标
> 学完后，你能用“仓库 → 元数据 → 依赖求解 → 签名验证 → 事务”解释 Linux 发行版如何安装软件，并能在 Arch、Debian/Ubuntu 和传统 Fedora/RHEL 系统上选对工具、先查询再操作。

> [!info] 核对边界
> 本页命令和当前工具边界已按 ArchWiki、Arch `pacman` 手册、Debian/Ubuntu APT 文档、DNF 文档、Red Hat 文档与 RPM 手册核对至 2026-09-01。发行版会继续演进；实际操作时，以本机版本的手册和发行版文档为准。

## 1. 包管理器不只是“下载命令”

从仓库安装一个包，通常会经过这条链：

```text
已配置的 repository（仓库）
            ↓
下载并缓存 package metadata（包名、版本、架构、依赖、摘要等）
            ↓
依赖求解：计算要安装、升级、替换或删除的整组包
            ↓
下载包文件，根据发行版信任配置检查签名与完整性
            ↓
展示事务摘要，等待用户确认
            ↓
解包、替换文件、运行维护脚本/钩子、更新本地包数据库
```

这里的几个名词不能混为一谈：

- **repository（仓库）**：按发行版规则组织的包和元数据集合；镜像站是它的一个网络副本，不是另一套包。
- **package metadata（包元数据）**：让客户端在安装前就能查找包、比较版本和求解依赖。“刷新”通常是更新这份本地视图，不等于已安装软件已升级。
- **dependency（依赖）**：包之间的版本、功能、冲突、替换等关系。高层工具的重要价值是对整组变更求解，而不只是解压一个文件。
- **signature（签名）**：在配置好的信任链上验证仓库元数据或包的来源与完整性。签名成功不等于软件没有漏洞，也不会把错信的第三方密钥变安全。
- **transaction（事务）**：一次计算并记录的包变更集合。事务摘要是重要的最后检查点，但“事务”不代表整台系统必然可原子回滚：维护脚本、用户数据、已消失的旧包都可能使恢复变复杂。

> [!warning] 不要关闭验证来“修复”签名错误
> `--nogpgcheck`、降低 `SigLevel` 或允许未认证 APT 仓库，都是绕过安全边界，不是通用故障排除步骤。先核对系统时间、发行版密钥环包、仓库配置、镜像状态和密钥指纹。

## 2. 四个名字，三条主要工具链

| 发行版边界 | 高层入口 | 底层包/数据库 | 负责范围 | 不应做的类比 |
| --- | --- | --- | --- | --- |
| Arch Linux | `pacman` | `libalpm`、`.pkg.tar.zst` | 同一工具处理同步库、依赖、安装、移除、查询与签名 | 不要把 `apt update` 的两步习惯直译成危险的 `pacman -Sy` 后停下 |
| Debian / Ubuntu | `apt`（交互）、`apt-get`/`apt-cache`（稳定脚本接口） | `dpkg`、`.deb` | APT 管仓库索引、下载和依赖求解；`dpkg` 管本地包数据库和包文件 | 不要默认用 `dpkg -i` 代替 `apt install`；前者不会自动从仓库下载并安装依赖 |
| 传统 Fedora / RHEL 系统 | `dnf`（新系统也可能是 DNF5 实现） | `rpm`、`.rpm` | DNF 管仓库、元数据、依赖和事务；RPM 管单包与本地 RPM 数据库 | 不要默认用 `rpm -i` 取代 `dnf install` |
| RHEL 8/9 中的 `yum` | `yum` 名称作为基于 DNF 的兼容入口 | 同 DNF/RPM 工具链 | 帮助旧命令习惯迁移 | 不要由此推断 RHEL 7 旧 YUM 的所有插件、Python API、输出和边缘参数都完全相同 |

### `yum` 的历史角色与当前边界

`yum` 是早期 Fedora/RHEL 系统中广泛使用的高层包管理器名称。DNF 后来接替了这套技术栈的主要实现。Red Hat 对 RHEL 9 的官方描述是：使用 DNF 管理软件；`yum` 作为 `dnf` 的别名提供一定程度的兼容性。

因此，新的教程和自己的操作记录应优先写 `dnf`，而不是为了“通用”一律改写成 `yum`。看到旧文章的 `yum` 命令时，先核对：

1. 文章面向哪个发行版和大版本；
2. 它依赖的是否是旧 YUM 插件或 Python API；
3. 本机 `yum` 是兼容入口、独立旧实现，还是根本不存在；
4. 当前发行版文档是否要求 `dnf`、`dnf5`、`rpm-ostree` 或另一套工具。

> [!important] Fedora 也不只有一种主机更新模型
> 本页 DNF/RPM 命令面向传统的 RPM 包管理系统。Fedora Silverblue、Kinoite 等镜像式变体的主机更新以 `rpm-ostree` 等机制为边界；不要把本页的 `dnf upgrade` 无条件复制过去。

## 3. 常见动词对照表

下表中 `PACKAGE` 是核对过的包名，`KEYWORD` 是搜索词。每一列都是一套独立语法，不要横向拼接参数。

| 目的 | Arch / pacman | Debian/Ubuntu / APT、dpkg | 传统 Fedora/RHEL / DNF、RPM |
| --- | --- | --- | --- |
| 辨认系统（只读） | `cat /etc/os-release` | `cat /etc/os-release` | `cat /etc/os-release` |
| 刷新元数据 | 不单独教 `pacman -Sy`；与全系统升级合并为 `sudo pacman -Syu` | `sudo apt update` | `sudo dnf makecache`；要强制过期后重新检查可用 `dnf --refresh ...` |
| 搜索仓库（只读） | `pacman -Ss KEYWORD` | `apt search KEYWORD` | `dnf search KEYWORD` |
| 查看候选包（只读） | `pacman -Si PACKAGE` | `apt show PACKAGE` 和 `apt policy PACKAGE` | `dnf info PACKAGE` |
| 安装 | `sudo pacman -S PACKAGE`；如果必须刷新数据库，用 `sudo pacman -Syu PACKAGE` 在完整升级中安装 | `sudo apt install PACKAGE` | `sudo dnf install PACKAGE` |
| 移除 | `sudo pacman -R PACKAGE`；`-Rs` 会扩大到某些无需依赖，必须审阅摘要 | `sudo apt remove PACKAGE`；`purge` 还删除包管理的系统配置，不等于删用户家目录数据 | `sudo dnf remove PACKAGE`；它可能同时移除未使用依赖，先看清摘要 |
| 更新已安装包 | `sudo pacman -Syu`（Arch 支持的完整系统升级路径） | `sudo apt update` 后 `sudo apt upgrade` | `sudo dnf upgrade` |
| 查已安装包（只读） | `pacman -Q PACKAGE`、`pacman -Qi PACKAGE` | `dpkg-query -W PACKAGE` | `rpm -q PACKAGE`、`rpm -qi PACKAGE` |
| 列某包文件（只读） | `pacman -Ql PACKAGE` | `dpkg -L PACKAGE` | `rpm -ql PACKAGE` |
| 查某文件属于哪个已安装包（只读） | `pacman -Qo /usr/bin/bash` | `dpkg -S /usr/bin/bash` | `rpm -qf /usr/bin/bash` |
| 查可用更新（不安装） | 已安装 `pacman-contrib` 时用 `checkupdates`；不要为此改用 `pacman -Sy` | 刷新后用 `apt list --upgradable` | DNF5 文档中是 `dnf5 check-upgrade`（若发行版将 DNF5 暴露为 `dnf`，命令名随之变为 `dnf`）；DNF 4 是 `dnf check-update`。有更新时退出码可为 100，不表示普通故障 |
| 缓存维护 | ArchWiki 优先推荐 `paccache -r`（来自 `pacman-contrib`，默认保留近期版本）；`pacman -Sc/-Scc` 更激进 | `sudo apt clean` 清已下载包缓存；`autoclean` 只移除已无法下载的旧包 | `sudo dnf clean packages` 清包缓存；`sudo dnf clean all` 还会清元数据等，下次需重新下载 |
| 查事务历史（只读） | 查 `/var/log/pacman.log`，它是日志而非通用自动回滚器 | 查 `/var/log/apt/history.log` 和 `/var/log/dpkg.log`，同样不是保证可回滚的快照 | `dnf history`、`dnf history info ID` |

### “系统整体升级”不等于“换发行版”

- Arch 是滚动发行，`pacman -Syu` 将本机包集合与当前仓库状态整体对齐。
- Debian/Ubuntu 中，`apt upgrade` 是当前已配置发行版范围内的包升级。`apt full-upgrade` 可为完成升级移除已安装包，必须审阅计划；它也不是不看发行版说明就跨大版本的通用按钮。
- DNF 中，`dnf upgrade` 更新来自当前启用仓库的已安装包。发行版大版本迁移、镜像式主机更新或 RHEL 订阅内容变更，都有额外边界。

## 4. Arch 为什么禁止 partial upgrade

Arch 官方仓库以一个协调的滚动包集合发布。新共享库进入仓库时，依赖它的包会按需重建。如果只更新同步数据库或只升级其中一部分，本机可能变成仓库从未提供过的版本组合。

```text
旧本地包集 + 新同步数据库
        ↓
只装一个新包，并带入新共享库
        ↓
仍留在旧 ABI 上的其他程序可能无法启动
```

因此不要运行：

```bash
sudo pacman -Sy PACKAGE
```

也不要先运行 `pacman -Sy`，过一段时间再用 `pacman -S PACKAGE`。如果需要刷新同步数据库，就同时完成全系统升级：

```bash
sudo pacman -Syu
```

需要在刷新时一并安装新包时，可以把包名放在同一次完整事务中：

```bash
sudo pacman -Syu PACKAGE
```

> [!note] 这不是说任何发行版都不能单包更新
> partial upgrade 是 Arch 明确的仓库支持边界。Debian/Ubuntu 和 Fedora/RHEL 有各自的依赖、安全更新与发行周期政策，不能把 Arch 的规则反向复制成其他发行版的命令。

## 5. 官方仓库、第三方仓库与 AUR

“包管理器能安装”只说明格式和工具链能配合，不代表来源获得了发行版官方的审查、更新或支持承诺。

| 来源 | 你应该核对什么 | 主要风险 |
| --- | --- | --- |
| 发行版官方仓库 | 仓库名、当前发行版/套件、官方密钥环包、镜像是否正确 | 仍然存在软件漏洞、打包错误和供应链风险，但有明确的发行版责任边界 |
| 第三方仓库 | 维护者身份、密钥指纹与 `Signed-By`/GPG 配置、支持发行版、包名冲突、禁用和移除方法 | 仓库优先级或同名包可替换大量官方包；密钥一旦被信任，仓库维护者就获得很大权限 |
| Arch User Repository（AUR） | 逐行审查 `PKGBUILD`、`.install`、补丁、下载 URL、校验和变更；以普通用户构建 | AUR 是用户提交的、完全非官方且未经彻底审查的构建配方，不是 Arch 官方二进制仓库 |
| 手工下载的 `.deb`/`.rpm`/本地 Arch 包 | 精确 URL、发布者、签名/摘要、架构、发行版兼容性和卸载路径 | 这一次安装没有经过已配置仓库的来源选择与对应信任链；安装后能否自动更新，取决于之后是否有可信仓库提供同名包，以及候选版本和优先级；安装过程还可能将来历不明的脚本以 root 权限执行 |

> [!danger] 不要盲信“一行安装”
> 不要直接把陌生页面的 `curl ... | sudo sh`、密钥导入、第三方仓库启用或 AUR helper 命令粘贴进真实系统。先下载为文件、阅读内容、独立核对来源，并在无个人数据的虚拟机中试验。

## 6. 安全操作顺序

### 第一步：辨认发行版和系统模型

```bash
cat /etc/os-release
command -v pacman
command -v apt
command -v dnf
command -v rpm-ostree
```

`command -v` 只说明命令是否可找到。容器、兼容环境或人工安装可能让一台机器同时出现多个工具，所以还要以 `/etc/os-release` 和当前发行版文档判断主系统应走哪条路。

### 第二步：先查来源和候选版本

```bash
# Arch：查官方同步库中的候选包
pacman -Si PACKAGE

# Debian/Ubuntu：同时看候选版本和来源优先级
apt policy PACKAGE

# Fedora/RHEL 传统系统：先看启用仓库，再看包
dnf repolist --enabled
dnf info PACKAGE
```

核对包名、发行版、架构、来源仓库和要求的版本。不要因为搜索结果的描述看起来相似，就认为是同一个上游项目。

### 第三步：把事务摘要当成必读内容

真正执行安装、移除或升级时，在确认前逐项看：

- 是否忽然移除桌面、内核、网络、SSH 或包管理器本身；
- 是否从意外的第三方仓库取包；
- 是否出现降级、大量替换、异常架构或新模块流；
- 下载量、解包后空间和 `/boot` 等关键分区是否足够；
- 是否需要重启服务或系统，远程维护时是否有另一条恢复通道。

如果摘要超出预期，回答 `n`，保留输出后再研究。不要在未读计划时加 `-y` 或 `--assumeyes`。

### 第四步：一次只使用本发行版的一套命令

下面是错误的“拼贴式翻译”，不要尝试：

```text
pacman update PACKAGE      # 把 apt/dnf 的动词套给 pacman
apt -S PACKAGE             # 把 pacman 的选项套给 apt
dnf -Qi PACKAGE            # 把 pacman 查询选项套给 dnf
rpm remove PACKAGE         # 把 dnf 的子命令套给 rpm
```

命令不通用，仓库政策也不通用。教程中看到不同发行版时，要翻译的是“意图”，然后去当前发行版手册查正确语法，而不是替换一个命令名。

## 7. 练习：不安装任何包，画出本机包管理链

> [!tip] 练习边界
> 本练习不使用 `sudo`，不刷新元数据，不安装、移除、升级或清缓存。查仓库的结果可能来自现有本地缓存，所以要标注“可能不是最新”。

### 步骤 A：辨认系统

```bash
cat /etc/os-release
```

记录 `ID`、`VERSION_ID` 和是否属于镜像式变体。然后只从下面选一组，不要全部执行。

### 步骤 B：搜索候选包

**Arch：**

```bash
pacman -Ss '^tree$'
pacman -Si tree
```

**Debian/Ubuntu：**

```bash
apt search tree
apt policy tree
apt show tree
```

**传统 Fedora/RHEL：**

```bash
dnf search tree
dnf info tree
```

如果本地元数据中没有 `tree`，不要为了完成练习就刷新或添加仓库；记录“缓存中未找到”即可。

### 步骤 C：用已安装的 `bash` 连接包、文件和本地数据库

**Arch：**

```bash
pacman -Qi bash
pacman -Ql bash
pacman -Qo /usr/bin/bash
```

**Debian/Ubuntu：**

```bash
dpkg-query -W bash
dpkg -L bash
dpkg -S /usr/bin/bash
```

**传统 Fedora/RHEL：**

```bash
rpm -qi bash
rpm -ql bash
rpm -qf /usr/bin/bash
```

### 步骤 D：用自己的话回答

1. 本机的高层仓库/依赖工具是什么？本地包数据库由哪个工具查询？
2. 候选 `tree` 来自哪个仓库，本地缓存的候选版本是什么？
3. `/usr/bin/bash` 属于哪个已安装包？查询读的是远程仓库还是本地包数据库？
4. 如果真要安装 `tree`，应使用哪一条发行版原生命令？确认前要看事务摘要的哪些字段？

### 成功标准

- [ ] 能从 `/etc/os-release` 而不是从命令猜测发行版；
- [ ] 只执行了一组与本机匹配的查询命令；
- [ ] 能区分仓库候选包信息与已安装包信息；
- [ ] 能说明 refresh/update 元数据与 upgrade 已安装包不是一件事；
- [ ] 能解释为什么 Arch 上不应执行 `pacman -Sy PACKAGE`；
- [ ] 能解释 APT/dpkg、DNF/RPM 的高层与底层分工；
- [ ] 能说明 RHEL 9 上 `yum` 的兼容角色，不把它夸大成所有 YUM 时代行为均未改变；
- [ ] 本练习没有修改已安装包、仓库配置或缓存。

## 8. 恢复、回滚和清理边界

### 还在确认提示前

直接回答 `n`。此时事务尚未执行，是最安全的“恢复”时机。

### 误装了一个包

1. 先用本页的已安装查询和文件列表命令确认精确包名；
2. 查事务日志，确定当时还更改了哪些依赖；
3. 用对应的 `pacman -R`、`apt remove` 或 `dnf remove` 发起新事务，但先审阅待移除清单；
4. 不要直接删 `/usr` 下的文件，否则本地包数据库会与真实文件偏离。

APT 的 `remove` 通常保留包管理的系统配置，`purge` 更激进；两者都不应被当成删除家目录用户数据的通用工具。

### 更新后出现问题

- **Arch**：先读 `/var/log/pacman.log`、官方新闻和 ArchWiki 故障排除。缓存可能帮助重装或降级个别包，但降级后仍必须满足整体依赖；不要用更多 partial upgrade 修补 partial upgrade。
- **Debian/Ubuntu**：先读 APT/dpkg 日志和当前发行版的修复文档。不要在不理解状态时反复强制覆盖或删除 dpkg 数据库文件。
- **DNF/RPM**：先用 `dnf history` 和 `dnf history info ID` 检查。`dnf history undo ID` 是一个新的反向事务尝试，不是快照恢复；旧包不可用时会失败，Red Hat 也不支持用它将关键 RHEL 系统包降回旧小版本。

### 事务中断或锁文件存在

不要看到锁就立即删除。先确认是否仍有正常包管理进程，不要同时启动第二个前端。确认为异常中断后，再按当前发行版的官方修复流程处理未配置包、数据库状态或 chroot 救援。

这里的事务锁/数据库锁是 pacman、APT/dpkg 或 DNF/RPM 用来防止多个进程同时改写系统包状态的并发保护；它不是 Python 项目中记录精确依赖版本和解析结果的 dependency lockfile。前者保护一次系统数据库写入，后者用于项目环境的可重现安装；详见 [[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|包管理器选择、锁定与迁移]]。

### 缓存不是“废物”

清缓存能释放空间，但也会移除重装或降级的本地材料。先确认磁盘压力来自包缓存，再选最小的清理范围；不要为了保持“干净”就设置无审阅的激进定时清理。

## 9. 继续学习

- 上一站：[[计算机知识/20-操作系统/01-Linux/07-环境变量Shell启动与PATH|环境变量、Shell 启动与 PATH]]
- 下一站：[[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备驱动、内核模块与 udev]]
- Python 项目依赖：[[计算机知识/10-编程语言/01-Python/08-pip与PyPI依赖管理|pip 与 PyPI 依赖管理]]
- 工具边界与锁定：[[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|包管理器选择、锁定与迁移]]
- 返回：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础 MOC]]

## 官方资料

### Arch Linux

- [ArchWiki：pacman](https://wiki.archlinux.org/title/Pacman)
- [ArchWiki：System maintenance — Partial upgrades are unsupported](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported)
- [ArchWiki：Arch User Repository](https://wiki.archlinux.org/title/Arch_User_Repository)
- [Arch Linux 手册：pacman(8)](https://man.archlinux.org/man/pacman.8)

### Debian / Ubuntu

- [Debian 手册：apt(8)](https://manpages.debian.org/trixie/apt/apt.8.en.html)
- [Debian 手册：apt-secure(8)](https://manpages.debian.org/trixie/apt/apt-secure.8.en.html)
- [Debian 手册：dpkg-query(1)](https://manpages.debian.org/trixie/dpkg/dpkg-query.1.en.html)
- [Ubuntu Server：Install and manage packages](https://ubuntu.com/server/docs/package-management/)

### Fedora / DNF / RPM / RHEL

- [Fedora Docs：Upgrading Fedora Linux Using DNF System Plugin](https://docs.fedoraproject.org/en-US/quick-docs/upgrading-fedora-offline/)
- [DNF 官方文档：Command Reference](https://dnf.readthedocs.io/en/latest/command_ref.html)
- [DNF5 官方文档：Check-Upgrade Command](https://dnf5.readthedocs.io/en/latest/commands/check-upgrade.8.html)
- [Red Hat Enterprise Linux 9：Managing software with the DNF tool](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_software_with_the_dnf_tool/)
- [RPM 官方手册：rpm(8)](https://rpm.org/docs/6.0.x/man/rpm.8)


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/13-Linux-课程地图|Linux · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/01-Linux/16-服务资源容器与分层故障定位|Linux 深化：服务、资源、容器与分层排障]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
