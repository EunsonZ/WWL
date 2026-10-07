---
type: lesson
stage: 4
status: ready
difficulty: 入门
estimated_minutes: 18
topics:
  - Daily notes
  - 日期属性
  - 时间工作流
tags:
  - playground/core-plugins
  - core/daily-notes
---

# 03 · Daily Notes

> [!info] 身份卡
> Daily notes 是第一方核心插件。运行命令时，今天的笔记已存在就打开，不存在才创建。

## 目标

- 配置每日笔记的位置、名称格式和模板。
- 验证同一天只会打开同一篇笔记。
- 理解 Daily template 只在首次创建时生效。
- 把 Date Property 变成通往对应 Daily note 的时间链接。

## 动手

> [!important] 这是一项会写入文件的设置练习
> 本 Vault 已有日记样例与既定的 Daily Notes 目录。为了学习本课，先阅读 [[Obsidian知识/30-实践/02-日记/2026-08-30|日记样例]]，并在其中观察模板、链接和任务；不要把本课的示例目录直接填入正在使用的 Vault 设置。只有在自己的测试 Vault 中，或已记录原设置与恢复路径时，再进行以下配置和创建步骤。

### 1. 准备 Daily template

以下只是独立测试 Vault 的教学设置：先在自己的测试 Vault 中选择或创建一个模板目录，例如 `_Templates`，再在其中新建 `每日笔记模板.md`。上一课并未创建这个目录；不要假定当前 Vault 已有它，也不要为阅读本课修改当前 Vault 的插件或目录设置。模板内容如下：

```markdown
---
type: daily
date: "{{date:YYYY-MM-DD}}"
tags:
  - daily
  - playground
---

# {{date:YYYY-MM-DD}}

## 今日重点

- [ ]

## 时间记录

- {{time:HH:mm}} 创建今日笔记

## 今天发现了什么

## 今天连接了哪些想法

- [[]]

## 明天继续

- [ ]
```

### 2. 配置并创建今天的笔记

在“设置 → 核心插件 → Daily notes”中：

- **Date format**：`YYYY-MM-DD`
- **New file location**：选择你已确认的测试目录；不要覆盖本 Vault 已配置的日记目录
- **Template file location**：选择刚才的每日笔记模板

执行 **Open today's daily note**：

1. 第一次执行时观察模板被插入。
2. 写下一行内容并关闭。
3. 再次执行同一命令。
4. 验证它打开原文件，没有生成第二份，也没有重新覆盖模板。

### 3. 用 Date Property 连回 Daily note

在另一篇普通笔记中添加 Date 类型的 `date` Property，选择今天。切到 Live Preview，点击日期，观察它指向对应 Daily note。再打开 Backlinks，看看时间入口如何加入链接网络。

> [!tip] 可选的自动子目录
> Date format 中的 `/` 会创建真实目录。比如 `YYYY/MM/YYYY-MM-DD` 会按年、月分层。初学阶段先使用单层日期，理解行为后再改。

## 成功标准

- [ ] 我阅读过一篇带模板的 Daily note；若在独立测试 Vault 中操作，也成功首次创建了带模板的 Daily note
- [ ] 我第二次运行时打开的是同一篇笔记
- [ ] 我知道 Daily template 不会回写旧日记
- [ ] 我从一篇普通笔记的 Date Property 打开了对应日记
- [ ] 我在 Backlinks 中看到了时间上下文

## 限制与边界

- Daily template 只在某日期笔记首次创建时应用。
- 修改模板不会更新已经存在的 Daily notes。
- `{{time}}` 是创建时写入的静态时间，不是动态时钟。
- 如果今天的 Daily note 已经按旧位置或旧格式存在，改变设置不会自动搬迁它。
- 日期格式里的 `/` 是真实文件夹分隔符，不只是视觉上的日期符号。
- Daily notes 不是日历界面；若需要第三方 Calendar，应在社区插件章节单独评估。

## 官方文档链接

- [Daily notes](https://obsidian.md/help/plugins/daily-notes)
- [Templates](https://obsidian.md/help/plugins/templates)
- [Properties](https://obsidian.md/help/properties)
- [Backlinks](https://obsidian.md/help/plugins/backlinks)

---

**上一站**：[[Obsidian知识/20-功能/01-官方插件实验室/02-核心 Templates|02-核心 Templates]] · **下一站**：[[Obsidian知识/20-功能/01-官方插件实验室/04-Canvas|04-Canvas]] · **返回 MOC**：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
