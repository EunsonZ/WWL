---
stage: 2
aliases: []
sources: []
prerequisites:
  - "[[电子电路/50-PCB布局与调试/05-KiCad项目到制造包与人工复核#ERC和DRC回答不同问题]]"
---
# RCDAQ-P1制造交接门槛

当前为可编辑教学候选，未经过KiCad读取/ERC/DRC/填区/导出；不能送厂。

1. 在明确KiCad版本打开完整rcdaq项目，检查所有嵌入符号/自有封装、netlist与BOM，按实际MPN图纸核编号/极性。
2. ERC含引脚电气类型/电源驱动责任；本版passive教学符号不能证明外ADC供电正确。
3. 从原理图更新PCB，核parity、重新填B.Cu区、完整DRC含短路/未连/边界/孔距，真实规则由制板方确认。
4. 导出F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,Edge.Cuts与PTH/NPTH Excellon和job；底层不镜像自改。另存版本SHA和工具输出。
5. 独立Gerberviewer逐层叠钻孔/外形、pin1/镂空/丝印压焊盘/阻焊桥/孔槽/填区，人核40×30mm单位与原点。
6. BOM含MPN/容差/额定/有效C/DC偏压/温度/装配DNP；组装坐标与正反面零度约定另验。所有候选MPN未选择，禁止声称可采购量产。
7. 截图、Gerber、照片、ERC/DRC日志目前都not_run/不存在；生成教学SVG不是这些证据。
