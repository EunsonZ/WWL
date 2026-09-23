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

WorkWithLLM 历史快照中 Omnisearch 与 Simplified Chinese Word Splitting 曾列为已安装并默认启用，HTTP API、图像/PDF/Office/OCR/AI 索引保持关闭；这不描述 WWL，也不证明插件当前已实际加载。目录、启用开关、加载成功、集成设置和一次检索结果须分别核对。

`cm-chs-patch` 自 v1.8 起默认使用系统分词，主要改善编辑器双击选词和 Vim 的中文按词移动。这一默认编辑器行为不会自动为 Omnisearch 提供该插件的中文索引分词。维护者说明，测试 Omnisearch 集成还须在设置中启用相应选项，并按提示安装可选 Jieba。当前库是否具备这些条件，以本机实际检查为准。

## 实验 A：搜索意图对照

在 `Obsidian知识/30-实践/01-实验区/插件/搜索语料/` 中完成三次查找：

1. Quick Switcher：已知标题时直接打开。
2. 核心 Search：用完整短语或属性找到精确集合。
3. Omnisearch：只记得大概词语或输入一个轻微错字时观察相关度排序。

成功标准：能说出“打开已知文件”“精确筛选”“模糊找回”分别应使用哪个入口。

## 实验 B：把编辑器分词与中文检索分开

选择一个真实中文读者问题，先确定一篇应能回答问题的主解释，再准备完整短语与自然说法。搜索没有结果不证明知识不存在。

1. **编辑器分词**：在实验笔记中双击连续中文；若使用 Vim，再比较 `w` / `b` 的选词边界。这只检查编辑行为，不能据此验收搜索索引。
2. **原生 Search**：用完整短语、较短词组或明确的 `path:` / 属性条件检索，记录实际命中的主解释，保留可复现的文本查询。
3. **Omnisearch**：若已加载，可用同一问题观察结果与排序；只有另行确认中文补丁已加载、Omnisearch 集成已启用、Jieba 依赖可用及索引已更新，才把结果记录为该中文分词集成的试验。条件缺失或未知时明确记录，继续使用原生 Search；不为完成课程自动下载依赖或清缓存。

成功标准：能分清编辑器选词、原生精确查询和 Omnisearch 相关性排序各自检查什么，只记录实际运行的现象。单个问题的命中不能当作广泛中文召回率；关闭社区插件后，正文、已知路径和原生 Search 查询仍可使用。

## 隐私与性能

- Omnisearch 的本地索引也包含 vault 词项，应像笔记一样视为私密数据。
- Excluded files 不是可靠的保密边界。
- 小型 playground 只索引 Markdown；移动端和大 Vault 不开启附件/OCR。
- HTTP server 会把搜索提供给外部程序，本课禁止开启。

> [!info] 系统分词与可选 Jieba 的边界
> 维护者将 Omnisearch 集成、较精确分词、新词发现和自定义词库列为需显式启用并安装 Jieba 的场景；系统编辑器分词成功不证明这些能力可用。
>
> Jieba 安装会下载 WASM。桌面端将其写入 Obsidian 共享 `userData`，不在当前 Vault 内；移动端才写入当前库的 `.obsidian/`。先确认真实检索需要及安装授权，本课不把安装依赖当作通过条件。

## 禁用与恢复

关闭插件不会修改 Markdown。关闭中文补丁会停止其编辑器分词增强，但不能据此认定 Omnisearch 的既有索引已同步更新。需要重建索引时，先说明原因，再由操作者使用 Omnisearch 自带的 Clear cache 并等待重建；不要删除源笔记。本课不自动清缓存，也不把清理操作当作检索验证。

## 官方来源

- [Search](https://obsidian.md/help/plugins/search)
- [Omnisearch](https://github.com/scambier/obsidian-omnisearch)
- [Simplified Chinese Word Splitting](https://github.com/AidenLx/cm-chs-patch)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/04-Tasks-TaskNotes与Calendar|04-Tasks-TaskNotes与Calendar]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/06-Advanced-Tables-Editing-Toolbar与Linter|06-Advanced-Tables-Editing-Toolbar与Linter]]
