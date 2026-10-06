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

先亲手写粗体、列表和链接，再用最小按钮集执行相同动作，切到 Source mode 查看结果。工具栏命令作用于当前活动页：有些写入普通 Markdown，有些会插入分隔线、标题或列表标记；颜色、背景和两端/居中对齐等命令还可能写入 HTML。格式刷、清除格式、自定义命令和绑定其他插件命令会扩大实际改写面，本实验不使用它们。

成功标准：能指出本次按钮实际改动的源码字符；知道工具栏不是另一种文件格式，也不因显示为按钮而限制其能调用的命令；关闭插件后本次写入的 Markdown 仍正常。

## 实验 C：Linter

只在实验副本环境中先核对 `Lint on save`、`Lint on File Change` 和 custom commands 的既有状态。只有保存触发、文件切换/关闭触发均已关闭，且没有已配置的 custom commands 时，才继续本实验；否则记录条件不满足并不执行，不为课程修改主库或共享环境的触发配置。

执行前保留这个副本的可恢复旧版本，例如确认其已有 Git 旧版本、File Recovery 旧快照或单独保存的副本；前后 diff 只用于比较，不是恢复依据。随后只运行 **Lint current file**。这是一次对当前文件的显式命令，不等于保存时或切换/关闭文件时自动运行；也不调用 **Lint all files in the vault** 或 **Lint all files in the current folder** 等扩大范围的命令。

执行后逐项比较 YAML/frontmatter、标题、列表、空行、行尾空格、脚注、链接和表格管道。实际会变化哪些内容取决于已启用规则，不能把“格式化”说成只改空格。custom commands 会在常规规则之后另行运行，因此本实验要求其在副本环境中原本为空，而不是临时修改共享配置。

成功标准：只修改目标副本；能用前后 diff 解释每一项实际变化，并能区分“手动执行当前文件”“保存时触发”“切换/关闭文件时触发”三种覆盖范围。

## 禁用与恢复

关闭插件不会自动撤销已经写入的格式。若副本结果不理想，先查看前后 diff 识别差异；随后立即 Undo，或从执行前保留的该副本旧版本恢复。旧版本可来自已确认的 Git 版本、File Recovery 旧快照或单独保存的副本；不要把“再跑一次”或全库 lint 当作恢复操作。

## 官方来源

- [Advanced Tables](https://github.com/tgrosinger/advanced-tables-obsidian)
- [Editing Toolbar](https://github.com/PKM-er/obsidian-editing-toolbar)
- [Linter](https://github.com/platers/obsidian-linter)
- [Bases](https://obsidian.md/help/bases)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/05-Omnisearch与中文分词|05-Omnisearch与中文分词]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/07-LaTeX-Suite|07-LaTeX-Suite]]
