---
type: lab
domain: electronics
stage: 3
content_status: usable
evidence_status: partial
aliases: []
sources: []
prerequisites: []
---
# B组：从局部模型走到一份可追踪的系统合同

基础入口依次读 L09 的六拍、L10 的首块时间、L12 的返回路径与 L13 的完整单位链；快进入口先核下表，再核输入 SHA 与源码。这里的四卡按输入登记SHA连接已发布模型，不消费其他待审候选。

| 读者问题 | 实验卡与实际返回 |
|---|---|
| 怎样辨别预期与真正RTL证据？ | [[电子电路/80-实践/46-阶梯实验与组合证据/05-L09真正运行RTL与性质\|L09：六拍、纳秒窗口、工具正常/故障合同]] |
| 怎样保持物理索引和递归状态？ | [[电子电路/80-实践/46-阶梯实验与组合证据/06-L10ADC到DMA与整数状态\|L10：编码、双槽所有权与整数滤波]] |
| 回流、线的参考平面与测试地在哪里？ | [[电子电路/80-实践/46-阶梯实验与组合证据/07-L12传播回流与测试平面\|L12：开路格图与有条件的回路预算]] |
| 单项通过为何不能签收整机？ | [[电子电路/80-实践/46-阶梯实验与组合证据/08-L13传感到输出联合预算\|L13：保留理想G200、因果稳态、模拟预算与失败]] |

## 固定连接器与复现

真源 `pipeline_lab.py` 与 `test_pipeline_lab.py` 各有同名 `-源码.md`；`pipeline-inputs.json` 的阅读镜像为 `pipeline-inputs-源码.md`。执行前先逐项SHA核验登记源；漂移抛ValueError，不能悄悄换模型。导入不运行生成、不安装依赖。数值连接仅用标准库，现有 `.venv/bin/python` 可运行。

先从 [[电子电路/80-实践/46-阶梯实验与组合证据/08-L13传感到输出联合预算#执行与四题|L13复建与执行入口]] 在WWL根建立五项冻结输入副本，完成SHA核验并保留该shell中的 `WWL_L13_INPUT`，再执行以下命令。当前主库embedded已修正ADC浮点阈值边界，budget已修正相关PSD的数值缩放，两者与原登记SHA不同，直接 `--vault .` 应拒绝。本卡使用固定提交 `678f1c7f5afaf5bd34be713798fe4df500131adb` 的输入复现既有教学合同；它不会替换或撤回main的修正，原 `pipeline-inputs.json` 保持。输出必须是库外不存在的新目录：

```bash
.venv/bin/python -B '电子电路/80-实践/46-阶梯实验与组合证据/pipeline_lab.py' --vault "$WWL_L13_INPUT" --output /private/tmp/B4-causal-20261016-my-new-run
WWL_SOURCE_VAULT="$WWL_L13_INPUT" .venv/bin/python -B -m unittest discover -s '电子电路/80-实践/46-阶梯实验与组合证据' -p test_pipeline_lab.py -v
```

输入固定32点、12bit/3.3V/1kS/s、4点块、双槽、J=.3ms、默认C=2ms。输出 `results.json`、`L10-pipeline.csv`、原ideal-G200的 `L13-pipeline.csv` 与新增 `L13-causal-butterworth-steady-state.csv`；JSON包括六拍正常/突变预测、W2有限图、C5ms全部丢块、反射事件、回路/去耦、fc100抗混叠失败与fc80重设计。原CSV保留索引、采样ns、完成ns、码、整数滤波与输出参考偏差V；新增CSV还记录连续四状态、滤波输入/输出V、ADC绝对电压V及队列块/槽/状态。合成输入不是仪器记录。缺参数由argparse退出2；已有目录抛FileExistsError；源版本漂移或非法32点输入在生成前拒绝。默认已运行快照保留为 [结果JSON](results-causal-steady/results.json) 与 [因果稳态CSV](results-causal-steady/L13-causal-butterworth-steady-state.csv)，均直接来自本轮已验输出；前者看完整字段，后者逐点核状态/电压/码/队列。它们是既有运行的正式附件，读取附件不等于本机复算；复算仍须按L13入口复建登记SHA的五项输入，生成全新库外目录。旧L10/L13 CSV不在新子目录重复复制。

2026-10-16作者用上述冻结输入运行12项组合测试通过（原8项回归加4项因果稳态检查，0.172s），新输出生成exit0。独立参考采用四极点复频响与连续状态矩阵消元，覆盖相位、端口、非零稳态初值、32点状态/码/队列及非法参数在状态变化前拒绝；原L10/L13 CSV与未改连接器使用同输入的输出逐字节相同。非作者又用连续状态矩阵的模态常数变易解独核四组参数、共128点，四状态最大差约1.249×10⁻¹⁶ V，并独立复跑12项测试通过（0.170s）。这128个电压在冻结floor/当前阈值ADC下同码；fc80/100最近阈值距离约28.1634402501/5.7692514468 µV，相关PSD修正不在本卡budget评估路径上，fc80/100新旧评估逐字段一致。五源导出SHA与两份旧CSV字节亦独核通过，具体参数、证据与容差见L13正文；不能将这组结论推广到任意阈值附近输入或其他配置。原基线41suite与全库114检查不在本组重复执行。L09实际HDL/形式工具缺失为not_run；既无VCD也无真实工具PASS日志。L13新增分支只含理想G200与理想四阶连续因果滤波器的负无穷正弦稳态；有限A/GBW、随机噪声和偏置仍是独立预算，没有逐样注入，零初态与真实AFE尚未覆盖。L12的EM/KiCad/板测、L13整机/热测、真人学习结果仍未运行。

## 读图责任

图继续指向正式主库已发布资产：L09 `expected-cycles.svg` 是CPU预期；L10的timeline是时间合同；L12 bounce、return-stack、decap-loop分别是均匀线与PCB意图；L13chain表示接口。正文说明所有端口、单位、时刻和来源身份。本组没有为这些旧资产创建新物理信用。V32—V35、V42、V43的组合图与正文在独立C组桥接卡审阅。
