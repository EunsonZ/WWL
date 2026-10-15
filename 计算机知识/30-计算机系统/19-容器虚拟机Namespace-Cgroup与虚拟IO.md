---
type: lesson
domain: computer-science
stage: 19
status: ready
difficulty: 进阶
estimated_minutes: 100
topics:
  - Namespace
  - Cgroup v2
  - Capability
  - Seccomp
  - LSM
  - 虚拟机
  - Virtio
  - GPU 隔离
tags:
  - computer-science/systems
  - computer-science/virtualization
  - computer-science/security
  - computer-science/io
---

# 容器、虚拟机、Namespace、Cgroup 与虚拟 I/O

## 本课目标

学完后，你应该能够：

- 分清“看到不同对象”“只能使用一定资源”“不能执行某类操作”和“运行另一套内核”四种不同机制；
- 解释 Linux namespace、cgroup v2、capability、seccomp 与 LSM 如何叠加，而不是把其中任意一层称为完整沙箱；
- 从 guest virtual address 追踪到 host physical address，并说明 VM exit、设备模拟、virtio 与设备直通的取舍；
- 解释容器为何复用宿主内核，以及 GPU 容器为何仍依赖宿主驱动；
- 只读解释进程在容器或 cgroup 中实际看到的 CPU、内存、PID 与 I/O 资源视图。

> [!prerequisite] 前置知识
> 先理解 [[计算机知识/30-计算机系统/02-进程虚拟地址空间与内存映射|进程虚拟地址空间与内存映射]]、[[计算机知识/30-计算机系统/08-异常中断系统调用与特权级|异常、中断、系统调用与特权级]]和 [[计算机知识/30-计算机系统/10-IO设备总线DMA与中断|I/O、设备、总线、DMA 与中断]]。本页讲机制，不是 Docker、Kubernetes 或某个云平台的命令教程。

> [!warning] 安全与实验边界
> 本页只允许读取当前进程可见的 `/proc` 与 cgroup/sysfs 状态。不要为了练习创建特权容器、挂载宿主根目录、开放设备节点、修改 cgroup、加载 BPF、改变 LSM/seccomp 策略、写 namespace 映射或配置设备直通。错误配置可能越权、杀死进程、造成资源争用或影响整台宿主机。

## 1. 先拆开四个经常混在一起的问题

“把程序隔离起来”不是单一操作。至少要分别回答：

| 问题 | 主要机制 | 它直接提供什么 | 它不自动提供什么 |
| --- | --- | --- | --- |
| 进程看见哪些对象？ | namespace | PID、挂载、网络、主机名等不同视图 | CPU/内存上限、完整安全策略 |
| 进程能消耗多少资源？ | cgroup v2 | 分组统计、权重、上限、压力与回收边界 | 文件/网络对象隐藏、syscall 语义隔离 |
| 进程能执行哪些敏感动作？ | capability、seccomp、LSM、DAC | 权限拆分、syscall 过滤、对象访问策略 | 另一套内核、无限资源下的可用性保护 |
| 是否运行独立内核？ | 虚拟机 | guest 内核与虚拟硬件边界 | 零开销、自动安全、自动高性能 I/O |

典型 Linux 容器把普通进程放进若干 namespace 与 cgroup，配置凭据、capability、seccomp 和 LSM，再准备 root filesystem。它仍在**宿主内核**上执行系统调用。典型硬件虚拟机则运行自己的 guest 内核；hypervisor/host 为它提供虚拟 CPU、内存和设备。

因此，“容器像一台轻量虚拟机”只适合描述使用感受，不适合作为机制解释。容器逃逸通常意味着跨过共享宿主内核或运行时边界；guest 内核漏洞首先影响该 guest，而 hypervisor、虚拟设备和共享服务仍是 VM 的攻击面。

## 2. Namespace 隔离的是名字与视图

Linux namespace 让同一内核中的进程对某类全局资源拥有不同视图。常见类型包括：

| Namespace | 隔离的主要视图 | 容易误解之处 |
| --- | --- | --- |
| PID | 进程 ID 层级与可见性 | 同一任务可在嵌套层级拥有不同 PID；最内层 PID 1 还有信号与回收职责 |
| mount | 挂载表与传播关系 | 不是复制整个文件系统；共享挂载传播配置仍可能带来跨边界影响 |
| network | 接口、地址、路由、端口、netfilter 等网络状态 | `127.0.0.1` 指向当前 network namespace 的 loopback，不是宿主服务 |
| IPC | System V IPC 与 POSIX message queue 等对象 | 不限制 CPU、内存或普通文件 |
| UTS | hostname 与 NIS domain name | 改名字不等于网络或身份安全 |
| user | UID/GID 映射及 namespace 内 capability | namespace 内的 `root` 不必等于宿主 UID 0，但映射和内核接口仍需正确约束 |
| cgroup | 进程看到的 cgroup 层级视图 | 不是资源 controller 本身 |
| time | 部分 monotonic/boottime offset 视图 | 不等于任意改宿主时钟，也不消除分布式时钟误差 |

namespace 可以组合，也可以分别共享。例如进程可共享 network namespace，却拥有不同 mount namespace。安全评审必须写出实际组合，不能只说“已启用 namespace”。

### PID 视图不是调度隔离

容器内 `ps` 只看到少量 PID，不表示这些进程独占 CPU。PID namespace 管名字；CPU 调度份额和配额由调度器与 cgroup、亲和性、cpuset 等共同决定。相反，设置 CPU quota 也不会自动隐藏宿主 CPU 拓扑：某些语言运行时若只依据 `os.cpu_count()` 建线程池，可能创建远多于配额能并行运行的线程。

### Mount 视图不是不可变边界

只读 bind mount 能限制某个挂载视图上的写入，但进程是否还能经别的路径、文件描述符、设备、网络服务或内核接口修改状态，要继续检查。挂载传播、`/proc`/`/sys` 的选择、设备节点与 capability 都会改变边界。

## 3. Cgroup v2：统一层级上的计量、分配与约束

cgroup v2 在统一层级中组织进程，并由 controller 管理资源。一个服务实际可用资源取决于它所在叶节点、祖先限制、在线 CPU、亲和性、NUMA、系统压力和调度竞争；不能只读一个数字。

常见只读文件及正确解释：

| 文件 | 含义 | 不能草率推出的结论 |
| --- | --- | --- |
| `cpu.max` | quota 与 period；`max` 表示该层没有 CPU 带宽硬上限 | `200000 100000` 表示最多约 2 个 CPU 的时间预算，不保证同时占有两颗物理核 |
| `cpu.weight` | 同层竞争时的相对权重 | 权重不是硬上限；空闲时可能使用更多 CPU |
| `cpuset.cpus.effective` | 祖先与当前配置作用后的有效 CPU 集 | 列出 8 个 CPU 不表示 quota 允许持续使用 8 CPU |
| `memory.current` | 当前记账内存 | 不等于某个进程 RSS，也不能与宿主 `free` 直接相减解释 |
| `memory.high` | 内存压力/回收的软节流边界 | 超过不一定立即 OOM |
| `memory.max` | 该 cgroup 的硬上限 | `max` 只表示本层无限；祖先与宿主仍有限 |
| `memory.events` | low/high/max/oom/oom_kill 等累计事件 | 孤立累计值不能定位发生时间或责任请求 |
| `pids.current` / `pids.max` | 当前任务数及上限 | “任务”与用户看到的进程数、线程数不必一一相同 |
| `io.max` / `io.stat` | 按设备的 I/O 限制与累计统计 | 页缓存命中、设备共享、写回与文件系统会改变应用观察到的延迟 |

多个限制共同作用。例如进程的 affinity 允许 CPU `0-7`，cpuset 有效集是 `2-5`，`cpu.max` 约等于 2 CPU：它只能在交集中被调度，并在每个 quota 周期受到约 2 CPU 时间的总预算约束。quota 用尽会发生 throttling；这与 CPU 已经 100% 忙、锁等待或 guest 被 hypervisor 抢占是不同原因。

### 内存限制不是“给容器预留一块连续 RAM”

cgroup 内存记账涵盖的类型与版本/配置有关，可能包含匿名页、页缓存和部分内核内存。`memory.max=4GiB` 不表示启动时物理划出 4 GiB，也不保证工作集永驻。压力下可能回收页缓存、触发 reclaim、进入 swap（若允许），最终出现 cgroup OOM。OOM 受层级、事件、进程可杀性和运行时策略影响；不要看到退出码就自动断言是宿主整体 OOM。

### 委派必须保持层级不变量

把子树交给非特权管理者需要控制可写文件、controller 开启位置和进程归属，避免子级逃离祖先限制或破坏同层公平。systemd、容器运行时与编排器通常都管理 cgroup；多个管理者直接写同一层级容易互相覆盖。本课实验因此只读，不尝试“修正”任何值。

## 4. Capability：把传统 root 权限拆成若干位

Linux capability 把许多原本属于 UID 0 的检查拆成能力，例如网络管理、改变部分身份、执行某些系统管理操作。进程凭据中可涉及 permitted、effective、inheritable、bounding 和 ambient 等集合；文件 capability 与 `execve` 规则也会参与新程序的权限计算。

三个关键结论：

1. **删除不需要的 capability 是减小权限面，不是完整沙箱。**普通无 capability 的进程仍可读取其 DAC 权限允许的文件、发起网络请求、消耗被允许的资源并调用大量 syscall。
2. **namespace 内 capability 有作用域。**user namespace 内看似拥有某项 capability，不必等价于 initial user namespace 中对宿主对象拥有同样权限。
3. **UID 0、capability 与对象策略是叠加关系。**DAC、LSM、挂载选项、seccomp 和内核具体检查都可能继续拒绝操作。

`no_new_privs` 可保证后续 `execve` 不通过 set-user-ID/set-group-ID 或文件 capability 获得新的权限，是部署 seccomp 等机制的重要配套，但它不撤销进程当前已经拥有的权限。

## 5. Seccomp 与 LSM：限制“调用面”和“对象访问面”

### Seccomp 过滤系统调用入口

seccomp filter 可依据 syscall 编号、架构和传入参数选择允许、拒绝、通知或终止等动作。它适合缩小一个进程需要的 syscall 面，例如服务不需要加载内核模块或改变某些 namespace 时，不必向它开放相应调用。

但 seccomp 不是路径权限系统。BPF filter 不能安全地把用户指针指向的任意路径字符串当作稳定对象语义；“允许 `openat` 但只允许 `/safe`”不能仅靠朴素 syscall 参数比较可靠实现。文件访问还要靠文件描述符设计、mount namespace、DAC 和 LSM 等机制。

过度宽松的 denylist 会漏掉等价或新 syscall；过度严格的 allowlist 又会因 libc、架构、内核与应用升级而误杀。生产策略应以真实调用需求、版本测试和失败观测为依据，不能复制一份来源不明的规则后宣称安全。

### LSM 在内核对象操作点执行策略

SELinux、AppArmor 等建立在 Linux Security Module hooks 上，可按标签、profile 或其他策略约束文件、进程、网络等对象操作。它们与传统 DAC 权限叠加；“Unix mode 允许”不保证 LSM 允许，“LSM 允许”也不绕过其他内核检查。

安全边界通常是组合：最小文件/设备暴露 + 非特权 UID 映射 + 删除 capability + `no_new_privs` + seccomp allowlist + LSM policy + cgroup 限制 + 内核/运行时更新。仍需根据威胁模型决定容器是否足够，还是应使用 VM、独立主机或更强的机密计算边界。

## 6. Rootless 容器：降低宿主权限，不是魔法开关

rootless 运行通常使用 user namespace，把容器内 UID 0 映射为宿主普通 UID，并让运行时本身也不以宿主 root 常驻。这样可显著降低运行时或容器进程被攻破后的宿主权限。

代价与边界包括：

- subordinate UID/GID 映射与文件所有权必须匹配；共享卷可能出现宿主/容器身份差异；
- 低端口、网络设备、mount、cgroup 委派和设备访问受平台配置限制；实现可能采用用户态网络或额外 helper；
- 宿主内核仍共享，内核漏洞、可达 syscall 与暴露设备仍需防护；
- “容器内显示 root”只描述该 user namespace 的身份，不证明能管理宿主。

评估 rootless 要检查失败模式与功能降级，不能为了让命令跑通而重新加入广泛 capability、特权设备或宿主 socket，从而抵消隔离收益。

## 7. 虚拟机的两阶段地址翻译

硬件辅助虚拟化中，guest 程序产生 guest virtual address（GVA）。guest 页表把它翻译为 guest physical address（GPA）；hypervisor 配置的第二阶段页表再把 GPA 翻译为 host physical address（HPA）：

```text
GVA
  │ guest page tables（guest OS 管理）
  ▼
GPA
  │ second-stage translation：Intel EPT / AMD NPT / Arm Stage-2
  ▼
HPA
```

硬件会缓存组合后的翻译，TLB 命中时不必每次遍历两套页表。未命中、权限变化、内存气球、换页、NUMA 放置与 overcommit 都会影响成本。把 VM 的“16 GiB guest physical memory”理解为永远固定、连续、驻留的 HPA 区域同样不准确。

第二阶段权限还允许 hypervisor 控制 guest 可访问哪些宿主页。IOMMU 对设备 DMA 做类似的地址与权限约束；否则直通设备可能绕过 CPU 页表访问不应触及的内存。

## 8. VM exit：guest 何时必须交回 hypervisor

多数普通用户态指令可直接在 CPU 上运行。某些敏感/特权操作、配置的异常、中断、页表或设备访问会触发 **VM exit**，CPU 保存 guest 状态并进入 hypervisor；处理后再 VM entry 返回 guest。

VM exit 不是“每条 guest 指令都解释执行”，但高频 exit、设备寄存器模拟、TLB 失效与中断注入可能很贵。常见优化思路是：

- 让安全的普通指令直接执行；
- 用硬件两阶段翻译减少内存虚拟化介入；
- 用 paravirtualized 接口把大量细碎设备陷入变成共享队列批处理；
- 对中断进行合并、批处理或轮询，并控制尾延迟；
- 对可信设备采用直通或 mediated device，同时接受迁移、共享与安全复杂度。

“exit 少”也不是完整性能结论；guest 内锁竞争、host 调度、NUMA 远端内存、存储后端与网络队列都可能主导延迟。

## 9. 虚拟 I/O：设备模拟、virtio 与直通

### 完整设备模拟

hypervisor 模拟某种真实设备寄存器与行为，guest 可使用既有驱动，兼容性好；但频繁 MMIO/PIO 与设备状态转换可能导致更多 exit 和复制。它适合启动兼容、旧系统或性能不敏感路径。

### Virtio 半虚拟化

virtio 让 guest 明知自己面对虚拟设备，并使用前端驱动与 host/back-end 通过共享内存队列（virtqueue）交换 descriptor：

```text
guest 应用 → guest 内核 → virtio frontend
                         │ descriptor / available-used ring
                         ▼
                   host/backend → 真实 NIC、文件、块设备或用户态服务
```

共享 descriptor 不等于端到端 zero-copy。guest buffer pin/map、host backend、协议栈、页缓存、加密与真实设备仍可能复制或做 DMA 映射。通知抑制和批处理可提高吞吐，却可能增加单请求等待；busy polling 可降延迟，却持续消耗 CPU。

### 设备直通与虚拟功能

PCI passthrough、SR-IOV virtual function 或 mediated device 可缩短 host 软件数据路径并获得更接近原生的设备语义。代价包括：设备共享与可观测性更复杂，live migration 受限，reset/固件/IOMMU 隔离必须可靠，guest 驱动也进入可信计算基。性能需求不能自动覆盖租户隔离和恢复要求。

## 10. 容器资源视图中的常见陷阱

进程可能同时看到三类数字：

1. namespace 过滤后的 `/proc` 视图；
2. 宿主或虚拟机的硬件拓扑信息；
3. 当前 cgroup 的有效限制与累计统计。

库和监控如果选错来源，就会误判容量。例如：

- `/proc/meminfo` 可能反映更大范围的内存，而 `memory.max` 才给出该 cgroup 上限；具体是否虚拟化取决于运行时与 procfs 挂载；
- `os.cpu_count()` 常返回在线逻辑 CPU 数，而 affinity/cpuset/quota 才约束实际并发预算；
- 容器内 PID 很小，不代表宿主没有其他竞争者；
- 应用读到的 I/O 字节可包含页缓存路径，块设备 cgroup 统计又按设备记账，两者口径不同；
- `cpu.stat`、`memory.events` 等为累计值，需要时间窗口差分，且差分仍不能单独证明因果。

稳健的容量初始化应读取运行时明确提供的并发配置，或综合 affinity、effective cpuset 与 CPU quota，并允许人工覆盖；同时把“线程数”“可运行 CPU 集”和“CPU 时间配额”等不同单位写清。

## 11. GPU：容器边界止于宿主驱动

GPU 容器通常不是在镜像里运行另一套内核驱动。典型路径是：

```text
容器应用 / framework
  → 容器中的用户态 CUDA/ROCm 等库
  → 被暴露的设备节点与宿主内核驱动
  → GPU firmware / engines / memory
```

容器工具负责选择设备、挂载或匹配必要的用户态库与设备节点；**宿主内核驱动仍是共享边界**。镜像中的 toolkit 版本、用户态库、宿主驱动与硬件能力必须满足兼容矩阵。仅有 `nvidia-smi` 输出不证明框架、kernel、collective 或所需精度路径可运行。

CPU、内存 cgroup 也不自动给出完整的 GPU 显存、engine 时间和带宽隔离。可见设备筛选只回答“能打开哪些设备”，不保证性能份额、显存配额、故障隔离或侧信道边界。MIG、time-slicing、vGPU、MPS、设备直通等机制提供的隔离单位各不相同，必须以具体硬件/驱动文档和实测为准。

VM 中 GPU 可采用设备模拟、API remoting、vGPU/mediated device 或整卡直通。整卡直通把驱动更多放到 guest，但仍依赖 IOMMU、firmware 与 host 配置；同时会影响迁移和共享。不要把“容器可见一张卡”与“VM 独占一张卡”写成相同安全/性能承诺。

## 12. 如何选择边界：从威胁与失败半径出发

| 场景问题 | 容器更常见的优势 | VM 更常见的优势 |
| --- | --- | --- |
| 启动密度与镜像分发 | 共享内核，启动快，文件层复用 | guest OS 更重 |
| 运行不同内核/内核版本 | 不适合；受宿主内核约束 | 可运行 guest 内核 |
| 恶意多租户隔离 | 需强硬化、最小 syscall/设备面，常再套 VM | 独立 guest 内核提供更强结构边界，但 hypervisor/设备仍需硬化 |
| 设备性能 | 直接复用宿主驱动路径方便 | 直通可接近原生，但迁移/共享复杂 |
| 故障半径 | 内核级故障可能影响宿主上所有容器 | guest 内核故障通常局限于 VM；host/hypervisor 故障仍共享 |
| 可观测与运维 | 宿主工具统一，namespace/cgroup 口径需谨慎 | guest/host 两套观测需关联 |

现实系统常组合二者：每个租户或信任域一个 VM，VM 内再用容器交付进程。边界越多，性能归因、时钟关联、网络/存储路径和配置责任也越复杂；必须记录哪一层拥有 CPU quota、OOM、设备、时间与重启决策。

## 13. 只读观察：验证当前进程的真实视图

Linux 上可读取：

```bash
# 当前进程的 namespace 链接；inode 相同通常表示两个进程共享该 namespace。
ls -l /proc/self/ns

# 当前进程的 UID/GID、capability 十六进制集合、允许 CPU/内存节点。
grep -E '^(Uid|Gid|Cap(Inh|Prm|Eff|Bnd|Amb)|NoNewPrivs|Seccomp|Cpus_allowed_list|Mems_allowed_list):' /proc/self/status

# 当前进程属于哪个 cgroup；cgroup v2 常见形式是 0::/某路径。
cat /proc/self/cgroup

# 仅在确认是 cgroup v2 后，从当前路径读取存在的控制文件。
cat /sys/fs/cgroup/cgroup.controllers
```

不要把示例中的 cgroup 根路径硬套到所有系统：容器内挂载位置、namespace 与委派可能改变可见路径；cgroup v1 的文件结构也不同。capability 十六进制位需要按本机内核头文件或可靠工具解码，不能凭位数猜能力名。macOS 与 Windows 没有 Linux namespace/cgroup v2 这套 ABI，应明确记为“不适用”，再使用各自的 sandbox、job object、hypervisor/container 文档解释。

配套的安全探针见 [[计算机知识/80-实践/06-计算机系统/07-资源视图与时间预算/README|资源视图与时间预算]]。它只读白名单文件，不创建容器、不写 cgroup，也不改变系统时间。

## 14. 练习与成功标准

1. 为“容器内进程看到 64 CPU，但 `cpu.max` 只允许约 2 CPU 时间”画出 online CPU、affinity、cpuset 与 quota 的交集/上限关系，并说明线程池开到 64 的风险。
2. 为同一服务分别设计 namespace、cgroup、capability/seccomp/LSM 与 VM 层的控制；每项写出保护对象和它无法保护的对象。
3. 画出一次 virtio-blk 写请求：guest 文件系统、guest block 层、virtqueue、host backend、host 文件/块设备、真实设备完成，再标出“guest syscall 返回”和“持久化”的不同边界。
4. 解释 GPU 容器中哪些组件来自镜像、哪些来自宿主，并写出至少三个需现场验证的兼容/隔离假设。
5. 成功标准：能用证据回答当前进程共享哪套内核、位于哪个 cgroup、有哪些有效 CPU/配额视图；没有执行任何写 cgroup、创建特权容器或设备直通操作。

## 15. 易错点回顾

- namespace 隐藏名字，不等于资源限额或完整安全边界；
- cgroup quota、weight、cpuset 与 affinity 单位不同，不能互相替代；
- 容器内 root、rootless 与宿主 root 是不同身份/作用域问题；
- seccomp 过滤 syscall，LSM/DAC 约束对象访问，二者需要叠加；
- VM 使用独立 guest 内核，但仍信任 hypervisor、虚拟设备与共享后端；
- virtio 减少设备模拟成本，不保证 zero-copy 或零 VM exit；
- GPU 容器共享宿主驱动，CPU/内存 cgroup 不自动等于 GPU 配额；
- 容量与性能结论必须读取**当前层的有效限制**，不能只看宿主拓扑或容器表象。

---

**上一站**：[[计算机知识/30-计算机系统/18-CPU拓扑缓存一致性NUMA与设备亲和性|CPU 拓扑、缓存一致性、NUMA 与设备亲和性]] · **下一站**：[[计算机知识/30-计算机系统/20-时间时钟计时器Deadline与跨主机关联|时间、时钟、计时器、Deadline 与跨主机关联]] · **实践**：[[计算机知识/80-实践/06-计算机系统/07-资源视图与时间预算/README|资源视图与时间预算]] · **返回**：[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/30-计算机系统/10-组成原理系统课程/06-虚拟地址TLB与存储系统|虚拟地址、TLB 与存储系统：翻译和取数据是两件事]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
