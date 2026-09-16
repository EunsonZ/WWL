---
type: lesson
domain: computer-science
stage: 13
status: ready
difficulty: 进阶
estimated_minutes: 90
topics:
  - linux
  - arch-linux
  - post-installation
  - system-maintenance
  - pacman
  - systemd
  - security
  - backup-and-recovery
tags:
  - computer-science/linux
  - computer-science/arch-linux
  - computer-science/system-maintenance
  - computer-science/security
---

# Arch Linux 安装后配置、维护与安全

> [!abstract] 本课目标
> 学完后，你能把“已经启动”推进到“可日常使用、可持续升级、出故障可恢复”：建立普通用户与可审计的提权路径，按硬件和使用场景选择网络、图形、音频、蓝牙、桌面、字体和输入法；遵守 pacman 的全系统升级模型；理解 AUR 的信任边界；用 systemd、日志、备份、备用内核和 Arch 安装介质完成日常维护与恢复。

> [!important] 适用范围与资料边界
> 本页假设你已经按上一课完成基础安装并能进入新系统。命令以 ArchWiki 当前英文页面为依据，但硬件型号、引导器、文件系统、桌面环境和网络拓扑并不相同。带 `sudo` 的命令会改变系统；先读解释、替换占位符、保存当前配置并准备恢复入口，不把本页当成“一键脚本”。

## 最短路线：首次必做与按需分支

不必在首次启动时把整页从头到尾执行一遍。先完成能够支撑日常登录、升级和恢复的最小闭环，再根据硬件与用途进入分支：

| 路线 | 章节 | 完成标准 |
| --- | --- | --- |
| **首次必做** | 2 首次启动验收 → 3 普通用户与 sudo → 4 网络与时间 → 8 pacman 完整升级 → 13 备份 → 14 日志 → 15 可启动恢复入口 | 普通用户可登录并受控提权；时间、网络、完整升级正常；能取回测试文件，且能说出 live ISO/chroot 恢复路径 |
| **按需分支** | 5 显卡/声音/蓝牙、6 桌面、7 字体/输入法、10 AUR、12 防火墙/SSH | 只配置实际需要的硬件和服务；每个新增 unit、端口和非官方包都能说明用途和回退方法 |
| **周期维护** | 16 每周 SOP、17 每月 SOP、18 清理边界、19 安全清单、21 恢复速查 | 维护有固定节奏，变更前有备份和证据，变更后有验收 |

## 1. 安装完成不是维护完成

一个最小 Arch 系统只保证你获得了可组合的基础。安装后的目标不是“把推荐软件全部装上”，而是建立下面这条可观察的维护链：

```text
普通用户日常操作
        ↓ 只在必要时 sudo
受信任的软件来源与完整升级
        ↓
systemd 管理明确需要的服务
        ↓
日志与验收暴露异常
        ↓
独立备份 + 可启动恢复介质 + 已验证恢复步骤
```

这条链有四个原则：

1. **按需安装和启用**：没有蓝牙设备就不必启动蓝牙服务；本机不提供远程登录就不必运行 SSH 服务。
2. **最小权限**：日常会话使用普通用户，只有具体管理命令提权；不要长期停留在 root shell。
3. **完整升级**：Arch 是滚动发行版，官方仓库的软件包按一个整体状态发布；partial upgrade 不受支持。
4. **先有恢复，再做变化**：升级、驱动切换、引导修改和清理之前，先确认备份、包缓存、备用启动项和安装介质可用。

## 2. 首次启动验收表

先做只读检查，再开始安装桌面或修改服务。表中“通过”不是要求输出逐字相同，而是要求你能解释实际输出。

| 验收面 | 只读检查 | 通过标准 | 异常时先看 |
| --- | --- | --- | --- |
| 当前身份 | `id`、`whoami` | 日常登录不是 `root`；UID、组符合预期 | `/etc/passwd` 的账户定义、用户创建步骤 |
| 提权路径 | `sudo -v`、`sudo -l` | 能用自己的密码完成授权；只看到预期规则 | `visudo`、`/etc/sudoers.d/`，不要直接盲改 sudoers |
| 时区与同步 | `timedatectl status` | 时区正确，系统时钟已同步，NTP 服务活跃 | 网络、`systemd-timesyncd` 日志、RTC 标准 |
| 网络接口 | `ip -brief link`、`ip -brief address` | 预期接口启用并取得地址 | `networkctl` 或 `nmcli`；确认没有两个管理器争用同一接口 |
| 路由与 DNS | `ip route`；按所选解析器查询域名 | 默认路由和 DNS 解析都工作 | 网络管理器、`resolvectl`、`/etc/resolv.conf` 的实际归属 |
| 挂载关系 | `findmnt`、`lsblk -f`、`df -hT` | 根、ESP/`/boot`、独立分区和子卷与设计一致；空间充足 | `/etc/fstab`、UUID、加密/LVM/Btrfs 层级 |
| 启动健康 | `systemctl --failed` | 没有无法解释的 failed unit | `systemctl status unit`、`journalctl -b -u unit` |
| 本次日志 | `journalctl -b -p warning` | warning 均能分类；没有持续的存储、文件系统或认证故障 | `journalctl -k`、对应 unit、硬件固件 |
| 内核与模块 | `uname -r`、`lspci -k` | 正在运行的内核可识别关键控制器，驱动绑定合理 | 对应硬件的 ArchWiki 页面、`journalctl -k` |
| 声音（如需） | `wpctl status` | 能看到期望的输入/输出节点 | ALSA、PipeWire、WirePlumber 用户日志 |
| 蓝牙（如需） | `rfkill`、`systemctl status bluetooth` | 设备未被意外阻断；仅在需要时服务活跃 | BlueZ、内核模块、硬件开关 |
| 监听端口 | `sudo ss -lpntu` | 每个监听进程都有用途，地址与接口范围合理 | 服务配置、防火墙规则；不需要的服务先停用 |
| 软件来源 | `pacman -Qm` | 每个 foreign package 都知道来源、维护者和更新方式 | AUR/本地包审阅记录 |
| 恢复能力 | 检查安装 U 盘、备份报告、备用启动项 | 能说明如何挂载系统、进入 chroot、取回至少一个测试文件 | 本页恢复章节；不要等故障后才找 ISO |

建议把首次验收输出和你的选择记录到个人维护日志，但不要公开机器名、用户名、IP、SSH 公钥指纹以外的密钥材料或完整硬件序列号。

## 3. 普通用户、sudo 与最小权限

### 3.1 日常账户与管理员身份分开理解

ArchWiki 将 `wheel` 作为常见的管理组，但加入 `wheel` **不会自动获得 sudo 权限**；sudo 也不是 `base` 必然提供的默认授权。若安装时尚未创建普通用户，可在本地 root 控制台完成：

先把新账户名填入默认为空的变量。连续的非空与重名检查是门禁；检查不通过时，后续命令不会执行：

```bash
NEW_USER_NAME=''
test -n "$NEW_USER_NAME" && \
  ! getent passwd "$NEW_USER_NAME" >/dev/null && \
  useradd -m -G wheel -s /bin/bash "$NEW_USER_NAME" && \
  passwd "$NEW_USER_NAME" && \
  pacman -S sudo && \
  EDITOR=nano visudo
```

在 `visudo` 中启用要求输入密码的 wheel 规则：

```sudoers
%wheel ALL=(ALL:ALL) ALL
```

然后**保持 root 控制台不退出**，另开一个本地 TTY，以新用户登录并验证：

```bash
id
sudo -v
sudo -l
sudo whoami
```

最后一条预期输出 `root`。只有验证成功后，才考虑是否锁定 root 的密码登录；这不是首次启动必须动作。若锁定 root，必须先确认 sudo、备用管理员账户和 live ISO/chroot 恢复路径都有效，否则可能把自己锁在系统外。

### 3.2 提权的安全习惯

- 普通阅读、下载、编译和个人配置不使用 sudo。
- 对一个明确的管理命令使用 `sudo command`；需要短时管理 shell 时才用 `sudo -i`，结束后立即 `exit`。
- 编辑 root 拥有的配置时优先使用 `sudoedit /path/to/file`，或由 `visudo` 这类专用校验器修改。
- 默认保留 sudo 密码确认。`NOPASSWD` 会让任何已取得该用户执行权的进程更容易直接提权，不把它当作“方便优化”。
- 不用 `sudo` 启动日常图形程序；否则容易在家目录留下 root 拥有的文件并扩大图形应用的权限。
- 重定向由 shell 处理，`sudo echo value > /root/file` 并不会让 `>` 自动提权。理解命令边界后使用 `sudoedit`，不要用复杂管道掩盖写入目标。
- 给服务单独的系统用户、文件权限和 systemd 沙箱边界，而不是让所有守护进程都以 root 运行。

> [!warning] sudoers 写坏时
> 不要关闭尚可用的 root/sudo 会话。先用 `visudo -c` 检查；若已经失去提权能力，从 Arch 安装介质挂载根文件系统并 `arch-chroot`，再用 `visudo` 修复。不要通过把 `/etc/sudoers` 改成宽松权限来“解决”。

## 4. 网络与时间：一个接口只交给一个管理者

### 4.1 网络管理器的选择边界

ArchWiki 明确建议：每个网络接口只运行一个 DHCP 客户端或网络管理器。常见选择是：

| 场景 | 合理起点 | 边界 |
| --- | --- | --- |
| 笔记本、经常切换 Wi-Fi/VPN、需要桌面托盘 | NetworkManager | 它自己管理地址、路由、DNS 和无线认证时，不再并行启用独立 dhcpcd/iwd 去争用同一接口 |
| 固定服务器、静态或声明式网络 | systemd-networkd，可配 systemd-resolved | 没有完整交互式桌面前端；配置按接口文件维护 |
| 只需底层无线认证的定制环境 | iwd 或 wpa_supplicant，再配地址与 DNS 管理 | “关联到 AP”不等于已经获得 IP、路由和 DNS |

完成一次全系统升级后，按选择安装并启用一种方案。例如桌面常用 NetworkManager：

```bash
sudo pacman -S networkmanager
sudo systemctl enable --now NetworkManager.service
nmcli general status
nmcli device status
```

固定环境若选择 systemd-networkd，应先写好并检查 `/etc/systemd/network/*.network`，再启用所需服务；不要照抄并同时启用上面的 NetworkManager 示例。

切换管理器时按这个顺序进行：

1. 保留本地控制台，记录当前接口名、地址、路由和 DNS。
2. 准备新方案配置，但先不在远程 SSH 会话中切断旧网络。
3. 停用旧管理器，再启用新管理器。
4. 验证地址、默认路由、DNS 和重启后的持久性。
5. 成功后才删除旧配置；失败则从本地控制台恢复旧服务。

### 4.2 时间同步也是软件供应链前提

错误时间会导致 TLS 证书和软件包签名验证失败。多数普通客户端使用 `systemd-timesyncd` 已足够：

```bash
sudo timedatectl set-ntp true
timedatectl status
timedatectl timesync-status
```

若你安装了 chrony 等其他 NTP 实现，只启用一个负责校时。硬件时钟通常使用 UTC；双系统需要按 System time 页面统一策略，而不是让多个系统反复互相纠正。

## 5. 显卡、声音、蓝牙：先识别，再按需配置

### 5.1 显卡与显示栈

先收集证据：

```bash
lspci -k
uname -r
journalctl -b -k
```

关注 VGA/3D 控制器、`Kernel driver in use` 和可用模块。选择驱动时：

- 优先检查内核已提供的开源驱动和 Mesa 用户空间是否已经满足需求；ArchWiki 的 System maintenance 建议先尝试开源驱动。
- NVIDIA 专有驱动的包取决于 GPU 代际、正在使用的内核和是否采用 DKMS；先到对应 NVIDIA 页面核对，不依据搜索结果或旧博客猜包名。
- 多显卡、外接 GPU、硬件视频加速和 PRIME 是下一层问题；先让单一会话稳定启动，再逐项增加。
- 不要一遇到黑屏就生成完整 `/etc/X11/xorg.conf`。ArchWiki 指出大多数 Xorg 配置可自动探测；本机覆盖应放在 `/etc/X11/xorg.conf.d/`，且只包含确实需要的选项。

### 5.2 声音：区分 ALSA、声音服务器与会话管理器

ALSA 是内核中的底层声音系统。桌面多应用、蓝牙音频、屏幕共享等通常还需要声音服务器；PipeWire 是常见选择，WirePlumber 是 ArchWiki 推荐的 PipeWire 会话管理器。

在已经完成 `pacman -Syu` 的系统上，按需安装兼容层：

```bash
sudo pacman -S pipewire pipewire-audio wireplumber pipewire-alsa pipewire-pulse
wpctl status
pactl info
```

PipeWire 通常通过用户 unit/socket 启动，不要把用户服务和系统服务混为一谈。若已有 PulseAudio 或 JACK 专门配置，先阅读 PipeWire 的替换边界，不把两个竞争的声音服务器强行叠加。排错顺序是：设备是否被 ALSA 识别 → WirePlumber 是否建立节点 → 默认 sink/source 是否正确 → 应用是否选择了正确设备。

### 5.3 蓝牙：不用就不启动

需要蓝牙时安装 BlueZ 并启用服务：

```bash
sudo pacman -S bluez bluez-utils
sudo systemctl enable --now bluetooth.service
rfkill
bluetoothctl
```

先检查硬件开关和 `rfkill`，再在 `bluetoothctl` 中执行配对。便携设备若不希望蓝牙自动上电，可按 Bluetooth 页面配置 `AutoEnable=false`。完全不使用蓝牙时可以：

```bash
sudo systemctl disable --now bluetooth.service
```

## 6. 桌面、Wayland、Xorg 与显示管理器

这四者不是同义词：

| 层 | 职责 | 选择边界 |
| --- | --- | --- |
| 桌面环境（DE） | 面板、设置、通知、电源、文件管理等成套体验 | 新手优先选一个完整 DE；混装多个 DE 会增加依赖和配置交叉 |
| 窗口管理器 / Wayland compositor | 窗口布局和合成 | 自定义环境还需自行补齐锁屏、通知、Polkit agent、截图、电源等组件 |
| Wayland / Xorg | 图形客户端与显示系统的协议/实现边界 | 优先使用 DE 对当前硬件支持良好的默认会话；旧应用可经 Xwayland 兼容，特殊驱动/工具再保留 Xorg 会话 |
| 显示管理器 | 图形登录与选择会话 | 只启用一个；也可不装，在 TTY 中按 DE/WM 文档启动 |

不要先问“Wayland 和 Xorg 哪个绝对更好”，而要验证：你的桌面默认支持什么、GPU 驱动是否支持、屏幕共享/输入法/远程桌面/色彩管理等关键应用是否工作。Wayland 与 NVIDIA 组合可能要求 DRM KMS 和显示管理器的额外条件；旧 NVIDIA 驱动的 Xwayland 加速能力也有限，应以当前对应页面为准。

切换显示管理器时先停用旧 unit，再启用新 unit，并保留 TTY 入口。下面是操作意图，不是可整块执行的脚本：

```text
systemctl status display-manager.service
sudo systemctl disable --now OLD_DISPLAY_MANAGER.service
sudo systemctl enable --now NEW_DISPLAY_MANAGER.service
```

先用第一条和所选桌面的官方文档确认旧、新 unit 的真实名称，再逐条执行对应动作。若新登录界面失败，用 `Ctrl+Alt+F2` 等切换到 TTY，停用新 unit、恢复旧 unit，并检查：

```bash
systemctl --failed
journalctl -b -u display-manager.service
```

## 7. 字体与输入法

### 7.1 字体先覆盖字符，再调外观

方框、缺字或中日文字形异常通常是字体覆盖或 fontconfig fallback 问题。一个常见起点是从官方仓库选择拉丁、CJK 和 Emoji 字体，例如：

```bash
sudo pacman -S noto-fonts noto-fonts-cjk noto-fonts-emoji
fc-match sans-serif
fc-match monospace
fc-match :lang=zh-cn
```

不要一次安装大量重复字体再猜优先级。用户级覆盖放在 `~/.config/fontconfig/fonts.conf`，系统级才使用 `/etc/fonts/local.conf`；修改后用 `fc-match --sort` 观察实际 fallback。包安装通常会处理缓存，手动排错时再按 Fonts 页面使用 `fc-cache`。

### 7.2 输入法与桌面/显示协议一起选

- GNOME 与 IBus 集成紧密，通常先使用桌面设置中的 Input Sources。
- KDE/Qt 环境常用 Fcitx5；中文还需要具体的 IME，例如 `fcitx5-chinese-addons` 或 `fcitx5-rime`。
- Fcitx5 本体只是框架，没有中文引擎就只能提供基础输入。
- Wayland 原生 text-input、Xwayland、GTK/Qt 输入模块的路径不同。不要把网上所有 `GTK_IM_MODULE`、`QT_IM_MODULE`、`XMODIFIERS` 变量全局叠加；先按当前 compositor/DE 的 ArchWiki 小节配置，再分别验证原生 Wayland、Xwayland、GTK、Qt 应用。

验收至少包括：终端、浏览器、一个 GTK 应用、一个 Qt 应用能切换并输入中文；重登后仍有效；密码框和锁屏没有异常预编辑行为。

## 8. pacman：只做完整系统升级

### 8.1 partial upgrade 为什么不受支持

Arch 官方仓库会在共享库升级时重建相关包。只刷新数据库或只升级其中一部分，可能让新库与旧二进制不匹配。因此日常升级命令是：

```bash
sudo pacman -Syu
```

下面这些组合不要使用。它们放在不可执行的 `text` 块中，仅用于识别错误模式：

```text
不要执行：pacman -Sy
不要执行：pacman -Sy PACKAGE_NAME
不要执行：pacman -Syuw
```

如果只想**安全查看**可用更新，安装 `pacman-contrib` 后使用：

```bash
checkupdates
```

`checkupdates` 使用临时数据库，不把运行系统留在“数据库已更新、软件未更新”的状态。若 `pacman -Syu` 在完成数据库同步后失败，先解决错误并完成这次升级，再进行其他安装操作。不要用创建假库符号链接、`--overwrite '*'`、`pacman -Rdd` 或长期 `IgnorePkg` 来掩盖不一致。

### 8.2 升级前检查

1. 阅读 ArchWiki System maintenance 指向的 Arch News，特别是较久未升级或有人工干预公告时。
2. 确认时间、DNS、镜像和签名验证正常。
3. 检查根、`/var` 和 ESP/`/boot` 空间：

   ```bash
   df -hT / /var /boot
   ```

   如果这些路径在同一文件系统，重复行是正常的；不存在单独 `/boot` 时按实际挂载检查。
4. 确认最近一次备份成功并能读取；重大升级前创建快照可加速回滚，但不能替代备份。
5. 保存可重建清单。不要在未知当前目录中用固定文件名重定向；下面把清单放入当前用户的状态目录，以 UTC 时间和内核版本创建权限为 `700` 的新目录。若同名目录或文件已存在，门禁会停止，不会覆盖：

   ```bash
   PACKAGE_MANIFEST_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/arch-maintenance/package-manifests"
   PACKAGE_MANIFEST_ID="$(date -u +%Y%m%dT%H%M%SZ)-$(uname -r)"
   PACKAGE_MANIFEST_DIR="$PACKAGE_MANIFEST_ROOT/$PACKAGE_MANIFEST_ID"

   umask 077
   install -d -m 700 "$PACKAGE_MANIFEST_ROOT" && \
     test ! -e "$PACKAGE_MANIFEST_DIR" && \
     mkdir -m 700 "$PACKAGE_MANIFEST_DIR" && \
     ( set -o noclobber
       pacman -Qqe > "$PACKAGE_MANIFEST_DIR/explicit-packages.txt" &&
       pacman -Qqm > "$PACKAGE_MANIFEST_DIR/foreign-packages.txt"
     ) && \
     test -s "$PACKAGE_MANIFEST_DIR/explicit-packages.txt" && \
     test -f "$PACKAGE_MANIFEST_DIR/foreign-packages.txt" && \
     wc -l "$PACKAGE_MANIFEST_DIR/explicit-packages.txt" \
       "$PACKAGE_MANIFEST_DIR/foreign-packages.txt" && \
     sha256sum "$PACKAGE_MANIFEST_DIR/explicit-packages.txt" \
       "$PACKAGE_MANIFEST_DIR/foreign-packages.txt"
   ```

   记录命令显示的目录、行数和校验和，再把这个完整的版本化目录纳入第 13 节定义的独立备份，并从备份端读回两个文件。本机上的版本化目录不是备份。清单可能包含隐私相关的软件名称，按备份资料保护。
6. 对远程机器保留带外控制台或第二条会话，避免同时升级网络、防火墙和 SSH 后失联。

### 8.3 升级时与升级后

运行升级并完整阅读输出：

```bash
sudo pacman -Syu
```

升级后：

```bash
systemctl --failed
sudo journalctl -b -p warning
grep -E '\.pac(new|save)' /var/log/pacman.log | tail
```

- 立刻处理 `.pacnew` / `.pacsave`。安装 `pacman-contrib` 后可用 `sudo pacdiff` 逐个比较；不能把 `.pacnew` 直接覆盖生产配置。
- 重启受影响的长期运行服务。内核、关键库或无法判断影响范围时，重启是最清晰的边界。
- 重启后再次验收网络、图形、声音、关键服务、挂载和日志。
- AUR/本地构建包不会自动变成官方受支持状态；共享库发生 soname 变化时，它们可能需要重新构建。

## 9. 镜像与 pacman keyring

### 9.1 镜像追求“同步且可用”，不只是测速第一

pacman 按 `/etc/pacman.d/mirrorlist` 从上到下尝试镜像。最快的镜像可能尚未同步，因此更新镜像时同时考虑同步状态、HTTPS、地域和速度。修改前备份：

```bash
sudo cp -a /etc/pacman.d/mirrorlist /etc/pacman.d/mirrorlist.backup
```

若 `mirrorlist.backup` 已经存在，改用一个新的、明确的文件名，不覆盖尚未确认用途的旧备份。

可以按 Mirrors 页面手工排序，或使用官方仓库中的 Reflector 根据当前 MirrorStatus 生成列表。自动覆盖前先查看 `reflector --help`，使用明确的过滤条件，把结果写到临时文件检查后再替换；排名工具不应高频运行，ArchWiki 建议大约每 1–2 周最多一次。

镜像故障的恢复顺序：

1. 看错误是 DNS/TLS、超时、404 还是签名问题，不把它们混为一类。
2. 临时把同步正常的 HTTPS 镜像移到前面。
3. 完成 `pacman -Syu`，验证包数据库和系统状态。
4. 若新列表有问题，恢复 `mirrorlist.backup`。

### 9.2 keyring 是信任链，不是报错开关

官方包默认要求签名验证；`archlinux-keyring` 提供最新受信任密钥。遇到签名错误先检查：

- 系统时间是否正确；
- 网络是否返回了真实软件包而不是认证门户页面；
- 系统是否很久未升级，keyring 是否过旧；
- 镜像是否同步。

不要把 `SigLevel` 改成 `TrustAll`，不要随意本地签署一个尚未核对指纹的密钥。对长时间未升级导致 keyring 过旧的特殊情况，ArchWiki 给出的连续流程是先同步并更新 keyring，随后**立即完成其余系统升级**；必须阅读当前 Package signing 页面并把两步视为一个不可中断操作，而不是把第一步当成日常命令。

## 10. AUR 的信任模型与 PKGBUILD 审阅

### 10.1 AUR 不是官方二进制仓库

AUR 保存用户提交的 `PKGBUILD` 和相关文件。它们完全非官方、没有经过彻底审查，也不由 pacman 负责自动更新。投票多、评论好、AUR helper 能安装，都不等于安全。

推荐流程是先填写默认为空的包名变量，通过非空门禁后才会安装构建工具、克隆和进入目录：

```bash
AUR_PACKAGE_NAME=''
test -n "$AUR_PACKAGE_NAME" && \
  sudo pacman -S --needed base-devel git && \
  git clone "https://aur.archlinux.org/${AUR_PACKAGE_NAME}.git" && \
  cd "$AUR_PACKAGE_NAME" && \
  less PKGBUILD
```

继续查看仓库中的 `.install`、补丁、service、desktop、脚本和其他文件，再以**普通用户**构建：

```bash
makepkg -si
```

`makepkg` 不应以 root 运行。安装阶段需要的提权由 pacman 按明确步骤处理。

### 10.2 审阅清单

在构建前回答这些问题：

1. `source=()` 指向哪里？是否是项目官方发布物，是否突然换域名、短链接或动态“latest”文件？
2. `sha256sums` 等校验是否有效？若上游提供 `.sig`/`.asc`，`validpgpkeys` 的指纹是否能独立核对？`SKIP` 需要什么理由？
3. `prepare()`、`build()`、`check()`、`package()` 分别执行什么？是否下载并立即执行第二阶段脚本？
4. 是否出现 `curl ... | sh`、`wget ... | bash`、`eval`、混淆编码、读取家目录秘密、修改 shell 配置、启动网络服务或删除广泛路径？
5. `.install` 脚本和 systemd unit 安装后会以谁的身份、在何时运行？是否新增监听端口或定时任务？
6. `depends`、`makedepends`、`optdepends` 是否合理？是否偷偷依赖另一个 AUR 包或未经说明的二进制 blob？
7. 最近提交为何变化？维护者、置顶评论、上游版本和包名是否仍一致？
8. 更新时重新审阅 diff，而不是因为旧版本看过一次就永久信任。

> [!danger] 停止条件
> 看不懂高权限命令、来源无法核验、校验被无理由跳过、脚本读取凭据或运行混淆载荷时，不构建、不安装，先向 Arch 社区求证。扫描工具和 AUR helper 不能替代人工审阅。

## 11. systemd 服务：安装不等于启用

systemd unit 常见操作如下。这是命令意图对照表，不是可整块执行的脚本；必须先把 `UNIT_NAME` 换成已确认的具体 unit，再只选需要的一条：

```text
systemctl status UNIT_NAME
systemctl cat UNIT_NAME
sudo systemctl start UNIT_NAME
sudo systemctl enable UNIT_NAME
sudo systemctl enable --now UNIT_NAME
sudo systemctl disable --now UNIT_NAME
systemctl --failed
journalctl -b -u UNIT_NAME
```

- `start` 只影响当前运行；`enable` 建立开机依赖；`enable --now` 同时做两件事。
- 并非每个 unit 都应该 enable；有些由 socket、timer、path、设备或其他 target 激活。
- 修改 vendor unit 时不要直接编辑 `/usr/lib/systemd/system/`；用 `systemctl edit UNIT_NAME` 创建 `/etc/systemd/system/` drop-in，并用 `systemctl cat UNIT_NAME` 检查最终合并结果。
- 普通用户服务使用 `systemctl --user` 和 `journalctl --user -u UNIT_NAME`；不要因为它是“服务”就一律加 sudo。
- `mask` 比 `disable` 更强，会阻止 unit 被手动或依赖启动。只有明确理解影响时才使用；恢复用 `unmask`。
- `systemctl reset-failed` 只清掉失败标记，不修复根因，还可能让后续取证更困难；先保存状态和日志。

## 12. 防火墙与 SSH 的最小配置

### 12.1 先缩小监听面，再加防火墙

检查监听进程：

```bash
sudo ss -lpntu
```

不需要的服务直接 `disable --now`。只供本机使用的服务绑定 Unix socket 或 loopback，而不是 `0.0.0.0`。确需远程访问时，再让防火墙只允许必要的协议、端口、来源网段和接口。

Arch 内核支持 nftables，但默认并不会自动为你启用防火墙。若选择 nftables：

```bash
sudo pacman -S nftables
sudoedit /etc/nftables.conf
sudo nft -c -f /etc/nftables.conf
sudo systemctl enable --now nftables.service
sudo nft list ruleset
```

ArchWiki 指出 nftables 包提供了一个简单安全的 `/etc/nftables.conf` 起点；仍要逐行确认是否适合桌面、服务器、容器、VPN 和 IPv6。不要同时让多个防火墙前端竞争管理同一规则集。远程操作时，必须先允许当前 SSH 管理路径并保留带外控制台，否则默认拒绝入站可能立即断开自己。

### 12.2 SSH 只在需要时开启

本机不接受远程登录时不要安装或启用 sshd。确需 SSH：

1. 安装 OpenSSH，但先保留本地控制台。
2. 为普通管理用户配置并测试公钥，核对服务器主机密钥指纹。
3. 用防火墙限制可信来源；公网暴露还需更严格的威胁模型。
4. 用 drop-in 禁止 root 远程登录，并在确认所有所需账户都能用公钥登录后关闭密码登录：

   ```text
   # /etc/ssh/sshd_config.d/20-local-hardening.conf
   PermitRootLogin no
   PasswordAuthentication no
   AuthenticationMethods publickey
   ```

5. 修改后先验证语法：

   ```bash
   sudo sshd -t
   sudo systemctl restart sshd.service
   ```

6. 保持现有会话不关闭，另开第二条连接验证普通用户登录和 sudo，成功后才结束旧会话。

> [!warning] 不能跳过的顺序
> ArchWiki 明确警告：关闭密码登录前，所有需要 SSH 的账户必须已经配置好 `authorized_keys`。改端口不能替代密钥认证、禁止 root、严格防火墙和日志审查。

## 13. 备份、快照与恢复验证

### 13.1 备份保护什么

至少覆盖：

- 个人不可再生数据与项目；
- `/etc` 中的本机配置；
- 应用在 `/var/lib` 等位置的必要状态，按应用文档做一致性备份；
- 引导器、加密、文件系统和挂载布局的恢复说明；
- 显式包清单、foreign package 清单和自建 `PKGBUILD`；
- 需要保留的 SSH 密钥、密码库和恢复密钥，并用更严格的加密与离线保护。

备份目的地至少要有一份不依赖当前系统盘；同盘另一个目录无法抵御整盘损坏。ArchWiki 的 Synchronization and backup programs 列出了 rsync、Borg、Restic 等不同模型；根据版本历史、加密、远程传输、元数据和恢复方式选择，不把“同步成功”自动等同于“有可回退的历史备份”。

### 13.2 快照不等于备份

Btrfs/LVM 快照适合在升级前快速冻结状态、测试变化和回滚，但通常仍依赖同一物理介质。ArchWiki 的 LVM 页面明确警告：CoW 快照没有创建原始数据的第二份副本，损坏的磁盘扇区也会影响快照。快照还可能不包含独立 ESP/`/boot`，并会随空间耗尽、误删或存储池故障一起失效。

正确关系是：

```text
快照：分钟级回滚工具
备份：跨故障域的数据恢复副本
安装介质 + chroot：系统无法启动时的维修入口
```

### 13.3 恢复演练才算验收

每月至少抽取一个普通文件恢复到临时目录并比较内容。重要系统还应在备用机器或虚拟机演练：读取备份仓库、恢复权限/扩展属性、重建包、恢复引导和登录。记录恢复所需的命令、密钥存放位置和预计时间，但不要把密钥值写进普通日志。

## 14. 日志：先保存证据，再修改系统

常用查询：

```bash
# 当前启动
sudo journalctl -b

# 上一次启动（日志已持久化时）
sudo journalctl -b -1

# 当前启动的内核消息
sudo journalctl -b -k

# 某个 unit：先把 UNIT_NAME 替换为真实名称
sudo journalctl -b -u UNIT_NAME

# 失败的 units
systemctl --failed

# pacman 事务历史
sudo less /var/log/pacman.log
```

排错时记录：发生时间、升级前后包版本、当前内核、复现步骤、unit 状态和相关日志范围。不要只贴最后一行，也不要把整份日志未经检查地公开；先移除主机名、用户名、内网地址、令牌和私密路径。

日志轮转或 vacuum 是空间管理，不是“修复错误”。清空日志会丢失证据；先用 `journalctl --disk-usage` 观察，再按 journald 页面设置持久上限，而不是遇到磁盘告警就盲目删除 `/var/log`。

## 15. 两层内核退路与 live ISO/chroot 恢复

### 15.1 fallback initramfs 与 `linux-lts` 不是一回事

| 退路 | 解决的问题 | 不能解决什么 |
| --- | --- | --- |
| fallback initramfs | 与当前内核配套，但跳过 `autodetect`，包含更广的模块；可处理默认 initramfs 漏模块 | 当前内核本身的回归 |
| `linux-lts` 等备用内核 | 提供另一条内核版本线，可绕过最新内核回归或外部模块兼容问题 | 文件系统损坏、错误 fstab、损坏引导器等 |
| Arch live ISO + `arch-chroot` | 系统完全无法启动时，从外部环境挂载并维修 | 不能自动判断你的加密、子卷、ESP 和引导方案 |

当前 mkinitcpio 默认不生成 fallback image；只有 `/etc/mkinitcpio.d/*.preset` 显式启用 `fallback` preset 时才会生成。先检查 preset、`/boot` 中的对应镜像文件和引导器条目，再决定是否需要启用：若第 12 课已经显式启用并成功生成，就沿用现有配置并测试；若尚未启用，则按 Mkinitcpio 页面配置 preset，重新生成 initramfs，并让引导器能选择它。不要把“文件存在”当作可启动证明，维护窗口中实际测试一次。

`linux-lts` 是官方仓库中的可选备用内核。安装后还必须让所用引导器出现对应 `vmlinuz-linux-lts` 与 `initramfs-linux-lts.img`（或对应 UKI）条目；外部内核模块也要有匹配版本。安装包而不验证启动菜单，不算建立退路。

### 15.2 无法启动时的通用恢复骨架

先尝试引导菜单中的备用内核或 fallback initramfs。仍失败时：

1. 启动最新 Arch 安装介质，连接网络并确认时间。
2. 用 `lsblk -f` 和原有记录识别根、ESP/`/boot`、加密容器、LVM 和 Btrfs 子卷。
3. 按原布局挂载，下面只是不可执行的占位骨架：

   ```text
   mount ROOT_DEVICE_OR_SUBVOLUME /mnt
   mount BOOT_OR_ESP_DEVICE /mnt/ACTUAL_BOOT_MOUNTPOINT
   arch-chroot -S /mnt
   ```

   有独立 `/var`、`/home`、Btrfs 子卷或加密/LVM 时必须先按 `/etc/fstab` 和原设计全部正确挂载。ESP 实际可能挂载在 `/boot`、`/efi` 或 `/boot/efi`，不能猜。截至 2026-09-01，当前 Arch 官方安装指南使用 `arch-chroot -S`；`-S` 表示通过 `systemd-run` 进入 systemd mode，不是软件包管理选项。若安装介质中的 `arch-chroot --help` 与当前官方手册不一致，停止照抄并以该介质版本的手册为准。
4. 进入 chroot 后先取证：

   ```bash
   findmnt
   less /var/log/pacman.log
   ls -l /boot
   ls -l /etc/mkinitcpio.d
   ```

   chroot 中依赖运行中 D-Bus 的 `timedatectl`、`hostnamectl` 等可能不可用，这不等于已安装系统的配置丢失。
5. 根据证据修复：完成中断的全系统升级、恢复 `.pacnew` 合并、重新安装匹配的内核、运行 `mkinitcpio -P`、修正 fstab，或按所用引导器页面重建配置。一次只改变一个故障面并读回结果。
6. `exit` 离开 chroot，检查挂载，卸载并重启。保留安装介质，直到正常内核、备用内核、网络和日志验收都通过。

> [!danger] 不要用“万能恢复命令”
> `pacman --overwrite '*'`、伪造缺失库符号链接、混用 Arch Linux Archive 与最新镜像、格式化分区、重装引导器或重建 keyring 都有明确前提。先判断故障发生在固件、引导器、initramfs、内核还是实际系统，再走对应 ArchWiki 页面。

## 16. 每周维护 SOP

适合个人工作站的起点如下；生产服务器应有维护窗口、测试副本和变更审批。

1. 阅读 Arch News，确认是否有人工干预事项。
2. 查看备份最近一次成功时间，并确认恢复凭据可用。
3. 运行只读健康检查：

   ```bash
   systemctl --failed
   sudo journalctl -b -p warning
   df -hT / /var /boot
   checkupdates
   ```

4. 处理已知磁盘、网络、时间、镜像或 keyring 异常；状态不明时不开始升级。
5. 运行 `sudo pacman -Syu`，完整阅读警告和可选依赖变化。
6. 用 `pacdiff` 人工合并 `.pacnew` / `.pacsave`，不覆盖自定义配置。
7. 检查 AUR/本地构建包的上游和 PKGBUILD diff，按需重新构建。
8. 重启受影响服务；内核或关键组件升级后安排重启。
9. 重启后复查：`uname -r`、`systemctl --failed`、网络、关键服务、图形/音频和本次启动日志。
10. 在个人维护记录中写明日期、主要包变化、人工干预、异常与恢复点。

## 17. 每月维护 SOP

1. 从备份恢复一个测试文件；季度或重大变更前做完整恢复演练。
2. 检查备用内核、fallback/备用启动项和 Arch 安装介质是否仍可用。
3. 审阅外来包与孤儿候选：

   ```bash
   pacman -Qm
   pacman -Qtd
   ```

   `pacman -Qtd` 只是候选清单。逐个确认用途；仍需要的包可改为显式安装原因，不把查询结果直接交给批量删除命令。
4. 审阅监听面和服务：

   ```bash
   sudo ss -lpntu
   systemctl --failed
   systemctl list-timers
   ```

5. 检查 pacman 缓存大小。确需释放空间时优先使用 `paccache` 的保留策略；默认 `sudo paccache -r` 会保留最近三个版本。先读 `paccache -h`，保留至少一个可回退版本，并确认备份/网络可用。
6. 检查 journal 占用、磁盘 SMART/文件系统健康和设备固件更新需求；按相应 ArchWiki 页面处理。
7. 镜像质量变差或长期未维护时再更新 mirrorlist，不高频测速。
8. 核对 sudoers、SSH key、管理员账户和恢复密钥；撤销离职/不再使用的访问，而不是无限累积。

## 18. 不要盲用清理命令

| 看似省事的操作 | 风险 | 更安全的做法 |
| --- | --- | --- |
| `pacman -Scc` | 清空全部包缓存，失去无需联网的快速降级来源 | 用 `paccache` 保留若干版本，先确认实际空间瓶颈 |
| 把 `pacman -Qtdq` 直接展开后批量 `-Rns` | 可删掉你仍直接需要、但安装原因记录不正确的工具 | 逐个审阅，必要时改为 explicit，再小批删除和验收 |
| `pacman -Rdd` | 跳过依赖检查，容易制造损坏系统 | 解决真实依赖关系；只按 Arch 开发者明确恢复指令例外使用 |
| 删除 `/var/log` 或大范围 vacuum | 丢失故障和安全取证 | 先看占用，设置 journald 上限并保留需要的启动历史 |
| `nft flush ruleset` | 立即移除整个防火墙 | 先保存规则，离线校验新配置，使用受控 reload 和带外入口 |
| 删除“旧内核”或 `/boot` 文件 | 可能删除唯一可启动退路或让引导条目悬空 | 先核对包归属、正在运行的内核、引导项和备用启动测试 |
| 删除所有快照 | 失去快速回滚点 | 按空间预算和保留策略删除，先确认独立备份完成 |
| 运行来源不明的“Arch 清理脚本” | 可能以 root 删除广泛路径、改镜像、禁服务 | 逐行审阅；把查询与写入分离；优先官方仓库工具和 ArchWiki 流程 |

清理的正确顺序是：**测量 → 识别归属 → 备份/保留回退 → 小范围执行 → 验证 → 记录**。

## 19. 安全实践清单

- [ ] 日常使用普通用户；sudo 需要密码且规则经 `visudo` 校验。
- [ ] 只启用明确需要的 systemd 服务；每个监听端口都有用途和范围。
- [ ] 只运行一个网络管理方案和一个防火墙管理方案。
- [ ] SSH 非必要不启用；必要时使用普通用户、公钥、禁止 root，并先验证再关密码。
- [ ] 官方仓库包保持完整升级，签名验证不降级。
- [ ] 每次 AUR 更新重新审阅 PKGBUILD、相关文件和 diff；构建不使用 root。
- [ ] 备份有独立故障域、加密和恢复测试；快照只作为回滚层。
- [ ] 升级前有空间、备份、备用内核/启动项和 live ISO。
- [ ] 异常先保存日志和 pacman 事务证据，再修改系统。
- [ ] 不复制执行带破坏性的清理、覆盖、依赖跳过或信任绕过命令。

## 20. 动手练习：为自己的机器写一张维护卡

在 [[计算机知识/80-实践/02-Linux/00-Linux实验室|Linux 实验室]] 中新建一篇个人实验记录，但不要记录秘密值。包含：

1. 当前普通用户、sudo 验证结果和 root 恢复入口；
2. 唯一的网络管理器、时间同步服务、桌面/显示协议选择；
3. 实际 GPU 驱动、声音栈和是否启用蓝牙；
4. 需要开机运行的 systemd units 与理由；
5. 监听端口清单与防火墙允许范围；
6. 官方包、foreign/AUR 包的更新路径；
7. 备份目的地、保留策略、最近一次恢复测试日期；
8. 正常内核、备用内核/fallback、ESP 挂载点和 live ISO/chroot 骨架；
9. 每周和每月 SOP 的实际执行日期；
10. 一条精确、可逆的变更实验，例如按需启用再停用蓝牙服务，并记录前后 `systemctl status`。

### 成功标准

- 你能解释每个启用服务和监听端口的用途。
- `sudo -l`、`timedatectl status`、网络、挂载和 `systemctl --failed` 的结果可解释。
- 能明确说出 `pacman -Syu` 与 `pacman -Sy` 的差异。
- 能用自己的话说明 AUR helper 为什么不能替代 PKGBUILD 审阅。
- 能从备份恢复一个测试文件，而不覆盖原文件。
- 能指出备用内核、fallback initramfs 和 live ISO/chroot 分别解决哪一层故障。
- 清理练习只做查询和计划，不执行不可逆批量删除。

## 21. 恢复与重置速查

| 变更 | 先验收 | 失败时恢复 |
| --- | --- | --- |
| sudoers | 保持 root 会话；`visudo -c`；第二 TTY 测试 | 用仍开放的 root 会话修复，或 live ISO + chroot + `visudo` |
| 网络管理器切换 | 本地控制台；记录旧 unit 和配置 | 停用新管理器，重新启用旧管理器并恢复旧配置 |
| 显示管理器/桌面 | 保留 TTY；确认旧 unit | TTY 中 `disable --now` 新 unit，恢复旧 unit，查本次启动日志 |
| 防火墙 | 保存旧规则；离线语法检查；保留管理路径 | 从带外控制台恢复旧 `/etc/nftables.conf` 并重载 |
| SSH 加固 | 公钥已测试；保留旧会话和本地控制台 | 恢复 drop-in，`sshd -t` 后重启；锁死则本地/chroot 修复 |
| pacman 升级 | 备份、空间、News、安装介质 | 查 pacman.log；完成中断升级；必要时用缓存/快照/Arch Linux Archive 按完整依赖集恢复 |
| 内核/initramfs | 备用内核或 fallback 已测试 | 选备用启动项；否则 live ISO 挂载后 chroot，重装匹配内核并重建 initramfs |
| 快照回滚 | 明确包含哪些子卷/卷和是否含 `/boot` | 按文件系统工具恢复；个人数据仍从独立备份取回 |

## 22. ArchWiki 官方参考

本页只使用 ArchWiki 官方资料。页面会持续更新，执行高影响操作前应重新阅读对应章节：

- [General recommendations](https://wiki.archlinux.org/title/General_recommendations)
- [System maintenance](https://wiki.archlinux.org/title/System_maintenance)
- [Users and groups](https://wiki.archlinux.org/title/Users)
- [Sudo](https://wiki.archlinux.org/title/Sudo)
- [Security](https://wiki.archlinux.org/title/Security)
- [Network configuration](https://wiki.archlinux.org/title/Network_configuration)
- [Network configuration/Wireless](https://wiki.archlinux.org/title/Network_configuration/Wireless)
- [systemd-timesyncd](https://wiki.archlinux.org/title/Systemd-timesyncd)
- [System time](https://wiki.archlinux.org/title/System_time)
- [Xorg](https://wiki.archlinux.org/title/Xorg)
- [Wayland](https://wiki.archlinux.org/title/Wayland)
- [Desktop environment](https://wiki.archlinux.org/title/Desktop_environment)
- [NVIDIA](https://wiki.archlinux.org/title/NVIDIA)
- [Sound system](https://wiki.archlinux.org/title/Sound_system)
- [PipeWire](https://wiki.archlinux.org/title/PipeWire)
- [Bluetooth](https://wiki.archlinux.org/title/Bluetooth)
- [Fonts](https://wiki.archlinux.org/title/Fonts)
- [Input method](https://wiki.archlinux.org/title/Input_method)
- [Fcitx5](https://wiki.archlinux.org/title/Fcitx5)
- [IBus](https://wiki.archlinux.org/title/IBus)
- [pacman](https://wiki.archlinux.org/title/Pacman)
- [pacman/Pacnew and Pacsave](https://wiki.archlinux.org/title/Pacman/Pacnew_and_Pacsave)
- [pacman/Package signing](https://wiki.archlinux.org/title/Pacman/Package_signing)
- [Mirrors](https://wiki.archlinux.org/title/Mirrors)
- [Arch User Repository](https://wiki.archlinux.org/title/Arch_User_Repository)
- [systemd](https://wiki.archlinux.org/title/Systemd)
- [systemd/Journal](https://wiki.archlinux.org/title/Systemd/Journal)
- [nftables](https://wiki.archlinux.org/title/Nftables)
- [OpenSSH](https://wiki.archlinux.org/title/OpenSSH)
- [System backup](https://wiki.archlinux.org/title/System_backup)
- [Synchronization and backup programs](https://wiki.archlinux.org/title/Synchronization_and_backup_programs)
- [LVM](https://wiki.archlinux.org/title/LVM#Snapshots)
- [Mkinitcpio](https://wiki.archlinux.org/title/Mkinitcpio)
- [Chroot](https://wiki.archlinux.org/title/Chroot)
- [arch-chroot(8)](https://man.archlinux.org/man/arch-chroot.8)
- [General troubleshooting](https://wiki.archlinux.org/title/General_troubleshooting)
- [Downgrading packages](https://wiki.archlinux.org/title/Downgrading_packages)
- [Arch Linux Archive](https://wiki.archlinux.org/title/Arch_Linux_Archive)

## 导航

- 上一站：[[计算机知识/20-操作系统/01-Linux/12-ArchLinux安装实战|Arch Linux 安装实战]]
- 下一站：[[计算机知识/20-操作系统/01-Linux/14-Linux开发容器与AI工作负载边界|Linux 开发容器与 AI 工作负载边界]] · 实验室：[[计算机知识/80-实践/02-Linux/00-Linux实验室|Linux 实验室]]
- 返回：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/13-Linux-课程地图|Linux · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/01-Linux/16-服务资源容器与分层故障定位|Linux 深化：服务、资源、容器与分层排障]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/20-操作系统/01-Linux/10-系统课程/08-安全备份运维与综合实验|Linux 运维全景：把恢复能力当成系统功能]]
- [[计算机知识/20-操作系统/01-Linux/10-系统课程/02-文件描述符管道与进程控制|Linux 进程与文件描述符：用小实验理解共享状态]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
