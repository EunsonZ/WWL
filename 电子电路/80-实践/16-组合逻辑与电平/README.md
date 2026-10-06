---
stage: 1
aliases: [组合逻辑电平实验]
sources: [本目录logic_examples.py, 本目录generate_figures.py]
prerequisites:
  - "[[电子电路/32-组合逻辑/06-组合逻辑全枚举与性质验证]]"
---
# 组合逻辑与电平实践

从 WWL 库根启动，所有输出明确放到库外。唯一数值源码是 [logic_examples.py](logic_examples.py)，唯一图源码是 [generate_figures.py](generate_figures.py)，测试是 [test_logic_examples.py](test_logic_examples.py)。这里没有平行复制的源码镜像；修改实现后须一起重跑同单元测试与图。模块导入只用标准库，不建目录、不载入绘图库。

本机已存在 `.venv/bin/python`，有 NumPy、Matplotlib、CairoSVG、Pillow。教学依赖无需 SciPy。迁移到其他机器时应使用已有的同等环境；缺依赖记录未运行，不自动安装。命令中的 `task_source` 是本目录的绝对路径，例如把下面变量设成 `$(pwd)/电子电路/80-实践/16-组合逻辑与电平`（候选未发布时应使用候选对应的绝对路径）。

```bash
task_source="$(pwd)/电子电路/80-实践/16-组合逻辑与电平"
task_output="$(mktemp -d /private/tmp/wwl-logic-run.XXXXXX)"
.venv/bin/python -B "$task_source/logic_examples.py" --output "$task_output/numeric"
.venv/bin/python -B -m unittest discover -s "$task_source" -v
.venv/bin/python -B "$task_source/generate_figures.py" --output "$task_output/figures"
```

两个 CLI 都必填 `--output`；缺参退出且不写文件。也可 `generate_figures.generate(output)` 显式生成。绘图在该函数内才导入重依赖、设置输出目录内的 `.mplconfig` 与 `.cache`，以 `matplotlib.figure.Figure` 和 Agg canvas 保存；无 pyplot、无 import 时字体缓存。灰度和暗背景预览也留在指定目录，白色图底保证暗界面中文字对比度。

`results.json` 保存 VTC 模型条件、V 单位边界、s 单位时间、W 单位功率及枚举计数。`figure-data.json` 保存图采样规则与数值；SVG 元素及文字可编辑。VTC 每支 350 点，排除 λ=0 中点的非唯一解，虚线表示其可行集合。负载使用 201 个均匀时间点、0–100 ns，解析 RC 公式无需数值积分误差；中心差分斜率测试步长 1 μV。图中不是具体型号的实测波形。

全枚举默认宽度 4、预算 10000，预先计算所需 1080 行，实际含 768 算术组、256 比较组及其余模块 56 行。宽度接口只允许 1–8；超预算先拒绝，不部分执行后报告成功。8 位要求 262200 行，可明确增预算，绝不从 4 位测试推定任意位宽全覆盖。单次 scalar 电气函数为闭式计算，没有迭代无限循环。字输入需 Python int，实数参数需有限 real scalar；bool、复数、字符串与嵌套数组不自动转换为合法输入。

8 个作者单元测试涵盖全枚举整数 oracle、解析噪声边界与 −1 斜率、RC 半电源和 VIH 回代、标志反例、总线冲突/释放及无效输入。导入副作用/CLI 缺参/图重建另有作者环境证据。作者检查不是独立签收；图、电路语义与来源在精确冻结版本之后再交独审。

这套实验运行的是 Boolean 和明确的长沟道/RC 模型，没有运行 HDL、SPICE、形式验证工具、硬件或真人阅读试验；总线 X/Z 是抽象诊断，SRAM 读扰是原理解释，未做 transistor-level SRAM 模拟。
