---
type: experiment
domain: electronics
stage: 1
content_status: usable
evidence_status: partial
aliases:
  - 交流网络与传函解析复算
sources:
  - "https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/66adf4d4611a57b949efa1b00a842a46_6002_l17.pdf"
prerequisites:
  - "[[电子电路/12-交流与变换域/02-阻抗导纳源与负载]]"
---
# 交流网络与传函解析复算

本实验把理想RC、串并联RLC和固定因果传函的手算变成可重复的数值检查。ac_lab.py是模型真源；test_ac_lab.py用KCL/KVL、周期积分、ODE残差与Laplace积分检验不同表达式是否相容；plot_ac_lab.py生成可编辑SVG以及PNG备览。没有任意电路求解器、SPICE或器件测量。

## 单位、拓扑与数据

电路默认R=1 kΩ、C=1 μF、RMS源电压1 V、角频率1000 rad/s。有载例显式Rs=200 Ω、RL=10 kΩ。RLC为L=10 mH、C=1 μF，串联固定1 V RMS或并联固定5 mA RMS。assets/results.json保存SI参数、KCL用相量、半功率点和四份显式网表；assets/waveforms.csv列time_s、vs、vc、i、pnetwork、pR、pC。

逆变换与RHP零点另用q=t/T0、p=sT0、T0=1 s。复数数据JSON以real/imag二元组保存，不能把p直接当物理Hz。函数要求正有限物理参数，不接受bool、NaN、负电阻等；Rs可零；rl=None表示开路。本组固定案例不接受随意的任意阶数多项式。

## 复现命令

在主库根使用现有虚拟环境，不安装依赖。将候选路径改为实际路径：

```bash
.venv/bin/python -B -m unittest discover -s /private/tmp/wwl-ee-revision-20261005-195537/impedance1/电子电路/80-实践/05-交流网络与传函 -p 'test_ac_lab.py' -v
MPLCONFIGDIR=/private/tmp/wwl-ee-impedance-mpl .venv/bin/python -B /private/tmp/wwl-ee-revision-20261005-195537/impedance1/电子电路/80-实践/05-交流网络与传函/plot_ac_lab.py --output /private/tmp/wwl-ee-revision-20261005-195537/impedance1/电子电路/80-实践/05-交流网络与传函/assets
```

Matplotlib配置在build函数内部读取局部matplotlibrc；导入不绘图，输出目录必须显式提供。SVG保留text和实际连接几何，Matplotlib PNG与SVG由同一figure派生，手写电路PNG由其SVG派生。字体原宽与360宽检查均可复核。

## 视图的验收边界

V10提供理想/有载RC拓扑、复电压/时间波形、瞬时功率；V14提供RC的t/s/jω与五类逆变换中的四幅，未提供z域；V15提供一阶极零因子/重极点、RHP零点的极点图/精确Bode/渐近线/阶跃、隐藏内部模态；V16提供串并联谐振拓扑与不同源负载/输出扫频，尚无三阻尼能量相平面。本目录没有code-sync镜像，源码只保留此一份。

七项CPU解析测试通过不代表语义独立签收、Obsidian真实显示、硬件安全或真人迁移题已通过。完整来源阅读范围与候选版本在库外READY.md和source-reading.md。
