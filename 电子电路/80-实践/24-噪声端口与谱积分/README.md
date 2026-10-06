---
stage: 1
aliases: []
sources:
  - https://www.ti.com/lit/an/slva043b/slva043b.pdf
  - https://www.analog.com/en/resources/technical-articles/coherent-sampling-vs-window-sampling.html
prerequisites:
  - "[[电子电路/38-随机噪声与测量/01-RMS方差相关与谱密度#每Hz的面积与每弧度的面积]]"
  - "[[电子电路/38-随机噪声与测量/03-噪声端口传递与输入等效#从原KCL得到七条传递]]"
  - "[[电子电路/38-随机噪声与测量/05-互谱FFT与噪声测量#FFT密度归一化与Parseval账本]]"
---
# 噪声端口与谱积分：一份可复算账本

本实践是五章正文的唯一CPU源码入口，真源为同目录 `noise_models.py`、`test_noise_models.py`、`generate_figures.py`。不另建逐字源码镜像。基础入口先预测300 K/2 kΩ开路PSD和四点记录面积，再运行；快进入口先查看 `ports` 的原KCL方向与 `spectral_output` 的共轭约定，再核对输出字典。两入口比较同一份参数、结果和图数据。

## 从库根启动，输出放新库外目录

主库已有.venv的NumPy/Matplotlib/CairoSVG/Pillow足够，本组不安装。以下命令从WWL库根执行；把输出目录换成自己新的库外路径，避免覆盖已有实验。

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/24-噪声端口与谱积分' -p test_noise_models.py -v
.venv/bin/python -B '电子电路/80-实践/24-噪声端口与谱积分/noise_models.py' --output /private/tmp/noise-my-new-run
.venv/bin/python -B '电子电路/80-实践/24-噪声端口与谱积分/generate_figures.py' --output /private/tmp/noise-my-new-run/figures
```

候选审阅阶段把源码路径改为隔离候选的绝对路径，cwd仍为库根。两程序 `main(argv=None)` 的 `--output` 必填，缺参数先退出2，不创建输出；显式调用 `generate(output)` 才生成。导入不读argv、不加载NumPy/Matplotlib、不生成文件或字体缓存；重依赖在调用时懒加载。图层用Figure/Agg直接构造，不用pyplot；生成时字体缓存限于指定输出目录的隐藏子目录。配置用局部rc_context，成功或异常均恢复调用前的Matplotlib参数和MPLCONFIGDIR/XDG_CACHE_HOME（原未设置的键恢复为未设置）；导入仍不改这些配置。

## 源码接口与输出

| 接口 | 输入、输出与模型边界 |
| --- | --- |
| `thermal(R,T)` / `shot(I,F)` | 单边V²/Hz或A²/Hz；计算接口不认证平衡/Poisson或给定F适用于真实器件 |
| `ports(f,...)` | 七个反相电阻网络复传递；电压源系数无量纲，电流源系数Ω；finite单极点A自足，不消费待审反馈课 |
| `spectral_output(h,S)` | H为行，Sij=E[Ni Nj*]，计算HSHᴴ；匹配1..8源矩阵，严格Hermitian、非负实对角、零对角无互谱，按各源尺度归一后验证PSD |
| `rc_band(R,C,T,low,high)` | 返回fc、Hz带宽、V²方差；`high=None`显式表示模型内无穷上限，有限积分用atan2避免两个近π/2相减失精 |
| `rc_state_variance(...)` | 独立初态方差和白热源模型的V(t)；非稳态，不能称全程WSS |
| `white_flicker(W,D,lo,hi)` | 指定矩形正频带，D/f低端必须正；不代表完整器件频谱 |
| `periodogram(x,fs,kind,remove_mean,y)` | 实1D记录；PSD/复交叉谱、bin宽、窗加权均方、CG与ENBW分开返回；DC/偶数Nyquist不倍增，奇数末bin倍增 |
| `average_periodogram(...)` | 精确完整1..128个不重叠段；没有自动重叠、零填充、Welch自由度或硬件CI声明 |
| `correlated_sample(rho,n,seed)` | 两独立基础发生器形成相关端口；理论/样本协方差与已知Gaussian模型的保守95%样本均方预测区间；不是未知总体置信估计 |
| `referred(So,Hu)` / `deembed(M,I,uncorrelated)` | 零信号传递显式拒绝；未知相关或负RSS差返回状态与null，保留未辨信息 |

标量实输入转换前拒bool、complex（包括零虚部）、字符串、数组、NaN、inf。R支持10⁻³..10¹² Ω、C支持10⁻¹⁵..1 F、T支持1..2000 K、f支持0..10¹² Hz、A0支持1..10¹²、fp支持10⁻⁹..10⁹ Hz。时间0..10¹² s、初态方差0..10¹² V²；普通实工具的默认绝对范围≤10¹⁰⁰，复谱/传递绝对值≤10¹⁰⁰；这些是计算范围，不扩展物理模型有效范围。频带PSD白/闪烁系数限制0..1相应SI单位，shot电流0..1 A、F0..10。输入等效的|Hu|<10⁻¹⁰⁰视为无可用定义，计算非有限结果显式ArithmeticError。

数组接口要求4..262144个有限实样本、幅度≤10⁶ V，fs10⁻⁶..10⁹ Hz，矩形或周期Hann窗；complex/object/嵌套/bool数组在强制float前拒绝。最多8源和128平均段限制资源预算，seed为0..2³²−1整数。谱矩阵的−10⁻¹²相关特征值容差只容许数值舍入；负输出仅在相对展开项舍入范围夹0，不放行明显不合法矩阵。

`results.json`保存手算对照和三种ρ实验；`parameters.json`声明固定电路/采样/随机种子/物理条件；`assets/figure-data.json`保存真实曲线数组、窗参数及模型对象。九SVG为原生电路或Matplotlib矢量真源，360/425 PNG从这些SVG渲染。灰度和深色周边预览用于作者核对，不作为额外正文资产。来源与机器验收在库外READY，正文只保留本入口。

## 判读与独立核对

原九项CPU行为测试分别覆盖Thevenin/Norton、原三节点KCL七源×五频点、复互谱共轭与20个BBᴴ原始组合、解析RC和另一实现Simpson积分、初态方差RK4、显式DFT及奇偶Parseval、窗与平均/随机样本范围、输入等效/去嵌，以及无效输入预算。Simpson0..100fc用20000区间，RK4 t=.3s/τ=.1s用3000步；它们与解析式对照，在固定例中的误差阈值写入测试，不声称覆盖任意极端频带积分。另有两个生成成功/实际SVG渲染异常的全局状态回归，普通去均值后的Hann DC反例和正弦峰值PSD系数在原测试中复算。导入副作用、CLI缺参和重建确定性另外记录在READY作者证据，不能替代独立审阅。

理论300 K/2 kΩ PSD为3.3135576×10⁻¹⁷ V²/Hz；10 nF热RC全带方差4.141947×10⁻¹³ V²，RMS0.643579599 μV；反相电阻网络DC输出ASD159.325107 nV/√Hz，按信号u端折回17.7045599 nV/√Hz；四点谱面积5，去均值1 μV²。随机样本与理论的差别是实验输出的一部分，不为通过测试修改seed或删除起伏。

读取旧 [[电子电路/80-实践/02-弱信号前端预算/README#固定参数与复算范围]]，只把单边单位、Rs/Req、各输入端电流与独立假设带回来；旧非反相级的G=N不适用于本反相级。返回U4时不要将本热RC再添到其已合成ADC噪声预算。两个实践互补，旧源码、镜像和真实记录保留。

## 实际结果的边界

本组CPU数值、结构检查、来源实际读取和图预览分别记录。无SPICE运行、ADC/示波器记录、硬件噪声注入、仪器校准、Obsidian UI或真人学习验收。真实器件PSD、相关矩阵、温度、输出线性范围和有限带宽必须由匹配条件的器件/测量证据填入；输入短接方式改变源阻抗，不能随意称同端口测量。作者不签自己的独立验收，发布由root在独审接受后进行。
