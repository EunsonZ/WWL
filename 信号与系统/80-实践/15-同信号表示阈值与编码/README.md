---
type: lab
domain: signals-systems
stage: 3
aliases:
  - 同真值STFT小波Mel与阈值编码实验
sources:
  - "[[信号与系统/20-数字信号处理/07-同信号时频多尺度表示阈值去噪与编码]]"
prerequisites:
  - "[[信号与系统/80-实践/13-Haar分析合成与边界/README]]"
  - "[[数学/70-信号处理与多模态数学/81-STFT重建与边界实验]]"
---
# 同信号表示、阈值和实际编码：每项结果都回到同一真值

[[信号与系统/20-数字信号处理/07-同信号时频多尺度表示阈值去噪与编码|应用主解释]]给出定义、推导、条件、失败例与撤提示迁移题。本目录保存同一数字测试真值的表示、两个固定噪声实现、阈值误差、真实编码文件及图，不采集硬件、不把两次实现冒称总体风险定理。

## 输入与旧源复用

[fixed-inputs.json](fixed-inputs.json) 固定 $N=256$、$f_s=1024$ Hz、单通道V、时刻 $n/f_s$，真值为 `.1 + .2*n/255 + .5*(n>=128) + .8*(n==80)`。记录时长 $N/f_s=.25$ s，最后样点时刻 $255/f_s$。生成器按索引定义事件；只改fs不会重采样同一连续波形，而会改变时间标签、记录时长和PSD归一，不能当作保持同一连续噪声谱的采样网格实验。这是已知真值的数字模型，理想单点脉冲/台阶不冒称已经经过有限带宽模拟前端。

输入卡保存两个完整256字符±符号串，每点噪声±.04V，标签seed7/11来自最初Python `random.Random(seed).getrandbits(1)`逐点生成；执行实际消费的是**符号串**，seed仅provenance标签。只改seed不改串不会改变噪声。没有Gaussian抽样或噪声标准差估计，两个固定实现不用于宣称概率保证。原噪声相对零MSE恰为.0016V²，有限去均值方差另有定义。

[representation_lab.py](representation_lab.py) 为新真源，动态导入三个已有规范源：

| 真源 | 复用行为与本次SHA256 |
| --- | --- |
| [lab13 filterbank_lab.py](../13-Haar分析合成与边界/filterbank_lab.py) | analysis/synthesis，配对奇phase1、合成偶插零；`03a5731f929b17641228708b7beb585e4c5481c3257c96e2ea8fb63483db5930` |
| [resample_lab.py](../02-流式音频重采样/resample_lab.py) | 旧完整卷积offline，由旧Haar继续调用；`773ef32198f5723e5ee7591990840efcdb30a3fbd42937d3fcf5f18d147839b1` |
| [81-STFT规范源码](../../../数学/70-信号处理与多模态数学/81-STFT重建与边界实验.py) | 完整复DFT/STFT/reconstruct；`25b34a8d211e19e087a0e5d810b08946590258544013baf9b39dcdc9da0e6c7a` |

旧源码与其活动镜像全部保持原字节；新源没有活动code-sync镜像，不在Markdown中再放一套算法。未重跑旧218 basis、44积分或旧STFT `run_checks`，只消费它们的已发布实现并检查本次新应用。

## 三份表示的共同数据与各自口径

谱比较的输入是**同一条clean数组**，不是从不同素材选择最好看的图。阈值部分的输入另为clean加两个固定噪声实现，两者在JSON/图标题中分开。

- STFT两组 `(L,H,F)=(16,4,32),(64,16,64)`，周期Hann；零延拓、帧起点 `range(-L+H,N,H)`，分别67/19帧。完整复谱shape分别67×32、19×64，DFT不缩放、逆1/F。完整记录分母约1.5，全部256点恢复；只取完整窗的对照保留真实首点unknown，不把`None`填0或裁掉首点算成功。
- 单边PSD $|X|^2/(f_s\sum w^2)$，只把内部共轭配对bin乘2，DC/Nyquist各乘1，单位V²/Hz。乘 $\Delta f=f_s/F$ 后总和等于窗平方加权均方V²。边界帧的窗归一仍是完整窗，不按有效记录长度偷偷改标度。保存全部复谱、PSD、实际覆盖和逐帧功率恒等式。
- Mel用6个高度为1、无面积归一的三角；8个节点按 `2595 log10(1+f/700)` 在0到Nyquist间等距。保存权重矩阵、Hz节点、从同一PSD计算的 `sum(B*PSD)*df`，单位V²。没有取log再参与任何逆变换。整体反号输入产生同PSD/Mel，用作具体非唯一碰撞。
- 四级Haar系数次序 `[a4,d4,d3,d2,d1]`，低支16、细节240，单位V、欧氏平方和V²。任意处理系数的原域平方误差等于相对clean系数的平方误差。若接连续积分或物理能量，先补采样间隔与对应归一，不拿离散系数平方和当J。

## 阈值、分母与反例

正式运行前固定 $\lambda=3\sigma=.12$ V，低支全部保留，只对240项细节作identity/drop/hard/soft。hard是 `v if abs(v)>lambda else 0`；soft是 `sign(v)*max(abs(v)-lambda,0)`；等号处置0。阈值不按clean真值或两个seed结果优化。

全部MSE分母固定原N，另给 $(1/f_s)\sum e^2$ V²·s。局部脉冲区和台阶区各为中心±`feature_halfwidth_samples`，默认±8、各17点；端点为首/尾各8点，共16点。各局部区可能重叠且分母不同，不直接相加。保留完整原域，不裁去不利边缘。

理论的一般风险账本只对预先固定、与噪声选择无关的保留集合成立；观测阈值集合是数据依赖的，不能直接用 `kept_count*sigma²` 作风险。正交Rademacher组合保协方差，不一般保独立；没有借Donoho的Gaussian/函数类定理认证本实验。

无噪反例固定单点幅值 $A=\lambda/2=.06$ V；四级soft把细节全部抹掉，只剩16点粗块均值.00375V。预先解析预期误差平方 $A^2(1-1/16)=.003375$ V²，保留能量.000225V²；原来零误差因此变坏。若参数使阈值0，该例退化为零，代码/图按实际条件显示。

## 实际字节格式与解码边界

八个输出是教学格式，非WAV/标准小波codec：

| 区域 | 声明格式 |
| --- | --- |
| 共同24B头 | Python struct `<4sHHIdI`：magic4/Nuint16/levelsuint16/fsuint32/qfloat64/Kuint32，little-endian标准宽度，无native padding |
| `PCM1`载荷 | 恰N个little-endian int16，levels0/K=N，总 `24+2N` byte |
| `WSP1`载荷 | K个 `<Hh`，递增uint16 index+非0 int16 code，编号对应完整Haar系数顺序，总 `24+4K` byte |

量化步长q=.01V、zero point0、Python round最近中点取偶；溢出拒绝，不clip/饱和/自动改scale。K指量化后的非零项，不是浮点阈值刚处理完的数目。magic版本固定单位V、Haar符号/相位与编号；N/levels/fs/q足以重建这个版本的记录。

程序编码成bytes、解码该bytes以算指标、写盘、再重新读取并实际解码；独立审阅再从实际文件按字节偏移另写decoder核全部结果。解码只消费文件字节与既有Haar逆，没有读clean或未编码浮点系数作旁路。严格检查长度/magic/scale/indices非零递增/元数据，容器没有校验和或真实性认证。

无溢出的正交量化误差平方至多 $Nq^2/4=.0064$ V²，MSE至多 $q^2/4=2.5\times10^{-5}$ V²；这是对**编码目标曲线**。输出同时保留对clean和对编码目标的误差，soft+量化不靠简单相加两个MSE算总体。实际总byte包括24B头和位置索引，bit/原样点除N，bit/s除记录时长N/fs。

## 重要性、独立预期、容差与失败判据

| 重要性 | 本包具体断言与独立预期 | 失败判据 |
| --- | --- | --- |
| 高 | 同clean数组/采样时刻/单位；噪声MSE恰σ²，符号串为实际输入；不将两次实现作期望定理 | 任一方法换数据/分母/截边/未记录变参即无法比较 |
| 高 | 旧Haar逐对恒等复合成有限正交W；全留、能量及任意处理后系数误差=原域误差 | 本输入max还原≤2e−12V，平方误差差≤2e−11·max(1,E)；不能用非线性basis检查替风险证明 |
| 高 | 旧STFT单边PSD积分恒等与有限覆盖；常数1V、L16/F32的完整内帧DC PSD=1/96 V²/Hz、积分1V²，D=1.5 | 恢复/功率守卫2e−11·max(1,量级)；首点unknown不能拿0或裁剪掩盖；DC全×2必失败 |
| 高 | actual Mel由已保存PSD/B/Δf积分，x和−x全功率特征相同 | 默认数组独立比较约绝对2e−11；丢Δf/面积规则变更会改变口径 |
| 高 | 弱无噪脉冲预期误差.003375V²；soft总体好不能推出局部好 | 默认解析误差绝对2e−13；任何‘阈值无损/删的全是噪声’结论被此例否定 |
| 高 | 实际codec完整长度24+2N或24+4K；独立解码还原量化系数，再核原域误差/真实文件SHA | 文件不解析、元数据/范围/长短/索引异常拒绝；quantizer bound加2e−12浮点余量；不能从未编码数组逆 |
| 中 | 2seed×4阈值方法是有限观察，预先λ=.12；预计会有不同总体/局部取舍 | 保存所有方法/区域，不删坏结果、不用真值选阈值；不以两seed外推最优风险 |
| 低 | 额外装饰扫描、更多噪声实现或原套件重跑 | 无此需要，本包省去；图只读本次数值JSON |

解码/quantizer的独立API也拒绝不匹配向量N、非正或非有限q、bool计数、溢出。有限输入预算为N64/128/256；Haar层数1..log2N；各真值分量≤2V、σ≤.2V、q在[.01,1]V；在该上界下变换系数不导致int16预算必溢出。采样率1..1e6整数；1..2个不同噪声标签/完整符号串；1..2组窗L8..64的2幂、H=L/4或L/2、F≥L且≤64的2幂；Mel2..6带。预算是有限实验接口，不是理论定义域。

## 本机实际运行与复现

2026-10-17，既有Python3.14.7/NumPy2.5.3，macOS27.0.1 arm64；无依赖安装。共享runner取2个flock槽中的一个，强制OMP/OpenBLAS/MKL线程1。默认组限180s，实际约.1231s；测试限60s，7项约.087s。不是硬件实时deadline保证。

在当前候选实验目录实际执行：

```bash
WWL_HAAR_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/13-Haar分析合成与边界/filterbank_lab.py' WWL_RESAMPLE_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/02-流式音频重采样/resample_lab.py' WWL_STFT_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/数学/70-信号处理与多模态数学/81-STFT重建与边界实验.py' /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B /private/tmp/wwl-next-context/run_local.py --timeout 60 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B -m unittest -v test_representation_lab.py > author-tests.txt 2>&1
/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B /private/tmp/wwl-next-context/run_local.py --timeout 180 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B representation_lab.py --inputs fixed-inputs.json --haar-source '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/13-Haar分析合成与边界/filterbank_lab.py' --resample-source '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/02-流式音频重采样/resample_lab.py' --stft-source '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/数学/70-信号处理与多模态数学/81-STFT重建与边界实验.py' --output results > author-run.txt 2>&1
/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B plot_representation.py --results results/results.json --output results
```

作者随后补强独立codec入口的N匹配/scale/类型检查，并加量化q=0和短向量N不匹配回归，用同一测试命令只换输出日志为 `author-tests-final.txt`；7项再次通过，约.079s。此验证不改变正式固定输入路线，默认数值/8文件复用第一次运行，没有冒称重跑。图的参数化显示修订只从保存JSON重生，不重新计算STFT或噪声。

完整库发布后，本机同环境可直接使用兄弟/根目录默认真源，写一个尚不存在的新目录：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B representation_lab.py --inputs fixed-inputs.json --output results-rebuilt
python -B plot_representation.py --results results-rebuilt/results.json --output results-rebuilt
```

多任务协作仍使用共享两槽runner；上述直接命令不自行获取槽。隔离候选必须像真命令一样传三个旧源路径。换机先核可用环境，不把本机依赖事实泛化为换机已运行。

## 实际结果入口

[results.json](results/results.json) 保留全部原真值/组件/时刻、观察noise、Haar各方法系数/曲线/误差、两STFT全部复谱和PSD/Mel、codec头字段/量化误差/两目标误差和SHA。逐方法地区指标见 [metrics.csv](results/metrics.csv)，stdout见 [author-run.txt](author-run.txt)，回归见 [author-tests.txt](author-tests.txt) 与 [author-tests-final.txt](author-tests-final.txt)。

| 实际文件（均已写盘重读decode） | 总byte | 含头bit/原样点 | 对clean MSE V² |
| --- | ---: | ---: | ---: |
| [clean-pcm.toy](results/clean-pcm.toy) | 536 | 16.75 | 8.29759e−6 |
| [clean-haar.toy](results/clean-haar.toy) | 164 | 5.125 | 4.78343e−6 |
| [seed7-pcm.toy](results/seed7-pcm.toy) | 536 | 16.75 | .00161173 |
| [seed7-haar.toy](results/seed7-haar.toy) | 648 | 20.25 | .00169664 |
| [seed7-soft-haar.toy](results/seed7-soft-haar.toy) | 104 | 3.25 | .000523415 |
| [seed11-pcm.toy](results/seed11-pcm.toy) | 536 | 16.75 | .00161369 |
| [seed11-haar.toy](results/seed11-haar.toy) | 652 | 20.375 | .00168665 |
| [seed11-soft-haar.toy](results/seed11-soft-haar.toy) | 104 | 3.25 | .000342695 |

非零严格少于一半才足以在本固定4B/index-value合同下比2B/样点小；不是一般压缩定理。原带噪稀疏文件比PCM大，阈值后小但有结构偏差。总体hard/soft改善与soft脉冲区变差同时保存，不能只按较小文件或较平曲线交付结论。

[plot_representation.py](plot_representation.py) 只读保存JSON生成 [representations.svg](results/representations.svg) 与 [denoising.svg](results/denoising.svg)。前者严格标clean、PSD绝对共同色标/截断显示、时间—尺度支持和Mel单位；后者保留全曲线/局部细节/全部case指标以及无噪反例。颜色外还有实虚线/行标签/title/desc与CJK字体回退。绘图的显示floor/色标截断不改变保存数据或误差。

非作者独核已以显式Haar矩阵、独立roots-recurrence DFT和固定偏移字节decoder逐核所有默认数据/8文件；不import作者函数或三个旧source当答案。另一实际CLI卡改到N128/fs800/J3、offgrid edge49/pulse77、σ.03/λ.075/q.02、两新符号实现、不同hop/FFT/Mel4，全部通过；全零N64/σλ0的空稀疏payload也通过。一般风险和单位推导另核原文与正文，旧source被复用不冒充第二独立oracle。最终两正式SVG已由非作者用CairoSVG渲染并实际查看通过：共同PSD色标、时间/频率/尺度单位、局部误差与无噪对照可读，无截断重叠；保存JSON重生两SVG字节一致。30wiki目标/标题、23relative路径及五页局部patch当前apply--check独核通过；第7自主选择表示迁移题与答案已核。原生Obsidian尚未验，完整#182仍OPEN。

## 迁移与未验接口

本机结果只管这个有限数字真值/容器与声明变式，不验证真实录音、感知改善、生产codec、连续db2/双正交存在/稳定性或一般长边界。真实采集应保存校准/单位、采样率与时间戳、抗混叠前端、量化和缺样/削顶、完整记录长度；预先声明真值或可辨识参考与误差预算，再比较模型偏差/噪声/边缘任务指标。没有独立真值时，不能把平滑后的峰消失直接叫噪声去除。

外部codec比较还需实际编码版本、所有头/码表/位置/校验开销、完整decode以及同失真/任务指标；固定q不等于不同codec在相同失真下比较。硬件实时性需设备上完整延时与deadline测量；本次未运行设备、原生Obsidian或真人感知/学习验收。完整#182的高阶/双正交连续构造、稳定/正则性及长边界按实际余项继续，不因本应用实例关闭整课。
