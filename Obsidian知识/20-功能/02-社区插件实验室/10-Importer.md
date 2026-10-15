---
type: plugin-lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 20
topics:
  - import
  - migration
  - portability
plugin_kind: official-community
plugins:
  - obsidian-importer
native_alternative:
  - core/markdown-import
  - file-copy
risk_level: medium
experiment_status: opt-in-sandbox-only
tags:
  - playground/plugin-lab
  - playground/import
---

# Importer

Importer 由 Obsidian 团队维护，但通过 Community plugins 商店分发。它不是核心插件。

## 原生替代

已有 Markdown 文件可直接复制或拖入 Vault，无需插件。Importer 适合 Notion、Evernote、Apple Notes、OneNote、Google Keep、Bear、Roam、Logseq、CSV、HTML 等需要转换的来源。

## 安装与启用状态

来源 WorkWithLLM 编写本课时将 Importer 作为已安装、默认关闭的实验插件。这是来源环境说明；WWL 的实际安装与启用状态以当前设置为准，本次没有迁入插件配置或执行导入插件。

## 随教材保留的样例

先比较 [[Obsidian知识/90-资源/03-素材/导入样本/sample.html|原 HTML 样例]] 与 [[Obsidian知识/90-资源/03-素材/导入样本/sample|Markdown 样例]] 的标题、列表和链接。阅读这两份普通文件即可理解转换前后的结构，无需执行 Importer。

## 安全实验

1. 复制课程提供的小型 HTML 或 CSV 样例，不使用真实个人导出。
2. 将输出目录设为 `Obsidian知识/30-实践/01-实验区/插件/Importer-Output/`。
3. 检查预览、附件数量和文件命名。
4. 只运行这一次小型导入。
5. 打开生成的 Markdown，检查标题、列表、链接、Properties 和附件。

成功标准：所有输出只位于指定 Sandbox；关闭 Importer 后，生成文件仍是可读 Markdown 和普通附件。

## 风险与限制

- 不把输出指向 Vault 根目录或正式知识目录。
- 不登录真实账号，不提供凭据，不从网络抓取个人资料。
- 导入可能创建大量文件、附件和链接；先小样本验证，再考虑真实迁移。
- 不把 Format Converter 的全库转换与 Importer 小样本实验混为一谈。

## 禁用与恢复

先检查输出目录中只有本课文件，再将其移入系统废纸篓或保留作对照。不要按名称模糊批量删除。禁用 Importer 不会删除已生成内容。

## 官方来源

- [Import notes](https://obsidian.md/help/import)
- [Obsidian Importer](https://github.com/obsidianmd/obsidian-importer)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/09-PDF++|09-PDF++]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/11-Obsidian-Git|11-Obsidian-Git]]
