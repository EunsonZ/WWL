---
type: lesson
stage: 4
status: ready
difficulty: 入门
estimated_minutes: 18
topics:
  - Bookmarks
  - Workspaces
  - 导航
tags:
  - playground/core-plugins
  - core/bookmarks
  - core/workspaces
---

# 06 · Bookmarks 与 Workspaces

> [!example] 两种“保存”
> Bookmarks 保存“我要快速回到哪里”；Workspaces 保存“我要以什么界面布局继续工作”。两者都不会复制或冻结笔记内容。

## 目标

- 收藏文件、文件夹、搜索、标题和块。
- 用书签组建立一个学习入口。
- 保存并切换两个任务型 Workspace。
- 区分导航快捷方式、布局快照和内容备份。

## 动手

### 1. 建立 Playground 书签组

在 Bookmarks 面板中新建 `🧭 Playground` 组，依次收藏：

- 文件：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
- 文件夹：`04-官方插件实验室`
- 搜索：先在 Search 中搜索 `tag:#playground`，再收藏查询
- 标题：收藏本页的“成功标准”
- 块：收藏下面这段带块 ID 的文字

这是一段可以被精确收藏和链接的实验文字。 ^bookmark-demo

给书签换成易读标题，拖动调整顺序，再折叠和展开书签组。

### 2. 建立“阅读”Workspace

把界面整理成：

- 中央：本页和 [[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
- 左侧：File explorer
- 右侧：Outline 与 Backlinks

运行 **Manage workspace layouts**，保存为 `01 · 阅读`。

### 3. 建立“关系探索”Workspace

重新整理：

- 中央：打开本地图谱或全局 Graph，再并排打开一篇课程
- 左侧：Search
- 右侧：Backlinks 与 Outgoing links

保存为 `02 · 关系探索`。在两个 Workspace 间来回切换，观察打开的文件、标签页、侧栏宽度和可见性如何恢复。

### 4. 更新与清理

修改 `01 · 阅读` 后用同名再次保存，验证它会更新已有布局。可再建一个临时 Workspace，并从管理界面删除它。

## 成功标准

- [ ] 我的书签组至少包含文件、搜索、标题和块
- [ ] 我知道书签不会复制源内容
- [ ] 我保存了“阅读”和“关系探索”两个 Workspace
- [ ] 我切换布局后看到了标签页和侧栏恢复
- [ ] 我能解释 Workspace 为什么不是备份

## 限制与边界

- Bookmarks 可以收藏文件、文件夹、全局 Graph、Search、标题、块和 Web 链接。
- Local Graph 不能被收藏；普通全局 Graph 可以。
- 收藏网页链接需要启用 Web viewer。
- 删除书签组会移除组内书签，但不会删除源文件。
- Workspace 只保存打开文件、标签页、侧栏宽度和可见性，不保存笔记版本。
- 同名保存会更新原 Workspace。
- `.obsidian/workspace.json` 与 `.obsidian/workspaces.json` 会随界面状态变化；在 Git 仓库中是否追踪应有明确策略，不能把它们当稳定内容文件。

## 官方文档链接

- [Bookmarks](https://obsidian.md/help/plugins/bookmarks)
- [Workspaces](https://obsidian.md/help/plugins/workspaces)
- [How Obsidian stores data](https://obsidian.md/help/data-storage)
- [Graph view](https://obsidian.md/help/plugins/graph)

---

**上一站**：[[Obsidian知识/20-功能/01-官方插件实验室/05-Bases|05-Bases]] · **下一站**：[[Obsidian知识/20-功能/01-官方插件实验室/07-Note Composer-Outline与Word Count|07-Note Composer-Outline与Word Count]] · **返回 MOC**：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
