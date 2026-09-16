---
type: lesson
domain: computer-science
stage: 12
status: ready
difficulty: 进阶
estimated_minutes: 150
topics:
  - Linux
  - Arch Linux
  - UEFI
  - GPT
  - systemd-boot
  - 系统安装
tags:
  - computer-science/linux
  - computer-science/arch-linux
---

# 12 · Arch Linux 安装实战

## 本课目标

完成本课后，你将能够：

1. 在虚拟机里沿 Arch 官方 Installation guide 的顺序完成一次手动安装；
2. 分清 live ISO、挂载到 `/mnt` 的目标系统和 `arch-chroot` 内部这三种系统执行上下文；
3. 在任何写盘操作前，用设备属性、分区视图和手工复述做三次独立核对；
4. 安装基础系统，生成并审查 `fstab`，配置本地化、账户、网络、initramfs 和引导器；
5. 用 systemd-boot 启动一个 UEFI/GPT/ext4 系统，并在失败时回到 live ISO 修复，而不是立刻重装；
6. 说清 `archinstall` 能自动化什么，以及它不能替你承担哪些判断。

> [!info] 现场核对与主线
> 本页在 **2026-09-01** 现场核对英文版 [ArchWiki Installation guide](https://wiki.archlinux.org/title/Installation_guide)。下面的阶段顺序以它为唯一主线；页面只在官方指南要求“自行选择”的位置，为教学虚拟机固定一组容易恢复的选择。Arch 是滚动发行版，真正安装时仍应重新打开官方页面核对命令和说明。

## 本课固定场景与不覆盖的场景

本课使用一台**可随时恢复快照的空白虚拟机**：

- x86_64；
- UEFI 启动，关闭 Secure Boot；
- 一块专供练习的空白虚拟磁盘，建议至少 32 GiB；
- GPT 分区表；
- 1 GiB EFI System Partition（ESP），挂载为 `/boot`；
- 其余空间为 ext4 根分区 `/`；
- 暂不建立独立 `/home`、磁盘 swap、LVM、RAID、LUKS、双系统或 Secure Boot；
- 使用官方 `linux` 内核、NetworkManager 和 systemd-boot。

这是一条用于理解安装链的最小路径，不是所有机器的通用答案。以下情况应先返回 [[计算机知识/20-操作系统/01-Linux/11-ArchLinux安装前规划|Arch Linux 安装前规划]]，再跟对应的官方专题页设计：

- 真实机器上保留数据或与 Windows/macOS 双启动；
- 已经存在 ESP；
- 全盘加密、LVM、RAID、Btrfs 子卷或休眠；
- 32 位 UEFI、Legacy BIOS/CSM、特殊存储控制器；
- 需要 Secure Boot、统一内核镜像（UKI）或厂商专有驱动。

> [!danger] 本课不授权写入真实磁盘
> 页面中的设备名始终是空变量或说明性占位符，不把 `/dev/vda`、`/dev/sda`、`/dev/nvme0n1` 等常见示例冒充成你的设备。只有你亲自在当前 live 环境识别并填写的路径，才可以进入写盘阶段。真实机器若没有已验证备份，不要用本页做第一次练习。

## 先看懂三个系统执行上下文

| 系统执行上下文 | 如何识别 | 主要工作 | 常见误区 |
| --- | --- | --- | --- |
| live ISO | 提示符通常是 root，根文件系统含 `airootfs` | 识别硬件、联网、分区、格式化、挂载、`pacstrap` | 以为 live ISO 的网络和时区会自动复制到新系统 |
| 目标树 `/mnt` | `findmnt -R /mnt` 能看到根分区与 ESP | 新系统尚未启动时的文件树 | 把 `/boot` 和 `/mnt/boot` 混为一谈 |
| `arch-chroot -S /mnt` 内 | `/` 已经是新系统，`cat /etc/arch-release` 存在 | 配置新系统、账户、服务、initramfs、引导器 | 在 chroot 中仍给路径加 `/mnt` 前缀 |

每次执行命令前都先问：“我现在在哪一层？”不确定时运行：

```bash
findmnt /
findmnt /mnt 2>/dev/null
cat /etc/arch-release
```

## 阶段 1：进入 live ISO，确认键盘、UEFI、网络与时钟

### 1.1 确认以 UEFI 模式启动

Arch 安装镜像当前不支持直接以 Secure Boot 启动；本课先在虚拟机固件里关闭 Secure Boot。进入 live 系统后检查 UEFI 位数：

```bash
cat /sys/firmware/efi/fw_platform_size
```

- 输出 `64`：本课所需的 x64 UEFI 模式；
- 输出 `32`：是 IA32 UEFI，能选的引导器受限，本课不继续；
- 报 `No such file or directory`：可能以 BIOS/CSM 模式启动，本课不继续。

不要因为虚拟机设置里勾选过“EFI”就跳过现场检查；安装介质实际以什么模式启动，决定引导器能否写入 EFI 变量。

### 1.2 键盘布局

live 环境默认是 US 键盘。先列出可用布局，再按实际键盘选择；不确定就保留默认：

```bash
localectl list-keymaps | less
```

需要修改时，把 `KEYMAP_NAME` 手工替换为列表中真实存在的名字，再单独运行：

```bash
loadkeys KEYMAP_NAME
```

先实际输入 `/`、`-`、`_`、`:` 和数字，确认键位与屏幕一致。错误键盘布局会让密码和设备路径看起来“莫名其妙地不对”。

### 1.3 联网

先观察接口，而不是猜接口名：

```bash
ip link
rfkill
```

- 虚拟机的模拟有线网卡通常由 live ISO 的 systemd-networkd 自动取得 DHCP 地址；
- Wi-Fi 使用 `iwctl` 交互连接；
- 若被 `rfkill` 阻止，先查清软/硬开关原因；
- 本页不展开静态 IP、WWAN 或企业认证网络。

验证 IP 路由和 DNS：

```bash
ip address
ip route
ping -c 3 ping.archlinux.org
```

### 1.4 时钟

联网后，live ISO 默认启用 systemd-timesyncd。检查：

```bash
timedatectl
```

应看到系统时钟已经同步。准确时间是软件包签名和 TLS 证书校验的前提，不要把签名失败直接归咎于镜像站。

> [!success] 阶段 1 成功标准
> `fw_platform_size` 输出 `64`；关键符号能按预期输入；`ping.archlinux.org` 可解析并收到响应；`timedatectl` 显示时钟已同步。

> [!tip] 阶段 1 回退点
> 此时还没有改目标磁盘。任何一项不满足，都可以关机，修正虚拟机 UEFI、网络或键盘设置，再从 ISO 重启。不要带着不确定性进入分区阶段。

## 阶段 2：只读识别磁盘，并完成三次核对

先做虚拟机快照，例如命名为“Arch-写盘前”。快照是这次练习最清晰的恢复边界，但它不能替代真实机器的数据备份。

### 2.1 罗列证据

以下命令都是只读的：

```bash
lsblk -e 7 -o NAME,PATH,SIZE,TYPE,FSTYPE,FSVER,MOUNTPOINTS,MODEL,SERIAL
fdisk -l
findmnt -no SOURCE /run/archiso/bootmnt 2>/dev/null
```

忽略 `rom`、`loop`、`airootfs`，也不要把承载 ISO 的设备当目标磁盘。记录目标虚拟磁盘的**路径、容量、型号/序列号、当前分区**四项证据。

### 2.2 建立空变量，禁止把示例设备名直接填进去

先复制的只能是这三个空变量：

```bash
TARGET_DISK=''
ESP_PART=''
ROOT_PART=''
```

根据刚才的真实输出，手工填写。例如名为 `TARGET_DISK` 的变量必须是整块磁盘，另外两个必须是其分区；这里故意不提供任何可直接沿用的设备值。

### 2.3 三次独立核对

**第一次：核对物理/虚拟身份。**

```bash
lsblk -d -o PATH,SIZE,MODEL,SERIAL,TYPE "$TARGET_DISK"
```

目标必须是预期容量和型号的 `disk`，不是 `part`，也不是安装介质。

**第二次：核对完整分区视图。**

```bash
fdisk -l "$TARGET_DISK"
lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINTS "$TARGET_DISK"
```

逐行解释输出。如果出现任何需要保留的数据、已有操作系统或不认识的分区，停止本课。

**第三次：手工复述目标路径。** 下面只验证，不执行任何写盘命令：

```bash
CONFIRMED_DISK=''
printf '请重新手工输入目标整盘路径，再给 CONFIRMED_DISK 赋值。\n'
test -n "$TARGET_DISK" && test -b "$TARGET_DISK" && test "$CONFIRMED_DISK" = "$TARGET_DISK"
```

把 `CONFIRMED_DISK` 重新手工填写为你眼前确认的路径。最后一条命令返回 0 才算第三次核对通过；它不证明选择正确，只证明两次独立输入一致。

> [!success] 阶段 2 成功标准
> 你能不用“应该是”来解释目标磁盘的路径、容量、型号/序列号和现有内容；三次核对均通过；写盘前快照已创建。

> [!tip] 阶段 2 回退点
> 还没有写盘。变量为空、输出不一致或任何一行看不懂时，运行 `poweroff` 并回到规划页。不要用“试一下”来确认磁盘身份。

## 阶段 3：危险区——分区与格式化

> [!danger] 从这里开始会破坏数据
> 本节只适用于本课的**空白练习虚拟磁盘**。不要全选复制本节。每个动作都要在读完说明、再次查看设备输出后单独运行。对既有 ESP 执行 `mkfs.fat` 会摧毁其他系统的引导文件；双系统必须跳出本课重新规划。

### 3.1 交互式建立 GPT 和两个分区

再次确认变量非空并显示目标：

```bash
test -n "$TARGET_DISK" && test -b "$TARGET_DISK"
lsblk -d -o PATH,SIZE,MODEL,SERIAL,TYPE "$TARGET_DISK"
```

确认无误后，**只单独运行**分区工具：

```bash
fdisk "$TARGET_DISK"
```

在 `fdisk` 中完成以下意图，而不是照抄一串按键：

1. 对空盘建立 GPT 分区表；
2. 建立约 1 GiB 的 EFI System Partition，并把类型设为 `EFI System`；
3. 用剩余空间建立 Linux x86-64 root `/` 分区；
4. 用 `p` 打印最终布局，逐项核对起止位置、大小和类型；
5. 只有最终布局完全正确才用 `w` 写入；任何不确定都用 `q` 不保存退出。

这样设计是为了让你阅读当前版本工具给出的提示；一串可无脑粘贴的交互按键会绕过最关键的人工确认。

写入后重新扫描并观察：

```bash
udevadm settle
lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,PARTTYPENAME "$TARGET_DISK"
```

此时才把两个**实际分区路径**分别填入 `ESP_PART` 与 `ROOT_PART`。路径规则会随磁盘类型变化，不能靠给整盘路径末尾盲加数字。

### 3.2 格式化前再设一道门

先把三个路径解析为当前启动中的真实块设备，并让门禁证明两个分区确实属于刚才确认的目标整盘。ESP 的 GPT 类型 GUID 必须是标准 EFI System Partition；只看到一个有效块设备路径还不够。

```bash
FORMAT_GATE='closed'
FORMAT_EXPECTED=''
TARGET_DISK_REAL=$(readlink -f -- "$TARGET_DISK")
ESP_PART_REAL=$(readlink -f -- "$ESP_PART")
ROOT_PART_REAL=$(readlink -f -- "$ROOT_PART")
ESP_TYPE_GUID='c12a7328-f81f-11d2-ba4b-00a0c93ec93b'

if test -n "$TARGET_DISK_REAL" && test -b "$TARGET_DISK_REAL" && \
   test "$(lsblk -ndo TYPE "$TARGET_DISK_REAL")" = disk && \
   test -n "$ESP_PART_REAL" && test -b "$ESP_PART_REAL" && \
   test "$(lsblk -ndo TYPE "$ESP_PART_REAL")" = part && \
   test -n "$ROOT_PART_REAL" && test -b "$ROOT_PART_REAL" && \
   test "$(lsblk -ndo TYPE "$ROOT_PART_REAL")" = part && \
   test "$ESP_PART_REAL" != "$ROOT_PART_REAL" && \
   test "$(readlink -f -- "/dev/$(lsblk -ndo PKNAME "$ESP_PART_REAL")")" = "$TARGET_DISK_REAL" && \
   test "$(readlink -f -- "/dev/$(lsblk -ndo PKNAME "$ROOT_PART_REAL")")" = "$TARGET_DISK_REAL" && \
   test "$(lsblk -ndo PARTTYPE "$ESP_PART_REAL" | tr '[:upper:]' '[:lower:]')" = "$ESP_TYPE_GUID"
then
  lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,PARTTYPE,PARTTYPENAME "$TARGET_DISK_REAL"
  blkid "$ESP_PART_REAL" "$ROOT_PART_REAL" 2>/dev/null
  FORMAT_EXPECTED="FORMAT $ESP_PART_REAL AND $ROOT_PART_REAL ON $TARGET_DISK_REAL"
  printf '逐字输入以下确认句才会解锁后续格式化：\n%s\n' "$FORMAT_EXPECTED"
  read -r FORMAT_CONFIRMATION
  if test "$FORMAT_CONFIRMATION" = "$FORMAT_EXPECTED"; then
    FORMAT_GATE="approved:$FORMAT_EXPECTED"
  else
    printf '确认句不匹配：格式化门禁保持关闭。\n' >&2
  fi
else
  printf '设备归属、设备类型或 ESP 类型检查失败：格式化门禁保持关闭。\n' >&2
fi

test "$FORMAT_GATE" = "approved:$FORMAT_EXPECTED"
```

你必须人工阅读刚显示的完整树，并能指出：哪个是约 1 GiB 的 ESP，哪个是较大的 root，两者的父盘为何都是 `TARGET_DISK_REAL`。若 `blkid` 显示已有文件系统而你不知道来源，或最后的 `test` 没有成功，不要格式化。不要通过手工伪造 `FORMAT_GATE` 绕过检查；变量只是把同一轮检查结果绑定到后续命令，不是磁盘身份的替代品。

对本课刚创建、确认无数据的 **ESP**，单独运行：

```bash
test "$FORMAT_GATE" = "approved:$FORMAT_EXPECTED" && \
  test "$(readlink -f -- "$ESP_PART")" = "$ESP_PART_REAL" && \
  mkfs.fat -F 32 "$ESP_PART_REAL"
```

回到 `lsblk -f` 检查 ESP 成为 `vfat`，再对本课刚创建、确认无数据的 **root** 单独运行：

```bash
test "$FORMAT_GATE" = "approved:$FORMAT_EXPECTED" && \
  test "$(readlink -f -- "$ROOT_PART")" = "$ROOT_PART_REAL" && \
  mkfs.ext4 "$ROOT_PART_REAL"
```

本课不创建 swap 分区。官方指南允许之后使用 swap file 或 zram；若规划中确实选择了 swap 分区，必须另开一轮设备确认后再按官方 `mkswap`/`swapon` 文档操作，不能把 root 分区误当 swap。

```bash
lsblk -f "$TARGET_DISK"
```

> [!success] 阶段 3 成功标准
> 分区表是 GPT；ESP 的分区类型为 EFI System 且文件系统为 FAT32/vfat；root 分区为 ext4；两者路径、大小和 UUID 清楚可辨。

> [!tip] 阶段 3 回退点
> `fdisk` 写入前可用 `q` 无保存退出。写入分区表或执行 `mkfs` 后，数据恢复不再可靠；本练习应关机并恢复“写盘前”虚拟机快照。真实磁盘不要继续尝试修补，应停止写入并按备份/数据恢复方案处理。

## 阶段 4：挂载目标文件系统

先挂 root，再在其内部挂 ESP；层级顺序很重要：

```bash
mount "$ROOT_PART" /mnt
mount --mkdir "$ESP_PART" /mnt/boot
```

核对挂载源、文件系统和层级：

```bash
findmnt -R /mnt
lsblk -f "$TARGET_DISK"
```

这里的 `/mnt/boot` 将在 chroot 里表现为 `/boot`。systemd-boot 只能直接读取 ESP 或 XBOOTLDR 上的内核、initramfs 和入口文件，因此本课选择把 ESP 挂到 `/boot`。

> [!success] 阶段 4 成功标准
> root 的 ext4 分区挂在 `/mnt`，ESP 的 vfat 分区挂在 `/mnt/boot`；没有把两者反过来，也没有多余目标挂载。

> [!tip] 阶段 4 回退点
> 若挂错，尚未安装前可运行 `umount -R /mnt`，重新核对变量后再按层级挂载。不要在挂错的目录树上运行 `pacstrap`。

## 阶段 5：镜像站与 `pacstrap`

live ISO 中所有 HTTPS 镜像当前默认启用，最上方的全球镜像通常足够。先检查，不需要为了“优化”而加入未知第三方源：

```bash
sed -n '1,40p' /etc/pacman.d/mirrorlist
```

本课在官方最小包集上加入控制台编辑器、文档、`sudo` 与一种明确选择的网络管理器：

```bash
pacstrap -K /mnt base linux linux-firmware nano man-db man-pages texinfo sudo networkmanager
```

选择说明：

- `base` 是唯一强制的基础包；它不包含 live ISO 里的全部工具；
- `linux` 提供本课使用的官方内核；
- `linux-firmware` 提供由 Linux 内核加载的网卡、显卡、存储控制器等**设备 firmware**；它不是主板的 UEFI/BIOS 固件，也不会替你更新机器固件。纯虚拟机通常可省略，但保留它便于之后把练习迁移到常规硬件；设备、驱动、内核模块与 firmware 的层次见 [[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备驱动、内核模块与 udev]]；
- `nano`、`man-db`、`man-pages`、`texinfo` 让新系统能编辑配置和查本机文档；
- `sudo`、`networkmanager` 是本课为后续账户与网络选定的实现，不是 Installation guide 强制指定的唯一方案；
- 物理 CPU 的 microcode 稍后按厂商单选；虚拟机不安装 guest microcode。

确认目标系统确实写入 `/mnt`：

```bash
test -f /mnt/etc/arch-release
arch-chroot /mnt pacman -Q base linux sudo networkmanager
```

> [!success] 阶段 5 成功标准
> `pacstrap` 无未处理错误；`/mnt/etc/arch-release` 存在；目标系统能查询到 `base`、`linux`、`sudo` 和 `networkmanager`。

> [!tip] 阶段 5 回退点
> 下载中断通常可在确认挂载仍正确后重跑 `pacstrap`。若包被写到错误分区，立刻停止，卸载 `/mnt` 并修正挂载；不要靠移动整个系统目录补救。

## 阶段 6：生成 `fstab`，然后进入 chroot

先预览将要生成的内容：

```bash
genfstab -U /mnt
```

逐行确认 `/` 与 `/boot` 的 UUID 和文件系统与 `lsblk -f` 一致。确认 `/mnt/etc/fstab` 仍为空或不存在后，**只生成一次**：

```bash
test ! -s /mnt/etc/fstab && genfstab -U /mnt >> /mnt/etc/fstab
```

`>>` 重复运行会追加重复条目，所以写后只读检查，不再生成：

```bash
sed -n '1,200p' /mnt/etc/fstab
findmnt --verify --tab-file /mnt/etc/fstab
```

当前官方指南使用：

```bash
arch-chroot -S /mnt
```

`-S` 对当前 systemd-boot 安装流程很重要：它让 chroot 使用 systemd 相关的集成，使 `bootctl` 能正确处理 EFI 变量。进入后，后续路径都以新系统的 `/` 为根，不再写 `/mnt/etc/...`。

> [!success] 阶段 6 成功标准
> `fstab` 只有一组预期条目且验证无错误；进入 chroot 后 `findmnt /` 指向目标 root，`findmnt /boot` 指向 ESP，`cat /etc/arch-release` 成功。

> [!tip] 阶段 6 回退点
> `fstab` 写错时，在 reboot 前用编辑器修正并重新验证，不要重复追加。chroot 配置遇到问题可 `exit` 回 live 环境；只要挂载仍正确，就能再次 `arch-chroot -S /mnt`。

## 阶段 7：时区、locale、控制台与主机名

以下命令开始都在 **chroot 内**执行。

### 7.1 时区与硬件时钟

先浏览 `/usr/share/zoneinfo/`，把空变量设为真实存在的 `Area/Location`：

```bash
TIME_ZONE_NAME=''
test -n "$TIME_ZONE_NAME" && \
  test -e "/usr/share/zoneinfo/$TIME_ZONE_NAME" && \
  ln -sf "/usr/share/zoneinfo/$TIME_ZONE_NAME" /etc/localtime && \
  hwclock --systohc && \
  readlink /etc/localtime
```

`hwclock --systohc` 按官方主线假设硬件时钟使用 UTC。时钟持续同步要由已安装系统的 NTP 客户端负责；本课使用 systemd 自带的 systemd-timesyncd，并让它在首次启动时随系统启用：

```bash
systemctl enable systemd-timesyncd.service
systemctl is-enabled systemd-timesyncd.service
```

### 7.2 locale 与控制台键盘

编辑 `/etc/locale.gen`，至少取消注释一个你要使用的 UTF-8 locale，例如：

```text
en_US.UTF-8 UTF-8
```

需要中文 locale 时可以同时启用 `zh_CN.UTF-8 UTF-8`，但 locale 不会自动安装中文字体或输入法。生成：

```bash
locale-gen
```

创建 `/etc/locale.conf`，其中 `LANG` 必须与刚生成的 locale 一致：

```text
LANG=en_US.UTF-8
```

如果 live 阶段改过控制台键盘布局，把同一个真实键盘布局持久化到 `/etc/vconsole.conf`：

```text
KEYMAP=KEYMAP_NAME
```

### 7.3 主机名

选择 1–63 个小写字母、数字或连字符组成的名字；不能以连字符开头。创建 `/etc/hostname`，只写一行，例如用你自己的 VM 名替换下列占位符：

```text
your-host-name
```

检查配置文件：

```bash
locale -a
cat /etc/locale.conf
cat /etc/hostname
```

> [!success] 阶段 7 成功标准
> `/etc/localtime` 指向存在的 zoneinfo 文件；systemd-timesyncd 已启用；`locale -a` 包含选定 locale；`locale.conf`、可选的 `vconsole.conf` 和 `hostname` 没有未替换占位符。

> [!tip] 阶段 7 回退点
> 这些都是可逆的配置文件。reboot 前可重新编辑、运行 `locale-gen` 与 `hwclock --systohc`；不要为了修正 locale 重做分区或 `pacstrap`。

## 阶段 8：root、普通用户与 sudo

先为 root 设置一个当前会话不会显示的强密码：

```bash
passwd
```

再为普通用户准备一个空变量，手工填写符合本机命名规则的用户名：

```bash
NEW_USER_NAME=''
USER_ACCOUNT_GATE='closed'

if [[ "$NEW_USER_NAME" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] && \
   ! getent passwd "$NEW_USER_NAME" >/dev/null
then
  if useradd -m -G wheel -s /bin/bash "$NEW_USER_NAME" && \
     passwd "$NEW_USER_NAME" && \
     id "$NEW_USER_NAME"
  then
    USER_ACCOUNT_GATE="created:$NEW_USER_NAME"
  else
    printf '账户创建、密码设置或身份核对失败：停止，不进入 sudo 配置。\n' >&2
    false
  fi
else
  printf '用户名为空、格式非法或账户已经存在：停止，不运行 useradd/passwd。\n' >&2
  false
fi

test "$USER_ACCOUNT_GATE" = "created:$NEW_USER_NAME"
```

本课采用一个有意收紧的练习规则：用户名为 1–32 个字符，以小写字母或下划线开头，后续只含小写字母、数字、下划线或连字符。已有账户不能由这段流程“顺便修改”。若 `useradd` 已成功而后面的密码或身份核对失败，账户可能已经部分创建；保持 root 会话，先用 `getent passwd "$NEW_USER_NAME"` 和 `id "$NEW_USER_NAME"` 取证并明确修复或清理，再从头核对，不得手工伪造 `USER_ACCOUNT_GATE`。

只通过 `visudo` 编辑 sudoers，取消下面这一行前的注释：

```text
%wheel ALL=(ALL:ALL) ALL
```

执行：

```bash
if test "$USER_ACCOUNT_GATE" = "created:$NEW_USER_NAME" && \
   EDITOR=nano visudo && \
   visudo -c && \
   sudo -l -U "$NEW_USER_NAME"
then
  printf '普通用户与 sudo 配置门禁通过。\n'
else
  printf '普通用户或 sudo 配置门禁失败：停止，不锁定 root。\n' >&2
  false
fi
```

不要把密码写进脚本、笔记、命令历史或安装配置。root 账户在本课保留为救援路径；安装后若要锁定 root，必须先证明普通用户的 sudo 和救援方式都可用。

> [!success] 阶段 8 成功标准
> root 与普通用户密码已分别设置；普通用户有 home 目录并属于 `wheel`；`visudo -c` 报配置有效；`sudo -l -U` 显示该用户有预期授权。

> [!tip] 阶段 8 回退点
> reboot 前可用 `passwd` 重设密码、用 `usermod -aG wheel` 修正组成员、用 `visudo` 修正规则。不要直接用普通编辑器覆盖 `/etc/sudoers`，也不要在 sudo 尚未验证前锁定 root。

## 阶段 9：microcode 与 initramfs

先判断当前是不是虚拟机：

```bash
systemd-detect-virt
```

- 在虚拟机或容器中，microcode 属于宿主机，guest **不安装** `intel-ucode` 或 `amd-ucode`；
- 在物理机上，先用 `lscpu` 确认厂商，只安装一个匹配包：Intel 对应 `intel-ucode`，AMD 对应 `amd-ucode`；不要两个都盲装。

物理机按确认的厂商，二选一单独执行：

```bash
pacman -S intel-ucode
```

或：

```bash
pacman -S amd-ucode
```

默认 `mkinitcpio` 的 `microcode` hook 会把可用 microcode 合并进 initramfs；加密、LVM、RAID 等场景则需要先按各自官方页面调整 `/etc/mkinitcpio.conf`。

当前 mkinitcpio 默认 preset 只生成 default image，不会自动生成本课后面要使用的 fallback image。为了让现有门禁和 systemd-boot fallback 入口真实成立，先**只编辑现有 preset 中的对应赋值**，不要用下面的片段覆盖整个文件，也不要改动其中的 `ALL_kver` 等内核包配置：

```bash
nano /etc/mkinitcpio.d/linux.preset
```

确认该文件中以下四个有效赋值各只有一处；原来带 `#` 的 fallback 行需要取消注释并按当前写法设置：

```bash
PRESETS=('default' 'fallback')
default_image="/boot/initramfs-linux.img"
fallback_image="/boot/initramfs-linux-fallback.img"
fallback_options="--skiphooks autodetect"
```

这里的 fallback 跳过 `autodetect`，会包含更广的模块，镜像通常也更大。保存后先读回精确值；四项必须全部匹配才继续：

```bash
grep -Fx "PRESETS=('default' 'fallback')" /etc/mkinitcpio.d/linux.preset && \
  grep -Fx 'default_image="/boot/initramfs-linux.img"' /etc/mkinitcpio.d/linux.preset && \
  grep -Fx 'fallback_image="/boot/initramfs-linux-fallback.img"' /etc/mkinitcpio.d/linux.preset && \
  grep -Fx 'fallback_options="--skiphooks autodetect"' /etc/mkinitcpio.d/linux.preset
```

本课未使用堆叠设备；preset 核对通过后，重新生成其中明确启用的 default 与 fallback images：

```bash
mkinitcpio -P
```

检查内核和两个 initramfs 文件：

```bash
test -s /boot/vmlinuz-linux
test -s /boot/initramfs-linux.img
test -s /boot/initramfs-linux-fallback.img
```

物理机还可验证合并的早期 microcode 内容：

```bash
lsinitcpio --early /boot/initramfs-linux.img | grep microcode
```

若改用不会合并 microcode 的生成器，systemd-boot 入口必须把单独的 `amd-ucode.img` 或 `intel-ucode.img` 放在普通 initramfs **之前**；本课不要混用两种方式。

> [!success] 阶段 9 成功标准
> `mkinitcpio -P` 无未处理错误；内核、正常 initramfs 和 fallback initramfs 均非空；物理机的厂商包选择正确且能看到早期 microcode，虚拟机明确跳过 guest microcode。

> [!tip] 阶段 9 回退点
> `mkinitcpio` 失败时不要 reboot。保留 fallback 镜像，修正报错指出的 hook、模块或缺包后重跑。默认配置不需要为了“优化”先删 hook。

## 阶段 10：为已安装系统启用网络

live ISO 的 systemd-networkd、systemd-resolved、iwd 等预配置不会自动变成新系统的网络方案。本课已经安装 NetworkManager，只启用这一套管理器：

```bash
systemctl enable NetworkManager.service
systemctl is-enabled NetworkManager.service
```

重启后，虚拟有线网卡通常会通过 DHCP 自动联网。Wi-Fi 可以登录后用 `nmtui` 交互配置，避免把密码直接放在命令历史中。

不要同时启用 NetworkManager、systemd-networkd、dhcpcd 等多个管理器去争用同一接口。若你选择 systemd-networkd 或 iwd，应完整跟它们的官方页面配置 DHCP、无线认证与 DNS，而不是只替换一条 enable 命令。

> [!success] 阶段 10 成功标准
> `systemctl is-enabled NetworkManager.service` 输出 `enabled`，并且没有为同一接口配置第二套网络管理器。

> [!tip] 阶段 10 回退点
> 还未重启时可用 `systemctl disable NetworkManager.service` 撤销启用，再完整配置另一方案。首启无网不等于安装损坏，可从本机控制台修复，或回 live ISO chroot 后补装/启用服务。

## 阶段 11：UEFI 主线——systemd-boot

Installation guide 要求选择适合分区方案的引导器，并转到其专页。针对本课的 x64 UEFI、ESP 挂载于 `/boot` 的场景，选择 systemd-boot。

### 11.1 安装 EFI boot manager

先检查条件，不满足就停止：

```bash
cat /sys/firmware/efi/fw_platform_size
findmnt /boot
test -d /sys/firmware/efi/efivars
```

确认 ESP 确实挂在 `/boot` 后：

```bash
bootctl install
```

本课使用前面的 `arch-chroot -S /mnt`，因为当前 systemd-boot 官方页指出普通非 systemd chroot 中 `bootctl` 会避免操作 EFI 变量。`bootctl install` 还会写 EFI fallback 路径；在已有多系统的真实 ESP 上可能覆盖该位置，因此本课只对空白 VM 执行。

### 11.2 取得 root UUID

```bash
findmnt -no UUID /
blkid
```

把 `/` 对应的 UUID 手工记录为 `ROOT_UUID_FROM_FINDMNT`。不要使用易随启动顺序变化的 `/dev/sdXn` 作为长期 root 参数，也不要把 ESP 的 UUID 写成 root UUID。

### 11.3 创建 loader 配置和启动入口

用编辑器创建 `/boot/loader/loader.conf`：

```text
default arch.conf
timeout 3
console-mode keep
editor no
```

创建 `/boot/loader/entries/arch.conf`，把最后一行的占位符替换成刚才真实取得的 root UUID：

```text
title   Arch Linux
linux   /vmlinuz-linux
initrd  /initramfs-linux.img
options root=UUID=ROOT_UUID_FROM_FINDMNT rw
```

再创建 `/boot/loader/entries/arch-fallback.conf`：

```text
title   Arch Linux (fallback initramfs)
linux   /vmlinuz-linux
initrd  /initramfs-linux-fallback.img
options root=UUID=ROOT_UUID_FROM_FINDMNT rw
```

路径以 ESP 根目录为基准：因为 ESP 挂到 `/boot`，文件 `/boot/vmlinuz-linux` 在入口中写作 `/vmlinuz-linux`。

检查不能残留占位符：

```bash
if ! test -s /boot/loader/loader.conf || \
   ! test -s /boot/loader/entries/arch.conf || \
   ! test -s /boot/loader/entries/arch-fallback.conf
then
  printf '错误：必需的 loader 配置或启动入口不存在/为空，停止。\n' >&2
  false
elif grep -q 'ROOT_UUID_FROM_FINDMNT' \
     /boot/loader/loader.conf \
     /boot/loader/entries/arch.conf \
     /boot/loader/entries/arch-fallback.conf
then
  printf '错误：仍有未替换的 root UUID 占位符，停止。\n' >&2
  false
else
  printf 'loader 必需文件存在且 root UUID 占位符检查通过。\n'
  bootctl status
  bootctl list
fi
```

这里使用默认 mkinitcpio 合并 microcode，所以入口只有一个 `initrd`。只有已经确认生成单独 microcode image 时，才按 [Microcode 官方页](https://wiki.archlinux.org/title/Microcode) 把对应 microcode `initrd` 放在普通 initramfs 前面。

### GRUB 分支：只给官方入口，不混抄命令

若你实际以 BIOS 启动、使用 systemd-boot 不支持的布局，或经规划决定采用 GRUB，请停止本页的引导器步骤，转到：

- [Arch boot process：Boot loader 选择](https://wiki.archlinux.org/title/Arch_boot_process#Boot_loader)
- [ArchWiki GRUB](https://wiki.archlinux.org/title/GRUB)

GRUB 的 UEFI、BIOS、Secure Boot、加密与文件系统组合会改变安装命令。本页不把另一套引导器命令混入可复制主线，也不要同时安装两套后再猜固件会选谁。

> [!success] 阶段 11 成功标准
> `bootctl status` 识别已安装的 systemd-boot 和正确 ESP；`bootctl list` 能列出正常与 fallback 入口；两个入口使用真实 root UUID；内核与 initramfs 文件均存在于入口可访问的 `/boot`。

> [!tip] 阶段 11 回退点
> 入口文件写错时先留在 chroot 内修正；`bootctl list` 未通过就不要 reboot。若首启失败，可再次以 UEFI 模式启动 ISO、重新挂载 root 与 ESP、执行 `arch-chroot -S /mnt`，再修正 loader 文件或重跑 `bootctl install`。

## 阶段 12：离开 chroot、卸载并重启

### 12.1 最终门禁

仍在 chroot 内逐项确认：

```bash
findmnt /
findmnt /boot
cat /etc/hostname
cat /etc/locale.conf
visudo -c
systemctl is-enabled NetworkManager.service
systemctl is-enabled systemd-timesyncd.service
bootctl list
pacman -Q linux
```

再检查没有遗留本页的关键占位符：

```bash
PLACEHOLDER_CHECK_FILES=(
  /etc/hostname
  /etc/locale.conf
  /boot/loader/loader.conf
  /boot/loader/entries/arch.conf
  /boot/loader/entries/arch-fallback.conf
)

if test -e /etc/vconsole.conf; then
  PLACEHOLDER_CHECK_FILES+=(/etc/vconsole.conf)
fi

if ! test -s /etc/hostname || \
   ! test -s /etc/locale.conf || \
   ! test -s /boot/loader/loader.conf || \
   ! test -s /boot/loader/entries/arch.conf || \
   ! test -s /boot/loader/entries/arch-fallback.conf || \
   { test -e /etc/vconsole.conf && ! test -s /etc/vconsole.conf; }
then
  printf '错误：必需配置不存在/为空，或已创建的 vconsole.conf 为空，停止。\n' >&2
  false
elif grep -qE 'ROOT_UUID_FROM_FINDMNT|KEYMAP_NAME|your-host-name' \
     "${PLACEHOLDER_CHECK_FILES[@]}"
then
  printf '错误：关键配置仍含占位符，停止。\n' >&2
  false
else
  printf '必需配置存在且关键占位符检查通过。\n'
fi
```

只有最后的显式“检查通过”分支才允许继续退出 chroot。`KEYMAP_NAME` 只在你确实创建了 `vconsole.conf` 时检查；未创建该可选文件不构成错误，但一旦创建就不得为空。

### 12.2 退出与卸载

离开 chroot：

```bash
exit
```

回到 live 环境后，先同步写入并尝试正常卸载：

```bash
sync
umount -R /mnt
```

若报告 `busy`，不要用强制或 lazy unmount 掩盖问题。先找出占用者：

```bash
fuser -vm /mnt
```

关闭仍在 `/mnt` 下工作的 shell 或进程，再正常卸载。确认 `findmnt /mnt` 无输出后重启：

```bash
reboot
```

虚拟机开始重启后，弹出 ISO 或把虚拟磁盘放到启动顺序前面；不要在文件系统仍挂载时直接强制断电。

> [!success] 阶段 12 成功标准
> 最终门禁全部通过；已离开 chroot；`/mnt` 正常卸载；虚拟机从目标虚拟磁盘进入 systemd-boot，而不是再次进入安装 ISO。

> [!tip] 阶段 12 回退点
> 在运行 `reboot` 前，任何检查失败都可以重新挂载并进入 chroot 修正。若重启后没看到入口，先检查固件启动顺序和 ISO 是否仍优先，不要马上重新分区。

## 阶段 13：第一次启动验证

用普通用户登录，按从身份到启动、文件系统、权限、服务、网络的顺序检查：

```bash
id
sudo -v
uname -r
cat /etc/os-release
findmnt /
findmnt /boot
bootctl status
systemctl --failed
systemctl status NetworkManager.service --no-pager
ip address
ip route
ping -c 3 ping.archlinux.org
timedatectl
```

物理机再检查早期 microcode 记录：

```bash
journalctl -k --grep=microcode
```

不要把“能看到登录提示”当成完整成功。至少还要证明：

- 普通用户能通过自己的密码使用 sudo；
- 内核版本来自已安装系统；
- `/` 与 `/boot` 挂载源符合 `fstab`；
- systemd-boot 的当前入口可识别；
- `systemctl --failed` 没有与本次安装相关的失败单元；
- IP、默认路由、DNS 与时间同步可用。

> [!success] 阶段 13 成功标准
> 上述六类证据均成立，并且重新再启动一次仍能进入同一个系统。此时才删除“写盘前”快照之前的临时安装状态；建议保留一个“基础系统首启成功”快照，进入下一课。

> [!tip] 阶段 13 回退点
> 若系统进不了登录界面，从 ISO **以 UEFI 模式**启动，重新识别分区并只挂载，不格式化：root → `/mnt`，ESP → `/mnt/boot`，然后 `arch-chroot -S /mnt`。先只读取证：检查 `fstab`、`/etc/mkinitcpio.conf`、`/etc/mkinitcpio.d/linux.preset`、`/boot` 中现有内核与 initramfs、loader UUID、`bootctl list` 和网络服务。`mkinitcpio -P` 会重写 initramfs，不是例行检查；只有证据指向 initramfs 配置或文件有误、已经完成相应修正并确认 Live ISO 恢复入口可用时才重新生成。能修复配置时不重装；只有确认磁盘布局本身错误且愿意恢复快照时，才回到写盘前状态重做。

## 一张故障定位表

| 现象 | 先取证 | 最可能的层 | 不要先做 |
| --- | --- | --- | --- |
| 又进入安装 ISO | 固件启动顺序、ISO 是否仍挂载 | 虚拟机/固件 | 重新格式化 |
| 没有 systemd-boot 菜单 | `bootctl status`、EFI 启动项、ESP 挂载点 | UEFI/boot manager | 改 root 文件系统 |
| 菜单有入口但找不到 root | loader 的 `root=UUID=`、`blkid`、`fstab` | kernel 参数/文件系统 | 反复 `bootctl install` |
| 掉进 emergency shell | initramfs 报错、`journalctl -xb`、`findmnt` | initramfs/fstab | 删除日志或 fallback 镜像 |
| 能登录但无网络 | `ip link`、`ip route`、服务状态、DNS | 网络管理器 | 同时启用多个管理器 |
| 普通用户不能 sudo | `id`、`visudo -c`、`sudo -l -U` | 账户/授权 | 锁定 root |

## `archinstall` 与手动安装的边界

`archinstall` 是 Arch 官方镜像中提供的自动化辅助库和 guided installer。它可以询问或接收磁盘布局、账户、引导器、网络和 profile 等配置，然后执行大量本页的机械步骤；在最新官方 ISO 中可直接运行 `archinstall`。它不是另一种发行版，也不是“不需要理解磁盘”的安全按钮。

适合使用 `archinstall` 的情况：

- 已经理解本页每个阶段，想在新的空白 VM 上快速重复一个已审查布局；
- 愿意在执行前逐项审查 disk configuration、bootloader、网络和账户设置；
- 能保留并在求助时提供 `/var/log/archinstall/install.log`；
- 接受它可能使用与手动 Installation guide 不同的默认值。

仍应选择手动安装或先停止规划的情况：

- 第一次学习 UEFI、挂载、`fstab`、initramfs 与启动链；
- 双系统、已有 ESP、加密、复杂存储或数据保留；
- 无法独立判断界面里显示的目标磁盘；
- 把 profile 当作软件包维护者承诺的配置；官方明确说明 archinstall profiles 是其自身配置，不由各包维护者支持。

官方还特别警告：archinstall 的手动分区界面不会替你防止分区重叠、未对齐或末分区覆盖 GPT 备份头。guided 并不等于“磁盘选择自动安全”。可以先运行：

```bash
archinstall --dry-run
```

它会模拟流程并保存配置而不执行永久写入，适合学习菜单和审查答案；密码等敏感数据应使用单独的 credentials 机制，不能写进普通配置、Vault 或版本控制。不要在已经做完一半的手动流程中途改跑 archinstall：恢复到干净快照后，选择一种完整路径。

## 练习与验收

### 练习 A：口述启动链

不看命令，用自己的话解释：

```text
UEFI 固件
  → systemd-boot EFI 程序
  → arch.conf
  → vmlinuz-linux + initramfs
  → root=UUID=...
  → 挂载根文件系统
  → systemd 启动用户空间与网络服务
```

### 练习 B：做一次非破坏性救援演练

在“基础系统首启成功”快照上：

1. 从 ISO 以 UEFI 模式启动；
2. 只用 `lsblk -f` 识别 root 和 ESP；
3. 按层级挂载到 `/mnt` 与 `/mnt/boot`；
4. 用 `arch-chroot -S /mnt` 进入并执行 `bootctl list`；
5. 退出并正常卸载；
6. 不运行 `fdisk`、`mkfs`、`pacstrap`，不修改任何文件。

这项练习证明你拥有“修复入口”，而不只是记住一次性安装命令。

### 完成清单

- [ ] 我使用空白 VM，并有写盘前快照；
- [ ] 我能区分 live ISO、`/mnt` 与 chroot；
- [ ] 三次磁盘核对都有独立证据；
- [ ] 我没有把页面示例设备名当作实际设备；
- [ ] `fstab` 使用持久标识且无重复条目；
- [ ] 普通用户、sudo、initramfs、网络与 systemd-boot 都有验证证据；
- [ ] 我能从 ISO 重新挂载并进入目标系统；
- [ ] 我知道 `archinstall` 自动化执行，但不替代布局判断、备份和验收。

## 横向连接

- [[计算机知识/20-操作系统/01-Linux/02-启动链Kernel与systemd|启动链：Kernel 与 systemd]]：理解固件、内核、initramfs、PID 1 和服务启动之间的关系。
- [[计算机知识/20-操作系统/01-Linux/03-目录结构挂载与文件系统|目录结构、挂载与文件系统]]：理解为什么先挂 root，再把 ESP 挂到 `/mnt/boot`，以及 `fstab` 如何复现层级。
- [[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备驱动、内核模块与 udev]]：安装后遇到磁盘、网卡或显卡不可用时，从固件、驱动、模块与设备事件分层定位。

## 官方参考

- [ArchWiki Installation guide](https://wiki.archlinux.org/title/Installation_guide)（本页唯一安装主线，2026-09-01 现场核对）
- [systemd-boot](https://wiki.archlinux.org/title/Systemd-boot)
- [Microcode](https://wiki.archlinux.org/title/Microcode)
- [Network configuration](https://wiki.archlinux.org/title/Network_configuration)
- [Arch boot process](https://wiki.archlinux.org/title/Arch_boot_process)
- [GRUB](https://wiki.archlinux.org/title/GRUB)（分支，不与本课命令混用）
- [archinstall](https://wiki.archlinux.org/title/Archinstall)
- [archinstall Guided installation](https://archinstall.archlinux.page/installing/guided.html)

## 导航

- 上一站：[[计算机知识/20-操作系统/01-Linux/11-ArchLinux安装前规划|Arch Linux 安装前规划]]
- 下一站：[[计算机知识/20-操作系统/01-Linux/13-ArchLinux安装后配置维护与安全|Arch Linux 安装后配置、维护与安全]]
- 返回：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/13-Linux-课程地图|Linux · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/01-Linux/16-服务资源容器与分层故障定位|Linux 深化：服务、资源、容器与分层排障]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/20-操作系统/01-Linux/10-系统课程/02-文件描述符管道与进程控制|Linux 进程与文件描述符：用小实验理解共享状态]]
- [[计算机知识/20-操作系统/01-Linux/10-系统课程/03-权限身份与最小授权|Linux 权限：文件能不能删，为什么不只看文件写位]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
