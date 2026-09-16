---
type: plugin-lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 26
topics:
  - tables
  - formatting
  - linting
plugin_kind: editing
plugins:
  - table-editor-obsidian
  - editing-toolbar
  - obsidian-linter
native_alternative:
  - core/markdown
  - core/properties
  - core/bases
risk_level: high
experiment_status: opt-in-sandbox-only
tags:
  - playground/plugin-lab
  - playground/editing
---

# Advanced Tables、Editing Toolbar 与 Linter

## 原生替代

先学普通 Markdown 表格与格式语法；结构化跨笔记数据优先使用 Bases；少量格式问题可手动修正或通过模板避免。

## 安装与启用状态

WorkWithLLM 历史快照中三个插件均已安装、默认关闭；WWL 状态须在 Settings 中另行确认。若在独立测试 Vault 评估，只在 `Obsidian知识/30-实践/01-实验区/插件/格式化/` 的副本上逐个开启，避免不知道是哪一个工具改写了文件。

## 实验 A：Advanced Tables

在副本中用 Tab/Enter 移动单元格，增加一行，调整列对齐，再对简单数值列排序。排序前后打开 Source mode 观察真实 Markdown，并立即练习 Undo。

成功标准：表格仍是普通 `|` 语法；能区分静态表格、Dataview 渲染表格和 Bases 视图。

> [!warning] 只操作副本
> Advanced Tables 上游仍标为 experimental，并警告 bug 可能损坏当前笔记。不要对真实数据排序、删除行列或运行复杂公式。

## 实验 B：Editing Toolbar

先亲手写粗体、列表和链接，再用最小按钮集执行相同动作，切到 Source mode 查看结果。不要使用 AI、颜色/对齐 HTML、格式刷、自定义正则或绑定高风险命令。

成功标准：知道工具栏只是生成或调用命令，不是另一种文件格式；关闭插件后 Markdown 仍正常。

## 实验 C：Linter

打开故意写乱的副本，只运行 **Lint current file**。在确认预览/差异后接受变更。保持 lint-on-save、lint-on-file-change、lint-all-files 和 custom regex 关闭。

成功标准：只修改目标副本；能用 Git diff 或 Undo 解释每一项变化。

## 禁用与恢复

关闭插件不会自动撤销已经写入的格式。若结果不理想，立即 Undo、用 File Recovery 恢复，或从本地 Git diff 还原实验文件。禁止“再跑一次全库 lint 试试”。

## 官方来源

- [Advanced Tables](https://github.com/tgrosinger/advanced-tables-obsidian)
- [Editing Toolbar](https://github.com/PKM-er/obsidian-editing-toolbar)
- [Linter](https://github.com/platers/obsidian-linter)
- [Bases](https://obsidian.md/help/bases)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/05-Omnisearch与中文分词|05-Omnisearch与中文分词]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/07-LaTeX-Suite|07-LaTeX-Suite]]
