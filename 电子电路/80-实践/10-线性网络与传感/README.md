---
type: experiment
domain: electronics
stage: 1
content_status: usable
evidence_status: partial
aliases:
  - DC线性网络CPU复算
sources:
  - "https://ocw.mit.edu/courses/6-071j-introduction-to-electronics-signals-and-measurement-spring-2006/9d19116cbabeada1c98004a4367a0ee0_nodal_mesh_methd.pdf"
prerequisites:
  - "[[电子电路/10-电路基础/10-节点与超节点从图到方程]]"
---
# 线性网络与传感：CPU复算实践

本实践服务M02-02..07六主题。network_lab.py是无文件/网络/硬件I/O的SI模型真源；build_visuals.py读取模型生成可编辑SVG/PNG和数据；导入两脚本均不生成文件。没有code-sync镜像。此实践不占用或签收L03：原L03仍是RLC能量与谐振实验。CPU结果不是SPICE、传感器测量或仪器读数。

## 端点、单位与返回值

solve接受一组元件元组：R(name,p,n,ohm)、I(name,p,n,A)、V(name,p,n,V)、G(name,p,n,cp,cn,S)。I/G箭头p→n，V正端p、负端n，V的未知支路电流p→n。G为VCCS，i=g_m[v(cp)−v(cn)]。字面字符串'0'是唯一参考，其他节点从元组建立；图面控制标签不增加导电支路。R要求正，独立源及gm允许带符号；拒绝bool、NaN、Inf、重复名称、无效元组及空网络。这里只保证正文有限教学数值，不承诺任意极端参数的浮点稳定或所有特殊拓扑可解。

load_account返回真实串联耗能内阻模型的电流、负载/内阻功率和供能效率。e=0（包括−0.0）时I_A、PL_W、PRs_W、Pdelivered_W均为0，eta返回None，表示无供能时0/0未定义；不能用化简后的电阻比填成50%。e非零时eta=RL/(Rs+RL)，负源极性只改变电流参考符号。

solve返回volts_V、currents_A、absorbed_W以及矩阵/右端/残差；吸收功率是(vp−vn)i，电压源负值表示供能。不能将混A/V方程残差向量的裸数字当有共同单位的物理误差；本测试对指定教学尺度检查逐行小值，并独立检查支路和功率。奇异网络由NumPy LinAlgError报出，不偷偷补电阻令其可解。

networks.json保留七个模型的原网表、单位电压/电流/吸收功率；bridge-data.csv给δ、开路/10k加载/一阶输出（V）。数据都是解析预测，没有实测栏被填入理论。没有硬件授权或连接动作。

## 从库根复现到库外新目录

使用现有.venv，不自动安装。作者实跑环境Python3.14.7、NumPy2.5.3、Matplotlib3.11.2、CairoSVG2.9.1。

```bash
.venv/bin/python -B -m unittest discover -s 电子电路/80-实践/10-线性网络与传感 -p 'test_network_lab.py' -v
MPLCONFIGDIR=/private/tmp/wwl-dc-reproduction-mpl .venv/bin/python -B 电子电路/80-实践/10-线性网络与传感/build_visuals.py --output /private/tmp/wwl-dc-reproduction
```

--output必填，缺参退出2而不写数据；Matplotlib配置在build函数内部加载，生成输出显式指定库外，保留发布assets。第一次字体缓存可能打印无可写系统fontconfig目录提示，作者实际生成成功；此提示不等同字体或图像验证通过，需看最后图。

七项CPU检查使用数值MNA与手算/独立2×2形式相互对照：节点/浮置源；网孔/超网孔；受控叠加与功率交叉；1 V端口测试和多负载；真实内阻功率守恒/极限与复负载可调域；桥精确/加载/四偏导/共同失配；无效输入及无返回支路/矛盾电压源。节点MNA无需输入正文解；网孔另解Ω矩阵；桥另比较解析式和中心差分。这些检查不能证明所有电路都正确。

## 可编辑视图与合同边界

共11对SVG/PNG：nodes、supernode、meshes、supermesh、controlled、port-test、power-circuit、bridge为真实端点拓扑；load-line、power-efficiency、bridge-sensitivity为数值曲线。电路原生宽360/font14，统计图4.25in/font11；图是合成模型，未提供照片/实测波形。port-test是V04缺项中的新局部受控源测试视图，不改已有accepted V04，不声明44图全覆盖。

M02六主题有图、完整数值、回代、条件/反例和理由答案。L01分压与等效源已有accepted主解释保留；本组增加含受控端口和桥加载解析复算，不宣称L01真实实验完成。L00仪器接法和L03 RLC不属于此写集合。全库检查、Obsidian客户端、SPICE、硬件、真人陌生题均未运行；内容独立签收待根审阅。来源读取与输入哈希在库外READY/source-reading报告。
