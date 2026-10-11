---
type: lesson
domain: artificial-intelligence
aliases:
  - 可实现与不可实现PAC
  - 近似ERM超额风险
sources:
  - "https://www.cs.huji.ac.il/~shais/UnderstandingMachineLearning/understanding-machine-learning-theory-algorithms.pdf"
  - "https://cs.uwaterloo.ca/~shai/Chapters_4_CS886.pdf"
prerequisites:
  - "[[AI/10-机器学习与深度学习基础/12-统计学习泛化与实验设计]]"
---

# PAC、一致收敛与近似ERM：训练最优离未来最优有多远

[[AI/10-机器学习与深度学习基础/12-统计学习泛化与实验设计#泛化界究竟在界什么|有限类界]]保护的是全部候选的一致偏差。现在追问：它怎样变成“一个学习算法学会了”的保证？需要先写清学什么、什么在随机变化，以及保证是否依赖未知分布。

## 对哪个样本、哪个假设类同时成立

设可测样本空间 $\mathcal Z=\mathcal X\times\mathcal Y$，未知但固定的总体分布为 $P$。训练集为有序序列 $S=(Z_1,\ldots,Z_n)\sim P^n$；各 $Z_i$ 独立且同分布。非空假设类 $\mathcal H$ 在看到此训练集前固定，损失 $\ell(h,z)\in[0,C]$，$C<\infty$。二分类时 $\mathcal Y=\{0,1\}$、$C=1$、$\ell(h,(x,y))=\mathbf1[h(x)\ne y]$。定义

$$R_P(h)=\mathbb E_{Z\sim P}\ell(h,Z),\qquad
\widehat R_S(h)=\frac1n\sum_i\ell(h,Z_i).$$

$R_P(h)$已对未来样本 $Z$ 取了期望；定理外层的概率通常在训练集 $S$ 上。若算法使用随机种子 $U$，写 $A(S,U)$；保证须明确是否还对 $U$ 取概率。以下先用确定性、可测的学习规则；概率事件中的上确界假设可测，常见可分离类可用可数稠密子类处理。不能在任意病态不可测类上忽略这个技术条件。

一个**一致收敛**保证是：对任意 $\epsilon>0,\delta\in(0,1)$，有不依赖 $P$ 的 $N(\epsilon,\delta)$，使

$$\forall P\ \forall n\ge N(\epsilon,\delta),\quad
\Pr_{S\sim P^n}\!\left[\sup_{h\in\mathcal H}|R_P(h)-\widehat R_S(h)|\le\epsilon\right]\ge1-\delta.$$

这里“同时”发生在同一个训练集上、对全部 $h$ 成立。它没有说每一个可能训练集都好，也没有说对任意部署分布同时好。$\delta$是训练集落在失败事件的概率，$\epsilon$是损失期望与样本均值之间的容差，有风险单位；两者不能混用。

从 [[数学/30-概率与统计/05-统计估计置信度与模型评测#准确率的标准误与近似区间|准确率区间]] 进入时，先问预测器是否已冻结；对固定预测器的一条区间没有自动保护用同一批数据选择的所有预测器。一致界恰好补上这一层。它允许在**预先固定的类内**数据选择 $h$。若先看样本再创造新特征/新类，需把整个选择机制纳入原来可保证的范围，或另用独立数据、稳定性等合适工具。

这种边界也适用于描述模型的语言。[[AI/10-机器学习与深度学习基础/30-统计学习理论/05-前缀描述与可数类泛化#训练后把赢家改名为一个 bit，哪一步失效|事后给赢家一个 bit 的反例]]保持大类固定、当次前缀码合法，却因解码器与置信预算依赖同一训练集而使错误套用的界失效；“数据后选模型”与“数据后改变保护它的预算”是不同层次。

## PAC的量词：可实现与不可实现

二分类**可实现**条件是存在 $h_*\in\mathcal H$ 满足 $R_P(h_*)=0$，即标签在该分布几乎处处可由类中函数预测。分布可以未知，函数类是归纳偏置。“没有测量噪声”本身不保证可实现：目标函数也可能不在类里。

可实现PAC可学习要求：存在一个算法 $A$ 和样本需求函数 $N$，满足

$$\forall\epsilon,\delta\in(0,1)\ \forall P\text{（在}\mathcal H\text{中可实现）}\quad
\forall n\ge N(\epsilon,\delta),\quad
\Pr_{S\sim P^n}[R_P(A(S))\le\epsilon]\ge1-\delta.$$

若要求 $A(S)\in\mathcal H$ 称 proper；允许输出其他可测预测器称 improper。PAC定义是样本保证，不自动要求运行时间为多项式；学习的计算复杂度是另一项条件。

**Agnostic PAC**去掉可实现假设，比较类内最优风险：

$$\exists A,N\ \forall\epsilon,\delta\in(0,1)\ \forall P\ \forall n\ge N(\epsilon,\delta),\quad
\Pr_{S\sim P^n}[R_P(A(S))\le\inf_{h\in\mathcal H}R_P(h)+\epsilon]\ge1-\delta.$$

它允许标签噪声，也允许类太简单；保证学得接近**该类最优**，并不把其风险强行降到零。一般有界损失也可用这个定义，但VC二分类基本定理不能原样搬到任意实值损失。定义与学习模型对照见[作者教材第3、4章](https://www.cs.huji.ac.il/~shais/UnderstandingMachineLearning/understanding-machine-learning-theory-algorithms.pdf#page=44)；作者课程中的[同题草稿第3章](https://cs.uwaterloo.ca/~shai/Chapters_4_CS886.pdf#page=29)也保留可实现/agnostic定义，草稿页码与正式书页码不同。下面推导写出本课使用的常数。

## 从好事件逐项推出近似ERM界

ERM选经验风险最小者；若最小值未达到或求解只能近似，设返回 $\widehat h\in\mathcal H$ 满足

$$\widehat R_S(\widehat h)\le\inf_{h\in\mathcal H}\widehat R_S(h)+\eta,\qquad\eta\ge0.$$

$\eta$是经验风险求解容差。取上节的一致好事件，对任意 $h\in\mathcal H$，

$$\begin{aligned}
R_P(\widehat h)
&\le\widehat R_S(\widehat h)+\epsilon &&\text{输出的估计误差}\\
&\le\widehat R_S(h)+\eta+\epsilon &&\text{近似经验最优}\\
&\le R_P(h)+\eta+2\epsilon &&\text{比较者的估计误差}.
\end{aligned}$$

对 $h$ 取下确界，得到

$$R_P(\widehat h)-\inf_{h\in\mathcal H}R_P(h)\le2\epsilon+\eta.$$

不用假装存在精确类内最优点：可以取风险离下确界不足 $a>0$ 的比较者，最后令 $a\downarrow0$。当 $\epsilon=.03,\eta=.01$，上界为 $.07$；如果一致好事件以概率 $.95$ 成立，这个超额风险界也至少以同一概率成立。$.01$不会自动增加或减少失败概率；若优化器也只以概率 $1-\delta_{\rm opt}$ 达到容差，需将两个失败事件合并，成功概率至少 $1-\delta-\delta_{\rm opt}$，不需要假设两事件独立。

这给出“一致收敛足以agnostic学习”的一般证明。对目标超额风险 $a$，精确ERM可取一致容差 $a/2$。[[AI/10-机器学习与深度学习基础/30-统计学习理论/02-增长函数VC与不可学习|下一课]]将提供无限二分类类的一致界。

## 三种误差与优化证书的合法换算

设 $R_P^*=\inf_{\text{所有允许的可测预测器 }g}R_P(g)$ 为所选损失下的Bayes风险，不要求存在最小者。在同一好事件上，

$$R_P(\widehat h)-R_P^*\le
\underbrace{\inf_{h\in\mathcal H}R_P(h)-R_P^*}_{\text{类外逼近误差}}
+\underbrace{2\epsilon}_{\text{一致估计误差}}
+\underbrace{\eta}_{\text{经验优化误差}}.$$

增大类可能减小逼近误差、同时增大一致估计误差。若所有函数都允许，训练误差可为零，后面VC课的打散构造会说明为什么没有分布无关的有限样本保证。

[[AI/10-机器学习与深度学习基础/15-核方法树集成与归纳偏置#六个二维点：从约束推到对偶，再回到预测|六点SVM]]与[[数学/40-微积分与优化/08-凸优化对偶与最优性证书#一张证书表怎样落到 SVM 与约束 QP|原始/对偶证书]]给出的gap针对其固定训练目标。把证书带进上面的 $\eta$ 前，要核对目标是否就是 $\widehat R$、是否同一reduction、是否同一损失。硬间隔SVM的 $\|w\|^2/2$ 最优性证书不是0-1经验风险容差。

例如优化目标是 $F_S(w)=\widehat R_S(w)+\lambda\Omega(w)$，$\Omega\ge0$，$\lambda\ge0$，可行集合为预先固定的 $\mathcal W$。若证书证明 $F_S(\widehat w)\le\inf_wF_S(w)+\eta_F$，则对任意比较者 $u\in\mathcal W$，

$$\widehat R_S(\widehat w)\le\widehat R_S(u)+\lambda\Omega(u)-\lambda\Omega(\widehat w)+\eta_F.$$

若有该集合上纯损失一致容差 $\epsilon$，才进一步得到

$$R_P(\widehat w)\le R_P(u)+2\epsilon+\lambda\Omega(u)+\eta_F,$$

此处只把非负的输出正则项舍去。$\eta_F$没有独自变成“纯经验风险ERM误差”：还要保留比较者正则代价。[[AI/10-机器学习与深度学习基础/30-统计学习理论/03-正则化稳定性与范数复杂度#正则强度为什么有两面|稳定性课]]另用算法稳定性证明平均风险界，避免要求整个大类一致收敛。

## 有限类为何在可实现时能更快

有限类 $|\mathcal H|=M\ge1$，0-1损失，iid，可实现，取一致ERM使训练错误为零。任意风险 $R_P(h)>a$ 的固定假设在全部 $n$ 个样本上恰好无错误的概率为

$$[1-R_P(h)]^n\le e^{-na}.$$

联合界给 $\Pr[R_P(\widehat h)>a]\le M e^{-na}$，所以 $n\ge\log(M/\delta)/a$ 充分。概率在 $S$ 上；结论无需对训练选出的 $h$重新假装它是固定假设，因为已经联合保护所有坏候选。

Agnostic情形用第12课 $C=1$ 的双侧界：一致容差 $a/2$ 要求 $n\ge2\log(2M/\delta)/a^2$，才给超额风险 $a$。$1/a$与$1/a^2$来自不同事件与前提，不能把快率直接移植到有噪声问题。近似ERM在可实现情形若仍允许非零训练错误，上面的“全部样本无错误”证明就要重写。

候选变成可数无限时，不能把 $M=\infty$ 代进有限等权公式。[[AI/10-机器学习与深度学习基础/30-统计学习理论/05-前缀描述与可数类泛化#一次好抽样同时保护所有模型|前缀描述与非等权联合界]]保留 iid、$[0,1]$ 损失与事前固定协议，用 $\delta_h=\delta2^{-\ell(h)}$ 保护同一个样本上的全部候选；代价是偏差半径随模型码长变化，不再是本页共用的 $\epsilon$。

## 改变抽样单位，证明在哪一步断裂

抽4位独立用户，每人复制16条完全相同记录，一共64行。经验平均与4人平均相同，随机变化仍只来自4个独立对象；Hoeffding证明中的64个独立因子不存在。按实体划分防止训练/测试泄漏很必要，但不能单凭划分方式使同一集合内64行变独立。[[AI/10-机器学习与深度学习基础/18-嵌套验证配对实验与指标陷阱#逐题配对与完整失败分母|配对与完整分母]]帮助区分训练种子、任务、用户；回到本页首节，在证明前声明 $Z_i$ 究竟是什么。

分布偏移也是不同问题。定理界的是 $P$ 下风险；部署改成 $Q$ 时，需要控制 $R_Q-R_P$ 或重新建模，不能把旧一致容差当迁移保证。80课保持同一个固定模型，只改变标签机制，给出正训练选择反而损害新风险的可算反例。

## 迁移题与答案

**题1。** 某输出纯经验风险距下确界不超过 $.01$，一致容差 $.03$。写出风险结论、概率与Bayes边界。

**答。** 在一致好事件上类内超额风险不超过 $.07$；该事件至少以所给 $1-\delta$ 的训练抽样概率成立。Bayes超额风险还加类外逼近误差；若根本没给它的界，就不能写出Bayes误差为 $.07$。

**题2。** 同一个求解器给正则目标gap $.01$，比较者 $\lambda\Omega(u)=.02$。一致容差 $.03$。能够得到什么？

**答。** 对这个比较者 $R_P(\widehat w)-R_P(u)\le .06+.02+.01=.09$，并可减去已知的 $\lambda\Omega(\widehat w)$改进。只写 $.07$遗漏了目标换算。拿答案回到SVM证书，说明证书的对象、单位与损失。

**题3。** 用同一个用户的64次重复观察代替64位iid用户，上界公式还可照抄吗？

**答。** 不能；原证明利用样本独立性控制经验平均的波动，重复数据没有新增独立信息。需按实际独立单位建模或采用明确的依赖数据理论。风险定义本身仍可写，iid集中结论已失去前提。

返回 [[AI/10-机器学习与深度学习基础/30-统计学习理论/00-统计学习理论-MOC|课程路线]]；继续 [[AI/10-机器学习与深度学习基础/30-统计学习理论/02-增长函数VC与不可学习|增长函数与VC]]。
