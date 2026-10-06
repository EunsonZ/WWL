---
type: lesson
stage: 4
status: ready
difficulty: 入门
estimated_minutes: 18
topics:
  - Templates
  - 模板变量
  - Properties
tags:
  - playground/core-plugins
  - core/templates
---

# 02 · 核心 Templates

> [!info] 身份卡
> Templates 是随 Obsidian 附带的第一方核心插件。它把普通 Markdown 文件当作可插入片段；它不是第三方 Templater 插件。

## 目标

- 指定一个模板文件夹并插入模板。
- 使用官方支持的 `title`、`date`、`time` 变量。
- 在模板中安全地使用 YAML Properties。
- 区分“整页模板”和“光标处片段模板”。

## 动手

### 1. 先阅读随教材保留的核心模板

本 Vault 已提供 [[Obsidian知识/90-资源/01-模板/核心模板/基础笔记|基础笔记]] 和 [[Obsidian知识/90-资源/01-模板/核心模板/Callout片段|Callout 片段]] 等核心模板。先打开模板和 [[Obsidian知识/30-实践/01-实验区/Markdown/01-自由草稿纸|自由草稿纸]]，手工复制需要的段落，观察 YAML 与正文结构。手工复制会保留变量原文；只有当前 Templates 的目录设置已包含该模板时，才使用 **Templates: Insert template**，观察标题、日期如何被展开为静态内容。本次导入没有调整模板目录。

> [!important] 不要为了本课改写既有模板设置
> Template folder location 是整个 Vault 的设置。只有在你明确要为自己的 Vault 建立新模板目录、已经记录原目录并知道如何改回时，才调整它。本课先提供无需配置的阅读与手工复制练习；插件插入步骤以你已有的可用模板设置为前提。

### 2. 阅读一个可自定义的模板

切到 Source mode，打开“基础笔记”，观察以下结构；若在自己的独立练习 Vault 中创建模板，可从这个最小版本开始：

```markdown
---
type: learning-note
created: "{{date:YYYY-MM-DD}}"
tags:
  - playground/template
---

# {{title}}

## 我学到了什么

## 示例

## 问题

## 相关笔记

- [[]]
```

观察 `{{title}}`、`{{date:YYYY-MM-DD}}` 被插入后会变成静态文本，YAML 则在 Obsidian 中显示成 Properties。

### 3. 插入一个片段模板

若已有设置能选择该模板，把光标放到草稿中间，运行 **Templates: Insert template** 并选择“Callout片段”；否则先手工复制这个片段。Templates 不只用于创建整页，也能在光标位置复用一小段 Markdown。

### 4. 插入当前日期或时间

在命令面板搜索：

- **Templates: Insert current date**
- **Templates: Insert current time**

它们使用 Templates 设置中的日期和时间格式。

## 成功标准

- [ ] 我阅读并复制了一个模板，区分了手工复制与插件展开变量
- [ ] 在已有模板设置可用的条件下，我用插件插入了一个现成模板
- [ ] 我插入后看到了标题、日期和时间的静态结果
- [ ] 我在 Source mode 看过模板本身
- [ ] 我成功在笔记中间插入过一个片段模板
- [ ] 我没有把第三方 Templater 的语法混进核心 Templates

## 限制与边界

- 官方当前文档化的变量只有 `{{title}}`、`{{date}}`、`{{time}}` 及其格式字符串。
- 条件、循环、JavaScript、弹窗输入、自动重命名和日期运算不是核心 Templates 的官方能力。
- 不要在本课使用 Templater 的 `<% ... %>` 语法。
- 在 YAML 中给模板变量加引号，例如 `created: "{{date}}"`。
- 官方警告：在 Live Preview 中编辑模板时，Properties 面板可能覆盖未加引号的变量；模板宜在 Source mode 编辑。
- 模板插入后得到的是静态文本，不会随着模板变化或时间流逝自动更新。
- 模板 Properties 会与目标笔记已有 Properties 合并；不要把反复插入整页模板当成可靠的旧笔记更新机制。
- 把模板目录迁移到别处前，要分别检查 Templates、Daily Notes 和现有链接；它们的路径不会因为普通 Markdown 内容变化而自动推断。

## 官方文档链接

- [Templates](https://obsidian.md/help/plugins/templates)
- [Properties](https://obsidian.md/help/properties)
- [Views and editing mode](https://obsidian.md/help/edit-and-read)

---

**上一站**：[[Obsidian知识/20-功能/01-官方插件实验室/01-命令面板页面预览与文件浏览器|01-命令面板页面预览与文件浏览器]] · **下一站**：[[Obsidian知识/20-功能/01-官方插件实验室/03-Daily Notes|03-Daily Notes]] · **返回 MOC**：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
