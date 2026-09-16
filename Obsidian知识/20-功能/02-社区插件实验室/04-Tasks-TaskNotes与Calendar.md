---
type: plugin-lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 30
topics:
  - tasks
  - tasknotes
  - calendar
plugin_kind: task-management
plugins:
  - obsidian-tasks-plugin
  - tasknotes
  - calendar
native_alternative:
  - core/tasks
  - core/search
  - core/bases
  - core/daily-notes
risk_level: medium
experiment_status: split-track
tags:
  - playground/plugin-lab
  - playground/tasks
---

# Tasks、TaskNotes 与 Calendar

## 原生替代

普通 `- [ ]` checkbox、核心 Search 的 `task-todo:`、Daily Notes、日期 Properties 和 Bases 已能组成轻量任务系统。

## 安装与启用状态

以下是课程编写时的环境快照，不是进行本课的前提。实际状态以 Settings → Community plugins 为准；如果插件未启用，不要为了完成清单而启用它，先完成“原生替代”部分或在独立测试 Vault 中评估。

- WorkWithLLM 快照中的 Tasks：已安装并默认启用，JavaScript expressions 保持关闭。
- WorkWithLLM 快照中的 Calendar：已安装并默认启用，作为 Daily Notes 导航层。
- WorkWithLLM 快照中的 TaskNotes：已安装但默认关闭，进入独立进阶实验时才开启。

这些历史条目不描述 WWL；在 WWL 中先于 Settings 核对状态，再决定是否在独立测试 Vault 评估。

## 两种任务模型

```text
Tasks：任务是普通笔记中的一行 checkbox
TaskNotes：每个任务是一篇带 YAML 的 Markdown 文件
```

不要让两个插件同时管理同一批任务，也不要绑定相同的 checkbox 快捷键。

## 实验 A：Tasks

打开 [[Obsidian知识/30-实践/01-实验区/插件/04-Tasks查询实验|04-Tasks查询实验]]，在其中创建一条普通任务，再通过 Tasks UI 添加一个测试日期。观察预置 Tasks 查询，从结果勾选任务，然后回到源任务行查看变化。

成功标准：任务始终可作为普通 Markdown 阅读；查询结果勾选会准确修改唯一的源任务行。

## 实验 B：Calendar

点击已有日期打开 Daily Note；观察文字量圆点和未完成任务圆点。保留“创建前确认”，不要连续点击未来日期制造大量空文件。

成功标准：Calendar 读取核心 Daily Notes 的目录、格式和模板，而不是建立另一套日记数据库。

## 实验 C：TaskNotes 独立路线

关闭 Tasks 的实验操作，先观察 `Obsidian知识/30-实践/04-TaskNotes/Tasks/` 中四篇静态 TaskNote 的 Properties；如需新建，只在该样例目录创建一条测试 TaskNote，再打开 TaskNotes 的 Bases 列表或看板。不要转换现有 checkbox，不启用 API、MCP、Webhook、Google/Microsoft/ICS 日历或批量迁移。

> [!note] Pomodoro 统计的前置条件
> 当前 TaskNotes 的番茄钟记录保存在插件内部；`Obsidian知识/30-实践/04-TaskNotes/Views/pomodoro-stats.base` 只有在设置中把存储位置切换为 Daily Notes 后才能读取统计。此切换不是默认练习，若要体验请先记录原设置，并只在实验 Vault 中进行。

成功标准：任务是独立 `.md`，禁用 TaskNotes 后 YAML 和正文仍存在；核心 Bases 仍可读取普通属性，但插件自定义视图和交互会消失。

## 风险与恢复

- 从 Tasks 查询勾选会回写源文件。
- TaskNotes 转换可创建大量文件并永久修改原任务，课程禁止批量转换。
- Calendar 点击空日期会创建文件。
- 只删除本课创建的实验任务；恢复时优先 Undo、File Recovery 或 Git diff。

## 官方来源

- [Tasks](https://github.com/obsidian-tasks-group/obsidian-tasks)
- [TaskNotes](https://github.com/callumalpass/tasknotes)
- [Calendar](https://github.com/liamcain/obsidian-calendar-plugin)
- [Daily Notes](https://obsidian.md/help/plugins/daily-notes)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/03-Dataview与Bases对比|03-Dataview与Bases对比]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/05-Omnisearch与中文分词|05-Omnisearch与中文分词]]
