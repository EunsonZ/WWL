---
type: reference
course_role: reference
status: ready
difficulty: 入门
estimated_minutes: 15
topics:
  - terminology
  - Obsidian
tags:
  - playground/reference
  - topic/onboarding
aliases:
  - Obsidian术语表
  - 术语表
---

# Obsidian 术语表

## A–C

| 术语 | 定义与边界 |
| --- | --- |
| Alias / 别名 | `aliases` 属性中的替代名称。Quick Switcher 和内部链接建议可据此找到同一笔记；别名不会复制或创建第二篇笔记。 |
| Attachment / 附件 | Vault 内的图片、音频、PDF 等普通文件。默认位置可在 Settings → Files and links 调整；嵌入附件不等于复制附件。 |
| Backlink / 反向链接 | 从目标笔记看“哪些笔记链接到了我”的派生视图。正文只保存前向内部链接，Backlinks 是索引结果。 |
| Base / Bases | 官方核心插件提供的数据库式视图。它按属性过滤、排序和编辑文件；数据仍保存在 Markdown/Properties，视图定义保存在 `.base` 文件或代码块中。 |
| Block / 块 | 可被块链接引用的 Markdown 单元，如段落、列表项或引用。人工块 ID 写作 `^block-id`；块引用是 Obsidian 特有能力。 |
| Bookmark / 书签 | 指向文件、文件夹、搜索、标题、块、图谱或 URL 的快捷入口，不复制目标。 |
| Callout | 基于引用语法的 Obsidian 信息框，如 `> [!warning]`。类型控制视觉和图标，正文仍是文本。 |
| Canvas | 官方二维无限画布，可放笔记、附件、网页、文本卡片和连线。文本卡片不是文件，除非转换为文件，否则不出现在 Backlinks。 |
| Command / 命令 | Obsidian 或插件注册的动作。Command Palette 可搜索全部命令，Hotkeys 把某个命令绑定到按键。 |
| Command Palette / 命令面板 | `Cmd/Ctrl + P` 打开的动作搜索器，支持模糊匹配；它找动作，不负责全文检索笔记。 |
| Community plugin / 社区插件 | 经商店或手动安装的第三方代码。关闭 Restricted mode 后运行，继承 Obsidian 的访问能力；目录审核不是权限沙箱。 |
| Core plugin / 核心插件 | 随 Obsidian 内置、由官方维护并可在 Settings 中开关的功能，例如 Search、Backlinks、Canvas、Bases。 |
| CSS snippet | `.obsidian/snippets/` 中的小段样式覆盖。只改界面/渲染外观，不应承担数据逻辑；排错时需与主题一起禁用测试。 |

## D–H

| 术语 | 定义与边界 |
| --- | --- |
| Daily note / 日记 | Daily Notes 核心插件按日期创建/打开的普通 Markdown 文件；不是特殊数据库记录。 |
| Dataview | 社区查询插件。DQL 读取索引并渲染动态视图；DataviewJS/Inline JS 会执行 JavaScript，风险面更大。 |
| Embed / Transclusion / 嵌入、转嵌 | `![[目标]]` 在当前页呈现另一文件、标题、块或附件。源内容仍只有一份，修改源后各处同步显示。 |
| Editing view / 编辑视图 | 可以修改 Markdown 的视图；包含 Live Preview 和 Source mode 两种编辑模式。 |
| Excluded files / 排除文件 | Settings 中不参与某些搜索、链接建议、图谱等索引的路径模式。排除不是删除，也不是访问控制。 |
| File Recovery / 文件恢复 | 官方核心插件保留本机 Markdown/Canvas 快照。快照设备本地、保留期有限，不是完整备份。 |
| Frontmatter / YAML frontmatter | 文件最开头两条 `---` 之间的结构化属性源码。Properties 是它的图形化编辑方式。 |
| Global Graph / 全局图谱 | 显示整个 Vault 内部链接网络的 Graph view。适合总体观察；节点密度不代表知识质量。 |
| Graph view / 图谱 | 官方根据内部链接自动生成的节点与边视图。与手工排布的 Canvas 不同。 |
| Hotkey / 快捷键 | 某个命令的可配置按键。复制/粘贴等 Editing shortcuts 多由操作系统提供，未必可在 Hotkeys 中改。 |

## I–P

| 术语 | 定义与边界 |
| --- | --- |
| Internal link / 内部链接 | 指向同一 Vault 文件、标题或块的链接，通常用 `[[...]]`。它表达关系，区别于文件夹的位置关系。 |
| Link text / 显示文字 | `[[目标|显示文字]]` 中用户看到的文字，只影响这个链接实例；需要全局替代名称时用 Alias。 |
| Linked mention / 已链接提及 | Backlinks 中真正包含指向当前笔记内部链接的提及。 |
| Live Preview / 实时预览 | 编辑模式之一：光标附近显示 Markdown 标记，其余内容尽量渲染。不是 Reading view，渲染细节可能不同。 |
| Local Graph / 局部图谱 | 只显示当前笔记周围若干层链接关系的 Graph view。比全局图谱更适合实际导航。 |
| Local-first / 本地优先 | 主要数据先存在设备本地文件中。它不自动等于离线、加密、同步或备份；这些是另外的问题。 |
| Markdown | 纯文本标记格式。Obsidian 支持 CommonMark/GFM 风格基础，并加入 Wikilink、嵌入、Callout 等扩展。 |
| MOC / Map of Content | 人工编排的一篇导航笔记，把相关内容按学习/思考路径连接起来。它是实践模式，不是特殊文件类型或插件。 |
| Note / 笔记 | 通常指 Vault 内的 `.md` 文件。属性、链接和嵌入都是文件内容或索引视图，不改变其文本文件本质。 |
| Orphan / 孤立笔记 | 没有链接关系的笔记（图谱过滤中的 Orphans）。孤立不一定错误；收件箱、模板和临时记录可能有意如此。 |
| Outgoing link / 出链 | 当前笔记指向其他笔记/文件的内部链接。Outgoing Links 插件汇总它们和未解析目标。 |
| Plugin / 插件 | 向 Obsidian 注册命令、视图或处理逻辑的软件模块。核心插件和社区插件的来源、信任模型不同。 |
| Property / 属性 | 文件级结构化元数据，支持 Text、List、Number、Checkbox、Date、Date & time、Tags。底层通常是 YAML frontmatter。 |

## Q–Z

| 术语 | 定义与边界 |
| --- | --- |
| Quick Action / 快速动作 | 移动端从应用顶部下拉触发的一条可配置命令；默认打开 Command Palette。 |
| Quick Switcher / 快速切换器 | `Cmd/Ctrl + O` 按名称/别名打开或创建笔记。它不是全文 Search。 |
| Reading view / 阅读视图 | 完整渲染 Markdown 的只读呈现。与 Editing view 并列；Live Preview/Source 是编辑子模式。 |
| Ribbon / 功能区 | 桌面左侧竖排命令图标区。移动端没有相同 Ribbon，动作位于 Open menu/导航栏。 |
| Restricted mode / 受限模式 | 禁止所有社区插件运行的安全模式；已安装文件仍保留但被忽略。旧教程可能称 Safe mode。 |
| Sandbox vault / 沙盒 Vault | Obsidian 官方示例/测试 Vault 或用户另建的最小测试 Vault。用于学习和最小复现，不等于系统级安全沙箱。 |
| Search / 搜索 | 官方核心插件，支持正文、文件、路径、标签、任务、属性和正则查询。与 Quick Switcher、Omnisearch、Bases 不同。 |
| Sidebar / 侧栏 | 容纳 File explorer、Search、Backlinks、Outline 等视图的左右区域。移动端通常隐藏并通过导航打开。 |
| Source mode / 源码模式 | 编辑模式之一，持续显示 Markdown 标记；适合调试 YAML、模板和复杂语法。 |
| Sync / 同步 | 让多个设备内容趋于一致的过程或 Obsidian 官方付费服务。同步会传播正确和错误变化，不能替代独立备份。 |
| Tag / 标签 | `#tag` 或 `tags` 属性中的横向关键词，支持 `/` 嵌套。适合主题/状态聚合，不适合替代具体概念笔记。 |
| Template / 模板 | 可重复插入的笔记结构。核心 Templates 功能受限；Templater/QuickAdd 提供更强自动化但扩大风险面。 |
| Theme / 主题 | 改变整个 Obsidian 界面的 CSS 包。主题不应改变笔记语义；排错时切回默认主题。 |
| Unlinked mention / 未链接提及 | Backlinks 找到的同名文本，但正文没有内部链接。它是候选关系，不是已建立的链接。 |
| Unresolved link / 未解析链接 | 内部链接指向当前不存在或无法唯一解析的目标。它可用于“先链接、后创建”，也可能是拼写/移动错误。 |
| Vault | Obsidian 打开的一个本地文件夹及其 `.obsidian` 配置。Vault 不是账户、云端数据库或单个文件。 |
| Wikilink | `[[目标]]` 风格内部链接。简洁、适合 Obsidian；强调跨工具兼容时可在设置中改用 Markdown links。 |
| Workspace / 工作区 | 当前标签页、分栏和侧栏布局；Workspaces 核心插件可命名保存布局。工作区不是笔记内容。 |

## 三组最常混淆的对照

### 内容、关系、结构、视图

| 层 | 例子 | 真正存在哪里 |
| --- | --- | --- |
| 内容 | Markdown 正文、任务、引用 | `.md` 文件 |
| 关系 | `[[内部链接]]` | 源笔记正文；Backlinks 由索引反算 |
| 结构 | Properties、tags、文件夹 | YAML/正文/文件系统 |
| 视图 | Bases、Graph、Search、Dataview | 配置/查询；通常不复制源数据 |

### Graph、Canvas、Bases

| 工具 | 关系来源 | 适合 |
| --- | --- | --- |
| Graph | 自动读取真实内部链接 | 观察连接、发现孤立/枢纽 |
| Canvas | 用户手工空间排布和连线 | 构思、教学、规划、比较 |
| Bases | 属性过滤、排序、公式与视图 | 项目清单、阅读清单、课程目录 |

### Core、Community、Service

| 类别 | 例子 | 是否需要 Restricted mode 关闭 | 付费 |
| --- | --- | --- | --- |
| Core plugin | Backlinks、Bases、Canvas | 否 | 核心功能免费 |
| Official-maintained store plugin | Importer、Maps | 是 | 插件通常免费 |
| Community plugin | Tasks、Dataview、Templater | 是 | 各插件自行决定，多数免费 |
| Official service | Sync、Publish | 否；通过核心插件连接 | 订阅 |

## 官方参考

- [Obsidian Help](https://obsidian.md/help/)
- [Core plugins](https://obsidian.md/help/plugins)
- [Internal links](https://obsidian.md/help/links)
- [Backlinks](https://obsidian.md/help/plugins/backlinks)
- [Properties](https://obsidian.md/help/properties)
- [Mobile app](https://obsidian.md/help/mobile)
- [Plugin security](https://obsidian.md/help/plugin-security)

---

索引：[[Obsidian知识/90-资源/02-参考/00-参考索引|00-参考索引]] · 核心插件：[[Obsidian知识/90-资源/02-参考/04-核心插件目录|04-核心插件目录]] · 社区插件：[[Obsidian知识/90-资源/02-参考/05-社区插件选型矩阵|05-社区插件选型矩阵]]
