---
type: practice
domain: 物理
stage: 4
aliases:
  - 实践03 TM平板扩展
sources:
  - https://ocw.mit.edu/courses/6-013-electromagnetics-and-applications-fall-2005/b779e35088c0fac1b35806ebdba23c76_lec15.pdf
  - https://web.mit.edu/6.013_book/www/chapter12/12.6.html
prerequisites:
  - "[[物理/20-电磁学/06-平板导模与功率归一化]]"
  - "[[物理/20-电磁学/09-TM平板导模与界面权重]]"
---

# 实践03扩展：TM平板导模与同功率比较

先读 [[物理/20-电磁学/09-TM平板导模与界面权重|TM 主解释]]，预测同厚 TM0 的传播常数、包层衰减和界面电场，再打开本页数值。本扩展复用 [[物理/80-实践/03-波界面与导模端口/README|实践03]] 的平板材料、峰值相量与有限控制段，单独计算 TM 和所需 TE 参考；所有新输出在 `tm/` 内。计算不调用原 `solve_waves.py`，没有重新运行原 Fresnel、损耗层或矩形腔流程。

## 固定输入与规范源码

[inputs.json](inputs.json) 保持 $n_c=1.50,n_s=1.45,\lambda_0=850$ nm、$V=1$、周期宽1 mm、控制长2 mm、每模前向100 µW；比较条件为 $V=0.5,2$。材料无损、各向同性、非磁、非色散；宽度是周期单元，没有条带侧缘。$V$ 按半厚 $d$ 定义，图中的扫 $V$ 是固定材料与波长改变半厚。

唯一计算和 SVG 真源是 [solve_tm.py](solve_tm.py)，只需 Python 标准库。采用峰值 $e^{i\omega t-i\beta z}$，从 $H_y$ 恢复 $E_x=\beta H_y/(\omega\epsilon)$、$E_z=-iH_y'/(\omega\epsilon)$。根以 $H_y$ 奇偶性编号，用不跨极点的相位残差二分80步。功率/电能/磁能分别对芯层、两侧包层作 Simpson 积分，每光滑段2000个子区间；每侧积分到8个振幅衰减长度，剩余两侧尾项用解析指数积分加回。

现代 SI 的 $\mu_0$ 不是精确定义常量；本计算与06一致，取 $\mu_0\approx4\pi10^{-7}$ H/m、$c_0=299792458$ m/s，再导出 $\epsilon_0=1/(\mu_0c_0^2)$。材料值是教学参数，没有对应真实材料牌号。

在本 `tm` 目录执行下列命令，默认输出保持本页固定输入对应关系：

```sh
python3 -I -B solve_tm.py --input inputs.json --output-dir results > results/stdout.json
```

`results/values.json` 保存完整输入、常数、Python版本、相量约定和 `cases`；stdout 同一 JSON。每个 `cases` 条件包含 `TM` 和 `TE` 各支，场样本只保存默认基模的 [TM0-fields.csv](results/TM0-fields.csv) 与 [TE0-fields.csv](results/TE0-fields.csv)。CSV 含米坐标、core/clad 区域、电场 V/m、磁场 A/m、能流 W/m²、能量密度 J/m³；接口处分别保存芯层/包层同坐标两行，使 $E_x$ 和 $S_z$ 的跳变可见。

三图的 [results](results/values.json) 与正文 `assets` 为字节镜像。确需以新的默认结果更新正文图时，先核输入与JSON，再执行：

```sh
python3 - <<'PY'
from pathlib import Path
import shutil
for source in Path('results').glob('tm-*.svg'):
    shutil.copyfile(source, Path('assets') / source.name)
PY
```

本页没有复制实现成 `code-sync` 镜像；上面的命令只调用/同步规范源码结果。改参数时使用新输入文件和新的输出目录，避免覆盖本页参考产物。

## 同功率下实际求到了什么

| $V=1$，同一 $d=352.2435482$ nm | TM0 | 同一卡 TE0参考 |
| --- | --- | --- |
| $u,w$ | 0.7525691663，0.6585132117 | 0.7390851332，0.6736120292 |
| $n_\mathrm{eff}$ | 1.4718905694 | 1.4728980250 |
| 标量系数与单位 | $A_H=30.1836871$ A/m | $A_E=7645.3952163$ V/m |
| 两包层功率比例 | 0.3423985007 | 0.3263879708 |
| 2 mm控制段总能量（J） | $9.96912382\times10^{-16}$ | $9.97300130\times10^{-16}$ |
| 固定厚度群速（m/s） | $2.00619436\times10^8$ | $2.00541436\times10^8$ |

两个标量系数属于不同场量，不能直接以数值大小比较。用每模100 µW及同截面下的 $S_z$、包层功率、总储能作比较。TE 参考只复算本组平板，旧实践输出文件仍是原结果；不得把这个参考列称为重跑旧实践全流程。

默认 TM0：原特征式残差约 $10^{-15}$ 量级；两界面 $H_y$ 跳跃为0、$E_z$ 跳跃绝对值约 $5.68\times10^{-13}$ V/m、$D_x$ 跳跃为0。积分加精确余尾得到100 µW，相对差约 $7.80\times10^{-12}$；未补余尾前漏掉约 $3.85\times10^{-8}$ 的功率比例。全截面电/磁能相对差约 $10^{-16}$；固定 $d$ 的频率差分群速与能量速度相对差约 $3\times10^{-12}$。残差是浮点模型自查，没有认证材料精度或一般数值误差界。

`interface_checks` 逐界面保存两侧场及切向 $E_y,E_z,H_y,H_z$ 和法向 $D_x$ 残差；本极化中为零的分量也明确保存。`power_quadrature_with_tail_W` 核功率，`UE/UH_quadrature_relative_error` 核储能；它们不与逐点 $E/H$ 幅度比混为一件事。`energy_per_z_length_J_per_m` 已乘周期宽，`control_energy_J` 再乘有限长度。

## 三图先预测，再读取数字

- [tm-roots.svg](assets/tm-roots.svg)：在 $V=1,2$ 的允许支内画 $u\tan u,-u\cot u$ 与 $r_\epsilon\sqrt{V^2-u^2}$；轴无量纲，按 $H_y$ 奇偶性标注。预测第一奇支是否已经过截止，再数真实根。
- [tm-fields.svg](assets/tm-fields.svg)：同一卡、同功率的 $H_y$、TM $E_x$ 与 TE $E_y$、TM $\operatorname{Im}E_z$、TE/TM $S_z$；分别标 A/m、V/m、W/m²及 x（µm），芯层在两界面线之间。先预测哪些分量连续，哪些跳变。
- [tm-confinement.svg](assets/tm-confinement.svg)：固定波长改变厚度，各支 $n_\mathrm{eff}$ 和两侧包层功率比例。每支严格从 $V>m\pi/2$ 开始；新支出现并不意味着该新模已经集中在芯层。

图域裁切和积分截断是两个选择：场图只展示界面附近，归一化仍使用全部无限包层。曲线从同一方程、输入和根生成，图上的黑点不是人工调整到交点。

## 改厚度和截止负例

默认 JSON 已包含 $V=0.5,2$ 两组条件，可先用正文迁移题预测，再核 `cases`。如果要自行改输入，在本目录执行以下脚本；它只生成新练习目录，不更新默认图。

```sh
python3 - <<'PY'
import json, subprocess, sys
from pathlib import Path
p=json.loads(Path('inputs.json').read_text())
p['V_normalized']=2.0
directory=Path('scratch-tm-v2')
directory.mkdir(exist_ok=True)
input_file=directory/'inputs.json'
input_file.write_text(json.dumps(p,indent=2)+'\n')
subprocess.run([sys.executable,'-I','-B','solve_tm.py','--input',str(input_file),
                '--output-dir',str(directory/'results')],check=True)
PY
```

保持材料与波长，$V=2$ 给 TM0/TM1 的 $u\approx1.0486635149,1.9033368110$，包层功率约9.96475%、57.25402%；$V=0.5$ 只有 TM0，$u\approx0.4547777512$，包层约68.99615%。各支100 µW是分别归一；这些数值没有宣称同时激励全部模式时仍只有100 µW。

要观察严格截止拒绝，可复制输入并将 `V_normalized` 写为 `math.pi/2`，然后指定 `--require-mode 1`。程序应报 `At/below this branch cutoff: no normalizable guided mode`，在创建输出前退出；不加此要求时，它只求严格存在的基模。$V=\pi/2+0.01$ 才会有第一奇支，它的包层比例接近1。没有芯包折射率差、非正功率/长度、NaN、或奇数 Simpson 子区间也应拒绝。

本程序的数值输入范围为 $0.05\le V\le8$、Simpson偶数20–20000、二分40–100步、尾长1–20；这些是有界教学复算范围，物理基模在更小正 $V$ 的存在性由正文推导，不由这个输入限制否定。逼近截止到浮点根无法区别 $w=0$ 时也拒绝归一。输入不同的实际材料/磁响应/非对称包层/侧缘/损耗，必须重建方程和界面，而非突破数值拒绝继续套公式。

## 返回接口与验证范围

返回 [[物理/20-电磁学/09-TM平板导模与界面权重|TM 主解释]]，带去全场、双界面残差、单位和包层比例；到 [[物理/20-电磁学/07-矩形波导腔模与端口#从场模态到电子的功率波，保留归一化合同|模态端口坐标]] 时带去模式、功率和参考面。08 是静电电容矩阵，不是动态50 Ω端口说明。

作者在隔离目录完成一次60 s上限预跑，标准库单进程计算实际耗时不足1 s；随后核默认、厚度变化、截止和非法输入。此处记录指定模型的作者自查，独立审阅与独立 runner 另行开展。未运行原实践的全流程、商业全波求解、真实器件、VNA、材料数据、Obsidian显示/同步或真人撤提示验收；一个 TM 代表解不关闭完整课程 #247。
