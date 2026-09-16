---
type: qa
title: "{{title}}"
created: "{{date}} {{time}}"
status: planned
risk_level: low
tags:
  - workflow/vault-qa
---

# {{title}}

## 本次变更

- 变更范围：
- 高风险区域：
- 预期不变项：

## 自动检查

- [ ] `scripts/check-vault`
- [ ] `scripts/check-vault --semantic`（Obsidian 已运行时）
- [ ] `git diff --check`
- [ ] 扫描旧路径、乱码、绝对本机路径和凭据形态
- [ ] JSON、Canvas 与 Base 文件可以解析

## Obsidian 内检查

- [ ] 首页、书签和快速切换可达
- [ ] 新建笔记、附件、日记和核心模板进入约定目录
- [ ] Backlinks、Graph、Bases、Canvas 与嵌入可用
- [ ] 社区插件的教学配置不含凭据

## 结果

| 检查 | 结果 | 证据 | 后续 |
| --- | --- | --- | --- |
|  |  |  |  |

## 结论

- [ ] 通过
- [ ] 有已知限制，可交付
- [ ] 未通过，需要修复
