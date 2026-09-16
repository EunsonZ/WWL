---
type: lesson
domain: computer-science
stage: 12
status: ready
difficulty: 进阶
estimated_minutes: 85
topics:
  - VFS
  - 文件描述符
  - inode
  - dentry
  - 路径解析
  - 链接
  - 权限检查
tags:
  - computer-science/systems
  - computer-science/filesystem
---

# VFS、文件描述符、inode、目录与路径解析

`open("/var/data/model.gguf", ...)` 看起来只是“按路径打开文件”，实际跨过了进程的文件描述符表、VFS 路径解析、挂载视图、目录项、inode、权限检查和具体文件系统实现。本课把这些对象拆开，解释为什么改名不等于改文件、为什么两个文件描述符可能共享偏移，以及为什么本地文件系统、网络文件系统和用户态文件系统能使用相似 API，却不必具有完全相同的语义与故障边界。

Linux 命令层的目录、挂载和链接入门见 [[计算机知识/20-操作系统/01-Linux/03-目录结构挂载与文件系统|目录结构、挂载与文件系统]] 与 [[计算机知识/20-操作系统/01-Linux/05-文件目录与文本处理命令|文件、目录与文本处理命令]]；本课关注它们背后的内核对象。

## 本课目标

学完后，你应该能够：

- 明确区分文件对象、路径、inode、目录项、文件描述符和 open file description；
- 解释 `open`、单独再次 `open`、`dup`、`fork`、`close`、`rename` 与 `unlink` 对这些对象分别做了什么；
- 画出 VFS、mount、dentry、inode 与具体文件系统之间的关系；
- 逐段解释绝对/相对路径、符号链接、挂载点、`.`、`..` 和目录搜索权限；
- 说明硬链接、符号链接与已打开文件在改名、删除和并发访问时的不同表现；
- 知道 VFS 提供统一入口，不会把本地磁盘、NFS 和 FUSE 的缓存、身份与持久化语义混为一谈。

## 1. 第一条边界：文件 ≠ 路径 ≠ inode ≠ FD

“文件”在日常语言里常把多个层次混在一起。更精确的拆法是：

| 对象 | 它是什么 | 它不是什么 |
| --- | --- | --- |
| 文件系统对象 | 一组内容和元数据；可以是普通文件、目录、符号链接、设备节点等 | 不必只有一个名字，也不必来自磁盘 |
| 路径（pathname） | 交给路径解析器的一串名字，例如 `../data/a.bin` | 不是永久对象 ID；解析结果依赖起点、挂载视图、链接和当时的目录树 |
| 目录项 | 父目录中“名字 → 对象”的关系；VFS 在内存中以 dentry 表示/缓存该关系 | 不是文件内容；dentry 也不是必须永久写在盘上的通用格式 |
| inode | VFS 对文件系统对象的内核表示，关联类型、权限、大小和数据映射等 | 通常不保存文件名；inode 号只在相应文件系统内有意义，还可能在对象删除后被复用 |
| 文件描述符（FD） | 某进程文件描述符表中的小整数索引，例如 `3` | 不是全系统对象 ID；另一个进程的 `3` 可以指向完全不同的对象 |
| open file description | 一次 `open` 建立的内核打开状态，Linux 内核实现中常对应 `struct file` | 不是路径字符串，也不是 inode；多个 FD 可以引用同一个打开状态 |

因此，“文件名就是文件”会立刻在以下情况中失效：

- 两个硬链接是两个路径名字，却指向同一 inode；
- 同一路径被分别 `open` 两次，通常得到两个 FD 和两个 open file description，却可到达同一 inode；
- 一个名字被 `unlink` 后，只要仍有打开引用，对象内容仍可由原 FD 访问；
- 路径在不同 mount namespace、容器根目录或当前工作目录中可能解析到不同对象；
- `/proc`、`tmpfs`、网络文件系统等对象并没有普通本地磁盘 inode 的同一种落盘形式。

> [!important] `设备号 + inode 号` 比路径更接近本地对象身份，但也不是永久全球 ID
> `stat` 显示的 inode 号需要和文件系统/设备身份一起解释。对象删除后编号可被复用；网络和堆叠文件系统还可能合成、重映射或改变可见标识。长期业务身份应由应用协议明确设计，不能偷用路径或 inode 号代替。

## 2. 三张表串起一次 `open`

下面是用于推理的简化模型，不是要求背诵的内核结构布局：

```text
进程 A 的 FD 表                     系统中的打开状态                VFS 路径与对象
┌──────────────┐                 ┌──────────────────┐       ┌────────────────────┐
│ fd 3 ────────┼────────────────→│ open description │──────→│ mount + dentry      │
│ fd 4 ────────┼──────┐          │ offset = 128      │       │        ↓             │
└──────────────┘      │          │ status flags     │       │ inode → 数据/操作集 │
                      └─────────→│ reference count  │       └────────────────────┘
进程 B 的 FD 表                   └──────────────────┘
┌──────────────┐                           ↑
│ fd 7 ────────┼───────────────────────────┘
└──────────────┘
```

从左到右应这样读：

1. FD 是**每进程**表中的索引；
2. 表项引用 open file description；
3. open file description 保存当前文件偏移、访问模式和 file status flags，并引用已解析的 VFS 对象；
4. VFS 对象把通用 `read`、`write`、`stat` 等操作分派给具体文件系统；
5. 最后才可能访问页缓存、本地块设备、远端服务器或用户态守护进程。

同一个 FD 表项还有自己的 **file descriptor flags**。最重要的例子是 `FD_CLOEXEC`：它决定成功执行新程序映像时该 FD 是否自动关闭。它是每个 FD 的属性；相对地，`O_APPEND`、`O_NONBLOCK` 一类 file status flags 位于共享的 open file description 上。修改后者可能被引用同一打开状态的其他 FD 看见。

Linux man-pages 对这一区分的权威定义见 [`open(2)`](https://man7.org/linux/man-pages/man2/open.2.html) 与 [`dup(2)`](https://man7.org/linux/man-pages/man2/dup.2.html)。

## 3. `open`、`dup` 与 `fork`：偏移到底归谁

### 3.1 分别 `open`：通常各有自己的偏移

```text
open("data", O_RDONLY) → fd 3 → OFD A（offset 0） ─┐
                                                   ├→ 同一 inode
open("data", O_RDONLY) → fd 4 → OFD B（offset 0） ─┘
```

两次独立 `open` 创建两个 open file description。用 `fd 3` 顺序读取使 OFD A 的偏移前进，不会因此改变 OFD B 的偏移。

### 3.2 `dup`：新 FD 共享原来的打开状态

```text
fd 3 ─┐
      ├→ OFD A（共享 offset、访问模式、file status flags）→ inode
fd 4 ─┘
```

`dup`、`dup2` 或相应 `fcntl` 操作复制的是引用，不是重新按路径打开。若先用 `fd 3` 读取 100 字节，再用 `fd 4` 顺序读取，后者通常从共享偏移 100 开始。关闭 `fd 3` 只移除一个引用；只要 `fd 4` 仍在，打开状态与对象引用就不会因这次 `close` 消失。

### 3.3 `fork`：父子进程的 FD 表分开，指向的打开状态仍可相同

`fork` 后父、子各有自己的 FD 表，但继承的对应 FD 引用同一 open file description，所以共享文件偏移和 file status flags。父子谁先读取会影响另一方下一次顺序读取的位置。这是共享状态，不是“两个 FD 数字恰好相同”的结果。

```text
父进程 fd 3 ─┐
             ├→ 同一 OFD（offset）→ inode
子进程 fd 3 ─┘
```

`exec` 不是 `fork`：成功的 `execve` 替换当前进程的程序映像，默认会保留未设置 close-on-exec 的 FD。因此创建可能跨 `exec` 的 FD 时，应在同一个原子操作中请求 close-on-exec，例如 `open(..., O_CLOEXEC)`，避免多线程程序在“先打开、后设置标志”的窗口里泄漏描述符。

### 3.4 不想共享顺序偏移时

`pread` / `pwrite` 显式给出本次 I/O 的位置，通常不改变 open file description 的共享偏移，适合多个执行流对已知位置并发访问。`O_APPEND` 则要求每次写入在写操作发生时定位到文件末尾；它避免普通“先 seek 到末尾、再 write”之间的竞争，但不把多次 `write` 合成事务，也不自动提供崩溃持久性。网络文件系统能否原样实现原子 append 还取决于协议和服务器。

## 4. VFS：统一接口，而不是统一内部布局

Linux VFS（Virtual File System）在系统调用与具体文件系统之间提供共同对象模型和操作入口。其关键对象可先理解为：

| VFS 对象 | 负责表达什么 | 典型关系 |
| --- | --- | --- |
| superblock | 一个已装载文件系统的内存级总体状态与操作 | 多个 mount 可引用同一底层文件系统/superblock |
| mount | 某个 mount namespace 中“把一棵文件系统树接到哪里”的关系 | 挂载根 dentry 接到另一棵树的挂载点 |
| dentry | 某父目录下某个名字的查找结果与缓存节点 | 可指向 inode，也可作为“此名字当前不存在”的 negative dentry |
| inode | 某个文件系统对象的属性、数据映射和操作 | 可被多个 dentry 引用，形成硬链接 |
| file / open file description | 一次打开后的运行时状态 | 被一个或多个 FD 引用，并关联 path/inode 与文件操作 |

VFS 让 `open`、`read`、`stat` 等调用可以面向 ext4、XFS、Btrfs、tmpfs、procfs、NFS 或 FUSE。统一的是调用形状和一组共同约定；数据结构怎样落盘、是否有远端往返、缓存何时重验证、哪些错误会延迟出现，仍由具体实现和下层系统决定。Linux 内核的整体说明见 [Overview of the Linux Virtual File System](https://docs.kernel.org/filesystems/vfs.html)。

### dentry 不只是“磁盘上的目录项”

dcache 会缓存名字查找结果，也会缓存 negative dentry，以便快速回答“这个父目录下目前没有这个名字”。本地文件系统通常可长时间复用缓存；网络文件系统可能要求重新验证，因为服务器端目录可能已经改变。dentry 活在内存中，它是 VFS 路径查找对象，不能直接等同于某种文件系统的磁盘目录记录。

### 一个 path 必须包含 mount 和 dentry

只有 dentry 不足以完整描述 VFS 路径位置：同一文件系统树可以被挂到多个位置，而不同 mount namespace 又可拥有不同挂载关系。内核的 `struct path` 因此概念上由“哪一个 mount + 其中哪一个 dentry”共同定位。路径穿过挂载点时，查找会切换到被挂载树的根；处理 `..` 时也必须考虑是否正位于挂载根。

## 5. Pathname 逐段解析

考虑：

```text
../models/current/weights.bin
```

解析器不是一次在全盘搜索整串字符，而是按规则逐段行走：

1. **选择起点**：绝对路径从该进程看到的根开始；相对路径通常从当前工作目录开始，`openat` 一类接口也可从一个目录 FD 开始；
2. **解析非末尾分量**：查找父目录中的名字，确认结果是可继续穿越的目录，并检查目录搜索权限；
3. **处理 `.` 与 `..`**：`.` 留在当前目录，`..` 转向逻辑父级，同时受进程根与挂载边界约束；
4. **穿越挂载点**：若当前 dentry 上覆盖着一个 mount，进入所挂载文件系统的根；
5. **处理符号链接**：相对目标从该链接所在目录继续，绝对目标从进程可见根重新开始，再接上尚未处理的路径；
6. **解析末尾分量**：是否必须跟随 symlink、是否允许目标不存在、是否创建、是否必须是目录，由具体系统调用和 flags 决定；
7. **返回稳定引用或错误**：例如 `ENOENT`、`ENOTDIR`、`EACCES`、symlink 循环/过深时的 `ELOOP`。

```text
起点
  │
  ├─ component ─→ dcache 命中？──否──→ 调具体文件系统 lookup
  │                    │                         │
  │                    └──────── dentry/inode ←─┘
  │
  ├─ mountpoint？→ 切到 mounted root
  ├─ symlink？────→ 展开目标后继续解析
  └─ final component → 按本次调用规则处理
```

完整实现还包含并发改名、RCU 快速查找、automount、大小写规则和安全约束。掌握主线比背内部锁名重要；Linux 内核的 [Pathname lookup](https://docs.kernel.org/filesystems/path-lookup.html) 专门解释了 dcache、权限和并发查找。

### 路径不是稳定授权句柄

“先 `stat(path)` 检查，再 `open(path)` 使用”之间，其他进程可能替换某个目录项或 symlink，形成 time-of-check to time-of-use（TOCTOU）窗口。在处理不可信目录时，更稳健的设计是：

- 先获得可信目录 FD，再使用 `openat` 家族相对该目录解析；
- 在真正取得 FD 后用 `fstat` 检查已打开对象，而不是重新检查原路径；
- 明确是否允许 symlink、跨 mount 或越出约束目录；Linux 特有的 `openat2` 可用解析 flags 表达部分约束；
- 不把字符串前缀比较当作“路径仍在某目录下”的安全证明。

这不是要求所有应用自行重写路径解析器，而是提醒：安全边界应建立在内核返回的对象引用与明确解析策略上。

## 6. 权限检查发生在路径的每一段

传统 Unix discretionary access control（DAC）要同时看目录和最终对象：

| 权限位置 | `r` | `w` | `x` |
| --- | --- | --- | --- |
| 普通文件 | 读取内容 | 修改内容 | 作为程序执行（还受格式、挂载和其他策略限制） |
| 目录 | 列出目录项名字 | 修改目录项，通常需配合 `x` | 搜索/穿越目录并访问已知名字 |

解析 `/a/b/file` 时，进程需要搜索沿途目录。即使最终文件可读，缺少某个父目录的搜索权限也可能得到 `EACCES`。反过来，知道名字且有目录搜索权，不等于能列出目录中的其他名字。

删除或改名主要是在**父目录**中修改目录项，所以目标普通文件本身的写位不是唯一或主要判断；父目录权限、sticky bit、挂载只读状态等都可能参与。最终决定还可能叠加：

- effective UID/GID、supplementary groups 与 ACL；
- capabilities、user namespace/idmapped mount 等身份映射；
- LSM 策略，例如 SELinux 或 AppArmor；
- mount flags 与文件 flags；
- 具体文件系统和网络服务器的访问规则。

访问检查常在 `open` 时决定能否取得相应 FD。之后路径被改名、原名字被删除，现有 FD 仍引用已打开对象；但这不表示所有后续操作永远绕过安全策略，特定操作、文件系统、租约或 LSM 仍可能再次检查或返回错误。

## 7. 硬链接、符号链接、改名与删除

### 硬链接：多个名字，共享一个 inode

```text
目录 A: report.txt ─┐
                    ├→ inode 421 → 数据
目录 B: latest.txt ─┘
```

硬链接通常不能跨文件系统，因为目录项要引用本文件系统内的 inode；普通用户也通常不能给目录任意增加硬链接。任一名字下的内容写入都会通过共享 inode 反映到另一个名字。删除一个名字只是减少链接数；当链接数为零且没有打开/映射等活动引用时，对象才具备被回收的条件。

### 符号链接：链接本身是对象，内容是一条路径

```text
current → releases/v2
```

符号链接可以跨文件系统，也能指向不存在的目标。相对目标相对于**链接所在目录**解析，而不是相对于调用进程当前目录。对链接使用 `lstat` 可观察链接本身；普通 `stat` 通常跟随到目标。是否跟随最后一个分量由 API 和 flags 决定。

### `rename` 与 `unlink` 只改变命名关系，不自动保证持久化

同一文件系统内的 `rename` 通常为目录命名更新提供原子可见性：观察者不会看到“半个名字”。用新文件 rename 覆盖旧路径是**切换这个名字指向的 inode**，不是原地改变旧 inode；旧 inode 的其他硬链接和已经打开的 FD 仍指向旧对象。`rename` 不等于多文件事务，也不等于改名已经在断电后可恢复；持久化还需要第 13 课讨论的 `fsync`、目录同步、文件系统实现与设备保证。

`unlink` 移除一个目录项。已经打开的 FD 不再依赖原路径查找，因此可继续读写对象。这也是日志轮转后“文件名看起来消失但空间仍未释放”的重要原因：仍有进程持有旧 inode 的打开引用。

## 8. 本地、网络与用户态文件系统的边界

### 网络文件系统

NFS、SMB/CIFS 等可挂进同一 VFS 树，但目录项和数据可能缓存在客户端，真正权威状态在服务器。于是：

- 客户端 dentry/inode 属性需要按协议与缓存策略重新验证；
- 网络分区、服务器重启、租约或凭据变化可能让已有操作阻塞、重试或返回 stale handle；
- 本地进程的 `O_APPEND`、锁、权限与 `fsync` 需要协议/服务器协作，不能只凭本地系统调用名称推断最终效果；
- “本机缓存里读到了”与“服务器已持久保存”是不同结论。

### FUSE 用户态文件系统

FUSE 让普通用户态守护进程提供数据和元数据，内核模块负责把 VFS 请求传给守护进程。一次看似普通的路径查找或读取可能包含内核—用户态往返，并受守护进程调度、权限、缓存配置和后端服务影响。守护进程卡住或退出时，挂载树上的操作也可能等待或失败。官方概览见 [Linux FUSE documentation](https://docs.kernel.org/filesystems/fuse/fuse.html)。

> [!warning] “能挂载”不是信任证明
> 远端服务器或 FUSE 守护进程参与命名、内容和属性解释。处理不可信文件系统时，应限制其权限与暴露面，避免把可执行文件、设备语义、锁或强一致性当成默认可信能力。

## 9. 安全只读观察

以下命令只查询现有状态，不创建、删除、改名或写入文件。它们按 GNU/Linux 环境编写；容器、精简发行版或受限 `/proc` 可能缺少命令或权限，记录差异即可，不要用 `sudo` 绕过。

```bash
# 当前路径属于哪个 mount；文件系统类型是什么
findmnt -T . -o TARGET,SOURCE,FSTYPE,OPTIONS

# 比较路径、设备号、inode、链接数和类型
stat -c 'path=%n dev=%D inode=%i links=%h type=%F' . /etc/hosts

# 只读查看路径每一段的类型与权限；部分系统没有 namei 命令
namei -l /usr/bin/env

# 查看当前 shell 已有的 FD 及其目标；不读取目标文件内容
ls -l "/proc/$$/fd"

# stdin 的打开状态；pos 是当前偏移，flags 是内核编码的状态标志
sed -n '1,8p' "/proc/$$/fdinfo/0"

# 当前进程看到的根、工作目录和 mount namespace 标识
readlink "/proc/$$/root" "/proc/$$/cwd" "/proc/$$/ns/mnt"
```

`/proc/$$/fd` 可能暴露终端、管道、已打开路径等环境信息；公开分享截图前应脱敏。`stat` 观察的是命令执行时的快照，不能证明对象随后没有被并发改名或替换。

## 练习：不用写磁盘，画出一次打开

1. 选择一个可公开、可读取的系统文件，例如 `/etc/hosts`；运行 `findmnt -T /etc/hosts`，记录它落在哪个 mount、是什么文件系统类型。若它被单独挂载，也把这个事实画出来。
2. 用 `namei -l /etc/hosts` 逐段列出目录与最终对象。对每个目录写下路径解析需要的是哪一种目录权限。
3. 用 `stat -c 'dev=%D inode=%i links=%h type=%F' /etc/hosts` 记录对象标识；解释为何只复制字符串 `/etc/hosts` 不能永久标识这个对象。
4. 画出“分别 `open` 两次”和“`open` 后 `dup`”两张图。每图标出 FD 数量、open file description 数量、共享/独立偏移和 inode 数量。
5. 思考：进程打开日志后，管理员把日志改名并创建同名新日志。旧 FD、新路径、旧 inode、新 inode 分别怎样对应？为什么服务通常需要显式重新打开日志？
6. 对比硬链接和符号链接：目标名字被删除后，它们各自剩下什么？为什么符号链接可跨文件系统而硬链接通常不行？

### 成功标准

- [ ] 能不含糊地说出：路径用于查找，inode 表示文件系统对象，FD 是进程表索引，open file description 保存一次打开的共享状态；
- [ ] 能判断两次 `open` 的偏移通常独立，而 `dup` 与 `fork` 继承引用的偏移共享；
- [ ] 能画出 `FD → open file description → mount+dentry → inode → 具体文件系统`；
- [ ] 能逐段解释路径起点、目录搜索权限、挂载切换和 symlink 展开；
- [ ] 能说明 `unlink` 后打开 FD 仍可用，以及回收同时受链接数与打开引用影响；
- [ ] 不会从“API 都叫 `open/read/fsync`”推断本地磁盘、网络服务器和 FUSE 后端具有相同延迟、缓存与持久化保证。

## 参考资料

- [Linux VFS overview](https://docs.kernel.org/filesystems/vfs.html)：VFS、superblock、inode、dentry 与 file operations 的内核对象模型。
- [Linux pathname lookup](https://docs.kernel.org/filesystems/path-lookup.html)：dcache、逐段查找、权限检查、挂载与并发路径解析。
- [`open(2)`](https://man7.org/linux/man-pages/man2/open.2.html)、[`dup(2)`](https://man7.org/linux/man-pages/man2/dup.2.html)、[`fork(2)`](https://man7.org/linux/man-pages/man2/fork.2.html)：open file description、共享偏移、FD flags 与继承关系。
- [`path_resolution(7)`](https://man7.org/linux/man-pages/man7/path_resolution.7.html)、[`openat2(2)`](https://man7.org/linux/man-pages/man2/openat2.2.html)：路径起点、symlink、权限和 Linux 特有的解析约束。
- [Linux FUSE documentation](https://docs.kernel.org/filesystems/fuse/fuse.html)、[Network filesystem caching API](https://docs.kernel.org/filesystems/caching/netfs-api.html)：用户态/远端实现怎样进入 VFS，以及缓存一致性为何需要额外协议。

---

**上一站**：[[计算机知识/30-计算机系统/11-存储设备块层页缓存与持久化|存储设备、块层、页缓存与持久化]] · **下一站**：[[计算机知识/30-计算机系统/13-文件系统布局日志CoW与一致性|文件系统布局、日志、CoW 与一致性]] · **内存基础**：[[计算机知识/30-计算机系统/02-进程虚拟地址空间与内存映射|进程虚拟地址空间与内存映射]] · **Linux 实务入口**：[[计算机知识/20-操作系统/01-Linux/03-目录结构挂载与文件系统|目录结构、挂载与文件系统]] · **返回**：[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/08-操作系统-课程地图|操作系统 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/02-操作系统原理/03-虚拟内存置换文件系统与崩溃边界|操作系统：虚拟内存、置换与崩溃一致性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
