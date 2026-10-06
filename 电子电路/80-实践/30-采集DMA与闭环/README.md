---
title: 采集DMA与闭环CPU实践
stage: 0
aliases: []
sources: []
prerequisites:
  - "[[电子电路/44-嵌入式采集与控制/01-电压编码校准与数据契约#编码区间先于重建电压]]"
  - "[[电子电路/44-嵌入式采集与控制/03-定时中断DMA与实时预算#从块周期推出最坏预算]]"
---

# 采集DMA与闭环CPU实践

## 运行与输出

从库根执行，已有 `.venv` 提供 NumPy、Matplotlib、CairoSVG。没有安装动作或 SciPy 要求。输出必须显式指定库外新目录；下例 shell 工作目录为 WWL 根，实践源是此目录中的唯一代码真源，不设另一份镜像。

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/30-采集DMA与闭环' -v
.venv/bin/python -B '电子电路/80-实践/30-采集DMA与闭环/generate.py' --output /private/tmp/wwl-embedded-example-new
```

候选尚未发布时，将上述两处实践相对路径换成候选的实际绝对路径。`generate.py` 的 `main(argv=None)` 必填 `--output`；缺参退出2且无文件生成。`generate(output)` 拒绝主库内路径，允许重复写所指定的实验输出目录，因此示例建议新目录。导入 models/generate 不读 argv、不加载 NumPy/绘图库、不创建缓存；真正生成时依赖才加载，临时绘图缓存留在输出临时子目录并删除，环境与 rcParams 成功或异常后均恢复。

`models.py` 是数值模型唯一源码；`test_models.py` 使用独立有理数整数历史、OLS 闭式和原 ODE 的 RK4 核对，`test_generate.py` 检查导入/缺参及成功/异常全局状态。`generate.py` 输出9幅可编辑SVG、各360/425宽PNG、parameters/results JSON和两组事件CSV及完整pipeline.csv。图文字、线条、节点与数学曲线可从源码重生，SVG不依赖截图填入电路。

## 参数与证据边界

pipeline.csv逐点保留实际模拟模型输入、ADC码、校准电压、块完成时刻、FIR有效位、IIR count和输出电压偏差。输出只表示CPU结果，不把CPU结束时刻冒充DAC施加时刻。output_reference_V=b+a·2048=1.6487904V，是此校准模型的整数居中参考；它与名义2048码bin中点和控制工作点1.65V不同。01-chain原码明确分支进入校准[V]和居中滤波[count]。

ADC floor-bin 规则固定12 bit、3.3V，输入有限实数0..3.3V；bool、complex（包括虚部零）、NaN/Inf、越界都拒绝。满量程精确端点有独立标记。实硬件 INL/DNL、建立、噪声不由这个函数证明。

时间模型≤256块，每块1..4096样本，总≤262144；period_ns整数1..1e9，IRQ delay整数0..1e9，CPU WCET整数1..1e9。第一块ready=B Ts，复用=(k+2)B Ts是教学假设。双槽/串行CPU模型用finish≤reuse判有效，等号先释放再复用；真实硬件应留正裕量。`events-overrun.csv`中每块discard是模型失败状态，不可随后当有效滤波输入。

`OwnedRing`容量1..16，每块1..4096合法码，token=(epoch,generation,slot)；忙槽拒绝，take/release在任何tuple相等比较和状态改变之前校验三个字段都是非bool整数：epoch在0..当前epoch，generation在1..当前generation，slot在合法槽范围，再核对状态和完整token，新epoch取消旧token。软件模型不暂停硬件。`CountFilter`严格校验完整块、索引、epoch后才改变状态，每次≤4096点；居中整数码范围−2048..2047，FIR/IIR此例的加权平均使输出也处于此界，使用精确整数范围内的float /4与ties-even无算术溢出。FIR前两点无真实历史而标invalid，IIR零初态为假设。显式重启应新建对象并传新epoch和真实origin，不能把gap悄悄压缩。

校准≤4096行，reference电压−10..10V、温度−50..150°C，码0..4095；要求满秩scaled design，condition<1e10，正斜率。OLS假设解释变量确知、参考误差iid同方差；输出covariance/σ/dof是这个模型内估计，没有宣称小样本覆盖率。变化配置、共模参考偏差、量化解释变量或外推需另立误差合同。

控制τp/τa为1e−6..1e3s，Ts1e−8..1s，两个Ts/τ比都在1e−6..20，K0..100；拒绝域外以明确有限数值承诺。状态[x,a,d]单位V，是工作点偏差；trace初值[1,0,0]是归一化线性例，最多4096步，状态超过1e6V模型预算则失败。输出没有物理限幅，不能拿图当真实3.3V板卡记录。原ODE RK4每保持区间500子步与解析结果在测试例10位小数核对，测试不证明全部连续参数域或实际稳定安全。

I2C RC只支持R100..1e6Ω、C1pF..1μF并返30%→70%上升时间；传输预算由正文明确帧组成推导。`device-contract.c.txt`只是带实际端口和故障出口的C伪代码，不编译，没有驱动平台函数实现。设备、IRQ最坏上界、真实D-cache、串口/CAN/USB互操作、SPICE、HDL、硬件和真人教学均not_run。

## 阅读返回路径

从 [[电子电路/44-嵌入式采集与控制/01-电压编码校准与数据契约#块与算法状态]] 取得q、count→V及跨块初态；从 [[电子电路/44-嵌入式采集与控制/03-定时中断DMA与实时预算#所有权比指针更重要]] 取得槽代际与复用规则；从 [[电子电路/44-嵌入式采集与控制/05-校准辨识与不确定度#四点完整算例]] 核对 results 的系数单位与残差；从 [[电子电路/44-嵌入式采集与控制/06-带延迟执行器的采样控制#保持区间的精确积分]] 核对第三个状态是一拍旧命令。

L10只贡献ADC→块→整数FIR/IIR→输出尺度的CPU合同和丢块/时延记录；固定点完整课程沿正式45/05，不重复重写M19-04。L13仅贡献采集时序/校准/局部控制CPU部分，电源/PCB/实测端到端系统未验收。X12给出已有CS实际主文到采样时刻和复用deadline的双向变量映射；X15仅给温度共线性/新观测的局部辨识桥，X13 PDE/传输不在本组范围。
