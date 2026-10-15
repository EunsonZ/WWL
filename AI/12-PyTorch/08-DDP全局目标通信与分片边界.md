---
type: deep-lesson
status: reviewed
updated: '2026-09-06'
review_round: 深化研究-02
tags:
- ai/deep-study
aliases: []
---

# DDP 全局目标、通信与分片边界：多卡如何仍然优化同一个损失

**先修与定位：** [[AI/12-PyTorch/05-变长批处理Packing与有效Token归一化|微批归一化]]、原 [[AI/12-PyTorch/04-混合精度分布式编译与性能诊断|性能入口]]。

## 先把数学目标写成全局分子和分母

设 $R$ 个 rank，各有若干微批。全部有效 token 的损失和为 $S=\sum_rS_r$，计数为 $N=\sum_rn_r$，目标是 $L=S/N$。常规 DDP 对各 rank 梯度求平均，因此每个 rank 反传 $R S_r/N$ 才得到

$$
\frac1R\sum_r\nabla_\theta\frac{R S_r}{N}
=\nabla_\theta\frac{\sum_rS_r}{N}.
$$

这里假设 $N$ 是不依赖参数的数据计数，并且未使用改变通信缩放的 hook。若局部先除以 $n_r$，同步后就是每 rank 等权，而非每 token 等权。[^S41]

例：两 rank 分别有 8、2 个 token，损失和分别为 8、6。全局 loss 是 1.4，局部均值平均是 2。记录日志时也应 all-reduce 分子与分母，而不是把局部 loss 直接平均后当全局值。

## no_sync 为什么必须覆盖 forward

DDP 在前向和反向过程中安排梯度同步。累积非末微批时，用 `no_sync()` 包住相应 forward 和 backward，最后一批才同步。仅围住 backward 不符合该接口的完整使用约定。[^S41]

所有 rank 需要参与一致的集体操作顺序。某 rank 因“没有有效标签”单独跳过训练，其他 rank 仍进入通信，可能挂起。整个全局窗口无有效 token 时共同跳过；只有局部无贡献时，则按具体图与参数使用策略保持零贡献路径。

损失全局计数归约和梯度归约也是不同操作。不能为了日志提前把有梯度的局部 loss 随意 all-reduce，误以为这就自动实现了跨 rank autograd。

## 数据并行不等于数据自动分好

常见 map-style 数据要通过分布式 sampler 分片，并在每个 epoch 更新其随机顺序。为了各 rank 步数一致而补齐的重复样本，会改变评估计数；验证时需去重或明确不重复的划分策略。iterable dataset 还要同时按 rank 和 worker 分片。[^S37]

DDP 同步梯度，不自动让普通 BatchNorm 的局部批统计变成全局统计。微批很小时，数据并行与一次大 batch 的计算行为可能不同。比较等价性应先去掉这些干扰，用确定性小模型验证，再增加真实训练特性。

## 通信为什么能与计算重叠

反向传播从后层逐步产生梯度。DDP 将梯度分桶，在桶就绪时启动通信，使较早的通信与尚未完成的反向计算重叠。桶太小有启动开销，桶太大可能推迟重叠，真实收益依赖模型与互连。[^S39]

数据并行、张量并行、流水并行、专家并行分别沿样本、算子维度、层与专家分割工作。它们不是四种同义的“把模型分成几份”。MoE all-to-all 与普通梯度 all-reduce 的数据内容和通信模式也不同，接 [[AI/20-LLM/20-架构/13-MoE路由梯度负载均衡与通信成本|专家路由]]。

## FSDP 与 ZeRO 省下什么，又新增什么

普通数据并行通常在各卡保留完整模型相关状态；分片方案按策略分散参数、梯度或优化器状态，计算时再收集需要的部分。节省驻留内存的代价可能是更复杂的通信、临时峰值和恢复流程。

不能只用“参数字节数除卡数”作为峰值显存。还有激活、临时 gather、通信缓冲区和算子 workspace。优化器状态分片不意味着激活也被自动分片；activation checkpointing 则是另一条计算换内存路径。

## 自检与验证边界

**问题：** 两卡每卡两条序列，所以四条序列一定各有相同损失权重吗？只有目标按序列等权时如此；按 token 等权要看长度。即使序列数相同，局部有效 token 数仍可能不同。

**本轮证据：** [[AI/80-实践/08-深层机制数值实验/00-数值实验导航与验收|CPU 实验]] 用独立梯度副本模拟 DDP 平均，验证缩放恒等式，另设错误局部平均作为反例。这是数学和本地实现验证，不是真实多进程通信或 GPU 扩展性能测试。运行边界见 [[AI/90-资源/08-本轮深化修订与验收报告|验收报告]]。

## 来源与证据边界

本页的数值例与推导用于解释机制，不代表大型模型或真实业务上的实测效果。方法与接口依据如下，来源核验日期为 2026-09-06。

[^S41]: [PyTorch 2.10：DistributedDataParallel](https://docs.pytorch.org/docs/2.10/generated/torch.nn.parallel.DistributedDataParallel.html)。固定版本；no_sync、求均值与未用参数。
[^S39]: [PyTorch 2.10：DDP design note](https://docs.pytorch.org/docs/2.10/notes/ddp.html)。固定版本；桶化和通信重叠。
[^S37]: [PyTorch 2.10：DataLoader与Dataset](https://docs.pytorch.org/docs/2.10/data.html)。固定版本；数据分片、组批与进程。

**返回与迁移：** [[AI/12-PyTorch/00-PyTorch-MOC|本主题课程地图]]；[[AI/00-开始/05-问题驱动知识图谱与难点导航|按问题跨主题继续]]。
