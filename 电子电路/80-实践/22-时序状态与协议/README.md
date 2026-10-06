---
stage: 2
aliases: [时序状态与协议CPU实验]
sources: []
prerequisites:
  - "[[电子电路/34-时序状态与协议/01-锁存触发与采样窗口#一次开门期间可以发生多次变化]]"
  - "[[电子电路/34-时序状态与协议/05-单槽缓冲替换与回压#队列不变量与有限测试各做什么]]"
  - "[[电子电路/34-时序状态与协议/06-复位亚稳态与CDC协议#单bit、脉冲、多bit不是同一个任务]]"
---
# 时序状态与协议CPU实验

六章正文是解释主源；本目录是唯一CPU源码单元，直接执行，不把源码另复制到阅读镜像，也不改旧U5 HDL。入口先看 [[电子电路/34-时序状态与协议/01-锁存触发与采样窗口|采样窗口]]；沿课程顺序到缓冲与CDC，用这里事件表检查沿前样本、沿后提交和失败前提。

在本目录执行仅需标准库的16项测试：

```bash
python3 -B -m unittest -v
```

显式输出CPU数据到库外：

```bash
python3 -B sequential.py --output /private/tmp/wwl-sequential-user-data
```

生成9组可编辑SVG、共享events.json，以及从SVG实际栅格化的360/425灰度与暗底PNG：

```bash
/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B build_visuals.py --output /private/tmp/wwl-sequential-user-figures
```

绘图构造使用确定的原生SVG事件坐标；显式生成阶段才加载本机已有CairoSVG/Pillow栅格化，不依赖GUI或字体缓存初始化。缺依赖按错误退出，不安装。两个模块的 `main(argv=None)` 都先解析必填 `--output`，import 不读取argv、不生成文件、不导入重依赖；输出主库内路径被拒绝。候选assets是本次实际生成结果，用户重跑应使用上述库外目录。

## API与模型范围

`timing` 参数单位ns，普通时刻/延迟/不确定度只接受有限实数0..10⁶、skew为±10⁶；周期必须正，cq_min≤cq_max、cd≤pd。先检查真实标量类型，拒bool、复数（含1+0j）、文本、数组、NaN/Inf、负延迟与超域，不先float转换把错误吞掉。它返回setup/hold slack与最小周期；负slack是违例，负的算术最小周期只说明该单路径setup预算不限制正周期，不能把它解释成负时钟。

`sample` 接初始bool、严格递增 `(time_ns,bool)` 事件、采样时刻与窗口；改变在开放窗口内部或恰采样沿时返回None，即未承诺。边界刚好满足约束允许，冗余“写同bit”不是变化。`latch` 接 `(time,D,G)`，G高时透明，G低保持；二者不计算模拟电压、传播延迟分布或HDL delta cycle。所有事件迭代器限4096条，超预算显式失败。

`counter`、`pipeline`、`Slot` 只接受精确Python int字，W为1..8，字须在[0,2^W−1]；bool不能冒充字，浮点不自动取整。counter的load优先；pipeline先取旧元组再提交，1..8级，None只表示无有效项。Slot继承旧单槽无直通、同沿交旧接新与reset flush；复位参数为高有效CPU标记，含义对应旧RTL低有效本地rst_n的已生效assert，不是新引脚电气规范。

`detector` 明确返回 `(next_state, output_before_edge, output_after_commit)`，Moore与Mealy依各自状态定义。Mealy沿后数值假定采样输入暂保持；不能据此保证真实脉冲宽度。`Synchronizer`/`ResetRelease`只模拟二值两级旧值移动；`handshake_trace`用源10ns与目的7ns（相位1ns）快照演示一次四相事务，显示目的15ns捕获42、源80ns完成往返。数据稳定与模拟解析在模型外，不是通用CDC仿真器。

`gray`仅检查固定有限字的相邻编码；没有实现异步FIFO。`log_mtbf`只接受resolve0..1000ns、τ/危险系数0.001..1000ns、频率1..10¹⁰Hz，返回自然log(MTBF/1s)。参数为用户显式教学假设；没有默认实际器件τ，也不输出未实测的“可靠年数”。源码数据中τ=.05ns等值注明hypothetical。

## 独立检查与边界

测试以绝对launch/capture时刻检查两种deadline，以二进制字符串截位核对计数，以历史列表检查流水线，以字符串后缀识别511条长度0..8的FSM前缀，以deque参考核对256个单沿组合与4096条四沿序列。后者包含恶意改变未接受输入的刺激，用来检查DUT不乱写，不能据此签收生产者协议；1024拍固定seed轨迹另遵守pending保持及复位epoch取消。

同步短脉冲、双沿复位释放、Gray相邻/回卷及握手捕获测试均是有限数字例。MTBF用独立直接失败率计算核对正常参数，再核对ΔTr/τ的log差。有限枚举不是实际HDL的完整形式证明；旧页已有归纳继续保留，本实验不改旧代码或旧锚点。

图中的时间为教学ns，字是bit/无符号word，不是电压测量。图caption明确功能抽象、透明窗口、sample/commit与不同域事件。九图包含实际事件与数值，没有把CPU轨迹画成模拟亚稳态。未运行HDL编译/仿真、SPICE、TCAD、综合/STA、形式工具、CDC/RDC、硬件、UI或人类阅读验收。
