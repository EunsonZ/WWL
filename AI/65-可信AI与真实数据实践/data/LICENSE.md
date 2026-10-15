---
type: resource
domain: artificial-intelligence
content_status: usable
evidence_status: partial
evidence_scope: "正文推导与作者数值复算、固定公开数据本地执行；独立语义审阅与Obsidian显示另验"
aliases: []
sources:
  - "https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset"
  - "https://creativecommons.org/licenses/by/4.0/"
prerequisites: []
---

# Bike Sharing数据归属与许可

原始发布者：Hadi Fanaee-T。数据名称：Bike Sharing（2013）。UCI Machine Learning Repository，数据DOI：[10.24432/C5W894](https://doi.org/10.24432/C5W894)。[数据页面](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset)，[固定下载入口](https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip)。

作者于2026-09-17实际打开的UCI页面License段落标明[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)。`hour.csv`与`Readme.txt`从UCI ZIP逐字节提取，没有改动CSV、增补行或更改字段。课程图表与预测结果由本地代码生成。许可链接和归属说明随数据一起保留。

归档Readme要求引用：Fanaee-T, Hadi, and Gama, Joao. “Event labeling combining ensemble detectors and background knowledge.” *Progress in Artificial Intelligence* (2013), [DOI10.1007/s13748-013-0040-3](https://doi.org/10.1007/s13748-013-0040-3)。这里仅转述数据归档的引用要求，未把该论文作为本组因果解释的验证证据。

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| hour.csv | 1156736 | e03de4ee4ef4dc376ac6e04bf829673c6269e8eba5c60fa121640fa2f829504f |
| Readme.txt | 5607 | b92c8628622948bf0828c43a1b315d1517c3d7fd63654730d0dea379b8e88175 |

原字节包含2011–2012年聚合小时计数与环境变量，没有个人ID；本组没有从它推断私人人口属性。当前页面与归档对season名称和温标解释不一致，课程使用原类别代码和归一化原值；页面17389实例与文件17379行也单列说明。数据hash固定文件版本，不能证明字段测量的社会有效性。
