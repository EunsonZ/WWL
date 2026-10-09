# ChinaResearch → WWL / Codex 研究交接包

整理日期：2026-10-09。原72页报告资料截止：2026-08-10。

## 执行入口

主任务：https://github.com/EunsonZ/WWL/issues/119
来源档案及公开讨论演进：https://github.com/EunsonZ/WWL/issues/118

已完成：来源文件检查、重点证据复核、新问题与反证设计、GitHub两个issue创建及读回。未完成：Codex执行、知识正文修改、实现PR、独立学术复核和真实Obsidian客户端交接。

两个issue包含内容级研究交接、主题覆盖、原报告逐章定位、纠偏、机制、实际来源、跨领域链接和验收；不是逐字聊天导出。本包保存原始TXT和PDF的完整字节、逐页文字派生稿、PDF外链表，以及本次可复算例子。

**本包仅在聊天中生成，未作为GitHub issue附件上传。** Codex若只读取GitHub issue，不会自动获得本包。将此ZIP作为Codex任务附件或解压到其可读工作目录后，先核验manifest.json，再根据AGENTS与#119归档。不可把ChatGPT的sandbox路径当作跨环境下载地址。

## 目录与身份

- `originals/ResearchReport.txt`：用户上传的历史报告，保留原文，不因本次校注修改。
- `originals/China_Governance_Economy_Society_2026_2035_Report.pdf`：原72页报告，含历史判断与待核引用。不是全部经独立验证的证据。
- `derived/report_extracted.md`：排序提取全文，带PDF物理页标记。
- `derived/pdf_body_normalized.md`：物理第9—72页正文，清理页眉、页脚和多余空行；并非无损版式还原。
- `derived/pdf_links.json`：PDF中的43个URL记录及物理页，不等于43项独立证据。
- `research/new_reflections.md`：本轮追问与反思概览，详细执行合同以#119为准。
- `research/reproduce_examples.py`：仅用Python标准库重算教师净变化与两个教学例，并可核验包文件哈希。
- `research/examples.json`：实际运行产生的计算结果。真实统计与教学构造分别标记。
- `research/sources.json`：本轮重点来源定位与读取边界，不是原PDF全部52条文献的替代。
- `manifest.json`：本包其他文件的SHA-256、字节数及文件角色；manifest本身不列自己的哈希。

## 使用边界

1. 原图的几何、曲线和公式上下标可能无法从文字提取恢复。原件到位后回到PDF视觉核对；没有原绘图数据时只能做带来源的重建，不声称恢复了原始代码。
2. 原报告内的概率是作者情景权重，不是已校准模型。政策建议不是已经实施的事实。
3. 原稿部分引用定义缺失，PDF部分书目不完整；不得找相似文章擅自补齐。
4. 保留旧数值的观察时点和修订版本。2026年上半年数据不等于2026年10月最新月度数据。
5. 不得把原稿→PDF→本次issue的复述链当成三个独立证据。
6. #118中“城乡保障覆盖”是整理表格的标签笔误，相关比较实际是平台直接/外包/众包劳动身份，#119已经明确更正。
7. 本包不含其他不可见project对话、完整逐字聊天日志、隐藏推理或未获得的原绘图数据。

## 本地复算

在本包根目录执行：

```bash
python research/reproduce_examples.py --verify-package
```

命令先验证现存manifest中的文件，再打印结果。不要运行后直接覆盖已纳入manifest的文件，除非同时生成一个新的包版本。
