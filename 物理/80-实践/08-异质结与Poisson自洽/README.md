---
stage: 0
aliases:
  - 异质结平衡自洽复算
prerequisites:
  - "[[物理/50-半导体物理/11-异质结带阶界面电荷与自洽边界]]"
sources:
  - "https://www.iue.tuwien.ac.at/phd/palankovski/node30.html"
  - "https://www.iue.tuwien.ac.at/phd/palankovski/node38.html"
  - "https://physics.nist.gov/cuu/Constants/Table/allascii.txt"
---

# 异质结与 Poisson 自洽：同一参数卡的复算

## 同一参数卡的运行与输出

先在 [[物理/50-半导体物理/11-异质结带阶界面电荷与自洽边界#先用耗尽近似读懂片电荷怎样重分配宽度|耗尽例]] 预测正片电荷怎样改变两侧宽度、界面势与位移跳跃，再与 [[物理/50-半导体物理/11-异质结带阶界面电荷与自洽边界#把移动载流子放回电荷，实际闭合一次自洽|平衡闭环]] 对照。

本目录只需 Python 3 标准库；单进程、单线程，最多 5000 格/侧、80 次 Newton、24 次回溯，不启动外部服务。常规运行远低于 60 秒预跑预算，不含专业工具、硬件或依赖安装。

```sh
python3 -B heterojunction_lab.py
python3 -B build_figures.py
```

[heterojunction_lab.py](heterojunction_lab.py) 是规范方程与求解真源，[inputs.json](inputs.json) 是同一 A/B 教学参数卡。[build_figures.py](build_figures.py) 消费实际 [results.json](results/results.json) 与 CSV，生成 [空间图](results/space.svg)、[电荷与条件变化图](results/charge-and-changes.svg)。源码不作 Markdown 代码镜像。

每次运行都重新求解三种片电荷、三级网格、B 掺杂加倍、非中性右静电边界变化、精确本征常势极限、半长延伸和失败例。输出只在 `--out` 目录生成；修改输入可另指定结果目录，保留原案例：

```sh
python3 -B heterojunction_lab.py --input inputs.json --out /private/tmp/heterojunction-rerun
python3 -B build_figures.py --results /private/tmp/heterojunction-rerun
```

参数变更要先复制并修改一份 `inputs.json`，将 `--input` 改为该路径；只修改输出名不会改变材料。`half_cells` 必须按整数倍递增，因为运行报告比较相同物理节点；本卡固定 120/240/480，即 $h=5,2.5,1.25$ nm。

## 三种片电荷、两个近似与一个共同账本

零/正/负片电荷的 CSV 分别为 [zero-profile.csv](results/zero-profile.csv)、[positive-profile.csv](results/positive-profile.csv)、[negative-profile.csv](results/negative-profile.csv)。字段写明 SI 单位；能量采用 eV。每个界面保留两行 $x=0$，材料标 A/B：$\phi$ 相同，但带边与统计不同。不可按 $x$ 去重后抹掉材料接口。

[mid-edge 数据](results/positive-edges.csv) 存 $D,E$。界面图的竖跳来自 JSON 中的重构单侧 $D(0^-),D(0^+)$；两相邻中点通量之差还含半控制体积体电荷，不能直接拿它与 $\sigma_s$ 比。片电荷是 C/m²，不作为有限高度的体 $\rho$ 矩形画进 C/m³ 图。

![[物理/80-实践/08-异质结与Poisson自洽/results/space.svg]]

JSON 对每种片电荷分别记录耗尽分段解、连续半无限 PB first-integral 解、三级有限 PB 解及差异，未把三者混为一个“解析精确答案”。耗尽近似保留固定杂质矩形而忽略移动电荷；有限 PB 每轮由统计重建电荷。正片电荷 $\phi_0$ 分别约 0.26424918、0.25223715、0.25223631 V，量级相近不代表模型相同。

## 求解与检查接口

`neutral_phi` 只为外端求中性势，用正根避免 p 型区二次式相消。`solve` 保持 Dirichlet、共同 $E_F$，联立全部内部势节点；界面控制体积按左右材料分半。Newton Jacobian 含 $\partial\rho/\partial\phi$，每次试步重新计算 $n,p,\rho$；并非固定 $\rho$ 的重复线性求解。

公开数值域：温度、长度、带隙、$N_c,N_v,\epsilon_r$ 正有限，掺杂非负有限，偏移、$E_F$、片电荷与边界位移有限；网格整数 4–5000 格/侧；载流子指数 $|\eta|\le100$。出域和迭代/回溯预算耗尽明确失败，不钳制指数来假装收敛。该接口允许的许多值会破坏 MB、完全电离或经典连续介质模型，物理条件须另验。常规 `run` 的额外耗尽/半无限比较只支持本 p-A/n-B、单调势与所写片电荷分支；变为积累或宽度超域时它报错，不能将比较器出域解释为一般 PB 无解。

实际输出保留每轮残差、阻尼及步长；三片电荷均 4 轮，细网格缩放残差小于 $2.4\times10^{-14}$。停止门限 $10^{-10}$ 按正文的 $S$ 缩放，`last_step_V` 是最后接受的更新，不单独充当精度证明。五个教学解均通过 $\max(n/N_c,p/N_v)\le e^{-3}$ 检查；300 K 完全电离与其他材料近似仍是输入。

作者自查还实际完成以下相互区分的核对：

- **界面与全局 Gauss：** 重构单侧 $D$ 后核片电荷；全区积分包含外端半控制体积，核 $D_R-D_L-Q_{\rm volume}/A-\sigma_s$。三片电荷细网格整体差小于 $2.3\times10^{-15}$ C/m²；掺杂加倍约 $2.57\times10^{-13}$ C/m²。
- **网格：** 5→2.5→1.25 nm 的同节点势差下降；最后最大差 2.84–3.61 μV，支持当前二阶趋势。小残差不替代网格误差。
- **连续极限：** `semi_infinite_oracle` 自主积分 Poisson 得 $D^2=2\epsilon\Delta F$，一维二分界面势；未调用离散 Newton 答案。与有限细网格界面差最大约 0.836 μV。半长 600→900 nm、固定间距重解，正片电荷界面势变化 $4.53\times10^{-11}$ V；分别记录有限域与离散影响。
- **精确与失效例：** 相同本征材料、零片电荷、同中性 Dirichlet 给精确常势；零迭代预算、零温、非整数网格均明确失败。另实际重解右端增加 0.3 V 的压力例，残差很小但 $\max(n/N_c,p/N_v)=109.6$，判 MB 失效，不能作为物理预测。

这些是作者检查和当前本机运行，不能代替未参与编写者的独立论证/源码核查及独立 runner。

## 改掺杂、边界与更广模型的接口

[doping-profile.csv](results/doping-profile.csv) 改 B 掺杂并重新计算中性外端；[boundary-profile.csv](results/boundary-profile.csv) 保持共同 $E_F$，改右静电势 0.05 V 后产生非中性端部积累。两者都重新求 Poisson 与占据，均记录守恒；不能继续使用旧势曲线并只调整颜色。

![[物理/80-实践/08-异质结与Poisson自洽/results/charge-and-changes.svg]]

右端非中性静电约束是合成平衡边值输入，不是两 Ohmic 储库间的外加偏置：后者需要两准 Fermi、连续方程与经过选择的异质界面通量。理想平衡不计算净输运电流，不能通过检查普通同材料 SG 式将材料带阶遗漏后称已核异质电流。

升级时分别给新输入与验证问题：FD/杂质电离消费 [[物理/50-半导体物理/03-温度占据电中性与杂质电离#退简并的反例与模型本身的边界|统计主解释]]；界面态需能级/DOS、占据电荷与（非平衡时）俘获动力学；偶极需另给势差/带偏移的分工；量子限制需态/波函数与 Poisson 耦合；完整偏置 DD 消费 [[电子电路/60-TCAD与器件场模型/01-漂移扩散Poisson与接触网格#指数拟合通量保留平衡抵消|运输离散]] 并补异质通量；真实工艺还需材料来源、几何、接触与独立观测。当前未实现这些升级，没有真实材料/工艺测量、商业 TCAD、Obsidian 客户端或真人学习验收。

界面与带阶模型依据 [TU Wien 半导体边界](https://www.iue.tuwien.ac.at/phd/palankovski/node30.html)、[材料带偏移](https://www.iue.tuwien.ac.at/phd/palankovski/node38.html)；常数采用 [NIST CODATA 2022](https://physics.nist.gov/cuu/Constants/Table/allascii.txt)。有限卡、独立 first-integral 推导及运行数量均来自本目录方程与数据，不是来源文献中的实测案例。
