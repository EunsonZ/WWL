---
type: reference
course_role: reference
status: ready
difficulty: 入门
estimated_minutes: 12
topics:
  - Markdown
  - Obsidian Flavored Markdown
tags:
  - playground/reference
  - topic/markdown
aliases:
  - Markdown速查表
---

# Markdown 速查表

> [!abstract] 心智模型
> Markdown 是纯文本标记；Reading view 负责完整渲染，Live Preview 在编辑时尽量预览，Source mode 显示原始标记。Wikilink、块引用、嵌入、Callout、`%%` 注释等属于 Obsidian 扩展，跨应用前要检查兼容性。

## 最常用的 15 个写法

| 目的 | 写法 | 备注 |
| --- | --- | --- |
| 一级标题 | `# 标题` | `#` 后留空格；一篇笔记通常只需一个 H1 |
| 二级标题 | `## 小节` | 最多六级；Outline 根据标题生成 |
| 粗体 | `**重要**` | `Cmd/Ctrl + B` |
| 斜体 | `*术语*` | `Cmd/Ctrl + I` |
| 删除线 | `~~旧内容~~` | 通用 Markdown 扩展 |
| 高亮 | `==重点==` | Obsidian 扩展，跨应用可能不渲染 |
| 无序列表 | `- 项目` | `*`、`+` 也可；建议统一用 `-` |
| 有序列表 | `1. 项目` | 源码可都写 `1.`，渲染时自动编号 |
| 任务 | `- [ ] 待办` | 完成：`- [x] 已完成` |
| 引用 | `> 引用内容` | 多行时每行前加 `>` |
| 行内代码 | `` `code` `` | 适合命令、属性名和短代码 |
| 代码块 | ` ```js ... ``` ` | 开头围栏后写语言可高亮 |
| 外部链接 | `[Obsidian](https://obsidian.md)` | URL 有空格时需编码或用 `<...>` 包围 |
| 内部链接 | `[[笔记名称]]` | 输入 `[[` 后用建议列表选择 |
| 嵌入 | `![[笔记名称]]` | `!` 表示转嵌，不复制源内容 |

## 段落与换行

```md
这是第一段。段内的一次回车在严格 Markdown 中通常视为软换行。
这仍可属于同一段。

空一行后，这是第二段。
这一行末尾加两个空格（实际输入时放在行末）
可强制行内换行；也可按 Shift+Enter。
```

| 操作 | 含义 |
| --- | --- |
| `Enter` 一次 | 编辑器中新行；最终是否保留取决于 Strict line breaks 设置和上下文 |
| 空一行 | 新段落；最可靠、最便携 |
| 行尾两个空格 | Markdown 硬换行 |
| `Shift + Enter` | 直接插入行内换行；列表中可续写同一项目 |

> [!question] 为什么连续空很多行，Reading view 仍只有一个段间距？
> Markdown 会折叠多余空白。不要用空行“排版”；需要结构时用标题、列表、分隔线或 Callout。

## 标题、强调与转义

```md
# 一级标题
## 二级标题
### 三级标题

**粗体**、*斜体*、***粗斜体***、~~删除~~、==高亮==

\*这一对星号按字面显示\*
1\. 这一行不会变成编号列表
```

- 标题层级表达文档结构，不要只为字号跳级。
- 需要显示 `* _ # ` | ~` 等标记本身时，在前面加反斜杠 `\`。
- 表格单元格中的竖线要写成 `\|`。

## 列表、任务与折叠

```md
- 第一项
  - 子项
    - 更深一层
- [ ] 一个普通 Markdown 任务
- [x] 已完成任务

1. 第一步
2. 第二步
   1. 子步骤
```

- `Tab` / `Shift + Tab` 缩进或减少缩进。
- 原生任务是 Markdown 清单；截止日期、重复规则和同一 Vault 跨笔记查询不是标准 Markdown，需要 Search、Bases 或 Tasks 等插件。
- 标题和缩进列表可在编辑器中折叠；折叠状态不是正文内容。

## 链接、别名与未创建笔记

| 目的 | 写法 | 可移植性 |
| --- | --- | --- |
| 链接到笔记 | `[[Obsidian知识/10-基础/02-链接与知识网络/原子笔记/渐进式总结]]` | Wikilink；许多工具支持，但非 CommonMark 标准；完整路径还能消除同名歧义 |
| 自定义显示文字 | `[[Obsidian知识/10-基础/02-链接与知识网络/原子笔记/渐进式总结\|总结方法]]` | Obsidian/Wikilink 语法 |
| 链接到标题 | `[[来源笔记#核心观点]]` | Obsidian 扩展 |
| 链接到当前笔记标题 | `[[#核心观点]]` | Obsidian 扩展 |
| 当前 Vault 跨笔记搜索标题 | `[[##关键词]]` | 输入辅助语法，不是最终链接格式 |
| 链接到块 | `[[来源笔记#^quote-01]]` | Obsidian 特有，外部软件通常不识别 |
| 当前 Vault 跨笔记搜索块 | `[[^^关键词]]` | 输入辅助语法 |
| Markdown 内链 | `[显示文字](路径/笔记.md)` | 更便携；空格需编码为 `%20` |

未创建的 `[[链接]]` 可以先存在；点击后才创建目标笔记。若链接包含路径，如 `[[Concepts/新概念]]`，新文件会按该路径创建，而不使用默认新笔记目录。

### 人工块 ID

```md
这是希望稳定引用的一段话。 ^core-conclusion

> 结构化块（引用、Callout、列表、表格）的块 ID 单独放一行。

^example-reference
```

块 ID 只能使用拉丁字母、数字和连字符；中文可作为标题，但不建议作为人工块 ID。编辑器也能自动生成随机块 ID。

## 嵌入与附件

| 目的 | 写法 |
| --- | --- |
| 嵌入整篇笔记 | `![[笔记名称]]` |
| 嵌入某个标题 | `![[笔记名称#核心观点]]` |
| 嵌入某个块 | `![[笔记名称#^core-conclusion]]` |
| 嵌入 Vault 图片 | `![[图片.png]]` |
| 限制图片宽度 | `![[图片.png\|400]]` |
| 限制图片宽 × 高 | `![[图片.png\|640x480]]` |
| 嵌入音频或视频 | `![[audio.mp3]]`、`![[video.mp4]]` |
| 嵌入 PDF 的指定页 | `![[document.pdf#page=3]]` |
| 限制嵌入 PDF 高度 | `![[document.pdf#height=400]]` |
| 外部图片 | `![替代文字](图片URL)` |

> [!important] 嵌入不是复制
> 修改源笔记后，所有嵌入位置都会显示新内容。删除或移动附件前先查 Backlinks；在 Obsidian 内重命名/移动，才能让应用按设置更新内部链接。

尺寸是显示请求，不会重采样或压缩附件。页码和高度只影响嵌入展示；原 PDF 文件、它的许可与可访问性仍由原附件决定。

## 引用与 Callout

```md
> 普通引用
> 可以有多行。

> [!note] 自定义标题
> 这是一个提示。

> [!warning]- 默认折叠
> 点击标题后展开。

> [!example]+
> `+` 表示默认展开但允许折叠。
```

常用类型：`note`、`abstract`、`info`、`todo`、`tip`、`success`、`question`、`warning`、`failure`、`danger`、`bug`、`example`、`quote`。类型影响图标和颜色，不应代替语义清晰的标题。

## 表格

```md
| 名称 | 状态 | 评分 |
| :--- | :---: | ---: |
| 示例 A | 进行中 | 4 |
| 示例 B | 完成 | 5 |
```

- 第二行不可省略；冒号控制左、中、右对齐。
- 表格适合少量静态比较；大量结构化项目优先用属性 + Bases。
- Advanced Tables 改善编辑体验，但底层仍是 Markdown 表格；操作前保留可恢复副本。

## 代码、数学与 Mermaid

````md
行内代码：`rg --files`

```js
const answer = 42;
```

行内数学：$E = mc^2$

块级数学：
$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$

```mermaid
flowchart LR
  A[收集] --> B[整理]
  B --> C[连接]
  C --> D[回顾]
```
````

- 外层需要展示三反引号代码时，用四个或更多反引号包围。
- Source/Live Preview 与 Reading view 的代码高亮引擎可能不同；以内容正确为先。
- Mermaid 适合可版本控制的流程图；Canvas 适合自由空间构思。

## 脚注、注释与分隔线

```md
这是一个脚注引用[^source]，也是一个行内脚注。^[短说明]

[^source]: 脚注定义可放在笔记任意位置。

这段会显示，%%这段只在编辑视图显示%%。

%%
多行 Obsidian 注释。
Reading view 不显示。
%%

---
```

- YAML frontmatter 也使用 `---`，但只在文件最开头成对出现。
- 行内脚注在 Reading view 完整渲染，Live Preview 中表现可能不同。

## Properties / YAML frontmatter

```yaml
---
type: concept
status: seed
created: 2026-08-30
fixture_reviewed: false
rating: 4
topics:
  - learning
  - note-taking
related:
  - "[[Obsidian知识/10-基础/02-链接与知识网络/原子笔记/渐进式总结]]"
tags:
  - topic/learning
aliases:
  - 渐进总结
---
```

- 属性区必须从文件第一行开始。
- 同一属性名在 Vault 中应保持同一类型。
- 属性中的内部链接要加引号；列表中的每个链接各占一项。
- 日期使用 ISO `YYYY-MM-DD`；复选框使用 `true` / `false`。
- 不要使用已弃用的 `tag`、`alias`、`cssclass`；使用 `tags`、`aliases`、`cssclasses`。
- 详细规范见 [[Obsidian知识/90-资源/02-参考/03-属性字典|03-属性字典]]。

## 兼容性分层

| 层级 | 典型语法 | 离开 Obsidian 后 |
| --- | --- | --- |
| 基础 Markdown | 标题、强调、列表、引用、代码、外链 | 通常可读、可渲染 |
| 常见扩展 | 表格、任务、删除线、脚注、数学 | 多数 Markdown 工具支持，细节可能不同 |
| Obsidian Flavored Markdown | Wikilink、嵌入、Callout、`%%` 注释、高亮 | 文件仍是文本，但目标软件可能显示源码 |
| Obsidian 特有引用 | 标题/块链接、块 ID、当前 Vault 标题搜索 | 通常需要 Obsidian 才能完整工作 |

## 常见错误

| 症状 | 检查 |
| --- | --- |
| 标题没有生效 | `#` 后是否有空格；是否仍在代码块中 |
| 列表断掉 | 列表符号后是否有空格；缩进是否一致 |
| 表格错列 | 单元格内容中的 `|` 是否写成 `\|` |
| 内链未解析 | 名称/路径是否准确；文件是否被排除；是否存在同名笔记 |
| 嵌入只显示链接 | 是否漏了前导 `!` |
| Callout 显示为普通引用 | 第一行是否严格为 `> [!type]` |
| YAML 变红或属性异常 | 是否从文件首行开始；冒号后是否有空格；内部链接是否加引号 |
| 单回车在阅读视图消失 | 使用空行分段、行尾双空格或 `Shift+Enter`；检查 Strict line breaks |

## 官方参考

- [Basic formatting syntax](https://obsidian.md/help/syntax)
- [Advanced formatting syntax](https://obsidian.md/help/advanced-syntax)
- [Internal links](https://obsidian.md/help/links)
- [Embed files](https://obsidian.md/help/embeds)
- [Callouts](https://obsidian.md/help/callouts)
- [Properties](https://obsidian.md/help/properties)
- [Attachments](https://obsidian.md/help/attachments)

---

索引：[[Obsidian知识/90-资源/02-参考/00-参考索引|00-参考索引]] · 去练习：[[Obsidian知识/10-基础/01-Markdown基础/00-Markdown基础-MOC|00-Markdown基础-MOC]] · 搜索：[[Obsidian知识/90-资源/02-参考/02-搜索语法速查表|02-搜索语法速查表]]
