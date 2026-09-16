---
type: moc
level: beginner
status: stable
module: bases
order: 0
plugins:
  - core/bases
tags:
  - playground/core/bases
aliases:
  - Bases 导航
---

# Bases 导航

> [!abstract] 一句话理解 Bases
> 笔记和属性仍保存在本地 Markdown 文件中；`.base` 文件保存过滤、列、排序与视图定义。本批 Base 只定位并读取 `Obsidian知识/` 下的教学材料；把它们当作只读导航与 schema 样本，不在此教学区修改源属性。

## 已准备的四个 Base

| Base | 数据范围 | 过滤重点 | 视图 |
| --- | --- | --- | --- |
| [[Obsidian知识/40-视图/02-Bases/课程进度.base\|课程进度]] | `Obsidian知识/` 下的课程教学材料 | 标签 + `type` | 表格、卡片 |
| [[Obsidian知识/40-视图/02-Bases/插件实验目录.base\|插件实验目录]] | `04-官方插件实验室` 与 `05-社区插件实验室` | 路径 + 标签 + 类型 | 表格、列表 |
| [[Obsidian知识/40-视图/02-Bases/示例笔记目录.base\|示例笔记目录]] | [[Obsidian知识/30-实践/01-实验区/数据/甲-晨间笔记\|甲]]、[[Obsidian知识/30-实践/01-实验区/数据/乙-阅读卡片\|乙]]、[[Obsidian知识/30-实践/01-实验区/数据/丙-项目记录\|丙]] | 路径 + 标签 | 表格、卡片 |
| [[Obsidian知识/40-视图/02-Bases/示例项目资料.base\|示例项目资料]] | 项目型样例 | 路径 + `type` | 表格、列表 |

> [!note] 空视图也是有效状态
> Base 只读取明确的教学路径。构建过程中对应材料可能尚未生成，因此暂时为空并不代表 Base 语法错误；符合既有路径、`type` 与标签条件的教学笔记出现后才会进入视图。

## 轮到你做

1. 打开 [[Obsidian知识/40-视图/02-Bases/示例笔记目录.base|示例笔记目录]]。
2. 切换“全部样例”和“样例卡片”。
3. 在表格中比较 `type`、`status`、`topics`、`fixture_reviewed`。
4. 阅读甲的源 Markdown，确认 `energy: 4` 是被 Base 显示的属性。
5. 本教学样本不要求修改属性；如在个人副本试验，先确认可回滚。
6. 打开 [[Obsidian知识/40-视图/02-Bases/示例项目资料.base|示例项目资料]]，确认只有丙。

## Base 与 Search 的分工

- Search 适合临时提问、全文命中与任务行上下文。
- Base 适合反复使用的结构化集合、列、排序、分组和卡片。
- Search 结果中的文本命中非常精确；Base 更依赖文件与属性 schema。
- 两者都引用源文件，不是副本。

## 常见问题

### 为什么刚创建的笔记没有出现

依次检查：路径是否满足 `file.inFolder(...)`；是否有要求的标签；`type` 拼写是否一致；属性值是否是期望类型；Obsidian 是否已完成索引。

### 为什么一列看起来混乱

同名属性可能被写成不同类型。例如 `progress: 40` 是数字，`progress: "40%"` 是文本。用 Properties view 检查全 vault 的属性类型，不要直接编辑 `.obsidian/types.json`。

### Base 能否代替 MOC

不能完全代替。Base 擅长按规则重组，MOC 则表达作者设计的叙事顺序、说明与取舍。本页就是 MOC，四个 `.base` 是动态目录。

## 下一步

- 学习属性：[[Obsidian知识/10-基础/03-属性标签与检索/01-属性类型|01-属性类型]]
- 学习搜索：[[Obsidian知识/10-基础/03-属性标签与检索/03-核心搜索语法|03-核心搜索语法]]
- 直接挑战：[[Obsidian知识/10-基础/03-属性标签与检索/07-检索挑战|07-检索挑战]]


> [!info] 本批语法核对范围
> 2026-09-08 对照 [Obsidian 官方说明](https://obsidian.md/help/bases/syntax) 核对核心 Bases 配置／属性类型语义；社区插件扩展和宏执行另行验证，不能以 YAML 可解析替代实际视图验收。


需要查阅来源中的函数目录或 JSON 示例时，见 [[Clippings/AGoodStart101/原稿索引#普通语法参考|普通语法参考原稿]]。这些是版本相关的参考样例，核心规则以官方说明和本库实际验证为准。
