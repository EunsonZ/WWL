---
stage: 2
aliases: []
sources:
  - https://docs.kicad.org/9.0/en/getting_started_in_kicad/getting_started_in_kicad.html
  - https://www.ti.com/lit/an/szza009/szza009.pdf
  - https://www.analog.com/media/en/training-seminars/tutorials/MT-031.pdf
prerequisites:
  - "[[电子电路/50-PCB布局与调试/01-符号引脚封装与BOM替代#先确定电路，再决定空间]]"
---
# KiCad项目到制造包与人工复核

**读者问题：有PCB文件，是否就能发厂？** 基础入口把同一板的符号、焊盘、铜、孔和装配对应起来；快进入口追一次版本转换、规则检查与制造交接。我们的原生项目是可编辑候选，KiCad软件读取/保存、ERC、DRC、填区和制造导出尚未运行，不能以文件扩展名冒充工具通过。

## 项目是多视图的共同版本

实验project/含rcdaq.kicad_pro、.kicad_sch、.kicad_pcb、自有PCBTeaching.pretty封装、fp-lib-table、rcdaq.net、bom.csv、testpoints.csv和制造检查单。符号嵌入原理图、封装嵌入PCB，仍保存库使后续可编辑；自有0805几何是教学值，不是具体MPN的已核land pattern。

[KiCad 9.0文档](https://docs.kicad.org/9.0/en/getting_started_in_kicad/getting_started_in_kicad.html)说明项目设置与原理图/布局一同保存。本次实际读到的指南基于9.0.9、revision152cd19e，候选采用原生s-expression语法并明确未用真实KiCad解析。CPU只核括号/字段、引脚网集与几何线，不替代软件的语法兼容及保存往返。

![[电子电路/80-实践/33-RC采集板与制造交接/assets/board-top.svg]]

图用同一board.json坐标绘制40×30mm俯视，不是假KiCad截图；黄色等颜色之外还有net名与线型，地via及TP可定位。B.Cu画布局意图，没有虚构已填充铜或照片。若修改PCB而不更新原理图/数据，应检测parity及版本差，不拿旧CPU模型结果继续签新板。

## ERC和DRC回答不同问题

ERC看引脚电气类型、未连、电源驱动及标注冲突；本原理图passive教学符号不能检出真实外ADC的供电/输入钳位错误，因此外部接口合同要人工复核。DRC看铜间距、短路/未连、孔/板边等规则，规则本身应来自制板/装配能力，不是默认数值越小越“高级”。本候选clearance=.25mm、signal=.25mm、power=.5mm、via外径.6/drill.3mm，未取得厂商批准。

B.Cu GND zone在原生PCB中只有边界定义，必须真正填区后检查与导出。移动焊盘、线或过孔会改变避让和孤岛；旧填区不代表新layout。CPU的“连续矩形平面”只是一层假设，不能据此宣称已存在地铜、没有热焊盘连接问题或可制造。

![[电子电路/80-实践/33-RC采集板与制造交接/assets/release-flow.svg]]

已有KiCad9 CLI时，复制完整项目至新工作目录，记录版本与输入SHA，再执行：

```bash
kicad-cli version
kicad-cli sch erc --exit-code-violations --output erc.rpt rcdaq.kicad_sch
kicad-cli pcb drc --schematic-parity --exit-code-violations --output drc.rpt rcdaq.kicad_pcb
kicad-cli pcb export gerbers --output fabrication/ rcdaq.kicad_pcb
kicad-cli pcb export drill --output fabrication/ rcdaq.kicad_pcb
```

具体选层/单位/钻孔分组按该实际版本帮助核对；GUI填区、从原理图更新与人工复核亦要完成，不把这些命令串当无条件签核脚本。[官方CLI9.0](https://docs.kicad.org/9.0/en/cli/cli.html)定义ERC/DRC、parity和导出接口；本环境命令未发现，因此未运行且不产生伪erc.rpt/drc.rpt/Gerber。

## 制造包必须能独立重建几何

铜F/B、阻焊F/B、需要的丝印、Edge.Cuts和PTH/NPTH钻孔，另有job/README版次；paste用于钢网而非自动必需制板层。Gerber不替代钻孔，BOM不替代装配坐标，3D视觉不替代铜连接。独立viewer叠层检查孔与焊盘同原点、40×30mm不是inch、闭合唯一板框、没有误镜像底层、孔槽/阻焊桥、丝印是否压焊盘与pin1标记。

BOM的MPN/供应商/替代状态、DNP和封装应与装配版一致，测试点可达；人要按connector**朝向与pin编号**接外ADC，不按屏幕位置猜。若制造方合并孔文件/调整叠层，要保存变更及人工批准，不把候选哈希换成任意新文件再沿用旧结论。

## 证据逐层保留

本课CPU模型/原创SVG、原生项目文本、真实KiCad解析/规则报告、独立Gerber复核、实板照片/电气测量是不同层。当前前两层可查，后几层not_run。V37要求同板授权照片与仪器定位，因此这里只交原理图/布局/TP部分，不借Arduino照片假装RCDAQ-P1已经制造，也不将另一型号外部板的素材合并成同板完整信用。

## 四题及理由

1. DRC零错误代表选中的0805适合实际MPN吗？**不。** 规则不能代替供应商焊盘/公差/装配条件。
2. 修改C2位置后沿用旧Gerber可吗？**不。** 改版需填区、重验、重导出并绑定新版本。
3. Gerber铜层正确却没有钻孔文件，是否完整？**不是。** 孔位/孔径/镀孔及分组需独立文件和叠层核对。
4. CPU几何连通通过，可在日志写ERC/DRC pass吗？**不可。** 本次未运行真实工具，模型检查的对象与规则不同。
