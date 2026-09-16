---
type: lesson
domain: computer-science
stage: 13
status: ready
difficulty: 进阶
estimated_minutes: 95
topics:
  - 文件系统布局
  - extent
  - 空闲空间
  - 日志
  - 崩溃一致性
  - 写时复制
  - 快照
  - 校验和
tags:
  - computer-science/systems
  - computer-science/filesystem
---

# 文件系统布局、日志、CoW 与一致性

应用收到一次 `write` 成功，不等于数据已经进入 SSD 的非易失介质；日志文件系统“恢复成功”，也不等于应用最后一组记录完整；快照和校验和能缩小某些故障，却都不能替代备份。本课沿着“逻辑文件偏移 → 文件系统元数据 → 块层与设备”追踪一次写入，比较日志与写时复制两条崩溃一致性路线，并把 `fsync` 的承诺放回完整存储栈解释。

开始前应先掌握 [[计算机知识/30-计算机系统/12-VFS文件描述符Inode目录与路径解析|VFS、文件描述符、inode、目录与路径解析]]；块层、页缓存与设备 flush 的上游路线见 [[计算机知识/30-计算机系统/11-存储设备块层页缓存与持久化|存储设备、块层、页缓存与持久化]]，文件映射的内存侧模型见 [[计算机知识/30-计算机系统/02-进程虚拟地址空间与内存映射|进程虚拟地址空间与内存映射]]。

## 本课目标

学完后，你应该能够：

- 从逻辑偏移、extent、文件系统块、空闲空间与设备地址解释文件怎样布局；
- 列出目录、inode、extent map、分配信息和 superblock 等元数据为何必须一致更新；
- 区分应用成功返回、用户态缓冲、页缓存、writeback、`fsync`、设备 flush 和断电后的真实可恢复状态；
- 解释 metadata journaling、data ordering、journal replay 与 `fsck` 分别解决什么问题；
- 用“新块 → 新父节点 → 新根”解释 CoW、快照、reflink 与空间放大；
- 说明校验和只负责检测，自动修复还需要可信冗余，快照也不是备份；
- 把 ext4、XFS、Btrfs、ZFS 与 APFS 当作机制实例，而不是从名字推断所有配置的行为。

> [!tip] 首读不需覆盖全部文件系统
> 第一轮读 `1 → 3 → 4 → 6 → 11`：先理解逻辑文件与块，再分清写入的成功层级、耐久替换和应用事务边界，最后用故障矩阵检验条件。第二轮再学 journaling、CoW、checksum、具体文件系统坐标与网络/FUSE。这种分层不删除任何边界，但避免首读把每个机制名称都当成必背表。

## 1. 文件是逻辑字节序列，设备处理的是块

应用看到普通文件是一段按字节编号的逻辑空间：偏移 0、1、2……文件系统需要把逻辑范围映射到底层存储。

```text
文件逻辑偏移
0 KiB                 64 KiB       96 KiB                     192 KiB
├──── extent A ────────┤  hole  ├──── extent B ───────────────┤
│                      │        │                              │
▼                      ▼        ▼                              ▼
文件系统块 8200..8215           文件系统块 12000..12023
          │                                  │
          └──── 块层/映射层/LVM/RAID/FTL ────┴→ 设备处理的地址
```

- **文件系统块**是许多布局和分配操作的基本单位；它不必等于内存页、设备逻辑扇区、物理闪存页或擦除块；
- **extent** 用“逻辑起点、物理起点、长度及状态”描述一段连续映射，避免给每个块保存一个独立指针；
- **hole（稀疏空洞）**表示某段逻辑范围没有实际数据块，读取通常得到零；文件逻辑大小可大于实际分配空间；
- **unwritten extent** 可以预留物理空间而仍在读取时表现为零，避免尚未初始化的旧介质内容泄露；
- 设备地址还可能经过加密映射、LVM、软件/硬件 RAID、虚拟磁盘、SSD FTL 或云块存储重映射，所以文件系统看到的“连续块”不保证物理介质真正连续。

extent 能降低大文件的映射元数据并帮助连续 I/O，但随着随机改写、共享块和空间紧张，一个文件仍可碎成多个 extent。也不能从 `du`、文件大小或 extent 数量单独推断实际物理占用：压缩、稀疏、reflink、快照和下层 thin provisioning 都可能改变答案。

## 2. 空闲空间本身也是关键元数据

文件系统必须回答“哪些范围可分配”。常见结构包括 bitmap、按长度/位置索引的树、分配组/块组中的局部结构，以及它们的组合。一次写入可能同时改变：

```text
文件内容块
  + 文件的 extent map / inode 大小
  + 空闲空间记录
  + 父目录项（新建/删除/改名时）
  + 时间戳、链接数、配额、xattr/ACL
  + 日志、校验和或引用计数
```

如果系统在中途崩溃，可能出现“同一块既分给文件又标为空闲”“块已占用却没有对象引用”“目录项指向未完成 inode”等矛盾。文件系统的一致性机制首先要保证这些结构能回到自洽状态。

### 延迟分配改变了 `ENOSPC` 出现时机

buffered write 可以先在页缓存中产生脏页，稍后 writeback 时才真正选择物理空间。延迟分配能结合更大范围做出更连续的分配，却意味着：

- `write` 已返回后，真正分配和 I/O 仍可能失败；
- 空间不足、配额或设备错误可能在后续 `write`、`fsync`、`close`，甚至其他相关 FD 上报告；
- CoW 文件系统改写旧数据也需要新空间；“删除文件”还可能因快照/共享引用存在而没有立刻释放对应块。

可靠应用必须检查每次写入长度与错误，也必须检查同步和关闭阶段的错误，不能只检查最早一次 `write`。

## 3. 一次写入经过哪些“成功层级”

下面是常见 buffered I/O 路线。具体文件系统、DAX、direct I/O、网络文件系统和应用库会改变路径，但层次区分仍然有用：

```text
应用对象/序列化状态
    │
    ▼
语言运行库或 stdio 缓冲 ── fflush/close library stream
    │
    ▼
write()/pwrite() ── 成功常表示内核已接受字节
    │
    ▼
页缓存中的 dirty pages + 内存中 dirty metadata
    │
    ▼
writeback / 文件系统事务、ordering、journal 或 CoW 提交
    │
    ▼
块层、驱动、控制器与设备 volatile write cache
    │
    ▼
非易失介质，或设备声称断电后仍可恢复的稳定状态
```

| 观察到的事件 | 可以安全推断什么 | 仍不能单独推断什么 |
| --- | --- | --- |
| 库的写函数成功 | 数据进入库定义的某层状态 | 已调用内核、已持久化 |
| `fflush` 成功 | stdio 用户态缓冲已交给内核接口 | 页缓存和设备已稳定 |
| `write` 返回正数 | 该数量字节被内核接受；短写需继续处理 | 所有请求字节都写入；断电后可恢复 |
| 后台 writeback 完成 | I/O 已按内核/驱动报告推进 | 相关目录更新已持久；设备没有谎报 |
| `fsync(fd)` 成功 | 文件系统要求相关数据与必要元数据到稳定存储，并等待下层报告完成 | 新文件名/改名的父目录项也一定稳定；故障设备绝不丢数据 |
| 设备 cache flush/FUA 完成 | 按设备/传输协议，先前相关写入已到声明的持久域或本次写入绕过易失缓存 | 固件、供电、介质和整个映射栈一定正确 |
| 断电后重新读取并校验 | 这次恢复路径读回了预期内容 | 没有潜伏损坏；备份和恢复演练可以省略 |

> [!important] “真实持久化”是一条端到端契约
> `fsync` 是应用向内核表达持久性需求的关键接口，但它依赖具体文件系统正确实现、块层正确传播 flush/FUA、控制器与设备诚实报告完成，以及电源故障时持久域真正有效。任何一层忽略或虚报语义，应用都无法只靠一个系统调用消除物理故障。

### `close`、`sync`、`fsync` 和 `fdatasync` 不是同义词

- `close` 释放 FD，也可能暴露先前延迟错误，但普通成功 `close` 不是文件持久化屏障；
- `fsync` 针对一个已打开文件，要求其修改的数据和关联元数据同步；
- `fdatasync` 可省略与后续正确读取无关的元数据，但文件大小等必要元数据仍要同步；
- 全局 `sync`/后台 writeback 面向更宽范围，不能替代应用为自身提交点建立清晰协议；
- `mmap` 修改文件页时还要按相应平台规则使用 `msync`/`fsync` 并检查结果，不能因为内存值已改变就推断文件已稳定。

Linux [`fsync(2)`](https://man7.org/linux/man-pages/man2/fsync.2.html) 特别指出：同步文件并不自动保证**包含它的目录项**已落盘。

## 4. 耐久替换协议：文件内容与文件名是两份状态

很多程序用“写临时文件，再 rename 覆盖正式文件”避免读者看到半写内容。一个概念上的本地文件系统协议是：

```text
1. 在目标同目录创建唯一临时文件，拒绝意外复用/跟随 symlink
2. 写入完整内容，处理短写和序列化错误
3. fsync(临时文件)，检查返回值
4. rename(临时名, 正式名)，检查返回值
5. fsync(父目录)，检查返回值
```

为什么每一步都存在：

- 同目录让 `rename` 通常保持在同一文件系统，从而使用该文件系统的原子命名语义；
- 同步临时文件使新内容先达到所需持久层；
- `rename` 提供名称切换的原子可见性，但不是多文件事务；
- 同步父目录使新建/改名/删除这样的目录项更新也进入提交范围。

这仍是**机制模板，不是可直接复制到所有平台的代码**。有的平台或文件系统不支持对目录执行 `fsync`，此时必须依据其官方持久化接口并用故障测试验证；不能默默忽略错误。程序还要处理原目标的权限/xattr、多个目录参与的 rename、文件系统特有语义、Windows/macOS API 差异、网络协议和错误恢复。若应用状态横跨多个文件，通常应使用数据库/事务日志或自带版本号与提交记录的协议，而不是假定若干 `rename` 能组成事务。

## 5. Journaling：先留下可重放的元数据事务

日志文件系统常把一组元数据修改组织为事务：

```text
内存中的修改
   │
   ├─→ 把事务记录写入 journal
   │       └─→ ordering / flush 后写 commit record
   │
   └─→ 稍后 checkpoint：把已提交修改写到最终位置

崩溃恢复：只重放拥有有效 commit 的完整事务；忽略未提交尾部
```

日志的关键价值是：若系统在多处元数据原地更新的中间崩溃，恢复程序可以根据完整提交记录重放或丢弃事务，而不必每次扫描全盘猜测每个结构的更新阶段。

### 三种常被混淆的“data mode”

以 ext4 的 JBD2 机制为例，概念上可比较：

| 模式 | journal 中主要记录什么 | 数据与元数据的顺序 | 崩溃后不能轻率承诺什么 |
| --- | --- | --- | --- |
| metadata journaling + ordered data | 元数据 | 关联的新数据块先到最终位置，再提交使其可见的元数据事务 | 未经 `fsync` 的最新应用内容一定保留 |
| metadata journaling + writeback data | 元数据 | 不强制新数据在相关元数据前完成 | 崩溃前刚改写的文件内容与新元数据对应正确 |
| data journaling | 数据与元数据都先经过 journal | 已提交事务可一起重放 | 多个系统调用自动成为一个应用事务；介质永不损坏 |

这张表只用于解释机制。挂载选项、文件系统版本、direct I/O、delayed allocation、应用同步调用和下层设备都会影响具体行为。ext4 官方的 [JBD2 journal design](https://docs.kernel.org/filesystems/ext4/journal.html) 说明了 commit record、replay 与三种 data mode。

### Write ordering 为什么不可省略

假设元数据先宣告“块 X 已属于文件并包含新数据”，设备却把真正的数据写入留在易失缓存。此时断电，恢复后元数据可能指向未写好或曾属于别人的块。日志/文件系统因此需要把“数据完成、日志事务、commit record、最终覆盖”之间的先后关系传到块层；flush 与 FUA 等机制用来约束会重排和缓存写入的设备。

只在 CPU 中按顺序调用两个 `write` 不等于设备也按该顺序稳定落盘。另一方面，无脑让每个小写入同步会严重牺牲合并、队列并行和吞吐；正确做法是让应用提交点、文件系统事务和设备持久化屏障相互对应。

## 6. Crash consistency 与 application consistency 是两层问题

**文件系统崩溃一致性**关心目录、分配、inode、引用计数等结构是否能恢复到自洽状态。**应用一致性**关心业务不变量，例如“订单记录和库存扣减必须一起出现”。前者不会自动推导后者。

例如应用依次写：

```text
余额 = 80
流水 += -20
```

即使文件系统在崩溃后结构完全健康，也可能只有第一项成为持久状态。应用需要自己的事务边界、write-ahead log、版本/校验记录、数据库事务或可幂等重放协议。

### `fsck` 与 journal replay

- **journal replay** 按文件系统事务日志恢复已提交、未 checkpoint 的更新，通常范围比全盘扫描小；
- **fsck** 检查并尝试修复文件系统结构不变量，例如分配引用、目录连接和 inode 状态；具体能力因文件系统而异；
- 两者都不等同于恢复应用最后想写的内容，也不能凭空找回已覆盖数据；修复结构时甚至可能把无法归属的对象放入恢复区或丢弃冲突引用；
- 现代文件系统可能提供在线检查、scrub 或导入时选择有效根等其他路线，不能把一个文件系统的维修命令套给另一个。

本课不提供任何卸载、强制修复、格式化或块设备写命令。真实故障应先停止非必要写入、保留日志与设备身份、确认备份，依据该文件系统官方流程在副本或受控恢复环境中处理。

## 7. Copy-on-Write：不覆盖旧树，最后切换根

CoW 文件系统的核心不是“每次复制整个文件”，而是修改某块时把新版本写到别处，并沿引用路径生成必要的新父节点：

```text
提交前                         准备新版本
Root A                         Root A（仍有效）
  └─ P1                         └─ P1 ─→ old data
      └─ old data

                               new data ← 新写自由块
                                  ↑
                               P1'       ← 新父节点
                                  ↑
                               Root B    ← 最后发布的新根
```

只要 Root B 尚未被原子地选为新有效根，Root A 仍描述旧的一致状态。提交成功后，新读者从 Root B 到达新版本；旧树中的块若仍被快照/reflink 引用就不能释放。

### 快照与 reflink 为什么便宜

- **快照**保留某个树根或子树根的引用；创建时不必复制所有文件数据；
- **reflink/clone** 让两个独立文件 inode 暂时共享 extent，任一方改写相应范围时再 CoW；
- 成本从“立即复制全部数据”变成“维护引用 + 以后只复制发生修改的路径/块”。

代价也来自同一机制：随机覆写会分配新块并更新多层元数据；旧版本被快照引用会延迟空间回收；共享 extent 需要引用计数；接近满盘时 CoW 可能更难找到空间；碎片与写放大会影响性能。因此快照策略必须同时设计保留期、空间监控和删除/回收行为。

### CoW 不是日志的简单反义词

日志文件系统可以带 CoW/reflink 功能，CoW 文件系统也可能有 intent log、log tree 或其他快速同步路径。分类时应问具体对象怎样更新：数据块是否原地覆盖、元数据树怎样提交、同步写如何快速持久化、恢复选哪个根，而不是只贴“journaling”或“CoW”标签。

## 8. Checksums：检测、定位与修复是三件事

校验和把内容映射成摘要。读取时重新计算并比较，可以发现部分 silent corruption、misdirected write 或不完整块。设计时要问：

1. 校验覆盖数据、元数据，还是两者？
2. 摘要存在哪里？若摘要和数据同样被错误覆盖，是否还能独立验证？
3. 是否记录预期块地址/对象身份/事务 generation，以检测“内容有效但写错位置”？
4. 检测到不匹配后，是否有另一份经过验证的副本用于修复？

**校验和本身通常只能检测，不能创造正确数据。** 有镜像、纠删码或备份时，系统才可能用另一份通过校验的副本自动/人工修复。冗余若同时遭遇软件错误、误删除、勒索、控制器故障或同一管理域事故，仍可能一起损坏。

> [!warning] Snapshot、RAID、checksum 都不是 backup
> 快照常与原数据共享设备和故障域；RAID 主要维持设备故障后的可用性；checksum 主要检测内容不一致。备份还需要独立副本、权限/位置隔离、版本保留以及真实恢复演练。

## 9. 五种文件系统只作为机制坐标

| 文件系统 | 用来观察的机制例子 | 不应从名字直接推断 |
| --- | --- | --- |
| ext4 | extent、块组与空闲空间结构；JBD2 元数据日志；ordered/writeback/journal data mode | 所有挂载都采用同一 data mode；`write` 成功就是持久化；日志等于内容校验 |
| XFS | allocation group 分区并行管理；extent 与 B-tree；面向元数据的事务日志和 delayed logging | “适合大文件”即可代替 workload/恢复验证；日志自动保护所有应用数据事务 |
| Btrfs | 数据/元数据 CoW；B-tree、extent 引用、subvolume snapshot/reflink；默认对数据与元数据校验 | snapshot 是独立备份；检测到损坏时单副本也必能修复；所有 NOCOW 配置仍有同样校验语义 |
| ZFS / OpenZFS | pool 与 vdev；CoW 指针树、transaction group、端到端校验、snapshot；同步写有专门 intent log 路线 | 任意 vdev 布局都能容忍相同故障；有 checksum 就不需冗余、scrub 或备份 |
| APFS | container 内 volume 可共享空间；CoW 元数据更新；clone、snapshot 与元数据校验 | 与 Btrfs/ZFS 的数据校验、RAID、恢复工具完全相同；Apple 平台所有存储介质行为一致 |

这些文件系统的 feature、默认值、平台支持和修复流程会变化。选择时应依据当前官方文档、工作负载、备份/恢复测试、硬件拓扑和运维能力，不用一张“谁最先进”的排行榜代替设计。

机制资料可从 [ext4 journal](https://docs.kernel.org/filesystems/ext4/journal.html)、[XFS documentation](https://docs.kernel.org/filesystems/xfs/index.html)、[Btrfs introduction](https://btrfs.readthedocs.io/en/stable/Introduction.html)、[OpenZFS Copy-on-Write](https://openzfs.github.io/openzfs-docs/Basic%20Concepts/Copy-on-write.html) 与 [Apple APFS FAQ](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/APFS_Guide/FAQ/FAQ.html) 进入。

## 10. 网络与用户态文件系统：持久化边界被拉长

VFS 的 `fsync` 入口可以相同，但下层可能不是本地块设备：

```text
应用 → 本机页缓存/VFS → 网络客户端 → 网络 → 服务器缓存/文件系统 → 服务器设备
```

对网络文件系统应额外确认：

- 协议版本怎样定义稳定写与 commit，客户端 `fsync` 需要等待到服务器哪一层；
- 客户端、代理和服务器是否都有缓存，断线重试是否可能重复操作；
- 服务器返回成功后，其文件系统与存储设备是否正确兑现持久化；
- 多客户端通过租约、锁、属性缓存或 close-to-open 规则获得什么一致性；
- 网络分区和服务器故障时，应用会阻塞、失败、重连还是读到旧缓存。

对 FUSE，应继续追问守护进程的 `flush`/`fsync` handler 实际做了什么：它可能写本地文件、对象存储、远程 API 或只更新内存。守护进程返回成功只是其协议承诺；后端耐久性还要由实现、配置和故障测试证明。统一文件 API 不会抹平分布式系统中的超时、重试、缓存一致性与部分失败。

相关诊断入口见 [[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|网络、存储、日志与故障排查]]；内核缓存边界可参考 [Network filesystem caching API](https://docs.kernel.org/filesystems/caching/netfs-api.html) 与 [FUSE documentation](https://docs.kernel.org/filesystems/fuse/fuse.html)。

## 11. 故障矩阵：把保证写成条件句

| 崩溃/故障时点 | 恢复后可能看到什么 | 正确结论 |
| --- | --- | --- |
| 用户态缓冲尚未交给内核 | 旧文件 | 库写成功不等于系统调用成功 |
| `write` 已返回，未做同步 | 旧内容、新内容、部分最新状态或后续错误，取决于实现 | `write` 成功主要是“已被接受” |
| 新文件已 `fsync`，创建它的目录未同步 | 文件内容可能稳定，但崩溃后名字是否可达缺少完整保证 | 内容与命名更新要分别提交 |
| 文件与相关目录都按协议同步成功 | 应恢复到协议承诺的提交点 | 仍依赖全栈正确兑现 flush/持久域 |
| journal 有完整 commit，尚未 checkpoint | 恢复时重放已提交事务 | replay 保护文件系统事务，不自动保护应用多文件不变量 |
| CoW 新树未发布有效根 | 从旧根恢复旧的一致状态 | 最新修改可能丢失，但不应暴露半棵新树 |
| checksum 不匹配且只有一份数据 | 能报告损坏，未必能修复 | 检测能力不等于恢复能力 |
| 本地 `fsync` 等待远端服务器 | 结果依赖协议、服务器和网络故障处理 | 不能把本地块设备模型原样套用 |

实际文件系统只会在其文档、挂载选项、硬件与应用调用共同满足时提供对应保证。任何恢复结论都应由故障注入、断电测试、重挂载/重启后的校验与备份恢复演练验证。

## 12. 安全只读观察

以下命令不创建文件、不触发修复、不改 mount，也不写块设备：

```bash
# 当前路径实际落在哪个文件系统；先看类型和挂载选项再谈机制
findmnt -T . -o TARGET,SOURCE,FSTYPE,OPTIONS

# 文件系统块大小、总量和空闲量；GNU stat 的 -f 查看文件系统状态
stat -f -c 'type=%T block=%S blocks=%b free=%f available=%a' .

# 比较逻辑大小与实际分配块；选择你有权观察的现有普通文件
stat -c 'path=%n size=%s allocated_blocks=%b block_unit=%B inode=%i' /etc/hosts

# 已挂载文件系统的字节与 inode 容量
df -hT .
df -i .

# 只读查看块设备拓扑与挂载关系；容器中可能没有对应设备可见性
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,RO

# 全局页缓存中正在等待/进行 writeback 的量，只是瞬时观察
grep -E '^(Dirty|Writeback):' /proc/meminfo
```

不要从单次 `Dirty: 0` 推断所有应用数据已经满足耐久协议；它只是全局瞬时统计，也不证明设备缓存已 flush。`stat` 中分配块的展示同样可能受压缩、共享 extent、网络文件系统或实现估算影响。

## 练习：为一次配置更新写崩溃协议

本练习只在纸面/笔记中推演，不执行写盘、mount、修复、格式化或断电测试。

1. 画出 buffered write 的完整路径：应用缓冲 → `write` → 页缓存 → 文件系统事务/CoW → 块层 → 设备缓存 → 非易失介质。在每条边上写出可能的错误或重排。
2. 某程序要把 `config.json` 原子替换为新版本。写出“同目录临时文件 → 完整写入 → 同步文件 → rename → 同步父目录”的状态机，并为每一步失败写出：旧版本是否仍可用、临时文件是否可能残留、程序应停止还是重试。
3. 对比 metadata journaling ordered mode、writeback mode 与 data journaling：分别说明 journal 里有什么、数据与元数据如何排序、崩溃后不能保证什么。
4. 画一棵三层 CoW 树，只修改一个叶块。标出哪些新块要写、旧根为何仍有效、快照会阻止哪些旧块释放。
5. 设计“发现 checksum mismatch”后的证据链：记录路径/设备/时间和只读日志，判断是否存在可信冗余，先保护可读数据，再进入该文件系统官方恢复流程。不要把“重新计算并覆盖 checksum”当作修复。
6. 为一个网络文件系统补充三问：`fsync` 成功到了客户端还是服务器哪一层？服务器是否有易失缓存？断线重试和多客户端缓存会怎样影响应用协议？

### 成功标准

- [ ] 能区分逻辑偏移、extent、文件系统块、设备地址和实际物理介质；
- [ ] 能说清 `fflush`、`write`、writeback、`fsync`、设备 flush 与断电恢复证据的层次；
- [ ] 知道同步文件内容后还可能需要同步父目录，且 `rename` 原子可见不等于已经耐久；
- [ ] 能解释日志 replay 保护文件系统结构事务，而应用仍需自己的事务协议；
- [ ] 能画出 CoW 的新块到新根提交路径，并列出快照的空间与故障域边界；
- [ ] 不会把 checksum 当成副本，也不会把 snapshot/RAID 当成已验证备份；
- [ ] 面对 NFS/FUSE 等实现时，会重新核对缓存、服务器/守护进程、同步和错误报告语义。

## 安全与恢复边界

本课只允许只读观察。不要在承载真实数据的设备上尝试 `mkfs`、分区工具、强制 `fsck`、强制挂载、日志清零、discard/TRIM、RAID 重建或模拟断电；也不要为“验证缓存”禁用写屏障或设备 flush。它们可能扩大损坏、覆盖恢复线索或让系统无法启动。

真正做崩溃一致性实验，应由 `计算机知识/80-实践/` 下的独立实验提供：使用无个人数据的可丢弃镜像/虚拟机，记录镜像校验和和重置点，限制写入目标，注入故障后只在副本上检查，并把“结构可挂载”“应用记录正确”“备份可恢复”设为三套不同验收标准。

## 参考资料

- [`fsync(2)`](https://man7.org/linux/man-pages/man2/fsync.2.html)、[`write(2)`](https://man7.org/linux/man-pages/man2/write.2.html)：写入返回、延迟错误、文件与目录同步的 Linux 接口边界。
- [ext4 JBD2 journal](https://docs.kernel.org/filesystems/ext4/journal.html)：commit、replay、checkpoint 与 data mode。
- [XFS documentation](https://docs.kernel.org/filesystems/xfs/index.html) 与 [XFS filesystem structure](https://www.kernel.org/pub/linux/utils/fs/xfs/docs/xfs_filesystem_structure.pdf)：allocation group、B-tree、extent 和日志机制。
- [Btrfs introduction](https://btrfs.readthedocs.io/en/stable/Introduction.html)、[Checksumming](https://btrfs.readthedocs.io/en/stable/Checksumming.html)、[Subvolumes](https://btrfs.readthedocs.io/en/stable/Subvolumes.html)：CoW、数据/元数据校验与“快照不是备份”。
- [OpenZFS Copy-on-Write](https://openzfs.github.io/openzfs-docs/Basic%20Concepts/Copy-on-write.html)：指针树、transaction group、checksum、snapshot 与同步写路线。
- [Apple APFS FAQ](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/APFS_Guide/FAQ/FAQ.html)：APFS 的 CoW、clone、snapshot 与元数据完整性边界。
- [Network filesystem caching API](https://docs.kernel.org/filesystems/caching/netfs-api.html)、[Linux FUSE documentation](https://docs.kernel.org/filesystems/fuse/fuse.html)：远端缓存与用户态守护进程怎样延伸文件 I/O 边界。

---

**上一站**：[[计算机知识/30-计算机系统/12-VFS文件描述符Inode目录与路径解析|VFS、文件描述符、inode、目录与路径解析]] · **下一站**：[[计算机知识/30-计算机系统/14-网络栈Socket与端到端数据路径|网络栈、Socket 与端到端数据路径]] · **性能连接**：[[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]] · **Linux 排障**：[[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|网络、存储、日志与故障排查]] · **返回**：[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/08-操作系统-课程地图|操作系统 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/02-操作系统原理/03-虚拟内存置换文件系统与崩溃边界|操作系统：虚拟内存、置换与崩溃一致性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND4 DEPTH LINKS -->
## 继续推演本页难点

[[计算机知识/20-操作系统/02-操作系统原理/10-系统课程/11-崩溃一致性与恢复状态机|rename 成功以后，断电重启一定还能看到新文件吗？]] 本专题补上状态转移、失败时间线及模型前提。

这不是替换本页：先掌握原理，再用补充页核对容易被一句话略过的条件。
<!-- END ROUND4 DEPTH LINKS -->

