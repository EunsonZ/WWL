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

1. 在 `Obsidian知识/30-实践/01-实验区/插件/Git-Demo.md` 增加一行测试文字。
2. 临时启用 Git，打开 Source Control view。
3. 观察 changed file 和 diff。
4. 打开 History view，比较现有提交历史。
5. 关闭插件，保留或用编辑器 Undo 撤销测试行。

成功标准：能识别工作区变更和历史版本；整个实验没有远端网络请求，也没有执行 discard、reset、delete repository 或 commit-and-sync。

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
- [Git plugin tips and Obsidian Sync](https://publish.obsidian.md/git-doc/Tips-and-Tricks)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/10-Importer|10-Importer]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/12-Local-REST-API|12-Local-REST-API]]
