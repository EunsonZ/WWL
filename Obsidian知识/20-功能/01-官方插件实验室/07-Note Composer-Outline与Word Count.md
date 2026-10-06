---
type: lesson
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 18
topics:
  - Note composer
  - Outline
  - Word count
tags:
  - playground/core-plugins
  - core/note-composer
  - core/outline
---

# 07 · Note Composer、Outline 与 Word Count

> [!warning] 先做副本
> Note Composer 的“合并整篇笔记”会把源笔记内容加入目标笔记，然后移除源笔记。第一次练习只在临时副本上操作，并保留确认步骤。

## 目标

- 把长笔记的一部分提取成新笔记并留下链接。
- 用 Outline 跳转和重排标题层级。
- 在状态栏观察中英文的字数与字符数。
- 识别 Note Composer 合并操作的破坏性边界。

## 动手

### 1. 创建安全的长笔记副本

新建 `_Scratch-长笔记.md`，复制下面内容：

```markdown
# 长笔记练习

## 问题

为什么要把一个过长的主题拆成多篇可链接笔记？

## 证据

独立笔记可以被其他上下文链接、嵌入和重组。

## 结论

拆分不是为了制造更多文件，而是为了让概念可以复用。
```

### 2. 提取一个小节

1. 在 Editing view 中选中“证据”标题及其段落。
2. 右键选择 **Extract current selection...**，或在命令面板搜索 Note Composer 的 Extract。
3. 在选择目标时创建一篇新笔记，例如 `可复用知识单元`。
4. 保持默认的“用链接替换原选区”行为。
5. 查看新笔记与 `_Scratch-长笔记` 的双向链接。

### 3. 用 Outline 重排结构

打开 `_Scratch-长笔记` 的 Outline：

- 点击“结论”跳到该节。
- 拖动标题改变章节顺序。
- 回到 Source mode，观察正文真实顺序也随之改变。

### 4. 观察 Word Count

在桌面端看状态栏，在移动端看右侧栏顶部：

- 记录提取前后的字数和字符数。
- 输入一段没有空格的中文，确认 Word count 支持中日韩文字。

### 5. 只阅读合并行为

**Merge current file with another file...** 会把源笔记加入目标笔记、更新指向源笔记的链接，并移除源笔记。除非你正在操作可丢弃的副本，否则不要为了完成本课执行合并。

## 成功标准

- [ ] 我在临时副本中提取了一个小节
- [ ] 原位置留下了指向新笔记的链接
- [ ] 我通过 Outline 跳转并重排过章节
- [ ] 我观察了中文内容的 Word Count
- [ ] 我知道合并会移除源笔记，因此没有在真实课程页上试验

## 限制与边界

- Note Composer 合并会移除源笔记；保留确认对话框，并先使用副本。
- 默认提取会用指向目标笔记的链接替换原选区；插件设置也可改为嵌入或不留下内容。
- Note Composer 有自己的模板变量，如 `{{content}}`、`{{fromTitle}}`、`{{newTitle}}`；不要和核心 Templates 的变量范围混为一谈。
- Outline 按标题结构工作；没有合理标题层级的长文很难导航。
- 拖动 Outline 会实际重排正文，不只是改变目录显示。
- Word count 显示统计，不会规定写作质量或目标。

## 官方文档链接

- [Note composer](https://obsidian.md/help/plugins/note-composer)
- [Outline](https://obsidian.md/help/plugins/outline)
- [Word count](https://obsidian.md/help/plugins/word-count)
- [Internal links](https://obsidian.md/help/links)

---

**上一站**：[[Obsidian知识/20-功能/01-官方插件实验室/06-Bookmarks与Workspaces|06-Bookmarks与Workspaces]] · **下一站**：[[Obsidian知识/20-功能/01-官方插件实验室/08-File Recovery与Sync边界|08-File Recovery与Sync边界]] · **返回 MOC**：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
