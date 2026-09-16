---
type: sop
title: Vault 质量检查 SOP
status: ready
topics:
  - quality-assurance
  - obsidian
tags:
  - workflow/sop
---

# Vault 质量检查 SOP

先插入 [[Obsidian知识/90-资源/01-模板/核心模板/Vault质量检查|Vault质量检查]]。检查强度应与改动风险成比例。

## 最小检查

```bash
scripts/check-vault
git diff --check
git status --short
```

## 涉及链接、属性、Bases 或 Canvas

在 Obsidian 正在运行时增加：

```bash
scripts/check-vault --semantic
```

然后人工打开首页、一个跨目录链接、一个 Base 和一个 Canvas。

## 涉及配置或插件

- 解析所有改动过的 JSON；
- 检查目录设置和插件内部路径；
- 确认 secret 配置被忽略、权限收紧且未输出值；
- 重载应用后确认新配置实际生效；
- 记录插件未启用或平台不支持导致的已知限制。

## 交付标准

报告具体通过项、失败项、警告和未运行项，不使用笼统的“看起来没问题”。检查失败时修复根因；教学例外只做精确 allowlist。
