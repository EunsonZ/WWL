---
stage: 1
aliases: ["监督 HMM POS 训练", "UNK 与 Viterbi"]
sources:
  - "https://web.stanford.edu/~jurafsky/slp3/A.pdf"
prerequisites:
  - "[[AI/35-传统NLP/10-真实语料序列标注/01-固定语料投影与切分]]"
---
# 监督 HMM：训练计数、UNK 与 Viterbi

训练句是 $(w_{1:T},y_{1:T})$，其中 $w$ 为 `FORM`，$y$ 为 `UPOS`。先只用训练集数词频。训练中出现次数不超过 1 的字符串被替换为 `<UNK>`；因此 `<UNK>` 的发射计数来自训练，也能为真正未见测试词保留概率。词表不能观察 dev/test 后扩充。

这接着 [[AI/35-传统NLP/02-HMM前向后向与Viterbi|手算 HMM 课]] 同一个问题：给定词序列，求最大联合概率的标签路径。手算课把 $\pi,A,B$ 指定为便于计算的概率，下面把参数换成固定训练子集上的计数估计；标签和词形的变化来自真实 UD 投影，动态规划仍是同一条 Viterbi 递推。真实前置是 [[AI/35-传统NLP/10-真实语料序列标注/01-固定语料投影与切分|固定语料输入与切分]]：该页在首次读取前记录 UD English EWT r2.16 的 tag/commit、许可说明和原文件 hash；本训练子集是其中 train 文件按文档规则保留的 3,113 句、45,820 个整数 token，不代表整个语料库。

令 $C_{start}(j)$ 是第一个标签计数，$C(i,j)$ 是标签相邻计数，$C(j,w)$ 是经 UNK 映射后的发射计数。对标签集合 $Y$、词表 $V$ 和平滑 $alpha>0$：

$$
P(y_1=j)=\frac{C_{start}(j)+\alpha}{N_{sent}+\alpha|Y|},\quad
P(y_t=j\mid y_{t-1}=i)=\frac{C(i,j)+\alpha}{C(i,\cdot)+\alpha|Y|},\quad
P(w\mid y=j)=\frac{C(j,w)+\alpha}{C(j,\cdot)+\alpha|V|}.
$$

分母的对象不同：初始项按句数，转移项按“前标签 i 后面确有下一个 token”的计数，发射项按标签 token 数。这里是教学中的一阶、固定长度 HMM，没有 EOS 概率；每句单独 Viterbi，不让上句末标签转到下句首标签。

小算例：训练两句 `can/VERB fish/NOUN` 与 `fish/NOUN swim/VERB`，将 `can`（若只出现一次）映射 `<UNK>`。`C(VERB,NOUN)=1`，`C(NOUN,VERB)=1`。新句 `can fish` 的第一词映射 `<UNK>`；Viterbi 对每个候选标签保存“到此标签的最大 log 分数”和其前标签，最后回溯。它找的是最大联合路径，不是每个位置单独最大后验标签。

开发集只比较 α∈{0.01, 0.1, 1.0} 的 HMM token accuracy，选最大者后冻结。此次运行选 α=0.01；选择发生在 test 之前。另有两条不使用上下文的参照：**unigram** 永远预测训练中最多标签，**word-frequency tag** 对训练见过的词预测其最常见 UPOS、否则回退最多标签。它们不是 HMM 的不同平滑，而是检验词形和标签链各自贡献的基线。

### 迁移题

若把 dev 的 OOV 词也加进词表再选 $alpha$，有什么问题？**答案：** 词表已利用开发输入，实验不再是“训练词表处理未知词”的测量；即使没有看 dev 标签，也改变了输入处理规则。应把词表规则固定在 train，然后才用 dev 选择已声明的有限参数。
