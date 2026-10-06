---
type: plugin-lab
status: ready
plugins:
  - QuickAdd
  - Templater
tags:
  - playground/plugin
  - playground/automation
---

# QuickAdd 与 Templater：手动对照

这页只解释和展示文本，不修改插件配置，也不执行宏、脚本、外部 AI 或系统命令。

## 三层能力

| 工具 | 最适合回答的问题 | 最小例子 |
| --- | --- | --- |
| Core Templates | “怎样重复插入一段固定骨架？” | 插入标题、日期和固定小节 |
| Templater | “模板内容怎样根据当前文件、日期或输入动态变化？” | 动态读取文件名、计算日期、提示输入 |
| QuickAdd | “怎样用一个入口完成捕获、建页或多个步骤？” | 把一行灵感追加到固定收件箱，或从模板创建笔记 |

## 同一个模板的写法

Core Templates 的语法较少，容易理解：

```markdown
# {{title}}

创建日期：{{date:YYYY-MM-DD}}
```

Templater 可以调用内部函数：

```markdown
# <% tp.file.title %>

创建日期：<% tp.date.now("YYYY-MM-DD") %>
```

这两个代码块只是展示语法，不会在本页自动执行。

## QuickAdd 的四种 Choice

- **Capture**：把输入追加到指定笔记或标题下。
- **Template**：按模板创建一则新笔记。
- **Macro**：顺序组合多个步骤。
- **Multi**：把多个 Choice 组织成菜单。

## 静态比较步骤

1. Core Templates 的典型结果是插入固定文本。
2. Templater 的典型结果会依赖文件名、日期或输入。
3. QuickAdd 的典型结果是通过一个入口捕获或创建内容。
4. 比较三者分别处理“内容骨架”“动态内容”和“工作流入口”。本页不要求执行任一命令。

> [!danger] 不跨过的边界
> Templater 能运行 JavaScript 和系统命令，QuickAdd Macro 也能调用脚本和外部 AI。不要从网页复制不理解的模板或脚本；本 playground 不要求开启系统命令、在线功能或 API key。

## 选择建议

- 只需要固定结构：先用 Core Templates。
- 需要日期计算、文件上下文或输入提示：再考虑 Templater。
- 需要随时捕获到固定位置，或把多步操作收进一个命令：使用 QuickAdd。
- 如果一个插件没有减少真实摩擦，就保持禁用。
