---
type: plugin-lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 24
topics:
  - dataview
  - bases
  - properties
plugin_kind: query
plugins:
  - dataview
native_alternative:
  - core/bases
  - core/search
risk_level: low
experiment_status: enabled-safe-subset
tags:
  - playground/plugin-lab
  - playground/query
---

# Dataview 与 Bases 对比

## 原生替代

核心 Bases 能以表格、卡片和列表查看、筛选、排序、分组并直接编辑 Markdown Properties；核心 Search 适合确定性的路径、标签、任务和属性查询。

## 安装与启用状态

WorkWithLLM 历史快照中 Dataview 已安装并默认启用；WWL 的实际状态未由本课推断。本课只讨论 DQL；若在独立测试 Vault 评估 Dataview，DataviewJS 与 Inline JavaScript 应保持关闭。

## 同一份数据，两种视图

打开 `Obsidian知识/30-实践/01-实验区/插件/Dataview与Bases/` 中的样例。每篇笔记都使用普通 YAML：

```yaml
type: book
status: reading
rating: 4
```

先用核心 Base 筛选 `type == "book"`、按 `status` 分组、按 `rating` 排序。再在实验页使用普通 DQL：

````markdown
```dataview
TABLE status, rating
FROM "Obsidian知识/30-实践/01-实验区/插件/Dataview与Bases"
WHERE type = "book"
SORT rating DESC
```
````

## 观察重点

| 问题 | Bases | Dataview DQL |
| --- | --- | --- |
| 能否直接编辑属性 | 可以 | 典型查询结果主要用于展示 |
| 是否需要专用语法 | 图形 UI 为主 | 需要 DQL |
| 禁用社区插件后 | `.base` 与 Properties 仍由核心读取 | 查询块显示为普通代码块 |
| 适合什么 | 可编辑数据视图 | 聚合、计算与自定义呈现 |

## 成功标准

- Base 与 Dataview 返回同一批 book 笔记。
- 修改某篇原始笔记的 `rating` 后，两种视图都更新。
- 能解释“数据属于 Markdown，视图属于工具”。

## 风险与禁止项

普通 DQL 是本课安全子集。不要开启或运行：

- `dataviewjs` 代码块。
- `$=` Inline JS。
- 从网络复制的脚本。

DataviewJS 具有插件级权限，可改写、创建、删除文件并联网。

## 禁用与恢复

关闭 Dataview 后，YAML、标签、链接和源文件不变，只是不再渲染查询。删除实验查询块即可复原；不要删除被查询的数据文件。

## 官方来源

- [Obsidian Bases](https://obsidian.md/help/bases)
- [Dataview](https://github.com/blacksmithgu/obsidian-dataview)
- [Dataview JavaScript security note](https://github.com/blacksmithgu/obsidian-dataview#javascript-queries-security-note)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/02-Templater与QuickAdd|02-Templater与QuickAdd]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/04-Tasks-TaskNotes与Calendar|04-Tasks-TaskNotes与Calendar]]
