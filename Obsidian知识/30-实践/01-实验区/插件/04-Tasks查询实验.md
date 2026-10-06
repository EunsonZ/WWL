---
type: plugin-lab
status: ready
plugin: Tasks
tags:
  - playground/plugin
  - playground/tasks
---

# Tasks：从 checkbox 到查询

下面前三行本质上仍是普通 Markdown checkbox。Tasks 可以在行尾增加可读的日期和重复规则，再用 `tasks` 代码块跨笔记汇总；本教学页只展示语法，不会加载查询结果。

## 普通 checkbox 与 Tasks 元数据

- [ ] 在实验区补一个双向链接 📅 2026-09-01
- [ ] 写一份插件实验报告 ⏳ 2026-09-02 📅 2026-09-03
- [ ] 每周回看一次实验记录 🔁 every week on Sunday 📅 2026-09-06
- [x] 打开 Tasks 查询实验页 ✅ 2026-08-30

尝试点击任务，或把光标放在任务行上调用 Tasks 命令。观察完成日期如何仍然保存在 Markdown 行内。

## 本实验目录中未完成的任务

```text
not done
path includes Obsidian知识/30-实践/01-实验区/插件
sort by due
```

## 本实验目录中已完成的任务

```text
done
path includes Obsidian知识/30-实践/01-实验区/插件
sort by done reverse
```

## 和 TaskNotes 比较

| 维度 | Tasks | TaskNotes |
| --- | --- | --- |
| 数据单位 | 一行 checkbox | 一则 Markdown 笔记 |
| 适合场景 | 会议行动项、日记待办、散落任务汇总 | 需要丰富属性、日历、看板与任务关系的工作 |
| 这里的样例 | 本页的 checkbox | `Obsidian知识/30-实践/04-TaskNotes/Tasks/` 中的四个静态任务笔记 |

> [!tip] 选择一种主模型
> 同一个真实任务不要同时复制成 checkbox 和 TaskNote。这里同时展示二者，是为了比较，不是要求日常重复维护。
