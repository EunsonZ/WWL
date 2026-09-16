---
type: sop
title: 链接与结构审计 SOP
status: ready
topics:
  - links
  - information-architecture
tags:
  - workflow/sop
---

# 链接与结构审计 SOP

先插入 [[Obsidian知识/90-资源/01-模板/核心模板/链接审计|链接审计]]，再按“机器扫描 + Obsidian 语义 + 人工走读”三层检查。

## 第一层：文件扫描

- Wikilink、Markdown link、图片和附件目标是否存在；
- 旧目录、绝对本机路径、乱码和重复路径是否残留；
- JSON、Canvas、Base 与 frontmatter 是否可以解析；
- 同名文件是否让短 Wikilink 产生歧义。

## 第二层：Obsidian 语义

- 查看 unresolved links、outgoing links 和 backlinks；
- 逐个查询 `.base`，确认筛选、属性和卡片视图有结果；
- 打开 Canvas，检查文件节点与连线；
- 检查 Bookmarks、Templates、Daily Notes 与附件目录。

## 第三层：学习路径走读

从首页实际点击到课程、练习和下一站。关键页至少应有一个进入链接、一个相关链接和一个返回 MOC 的路径。链接数量不是目标；有解释力的连接才是。

## 结果分级

- **错误**：入口失效、真实内容不可达、查询或配置指向不存在路径。
- **警告**：孤立页、同名歧义、缺少返回路径、链接语义太弱。
- **教学例外**：故意断链必须精确列入 contract，并说明目的。
