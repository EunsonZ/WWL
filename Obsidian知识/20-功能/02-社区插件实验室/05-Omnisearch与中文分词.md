---
type: plugin-lab
stage: 5
status: ready
difficulty: 入门
estimated_minutes: 18
topics:
  - search
  - chinese
  - indexing
plugin_kind: search
plugins:
  - omnisearch
  - cm-chs-patch
native_alternative:
  - core/search
  - core/quick-switcher
risk_level: low
experiment_status: enabled-safe-subset
tags:
  - playground/plugin-lab
  - playground/search
---

# Omnisearch 与中文分词

## 原生替代

核心 Quick Switcher 按文件名和 alias 打开笔记；核心 Search 用引号、`path:`、`tag:`、任务和属性运算符做确定性查询。

## 安装与启用状态

WorkWithLLM 历史快照中 Omnisearch 与 Simplified Chinese Word Splitting 已安装并默认启用，HTTP API、图像/PDF/Office/OCR/AI 索引保持关闭；这不描述 WWL。若在独立测试 Vault 评估，中文分词优先使用系统引擎，并在 Settings 中逐项确认功能状态。

## 实验 A：搜索意图对照

在 `Obsidian知识/30-实践/01-实验区/插件/搜索语料/` 中完成三次查找：

1. Quick Switcher：已知标题时直接打开。
2. 核心 Search：用完整短语或属性找到精确集合。
3. Omnisearch：只记得大概词语或输入一个轻微错字时观察相关度排序。

成功标准：能说出“打开已知文件”“精确筛选”“模糊找回”分别应使用哪个入口。

## 实验 B：中文分词

在实验笔记中双击一段连续中文，比较系统默认与插件启用后的选词边界；如果使用 Vim，可比较 `w`/`b` 的中文移动。不要为了课程下载 Jieba WASM。

成功标准：中文选词更符合词语边界，且插件关闭后正文没有任何变化。

## 隐私与性能

- Omnisearch 的本地索引也包含 vault 词项，应像笔记一样视为私密数据。
- Excluded files 不是可靠的保密边界。
- 小型 playground 只索引 Markdown；移动端和大 Vault 不开启附件/OCR。
- HTTP server 会把搜索提供给外部程序，本课禁止开启。

> [!info] Jieba 是可选组件
> 可选 Jieba 会下载 WASM；桌面端会把它写入 Obsidian 的共享 `userData`，不在 Vault 内。只有确需更精确索引或自定义词典时才主动安装。

## 禁用与恢复

关闭插件不会修改 Markdown。需要清理时使用 Omnisearch 自带的 Clear cache，再等待重建；不要删除源笔记。关闭中文分词即可恢复系统选词。

## 官方来源

- [Search](https://obsidian.md/help/plugins/search)
- [Omnisearch](https://github.com/scambier/obsidian-omnisearch)
- [Simplified Chinese Word Splitting](https://github.com/AidenLx/cm-chs-patch)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/04-Tasks-TaskNotes与Calendar|04-Tasks-TaskNotes与Calendar]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/06-Advanced-Tables-Editing-Toolbar与Linter|06-Advanced-Tables-Editing-Toolbar与Linter]]
