---
type: practice
domain: 物理
stage: 4
aliases:
  - E04 E05 波与端口复算
sources:
  - https://ocw.mit.edu/courses/6-013-electromagnetics-and-applications-spring-2009/pages/lecture-notes/
  - https://web.mit.edu/6.013_book/www/chapter13/13.5.html
prerequisites:
  - "[[物理/20-电磁学/05-波传播与平面界面]]"
  - "[[物理/20-电磁学/06-平板导模与功率归一化]]"
  - "[[物理/20-电磁学/07-矩形波导腔模与端口]]"
---

# 波界面与导模端口：从边界到功率

本实践复算三个连续问题：界面两边的场怎样核功率；两个介质界面怎样选出有限功率导模；导波出口或 PEC 端面怎样改变端口与腔频率。先读对应正文的对象、峰值相量和边界条件，再运行。计算是这些指定模型的回代，不能代替一般证明或实际材料、硬件验收。

## 输入、命令与代码真源

输入为 [inputs.json](inputs.json)，唯一计算与 SVG 生成真源为 [solve_waves.py](solve_waves.py)。只用 Python 标准库，无商业场求解器或新依赖。所有长度为 m、频率为 Hz、功率为 W、导电率为 S/m；`V_normalized` 是半厚度归一化频率，不是电压。`periodic_width_m` 规定沿 y 的周期单元，未建模真实条带侧缘。默认 `simpson_subintervals=4000`（每个光滑分段），二分80步；腔体电/磁场体积分用40×40网格。

在本目录运行：

```sh
python3 -B solve_waves.py --input inputs.json --output-dir results > results/stdout.json
```

本机实际运行版本为 Python 3.14.7。程序把完整输入、近似常数与结果写入 `results/values.json`，stdout 同一 JSON 被保存为 `results/stdout.json`；两者本次字节相同。现代 SI 的 μ0 不是精确定义值，本教学计算取 `4π×10⁻⁷ H/m` 近似并由 `c0=299792458 m/s` 导出 ε0；全部结果沿用此约定。

五个 SVG 由同一求解条件生成，标题/说明中的材料、频率、半厚度、模式、长度和轴单位取实际输入与计算结果。正文的 `assets/*.svg` 是 `results/*.svg` 的字节镜像，不是手工另画的公式图。重算默认输入并更新正文附件时，在本目录执行：

```sh
python3 - <<'PY'
from pathlib import Path
import shutil
for source in Path('results').glob('*.svg'):
    shutil.copyfile(source, Path('assets') / source.name)
PY
```

本组 Markdown 没有复制 Python 实现为 `code-sync` 代码块；命令块只调用真源。改参数练习应输出到新目录，保留默认正文与附件的对应关系。

## 默认模型及实际输出

| 对象及边界 | 可核输出 |
| --- | --- |
| 无损单界面：n1=1.5、n2=1、850 nm，30°从法向入射，右侧仅外向/衰减波 | TE：R=0.1057727911、T=0.8942272089；TM：R=0.00460754345、T=0.9953924566；50°比较得 R=1、T=0、κ≈4.18385046×10⁶ m⁻¹ |
| 10 GHz有限层：入/出 n=1，层 n=1.5、σ=0.03 S/m、L=10 mm，30°，切向入射峰值1 V/m；两界面切向 E/H 连续，右侧无反向入射 | TE：R=0.00776443433、T=0.9098066726、热积分 A=0.08242889308；TM：0.00319764538、0.9177505956、0.07905175901 |
| 无损对称平板：nc=1.50、ns=1.45、850 nm、Vn=1，包层无穷远衰减，y周期宽1 mm，z控制长2 mm，前向100 µW | d=352.2435482 nm；TE0：u=0.7390851332151605、w=0.673612029183215、neff=1.4728980249713144；A≈7645.3952 V/m峰值，包层功率占32.6388% |
| 同平板撤提示输入 Vn=2 | TE0：u≈1.029866529、neff≈1.48690600；TE1：u≈1.895494267、neff≈1.45516730；TE1 为奇场，不能强设中心场峰值为 A |
| 真空 PEC 矩形 a=20 mm、b=10 mm、L=60 mm，10 GHz纯 TE10 输入1 W、同模式匹配出口 | fc=7.49481145 GHz，β≈138.750325 m⁻¹、ZTE≈569.056941 Ω，E0≈3373.59435 V/m；平均储能≈0.302312222 nJ，S21≈−0.453811345−i0.891097786 |
| 同截面5 GHz的单个衰减解 | α≈117.015363 m⁻¹，60 mm振幅比≈0.000893002，平均轴向功率0；这个比值不是任意有限耦合段的 S21 |
| 同截面和60 mm长，两端封成 PEC，初始总能量1 nJ的自由 TE101 | f101≈7.90022494 GHz、Ec≈8677.20795 V/m；瞬时电/磁能量按 cos²/sin²交换，总量守恒；没有有限损耗线宽或加载端口 |

单界面与有限层的 r/t 都使用固定坐标的切向电场幅；TM 系数不直接等于换反射偏振基后的矢量幅。有限层用 εc=ε′−iσ/ω传播，但 D=ε′E、Jf=σE，导电率跳变时允许自由表面电荷；JSON 的两处 TM 表面电荷同时核 `iωρs=J1n−J2n`。TM 焦耳热包括法向 Ez，不能只积分 Ex。

平板功率对两侧全部包层积分。数值域每侧到8个衰减长度；余尾解析加回，总功率相对差约4.65×10⁻¹³，域外功率比例约3.67×10⁻⁸。中心频率差分固定实际 d，检验群速，而非固定 Vn 改频率。vg≈2.00541436×10⁸ m/s 与能量速度一致；控制段总能量≈9.97300130×10⁻¹⁶ J。

默认有限层功率余额残差最大约1.1×10⁻¹⁶，切向边界回代最大约2.9×10⁻¹⁶，TM 表面连续性归一化残差约2.9×10⁻¹⁷；平板根残差约6.7×10⁻¹⁶，矩形功率和闭腔能量相对差约2.3×10⁻¹⁶。这是本次浮点计算与解析式的吻合，未给实际介质、有限孔径或一般 PDE 的误差保证。

## 附件怎样回答问题

- `fresnel.svg`：从同一导纳式画 TE/TM 反射功率，检验 Brewster 零反射和临界角以上的 R=1。
- `finite-layer.svg`：切向场干涉起伏与净功率因热耗下降分开画，两侧边界一起求解。
- `slab-roots.svg`：同一偶奇特征式与包层半圆的交点，黑点读取 JSON 求根数据；默认 Vn=0.5/1/2，函数与 u/w 轴均无量纲。
- `slab-modes.svg`：上图为实际输入的偶/奇场，下图固定波长改变半厚的 TE 分支；不是固定器件频响。
- `rectangle-cavity.svg`：上图由截止方程画 β/α，下图用封端正弦场画 TE101；二者边界不同。
- `layer-TE-fields.csv`：201个有限层采样，含 z、切向场峰值、净功率比和焦耳热密度；JSON 同时保留 TM 总热积分。
- `slab-TE0-fields.csv`：401个横向采样，含 x、无量纲场、峰值电场、Hz虚部和 Sz；默认仅 TE0 的 CSV，其他模式信息见 JSON，SVG 按实际输入画全部 TE 导模。

## 特征根交点图的预测与复算

[[物理/20-电磁学/06-平板导模与功率归一化#把特征根看成两个函数的交点|正文交点图]] 让你先预测 Vn=0.5和2的模式数，再按允许支区间数交点。`inputs.json` 的 `root_diagram_comparison_V=0.5`、`V_normalized=1`、`transfer_V_normalized=2` 决定默认三个面板，重复条件去重；把比较输入0.5改0.75，会同步改变面板、半厚、曲线和根标签。默认0.5只含 TE0，2含 TE0/TE1；对应根与原式残差在 `results/values.json` 的 `slab_root_intersections`，不是仅由图片像素估计。

运行本页默认命令即可生成 `results/slab-roots.svg`，按上面的附件同步命令更新正文镜像。每一面板蓝/橙曲线只画本支允许区间，极点不连接，上超纵轴的部分由图域裁切；绿色包层条件没有被替换成直线。图只检查无损非磁对称平板 TE 条件，不包含 TM 或真实材料损耗。

## 参数迁移与可预期反例

在本目录执行下面脚本会为每个练习复制默认输入，调用同一真源，写到本地 `scratch-wave-exercises/`；它不更新默认附件。这些条件已由作者在隔离临时目录实际运行过。

```sh
python3 - <<'PY'
import copy, json, math, subprocess, sys
from pathlib import Path
base=json.loads(Path('inputs.json').read_text())
cases=[('slab-v05','slab',{'V_normalized':0.5}),
       ('slab-v2','slab',{'V_normalized':2.0}),
       ('layer-lossless','layer',{'sigma_layer_S_per_m':0.0}),
       ('layer-halfwave','layer',{'sigma_layer_S_per_m':0.0,
          'thickness_m':math.pi/(2*math.pi*base['layer']['frequency_Hz']/299792458 *
              math.sqrt(base['layer']['n_layer_real']**2-
                  (base['layer']['n_incident']*math.sin(math.radians(base['layer']['angle_deg'])))**2))}),
       ('rectangle-length120','rectangle',{'length_m':0.12}),
       ('rectangle-f8GHz','rectangle',{'frequency_Hz':8e9})]
for name,section,changes in cases:
    p=copy.deepcopy(base);p[section].update(changes)
    directory=Path('scratch-wave-exercises')/name
    directory.mkdir(parents=True,exist_ok=True)
    input_file=directory/'inputs.json';input_file.write_text(json.dumps(p,indent=2)+'\n')
    with (directory/'stdout.json').open('w') as stream:
        subprocess.run([sys.executable,'-B','solve_waves.py','--input',str(input_file),
                        '--output-dir',str(directory/'results')],stdout=stream,check=True)
PY
```

先作预测再打开输出：

| 变条件 | 答案与边界 |
| --- | --- |
| Vn=0.5 | 仅偶 TE0，u≈0.4501836113、w≈0.2175654295、neff≈1.4595983977，包层功率约66.58% |
| Vn=2 | 出现两支 TE0/TE1，半厚加倍；新奇模更松散，包层约54.84%，不能据总体 Vn增大就断言每一模都更集中 |
| σ=0、L仍10 mm | TE的 R≈0.00806426936，TM的 R≈0.00330745065；各自 T=1−R、热积分0，层无损不保证无反射 |
| 无损层 qL=π | L≈10.5993 mm，两个界面的总反射趋0；单个界面仍有失配 |
| 矩形 L=120 mm | fc和ZTE不变；总行波储能加倍，S21≈−0.588110526+i0.808780569，闭腔f101≈7.59819304 GHz |
| 矩形 f=8 GHz | 仍传播但近截止，E0≈4641.57451 V/m、vg≈1.04845698×10⁸ m/s、总储能每米≈9.53782581 nJ/m |

最后把矩形 a,b缩半，仍10 GHz：TE10截止变14.9896 GHz，程序应以 `The reference TE10 port must be above cutoff` 拒绝按1 W传播模求解。若希望算有限低于截止段的传输，应新增两端实际散射边界，不能绕过拒绝把虚 β当实功率波。平板恰好 Vn=mπ/2 的新支 w=0，程序排除其有限功率归一化；临界入射 q=0则用极限，不直接代入1/q。特别地，将 `interface.sample_angle_deg` 改成 `math.degrees(math.asin(n_transmitted/n_incident))` 时，程序用平方波数判别式的相对容差拒绝计算；浮点残留不被当作可求巨大 TM 导纳的传播波。其 ±10⁻⁷度比较远离此容差，较小角给实正 q和正 T，较大角给负虚 q、R=1和T=0。

本程序服务这些正实材料参数及选定平面/周期/PEC边界；参数若引入新的截止、非传播外侧、极薄/极厚损耗层或近奇异点，先核数值条件与物理模型，不能把成功退出当作任意输入的认证。真实频散、磁介质或非线性材料需改本构后重建求解。

## 同一卡的 TM 平板扩展

继续 [[物理/20-电磁学/09-TM平板导模与界面权重|TM 主解释]] 和 [[物理/80-实践/03-波界面与导模端口/tm/README|实践03 TM扩展]]。扩展保持相同材料、850 nm、半厚、周期宽和100 µW，独立真源 `tm/solve_tm.py` 与 `tm/inputs.json` 只写 `tm/results/`，图位于 `tm/assets/`。先预测 TM 的介电加权匹配、法向电场跳变及包层功率，再复算根、完整场、储能和固定厚度群速；TE 列只是同一卡的参考计算，原五组结果与命令仍对应原实验。

## 返回正文与证据边界

返回 [[物理/20-电磁学/05-波传播与平面界面|平面波与界面]]、[[物理/20-电磁学/06-平板导模与功率归一化|平板根与归一化]]、[[物理/20-电磁学/07-矩形波导腔模与端口|矩形模式及端口]]。把具体模式带到 [[电子电路/64-光电探测与光子互连/01-发光探测与光波导#波导保留的是模式及边界条件|电子光波导]] 时保留耦合/传播损耗假设；带到 [[电子电路/46-电磁射频与高速/03-阻抗匹配与S参数#实参考功率波与S矩阵|电子实参考功率波]] 时保留 RMS、参考面与端口模式。

本机已运行固定输入、变条件与负例，SVG已栅格化目视检查。独立理论/代码审阅由接收环节开展；未运行商业求解器、硬件、VNA或实际光器件，也未由此核验Obsidian点击、同步、真人理解或完整课程。#247仍保持开放，剩余一般材料频散、非对称/矢量复杂导模、实际馈电加载、多模/损耗/辐射边界需要后续正文和证据。

## 从 PEC 腔接有限壁损扩展

[[物理/80-实践/03-波界面与导模端口/cavity-loss/README|六壁损耗与自由衰减]] 复用本页矩形腔几何、1 nJ及峰值相量，在独立源码/输入/结果下增加局部正常导体壁阻抗、六面热积分与Q。先读 [[物理/20-电磁学/10-矩形腔壁损与有限Q|壁损主解释]] 预测电导和尺寸变化，再核三图。原 `solve_waves.py` 与PEC/界面/平板结果未由这一扩展重跑或改写；壁损不是低于截止场幅比。
