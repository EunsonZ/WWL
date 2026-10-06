---
type: lab
domain: electronics
stage: 1
content_status: usable
evidence_status: partial
aliases: []
sources:
  - "https://steveicarus.github.io/iverilog/usage/command_line_flags.html"
  - "https://steveicarus.github.io/iverilog/usage/waveform_viewer.html"
  - "https://yosyshq.readthedocs.io/projects/sby/en/latest/reference.html"
prerequisites:
  - "[[电子电路/35-HDL实现与验证/02-参数化RTL与接口#一格接口怎样允许同沿替换]]"
  - "[[电子电路/35-HDL实现与验证/03-测试平台调度与独立参考#驱动和观察分别占据安全窗口]]"
---
# U26：同一合同的预期、CPU核对和真实工具结果

基础入口先在六拍预期表里找出A1交付时刻，再运行CPU测试。快入口先查源码、宽度和观察窗口，然后按本页命令运行工具。目的不是增加一张绿色截图，而是能说出哪一层运行过、哪一层仍缺证据。此处是原U5缓冲器的工具接口增量，保留旧目录、镜像和记录；不替换原实践。作者机器的iverilog/vvp/Yosys/SBY均缺失，未安装，真实HDL、综合、自动证明均not_run。

## 真源和观测合同

`elastic_slot.sv` 是单时钟、无直通、可同沿替换、异步低有效局部复位的RTL。WIDTH只允许1…8；上游未握手保持有效字。局部复位同步释放由集成者负责，此源码没有CDC或reset同步器。`elastic_slot_reference.sv` 用完整next-state过程表达同一二值更新，给综合/等价迁移练习；它不是独立队列，不能替代tb参考。

`tb_slot.sv` 用已接受历史数组和交付游标核对FIFO前缀及容量。时钟10 ns，下降沿驱动，1 ns后记录沿前端口，上升沿后1 ns检查新状态。定向第一PUSH在25 ns，第2沿在35 ns；macro突变的预期head错误观察点为36 ns。随机SV刺激是1000周期LFSR seed205017；Python seed同标识但不同PRNG，两个序列并不相同。源pending在阻塞时保持，复位epoch取消pending及未交付队列。

`slot_properties.sv` 是WIDTH=2的时钟采样性质harness，`slot.sby` 的bmc/prove/cover/mutant任务分别记录。初次采样assume复位，后续复位任意，合法源hold假设只在连续非复位时使用。past_valid防首拍无过去值；当前和上次reset guard保护head/stall检查。async2sync是工具抽象，不能据此验证亚周期异步复位脉冲、恢复移除或亚稳态。

Python模型只用标准库；import不parse argv、不探工具、不建目录。生成器惰性加载CairoSVG/Pillow，必填output先解析；数据与图只有调用generate或main才写出。无code-sync镜像新增：本页描述真源，不复制源块造成第二来源。

## CPU验证和可编辑图

以下命令从实际库根执行，输出换成你自己的**库外新目录**；不把发布assets当复现实验输出。库的venv已经有渲染依赖，缺依赖只记not_run，不安装。

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/26-HDL缓冲器与性质' -p 'test_hdl_model.py' -v
.venv/bin/python -B '电子电路/80-实践/26-HDL缓冲器与性质/generate.py' --output /private/tmp/wwl-u26-new-figures
```

固定W2的8可达状态/256转移，以及W1/2/4/8各1000周期合法随机历史检查，是CPU有限验证。9测试包括拒绝输入、reset取消、signed/carry分离、有限budget出口和故障第2拍反例。`assets/expected-waveform.json/csv`、`expected-fault.json` 和全部SVG/PNG是预期或概念图，不是工具导出的VCD。图源为generate.py，9组SVG均有360/425px渲染，保持英文图中文字与中文正文的符号映射。

## 真实HDL运行合同

工具已由使用者另行具备时，从库根运行：

```bash
.venv/bin/python -B '电子电路/80-实践/26-HDL缓冲器与性质/run_hdl.py' --output /private/tmp/wwl-u26-normal-run
.venv/bin/python -B '电子电路/80-实践/26-HDL缓冲器与性质/run_hdl.py' --output /private/tmp/wwl-u26-fault-run --fault
```

runner保存精确argv。缺iverilog或vvp，exit=2，只有execution-status.json status=not_run；不写假的compiler日志和VCD。已有工具时每步45秒budget；真实编译/执行stdout、stderr和returncode各存文件。正常运行预期simulation_passed、exit0；宏版预期simulation_failed、exit1并在36 ns检测A1/B2差异。必须检查这是逻辑反例，不是语法或缺参错误。两次运行应使用不同目录，避免旧VCD污染身份。

手动等价命令（将OUTPUT换成已创建的库外绝对目录）：

```bash
iverilog -g2012 -Wall -s tb_slot -o /private/tmp/wwl-u26-normal-run/slot.vvp '电子电路/80-实践/26-HDL缓冲器与性质/elastic_slot.sv' '电子电路/80-实践/26-HDL缓冲器与性质/tb_slot.sv'
vvp /private/tmp/wwl-u26-normal-run/slot.vvp +VCD=/private/tmp/wwl-u26-normal-run/slot.vcd
```

`+VCD`必填；测试平台不默认当前目录文件名。完整源码和宏SHA、工具`iverilog -V`/`vvp -V`、编译returncode0、normal PASS摘要及非空实际VCD才可形成这一次运行身份。查看25、35、55、65 ns沿前与26、36、56、66 ns沿后；波形中沿后B2不能当作55 ns交付B2。

## 自动性质与综合等价命令

在源码目录启动，但明确输出到库外：

```bash
cd '电子电路/80-实践/26-HDL缓冲器与性质'
sby -d /private/tmp/wwl-u26-bmc slot.sby bmc
sby -d /private/tmp/wwl-u26-prove slot.sby prove
sby -d /private/tmp/wwl-u26-cover slot.sby cover
sby -d /private/tmp/wwl-u26-mutant slot.sby mutant
```

需要SBY、Yosys及配置所用boolector，不自动装。bmc depth12检查有限展开；prove成功需基例和归纳闭合；cover要有替换、阻塞、非空复位见证；mutant预期FAIL，但具体反例采样步可与tb的36 ns不同，形式步不是物理纳秒。配置timeout45秒，日志及status必须来自真正工具执行。FAIL与ERROR区分：前者有逻辑反例，后者可能是前端/solver失败。没有实际运行时只能保留命令和预期。

从该目录执行概念RTL综合/重写等价命令，output目录事先创建在库外：

```bash
yosys -l /private/tmp/wwl-u26-synth/actual.log -p 'read_verilog -sv elastic_slot.sv; hierarchy -check -top elastic_slot; proc; opt; check -assert; write_json /private/tmp/wwl-u26-synth/netlist.json'
yosys -l /private/tmp/wwl-u26-equiv/actual.log -p 'read_verilog -sv elastic_slot.sv; proc; async2sync; opt; design -stash gold; read_verilog -sv elastic_slot_reference.sv; proc; async2sync; opt; design -stash gate; design -copy-from gold -as gold elastic_slot; design -copy-from gate -as gate elastic_slot_reference; equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple; equiv_induct; equiv_status -assert'
```

逐拍比较全部端口包括保留的无效data，reset映射须一致。async2sync模型、初始状态和equiv_induct特殊定义须核日志与reset基例；不能从一个成功状态概括任意四值/物理等价。此命令没有标准单元库或布局布线，不是STA/CDC签核。真实网表应辨认寄存器与MUX/enable，无预期锁存；若工具报告其它结构，先核源码/参数/宏再解释。当前没有产生netlist.json或实际综合log。

## 当前证据与下一步判据

本交付的作者CPU运行和静态/图检查在库外READY绑定；它不是独立签收或学习者掌握记录。当前tool probe实际缺失，normal/fault compile+simulation、formal四任务、综合/等价、STA/CDC和硬件全部未运行。工具缺失按本批授权保留内容候选，不伪装完成M17-06的真实运行层。完成这层时必须补同版本来源、精确命令、退出码与实际失败/正常波形，而非把expected CSV改后缀成VCD。
