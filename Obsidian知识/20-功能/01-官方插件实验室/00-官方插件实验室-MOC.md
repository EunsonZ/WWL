---
type: lesson
stage: 4
status: ready
difficulty: 入门
estimated_minutes: 180
topics:
  - Obsidian 核心插件
  - 本地优先
  - 官方服务边界
tags:
  - playground/core-plugins
  - learning/moc
---

# 官方插件实验室 · MOC

> [!abstract] 这一站学什么
> 这一站只使用 Obsidian 随应用附带、由官方开发和支持的核心插件。你会把同一批本地 Markdown 文件变成模板、日记、画布、数据库式视图和可切换工作台，同时分清核心插件、官方维护的社区插件，以及需要付费订阅的 Sync / Publish 服务。

## 目标

- 知道“Markdown 原生能力”“核心插件”“社区插件”“付费服务”不是同一层。
- 能通过命令面板发现功能，而不是死记全部图标。
- 完成 Templates、Daily notes、Canvas、Bases、Bookmarks 和 Workspaces 的最小闭环。
- 在执行同步、发布、全库转换或合并笔记前识别风险。

## 动手

### 先看清四层

| 层级 | 例子 | 是否要额外安装或订阅 |
| --- | --- | --- |
| 原生文件与编辑能力 | Markdown、内部链接、Properties、正文标签 | 不需要 |
| 第一方核心插件 | Canvas、Bases、Templates、Backlinks、Search | 随应用附带；可能需要在“设置 → 核心插件”启用 |
| 官方维护的社区插件 | Importer、为 Bases 提供地图视图的 Maps | 需要从社区插件商店另行安装 |
| 可选付费服务 | Obsidian Sync、Obsidian Publish | 有内置入口，但真正云端能力需要账户与订阅 |

> [!warning] 本实验室不会替你联网
> 本区不会连接远程 Vault、不会上传笔记、不会发布网站，也不会安装社区插件。涉及账号、订阅和外部数据写入的步骤只解释边界。

### 学习路线

| 顺序 | 课程 | 预计 | 重点 |
| --- | --- | ---: | --- |
| 1 | [[Obsidian知识/20-功能/01-官方插件实验室/01-命令面板页面预览与文件浏览器\|01-命令面板页面预览与文件浏览器]] | 15 分钟 | 找命令、悬停预览、管理文件 |
| 2 | [[Obsidian知识/20-功能/01-官方插件实验室/02-核心 Templates\|02-核心 Templates]] | 18 分钟 | 插入可复用的 Markdown 片段 |
| 3 | [[Obsidian知识/20-功能/01-官方插件实验室/03-Daily Notes\|03-Daily Notes]] | 18 分钟 | 用日期和模板形成时间入口 |
| 4 | [[Obsidian知识/20-功能/01-官方插件实验室/04-Canvas\|04-Canvas]] | 20 分钟 | 在开放画布上连接笔记和材料 |
| 5 | [[Obsidian知识/20-功能/01-官方插件实验室/05-Bases\|05-Bases]] | 25 分钟 | 用 Properties 建立数据库式视图 |
| 6 | [[Obsidian知识/20-功能/01-官方插件实验室/06-Bookmarks与Workspaces\|06-Bookmarks与Workspaces]] | 18 分钟 | 保存入口和任务布局 |
| 7 | [[Obsidian知识/20-功能/01-官方插件实验室/07-Note Composer-Outline与Word Count\|07-Note Composer-Outline与Word Count]] | 18 分钟 | 拆合笔记、重排章节、观察字数 |
| 8 | [[Obsidian知识/20-功能/01-官方插件实验室/08-File Recovery与Sync边界\|08-File Recovery与Sync边界]] | 20 分钟 | 区分快照、同步和备份 |
| 9 | [[Obsidian知识/20-功能/01-官方插件实验室/09-Web Viewer\|09-Web Viewer]] | 12 分钟 | 在 Obsidian 内阅读公开网页 |
| 10 | [[Obsidian知识/20-功能/01-官方插件实验室/10-更多核心插件速览\|10-更多核心插件速览]] | 16 分钟 | 建立剩余核心插件的功能地图 |

### 推荐的练习方式

1. 按 `Cmd/Ctrl+P` 打开命令面板。
2. 搜索课程中加粗显示的动作关键词；界面语言不同时，命令名称可能不同。
3. 每做完一课，勾选该页的“成功标准”。
4. 回到本页，在右侧反向链接面板观察各课程如何链接回 MOC。

## 成功标准

- [ ] 我能说出核心插件与社区插件的区别
- [ ] 我知道 Sync / Publish 的内置入口不等于免费云服务
- [ ] 我完成了至少一个本地工作流：模板、日记、Canvas 或 Base
- [ ] 我没有在不理解影响范围时执行全库转换、笔记合并、远程同步或公开发布
- [ ] 我知道所有核心插件的权威清单在哪里查看

## 限制与边界

- 核心插件虽由官方维护，但仍可被关闭；看不到命令或图标时先检查启用状态。
- 命令名称会随界面语言和已启用插件变化，因此本指南强调“搜索关键词”。
- Canvas、Bases 和 Workspaces 是视图或布局层，不会改变“Markdown 文件是主要源数据”这一事实。
- Maps 和 Importer 由 Obsidian 团队维护，但仍是社区插件，受社区插件的安装与安全模型约束。
- Sync 与 Publish 是可选付费服务；实际价格和套餐以实时官网为准。

## 官方文档链接

- [Core plugins](https://obsidian.md/help/plugins)
- [How Obsidian stores data](https://obsidian.md/help/data-storage)
- [Community plugins](https://obsidian.md/help/community-plugins)
- [Obsidian pricing](https://obsidian.md/pricing)

---

**上一站**：[[Obsidian知识/00-开始/05-Obsidian功能地图|Obsidian 功能地图]] · **下一站**：[[Obsidian知识/20-功能/01-官方插件实验室/01-命令面板页面预览与文件浏览器|01-命令面板页面预览与文件浏览器]] · **返回 MOC**：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
