---
stage: 1
aliases:
  - 储能与变换域桥梁复算
sources:
  - https://math.mit.edu/~hrm/papers/lmt.pdf
prerequisites:
  - "[[电子电路/10-电路基础/06-储能与开关前后的初值]]"
---
# 储能与变换域桥梁复算

先在 [[电子电路/10-电路基础/07-RC与RL的第一次时间域求解|第一次RC/RL求解]] 手算，再用本单元核对面积、状态与初值端口。这里是本批新增六节正文的CPU图解支持；未认证SPICE、实物或真人学习效果。通用卷积/ROC严格解释复用信号主文，电子侧图件体现节点、状态、量纲和初始储能源方向。

## 参数与结果合同

RC：R=1000 Ω、C=1e−6 F、源1 V、初值.4 V；RL：R=100 Ω、L=.01 H、源1 V、初值.02 A。`transform_lab.py`为纯stdlib数值真源，输入有限实标量，时间非负，R/C/L正；bool、非有限、非法时间和派生溢出拒绝。各函数计算常输入单个时刻，未提供块状态或离散滤波器API，不混用旧RC实验的n→n+1合同。

RC在.25 ms为.5327195302 V，1 ms为.7792723353 V；初始储能.08 μJ。RL在.1 ms为13.67879441 mA，电感电压−.3678794412 V。生成CSV使用SI列名：time_s、rc_voltage_V、rc_current_A、rc_charge_C、rc_energy_J、rl_current_A、rl_voltage_V、rl_energy_J；模态CSV明确sigma_per_s与omega_rad_per_s。

## 实际可复现入口

先在本目录启动，使用已有Python。数值核与大部分数值测试只需stdlib，完整生成/进程测试还需已有CairoSVG；本批使用主库已有`.venv/bin/python`。缺依赖记未运行，不自动安装。

```bash
python3 -B -m unittest -v test_transform_lab
```

```bash
task_transform_output="$(mktemp -d /private/tmp/wwl-transform-reproduce.XXXXXX)"
python3 -B build_visuals.py --output "$task_transform_output/nested/assets"
```

`build_visuals.generate(output)`只在显式调用时载入CairoSVG并创建目标，`main(argv=None)`要求--output，缺省退出2。导入不解析陌生调用者argv、不产生目录或图。选择新的库外目录运行，比较CSV、参数、SVG结构和图中方向，不以跨环境文件字节相同认证结果。

## 六组原创图各自解释什么

| 图源输出 | 对应内容 | 视觉与数据合同 |
|---|---|---|
| switch-state | V05开关前后 | 两幅RC接线与一幅独立RL接线；节点a/0、源/触点/R/C/L与完整返回路径；预充.4 V及开关后有限R |
| charge-energy | V06变化率与面积 | RC电压、电流及能量；0到1 ms阴影给电荷增量.379272 μC；CSV足以复算 |
| s-modal | V11复频率模态 | 三个s点对应同ω、不同σ的实部波形，各自电压轴尺度明示 |
| roc-regions | V12侧别与ROC | 左右同式的不同开半平面、双侧开条带；规范化轴sigma/a、omega/a，虚线不包含 |
| origin-jump | 微分边界 | .4→1 V跳变，广义导数冲激面积.6 V；示意箭头不是实际有限脉冲高度 |
| initial-sources | V13初值源 | C/L各串并联端口图；a对b为正，I进入a；源方向与元件式一致 |

SVG真源是生成器的几何与数值参数，全部有title/desc；同一425px画布实际输出360与425px PNG。正文中中文图注解释英文图标。最小图文字12源像素，在360px下约10.2px；多数标签14–16源像素对应11.9–13.6px。使用固定白底/黑线，线型与阴影不靠色相分辨。每幅原图保留可编辑SVG与参数JSON，未使用照片、厂家图复制或物理实测数据。

作者已查看六幅360预览并调整白底、轴标及累计面积；这是独立文件预览，不是Obsidian深浅主题、公式和真实阅读完成证据。

## 验证与源码交接

`test_transform_lab.py`由独立RK4核对RC/RL时域状态，用独立Simpson积分核对电荷/源能量/电阻热量、左右侧/条带ROC内复数积分、0+/0−跳变边界，以及C/L串并联初值端口。测试明确没有试图用有限数值积分“证明无穷区间发散”；边界发散由正文加权绝对尾项判定。另测生成器导入/缺参无副作用、新嵌套输出、XML/title/desc/PNG实际宽度、CSV初值/样点和源资产哈希未变。

阅读真源镜像 [[电子电路/80-实践/04-储能与变换域桥梁/源码与验证|三份逐字源码镜像]]，修改真源后才同步镜像。图的版权为本库原创生成；公式和模型按正文一手资料定位及本批自行推导，不冒称整课、所有器件或真实学习者通过。
