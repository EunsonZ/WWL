---
type: experiment
domain: electronics
stage: 1
content_status: usable
evidence_status: partial
aliases:
  - RLC功率三角形与周期功率复算
sources:
  - "https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/66adf4d4611a57b949efa1b00a842a46_6002_l17.pdf"
prerequisites:
  - "[[电子电路/12-交流与变换域/21-从阻抗方向到功率周期账]]"
---
# RLC 功率三角形与周期功率复算

本组只算四个固定、理想、串联、同频正弦稳态模型。不是任意网表、暂态或器件求解器。共同输入为 10 V RMS、ω=1000 rad/s、R=10 Ω；RL 加 10 mH，RC 加 100 μF，RLC 加 10 mH 与 200 μF。参数用于数学复算，图中没有实物搭建或测试结果。

`models.py` 为真源，`cases()` 返回独立的四份 SI/RMS 对象，`waveform(case,count)` 只接受等于固定记录的对象和 256–65536 的整数采样数，拒绝布尔及浮点采样数。时刻为 [0,T) 等距网格，不重复终点；CSV 包含端口和各元件的电压、瞬时功率，可逐行核对 KVL 和能量账。图里的 P 用 W、Q 用 var、|S| 用 VA，相加的是复数分量，三者不是三份耗散。

在库根运行测试；输出必须选库外新目录，路径已存在则拒绝，避免覆盖先前结果。

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/43-阻抗与功率图解' -v
.venv/bin/python -B '电子电路/80-实践/43-阻抗与功率图解/generate.py' --output /private/tmp/wwl-rlc-power-new
```

`generate(output)` 与 `main(argv=None)` 支持导入，导入不解析参数、不绘图、不生成文件。调用后生成 4 张原生可编辑 SVG、8 张 360/425 宽 PNG、cases.json 和 waveforms.csv，共 14 个文件。依赖沿用本库现有 CairoSVG，不安装包；不用 Matplotlib，不改其 rc 参数、环境变量、当前目录或随机状态。多文件生成并非原子事务，异常中断后的部分目录应保留供检查，另选新目录重跑。

六项模型检查包括独立闭式值、端口与元件周期平均、时间域逐点守恒、本构导数、负瞬时功率反例、共同相位与峰值约定；两项输出检查覆盖导入、缺参、显式输出及已有输出拒绝。CPU 检查不等同于 SPICE、仪表、元件、实物、Obsidian 或真人学习验收。测试与图版本的独立审阅结果见库中的实际结果日志；未完成的层次保持待验。
