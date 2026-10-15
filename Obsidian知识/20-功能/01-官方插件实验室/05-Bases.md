---
type: lesson
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 25
topics:
  - Bases
  - Properties
  - 数据库式视图
tags:
  - playground/core-plugins
  - core/bases
---

# 05 · Bases

> [!info] 身份卡
> Bases 是第一方核心插件。它给本地 Markdown 文件和 Properties 建立可编辑、可筛选、可排序的数据库式视图；Base 本身不是封闭数据库。

## 目标

- 用多篇 Markdown 笔记建立一个 Base。
- 创建 Table、Cards 和 List 三种视图。
- 从 Base 修改 Properties，并回到源文件验证。
- 理解 `.base` 保存视图配置，而数据仍在 `.md` 文件中。

## 动手

### 1. 准备三篇“书籍”笔记

在本实验室下新建 `_BasesLab` 文件夹。创建三篇不同书名的 Markdown 文件，并给每篇使用一致 Properties：

```yaml
---
type: book
status: reading
rating: 4
finished:
cover:
tags:
  - playground/book
---
```

修改每篇的 `status` 和 `rating`，让数据有差异。正文中写一句摘要，并互相建立至少一个内部链接。

### 2. 创建 Library Base

创建 `Library.base`，并在视图的 Filter 中限定：

- `file.hasTag("playground/book")`

不要跳过过滤：没有过滤条件的 Base 默认会显示整个 Vault。

建立三个视图：

1. **All**：Table，显示文件名、status、rating、finished。
2. **Gallery**：Cards，可在有图片后把 cover 设为图片来源。
3. **Reading list**：List，只显示仍在阅读的书。

### 3. 验证双向编辑

修改前记下三篇练习笔记的原始 `rating` 和 `status`，便于最后恢复。

1. 在 Table 中把一本书的 `rating` 改成另一个数字。
2. 打开对应 `.md`，切到 Source mode，观察 YAML 已改变。
3. 直接在 YAML 中修改 `status`。
4. 回到 Base，观察视图更新。
5. 添加排序、单属性分组和一个简单公式。
6. 尝试复制当前结果或导出 CSV。

### 4. 嵌入指定视图

在练习笔记中输入：

```markdown
![[Library.base]]
![[Library.base#Gallery]]
```

### 5. 退出与恢复

在设置的核心插件中关闭 Bases 后，书籍笔记的正文和 Properties 仍在原 `.md` 文件中，`Library.base` 也仍保存视图配置；只是不能继续使用 Bases 视图。重新启用 Bases 并打开同一个 `Library.base`，即可继续使用这些视图。

停用插件不会撤销之前从表格写入 YAML 的改动。要恢复练习数据，打开三篇 Markdown 笔记，将 `rating` 和 `status` 改回事先记下的原值；保留或清理自建的练习文件由你决定，不需改动其他笔记。

## 成功标准

- [ ] 我的 Base 只显示带 `playground/book` 标签的笔记
- [ ] 我创建了 Table、Cards 和 List 三种视图
- [ ] 我从 Base 修改过 Property，并在 Markdown 源文件中看到了变化
- [ ] 我从 YAML 修改过 Property，并在 Base 中看到了变化
- [ ] 我能解释 `.base` 与 `.md` 各自保存什么

## 限制与边界

- 无过滤条件时 Base 会覆盖整个 Vault；教学 Base 必须按路径、标签或类型过滤。
- 当前可以设置多个排序条件，但一次只能按一个属性分组。
- Bases 中每一行代表一个文件，不是脱离文件存在的任意数据库记录。
- Table、Cards、List 是核心布局；官方当前文档分别标示最低应用版本为 1.9、1.9、1.10。
- Map 视图最低需要 Obsidian 1.10，且需要另装 Obsidian 团队维护的 **Maps 社区插件**。Maps 虽由 Obsidian 团队维护，仍受社区插件安装、安全和更新模型约束。
- 官方当前文档标示 Kanban view 最低需要 Obsidian 1.14；官方 Roadmap 当前将它列为 Active。Calendar view 仍在 Roadmap 的 Planned 项中，不能把 Calendar 写成已交付的 Bases 布局。
- 以上是 2026-09-23 核对的官方文档和 Roadmap 状态。本批实际运行的 WWL 与临时验证库均为 Obsidian 1.13.7，不满足文档所列的 Kanban 最低版本；本课未验证 Kanban、Calendar 或 Maps，也未为这些布局升级应用或安装插件。

## 官方文档链接

- [Introduction to Bases](https://obsidian.md/help/bases)
- [Bases views](https://obsidian.md/help/bases/views)
- [Bases syntax](https://obsidian.md/help/bases/syntax)
- [Map view and Maps plugin](https://obsidian.md/help/bases/views/map)
- [Obsidian Roadmap](https://obsidian.md/roadmap/)
- [Properties](https://obsidian.md/help/properties)

---

**上一站**：[[Obsidian知识/20-功能/01-官方插件实验室/04-Canvas|04-Canvas]] · **下一站**：[[Obsidian知识/20-功能/01-官方插件实验室/06-Bookmarks与Workspaces|06-Bookmarks与Workspaces]] · **返回 MOC**：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
