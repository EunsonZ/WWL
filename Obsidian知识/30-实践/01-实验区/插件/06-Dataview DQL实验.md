---
type: plugin-lab
status: ready
plugin: Dataview
tags:
  - playground/plugin
  - playground/dataview
---

# Dataview：只使用 DQL 的本地查询

Dataview 会读取 Markdown 的 Properties、标签、链接和文件信息，并把查询结果渲染成动态视图。这里将 DQL 保留为静态语法样本；**没有 DataviewJS，也不执行任意 JavaScript 或查询**。

> [!info] 查询没有结果时
> 确认 Dataview 已启用，并检查目标文件夹中是否已有 Markdown 文件。DQL 查询块不会创建、删除或上传任何文件。

## 查询 `Obsidian知识/30-实践/01-实验区/数据`

下面的表格列出数据实验页的链接、类型、状态和标签。

```text
TABLE WITHOUT ID
  file.link AS "记录",
  type AS "类型",
  status AS "状态",
  file.tags AS "标签"
FROM "Obsidian知识/30-实践/01-实验区/数据"
SORT file.name ASC
```

## 查询 `30-示例项目`

下面的表格按最近修改时间列出项目内容，并读取已有的 `type`、`status` 和 `project` Properties。

```text
TABLE
  type AS "类型",
  status AS "状态",
  project AS "所属项目",
  file.mtime AS "最近修改"
FROM "30-示例项目"
SORT file.mtime DESC
LIMIT 20
```

## 观察 DQL 与 Bases 的区别

- Bases 是核心插件，适合用图形界面建立可编辑的结构化视图。
- Dataview 使用文本查询，适合把查询与笔记一起版本管理，并表达更复杂的筛选与计算。
- 查询结果是动态视图，不会把渲染后的表格写回源笔记。

## 静态阅读检查点

- 修改一份副本中的 `status` 时，动态查询通常会反映属性变化。
- 将 `LIMIT 20` 改成 `LIMIT 5` 会限制结果数。
- 增加 `WHERE status = "active"` 会筛选状态。
- 不粘贴来源不明的 `dataviewjs` 代码块。
