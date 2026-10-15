---
type: plugin-lab
stage: 5
status: ready
difficulty: 入门
estimated_minutes: 12
topics:
  - community-plugins
  - safety
  - learning-path
plugin_kind: mixed
plugins:
  - calendar
  - cm-chs-patch
  - dataview
  - obsidian-tasks-plugin
  - omnisearch
  - obsidian-local-rest-api
native_alternative:
  - core-plugins
risk_level: mixed
experiment_status: guide-ready
verified: 2026-09-02
tags:
  - playground/plugin-lab
  - playground/community
---

# 社区插件实验室

社区插件让 Obsidian 适应不同工作方式，但不是基础知识的替代品。本章始终先给出核心功能路径，再进入插件增强。

> [!important] 已安装不等于已启用
> 插件文件存在于 `.obsidian/plugins/`，只代表它已安装。只有插件 ID 出现在当前启用列表且 Restricted mode 已关闭时，代码才会运行。请以 Settings → Community plugins 的开关为准。

## 原生替代与 WorkWithLLM 历史安装快照

核心插件和普通 Markdown 是本章所有实验的原生替代，也是关闭社区插件后的可读退路。

下列清单是来源库 WorkWithLLM 编写课程时的环境快照，不是 WWL 当前状态，也不是“新手应启用的插件清单”。插件更新、启用状态和 Restricted mode 都可能变化；在 WWL 实际操作前必须以 **Settings → Community plugins** 为准，并先确认原生路径不能满足需求。

WorkWithLLM 于 2026-09-02 的只读复核坐标是：Obsidian `1.13.7`；版本来自应用包和各插件 `manifest.json`，启用列表来自该来源库的 `.obsidian/community-plugins.json`。本课程不据此推断 WWL 的插件文件、启用状态、服务运行态或高风险设置。

该 WorkWithLLM 历史快照中默认启用的社区插件为：

- `calendar`
- `cm-chs-patch`
- `dataview`
- `obsidian-tasks-plugin`
- `omnisearch`
- `obsidian-local-rest-api`

前五项用于日期导航、中文输入与检索、只读查询和 Markdown 任务。`obsidian-local-rest-api` 是来源库为其当时的协作契约保留的 **integration exception**：它不是普通新手默认推荐，不能公开端口或密钥，也不属于本课程的必做操作。

该快照中的其余插件为“已安装但默认关闭”。在 WWL 中只有先独立确认已安装、风险和原生替代后，才可按需评估；完成实验后可再次关闭。

## 推荐路线

> [!tip] 编号是稳定课程 ID，不是强制阅读顺序
> 下面的顺序是当前建议学习路线；为了不让链接因重命名失效，文件名保留稳定编号。将来调整学习顺序时修改本 MOC，不通过批量重命名改变路线。

1. [[Obsidian知识/20-功能/02-社区插件实验室/01-社区插件的安全与选型|01-社区插件的安全与选型]]：先建立信任、备份和恢复边界。
2. [[Obsidian知识/20-功能/02-社区插件实验室/03-Dataview与Bases对比|03-Dataview与Bases对比]]：理解数据与视图的区别。
3. [[Obsidian知识/20-功能/02-社区插件实验室/04-Tasks-TaskNotes与Calendar|04-Tasks-TaskNotes与Calendar]]：比较两种任务数据模型。
4. [[Obsidian知识/20-功能/02-社区插件实验室/05-Omnisearch与中文分词|05-Omnisearch与中文分词]]：比较精确搜索与相关度找回。
5. [[Obsidian知识/20-功能/02-社区插件实验室/02-Templater与QuickAdd|02-Templater与QuickAdd]]：从核心模板进入自动化。
6. [[Obsidian知识/20-功能/02-社区插件实验室/06-Advanced-Tables-Editing-Toolbar与Linter|06-Advanced-Tables-Editing-Toolbar与Linter]]、[[Obsidian知识/20-功能/02-社区插件实验室/07-LaTeX-Suite|07-LaTeX-Suite]]：写作增强。
7. [[Obsidian知识/20-功能/02-社区插件实验室/08-Excalidraw|08-Excalidraw]]、[[Obsidian知识/20-功能/02-社区插件实验室/09-PDF++|09-PDF++]]、[[Obsidian知识/20-功能/02-社区插件实验室/10-Importer|10-Importer]]：视觉、阅读与迁移。
8. [[Obsidian知识/20-功能/02-社区插件实验室/11-Obsidian-Git|11-Obsidian-Git]]、[[Obsidian知识/20-功能/02-社区插件实验室/12-Local-REST-API|12-Local-REST-API]]：高风险集成。
9. [[Obsidian知识/20-功能/02-社区插件实验室/13-插件实验报告|13-插件实验报告]]：决定哪些插件真正值得保留。

## WorkWithLLM 编写时的 17 个已安装插件

| 功能组 | 插件 ID 与 WorkWithLLM 快照版本 | WorkWithLLM 默认态 |
| --- | --- | --- |
| 查询与任务 | `dataview` 0.5.68、`obsidian-tasks-plugin` 8.4.0 | 启用安全子集 |
| 日期与中文 | `calendar` 1.5.10、`cm-chs-patch` 1.13.4、`omnisearch` 1.30.1 | 启用安全子集 |
| 自动化 | `templater-obsidian` 2.25.0、`quickadd` 2.23.0 | 已安装，默认关闭 |
| 结构化任务 | `tasknotes` 4.12.5 | 已安装，默认关闭 |
| 写作整理 | `table-editor-obsidian` 0.23.2、`editing-toolbar` 4.1.1、`obsidian-linter` 1.32.0、`obsidian-latex-suite` 1.12.8 | 已安装，默认关闭 |
| 视觉与阅读 | `obsidian-excalidraw-plugin` 2.26.4、`pdf-plus` 0.40.31 | 已安装，默认关闭 |
| 迁移与版本 | `obsidian-importer` 3.1.3、`obsidian-git` 2.39.0 | 已安装，默认关闭 |
| 外部集成 | `obsidian-local-rest-api` 5.1.0 | Baseline 集成例外；“启用”不等于已验证运行态 |

## 实验纪律

- 只操作 `Obsidian知识/30-实践/01-实验区/插件/` 中的样例或副本。
- 不运行陌生 JavaScript、系统命令、宏、Excalidraw scripts 或 LaTeX snippets。
- 不开启 AI、OCR、Webhook、外部日历、HTTP server、远端同步或自动批量格式化。
- 不展示、复制或提交 API key、token、私钥和 OAuth 数据。
- 不做删除、覆盖、全库转换和远端 push。
- 每次只启用一个新插件；记录现象后再决定是否保留。

查看完整对照：[[Obsidian知识/90-资源/02-参考/05-社区插件选型矩阵|05-社区插件选型矩阵]]。实验材料入口：[[Obsidian知识/30-实践/01-实验区/插件/05-社区插件实验室|社区插件实验区]]。

## 总成功标准

- 能说出每款插件扩展的核心功能。
- 能说明禁用插件后哪些数据仍是普通 Markdown。
- 能为一次插件实验指出风险、恢复方法和退出条件。
- 关闭非默认插件后，基础课程、链接、Properties、Bases 和任务仍可阅读。

## 禁用与恢复

实验完成后关闭临时启用的插件。插件生成的 Markdown 不会随开关自动删除；先核对 `Obsidian知识/30-实践/01-实验区/插件/` 中的精确变更，再使用 Undo、File Recovery 或本地 Git diff 恢复。不要批量删除插件目录或 `.obsidian`。

## 官方来源

- [Community plugins](https://obsidian.md/help/community-plugins)
- [Plugin security](https://obsidian.md/help/plugin-security)
- [Obsidian community releases registry](https://github.com/obsidianmd/obsidian-releases)

---

上一站：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/01-社区插件的安全与选型|01-社区插件的安全与选型]]
