---
type: lab
domain: signals-systems
stage: 3
aliases: []
sources:
  - https://ocw.mit.edu/courses/18-327-wavelets-filter-banks-and-applications-spring-2003/9ae8fd2b4313aea9cb1d828e3d431301_Handout3.pdf
  - https://ocw.mit.edu/courses/18-327-wavelets-filter-banks-and-applications-spring-2003/48b610fc0f1cc941fb7d1677d48b7a1f_Handout5.pdf
  - https://ocw.mit.edu/courses/18-327-wavelets-filter-banks-and-applications-spring-2003/d22d96dea13c0396474b1d87439fc4d0_Handout15.pdf
prerequisites:
  - "[[信号与系统/20-数字信号处理/05-完美重建滤波器组与小波]]"
---
# Haar联合恢复与有限边界：从四点到全部基向量

本实验核的是同一线性分析—合成算子，而非在一段素材上听起来像原声。[[信号与系统/20-数字信号处理/05-完美重建滤波器组与小波|主解释]]提供任意输入的两通道混叠/失真条件、相位/多相约定、Haar逐对恒等式与边界反例。现有STFT覆盖重建继续复用原页，不在这里另造一个STFT实现。

## 直接复用哪个真源

[filterbank_lab.py](filterbank_lab.py) 直接导入已有 [resample_lab.py](../02-流式音频重采样/resample_lab.py) 的 `offline`：分析用 `factor=2,phase=1`，合成用同一函数 `factor=1,phase=0` 作完整卷积。原函数和它的活动源码镜像均未改。本目录只新增两支组合、边界及有限核对；不复制原193抽头滤波器、流式环状态或定点实现。

默认从当前目录的兄弟实践02加载规范源；隔离候选未携带整个库时，通过 `--resample-source` 指定主库真源。结果保留所读绝对路径及SHA-256；本次真源为 `773ef32198f5723e5ee7591990840efcdb30a3fbd42937d3fcf5f18d147839b1`。读者应使用自己当前同版真源，不从旧Markdown镜像执行代码，也不把哈希相同当作本次又跑了一遍旧重采样全套。

既有本机 `.venv` 实测Python3.14.7、NumPy2.5.3可用，未安装组件。绘图 [plot_filterbank.py](plot_filterbank.py) 只需标准库，仅读落盘JSON。规范算法源在`.py`，本目录不新增重复代码镜像。

## 固定输入、相位与边界

[fixed-inputs.json](fixed-inputs.json) 固定四点 $(1,3,2,6)$ V、奇五点 $(1,3,2,6,5)$ V、$f_s=8$ Hz，边界 `zero`/`repeat`，有限长度 $N=1,2,3,4,5,7,8,16,31,32$，离散shear参数 $\lambda=.5$。

分析因果tap为 $h_0=(1,1)/\sqrt2,h_1=(-1,1)/\sqrt2$，保留完整卷积的奇下标 $2m+1$，得到 $a=(e+o)/\sqrt2,d=(e-o)/\sqrt2$。合成系数插在偶位置，$f_0=(1,1)/\sqrt2,f_1=(1,-1)/\sqrt2$；完整线性卷积后恢复原配对。数学输出无下标延时，实际每对必须收到奇样点以后才可用，8 Hz下首对至少等1/8 s。

原长度为奇数时，只向右补一个0或重复末点，分析/合成后按保存的原 $N$ 裁剪；源数组未被就地修改。这个有限两抽头边界不冒充一般长小波滤波器的对称延拓算法。两支系数及原长度/边界/相位必须同时保留，不能从系数数量猜原帧边界。

同时做两类故意失效：将合成高支整体反号，会交换每对，四点输出 $(3,1,6,2)$；把分析改为phase0，则同四tap变成一拍延时，完整输出先保留，正确裁 `y[1:1+N]`，错误裁 `y[:N]` 得 $(0,1,3,2)$。这些失败是事先从代数预言，未通过调整裁剪把它们伪装成PR。

## 重要性、事先预期与失败判据

**一般PR/抽取相位、边界裁剪、能量/投影断言是高重要性**：其中一个符号或延时错了，某些常数素材仍可通过；误用边界能量会把有损处理叫作正交投影。**图的颜色及额外随机扫参不承重**，本实验不靠增加扫描数量强化结论。

| 核对对象 | 正式运行前由手算/线性模型确定的预期 |
| --- | --- |
| 四点全留 | $a=(2\sqrt2,4\sqrt2)$、$d=(-\sqrt2,-2\sqrt2)$，恢复原四点；离散平方和50=40+10 V²。不是J，也不是连续能量积分。 |
| 丢四点细节 | 低保留 $(2,2,4,4)$，误差10 V²；错误高支符号输出 $(3,1,6,2)$，误差40 V²。 |
| 奇五点zero | 延拓平方和/系数平方和75 V²，低保留裁为 $(2,2,4,4,2.5)$，原域误差16.25 V²；细节平方和22.5 V²属于6维延拓误差。原域低保留矩阵的幂等误差为.25。 |
| 奇五点repeat | 延拓/系数平方和100 V²，而原域75 V²；裁剪全留仍恢复，低保留原域误差10 V²。 |
| 有限非正交双基 | $a'=a+.5d,d'=d$，逆先还原 $a=a'-.5d'$；全留恢复，系数平方和32.5 V²，删 $d'$ 后 $(1.5,1.5,3,3)$、误差12.5 V²。四点低保留幂等但非对称（最大差.5）。不宣称连续双正交小波/MRA构造。 |
| 多尺度首桥 | 四点二级系数 $a_2=6,d_2=-2,d_1=(-\sqrt2,-2\sqrt2)$；常数3的细节0，斜坡 $x[n]=n$ 的细节 $-1/\sqrt2$。Haar恰一个消失矩来自正文直接积分，不靠有限样本证一般定理。 |

固定记录恢复误差容差为 $2\times10^{-12}\max(1,\max|x|)$ V；字面固定系数/范数回归用 $10^{-13}$ V或约 $10^{-12}$ V²。全部basis形成的PR矩阵每元素误差≤$2\times10^{-12}$。容差在正式运行前按浮点计算尺度选定，不因失败后改输入刷过；错误符号/相位应产生上表的明确错误。

若失败，保留新目录、实际输入/真源和stdout，先查卷积相位、插零位置、尾点、原长度/边界及归一化；不得靠删不利边缘缩小误差。程序拒绝覆盖已有输出目录和图文件。

## 全部basis能证明到哪里

每个固定 $N$、固定边界都处理 $N$ 个标准基向量；把所有恢复列合成 $Q_N$，检查 $Q_N-I_N$，另组成低保留矩阵 $P_N$ 核 $P_N^2-P_N$ 与 $P_N-P_N^T$。固定输入是20个长度/边界组合，共218个基向量。精确线性代数下，全部列确定这个有限算子，故能判该 $N$ 域的全输入PR；浮点运行则是对应实现的有限数值核对，不能形式认证全部机器数、溢出域或所有长度。

任意偶长度的数学结论另由每对2×2逆矩阵证明；奇长度的全系数恢复来自显式线性延拓 $E_N$、成对逆变换以及裁剪 $C_NE_N=I_N$。`repeat`并非原欧氏能量等距，`zero`删细节后裁剪也不保留原域正交投影。本实验没有整数取整lifting、阈值、饱和或自适应分支；那些流程非线性，不能拿basis测试充全输入证明，必须另证逐步逆或相应条件。

## 实际运行与重放

2026-10-16在候选目录、macOS27.0.1 arm64实际运行，Python3.14.7/NumPy2.5.3，1进程1线程，经共享两槽调度器。测试限60秒，正式有限计算限180秒，预定全组少于5分钟。实际命令（当前目录为本实验目录）：

```bash
WWL_RESAMPLE_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/02-流式音频重采样/resample_lab.py' /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B /private/tmp/wwl-next-context/run_local.py --timeout 60 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B -m unittest -v test_filterbank_lab.py > author-tests.txt 2>&1
/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B /private/tmp/wwl-next-context/run_local.py --timeout 180 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B filterbank_lab.py --inputs fixed-inputs.json --resample-source '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/02-流式音频重采样/resample_lab.py' --output results > author-run.txt 2>&1
/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B plot_filterbank.py --results results/results.json --output results
```

首轮7项回归与正式218basis通过，正式计算耗时0.028秒；这是本次观测，不是设备时限保证。独核随后发现合法高幅原输入的内部系数可能超过原输入上限，作者将 $10^6$ V预算移到原输入校验，内部系数只核类型/有限，新增高幅回归后8项通过，记录 [author-tests-final.txt](author-tests-final.txt)。该验证修订不改变固定输入的数值路径，正式默认结果复用上述一次运行，未冒称重跑218basis。最终相关测试命令与首轮相同，只将stdout写到 `author-tests-final.txt`。

共享调度器/上述绝对路径是本机事实，不是分发依赖。接入完整库后，可从库根用已有支持NumPy的解释器重放到自己的新目录：

```bash
.venv/bin/python -B -m unittest discover -s '信号与系统/80-实践/13-Haar分析合成与边界' -p 'test_filterbank_lab.py' -v
.venv/bin/python -B '信号与系统/80-实践/13-Haar分析合成与边界/filterbank_lab.py' --inputs '信号与系统/80-实践/13-Haar分析合成与边界/fixed-inputs.json' --output /private/tmp/haar-replay-new
.venv/bin/python -B '信号与系统/80-实践/13-Haar分析合成与边界/plot_filterbank.py' --results /private/tmp/haar-replay-new/results.json --output /private/tmp/haar-replay-new
```

未搬整库的候选需额外传 `--resample-source`，测试可用 `WWL_RESAMPLE_SOURCE` 环境变量指定同一真源。程序需要NumPy，因为原`offline`本就用它；没有偷偷以另一套卷积替代缺依赖。如环境缺失，先按既有环境合同处理，再运行，不将未执行写成通过。

原记录输入限制1至32有限实数、绝对幅值≤$10^6$ V，第一条4点、第二条奇长；sampling rate正有限至 $10^6$ Hz，边界仅zero/repeat，1至16个不同整数basis长度1至32，$|\lambda|\le1$。bool不当样本或计数，非有限、非法mode/长度拒绝。这些是有限输出/浮点预算，不是理论定义域。变换后的合法系数可超过原输入幅值，例如四个 $10^6$ V的低系数约 $1.414\times10^6$ V；不应因此把合法输入挡在逆变换前。

## 数据与图

[results.json](results/results.json) 保存输入、实际解释器/NumPy、复用真源路径/hash、4种记录/边界、20组有限矩阵指标、相位0完整输出、两级系数与常数/斜坡响应。[samples.csv](results/samples.csv) 逐样点列原输入、全留、低保留、shear低保留和错误高支；[basis.csv](results/basis.csv) 列每个 $N$ 的矩阵误差与幂等/对称指标。原始stdout见 [author-tests.txt](author-tests.txt)、[author-run.txt](author-run.txt)。

![四点Haar两支与恢复](results/haar.svg)

![奇长度边界及可逆非正交反例](results/boundary.svg)

图由 [plot_filterbank.py](plot_filterbank.py) 仅读同一JSON生成，含title/desc、CJK字体回退、实/虚线和圆/方点。主图的全系数恢复与输入重合，低保留/故意错误各自显示，不能因为一条重合线就宣称所有输入都通过。第二图把原域能量、延拓/系数能量和裁剪误差分别列出。

## 改条件再回到主解释

先用另一个奇长记录预测最后配对、系数数量和裁剪范围；再改变 `odd_samples_V` 到新目录。若变更 $\lambda$，先预测全留仍逆，但系数能量和斜投影方向会变；$\lambda=0$退回正交Haar。若把分析phase改0，不能只改函数参数：合成后的延时补偿、输出保留区间和理论前因子都须一起重查。

主文[[信号与系统/20-数字信号处理/05-完美重建滤波器组与小波#撤去Haar名字，再交完整的恢复承诺|迁移题]]含解释答案。改变阈值/舍入或丢更多系数已经改变算子；稀疏、压缩文件、去噪优劣需实际码率与独立真值失真，不由本页PR核对代签。

## 独核、外部接口与未验层

作者回归与执行是第一层；非作者从精确逐对算术、边界矩阵、z域和相位另建参考，不导入作者函数或旧offline作答案，再核固定结果、改参数和图像。独核已用未导入作者函数/旧offline的Fraction逐对与边界矩阵核4记录、两CSV、20组合218basis、phase0完整延时、shear及投影指标；另改记录/长度/采样率/λ的104basis通过，合法高幅修后CLI与独立舍入包络核对通过，6组非法输入CLI退出2且不创建输出。两正式SVG在已有CairoSVG中实际渲染目视，文字/标签/边界/单位清楚，重生字节一致；这是该渲染器的像素核对，不推定原生Obsidian通过。最终逐项签收随本批接收记录，不把复用旧实现冒称第二份独立答案。

真实采集、流式交付与压缩/去噪应用各需输入与失效条件，当前仅保留接口、不接硬件：

| 外部输入/条件 | 预期及失败接口 |
| --- | --- |
| 完整原采样序列、幅值单位/采样率、帧原长度、两支系数及相位、边界/滤波器、滤波状态 | 全留恢复至声明延时/容差；缺支、漏尾、相位或边界元数据错时，保留错误索引与完整分母。 |
| 分块到达时刻、历史与EOF、排队/运算/播放时间 | 理论无下标偏移不等于低时延；至少等到每对第二个输入，实际deadline须设备时间戳测量。 |
| 量化/舍入/阈值/饱和规则和实际编码文件 | 重新核非线性逆、溢出、码率/开销及原坐标误差；不能仍引用线性basis判定。 |
| 原始真值、噪声/场景与独立评测、边缘恢复和感知指标 | 去噪/压缩不要求全留PR，但要报告有损收益与代价；无真值时不报已恢复真实细节。 |

未验：原生Obsidian显示、真实采集/设备实时deadline、整数lifting/量化码率、完整小波/双正交MRA构造、长边界和STFT/小波/Mel同信号应用比较、真人迁移理解。#182完整课程仍按这些余项判断，不因本首包闭合而自动关闭。
