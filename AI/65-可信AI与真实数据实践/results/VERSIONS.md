---
type: resource
domain: artificial-intelligence
content_status: usable
evidence_status: partial
evidence_scope: "固定数据本地执行与文件版本；语义与真实客户端另验"
sources:
  - https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset
prerequisites: []
---

# 小时项目冻结版本

契约：bike-local-hour-v1。日期边界：2011训练、2012上半年开发、2012第三季度区间校准、2012第四季度最终测试；固定原文件17379行，日期实体不跨集。Python3.14.7、NumPy2.5.3、Matplotlib3.11.2。主模型由开发MAE选λ=0.1，无重拟合；偏移来自开发残差75%分位数，半径来自校准绝对残差秩。主测试记录2168条。源码、模型、区间、行动、预测与报告是同一变更单元。

SHA-256记录固定文件字节，跨平台浮点末位可能不同。这里的结果文件是真实本地运行观察，不替代未来季度验证、人口公平研究或生产上线。重复运行3次用于检查可复算与修复输出保全/发布前校验，测试集没有变成3份独立样本。

| 文件 | SHA-256 |
| --- | --- |
| trustworthy_lab.py | 03a50698a1082bd2a5ad57c72dea37cf9df2d5b8d54ae0880e64a275d3f30e5f |
| test_trustworthy_lab.py | 65230ba71e229a8948ffd0cc2b65f5b985d7f1ac9066226957cd932a15b1a04d |
| plot_trustworthy.py | 4c50c60679ac85d6bbfec1f0bd7f8ae98a9f81fbb4447bf757e4656166f06ad9 |
| data/hour.csv | e03de4ee4ef4dc376ac6e04bf829673c6269e8eba5c60fa121640fa2f829504f |
| data/Readme.txt | b92c8628622948bf0828c43a1b315d1517c3d7fd63654730d0dea379b8e88175 |
| results/model.json | efcbbdc7f019464140d06ab8a557acc08a12f25b1ab20212b57ca4ca298fe02a |
| results/report.json | c8cd41f5945937161a4342ab44ab6ecd3a4d76383cd348bd59e50b7bd75b6408 |
| results/test_predictions.csv | 2408441382fdee1f4e3d23e414c78e8dd1155b9155165215596811a9ed44e580 |
