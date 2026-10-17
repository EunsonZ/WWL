---
type: lesson
domain: mathematics
stage: 3
aliases: []
sources:
  - https://builds.openlogicproject.org/open-logic-complete.pdf
  - https://people.math.ethz.ch/~halorenz/4students/LogikGT/masterthesis.pdf
prerequisites:
  - "[[数学/12-离散数学与逻辑/20-数理逻辑与集合论/05-算术编码可表示性与证明谓词]]"
  - "[[数学/12-离散数学与逻辑/20-数理逻辑与集合论/06-对角引理Godel与Rosser第一不完备]]"
---
# 第二不完备：固定Prov以后，谁能证明哪一种一致性

“系统不能证明自己一致”必须补齐系统、证明谓词和一致性句。这里沿05的 $T=PA\cup W$ 及具体带证书 $\Prov_T$，不把任意写着“自洽”的句子当作同一定理。

## Löb定理：反思规则有多强

缩写 $\Box A=\Prov_T(\nu(\ulcorner A\urcorner))$，D1是外部可导性规则，D2/D3是PA已证明的内部句。**Löb定理**说：若 $T\vdash\Box A\to A$，则 $T\vdash A$。本身不需要先假设T一致；它说明一旦某个内部反思式可证，代价是A本来就已可证。

用06对角引理取句子L，使
$$T\vdash L\leftrightarrow(\Box L\to A).$$
完整推导如下，所有未标为元步骤的蕴含都在T内部。

| 步 | 得到什么 | 为什么 |
|---|---|---|
| 1 | $L\to(\Box L\to A)$ | 固定点一方向 |
| 2 | $\Box L\to\Box(\Box L\to A)$ | 对1用D1，再D2 |
| 3 | $\Box(\Box L\to A)\to(\Box\Box L\to\Box A)$ | D2实例 |
| 4 | $\Box L\to\Box\Box L$ | D3 |
| 5 | $\Box L\to\Box A$ | 2/3/4，蕴含接合 |
| 6 | $\Box L\to A$ | 5与题设T已证的 $\Box A\to A$ |
| 7 | L | 固定点反方向与6 |
| 8 | $\Box L$，再得A | 对已得定理7用D1，再用6 |

没有在第8步把“假设L”为真就套D1；7已经是T的定理。这也是不能把D1误当内部 $A\to\Box A$ 或 $\Box A\to A$ 的原因。

## 具体Con与第二不完备

固定算术假句 $\bot_A\equiv0=S0$，定义
$$\operatorname{Con}_T\equiv\neg\Prov_T(\nu(\ulcorner\bot_A\urcorner)).$$
T包含PA，故证明 $\neg\bot_A$。不证明逻辑 $\bot$ 与不证明 $\bot_A$ 等价：从逻辑矛盾可爆炸得 $\bot_A$，反向用PA的 $\neg\bot_A$ 合成逻辑矛盾。因此这个Con准确表达“没有这种标准带证书T反证”。

若T一致却证明 $\operatorname{Con}_T$，由否定与爆炸，它证明 $\Box\bot_A\to\bot_A$。Löb取A为 $\bot_A$，得到 $T\vdash\bot_A$，与一致性矛盾。于是
$$\boxed{T\text{一致、可枚举公理化且含PA}\ \Longrightarrow\ T\not\vdash\operatorname{Con}_T.}$$
这没有预设ω一致，也不意味着T证明 $\neg\operatorname{Con}_T$。若T一致，标准N中的Con真，由定义和证书标准正确性可知；“标准真但内部不可证”的对象在这里同样明确。更强理论可以证明较弱理论的Con，只须写清强弱理论与自身新的边界，不能把它冒称弱理论自证。

## Gödel句与Con在这个呈现中怎样关联

对06的原Gödel句 $G_T\leftrightarrow\neg\Box G_T$，本课的具体编码还能在PA中推出
$$G_T\leftrightarrow\operatorname{Con}_T.\tag{GC}$$
证明不以一致性为内部前提：由PA已证 $\bot_A\to G_T$，D1/D2给 $\Box\bot_A\to\Box G_T$，所以G的否定可证性读数给 $G_T\to\operatorname{Con}_T$。

另一边，$G_T\to\neg\Box G_T$ 的D1/D2给 $\Box G_T\to\Box\neg\Box G_T$，D3给 $\Box G_T\to\Box\Box G_T$。一份 $\Box G_T$ 的证明与其否定的证明可用固定矛盾推导合成 $\bot_A$ 的证明，D2把这项构造内化，故 $\Box G_T\to\Box\bot_A$。逆否得 $\operatorname{Con}_T\to\neg\Box G_T$，再用固定点得G。这里所有使用D1的有限定理本身由PA给出，05的正证书检查也在PA可证，故(GC)在PA就成立。该结论针对本课原G及标准Prov，不是任意独立句都等价于一致性，也没有说Rosser句必须满足(GC)。

## 一致却证明假Σ1：一份准确相对反例

假设PA一致，令
$$U=PA+\neg\operatorname{Con}_{PA}.$$
U仍一致。否则有限证明可在PA里用RAA解除额外假设 $\neg\operatorname{Con}_{PA}$，得到 $PA\vdash\operatorname{Con}_{PA}$，与第二定理矛盾。U是含PA的可枚举理论，却证明标准假Σ1句 $\neg\operatorname{Con}_{PA}$；标准假来自元假设“PA没有真实反证”，不是来自U本身的认证。

它还证明**自己**原Gödel句 $G_U$ 的否定。05的PA证明到U证明嵌入给 $PA\vdash\operatorname{Con}_U\to\operatorname{Con}_{PA}$，所以U中的 $\neg\operatorname{Con}_{PA}$ 推出 $\neg\operatorname{Con}_U$；由(GC)得 $U\vdash\neg G_U$。U一致仍保证N中 $G_U$ 真且U不证明 $G_U$，与06的第一侧完全一致。$G_U$ 与 $G_{PA}$ 是不同句子，不偷换理论下标。

这证明：一致不等于Σ1健全，也不等于ω一致；原Gödel句的第二侧需要补条件。Rosser定理在同一U上仍给另一个句子 $R_U$ 的双向不可证，两种构造没有冲突。

## 不可删的前提与任意“自洽”句的陷阱

**有效公理化不能删。** 真算术 $\operatorname{Th}(\mathbb N)$ 包含PA，一致，并且每句或其否定按标准真值就在理论里，所以完备。若它还能有效枚举，Rosser会让它不完备，矛盾；故真算术不是可枚举公理化理论。04使用它作紧致前提只要它是一个句子集，没有声称能枚举，逻辑完全相容。

**算术表达能力不能删。** 在只有常量c与等号的语言，$T_1=\{\forall x(x=c)\}$ 恰有一个单点结构（至同构）。每个句子可递归求真假：项都指同一点，等式真，量词只有一个值。由03强完备，T₁对每句可证明其真方向，是一致、完备而且可判定的理论；它没有包含PA所需的算术结构。不能仅看“无限多公式”就套不完备。

**一致性不能删。** $PA+\bot_A$ 不一致，爆炸可证每句，包括自身Con及其否定。它没有反驳任何带“一致”的结论。

**同一个标准外延，不保证同一个内部呈现。** 设 $a=\ulcorner\bot_A\urcorner$，造
$$P^*(x)\equiv\Prov_T(x)\land x\ne\nu(a).$$
PA显然证明 $\neg P^*(\nu(a))$。若T一致，标准N中原Prov本就不含a，故 $P^*$ 与Prov对全部标准自然数取值相同；但T不能因此把这个新公式当成原标准Prov来套第二定理。若它还同时具所需D1–D3，Löb会再次阻止这项“自证”，所以至少一项内部条件不能保留。这里显示的是**表示方式和内部证明条件**的敏感性，不是“一致性随换一个名字便解决了”。

回到 [[哲学与文化/20-论证知识与规范/04-量词有效性与反模型#共同正文：变量赋值怎样决定真假|真值的模型范围]] 与 [[AI/13-搜索推理与规划/05-知识表示规则归结与查询#两个模型把开放世界的未决定算清|查询未决定]]：02的空理论双模型是一个具体句子的语义未决定；Gödel/Rosser是满足明确算术条件的一整类有效理论的元定理。某次搜索超时仍不能声称已定位独立句、标准真值或任意硬件程序不可能认证。

ZF/ZFC、Cantor与内外可数现由 [[数学/12-离散数学与逻辑/20-数理逻辑与集合论/08-ZF公理Cantor与模型内外的可数|08]] 承担，接09的序基数/超限递归、10的AC/Zorn与实际存在性应用。那条链的理论与模型前提独立写清：本页没有通过算术元定理认证ZF一致，也不把全部证明论、模态逻辑或高级独立性冒称已证。

## 迁移题

1. 对固定一致T，若 $T\vdash\Box A\to A$，能得什么？分别取 $A=0=0$ 与 $A=\bot_A$，结论为何不同？
2. 假设PA一致，U=PA+¬ConPA。它是否一致、Σ1健全、ω一致？它证明的是 $\neg G_U$ 还是仅 $\neg G_{PA}$？逐个给所需桥。
3. $P^*(x)$ 在标准N与Prov同外延，却有PA可证的“无a证明”。为什么不是第二定理的反例？仅有标准外延相同足够转移哪些内部条件吗？
4. 真算术既一致又完备，为什么没有反驳Rosser？紧致性使用它是否要求能运行其公理枚举？
5. 某AI系统回答“我未找到反证，所以已经在自身规则里证明自身一致”。请标出它缺少的理论/证明谓词/有限推导/一致性句证据；与本页真正的第二定理比较。

## 题解

1. Löb给 $T\vdash A$。若 $A=0=0$，PA本来就证明A，因而也能证明 $\Box A\to A$，没有冲突。若 $A=\bot_A$，一致T不能证明A，所以也不能证明该反射实例；“我证明了自身可证明性对每句都正确”比已给D1–D3强得多。
2. 由PA一致和第二定理，PA不证ConPA；若U不一致，用RAA解除额外的¬ConPA即可在PA证明ConPA，矛盾。因此U一致。它证明标准假的Σ1句¬ConPA，故不Σ1健全。PA到U的证明嵌入在PA中给 $\operatorname{Con}_U\to\operatorname{Con}_{PA}$，逆否使U证明¬ConU；PA层(GC)又给 $G_U\leftrightarrow\operatorname{Con}_U$，故U证明 $\neg G_U$，并非只论 $G_{PA}$。06还给每个标准n的 $\neg\Prf_U(\nu(n),\nu(\ulcorner G_U\urcorner))$，而U由¬G_U证明其存在量化，直接违反ω一致。
3. 第二定理的对象是05固定的具体Prov与内部D1–D3。标准N的外延相同，只是对标准输入真值相同；并未在PA或T中证明相应的统一公式、证明拼接或正内省。PA可证¬P*(ν(a))，若该P*仍同时满足足够的内部条件，Löb会推出假句，和T一致矛盾。因此不能把“外延恰相同”当成自动转移内部导出条件的桥。
4. Th(N)不满足可枚举公理化条件；否则Rosser与其完备性矛盾。紧致性是关于任意句子集的有限可满足性与整体可满足性，不要求输入公理能由计算机枚举。04的每个有限约束在标准N满足，就可用于这个语义定理；它没有提供真算术算法。
5. 首先须固定所谈系统T是否为有效给出的算术理论、规则是哪套、是否有PA表达能力；然后给具体标准Prov与它的编码、写出具体Con句，并展示规则内的有限证明。“搜索未找到”只是某段运行未输出，既没有给Con的有限推导，也没有排除未来反证。若恰满足本包条件且T一致，第二定理进一步排除这项内部Con证明；不满足条件的AI查询仍应按实际模型与规则分析，不能靠一句Gödel口号代办。

## 来源边界

Open Logic Project §37.7 提供从固定点和可证明性条件到第二不完备的推导；本页另完整写出Löb链与(GC)，把05的PA层条件实际用到。Krapf《A Complete Proof of Incompleteness》§4.3（印刷47–52页）展开另一种Hilbert编码下的导出条件，其具体系统与本包ND不同；05已给本系统的结构证明，未声称照搬该文的逐行证书。有限实验只核代码接口与证明拼接的一小片段；不能运行一次程序便宣布PA或U一致。
