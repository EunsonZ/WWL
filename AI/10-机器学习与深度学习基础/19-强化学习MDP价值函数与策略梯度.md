---
type: deep-lesson
status: reviewed
updated: '2026-09-06'
review_round: 深化研究-02
tags:
- ai/deep-study
aliases: []
---

# 强化学习：从 MDP、价值函数到语言模型策略梯度

**先修与定位：** [[AI/11-数学与统计桥梁/03-概率似然贝叶斯与信息论|期望与条件概率]]、[[AI/11-数学与统计桥梁/02-矩阵微积分VJP与反向传播|梯度]]。

## 和监督学习相比，多出来的困难是什么

监督学习通常拿到输入与标签；强化学习通过行动改变接下来会遇到的数据，再依据回报更新策略。奖励延迟、探索不足和策略改变导致的数据分布变化，是其核心难点。不能只把“分数当标签”就说理解了 RL。

一个有限 MDP 用状态 $s$、动作 $a$、转移分布、奖励与折扣因子 $\gamma$ 描述。Markov 条件要求状态包含预测下一步所需的信息；真实对话系统只有部分观察时，完整历史或状态估计可能比单条消息更合适。

## 回报、价值和优势各回答什么

定义从 $t$ 开始的回报 $G_t=\sum_{k\ge0}\gamma^kr_{t+k}$。$V^\pi(s)$ 是按策略继续行动时的期望回报；$Q^\pi(s,a)$ 是先采取指定动作再继续的期望回报；优势 $A^\pi(s,a)=Q^\pi(s,a)-V^\pi(s)$ 衡量该动作比本状态通常行为好多少。

Bellman 关系来自把第一步奖励与后续回报拆开：

$$
V^\pi(s)=\mathbb E_{a\sim\pi,s'}[r(s,a,s')+\gamma V^\pi(s')].
$$

如果现在奖励为 1，下一状态价值为 4，$\gamma=0.9$，一步目标为 4.6。用估计的价值替代完整未来称为 bootstrap；它减少等待和某些方差，但引入对价值估计误差的依赖。

## 为什么能对离散动作的概率求梯度

动作本身不可微并不妨碍优化动作分布。对一个简化单步任务，

$$
\nabla_\theta\mathbb E_{a\sim\pi_\theta}[r(a)]
=\sum_a r(a)\nabla_\theta\pi_\theta(a)
=\mathbb E[r(a)\nabla_\theta\log\pi_\theta(a)].
$$

这里假设奖励不直接依赖参数且可交换求和与求导。它通过增加高回报动作的概率工作，而不是对整数 token ID 求导。序列情形把整条轨迹的 log-prob 分解为各步之和，再用适当的回报或优势为每步加权。[^S29]

与动作无关的基线可减方差，因为 $\mathbb E[b(s)\nabla\log\pi(a\mid s)]=b(s)\nabla\sum_a\pi(a\mid s)=0$。基线若依赖当前动作，一般不能直接使用这个无偏结论。组内均值包含当前样本也带来有限样本细节，见 [[AI/20-LLM/30-训练/13-GRPO重要性比率归一化与奖励偏差|GRPO 深入]]。

## on-policy、off-policy 与重要性采样

旧策略 $q$ 采样的数据，要估计新策略 $p$ 的期望，可在支持集覆盖时用 $p(a)/q(a)$ 加权。若 $q(a)=0,p(a)>0$，旧数据不提供该动作的信息，不能凭空校正。长序列的联合概率比是多个 token 比率的乘积，可能有很大方差。

## 动态规划、Monte Carlo 与 TD 的差别在“目标从哪里来”

若已知完整转移与奖励模型，动态规划可对所有状态做 Bellman backup。策略评估的同步更新是

$$
V_{k+1}(s)=\sum_a\pi(a\mid s)\sum_{s',r}P(s',r\mid s,a)[r+\gamma V_k(s')].
$$

若不知道模型但能采样完整 episode，Monte Carlo 用真实回报 $G_t$ 作目标；TD(0) 在一步后用 $r_t+\gamma V(s_{t+1})$ 作目标。前者不 bootstrap、常方差高且要等终局；后者 bootstrap、可在线更新但会继承当前价值误差。

| 方法 | 需要模型 | bootstrap | 需等终局 | 一步目标 |
|---|---:|---:|---:|---|
| 动态规划 | 是 | 是 | 否 | 对所有下一状态求期望 |
| Monte Carlo | 否 | 否 | 是 | 完整采样回报 $G_t$ |
| TD(0) | 否 | 是 | 否 | $r+\gamma V(s')$ |

两步轨迹奖励为 $0,2$，$\gamma=0.5$。从第一步看的 Monte Carlo 回报为 $0+0.5\times2=1$。若当前下一状态估值为 3，TD 一步目标为 $0+0.5\times3=1.5$。两个目标不同不表示有一个算错；它们使用了不同信息。

## 从 Bellman 最优方程到 Q-learning

最优动作价值满足

$$
Q^*(s,a)=\mathbb E[r+\gamma\max_{a'}Q^*(s',a')\mid s,a].
$$

表格 Q-learning 用观测转移更新

$$
Q(s,a)\leftarrow Q(s,a)+\alpha\left[r+\gamma\max_{a'}Q(s',a')-Q(s,a)\right].
$$

若 $Q(s,a)=1,r=2,\gamma=0.9,\max Q(s',\cdot)=4,\alpha=0.1$，TD error 为 $2+3.6-1=4.6$，新值为 1.46。若 $s'$ 是终止状态，后续项应为 0；把 episode 因时间上限截断和真正终止混成同一个 done 标志会造成错误目标。

Q-learning 的目标使用 greedy 最大值，行为策略可以探索，因此是 off-policy。SARSA 的目标使用实际下一动作 $Q(s',a')$，在探索策略下学习的是该策略的价值。函数逼近、bootstrap 与 off-policy 三者组合可能不稳定；经验回放和目标网络是工程缓解，不是普遍收敛证明。

## 探索是信息问题，不只是加随机噪声

$\epsilon$-greedy 以概率 $\epsilon$ 随机行动，简单但不利用不确定性。若危险动作一次就可能造成不可逆损失，盲目探索不可接受；需要安全约束、离线数据、模拟器或人工边界。离线 RL 只能看到行为策略覆盖过的动作：数据外动作的价值可能被函数逼近高估，不能仅靠 Bellman 方程制造反事实证据。

```mermaid
flowchart LR
    A[行为策略采样] --> B[状态-动作覆盖]
    B --> C[价值/策略估计]
    C --> D[新策略]
    D --> E[改变未来数据]
    E --> A
```

这条反馈环把 RL 和普通固定数据监督学习区分开。用历史日志做策略评估时，需明确 propensity/支持集，机器学习中的反事实评估边界见 [[AI/10-机器学习与深度学习基础/21-因果机器学习选择偏差与反事实评估|第 21 课]]。

## Actor-Critic 为什么同时学两样东西

actor 参数化策略，critic 估计价值或优势。一个常见一步优势估计为

$$
\widehat A_t=r_t+\gamma V_\phi(s_{t+1})-V_\phi(s_t).
$$

actor 用 $\widehat A_t\nabla\log\pi_\theta(a_t\mid s_t)$ 更新，critic 用 TD 误差学习。critic 有偏或学得过慢会误导 actor；共享表示还可能让两个目标相互干扰。GAE 把多步 TD residual 加权折中偏差和方差，但 $\lambda$ 不是“越大越准”的通用旋钮。

**可复算实验：** `value_iteration` 在一个两状态两动作的已知 MDP 上迭代 Bellman 最优算子；`td_targets` 复算 SARSA 与 Q-learning 的一步目标。正文另用公式说明终止状态的 bootstrap 必须置零。实验只验证表格公式，不外推为深度 RL 的稳定性证据。

PPO 用裁剪 surrogate 限制旧样本对更新的激励，但不是严格强制所有状态上 KL 小于某个阈值。训练时用的 token 比率、轨迹比率和序列平均比率是不同估计与优化设计，不能仅因都写成 $\rho$ 就互换。[^S36]

## LLM 为什么既像序列决策，又常像 contextual bandit

把状态定义为提示加已生成前缀，动作是下一 token，转移是追加该 token，即可建立序列决策表示。若只在最终答案打分，也可把整个回答当一个巨大动作，形成 contextual bandit 视角。两个视角有助于理解不同目标，但不消除信用分配与搜索难度。

SFT 对示范答案做最大似然；奖励优化对模型自己的候选做选择性增强。训练奖励是代理目标：通过字符串检查不等于正确完成任务，通过有限测试不等于程序全域正确。验证器应有独立留出集与防泄漏边界。

## 自检与参考解

**问题：** 为什么模型拿到较高奖励，却可能更长、更重复、事实性更差？奖励可能对长度、格式或特定捷径存在偏好；策略在优化实际奖励，而不是研究者未写入的完整意图。

**问题：** 去掉价值网络是否就没有 baseline？不是。GRPO 的组内比较仍构造了相对基线，只是不单独训练同样形式的价值模型。

接 [[AI/20-LLM/30-训练/12-从KL约束到DPO的逐步推导|离线偏好优化]]、[[AI/20-LLM/30-训练/13-GRPO重要性比率归一化与奖励偏差|组相对策略优化]]、[[AI/20-LLM/40-推理/10-测试时计算验证器误差与预算公平性|验证器与测试时计算]]，避免把训练时 RL 与推理时多采样混成一种操作。

## 来源与证据边界

相关接口与延伸方法可继续核对：[^S16]。

本页的数值例与推导用于解释机制，不代表大型模型或真实业务上的实测效果。旧论文来源与本轮新增作者教材定位均于 2026-09-16 复核。

[^S29]: [Sutton等：Policy Gradient Methods for Reinforcement Learning](https://papers.nips.cc/paper/1713-policy-gradient-methods-for-reinforcement-learning-with-function-approximation)。原始研究；策略梯度。
[^S36]: [Schulman等：Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347)。2017；PPO裁剪目标。
[^S16]: [Shao等：DeepSeekMath](https://arxiv.org/html/2402.03300v3)。2024；GRPO原始来源。

完整入门主线见 [Sutton 与 Barto：《Reinforcement Learning: An Introduction》第 2 版作者稿](https://www.incompleteideas.net/book/bookdraft2018mar21.pdf)：第 3–6 章对应 MDP、动态规划、Monte Carlo 与 TD，第 13 章对应策略梯度。

**返回与迁移：** [[AI/10-机器学习与深度学习基础/00-机器学习与深度学习基础-MOC|本主题课程地图]]；[[AI/00-开始/05-问题驱动知识图谱与难点导航|按问题跨主题继续]]。
