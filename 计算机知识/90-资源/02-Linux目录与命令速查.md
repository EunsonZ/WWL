---
type: reference
domain: computer-science
stage: 90
status: ready
difficulty: 入门
estimated_minutes: 10
topics:
  - linux
  - filesystem-hierarchy
  - command-line
  - troubleshooting
tags:
  - computer-science/linux
  - computer-science/reference
nav:
  previous: 计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC
  next: 计算机知识/80-实践/02-Linux/00-Linux实验室
---

# Linux 目录与命令速查

这是一张“先查再动手”的桌面速查表。命令后面的标签表示典型风险，而不是对所有发行版和所有参数的绝对保证：

- **只读**：观察或查询，通常不改变系统；
- **普通写入**：在当前用户有权限的位置创建或修改数据；先使用临时目录或版本控制；
- **需特权**：通常需要 root 或设备/服务权限；先确认目标和恢复方法；
- **高风险**：可能删除、覆盖、卸载、重启、改变权限或影响网络/服务；本表只写占位符或查询形式，不提供可直接照抄的真实磁盘破坏命令。

> [!warning] 占位符不能整行复制
> 命令中的大写词（例如 PATH、FILE、UNIT、PID）只是占位符，运行前必须替换成已经核对的精确目标。先确认 pwd、身份、挂载点和作用范围；涉及写入、特权、服务、设备或包管理时，先做只读预览并准备恢复路径。

## FHS 目录地图

FHS（Filesystem Hierarchy Standard）描述常见目录的职责；现代发行版可能通过 systemd、厂商布局或 `/usr` 合并实现细节，但不要仅凭目录名猜测文件用途。

| 路径 | 通常存放 | 首选观察方式 |
| --- | --- | --- |
| `/` | 根层级与所有挂载点 | `findmnt`（只读） |
| `/boot` | 引导加载器、内核、initramfs | `ls -la /boot`（只读） |
| `/etc` | 主机和系统服务配置 | `ls -la -- /etc`、`man 5 FORMAT`（只读） |
| `/home` | 普通用户家目录 | `ls -la /home`（只读） |
| `/root` | root 家目录 | `ls -la -- ROOT_HOME`（只读；需要权限时先获准） |
| `/usr` | 大多数用户空间程序、库、共享数据 | `command -v COMMAND`、`ls -- /usr`（只读） |
| `/var` | 会变化的数据：缓存、队列、状态、日志 | `du -sh /var/*`（只读，可能权限不足） |
| `/run` | 本次启动的运行时状态、PID、socket | `find /run -maxdepth 1 -type d`（只读） |
| `/tmp` | 短期临时文件 | `mktemp -d`（普通写入；按需清理） |
| `/dev` | 设备节点 | `ls -l /dev`（只读；不要直接写设备） |
| `/proc` | 内核和进程的虚拟接口 | `cat /proc/uptime`（只读） |
| `/sys` | 设备、驱动和内核对象的虚拟接口 | `find /sys -maxdepth 1 -type d`（只读） |
| `/mnt`、`/media` | 临时或可移动介质挂载点 | `findmnt`（只读） |
| `/opt` | 可选的第三方软件 | `ls -la /opt`（只读） |

目录、挂载、inode 和文件系统的完整解释：[[计算机知识/20-操作系统/01-Linux/03-目录结构挂载与文件系统|目录结构、挂载与文件系统]]。

## 帮助、导航与命令解析

| 目的 | 命令/形式 | 风险 |
| --- | --- | --- |
| 查看 Bash 手册 | `man bash` | 只读 |
| 查看命令手册 | `man 1 COMMAND` | 只读 |
| GNU 长篇文档 | `info coreutils` | 只读 |
| 查看短帮助 | `COMMAND --help` | 只读 |
| 查找摘要关键词 | `apropos KEYWORD` | 只读 |
| 判断 Bash 如何解析名称 | `type -a COMMAND` | 只读 |
| 查看 PATH 中的解析结果 | `command -v COMMAND` | 只读 |
| 查看当前目录 | `pwd` | 只读 |
| 切换目录 | `cd -- DIRECTORY` | 普通写入（改变当前 shell 状态） |
| 查看历史 | `history` | 只读；可能显示秘密 |

Shell 的 prompt、引用、glob、管道、重定向、标准流和退出码：[[计算机知识/20-操作系统/01-Linux/04-Shell命令行与帮助系统|Shell 命令行与帮助系统]]。

## 文件与目录

| 目的 | 命令/形式 | 风险 |
| --- | --- | --- |
| 列出详细信息 | `ls -la -- PATH` | 只读 |
| 查看文件类型 | `file -- PATH` | 只读 |
| 查看权限/所有者 | `stat -- PATH` | 只读 |
| 创建空文件 | `touch -- NEW_FILE` | 普通写入 |
| 创建目录 | `mkdir -p -- NEW_DIRECTORY` | 普通写入 |
| 复制到明确目标 | `cp -i -- SOURCE DESTINATION` | 普通写入；可能覆盖前确认 |
| 移动/改名 | `mv -i -- SOURCE DESTINATION` | 普通写入；路径错误可能覆盖 |
| 删除 | `rm -i -- EXACT_FILE` | 高风险；本表不提供真实目标 |
| 计算目录大小 | `du -sh -- PATH` | 只读 |
| 查找路径 | `find ROOT -type f -name 'PATTERN'` | 只读；先限定 `ROOT` |

文件、目录、文本流和 glob 的完整练习：[[计算机知识/20-操作系统/01-Linux/05-文件目录与文本处理命令|文件、目录与文本处理命令]]。

## 文本与数据流

| 目的 | 命令/形式 | 风险 |
| --- | --- | --- |
| 查看短文件 | `less -- FILE` | 只读 |
| 查看开头/结尾 | `head -- FILE`、`tail -- FILE` | 只读 |
| 搜索文本 | `grep -n -- 'LITERAL' FILE` | 只读 |
| 统计行/词/字节 | `wc -l -w -c -- FILE` | 只读 |
| 排序/去重到屏幕 | `sort -- FILE \| uniq` | 只读 |
| 分列/转换 | `cut`、`tr` | 只读 |
| 观察管道分流 | `tee COPY` | 普通写入（目标文件） |
| 比较文件 | `diff -u -- OLD NEW` | 只读 |
| 安全预览重定向 | `printf '%s\n' 'TEXT'` | 只读 |

先确认输入路径，再使用 `>`（截断写入）或 `>>`（追加）；不要把未经审阅的 glob 当作唯一目标。

## 进程、权限与作业

| 目的 | 命令/形式 | 风险 |
| --- | --- | --- |
| 查看进程 | `ps -ef`、`pgrep -a NAME` | 只读 |
| 观察资源 | `top` 或 `free -h` | 只读 |
| 当前作业 | `jobs -l`、`fg`、`bg` | 只读/普通写入（改变当前 shell 作业状态） |
| 查看进程打开文件 | `lsof -p PID` | 只读；可能需特权 |
| 发送终止信号 | `kill -TERM PID` | 需特权/高风险；先确认 PID |
| 修改模式 | `chmod MODE EXACT_PATH` | 需特权/高风险；不使用无界递归示例 |
| 修改所有者 | `chown USER:GROUP EXACT_PATH` | 需特权/高风险 |
| 当前身份 | `id`、`groups` | 只读 |

进程生命周期、信号、前台/后台和权限模型：[[计算机知识/20-操作系统/01-Linux/06-用户权限进程与作业控制|用户、权限、进程与作业控制]]。

## 环境变量与启动

| 目的 | 命令/形式 | 风险 |
| --- | --- | --- |
| 查看变量 | `printf '%s\n' "$PATH"` | 只读 |
| 查看环境 | `env`、`printenv` | 只读；可能暴露秘密 |
| 临时设置变量 | `NAME=value COMMAND` | 普通写入（仅该进程） |
| 查找程序 | `command -v COMMAND` | 只读 |
| 查看当前 shell | `ps -p $$ -o comm=` | 只读 |

变量作用域、PATH 和 shell 启动文件：[[计算机知识/20-操作系统/01-Linux/07-环境变量Shell启动与PATH|环境变量、Shell 启动与 PATH]]。

## systemd、服务与日志

| 目的 | 命令/形式 | 风险 |
| --- | --- | --- |
| 查看启动状态 | `systemctl is-system-running` | 只读 |
| 查看服务状态 | `systemctl status UNIT` | 只读 |
| 查看失败单元 | `systemctl --failed` | 只读 |
| 查看本次日志 | `journalctl -b` | 只读 |
| 查看服务日志 | `journalctl -u UNIT --since 'TIME'` | 只读 |
| 查看磁盘日志占用 | `journalctl --disk-usage` | 只读 |
| 启动/停止/重启服务 | `systemctl ACTION UNIT` | 需特权/高风险；先确认 unit |
| 设置开机启用 | `systemctl enable UNIT` | 需特权/高风险 |

启动链、Kernel 与 systemd：[[计算机知识/20-操作系统/01-Linux/02-启动链Kernel与systemd|启动链、Kernel 与 systemd]]；网络、存储、日志排查：[[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|网络、存储、日志与故障排查]]。

## 网络、磁盘与设备

| 目的 | 命令/形式 | 风险 |
| --- | --- | --- |
| 查看接口和地址 | `ip address`、`ip link` | 只读 |
| 查看路由 | `ip route` | 只读 |
| 查看监听端口 | `ss -tulpen` | 只读；部分信息需特权 |
| 测试解析 | `getent hosts HOSTNAME` | 只读 |
| 查看挂载 | `findmnt`、`lsblk -f` | 只读 |
| 查看空间 | `df -hT`、`du -xhd1 -- PATH` | 只读 |
| 查看内核/设备 | `uname -a`、`lsusb`、`lspci` | 只读 |
| 挂载/卸载 | `mount EXPLICIT_DEVICE EXPLICIT_MOUNTPOINT` | 需特权/高风险；不提供可照抄目标 |

网络、存储、日志与故障排查详见[[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|网络、存储、日志与故障排查]]；设备、驱动、内核模块和 udev 详见[[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备、驱动、内核模块与 udev]]。

## 包管理

先确认发行版和包管理器；不要把不同发行版的命令混用。

| 目的 | 命令/形式 | 风险 |
| --- | --- | --- |
| 识别系统 | `cat /etc/os-release` | 只读 |
| 查询已安装包 | `pacman -Q`、`apt list --installed`、`dnf list installed` | 只读 |
| 搜索包 | `MANAGER search NAME` | 只读/网络读取 |
| 查看包文件清单 | `MANAGER files PACKAGE` | 只读 |
| 安装/升级/卸载 | `MANAGER ACTION PACKAGE` | 需特权/高风险；先读事务预览 |

发行版包管理器选择、锁定和迁移：[[计算机知识/20-操作系统/01-Linux/08-pacman-apt-dnf与yum包管理|pacman、apt、dnf 与 yum 包管理]]。

## 总体安全顺序

遇到故障时按“确认身份与系统 → 只读观察 → 缩小目标 → 备份或可恢复变更 → 最后才特权操作”的顺序。`sudo` 只扩大权限，不验证命令正确性；任何含 `PATH`、`UNIT`、`PID` 或 `PACKAGE` 的占位符，都必须替换成你已核对的精确目标，不能整行盲目复制。

## 导航

返回：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础]] · [[计算机知识/00-开始/00-计算机知识-首页|计算机知识首页]]

下一站实践：[[计算机知识/80-实践/02-Linux/00-Linux实验室|Linux 实验室]]
