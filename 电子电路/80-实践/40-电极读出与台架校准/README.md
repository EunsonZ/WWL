---
stage: 3
aliases: []
sources:
  - https://www.gamry.com/assets/White-Papers/Gamry-Common-Equivalent-Circuit-Models.pdf
  - https://www.analog.com/media/en/technical-documentation/technical-articles/ecg-eeg-emg_final.pdf
  - https://webstore.iec.ch/en/publication/67497
prerequisites:
  - "[[电子电路/68-生物电子与电化学接口/01-生物电与电极接口#从加载到共模误差]]"
  - "[[电子电路/68-生物电子与电化学接口/02-安全隔离与测量链#范围预算：偏置先于增益]]"
  - "[[电子电路/68-生物电子与电化学接口/03-低噪声采集与伪迹处理#每个噪声源必须有端口]]"
content_status: usable
evidence_status: partial
---
# 电极读出与台架校准

## 复算对象与边界

本实验使用合成双端口源，计算简化 Randles、输入加载造成的共模转换、独立噪声、ADC范围与状态滤波。所有参数是教学参数。没有人体连接指引、患者数据、真实器件规格保证或医疗合规结论。IEC60601-1 Ed3.2只读官方目录，规范全文未取得；目录不支持泄漏限值或测试条款。

`models.py` 是源码真源，没有 code-sync 镜像。接口均用 SI；阻抗/传递返回复数，输入标量拒绝 complex、bool、字符串、嵌套及非有限值。有限域是实验实现合同，不是物理定义域：

|接口|对象、单位与输入范围|返回、用途与限制|
|---|---|---|
|randles|f 0..100k Hz，Rs100..100k Ω，Rct1k..10M Ω，Cdl1n..100μ F|Z Ω；固定局部被动界面，不含半电池DC/扩散/运动|
|readout|两组三参数；Rin100k..1G Ω，Cin1p..10n F；Ad1..1000，名义CMRR20..140 dB|Hd,Hc,T1,T2 V/V与两Zparallel Ω；Ac/Ad正实、固定的行为模型|
|noise_psd|上列域；T250..350 K，en0..1μ V/√Hz，每路in0..1n A/√Hz|各输出单边PSD V²/Hz；接口平衡热噪声、Rin热电流、独立放大器源，没有非平衡/相关/运动噪声|
|integrate_noise|.1≤fL≤10k，.2≤fH≤100k Hz且fH>fL；2..8192偶数段|指定矩形带输出 RMS V，有限Simpson；N/2N比较为估计，无通用误差证明|
|barrier_current|f0..1M Hz，Cp.1p..10n F，Vrms0..10 V|理想正弦位移电流 RMS A；不是安全允许值|
|adc_budget|span.5..10 V，8..24位，G1..1000，vp0...1 V，e0±.5 V，ap0...5 V|峰值/余量V、输入LSB V/码及条件量化RMS V；对称端口，不覆盖实际ADC非理想|
|rc_hold|fs100..100k Hz，.1≤fc≤fs/4 Hz；1..10000个平坦样本与初值均±10 V|分段恒定驱动的区间终点状态 V；一次序列保留状态，没有每片段重置|
|tone|4..10000平坦样本±10 V；.1≤f≤fs/2−.01 Hz|2/N有限复投影V峰值；实验采用整数非DC、非Nyquist周期，不自动是任意频谱估计|

接口注释逐项写变量、返回与条件。选择工程教学范围防止把任意浮点极值当普适求解器。没有迭代收敛循环；最大积分、序列与图采样次数固定有限。无效输入抛 ValueError，不静默产生假解。

## 运行和独立核对

用已有Python环境从本目录运行，不安装依赖：

```bash
python -B -m unittest discover -s . -v
python -B generate.py --output /private/tmp/f05-new-run
```

`--output` 必填，只接受不存在且在主库与候选之外的新目录。模型和生成器导入只定义对象，不解析argv、不导入Matplotlib/NumPy、不写文件。生成时才加载Matplotlib/CairoSVG；使用Figure与局部rc_context，不用pyplot或改全局绘图设置。caller可将MPLCONFIGDIR设在自己的库外目录。

12项测试分别核：原导纳实虚部/半圆、两节点矩阵独立消元、完全匹配CMRR、内部电阻源对热谱、独立源节点注入、中点法对Simpson、时域导数RMS对隔离电流、均匀误差原积分和范围、原ODE阶跃及状态接续、整数周期有限投影与950→50 Hz混叠、删去合法50 Hz内容的反例、无效域。有限样本与方程测试验证教学模型，不能证明真实生物界面或医学安全。

## 图和数据

- `interface.svg`：二维材料顺序和两端Rs+(Rct||Cdl)，对象与局部斜率明确，无制造尺寸。
- `readout.svg`：有返回的两合成源、两Ze和两个加载支路，同一0参考；供电读出仅行为框。
- `isolation.svg`：域隔离概念与独立闭合Cp正弦回路；显式不是人体接线图。
- `impedance-cmrr.svg`：同一界面半圆与失配后有效/名义CMRR比较，频轴与单位保留。
- `noise-calibration.svg`：各输出ASD除固定Ad的显示标尺和连续RC已知频率校准，不冒称全链实测。
- `synthetic-artifact.svg`：10 Hz差分、50 Hz共模及输出1.2 V偏置阶跃，±1 V限幅与限幅后RC三列。

各SVG可编辑，并配360/425像素PNG。`result.json`保存参数来源性质、复算值、两积分分辨率与削顶样本数；`synthetic.json`保存fs、时间、三列原始数据。RC返回区间终点而源正弦数组用t=n/fs，这一采样/保持约定见第三章，不能把RC当连续正弦稳态响应直接比较。

V43本组仅贡献“隔离/保护/信号链概念”的F05部分；F06阵列电流求和与非理想没有由本组证明，整行维持partial。图不是人体连接指南，保护仅概念，没有保护元件选型与故障合格保证。无需要3D的新空间量，二维剖面能直接解释材料/电荷与端口，故没有装饰3D。

本轮证据分层：CPU模型、源码测试、逐byte再生成与作者静态窄屏/灰度/反色检查分别记录在库外READY。来源记录实际正文/目录范围；SPICE、电化学台架、人体、安全规范条款、认证、客户端、真人阅读全部not_run。作者不自签独立审阅，主库发布由root处理。
