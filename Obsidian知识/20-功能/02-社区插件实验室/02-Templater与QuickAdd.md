---
type: plugin-lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 28
topics:
  - templates
  - capture
  - automation
plugin_kind: automation
plugins:
  - templater-obsidian
  - quickadd
native_alternative:
  - core/templates
  - core/daily-notes
  - core/command-palette
risk_level: high
experiment_status: opt-in-safe-subset
tags:
  - playground/plugin-lab
  - playground/automation
---

# Templater 与 QuickAdd

## 原生替代

先使用核心 Templates 的 `{{title}}`、`{{date}}`、`{{time}}`，再用 Command palette 插入模板。普通快速追加也可通过 Daily Notes、Obsidian URI 或手动编辑完成。

## 安装与启用状态

来源 WorkWithLLM 的历史课程快照中，Templater 与 QuickAdd 已安装、默认关闭；WWL 的状态须在 Settings 中独立确认。本次只导入模板和静态语法示例，未运行宏或更改设置。若另行在个人实验副本评估，不要同时开启未知自动触发配置。

## 数据模型

- Templater：在创建或插入时计算模板内容。
- QuickAdd：把 Template、Capture、Macro 和 Multi 组合成入口。
- 生成结果通常是普通 Markdown；自动化配置属于插件设置，禁用后快捷流程会消失。

## 安全实验 A：Templater 内置函数

在 `Obsidian知识/30-实践/01-实验区/插件/Templater/` 创建实验副本，只使用插件内置的日期、文件名、光标和 prompt/suggester UI。不要使用 `<%* ... %>` 执行块，不添加 `.js` 用户脚本，不启用系统命令、Startup Templates 或“新文件自动触发”。

成功标准：生成的笔记关闭 Templater 后仍是完整 Markdown，且没有外部请求或后台改写。

## 安全实验 B：QuickAdd Capture

在 QuickAdd 设置中建立一个临时 Capture：

- 目标仅为 `Obsidian知识/30-实践/01-实验区/插件/QuickAdd-Inbox.md`。
- 只允许 append。
- 文件存在时保留原内容；不覆盖。
- 不运行 Templater on entire destination file。
- 不添加 Macro、User Script、AI 或 URI callback。

运行一次，输入一行无敏感信息的文本。

成功标准：目标文件末尾只新增一段；其他文件和 Properties 不变；关闭 QuickAdd 后文本仍可读。

## 风险边界

> [!danger] 不运行陌生脚本
> Templater 可执行任意 JavaScript 和系统命令；QuickAdd User Script/Macro 可调用 Obsidian API、其他插件、Node/Electron，并批量改写文件。

- 不复制网络文章中的模板脚本。
- 不配置覆盖、删除、移动、启动宏和全局快捷键。
- 不把真实 API key 放入 QuickAdd AI 配置。
- QuickAdd 的 `data.json` 是可能承载 AI 凭据的本机状态，不应进入版本历史；需要共享教学配置时，另写脱敏样例或 Markdown 步骤。注意 `.gitignore` 只阻止新的未跟踪文件：若该路径曾经被 Git 跟踪，必须先审阅并在一次单独授权的 Git 变更中从索引移除，不能把“已加入忽略规则”误当成已经消除历史风险。
- 模板示例和真正模板文件分目录，避免示例文本被自动执行。

## 禁用与恢复

关闭两个插件后，已生成 Markdown 不受影响。删除临时 Choice 前先记录配置；若 Capture 写错位置，用 Undo、File Recovery 或 Git diff 恢复目标文件，不执行全库清理。

## 官方来源

- [Obsidian Templates](https://obsidian.md/help/plugins/templates)
- [Templater](https://github.com/SilentVoid13/Templater)
- [QuickAdd](https://github.com/chhoumann/quickadd)
- [QuickAdd Choices](https://quickadd.obsidian.guide/docs/Choices/)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/01-社区插件的安全与选型|01-社区插件的安全与选型]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/03-Dataview与Bases对比|03-Dataview与Bases对比]]
