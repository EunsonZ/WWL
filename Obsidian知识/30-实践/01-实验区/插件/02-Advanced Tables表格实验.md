---
type: plugin-lab
status: ready
plugin: Advanced Tables
tags:
  - playground/plugin
  - playground/table
---

# Advanced Tables：表格实验

先在编辑模式中把光标放进表格。原生 Obsidian 已经能创建和编辑 Markdown 表格；Advanced Tables 进一步提供 Tab/Enter 导航、行列移动、排序、对齐和公式。

## 实验一：键盘导航与自动格式化

| 实验 | 预计分钟 | 状态 |
| --- | ---: | --- |
| Markdown 基础 | 15 | 已完成 |
| 双向链接 | 20 | 进行中 |
| 查询视图 | 25 | 未开始 |

尝试：

1. 在任一单元格按 `Tab` 移到右侧单元格。
2. 在最后一个单元格按 `Tab`，观察是否自动增加新行。
3. 打开命令面板，搜索 `Advanced Tables`，尝试移动当前行或切换对齐。
4. 切换到源码模式，确认结果仍然是普通 Markdown 文本。

## 实验二：表格公式

下面的公式是表格后的 HTML 注释。把光标放在表格内，运行 **Advanced Tables: Evaluate formulas**；插件会把“总计”写入最后一格。

| 项目 | 分钟 |
| --- | ---: |
| 阅读插件说明 | 10 |
| 完成小实验 | 20 |
| 写实验报告 | 15 |
| **总计** |  |
<!-- TBLFM: @>$2=sum(@I..@-1) -->

> [!tip] 可恢复性
> 公式计算只改这张表。若结果不符合预期，使用撤销即可；不要把实验直接放进重要项目数据表。

## 观察问题

- 插件是在扩展 Markdown，还是引入只有插件才能读懂的数据？
- 关闭插件后，表格内容是否仍可读？
- 与原生表格编辑相比，哪一项操作确实更快？

