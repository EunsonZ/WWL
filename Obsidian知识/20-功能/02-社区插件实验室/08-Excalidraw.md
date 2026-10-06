---
type: plugin-lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 24
topics:
  - visual-thinking
  - drawing
  - links
plugin_kind: visual
plugins:
  - obsidian-excalidraw-plugin
native_alternative:
  - core/canvas
  - mermaid
risk_level: medium
experiment_status: opt-in-safe-subset
tags:
  - playground/plugin-lab
  - playground/visual
---

# Excalidraw

## 原生替代

核心 Canvas 适合把真实笔记、附件、网页和文本卡片排成空间关系；Mermaid 适合可版本化的文本流程图。Excalidraw 的独特价值是自由手绘和视觉注释。

## 安装与启用状态

WorkWithLLM 历史快照中 Excalidraw 已安装、默认关闭；WWL 状态须在 Settings 中另行确认。若在独立测试 Vault 评估，AI、OCR/Taskbone、on-load scripts、脚本库、启动脚本、oEmbed 和远程图片应保持关闭。

## 安全实验

在 `Obsidian知识/30-实践/01-实验区/插件/Excalidraw/` 创建一张学习地图：

1. 画三个节点和两条带文字的箭头。
2. 给一个图形添加指向本 Vault 实验笔记的 Wikilink。
3. 嵌入一小段本地 Markdown。
4. 将绘图嵌回实验说明页，查看 Backlinks。

成功标准：能从绘图打开目标笔记；笔记能发现绘图的反向链接；没有发送外部请求。

## Canvas 与 Excalidraw 的边界

| Canvas | Excalidraw |
| --- | --- |
| 以笔记、附件和卡片为节点 | 以自由图形、文字和手绘为主 |
| 开放 JSON Canvas | 绘图数据主要由插件解释 |
| 适合组织材料 | 适合草图、讲解和标注 |

为增强可移植性，可在用户明确需要时配置本地 SVG/PNG 导出；不要依赖远程图片作为唯一内容。

## 风险与禁止项

- 不导入陌生 Excalidraw scripts。
- 不启用 AI/OCR，不填写 API key。
- 不让脚本在插件加载时自动执行。
- 压缩绘图并非人类友好的普通正文；重要结论仍写回 Markdown。

## 禁用与恢复

关闭插件后绘图源文件仍在，但交互编辑会消失。不要删除绘图源文件；若误改，用 Undo、File Recovery 或 Git diff 恢复。实验结束后可关闭插件。

## 官方来源

- [Canvas](https://obsidian.md/help/plugins/canvas)
- [Excalidraw for Obsidian](https://github.com/zsviczian/obsidian-excalidraw-plugin)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/07-LaTeX-Suite|07-LaTeX-Suite]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/09-PDF++|09-PDF++]]
