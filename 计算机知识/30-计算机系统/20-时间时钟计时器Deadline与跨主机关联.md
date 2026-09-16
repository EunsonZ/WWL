---
type: lesson
domain: computer-science
stage: 20
status: ready
difficulty: 进阶
estimated_minutes: 100
topics:
  - Realtime
  - Civil Time
  - Monotonic Clock
  - CPU Time
  - GPU Clock Domain
  - Timer
  - Deadline
  - NTP
  - PTP
  - 分布式追踪
tags:
  - computer-science/systems
  - computer-science/time
  - computer-science/distributed-systems
  - computer-science/performance
---

# 时间、时钟、计时器、Deadline 与跨主机关联

## 本课目标

学完后，你应该能够：

- 区分 realtime、civil time、monotonic、boottime、进程/线程 CPU time 与 GPU clock domain；
- 解释硬件计数器、内核 timekeeping、读取时钟和 timer 唤醒之间的关系；
- 用绝对 deadline 和剩余预算设计多层调用，不把每层 timeout 误当端到端保证；
- 识别 suspend、时钟校准、DVFS、异步 GPU 提交和虚拟机迁移对测量的影响；
- 在跨主机日志与 trace 中显式保留同步误差，而不是把 wall timestamp 当因果顺序。

> [!prerequisite] 前置知识
> [[计算机知识/30-计算机系统/08-异常中断系统调用与特权级|异常、中断、系统调用与特权级]]解释 timer event 如何让 CPU 转向内核，[[计算机知识/30-计算机系统/09-进程线程调度同步与IPC|进程、线程、调度、同步与 IPC]]解释唤醒后为何还需等待调度，[[计算机知识/30-计算机系统/15-性能分析可观测性与系统设计|性能分析、可观测性与系统设计]]使用 wall/CPU time 和 latency budget。本页建立这些概念的统一时间模型。

> [!warning] 操作边界
> 本页与配套实践不修改系统时间、时区、NTP/PTP、timer frequency、CPU/GPU 频率或虚拟机设置。改系统时间会影响 TLS、日志、数据库、构建、缓存与分布式协议；生产时间同步必须由平台负责人按变更流程执行。

## 1. “现在几点”和“过去多久”是两类问题

时钟 API 最常见的错误，是拿能映射到日历的 clock 测持续时间，或拿只保证本机递增的 clock 当跨主机时间戳。

| 时间概念 | 主要问题 | 典型用途 | 主要风险 |
| --- | --- | --- | --- |
| Realtime / wall clock | 当前相对于某个 epoch 是何时？ | 日志、协议日期、证书有效期、文件时间 | 可被校准、跳变或调整；不是稳定 duration clock |
| Civil time | 某地区日历显示什么日期时间？ | 用户日程、营业时间、法规日期 | 时区规则/DST 会变化；本地时间可重复或不存在 |
| Monotonic clock | 本机从某个未指定起点单调经过多久？ | duration、timeout、deadline | 不能转成跨主机日历时间；是否含 suspend 依 clock/API |
| Boottime 类 clock | 自启动起经过多久，常含 suspend | 租约、开机时长、希望跨 suspend 的 deadline | 平台支持与语义不同；不等于 UTC |
| Process CPU time | 本进程线程实际获得多少 CPU 执行时间？ | CPU 成本分析 | 不含睡眠/多数 I/O 等待；多线程可累计得快于 wall time |
| Thread CPU time | 当前线程获得多少 CPU 执行时间？ | 单线程热点/配额分析 | 不代表进程总成本或用户延迟 |
| GPU/device clock | 设备自己的时间戳/周期域 | kernel timeline、设备事件 | 与 host clock 不同域；DVFS、wrap、校准与 API 同步语义需确认 |

Python 的 `time.time()`/`time.time_ns()`通常读取 realtime；`time.monotonic()`和 `time.perf_counter()`用于经过时间，后两者在某平台可能共享实现，但 API 承诺不同。`process_time()`和 `thread_time()`测 CPU time。应以 `time.get_clock_info()`和平台文档核验实现，不能从函数名猜是否含 suspend。

## 2. Civil time 不是一个简单整数

用户说“2026-11-01 01:30”时，缺少时区和时区数据库版本。实行 daylight saving time 的地区可能在回拨时出现两次 01:30，在前拨时让一段本地时间根本不存在。未来的政治决定还可能更新时区规则。

稳健数据模型通常分别保存：

- 表示瞬间的 UTC/epoch 时间或带 offset 的时间戳；
- IANA time zone ID，例如 `Asia/Shanghai`，用于按相应规则展示；
- 对未来日程，保留“当地 09:00”这一 civil intent，因为未来规则变化后简单固定 UTC 可能偏离用户意图；
- 必要时记录解析歧义选择和 tzdb 版本。

时区 offset（如 `+08:00`）不是完整时区规则。服务器统一记录 UTC 有利于关联，但面向人的计划仍需保留原始时区语义。

### Leap second 与 POSIX 时间边界

UTC 会处理 leap second，而常见 POSIX timestamp 模型并不唯一表示每个 UTC leap second；系统可能 step、slew 或采用 leap smear。不同服务策略不一致时，同一真实事件的 wall timestamp 可能产生偏差。对需要严格时间尺度的测量，应明确 UTC、TAI、GPS 或设备时间等尺度，而不是只写“纳秒时间戳”。

## 3. 从硬件计数器到操作系统时钟

硬件提供递增计数来源，例如架构 counter、TSC、HPET 或设备 counter。内核选择 clocksource，维护“计数差 → 纳秒”的比例与基准，并把同步服务的校准以 step 或逐渐调速等方式作用到 realtime/timekeeping。

```text
硬件 counter
  → 内核 clocksource 与换算参数
  → realtime / monotonic / boottime 等逻辑 clock
  → vDSO 或 syscall 暴露给进程
```

现代系统常通过 vDSO 在用户态读取共享 timekeeping 数据，避免每次读时间都陷入内核；但实现依平台和 clock 类型而异。读 clock 很快也不代表零开销，更不代表纳秒字段具有纳秒级准确度。至少区分：

- **resolution：**API 可表示或时钟可分辨的最小变化；
- **precision：**重复测量的离散程度；
- **accuracy：**与目标时间尺度真实值的接近程度；
- **stability：**频率随温度、功耗、时间等变化的程度。

返回整数纳秒只说明表示单位，不证明硬件/同步准确到 1 ns。

### TSC、跨核与频率变化

现代 x86 常提供 invariant/constant-rate TSC 并由 OS 校准和同步使用，但虚拟化、旧硬件、固件或迁移仍可能改变保证。CPU 核心 DVFS 改变执行吞吐，不必等比例改变架构时间 counter。不要用“CPU 当前 3 GHz”把任意 cycle counter 直接换算为 wall time；应使用文档化的 clock 或性能计数器语义。

## 4. 读时间不等于获得 timer 唤醒

Clock 回答时间值；timer 表示“达到某个时间条件后通知或唤醒”。内核把 timer 放入数据结构，并根据最近 expiry 配置硬件 timer 或 tickless 调度。到期通常只意味着任务变为 runnable 或回调可执行，不意味着用户代码在该纳秒立即运行：

```text
设置 expiry
  → 内核 timer queue
  → 硬件事件 / 时钟事件
  → 中断与内核处理
  → 任务变 runnable
  → 调度器选择 CPU
  → 用户代码实际继续
```

实际唤醒延迟还受 CPU 负载、优先级、power state、timer coalescing、虚拟机 vCPU 调度和运行时 event loop 影响。因此 `sleep(10ms)`通常承诺“至少不早于某边界继续尝试”，不是“精确暂停 10ms”。

系统会合并 timer 来降低唤醒与功耗，实时系统则可能为确定性付出吞吐、能耗与配置复杂度。高分辨率 timer 也不会消除调度排队。

## 5. Monotonic duration：测量本机经过时间

测量一段代码的 wall duration，使用同一 monotonic clock 的差值：

```python
start = time.monotonic_ns()
result = do_work()
elapsed_ns = time.monotonic_ns() - start
```

需要先定义边界。异步 GPU launch、异步文件/网络 I/O 和线程池 submission 可能很快返回，却只代表工作已提交。若目标是设备 kernel 完成时间，必须使用该设备 API 的 event/timestamp 与必要同步；若目标是端到端用户延迟，则同步等待本来就是边界的一部分，不能为了得到漂亮数字而删掉。

`process_time_ns()`可帮助区分进程用 CPU 与等待，但不能直接从 `wall - process CPU` 得出“I/O 时间”：其中还包括调度等待、其他进程竞争、sleep、锁、page fault、设备与 runtime 活动；多线程 CPU time 的累计也可能超过 wall duration。

### Suspend 是否计入必须明确

一些 monotonic clock 在 suspend 时停止，boottime 类 clock 继续累计。一个“10 分钟后提醒”和“最多占用 10 分钟 CPU”显然需要不同 clock。语言标准库可能不暴露所有原生 clock，因此必须记录 API 和平台，而不是笼统写“用了 monotonic”。

## 6. Deadline 比逐层重置 timeout 更能保持端到端预算

**Timeout**通常是从某一层开始允许等待多久；**deadline**是按同一 clock domain 表示的最晚完成时刻。假设请求总预算 1000 ms，依次经过排队、服务 A、服务 B：

```text
错误：每层各自 timeout=1000ms
排队 700 + A 等 1000 + B 等 1000 → 端到端可能远超 1000ms

正确主线：入口建立 deadline=D
每层开始时 remaining=max(0, D-monotonic_now)
排队、重试、RPC、设备等待都从同一剩余预算中消费
```

跨进程/跨主机传播绝对 monotonic 数值通常无效，因为 monotonic epoch 是本机私有。常见协议做法是传播剩余 timeout/budget，并在接收端立即用自己的 monotonic clock 建立本地 deadline；传输和排队已经消耗的时间、时钟误差与协议编码都需要安全余量。若协议传播 wall-clock deadline，则必须把同步不确定性纳入拒绝/提前截止策略。

### 预算不能全部交给最深一层

每层要预留：

- 返回与序列化时间；
- 取消传播和资源清理；
- 可能的一次有条件重试；
- 调度/网络抖动；
- 上游形成明确错误响应的时间。

例如入口剩余 300 ms 时，不应把下游 timeout 也设 300 ms，再期待超时后还能完成 fallback 和响应。安全 margin 应来自延迟分布和失败策略，而不是固定拍脑袋常数。

## 7. 正确实现 deadline 等待循环

等待可能因为信号、spurious wakeup、部分进度或无关事件提前返回。循环应反复计算剩余预算，而不是每次重新使用原 timeout：

```python
deadline_ns = time.monotonic_ns() + budget_ns
while not condition_ready():
    remaining_ns = deadline_ns - time.monotonic_ns()
    if remaining_ns <= 0:
        raise TimeoutError
    wait_for_condition(timeout=remaining_ns / 1_000_000_000)
```

还要检查 API 使用相同 clock：某些条件变量或 timer 接口允许选择 realtime/monotonic，某些则由平台固定。算术要处理单位、溢出、负剩余时间和极大 timeout；相对 duration 更适合用整数纳秒或有单位类型，避免毫秒/秒混用。

deadline 到达后，正在运行的工作不会自动消失。上游需传播取消，底层需在安全点检查；不能取消的设备/系统调用仍可能完成。此时应丢弃过期结果、释放资源，并防止重试与迟到结果共同产生重复副作用。

## 8. Timeout 是未知结果，不总是失败结果

网络调用超时时，请求可能：

1. 尚未发送；
2. 部分发送；
3. 已被服务执行，但响应丢失或太晚；
4. 服务仍在后台运行；
5. 已完成并持久化，只是客户端不知情。

所以 retry 必须与幂等键、去重、查询状态和总 deadline 一起设计。把 timeout 记为“下游没有执行”会导致重复扣款、重复任务或相互覆盖。取消也不是回滚；它只是请求尽早停止，业务副作用需要事务/补偿语义。

## 9. CPU 与 GPU 是不同 clock domain

GPU 工作常由 CPU 异步提交到 queue/stream。涉及至少三条时间线：

```text
host monotonic clock：API 调用、排队、等待、端到端
GPU device clock：kernel/event 在设备时间域中的开始与结束
外部 trace clock：采集器把 host、driver、device 事件相关联后的 timeline
```

只测 CPU 侧 launch 前后通常得到 submission overhead，不是 kernel duration。设备 event 能测同一设备/stream 上定义的间隔，但跨 stream、跨 GPU 或 host-device 对齐要遵守 API 的同步与校准规则。GPU DVFS 会改变“多少 device cycles 完成工作”，而 event API 是否直接给稳定时间单位由平台定义。

Profiler 展示在一张时间轴上，不代表所有原始 timestamp 天然同域；工具可能周期性校准、插值并报告误差。多 GPU collective 还涉及网络/NIC clock、GPU clock 与 host clock。比较微秒级空隙前应记录 profiler 版本、timestamp 精度、是否 replay、采样与校准方式。

### 测量边界示例

| 想回答的问题 | 应包含的边界 | 不充分的测法 |
| --- | --- | --- |
| 单个 GPU kernel 设备执行多久 | 正确 stream 中的 device events/工具 timestamp，并满足同步要求 | CPU 侧 launch 调用差值 |
| 一次推理用户等待多久 | 请求入口到结果可消费的 host monotonic duration | 只加所有 kernel duration |
| GPU 是否空闲等待 CPU | 相关联的 host/driver/device timeline | 单一 utilization 百分比 |
| 多机 collective 哪台先慢 | 每机本地 duration + 同步误差范围 + collective/trace ID | 直接排序不同主机 wall timestamp |

## 10. 虚拟机、容器与时间

容器通常读取宿主内核提供的 clock，但 time namespace 可为部分 clock 提供 offset 视图；这不使容器获得独立物理 oscillator。容器内改 timezone 只影响 civil 展示配置，不应与修改宿主 realtime 混为一谈。

VM 的虚拟 clock 要处理 vCPU 未运行、宿主 suspend、CPU 热迁移与 live migration。hypervisor 和 guest OS 会利用硬件/虚拟 time source 维持单调性和 wall clock 校准，但迁移前后 counter offset、频率与同步质量必须由平台机制保证。对严格 deadline/lease 协议，应查所用 hypervisor 与 guest clocksource 文档并做故障测试，不能假定“虚拟机里的 TSC 与裸机完全一样”。

checkpoint/restore 也会让进程在 wall time 上消失一段时间。恢复后一个本机 deadline 是否已经过期，取决于所选 clock 是否包含暂停与运行时如何恢复 timer；这是业务策略，不能交给偶然 API 行为。

## 11. 跨主机同步：得到的是误差范围，不是真正共享时钟

每台机器有自己的 oscillator，会产生 offset（相对参考的时间差）与 frequency error/drift（走时速率误差）。NTP 类协议通过网络交换 timestamp 估计 offset 与 delay，再调整本机 clock；PTP 配合硬件 timestamp 和受控网络可达到更高精度。两者都受路径不对称、排队、timestamp 位置、holdover、拓扑和故障影响。

若往返时间 RTT 为 4 ms，简单假设单程各 2 ms 只是**对称路径假设下的估计**。请求去程可能 0.5 ms、回程 3.5 ms；仅凭两个端点 timestamp 无法唯一求出单程延迟。同步系统应输出当前 offset/uncertainty/stratum 或相应质量指标，应用再根据风险设边界。

### Wall timestamp 不提供因果顺序

机器 A 的日志时间 `10:00:00.100`、B 的 `10:00:00.099` 不证明 B 的事件先发生：同步误差可能大于 1 ms。消息传递提供更强的因果事实：发送必须先于接收。Lamport clock 可保持这种 happens-before 顺序；vector clock 能表达更丰富并发关系；hybrid logical clock 结合近似物理时间与逻辑顺序。它们解决的是排序/因果元数据，不替代 duration 测量或 UTC 展示。

## 12. 跨主机 trace 如何诚实关联

分布式 trace 常把 span wall timestamp 投影到一条轴上。若服务 A/B offset 不同，子 span 可能看起来早于父 span，或网络耗时为负。稳健证据应包含：

- trace/span/parent ID，先用因果边建立结构；
- 每个进程内部用 monotonic clock 测 duration；
- wall timestamp 用于粗时间窗与跨系统检索；
- 主机、进程启动标识与 clock domain；
- 时间同步状态、估计 offset 与 uncertainty；
- 采集/导出延迟，避免把日志到达顺序当事件顺序。

若 A 的事件区间是 `[t_A-ε_A, t_A+ε_A]`，B 类似，两个区间重叠时就不应仅凭 wall time 排序。高精度需求可在同一请求的往返握手中估计局部映射，但路径不对称仍形成误差下界。

### 用关联而不是伪造精度

一次多机 LLM 推理可记录：request ID、每机本地 queue/prefill/collective/decode duration、collective sequence、设备 event 与同步质量。这样即使 wall clock 不能精确到微秒，也能判断“同一 collective 中 rank 3 本地等待更久”。把所有 timestamp 格式化为九位小数并不会增加真实准确度。

## 13. 时间故障的可观察性

至少监控：

- 同步 daemon 是否有有效上游；
- offset、frequency correction、round-trip delay、uncertainty 与上次成功更新时间；
- clock step/slew、源切换、leap 状态和 VM migration/suspend 事件；
- 应用层 deadline exceeded、排队过期、取消传播与迟到完成；
- trace 中负 duration、子 span 越界与主机集中异常；
- CPU/GPU profiler 的 clock calibration 警告。

出现时钟异常时，不要先手工强制设时钟来“让图好看”。先保护原始日志和同步状态，判断证书/租约/数据库等风险，按平台流程恢复；手工 step 可能破坏取证并制造第二次跳变。

## 14. 只读观察与配套实践

Python 标准库可在不改时钟的情况下报告 clock 属性：

```python
import time

for name in ("time", "monotonic", "perf_counter", "process_time", "thread_time"):
    try:
        info = time.get_clock_info(name)
    except ValueError:
        print(f"{name}: SKIP")
    else:
        print(name, info.monotonic, info.adjustable, info.resolution)
```

`adjustable=False`表示该 clock 不能被跳变式设置；Python 的这个字段不描述 NTP 式渐进频率校正。它也不表示频率绝对无误差，更不说明 suspend 语义。运行 [[计算机知识/80-实践/06-计算机系统/07-资源视图与时间预算/README|资源视图与时间预算]] 可同时看到本机 clock 属性、sleep/CPU time 差异、absolute deadline 剩余预算，以及 Linux 当前 cgroup 视图。非 Linux 的 cgroup 部分会明确 `SKIP`。

## 15. 练习与成功标准

1. 为“每天本地 09:00 运行”“收到请求后 500 ms 截止”“最多使用 100 ms CPU”“GPU kernel duration”分别选择 clock/domain，并解释为什么不能互换。
2. 将三层各 1 s timeout 的伪代码改为入口 deadline + 每层剩余预算；加入 100 ms 清理/返回余量，并解释 retry 如何消费总预算。
3. 画出 host submission、GPU stream、device event 和 host completion 四个事件；分别给出 submission latency、kernel device duration 和端到端 latency 的测量边界。
4. 两台主机同步误差各为 ±2 ms，日志相差 1 ms。写出为何无法仅凭 timestamp 排序，并给出 trace ID + 消息因果的替代证据。
5. 成功标准：配套 unittest 全部通过或按平台明确 `SKIP`；能解释 clock 的 monotonic/adjustable/resolution 不等于 accuracy；没有修改系统时间或同步设置。

## 16. 易错点回顾

- realtime 适合日期关联，不适合可靠 duration/deadline；
- civil time 需要时区规则，offset 不是完整时区；
- monotonic epoch 只在本机 clock domain 有意义，不能直接跨主机传播绝对值；
- timer 到期只让工作有机会运行，不保证准点执行；
- 每层重置 timeout 会突破端到端预算；deadline 到达也不会自动撤销副作用；
- CPU time、host wall time 和 GPU device time 是不同口径；
- NTP/PTP 降低 offset，但跨主机 timestamp 仍带不确定性；
- trace ID 和消息因果比微秒小数位更可靠，duration 应尽量在同一主机/clock 上测量。

---

**上一站**：[[计算机知识/30-计算机系统/19-容器虚拟机Namespace-Cgroup与虚拟IO|容器、虚拟机、Namespace、Cgroup 与虚拟 I/O]] · **实践**：[[计算机知识/80-实践/06-计算机系统/07-资源视图与时间预算/README|资源视图与时间预算]] · **返回**：[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]] · **相关**：[[计算机知识/30-计算机系统/15-性能分析可观测性与系统设计|性能分析、可观测性与系统设计]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
