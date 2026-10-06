---
type: lesson
domain: computer-science
stage: 10
status: ready
difficulty: 进阶
estimated_minutes: 80
topics:
  - I/O
  - 设备控制器
  - 总线
  - MMIO
  - PIO
  - DMA
  - IOMMU
  - 中断
tags:
  - computer-science/systems
  - computer-science/io
  - computer-science/hardware
---

# I/O、设备、总线、DMA 与中断

## 本课目标

学完后，你应该能够：

- 画出应用、系统调用、内核子系统、驱动、设备控制器和实际设备之间的 I/O 链路；
- 区分 port-mapped I/O、memory-mapped I/O（MMIO）与“CPU 普通读写 RAM”；
- 解释 DMA descriptor、device-visible address、scatter-gather 和 IOMMU 的职责；
- 区分 polling、interrupt、interrupt coalescing 与延迟处理的取舍；
- 不把 DMA 说成“完全不需 CPU”，也不把中断说成“设备直接运行用户回调”。

适用场景：理解 NVMe/网卡/GPU 驱动路径，分析高吞吐 I/O 队列，排查 DMA 映射、中断或设备超时问题，以及将 CUDA 的 host–device 数据移动放回整个系统中理解。

## 1. 三层语义不能混在一起

| 层次 | 回答的问题 | 典型边界 |
| --- | --- | --- |
| POSIX/用户空间抽象 | 进程如何用 FD、`read`/`write`、`mmap` 等请求 I/O？ | 不承诺底层是中断、轮询还是 DMA，也不暴露设备寄存器布局 |
| Linux 实现 | 哪个驱动管理设备？请求如何排队？DMA 映射和 IRQ 如何由内核 API 管理？ | 子系统、驱动 API、队列数量和绑定会随内核、配置、架构变化 |
| 硬件/总线协议 | 寄存器如何可见？事务怎样经过 PCIe/SoC interconnect？设备怎样发 DMA 和中断？ | 能力受设备、控制器、平台和协议版本约束，不能从 API 名称猜出硬件必然行为 |

文件描述符是进程与内核对象的句柄，不是 PCIe 总线地址。用户程序对 FD 调用 `read` 时，内核可以从已缓存的数据返回，也可以建立真实设备请求；这两条路径对该 POSIX 调用可以拥有相同的可见结果。

## 2. 从应用到设备的主链

```text
应用/库
  → 系统调用或受控的用户空间设备接口
  → Linux 内核子系统（文件、网络、块层、DRM 等）
  → 设备驱动构造请求和 descriptor
  → 通过 MMIO/PIO 通知设备控制器
  → 控制器通过总线/interconnect 执行事务和 DMA
  → 设备完成后写 completion，并可选发中断
  → 驱动回收请求，内核唤醒等待者或交付后续工作
```

这是常见高层模型，不是所有设备的唯一路径。例如，低速字符设备可以主要由 CPU 搬运少量字节；高速网卡、NVMe 和 GPU 通常使用多队列、DMA 与批处理。设备、驱动、firmware、`/sys` 与 `/dev` 的 Linux 观察路径见 [[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备驱动、内核模块与 udev]]。

## 3. 设备控制器把协议翻译成硬件动作

“设备”不必只是最终介质。常见链路中还有：

- **总线/互连**：PCIe、USB 或 SoC interconnect 等承载地址、命令、数据和完成事务；
- **控制器**：解释队列命令，管理实际介质/链路，更新状态并报告错误；
- **device firmware**：部分设备内部执行的程序，与 Linux 驱动、平台 UEFI 都不是同一物；
- **driver**：内核中懂得设备协议的软件，负责权限、队列、映射、超时、错误恢复与上层接口。

“总线带宽为 X”是理论链路能力的一个维度，不是单次 I/O 延迟、应用吞吐或有效 payload 带宽的直接承诺。协议开销、队列深度、命令尺寸、控制器、内存系统和上层锁竞争都会改变结果。

## 4. PIO 与 MMIO：CPU 怎样触达控制寄存器

### Port-mapped I/O（也常被称为一种 PIO）

某些 ISA 提供独立 I/O 地址空间和专用指令。CPU 对端口号执行读写，不把它当普通 RAM 地址。这种方式带有架构特异性，不应从 x86 经验推出所有平台都有同样端口空间。

### Memory-mapped I/O（MMIO）

设备的控制/状态寄存器被放进 CPU 地址空间的特定区域。指令形式可能像加载/存储，但语义不是普通内存：

- 读某个状态位可能有副作用，写入某个位可能是“写 1 清除”；
- 宽度、对齐、可合并性和访问顺序由设备/平台契约限定；
- 内核必须用架构适配的 MMIO accessor 和 barrier，不能仅靠普通指针或 C/C++ `volatile` 宣告设备顺序正确；
- 这些区域通常不应直接暴露给未受信任进程。

PIO 还常被宽泛地用于“CPU 亲自在设备数据寄存器与内存间搬数据”，与 DMA 对比。阅读文档时应先确认它是指端口地址空间，还是 CPU-driven data transfer，不要被同一缩写混淆。

## 5. DMA：让设备成为内存事务的发起者

在典型 DMA 路径中，CPU/驱动并没有消失：

```text
pseudocode: 概念性 DMA 提交

buffer = allocate_or_pin_memory()
device_address = dma_map(buffer, direction)
descriptor = {device_address, length, operation, request_id}
publish_descriptor_to_queue(descriptor)
memory_ordering_point_required_by_platform()
ring_device_doorbell()

... device reads descriptor and transfers data ...

completion = reap_completion()
dma_unmap(device_address, direction)
release_or_reuse(buffer)
```

CPU 仍负责准备缓冲、建立 DMA 映射、构造 descriptor、通知设备、处理 completion/错误并回收资源。DMA 减少的是 CPU 对大量 payload 的逐字节/逐字复制工作，不是所有 CPU 工作。

### Scatter-gather 与地址的三种视角

一段连续虚拟缓冲可以由多个不连续物理页组成。scatter-gather 列表让设备按多个段完成一个逻辑传输，减少为连续物理内存做额外拷贝的需求。必须分清：

1. CPU 进程使用的虚拟地址；
2. 内核管理的物理页/内存区段；
3. 设备发出事务时使用的 DMA address/IOVA。

三者不能直接互换，驱动应通过平台 DMA API 建立映射。还要区分内存一致 DMA 与需显式同步 cache 的 streaming DMA；具体要求取决于架构和平台。

### DMA 不自动等于 zero-copy

完整路径可能仍有：应用缓冲到内核缓冲的拷贝、bounce buffer、协议封装、设备内部拷贝或 GPU 显存中的再布局。“一次 DMA 发生了”只描述链路某一段，不能单独证明端到端零拷贝。

## 6. IOMMU：映射与隔离，不是“DMA 加速开关”

IOMMU 可以将设备看到的 I/O 虚拟地址（IOVA）翻译到授权物理页，并将不合法访问报告为 fault。它可用于：

- 限制设备只访问被映射的页，缩小错误/恶意 DMA 的影响面；
- 为虚拟机或设备直通构建独立地址域；
- 将设备可见的连续 IOVA 映射到不连续物理页。

但 IOMMU 不会修复驱动的生命周期错误，也不会为 DMA payload 自动加密。映射粒度、IOTLB、平台一致性与安全配置还可能影响成本。某个系统是否启用 IOMMU、设备是否经过这条翻译路径，必须现场确认。

## 7. 中断、轮询与批处理

### 中断是“有事情处理”的硬件通知

设备完成请求或发生错误后，可通过引脚信号或 MSI/MSI-X 等机制请求 CPU 处理。概念路径是：

```text
设备写 completion
  → 发中断请求
  → CPU 进入内核的中断处理路径
  → 快速确认来源/必要状态，护住队列
  → 把较长的 completion 回收交给延迟处理/轮询预算
  → 更新请求状态，唤醒线程或调用上层完成路径
```

中断处理不是进程的普通函数调用，也不会在设备完成的瞬间直接运行用户空间 callback。中间还有 IRQ 分发、驱动完成、调度与用户态返回边界。

### Polling 与 interrupt coalescing

- **中断为主**：空闲时 CPU 可做其他事，但每个事件的中断可在高吞吐下形成风暴；
- **轮询为主**：CPU 持续查队列，在高负载下可减少每件切换与尾延迟，但空载会消耗 CPU/能源；
- **coalescing/moderation**：累积多个 completion 后再通知，降低中断率但可能增加单个请求等待；
- **混合方式**：先中断唤起，高负载期限额轮询一批，没有更多工作后恢复中断。

没有一种模式在低延迟、高吞吐、低 CPU 占用和低功耗上同时最优。应用指标、工作负载和设备队列证据才能决定。

## 8. Queue、descriptor、doorbell 与 completion

现代高速设备常用内存中的环形队列：

```text
submission queue in memory
  [descriptor A][descriptor B][free]...
        ^ producer tail

driver 写好 descriptor → 执行规定顺序操作 → MMIO doorbell 通知新 tail
device 取 descriptor → DMA/execute → 在 completion queue 写 request_id/status
driver 通过中断或 polling 回收 completion
```

多队列可降低多核共享一把锁的竞争，并让 MSI-X vector/CPU affinity 与工作队列配合。但队列越多不等于吞吐无限提升：设备内部并行度、总线、内存带宽、NUMA 位置、中断分布和软件批处理都会成为上限。

## 9. 可观察小例子：一个读请求的两条时间线

假设应用请求的数据当前不在内核缓存：

| 阶段 | 应用线程 | CPU/内核 | 设备 |
| --- | --- | --- | --- |
| 提交 | 进入读接口 | 验证参数，建请求、DMA 映射和 descriptor | 未执行 |
| 启动 | 可能阻塞，也可能已返回异步提交结果 | 发 doorbell，可调度其他工作 | 取 descriptor，读取介质并 DMA 到映射页 |
| 完成 | 尚未必然运行 | IRQ 或 poll 发现 completion，完成请求 | 写 completion，可发中断 |
| 交付 | 被唤醒后竞争 CPU，最终取得数据 | 做必要的同步/拷贝并返回用户态 | 可已处理其他请求 |

若数据已在页缓存，就可能绕过“设备执行”阶段而直接交付。因此，同一个应用 `read` 的延迟可以相差很大；不先辨别 cache hit/miss，就不能只归因于磁盘或中断。

## 10. 一条危险故障链：descriptor 没有真正就绪

```text
驱动在内存中填 descriptor 的地址/长度
  → 缺少平台要求的 DMA/MMIO 顺序保证
  → doorbell 事务先于 descriptor 最终可见性到达设备
  → 设备取到旧地址或旧长度
  → IOMMU 可拒绝为 fault；无有效隔离时则可能破坏无关内存
  → 请求超时、设备 reset，上层看到 I/O error 或数据损坏
```

修复不是随意加一个语言级 `volatile`，而是使用该内核/平台对 DMA 与 MMIO 规定的 accessor、mapping 和 ordering primitive，并定位映射生命周期。同时要留存 IOMMU fault、设备 status、超时前后 completion 队列与内核日志的时间关系。

## 11. 与 CUDA 的连接

CUDA 中的 host-to-device/device-to-host 传输会经过具体平台链路，通常需驱动建立映射并调度 copy engine/DMA。但需要保留三条边界：

- page-locked/pinned host memory 会在保持锁页的生命周期内阻止相关页被换出，并让驱动建立或复用适合 DMA 的设备可见映射；它不表示物理连续、IOVA 永久不变或传输必然与 kernel 重叠，过量 pin 还会压缩操作系统可回收内存；
- `cudaMemcpyAsync` 的 API 名称不承诺真实 overlap，还需 pinned memory、可用 copy engine、没有隐式依赖并用 timeline 验证；
- CUDA event/stream 表达 device 工作依赖，不等于 CPU IRQ；两者可在实现链上相关，却属于不同抽象层。

完整的 CUDA 异步条件见 [[计算机知识/40-并行与异构计算/01-CUDA/06-Stream-Event与异步流水线|Stream、Event 与异步流水线]]，host/device 成本模型见 [[计算机知识/40-并行与异构计算/01-CUDA/01-CPU与GPU异构执行模型|CPU 与 GPU 异构执行模型]]。

## 练习

1. 为一次 NVMe 读画出“应用 → 内核块层 → NVMe driver → submission queue/doorbell → controller DMA → completion/interrupt → 唤醒应用”，标出 CPU 工作和设备工作。
2. 解释 CPU 虚拟地址、物理页与 IOVA 为何不能互换；再说明 IOMMU 在驱动使用了已解除映射地址时可能产生什么证据。
3. 对“每秒 10 个事件”和“每秒数百万个小 completion”比较纯中断、纯轮询和混合批处理，分别写出延迟、CPU 占用和吞吐取舍。
4. 审查“设备是 DMA，所以 CPU 完全不参与且是 zero-copy”这句话，列出至少五个需补充证据的环节。
5. 把本课故障链改写成一张证据表：每层列出预期状态、失败现象和能排除的假设。

## 成功标准

- 你能完整画出“用户 API → Linux 子系统/驱动 → 设备控制器/总线”，不把 FD 当设备地址；
- 你能区分 MMIO、port I/O 和 CPU-driven data transfer 几种语境；
- 你能说清 DMA 映射、descriptor、doorbell、completion 和 IOMMU 各自的作用；
- 你知道中断、polling 和 coalescing 是延迟/吞吐/CPU 成本的取舍，不是一个绝对排名；
- 你不会把 pinned host memory 推广为物理连续、IOVA 永久固定或异步传输必然与 kernel 重叠；
- 你不会用 C/C++ `volatile` 替代驱动所需的 DMA/MMIO 映射与顺序协议。

---

**上一站**：[[计算机知识/30-计算机系统/09-进程线程调度同步与IPC|进程、线程、调度、同步与 IPC]] · **下一站**：[[计算机知识/30-计算机系统/11-存储设备块层页缓存与持久化|存储设备、块层、页缓存与持久化]] · **Linux 连接**：[[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备驱动、内核模块与 udev]] · **C++ 连接**：[[计算机知识/10-编程语言/02-C++/09-内存布局ABI缓存与SIMD|内存布局、ABI、缓存与 SIMD]] · **返回**：[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。


## 电子电路往返：采样率、复用期限和DMA所有权

去 [[电子电路/44-嵌入式采集与控制/03-定时中断DMA与实时预算#采样时刻不是中断时刻|采样与IRQ两条时间线]]，带采样 $t[n]=t_0+nT_s+\varepsilon[n]$（s）、四点一块B=4、Ts=1 ms、两槽，以及每块处理C和最坏IRQ延迟J（s）。本页descriptor/completion说明谁启动、谁观察完成；返回 [[电子电路/44-嵌入式采集与控制/03-定时中断DMA与实时预算#从块周期推出最坏预算|最坏时刻递推]] 用 $f_k=\max(r_k+J,f_{k-1})+C$ 与槽复用 $d_k=(k+2)BT_s$ 比较。IRQ入口不是四个样本的共同采样时刻，DMA减少payload搬运不承诺实时期限。

在无额外等待、顺序处理、相同有界J/C的教学条件下，C≤BTs可避免服务积压；两槽仍需首块J+C≤BTs并满足后续每块期限。实际干扰、中断屏蔽、总线仲裁或DMA不可达区域要写入更强模型。缓存可见性是另一条件，去 [[电子电路/44-嵌入式采集与控制/03-定时中断DMA与实时预算#内存可见性与 cache 是另一个合同|cache与发布顺序]] 带回平台规定的同步；逻辑所有权FREE/READY不是cache维护命令。环形DMA未必停写，不能把软件队列满当外设ready回压。

**迁移1。** B=8、Ts=.5 ms、J=.6 ms、C=2.5 ms、两槽，第一块何时完成/复用，最旧和最新样本年龄多少？**答案：** r0=4 ms，完成7.1 ms，复用8 ms，裕量.9 ms；样本0..7在0..3.5 ms，年龄7.1及3.6 ms。只把C=2.5 ms报告成端到端延迟会漏采集与IRQ等待。

**迁移2。** 改C=4.5 ms，增加100个缓冲槽；长期能无丢失吗？**答案：** 到达每4 ms一块而服务需4.5 ms，积压净增，任何有限槽最终耗尽。增加容量可吸收有界突发但不能改长期服务率；需减少工作、降低采样或定义丢弃/停机与epoch策略。按具体设备完成可见性后再发布，不能用volatile替代cache或内存序。
