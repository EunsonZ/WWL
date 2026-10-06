---
type: plugin-lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 18
topics:
  - math
  - latex
  - snippets
plugin_kind: editing
plugins:
  - obsidian-latex-suite
native_alternative:
  - core/mathjax
risk_level: medium
experiment_status: opt-in-safe-subset
tags:
  - playground/plugin-lab
  - playground/math
---

# LaTeX Suite

## 原生替代

Obsidian 原生使用 MathJax 渲染 `$...$` 和 `$$...$$`。先手写一条分数、上下标和矩阵，理解最终文件保存的是标准 LaTeX 文本。

## 安装与启用状态

WorkWithLLM 历史快照中 LaTeX Suite 已安装、默认关闭；WWL 状态须在 Settings 中另行确认。STEM 用户可在独立测试 Vault 按需评估；其他用户可以跳过。

## 安全实验

在 `Obsidian知识/30-实践/01-实验区/插件/LaTeX/` 的公式练习中：

1. 手写 `$E=mc^2$`。
2. 使用内置 snippet 输入一个分数和一个带上下标的公式。
3. 使用 tab stop 在占位位置间移动。
4. 切到 Source mode，确认结果仍是标准 LaTeX。

成功标准：关闭 LaTeX Suite 后，已经生成的公式仍由 MathJax 正常渲染。

## 风险与限制

- 不导入来源不明的 snippets；插件的 snippet 配置可包含 JavaScript。
- 不在本课修改全局 snippet 文件或 conceal 行为。
- 中文输入法下若触发词冲突，先关闭插件或缩小触发范围。
- 插件加速输入，不改变 MathJax 能否渲染某个命令。

## 禁用与恢复

关闭插件只失去自动展开和光标增强，公式文本不变。若 snippet 展开错误，立即 Undo；不要对全文做正则替换。

## 官方来源

- [Obsidian math](https://obsidian.md/help/advanced-syntax#Math)
- [LaTeX Suite](https://github.com/artisticat1/obsidian-latex-suite)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/06-Advanced-Tables-Editing-Toolbar与Linter|06-Advanced-Tables-Editing-Toolbar与Linter]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/08-Excalidraw|08-Excalidraw]]
