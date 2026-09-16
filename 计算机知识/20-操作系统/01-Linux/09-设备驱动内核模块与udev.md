---
type: lesson
domain: computer-science
stage: 9
status: ready
difficulty: 入门
estimated_minutes: 55
topics:
  - Linux
  - 设备驱动
  - 内核模块
  - udev
  - firmware
  - DKMS
tags:
  - computer-science/linux
  - computer-science/kernel
  - computer-science/hardware
---

# 09 · 设备驱动、内核模块与 udev

> 上一站：[[计算机知识/20-操作系统/01-Linux/08-pacman-apt-dnf与yum包管理|08 · pacman、apt、dnf 与 yum 包管理]] ｜下一站：[[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|10 · 网络、存储、日志与故障排查]] ｜返回：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础 MOC]]

## 本课目标

学完本课，你应该能够：

1. 从硬件、总线、内核驱动、设备接口、udev 一直追到用户态程序，而不是把“驱动”当成一个不透明安装包；
2. 区分编入内核的驱动与可加载模块，理解模块别名、依赖、参数和 firmware 各解决什么问题；
3. 用 `lspci -k`、`lsusb`、`lsmod`、`modinfo`、`modprobe` 的只读模式、内核日志和 `udevadm` 收集一条完整证据链；
4. 解释 `/dev`、`/sys`、`/proc` 的不同角色，以及“没有 `/dev` 节点”为什么不一定代表没有设备；
5. 判断 DKMS、匹配的 kernel headers、initramfs 和模块签名分别在什么时候相关；
6. 在 GPU、Wi-Fi、存储或输入设备故障时，先保留可启动状态，再做单一、可恢复的变更。

> [!warning] 本课只观察，不改驱动状态
> 本页不提供直接加载、卸载、blacklist、改写 udev 规则或安装第三方驱动的命令。卸载正在承载根文件系统、图形桌面、网络连接或输入设备的驱动，可能立刻造成 I/O 错误、黑屏、断网或失去键盘；blacklist 进入 initramfs 后还可能让下一次启动找不到根设备。任何真实变更都应先确认精确硬件 ID、当前绑定、启动依赖和恢复入口。

## 1. 主链：从一块硬件到用户态程序

先建立这一条主链：

```text
hardware
  物理或虚拟设备
      ↓ 被某种连接方式枚举
bus
  PCI / USB / platform / ACPI / I²C / SPI / virtio ...
      ↓ 设备 ID 或兼容信息与驱动匹配，驱动 probe
kernel driver
  控制设备、处理中断/DMA/电源管理，可能请求 firmware
      ↓ 注册面向用户态的接口
device interface
  /dev 节点、网络接口、sysfs 属性、socket/ioctl/mmap 等
      ↓ 内核发出 uevent；设备管理器补充命名、权限、符号链接
udev / systemd-udevd
      ↓ 用户态库、守护进程与应用打开或管理这些接口
userspace
  Mesa/Vulkan、NetworkManager/iwd、文件系统与 mount、libinput/桌面等
```

这不是“每层必定生成一个文件”的流水线：

- PCI、USB 等总线负责发现设备，并按总线自己的 ID 规则寻找可支持它的驱动；匹配后，内核调用驱动的 `probe`。驱动成功绑定的结果可在 sysfs 的设备、总线和驱动关系中观察。
- **驱动不等于设备节点。** 网络接口常显示在 `/sys/class/net`，但通常没有 `/dev/eth0`；GPU、输入和存储则常有不同类型的 `/dev` 节点。
- 现代系统的 `/dev` 通常以 devtmpfs 提供内核已注册设备的基础节点，udev 再依据内核事件管理权限、所有者、附加符号链接和部分命名。把所有节点都简单说成“udev 凭空创建”并不准确。
- 有了驱动和节点也只证明链条走到某一层。Wi-Fi 仍可能缺少认证或网络配置，磁盘仍可能没有可挂载文件系统，GPU 仍可能缺少匹配的用户态图形栈。

### 设备 ID 如何找到候选驱动

以 PCI 为例，一块设备会携带 vendor、device、subsystem、class 等标识。驱动模块会声明一组可匹配的 alias；系统可把设备在 sysfs 暴露的 `modalias` 交给模块工具，解析出候选模块。USB 也采用类似思想，但 ID 格式和匹配语义属于 USB 总线。

```text
设备的 modalias
      ↓ 与模块元数据里的 alias 匹配
候选模块
      ↓ 处理依赖并请求内核装入
驱动注册到对应 bus
      ↓ ID 匹配、probe 成功
设备 ↔ 驱动绑定
```

“候选模块”不等于“当前正在使用的驱动”。对 PCI 设备，`lspci -k` 输出中的 `Kernel driver in use` 才是当前绑定证据；`Kernel modules` 更接近可处理该设备的候选列表。

## 2. built-in 与 loadable module

Linux 驱动代码可以直接编进内核映像，也可以构建为 `.ko` 可加载模块。二者运行后都在内核态，权限和崩溃影响没有“插件比较安全”的区别。

| 维度 | built-in：编入内核 | module：可加载模块 |
| --- | --- | --- |
| 何时可用 | 内核启动时已经存在 | 可由启动流程或运行时按需装入 |
| 磁盘形态 | 不需要当前内核目录中的独立 `.ko` 才能运行 | 通常位于 `/lib/modules/<kernel-release>/` 下，可能被压缩 |
| `lsmod` | 通常不列出 | 已加载时列出 |
| `modinfo` | 未必能按普通 `.ko` 方式查询；取决于内核构建产物和发行版提供的元数据 | 可读取 license、alias、depends、firmware、参数、签名和 vermagic 等字段 |
| 卸载 | 不能作为模块卸载 | 只有内核支持卸载、引用计数与驱动状态允许时才可能卸载；“可能”不等于“应该” |
| initramfs | 驱动本体无需作为 `.ko` 放入 initramfs；但早期请求的 firmware 仍可能需要在那里 | 若挂载根文件系统前就要用到，模块及其依赖/firmware 需要在 early userspace 可用 |

> [!important] `lsmod` 没看见，不代表驱动不存在
> 可能原因至少包括：驱动编入内核、设备尚未触发加载、你查错了模块名、驱动已被另一个模块提供，或设备根本未被总线枚举。先看总线枚举和绑定关系，再解释 `lsmod`。

### 模块的关键元数据

假设已经从 `lspci -k`、`lsusb -t` 或 sysfs 找到模块名。下面的变量默认为空；只有明确填入已核对的模块名才会执行只读查询：

```bash
MODULE_NAME=""
if printf '%s\n' "$MODULE_NAME" | grep -Eq '^[A-Za-z0-9_.+:-]+$'; then
  modinfo "$MODULE_NAME"
  modinfo -F filename "$MODULE_NAME"
  modinfo -F alias "$MODULE_NAME"
  modinfo -F depends "$MODULE_NAME"
  modinfo -F firmware "$MODULE_NAME"
  modinfo -F parm "$MODULE_NAME"
  modinfo -F vermagic "$MODULE_NAME"
  modinfo -F signer "$MODULE_NAME"
else
  printf '%s\n' '请先把 MODULE_NAME 设置为已从 lspci/lsusb/sysfs 核对的模块名；未执行查询。'
fi
```

这些字段应这样理解：

- `alias`：可让哪些硬件或逻辑别名解析到这个模块；同一模块通常有许多 alias。
- `depends`：装入本模块前需要的其他模块。`depmod` 生成 `/lib/modules/<version>/modules.dep.bin`，`modprobe` 使用它解析依赖；不要手工编辑依赖数据库。
- `firmware`：驱动可能向内核 firmware loader 请求的设备固件文件名。它不是另一个内核模块，也不等于主板上的 UEFI 固件。
- `parm`：模块参数名、类型和说明。参数可能影响探测和行为，但仅看到参数名不足以证明某个值适合本机。
- `vermagic`：模块构建目标的内核版本/构建特征线索。它可帮助发现“模块为另一个内核构建”的问题，但最终能否加载仍由内核校验与日志决定。
- `signer`：签名者字段。空值可能表示没有可显示的签名；非空只证明模块带有相关元数据，**不证明当前内核一定信任该签名**。

当前已加载模块可以这样观察：

```bash
lsmod
cat /proc/modules
```

`lsmod` 只是把 `/proc/modules` 格式化为更易读的表格。`Used by`/引用计数可提示依赖关系，但不能作为“计数为零就可安全卸载”的保证：驱动可能管理现实中的设备、控制台或正在变化的状态。

### `modprobe` 在这里用只读预演

普通 `modprobe MODULE_NAME` 会请求改变内核运行状态，本课不执行。以下模式用于观察解析结果而不真正加载；变量默认为空，且只允许 dry-run/show 模式：

```bash
MODULE_NAME=""
MODALIAS=""
if printf '%s\n' "$MODULE_NAME" | grep -Eq '^[A-Za-z0-9_.+:-]+$'; then
  modprobe --show-depends "$MODULE_NAME"
  modprobe --dry-run --verbose "$MODULE_NAME"
else
  printf '%s\n' '未执行 modprobe 预演：MODULE_NAME 为空或包含不安全字符。'
fi
MODALIAS_SAFE=0
case "$MODALIAS" in *' '*|*$'\t'*) ;; *) MODALIAS_SAFE=1 ;; esac
if [ -n "$MODALIAS" ] && [ "$MODALIAS_SAFE" -eq 1 ]; then
  modprobe --show-alias "$MODALIAS"
else
  printf '%s\n' '未执行 alias 预演：请先填入从 sysfs 读取的 MODALIAS。'
fi
```

- `--show-alias` 显示某个 modalias 可解析到哪些模块；把 alias 放在引号中，避免其中字符被 shell 解释。旧资料可能写兼容名称 `--resolve-alias`，当前 kmod 手册已把后者标为将移除的拼法。
- `--show-depends` 显示预期的依赖/操作序列。
- `--dry-run --verbose` 显示普通请求会采取的动作，但不执行。

预演仍要结合 `modinfo`、`/etc/modprobe.d/` 与发行版生成的配置理解。看到一条解析结果，不授权你照着执行真实加载、blacklist 或卸载。

## 3. firmware：驱动代码之外的设备程序

许多 Wi-Fi、GPU、蓝牙、存储控制器等设备在初始化时还需要一段 firmware。常见流程是：

```text
驱动 probe
  ↓ request_firmware("某个文件名")
内核 firmware loader 查找 built-in/cache/文件系统等来源
  ↓
驱动把得到的二进制交给设备
  ↓
设备完成初始化
```

常见的根文件系统查找位置位于 `/lib/firmware` 及其版本化/更新目录，但 usr merge 的系统可能让路径最终指向 `/usr/lib/firmware`。应以本机与发行版布局为准，不凭另一个发行版的包名猜测。

缺少 firmware 时，可能出现以下组合：

- 总线仍能枚举硬件；
- 驱动可能已经绑定或部分初始化；
- `/dev` 节点或网络接口可能存在，也可能没有；
- 真正解释失败原因的文字出现在内核日志，如 requested firmware、failed to load、timeout 等。

因此不要看到 Wi-Fi 不工作就立即换驱动，也不要看到一条“missing firmware”就安装互联网上的任意二进制。先把**请求的精确文件名、驱动名、硬件 ID、当前内核、启动阶段**一起保存，再查发行版官方包所提供的文件。

> [!note] built-in 驱动也可能依赖 initramfs 中的 firmware
> 如果编入内核的驱动在真实根文件系统挂载前就请求 firmware，仅把文件放在晚些时候才可访问的根文件系统可能发生时序竞争。内核文档建议把这种早期需要的 firmware 放入 initramfs。built-in 只省去了 `.ko`，没有自动把外部 firmware 变成内核的一部分。

## 4. `/dev`、`/sys` 与 `/proc` 各回答什么

| 路径 | 本质 | 对驱动排错最有价值的问题 | 注意 |
| --- | --- | --- | --- |
| `/dev` | 设备特殊文件所在的运行时层级；字符/块节点用 major:minor 连接到内核接口 | 用户态应打开哪个节点？权限与稳定符号链接是什么？ | 节点不是设备数据的普通副本；网络接口等设备不一定有节点。名称如 `/dev/sda` 也不适合作永久身份。 |
| `/sys` | sysfs：内核对象、设备树、总线、类、驱动和属性的视图 | 内核枚举了什么？设备挂在哪条总线？绑定到哪个驱动？modalias 和类是什么？ | 不少属性可写；本课只读。路径内部细节并非都保证长期稳定，优先使用 udev 等抽象。 |
| `/proc` | procfs：进程与部分系统/内核运行状态的视图 | 哪些模块已加载？当前内核/进程状态是什么？ | 不是硬件拓扑的主要数据库；`/proc/modules` 只覆盖已加载模块。 |

### 用 sysfs 证明绑定关系

PCI 设备地址通常类似 `0000:03:00.0`。把已由 `lspci -D` 核对的地址填入变量；默认空值会阻止查询：

```bash
PCI_ADDRESS=""
PCI_PATH="/sys/bus/pci/devices/$PCI_ADDRESS"
if printf '%s\n' "$PCI_ADDRESS" | grep -Eq '^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]$' && [ -d "$PCI_PATH" ]; then
  readlink -f "$PCI_PATH"
  if [ -e "$PCI_PATH/driver" ]; then readlink -f "$PCI_PATH/driver"; fi
  cat "$PCI_PATH/modalias"
  udevadm info --query=all --path="$PCI_PATH"
  udevadm info --attribute-walk --path="$PCI_PATH"
else
  printf '%s\n' '未执行 sysfs 查询：PCI_ADDRESS 为空、格式不符或设备目录不存在。'
fi
```

- 设备目录存在：内核的 PCI 层已经枚举它。
- `driver` 符号链接存在：当前有驱动绑定；链接目标名称是强证据。
- 没有 `driver` 链接：只说明当前没有绑定，不自动说明硬件坏了，也不说明应该强制加载某个候选模块。
- `modalias`：可用于上节的 `modprobe --show-alias` 只读解析。
- `udevadm info`：显示 udev 数据库属性；`--attribute-walk` 还沿父设备链展示可用于理解规则匹配的 sysfs 属性。

对一个已经知道的设备节点，可从 `/dev` 反向追到设备：

```bash
DEVICE_NODE=""
case "$DEVICE_NODE" in
  /dev/*)
    if [ -e "$DEVICE_NODE" ]; then
  udevadm info --query=all --name="$DEVICE_NODE"
  udevadm info --query=path --name="$DEVICE_NODE"
    else
      printf '%s\n' '未执行设备节点查询：DEVICE_NODE 必须是已存在的 /dev 路径。'
    fi
    ;;
  *)
  printf '%s\n' '未执行设备节点查询：DEVICE_NODE 必须是已存在的 /dev 路径。'
    ;;
esac
```

`udevadm monitor` 可同时观察内核 uevent 与 udev 处理后的事件：

```bash
udevadm monitor --kernel --udev --property
```

运行后再插入一个**不含唯一重要数据**的普通 USB 设备，观察完按 `Ctrl-C` 退出。monitor 只观察事件；不要在生产远程会话中随意拔插网卡、存储或安全令牌。

## 5. 一组只读命令，分别看不同层

### PCI：`lspci -k`

```bash
lspci -Dnnk
```

- `-D` 显示完整 domain:bus:device.function 地址，便于与 sysfs 对齐；
- `-nn` 同时显示人类名称和数字 vendor/device ID，避免名称数据库缺失时丢失证据；
- `-k` 显示当前使用的内核驱动与候选模块。

对 GPU、PCIe Wi-Fi、NVMe 控制器和以太网控制器，这通常是第一条命令。普通用户对部分 PCI 配置空间的读取可能受限，但基础枚举通常仍可用。

### USB：`lsusb`

```bash
lsusb
lsusb -t
```

第一条列出 USB bus/device 与 vendor:product ID；树状输出可展示端口层级、接口 class、速度和已绑定的 `Driver=`。USB 设备可能有多个 interface，每个 interface 可以由不同驱动处理，所以“整个 USB 设备只有一个驱动”并非总是成立。

### 模块：`lsmod`、`modinfo`、`modprobe`

```bash
lsmod
MODULE_NAME=""
if printf '%s\n' "$MODULE_NAME" | grep -Eq '^[A-Za-z0-9_.+:-]+$'; then
  modinfo "$MODULE_NAME"
  modprobe --dry-run --verbose "$MODULE_NAME"
else
  printf '%s\n' '未执行模块查询或预演：MODULE_NAME 为空或包含不安全字符。'
fi
```

它们依次回答：“哪些可加载模块现在已加载？”、“磁盘上的这个模块声明了什么？”、“按当前别名、依赖与配置解析，请求它时预计做什么？”三者不能互相替代。

### 内核日志：`dmesg` 与 `journalctl -k`

```bash
dmesg --ctime --level=err,warn
journalctl -k -b
journalctl -k -b -1
```

- `dmesg` 读取内核 ring buffer；某些系统限制普通用户读取，权限错误本身不是驱动坏了。
- `journalctl -k -b` 读取当前启动的 kernel transport 记录；`-b -1` 看上一次启动，适合“更新后本次失败、上次正常”的对照。只有 journal 持久保存了对应启动记录时，历史才存在。
- 日志里的时间顺序很重要：先出现 device ID，随后是哪一个 driver probe、请求了哪个 firmware、为何超时或拒绝。不要只截取最后一行错误。

### udev：`udevadm`

```bash
udevadm info --query=all --path=/sys/class/net/lo
udevadm monitor --kernel --udev --property
```

第一条用普遍存在的 loopback 接口演示属性查询；它不是物理硬件练习的最终目标。第二条区分 kernel event 与 udev event，能帮助定位“内核根本没发事件”还是“udev 处理后名称/权限不符合预期”。

## 6. 四个设备例子：同一主链，不同用户态接口

### GPU：驱动绑定不等于图形栈完整

```text
PCI GPU
  → amdgpu / i915 / nouveau / nvidia 等内核驱动之一
  → /dev/dri/card*、/dev/dri/renderD* 与 sysfs DRM 类
  → udev 设置节点权限/符号链接
  → Mesa、Vulkan/OpenGL 实现、显示服务器/合成器或计算运行时
```

先用 `lspci -Dnnk` 确认硬件 ID 和 `Kernel driver in use`，再看 kernel log 是否有 firmware、签名、probe 或 GPU reset 错误。桌面黑屏也可能发生在用户态库版本、显示管理器、显示协议或配置层；不要仅凭 `lsmod` 看到模块就宣布 GPU 正常。

用于计算的 GPU 还要经过 CUDA/ROCm 等用户态运行时、进程权限和实际工作负载验证。`lspci` 的驱动绑定、`/dev/dri` 节点存在，或某条 GPU 信息命令能运行，都不足以证明 C++/Python 程序已经能完成一次计算；不要为了让检测“通过”而重装驱动、切换 kernel、手工加载模块或把用户加入未知权限组。后续按“内核驱动 → 用户态运行时 → 最小程序 → 真实模型”的分层证据见 [[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]] 与 [[AI/20-LLM/40-推理/04-推理显存量化与硬件路线|推理显存、量化与硬件路线]]。

### Wi-Fi：驱动、firmware、射频与联网是四件事

```text
PCI/USB 无线设备
  → iwlwifi / ath* / brcmfmac / mt76 / rtw* 等驱动族
  → firmware 初始化设备
  → /sys/class/net/<interface>（通常没有 /dev/<interface>）
  → udev 命名；iwd/wpa_supplicant/NetworkManager 等用户态组件
  → 认证、地址、路由、DNS
```

`lspci -k` 或 `lsusb -t` 能证明枚举/绑定，日志能证明 firmware 与初始化，`/sys/class/net` 能证明网络接口注册；它们都不能单独证明接入点密码、DHCP、路由或 DNS 正常。

### 存储：控制器、块设备、文件系统、挂载仍是不同层

```text
NVMe / SATA / USB 存储硬件
  → PCI/USB 控制器驱动与块层
  → /dev/nvme0n1、/dev/sdX 等块节点
  → udev 提供 /dev/disk/by-id、by-uuid 等符号链接
  → 分区/文件系统驱动
  → mount 后成为目录树的一部分
```

USB 外置盘还可能经过 `usb-storage` 或 UAS/SCSI 层，设备名也可能因发现顺序变化。排错时保留 vendor:product、序列/WWN（若可靠）、sysfs 路径与 `/dev/disk/by-*` 映射；不要把当前的 `/dev/sdX` 字母当作永久身份。

存储驱动尤其不适合尝试卸载：根文件系统、swap、日志或正在写入的数据可能依赖它。先确认挂载与启动链，再讨论任何变化。

### 输入设备：一个物理设备可能产生多个 event 节点

```text
USB / 蓝牙 / 内建键盘、鼠标、触控板
  → HID/总线驱动与 input subsystem
  → /dev/input/event* 等节点
  → udev 权限和属性
  → libinput、桌面合成器或应用
```

多功能键盘可能同时暴露键盘、媒体键、触控板等多个 interface/event 节点。`lsusb -t`、`udevadm info` 和内核日志负责解释设备链；“应用收不到按键”还可能是会话权限、桌面输入栈或应用层问题。不要为了测试而卸载当前唯一键盘的驱动。

## 7. DKMS 与 kernel headers：只与外部模块构建相关

内核源码树之外的模块必须针对目标内核构建。内核 kbuild 文档明确要求目标内核的配置和 headers/build artifacts；发行版通常把这些放在与每个内核版本对应的 headers/devel 包中。

**DKMS（Dynamic Kernel Module Support）**保存外部模块源码，并在安装新内核时尝试为新内核重建模块。它解决“内核升级后重新构建”这件事，不保证：

- 模块源码兼容新内核 API/ABI；
- 构建过程一定成功；
- 新模块已被正确放进需要的 initramfs；
- Secure Boot/lockdown 策略会信任它的签名；
- 用户态库与内核模块版本彼此匹配。

如果系统确实使用并安装了 DKMS，可进行下面的只读核对；`dkms` 命令不存在只说明这套框架未安装，不能据此判断硬件驱动故障：

```bash
uname -r
readlink -f "/lib/modules/$(uname -r)/build"
dkms status
MODULE_NAME=""
if printf '%s\n' "$MODULE_NAME" | grep -Eq '^[A-Za-z0-9_.+:-]+$'; then
  modinfo -F filename "$MODULE_NAME"
  modinfo -F vermagic "$MODULE_NAME"
  modinfo -F signer "$MODULE_NAME"
else
  printf '%s\n' '未执行模块元数据查询：MODULE_NAME 为空或包含不安全字符。'
fi
```

判断逻辑：

1. `uname -r` 是**当前正在运行**的内核；磁盘上刚安装的新内核可能不是它。
2. `/lib/modules/<release>/build` 应指向目标内核的有效构建/headers 目录。只安装“某个 headers”不够，版本和发行版内核变体要匹配。
3. `dkms status` 应显示模块对目标内核的构建/安装状态；成功字样之后仍要用目标内核启动并查看绑定与日志。
4. `vermagic` 或日志显示版本不匹配时，不要强制绕过校验。应回到模块源码版本、目标内核和 headers 的对应关系。

发行版内核自带的 in-tree 模块通常随内核包一起提供，不需要 DKMS。没有外部模块需求时，安装 DKMS 不会让硬件“自动获得更好的驱动”。

## 8. initramfs 何时与驱动相关

initramfs 是真实根文件系统挂载前运行的 early userspace。问题不在于“这是驱动，所以要不要放”，而在于：**挂载真实根之前是否必须使用它？**

它在完整开机顺序中的位置见 [[计算机知识/20-操作系统/01-Linux/02-启动链Kernel与systemd|启动链中的 kernel、modules 与 initramfs]]；本节只回答设备相关内容为何必须提前进入 early userspace。

常见需要提前可用的对象包括：

- 承载根文件系统的 NVMe/SATA/SCSI/virtio/USB 存储驱动；
- 根文件系统本身的文件系统驱动；
- dm-crypt、LVM、软件 RAID 等根存储栈及其用户态工具；
- 输入解密口令所需的 USB/HID/键盘驱动和键盘布局；
- 网络根文件系统所需的网卡驱动、firmware 与网络组件；
- 选择 early KMS 时的 GPU 驱动与 firmware。

通常不需要放入 initramfs 的情况是：设备只在真实根挂载后才使用，且它的模块、依赖和 firmware 此时已经可访问。例如一个启动完全不依赖的晚插 USB 设备，通常无需因为“它有驱动”就扩大 initramfs。

下面几类变更可能要求由**本发行版的 initramfs 工具/包管理钩子**重新生成镜像：

- 更换了 early-boot 驱动或 DKMS 模块；
- 更新了它在 early userspace 需要的 firmware；
- 修改了需要被收进镜像的模块配置；
- 改变了根存储、加密、RAID、LVM、文件系统或启动时输入方案。

mkinitcpio、dracut、initramfs-tools 等工具的配置、预设和恢复入口不同，本课不提供一条跨发行版“通用重建命令”。一个危险信号是：当前系统看似正常，但磁盘上的 initramfs 仍含旧模块或旧配置；这类问题往往只在**下一次重启**出现。

## 9. Secure Boot 与模块签名：证明谁签了，还要证明内核信谁

UEFI Secure Boot 验证启动链中的 EFI 二进制；Linux 的模块签名机制则由内核在模块加载时检查签名。发行版可能通过 shim、MOK、kernel lockdown 和内核配置把二者连成策略，但“固件界面显示 Secure Boot enabled”不能单独说明每个内核的模块强制策略细节。

模块签名的核心关系是：

```text
模块的完整内容
  → 私钥生成签名，签名附加到模块
  → 内核持有或导入相应的受信任公钥/证书
  → 加载时由内核验证
  → 策略决定：接受、拒绝，或接受但标记 taint
```

关键边界：

- “文件尾部有签名”不等于签名有效；内核文档明确说明，仅见签名标记不能证明验证成功。
- `modinfo -F signer <module>` 非空不等于当前内核信任该 signer。
- 在强制模式下，未签名、签名无法解析或公钥不受信任的外部模块可能被拒绝；实际错误应以本次启动的 kernel log 为准。
- DKMS 可以参与构建后签名，但密钥生成、私钥保护、公钥/MOK 注册和自动化方式都依赖发行版安全方案。不要下载陌生“关闭 Secure Boot/强制签名”的脚本，也不要把私钥放进公开仓库。

只读证据仍从这几处开始：

```bash
MODULE_NAME=""
if printf '%s\n' "$MODULE_NAME" | grep -Eq '^[A-Za-z0-9_.+:-]+$'; then
  modinfo -F signer "$MODULE_NAME"
  modinfo -F sig_id "$MODULE_NAME"
  modinfo -F sig_key "$MODULE_NAME"
else
  printf '%s\n' '未执行签名查询：MODULE_NAME 为空或包含不安全字符。'
fi
journalctl -k -b
dmesg --ctime --level=err,warn
```

关注 `verification`、`signature`、`required key`、`lockdown` 等上下文，但保留完整的前后日志与模块名；相同词语在不同内核版本/策略中可能代表不同阶段。

## 10. 排错证据顺序：从“看见硬件”到“应用能使用”

不要从搜索引擎里找到一个模块名就直接安装或 blacklist。按层收集证据，在哪一层第一次偏离预期，才在哪一层继续查。

下面是设备专用证据链；把它放回“现象 → 层次 → 证据 → 最小变更 → 回退”的通用方法时，参见 [[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|可回退的系统排错流程]]。

| 顺序 | 要回答的问题 | 主要证据 | 常见结论边界 |
| --- | --- | --- | --- |
| 0. 定义现象 | 从何时开始？冷启动、内核更新、睡眠恢复还是热插拔后？ | 时间、当前/上次内核版本、可重复步骤 | “设备坏了”不是可验证描述。 |
| 1. 总线枚举 | 内核能否看见精确硬件 ID？ | PCI：`lspci -Dnnk`；USB：`lsusb`、`lsusb -t` | 完全未枚举时，先看供电、连接、固件设置、虚拟机直通与总线日志。 |
| 2. 驱动绑定 | 当前到底绑定到谁？ | `Kernel driver in use`；sysfs 的 `driver` 链接 | 候选模块列表不等于已绑定。 |
| 3. 模块可用性 | 驱动是 built-in 还是 module？磁盘模块与内核是否匹配？ | `lsmod`、`modinfo`、`modprobe --dry-run --verbose` | `lsmod` 缺席不能否定 built-in。 |
| 4. probe 与 firmware | 绑定/初始化在哪一步失败？请求了哪个文件？ | `dmesg`、`journalctl -k -b` | 保存前后文，不只搜索一行 `error`。 |
| 5. 内核接口 | 设备类、节点或网络接口是否注册？ | `/sys/class`、`/sys/bus`、`/dev` | 没有 `/dev` 节点可能是该类设备本来不使用节点。 |
| 6. udev | kernel event 后，命名、权限、符号链接如何变化？ | `udevadm info`、`udevadm monitor` | udev 不能修复内核从未枚举/从未注册的设备。 |
| 7. 用户态 | 正确的库/守护进程/会话是否使用正确接口？ | 对应程序日志和状态 | 驱动已绑定不等于 Wi-Fi 已联网、GPU 已渲染或磁盘已挂载。 |
| 8. 启动差异 | 只在重启或新内核失败吗？ | `journalctl -k -b -1`、旧/新内核与 initramfs 对照 | 当前成功可能只是尚未使用磁盘上的新模块/镜像。 |

### 一份适合求助的最小证据包

在分享前删除主机名、序列号、MAC、WWN、用户名和其他不必要的唯一标识，然后保留：

1. 发行版与当前 kernel release；
2. 精确硬件 vendor:device 或 vendor:product ID；
3. 当前 `Kernel driver in use`/USB interface `Driver=`；
4. `modinfo` 的 filename、depends、firmware、vermagic、signer；
5. 故障发生时前后连续的 kernel log；
6. 对应 sysfs 路径、udev 属性和用户态接口是否存在；
7. 最近一次明确变更，以及旧内核/上次启动是否正常。

不要把完整 `lspci -vvxxx`、所有 udev 属性或整份 journal 不加审阅地发到公开场所；详细输出可能包含拓扑、序列号或其他设备标识。

## 11. 动手练习：追踪一个设备，但不改变它

选择一项当前不是你唯一网络、根存储、当前显示输出或唯一输入来源的设备。推荐用普通 USB 鼠标、USB 音频设备，或只观察一项 PCI 设备；不要拔插承载重要数据的存储。

### 步骤 A：确定总线与硬件 ID

- PCI 设备：运行 `lspci -Dnnk`，记下完整地址、vendor:device ID、`Kernel driver in use` 与 `Kernel modules`。
- USB 设备：运行 `lsusb` 和 `lsusb -t`，记下 bus/device、vendor:product ID、interface class 与 `Driver=`。

### 步骤 B：找到内核对象

PCI 设备把实际地址代入：

```bash
PCI_ADDRESS=""
PCI_PATH="/sys/bus/pci/devices/$PCI_ADDRESS"
if printf '%s\n' "$PCI_ADDRESS" | grep -Eq '^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]$' && [ -d "$PCI_PATH" ]; then
  readlink -f "$PCI_PATH"
  if [ -e "$PCI_PATH/driver" ]; then readlink -f "$PCI_PATH/driver"; fi
  cat "$PCI_PATH/modalias"
  udevadm info --query=all --path="$PCI_PATH"
else
  printf '%s\n' '未执行 sysfs 查询：PCI_ADDRESS 为空、格式不符或设备目录不存在。'
fi
```

USB 设备可以先从 `lsusb -t` 的 bus/port 层级和 `/sys/bus/usb/devices/` 对照；不确定哪个目录对应目标时，停在枚举证据，不要凭猜测写 sysfs。

### 步骤 C：查模块元数据

若已确定它是可加载模块 `<module>`：

```bash
lsmod
MODULE_NAME=""
if printf '%s\n' "$MODULE_NAME" | grep -Eq '^[A-Za-z0-9_.+:-]+$'; then
  modinfo -F filename "$MODULE_NAME"
  modinfo -F alias "$MODULE_NAME"
  modinfo -F depends "$MODULE_NAME"
  modinfo -F firmware "$MODULE_NAME"
  modinfo -F vermagic "$MODULE_NAME"
  modprobe --dry-run --verbose "$MODULE_NAME"
else
  printf '%s\n' '未执行模块查询或预演：MODULE_NAME 为空或包含不安全字符。'
fi
```

若 `lspci -k` 已显示 `Kernel driver in use`，但 `lsmod` 和 `modinfo` 都找不到同名模块，记录“可能是 built-in/元数据不可用”，不要把它改写成“没有驱动”。

### 步骤 D：按时间读日志

```bash
dmesg --ctime --level=err,warn
journalctl -k -b
```

如果目标是安全的热插拔 USB 设备，可先运行 `udevadm monitor --kernel --udev --property`，再拔插一次并按 `Ctrl-C`。把 kernel event 和 udev event 中相同的 DEVPATH/ID 对上。

### 成功标准

你完成练习时，应能给出一张不自相矛盾的“设备身份证”：

- [ ] 知道设备属于 PCI、USB 还是其他 bus，并保存精确数字 ID；
- [ ] 能指出总线枚举证据、当前绑定证据和 sysfs 路径；
- [ ] 能说明驱动是已加载 module、可能 built-in，还是当前未绑定，并写明判断依据；
- [ ] 若涉及 module，能解释至少一条 alias、dependency、firmware 或 vermagic 信息；
- [ ] 能指出它面向用户态的是 `/dev` 节点、网络接口还是其他接口；
- [ ] 能区分 kernel event 与 udev 处理结果；
- [ ] 没有执行真实 `modprobe` 加载、模块卸载、blacklist、规则改写或驱动安装；
- [ ] 没有把未审阅的序列号、MAC、WWN 或完整系统日志公开。

## 12. 变更前的恢复设计

本课练习没有持久改动，退出 monitor 或关闭终端即可结束。将来真的需要变更驱动时，先写出恢复路径，再动手：

1. **保留当前证据**：硬件 ID、绑定、模块文件、firmware 名、kernel release、日志与变更时间。
2. **确认启动依赖**：根存储、加密解锁键盘、当前 GPU、远程网络或唯一输入是否依赖目标驱动；只要答案不确定，就不要在线卸载或 blacklist。
3. **保留可启动入口**：不要先删除当前可工作的内核/initramfs；确认启动菜单中仍有旧内核或 fallback，准备与本机架构匹配的救援介质和解密凭据。
4. **一次只改一层**：驱动包、firmware、模块参数、udev 规则、initramfs、Secure Boot 信任不要同时改变。每一步记录前后 diff 和验证结果。
5. **重启前验证构建链**：外部模块的 DKMS 状态、目标 headers、vermagic、签名，以及需要时生成的 initramfs 都要对应将要启动的内核。
6. **失败时回退**：优先从启动菜单进入先前可工作的 kernel/fallback；若无法启动，使用救援介质挂载系统，撤销那一项已知变更或恢复先前镜像。不要在 emergency shell 中继续叠加来源不明的修复命令。

> [!danger] 三类“快捷修复”最容易扩大故障
> - 复制一条 `blacklist`，却没确认目标模块是否承载根存储、GPU 控制台或网络，并把错误配置打进 initramfs；
> - 强行卸载或重新绑定当前正在使用的驱动，以为“再加载一次就好”；
> - 运行厂商网站或论坛提供的整段 root 安装脚本，同时修改内核模块、用户态库、initramfs 和 Secure Boot 状态。
>
> 正确做法不是背另一条万能命令，而是回到本页的证据顺序，定位第一次偏离预期的层，再参考当前发行版与硬件厂商的正式支持路径设计最小变更。

## 延伸阅读（仅使用指定的一手文档范围）

### Linux kernel documentation

- [Driver Binding：设备、总线与驱动如何匹配和绑定](https://docs.kernel.org/driver-api/driver-model/binding.html)
- [Rules on how to access information in sysfs](https://docs.kernel.org/admin-guide/sysfs-rules.html)
- [Firmware lookup order](https://docs.kernel.org/driver-api/firmware/lookup-order.html) 与 [Direct filesystem lookup](https://docs.kernel.org/driver-api/firmware/direct-fs-lookup.html)
- [Building External Modules：kbuild、目标内核配置与 headers](https://docs.kernel.org/kbuild/modules.html)
- [Kernel module signing facility](https://docs.kernel.org/admin-guide/module-signing.html)

### man-pages 与上游工具手册

- [`sysfs(5)`](https://man7.org/linux/man-pages/man5/sysfs.5.html) 与 [`proc_modules(5)`](https://man7.org/linux/man-pages/man5/proc_modules.5.html)
- [`lsmod(8)`](https://man7.org/linux/man-pages/man8/lsmod.8.html)、[`modinfo(8)`](https://man7.org/linux/man-pages/man8/modinfo.8.html)、[`modprobe(8)`](https://man7.org/linux/man-pages/man8/modprobe.8.html) 与 [`modules.dep(5)`](https://man7.org/linux/man-pages/man5/modules.dep.5.html)
- [`dmesg(1)`](https://man7.org/linux/man-pages/man1/dmesg.1.html)
- Arch manual pages 收录的 [`lspci(8)`](https://man.archlinux.org/man/lspci.8.en) 与 [`lsusb(8)`](https://man.archlinux.org/man/lsusb.8.en)

### udev / systemd

- [`udev(7)`](https://www.freedesktop.org/software/systemd/man/latest/udev.html)
- [`udevadm(8)`](https://www.freedesktop.org/software/systemd/man/latest/udevadm.html)
- [`journalctl(1)`](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html)

### ArchWiki：发行版实践边界

- [Dynamic Kernel Module Support](https://wiki.archlinux.org/title/Dynamic_Kernel_Module_Support)
- [Arch boot process / Initial ramdisk](https://wiki.archlinux.org/title/Initial_ramdisk) 与 [mkinitcpio](https://wiki.archlinux.org/title/Mkinitcpio)
- [Unified Extensible Firmware Interface / Secure Boot](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot) 与 [Signed kernel modules](https://wiki.archlinux.org/title/Signed_kernel_modules)

---

**上一站**：[[计算机知识/20-操作系统/01-Linux/08-pacman-apt-dnf与yum包管理|pacman、apt、dnf 与 yum 包管理]] · **下一站**：[[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|网络、存储、日志与故障排查]] · **返回 MOC**：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/13-Linux-课程地图|Linux · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/01-Linux/16-服务资源容器与分层故障定位|Linux 深化：服务、资源、容器与分层排障]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
