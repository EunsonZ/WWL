---
type: plugin-lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 28
topics:
  - git
  - version-control
  - backup
plugin_kind: integration
plugins:
  - obsidian-git
native_alternative:
  - core/file-recovery
  - core/sync-version-history
  - command-line-git
risk_level: high
experiment_status: opt-in-local-only
verified: 2026-09-02
tags:
  - playground/plugin-lab
  - playground/version-control
---

# Obsidian Git

## 原生替代

File Recovery 提供设备本地快照；Obsidian Sync 的版本历史属于付费同步服务；命令行 Git 提供同样的版本控制底层能力。它们分别解决恢复、同步和版本审计，不应混为一谈。

## 安装与启用状态

WorkWithLLM 历史快照中 Obsidian Git 已安装、默认关闭，且当时的来源 Vault 是没有 remote 的本地 Git 仓库；这些都不描述 WWL。本课只说明只读 status/diff/history 的教学边界；不创建 remote，不 commit、不 push/pull，不配置自动同步。

> [!note] 2026-09-02 快照边界
> WorkWithLLM 于 2026-09-02 从插件 `manifest.json` 只读确认 `obsidian-git` 版本为 `2.39.0`，并从 Git 自身确认当时没有 remote。没有读取或修改插件 `data.json`，也没有启动插件命令。“已安装、默认关闭”是有日期的来源 Vault 快照；WWL 的状态须分别在 Settings 与 Git 中复核。

## 安全观察实验

启用已有插件可能立即触发它已保存的定时提交、推送或启动拉取设置。未核验这些设置时，临时启用不能算只读观察。本练习不改变插件状态；也不直接在状态未知的 WWL 上试命令。下面的观察操作以 Git 2.51 或以上、完整存有所需对象、无 remote、无 clean/process 过滤器的独立本地练习库为前提，插件及其他同步程序未在该练习库运行。版本和前提不能核实就只阅读示例，不执行、不安装、不为本课新增服务。`--no-ext-diff/--no-textconv` 仅关闭对应外部差异转换，不能禁用属性中的所有过滤器；完整对象与 `--no-lazy-fetch` 用来排除缺对象时的按需拉取。原生命令不构成任意配置下的通用隔离边界。

1. 在已满足上述条件的独立练习库根选择自己负责、已保存且已被 Git 跟踪的练习文件，保留修改前副本；增加一行测试文字后保存。示例命令中的路径换成该文件。
2. 查看变更：`git --no-pager --no-lazy-fetch -c core.fsmonitor=false --no-optional-locks status --short`。它报告本地工作区，不执行远端同步。
3. 查看该文件差异：`git --no-pager --no-lazy-fetch -c core.fsmonitor=false --no-optional-locks diff --no-ext-diff --no-textconv -- "练习文件.md"`。禁用外部 diff/textconv 程序，避免把本地观察交给未知的配置程序。
4. 查看既有历史：`git --no-pager --no-lazy-fetch -c log.showSignature=false log -5 --oneline -- "练习文件.md"`；未提交文件可以没有自己的历史，不为得到输出创建提交。
5. 用编辑器 Undo 或对照保留的副本只撤销自己的测试行，再看该文件 diff。已有别人的修改仍保留。

成功标准：能区分工作区变更与已提交历史，并解释每条命令观察的对象。在上述明确前提下，这些观察命令不请求远端，也不执行 discard、reset、delete repository 或 commit-and-sync；其他已经运行的同步程序可能独立联网，本课不把这些程序的状态说成已核验。

## 高风险命令

> [!danger] 不把 Git 当实时同步
> `Discard changes`、`Delete repository`、pull 合并和自动 commit-and-sync 都可能造成难以恢复的改变。移动端实现官方明确标为高度不稳定。

- 不保存 PAT/password 到 Vault 或插件配置。
- 不启用 auto-commit、auto-pull、auto-push、pull on startup。
- 若使用 Obsidian Sync，Git 最好只在一台桌面设备作为备份/版本历史，并避免 Git pull 再次改写已同步文件。

## 禁用与恢复

禁用插件不会删除 `.git` 或历史。若只是实验文字，用 Undo 恢复。不要为了退出课程删除仓库。真正需要回退时先查看 diff、确认精确文件，再使用安全的版本恢复流程。

## 官方来源

- [File Recovery](https://obsidian.md/help/plugins/file-recovery)
- [Obsidian Git](https://github.com/Vinzent03/obsidian-git)
- [Git 全局选项与按需拉取](https://git-scm.com/docs/git)
- [Git 属性与过滤器](https://git-scm.com/docs/gitattributes)
- [Git 原生 diff 文档](https://git-scm.com/docs/git-diff)
- [插件的自动动作与功能](https://publish.obsidian.md/git-doc/Features)
- [Git plugin tips and Obsidian Sync](https://publish.obsidian.md/git-doc/Tips-and-Tricks)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/10-Importer|10-Importer]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/12-Local-REST-API|12-Local-REST-API]]
