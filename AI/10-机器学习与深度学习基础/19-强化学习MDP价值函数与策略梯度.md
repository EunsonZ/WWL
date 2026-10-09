---
type: deep-lesson
status: reviewed
evidence_status: partial
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


当s本身不可观察，不能把最近读数直接代入这里的状态价值。[[AI/13-搜索推理与规划/20-部分可观测决策/01-有限模型belief与决策状态#为什么belief足以递推|belief充分性]]给出隐藏状态、固定转移/观测核与可见时域下的条件；[[AI/13-搜索推理与规划/20-部分可观测决策/02-beliefBellman与独立策略树#从条件期望到Bellman递推|belief Bellman]]仍比较当前收益加未来最优值，但后继是按新观测得到的belief，奖励为r=−L。它是已知模型的有限决策计算，不把本文Q-learning样本更新改称已完成POMDP学习。

### 同一个有限环境，逐回合观察 MC、TD 与 Q-learning

用两非终止状态 $s_0,s_1$ 和终止状态 end，固定 $\gamma=.5$、步长 $\alpha=.5$。每条边是确定性转移，标出动作和立即奖励：

```mermaid
flowchart LR
    S0["s₀"] -->|"go, r=0"| S1["s₁"]
    S0 -->|"quit, r=0.5"| END["end: terminated"]
    S1 -->|"finish, r=2"| END
    S1 -->|"quit, r=0"| END
```

先手算最优目标：$Q^*(s_1,finish)=2$、$Q^*(s_1,quit)=0$；$Q^*(s_0,go)=0+.5\times2=1$，而 $Q^*(s_0,quit)=.5$。这里可以枚举全部三个完整行动序列验证最优回报为 1；已知模型的解是对照，下面仍模拟只用样本更新的学习者。

所有估计从 0 开始。同一批六个完整回合依次是 `(go,finish)` 三次、`(quit)` 一次、`(go,quit)` 两次。MC 回合结束后用完整回报更新 $V\leftarrow V+.5(G-V)$；TD(0) 与 Q-learning 沿时间正序逐步在线更新。每回合无状态重访，first-visit 与 every-visit MC 在这里相同。固定步长和脚本行为让轨迹易跟算，不满足本页就能宣称收敛或最优探索的条件。[^RLworked]

| 回合与行为 | $G(s_0)$ | MC $V(s_0)$ | TD $V(s_0)$ | 两种V法的 $V(s_1)$ | Q $(s_0,go)$ | Q $(s_0,quit)$ | Q $(s_1,finish)$ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 go,finish | 1 | .5 | 0 | 1 | 0 | 0 | 1 |
| 2 go,finish | 1 | .75 | .25 | 1.5 | .25 | 0 | 1.5 |
| 3 go,finish | 1 | .875 | .5 | 1.75 | .5 | 0 | 1.75 |
| 4 quit | .5 | .6875 | .5 | 1.75 | .5 | .25 | 1.75 |
| 5 go,quit | 0 | .34375 | .6875 | .875 | .6875 | .25 | 1.75 |
| 6 go,quit | 0 | .171875 | .5625 | .4375 | .78125 | .25 | 1.75 |

$Q(s_1,quit)$ 始终 0。第一回合 TD 更新 $s_0$ 时下一状态值仍是 0，所以还学不到未来的 2；MC 等到终局就拿到回报 1。第五回合即使实际最终奖励为 0，TD 先读取旧 $V(s_1)=1.75$，$s_0$ 的目标 .875，把 .5 更新为 .6875，随后才把 $V(s_1)$ 降至 .875。不能把“回合结束后的值”倒填到先前在线更新。第六回合 TD 目标为 $.5\times.875=.4375$，而 Q-learning 的目标继续取 $.5\max(1.75,0)=.875$，于是两个 $s_0$ 估计分开：Q-learning 保留未被后来 quit 样本改写的 finish 动作估值。MC/TD 此处估计样本行为的状态价值，Q-learning 尝试学 greedy 控制价值；数值大小本身不是算法优劣排名。

**真正终止与外部截断改变哪一步？** 定义 bootstrap 目标 $r+\gamma(1-\text{terminated})\widehat V(s')$。假设 `go` 后采样器因外部时间上限停下来，最后观察仍是 $s_1$，且 $\widehat V(s_1)=2$：`terminated=False,truncated=True` 时目标是 $0+.5\times2=1$；若这个转移真正进入终止状态，即使表里误存“下一值 2”，目标仍应是 0。两标志同时为真也按真正终止屏蔽。[^Timeworked]

这一区别只适用于时间上限是环境外的采样限制。若任务本身有有限时域，剩余时间须纳入 Markov 状态，任务时域结束可是真正终止。MC 无完整未来时不能把截断前缀直接当全回报；实验 `mdp_learning` 拒绝没有终止的回合，而 `bootstrap_target` 单独核对两标志，防止“为了跑通”把缺失未来设为零。

到 [[AI/90-资源/实验/ai_worked_examples_20260917/README|五个可跟算实验]] 的 RL 部分运行 `mdp_learning` 与 `bootstrap_target`，查看所有 Q 项和逐回合数值。迁移题：若改为回合末反向更新 TD，第一个回合 $V(s_0)$ 还是 0 吗？不是：先更新 $V(s_1)=1$ 后，$s_0$ 会变为 .25；这已经改变更新时序，不能拿它去匹配上表。

[^RLworked]: David Silver 作者课程：[Lecture 4: Model-Free Prediction，第 10–12 张](https://davidstarsilver.wordpress.com/wp-content/uploads/2025/04/lecture-4-model-free-prediction-.pdf)，给固定步长 MC 与 TD(0) 更新；[Lecture 5: Model-Free Control，Q-learning 部分](https://davidstarsilver.wordpress.com/wp-content/uploads/2025/04/lecture-5-model-free-control-.pdf)，给 off-policy 最大值目标。2026-09-17 核对；环境与六回合轨迹为教学构造，Sutton/Barto 教材入口沿用文末。
[^Timeworked]: [Gymnasium 官方：Handling Time Limits](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/)：环境外截断保留 bootstrap、真正终止屏蔽及有限时域状态条件；2026-09-17 核对。

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
