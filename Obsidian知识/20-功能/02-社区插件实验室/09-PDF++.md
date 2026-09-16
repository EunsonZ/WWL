---
type: plugin-lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 24
topics:
  - pdf
  - annotations
  - backlinks
plugin_kind: reading
plugins:
  - pdf-plus
native_alternative:
  - core/pdf-viewer
  - core/attachments
risk_level: high
experiment_status: opt-in-copy-only
tags:
  - playground/plugin-lab
  - playground/pdf
---

# PDF++

## 原生替代

核心 PDF Viewer 已能打开、搜索、嵌入 PDF，并用 `#page=N` 指向页码。普通附件和 Wikilink 足以完成基础阅读引用。

### 原书、页码与笔记各保存什么

若把原书 PDF 复制到 Vault，先确定它是这份材料在本 Vault 中的唯一权威副本；资源索引或配套阅读笔记记录作者、版本、阅读状态和关联主题。不要同时维护两份看似相同、却可能分别被改动的原书。

页码链接只定位证据，不能代替解释。可以在阅读笔记中写：

```markdown
> ![[原书.pdf#page=17]]

这页提出了什么？它支持或限制哪个概念？
```

需要限制嵌入高度时可使用 `![[原书.pdf#height=500]]`。页码、版本或链接失效时，应报告定位无法复核，而不是据此把原文改写成确定结论。这里的“原书”和阅读笔记是不同角色：PDF 保留原始材料，Markdown 保存页码、自己的解释、反例和后续链接。

> [!info] 核验范围（2026-09-08）
> [官方 Embed files 文档](https://obsidian.md/help/embeds)已核对本节使用的核心嵌入语法，包括 PDF 的 `#page=N` 与 `#height=N`。本次未运行 PDF++，因此没有核对其选区链接、反向链接高亮或其他插件行为。

> [!note] 阅读顺序
> 可先判断材料是否与当前问题有关；再检查方法、样本、测量、结果和局限；最后关掉 PDF，用自己的话写一句结论、最强证据与最大限制，再打开原文核对。这个流程帮助区分高亮、摘录和可复核的判断。

## 安装与启用状态

WorkWithLLM 历史快照中 PDF++ 已安装、默认关闭；WWL 状态须在 Settings 中另行确认。若在独立测试 Vault 评估，只在 `Obsidian知识/30-实践/01-实验区/插件/PDF/` 的无敏感信息 PDF 副本上临时启用；直接 PDF 写入、Page Composer 和自定义 JavaScript 模板应保持关闭。

## 安全实验

1. 用核心 Viewer 打开样例 PDF，建立一个页码链接。
2. 启用 PDF++ 后选中一句测试文本，复制为带页码/选区位置的链接。
3. 将链接粘贴到实验笔记的 callout 中。
4. 从 Markdown 点击回到原位置，再观察 PDF 对应的 Backlinks。

成功标准：能完成“来源选区 → Markdown 笔记 → 回到原文”的往返；原始 PDF 文件内容不被修改。

## 风险与限制

- PDF++ 可以直接写注释、删除注释和操作页面；这些能力可能损坏 PDF，本课禁止。
- 自定义复制模板表达式可执行 JavaScript，不使用网络示例。
- PDF 链接可移植到普通文件层面，但精确选区交互依赖 Obsidian/PDF++。
- 不在真实文献唯一副本上实验。

## 禁用与恢复

关闭 PDF++ 后 Markdown 链接仍保留，插件增强定位和工具栏会消失。若误写 PDF，立即停止编辑，从实验副本重新复制；不要继续执行批量修复或页面删除。

## 官方来源

- [Embed files and PDF pages](https://obsidian.md/help/embeds)
- [PDF++](https://github.com/RyotaUshio/obsidian-pdf-plus)
- 原稿中的个人知识系统与 PDF 工作流讨论：[[Clippings/AGoodStart101/Obsidian1|Obsidian1]]（本页只采用其组织与阅读建议；软件行为以官方文档为准）

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/08-Excalidraw|08-Excalidraw]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/10-Importer|10-Importer]]
