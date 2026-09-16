---
type: changelog
title: 2026-09-04_1519-Codex-新增NewAgents协作与知识编写指南
status: complete
scope: vault
verified: 2026-09-04
tags:
  - maintenance/log
  - maintenance/agents
  - maintenance/authoring
  - maintenance/crosslinks
---

# 2026-09-04_1519-Codex-新增NewAgents协作与知识编写指南

> [!summary] 结果
> 根目录新增 [[NewAgents.md|NewAgents.md — WorkWithLLM Agent 实践与知识编写指南]]，将 Obsidian 操作、目录归属、通用知识写作、分学科正确性规范、链接管理、目录迁移、多 Agent 协作和验证证据整理为一份可直接执行的手册。[[agents.md|agents.md]] 继续是唯一权威仓库规范；新指南明确从属于它，没有建立第二份 Baseline。

## 一、职责边界

- `agents.md` 继续规定工具、授权、安全、Git、验证和交接的硬性边界。
- `NewAgents.md` 解释怎样把这些边界落实为写前检查、知识组织、学科审校、链接设计、目录操作、证据分层和完成清单。
- 系统、开发者和用户当前指令优先于仓库文件；`NewAgents.md` 与 `agents.md` 冲突时以 `agents.md` 为准。
- 新指南没有要求所有课程机械链接到维护文档，只从根入口、贡献入口和 AI 协作工具箱提供稳定进入路径，避免污染知识 Graph。

## 二、主要内容

新指南包含：

1. 每次任务的“现场确认—任务合同—最低能力层—修改—读回—验证—交接”闭环；
2. 直接文件、原生 Obsidian CLI、GUI、Local REST API、插件与 Git 外部动作的能力分层；
3. 精确 `path=`、低输出查询、active file 禁用和 CLI 失败处理；
4. 根目录、编号、稳定课程、实践、资源、Clippings 与 Logs 的归属规则；
5. 多学科通用的粒度、教学结构、权威页、证据、不确定性、元数据、练习、代码同步和安全规范；
6. Obsidian、编程知识、计算机知识、数学、AI、哲学与文化的特别学科指南；
7. 计算机知识内部对语言与依赖、Linux、算法、系统、编译、媒体和 CUDA 的独立正确性要求；
8. 面向未来自然科学、社会科学、历史、法学、医学和语言学的扩展检查项；
9. 入站、返回、先修、应用、实现、对比和证据链接的语义规则；
10. 单文件移动、批量迁移、UTF-8 路径、配置面、删除与恢复要求；
11. 多 Agent 文件所有权、经济模型分配、作者—审校者分离和交付格式；
12. 静态、toy、CPU、GPU、真实工件与人工验收的证据等级；
13. 新增课程、新增领域、整理 Clippings、更新工具页和目录迁移的简明操作手册；
14. 修改前、内容、链接结构、代码验证、Git 与交接检查清单。

## 三、入口与 contract

以下稳定入口增加了最小连接：

- [[README.md|WorkWithLLM Knowledge Vault]]；
- [[CONTRIBUTING.md|参与维护 WorkWithLLM]]；
- [[agents.md|Agent 权威操作规范]]；
- [[Obsidian知识/90-资源/04-AI协作工具箱/00-AI协作工具箱-MOC|AI 协作工具箱]]。

`config/vault-contract.json` 将 `NewAgents.md` 与本日志加入 `requiredPaths`，使后续误删能够由检查器发现。没有把指南机械加入六个知识域的每一篇首页或课程。

## 四、写入范围与保护

本次只新增：

- `NewAgents.md`；
- 本日志。

并局部更新：

- `agents.md`；
- `README.md`；
- `CONTRIBUTING.md`；
- `Obsidian知识/90-资源/04-AI协作工具箱/00-AI协作工具箱-MOC.md`；
- `config/vault-contract.json`。

现有 `.obsidian/` 修改和删除、C++ `stl.cpp` 删除、哲学与文化原始材料、收件箱文件，以及之前尚未提交的 AI、数学、计算机知识和脚本变更均未恢复、覆盖、删除或暂存。

## 五、验证与已知限制

实际验证结果：

- `NewAgents.md` 共 989 行，包含 14 个一级主题段、当前六个知识域的特别指南、未来学科扩展规则和 33 个有效 Wikilink；
- Obsidian `outline` 成功解析完整标题层级，`backlinks` 索引到根规范、README、CONTRIBUTING、变更日志和 AI 协作工具箱五个预期入口；
- 独立格式审校确认 frontmatter、一级标题、围栏、LF/末尾换行、控制字符、行末空格、链接目标和 contract 均无本轮问题；
- 独立内容审校没有发现 P0；发现的同目录 `code-sync`/实践区边界、多 Agent 授权、局部完成与全库验收三项 P1 已按 `agents.md` 收紧；
- 内容审校提出的 MOC 入口、工具版本、随机种子和测试适用范围也已改成按内容风险触发，避免将每篇笔记强制成同一种模板；
- `config/vault-contract.json` 通过 JSON 解析；
- `scripts/check-vault` 为 `3 error / 308 warning`，`scripts/check-vault --semantic` 为 `3 error / 311 warning`；`NewAgents.md` 与本日志没有新增 error 或 warning；
- Wikilink 与文本完整性相关的 10 项单元测试通过；
- `git diff --check` 通过；
- `*.pyc`、`*.pyo`、`*.tmp`、`*.bak` 扫描为零。

完整 Vault 的 3 个既有受保护 error 来自被用户删除的 `.obsidian/community-plugins.json`（缺失与无法解析两项）和 C++ `stl.cpp` code-sync 目标（1 项）。本次没有为了得到 `0 error` 擅自恢复用户文件，也不将窄范围验证描述成全 Vault 已通过。

## 六、恢复与未执行动作

本次新增内容尚未提交。需要撤回时，应只针对上节列出的精确路径审阅和反向修改；不得对混合工作树执行 `git reset --hard`、`git clean` 或大范围 restore。

本次未执行 commit、push、添加 remote、Obsidian Sync、外部发布、插件/MCP/Local REST API 调用、联网下载或系统配置修改。
