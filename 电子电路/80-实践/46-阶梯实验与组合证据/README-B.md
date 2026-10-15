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

基础入口依次读 L09 的六拍、L10 的首块时间、L12 的返回路径与 L13 的完整单位链；快进入口先核下表，再核输入 SHA 与源码。这里的四卡只连接正式主库模型，不消费其他待审候选。

| 读者问题 | 实验卡与实际返回 |
|---|---|
| 怎样辨别预期与真正RTL证据？ | [[电子电路/80-实践/46-阶梯实验与组合证据/05-L09真正运行RTL与性质\|L09：六拍、纳秒窗口、工具正常/故障合同]] |
| 怎样保持物理索引和递归状态？ | [[电子电路/80-实践/46-阶梯实验与组合证据/06-L10ADC到DMA与整数状态\|L10：编码、双槽所有权与整数滤波]] |
| 回流、线的参考平面与测试地在哪里？ | [[电子电路/80-实践/46-阶梯实验与组合证据/07-L12传播回流与测试平面\|L12：开路格图与有条件的回路预算]] |
| 单项通过为何不能签收整机？ | [[电子电路/80-实践/46-阶梯实验与组合证据/08-L13传感到输出联合预算\|L13：理想G200时间链、模拟预算与两个失败]] |

## 固定连接器与复现

真源 `pipeline_lab.py` 与 `test_pipeline_lab.py` 各有同名 `-源码.md`；`pipeline-inputs.json` 的阅读镜像为 `pipeline-inputs-源码.md`。执行前先逐项SHA核验正式源；漂移抛ValueError，不能悄悄换模型。导入不运行生成、不安装依赖。数值连接仅用标准库，现有 `.venv/bin/python` 可运行。

在 WWL 根执行以下命令，输出必须是库外不存在的新目录：

```bash
.venv/bin/python -B '电子电路/80-实践/46-阶梯实验与组合证据/pipeline_lab.py' --vault . --output /private/tmp/B4-chain-fresh
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/46-阶梯实验与组合证据' -p test_pipeline_lab.py -v
```

输入固定32点、12bit/3.3V/1kS/s、4点块、双槽、J=.3ms、默认C=2ms。输出 `results.json`、`L10-pipeline.csv`、`L13-pipeline.csv`；JSON包括六拍正常/突变预测、W2有限图、C5ms全部丢块、反射事件、回路/去耦、fc100抗混叠失败与fc80重设计。CSV明确索引、采样ns、完成ns、码、滤波状态与输出参考偏差V；合成输入不是仪器记录。缺参数由argparse退出2；已有目录抛FileExistsError；源版本漂移或非法32点输入在生成前拒绝。

八项作者组合检查通过，涵盖不同参考算法与失效条件；此结果待非作者独立复核，作者没有自签。原基线41suite与全库114检查不在本组重复执行。L09实际HDL/形式工具缺失为not_run；既无VCD也无真实工具PASS日志。L12的EM/KiCad/板测、L13整机/热测、真人学习结果仍未运行。

## 读图责任

图继续指向正式主库已发布资产：L09 `expected-cycles.svg` 是CPU预期；L10的timeline是时间合同；L12 bounce、return-stack、decap-loop分别是均匀线与PCB意图；L13chain表示接口。正文说明所有端口、单位、时刻和来源身份。本组没有为这些旧资产创建新物理信用。V32—V35、V42、V43的组合图与正文在独立C组桥接卡审阅。
