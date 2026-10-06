---
type: lesson
stage: 1
status: ready
difficulty: 入门
estimated_minutes: 15
topics:
  - 引用
  - 代码块
  - Callout
tags:
  - playground/markdown
  - markdown/callout
---

# 03 · 引用、代码与 Callout

## 普通引用

**源码：**

```markdown
> 写作不是把想法装进笔记，
> 而是让想法在写作中变清楚。
>
> > 引用也可以嵌套。
```

**渲染效果：**

> 写作不是把想法装进笔记，
> 而是让想法在写作中变清楚。
>
> > 引用也可以嵌套。

引用适合标记原话或上下文。若引用来自外部，请同时记录来源链接；若只是自己的提醒，Callout 往往更清晰。

## 行内代码与代码块

行内代码适合命令、属性名或短片段，例如 `Cmd/Ctrl + P` 与 `status: ready`。

**源码：**

````markdown
```python
def backlink(source, target):
    return f"{source} → {target}"
```
````

**渲染效果：**

```python
def backlink(source, target):
    return f"{source} → {target}"
```

在开头三个反引号后写语言名，可获得语法高亮。代码块中的 Markdown 不会被解析，因而也很适合展示“原始语法”。

## Obsidian Callout

Callout 是 Obsidian 在引用语法上的扩展。

**源码：**

```markdown
> [!note] 可自定义标题
> 这是普通说明。

> [!warning]- 默认折叠
> 标题后的减号让内容默认收起。

> [!question]+ 默认展开且可折叠
> 标题后的加号让内容默认展开。
```

**渲染效果：**

> [!note] 可自定义标题
> 这是普通说明。

> [!warning]- 默认折叠
> 点击标题查看被折叠的内容。

> [!question]+ 默认展开且可折叠
> 点击标题可以收起或再次展开。

常见类型包括 `note`、`abstract`、`info`、`todo`、`tip`、`success`、`question`、`warning`、`failure`、`danger`、`bug`、`example` 与 `quote`。

## 嵌套 Callout

```markdown
> [!example] 外层
> 外层内容
> > [!tip] 内层
> > 内层内容需要再加一个 `>`。
```

> [!example] 外层
> 外层内容
> > [!tip] 内层
> > 内层内容需要再加一个 `>`。

## 轮到你

在 [[Obsidian知识/30-实践/01-实验区/Markdown/01-自由草稿纸|自由草稿纸]] 新建三个 Callout：

1. 一个默认展开的 `tip`。
2. 一个默认折叠的 `warning`。
3. 一个嵌套在 `example` 里的 `question`。

---

**上一站**：[[Obsidian知识/10-基础/01-Markdown基础/02-列表任务与表格|02-列表任务与表格]] · **下一站**：[[Obsidian知识/10-基础/01-Markdown基础/04-附件媒体与数学|04-附件媒体与数学]] · **返回 MOC**：[[Obsidian知识/10-基础/01-Markdown基础/00-Markdown基础-MOC|00-Markdown基础-MOC]]
