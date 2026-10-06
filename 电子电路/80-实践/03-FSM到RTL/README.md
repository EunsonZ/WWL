---
stage: 1
aliases: []
sources:
  - "https://rhlab.ece.uw.edu/wp-content/uploads/sites/26/2022/03/Lab-5_-Sequential-Logic-and-Finite-State-Machines.pdf"
  - "https://resources.altera.com/quartushelp/24.2/da_rules/res_50001.htm"
prerequisites:
  - "[[电子电路/30-数字电路与实现/01-状态机寄存器与时序合同]]"
  - "[[电子电路/30-数字电路与实现/02-RTL性质复位与跨时钟边界]]"
---
# U5：一格FSM到RTL与验证

对象是单时钟、单项、无穿透 ready/valid 弹性缓冲；EMPTY/FULL 是控制状态，数据寄存器另外保存 W 位。先从 [[电子电路/30-数字电路与实现/01-状态机寄存器与时序合同#先固定沿前与沿后|六拍手算表]] 预测 A1/B2，或直接从 [[电子电路/30-数字电路与实现/01-状态机寄存器与时序合同#对所有长度的输入序列证明安全|队列归纳]] 出发，两条入口回到同一代码。

## 真源与实际证据

- `elastic_buffer.sv` 是参数 WIDTH≥1 的 RTL；本地 rst_n 异步 assertion，集成层负责本时钟域同步 release。本模块不含同步链。
- `tb_elastic_buffer.sv` 是 10 ns 时钟教学测试台，下降沿驱动，上升沿之后检查更新；独立一格队列、定向 stall/replace/reset、5000 拍确定性伪随机激励。上游被拒绝时保持 pending 数据；flush 明确取消复位 epoch 中的 pending、清 s_valid，并在释放后的间隔上升沿检查 EMPTY，避免旧有效输入偷偷被接入而队列未记账。
- `buffer_model.py` 是纯 Python 二值沿模型；CLI 要求显式 `--output`，输出六拍 CSV。`test_buffer_model.py` 包含独立八行真值表、4 位旧/新数据枚举共 2048 情况、20000 拍独立队列与复位 epoch、拒绝非法输入、stall 反例和首拍无穿透。
- [[电子电路/80-实践/03-FSM到RTL/04-源码性质与验证|源码性质与验证]] 保存上述四份逐字 code-sync 镜像，执行以真源为准。正文说明 [[电子电路/30-数字电路与实现/02-RTL性质复位与跨时钟边界|SVA、复位与签核边界]]；可选 U5_SVA 宏只打开两条性质，默认测试台使用立即断言。
- `assets/build_visuals.py` 是可编辑 SVG 的确定性生成源，接受 `--output`；`fsm.svg`、`cycles.svg`、`signoff.svg` 与各自 425px PNG 是交付图。`trace.csv` 是模型实际生成的教学轨迹。重新生成需要已有 cairosvg，不自动安装。

本批 Python 6 项测试通过；SVG 渲染与三幅 425px PNG 已实际查看。普通 PATH 与常见 Homebrew/local 路径未找到 iverilog、verilator、yosys；因此 **RTL/测试台/SVA未编译未仿真，综合未运行**。Python 层通过不为 SV 提供编译或语义运行证据；这里不包含真实 Obsidian 客户端、FPGA、CDC/RDC、布局 STA、形式工具或生产测量通过证据。

## 可复现命令

从本目录运行，无新增依赖：

```bash
python3 -B -m unittest -v test_buffer_model
```

生成必须指向新的库外目录；例如先创建一个已有许可的 `/private/tmp` 临时目录，把实际绝对路径代入：

```bash
python3 -B buffer_model.py --output /private/tmp/u5-reproduce/assets
python3 -B assets/build_visuals.py --output /private/tmp/u5-reproduce/assets
```

第二条需要已有 cairosvg；本批使用主库 `.venv/bin/python`，普通 python3 缺此依赖时记录图再生未运行。两条均不向源码旁写 bytecode（-B）。`--output` 不自动防止指定源码 assets；复现者必须用新路径保护冻结结果。比较 CSV 字节与 SVG/PNG，跨渲染器版本也要实际看文字和连线。

若将来已有 Icarus Verilog，可在本目录显式把二进制写库外并运行；下面是未执行命令，不是验收结果：

```bash
iverilog -g2012 -s tb_elastic_buffer -o /private/tmp/u5-reproduce/tb.vvp elastic_buffer.sv tb_elastic_buffer.sv
vvp /private/tmp/u5-reproduce/tb.vvp
```

默认不定义 U5_SVA，避免把某工具不支持的 concurrent assertions 混成默认模拟合同；需要支持 SVA 的工具另外以该宏编译并记录工具/版本/命令/退出码与 cover 结果。无工具不得安装或把命令存在当通过。

## 验证责任与改坏练习

Python 独立八行表认证二值转移，独立队列认证有限样本的顺序/容量/清空，完整任意长度安全由主课归纳承担。测试故意展示未接受 B2 覆盖 A1 的错误结果，但不是自动 HDL mutation 测试。复制源码到库外再把 SV 写使能改为 s_valid，期望测试台在 stall 后报告 ordering/stall；实际运行后才能报告检出。

自主迁移请完成 [[电子电路/30-数字电路与实现/01-状态机寄存器与时序合同#反例与迁移|五拍输入与去ready组合路径题]]，再完成 [[电子电路/30-数字电路与实现/02-RTL性质复位与跨时钟边界#独立迁移题与答案责任|CDC/复位/多周期约束辨错题]]。接受合法等价电路与明确未知；改变容量、穿透或吞吐必须给新时序合同，不能借“等价”跳过差一拍。
