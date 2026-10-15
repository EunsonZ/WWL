# Start Here with TaskNotes

> [!important] Optional plugin laboratory
> TaskNotes is a community-plugin workflow, not a prerequisite for this Vault. Its commands, view files, and settings can change with the plugin version. Before enabling it or creating task notes, first read [[Obsidian知识/20-功能/02-社区插件实验室/04-Tasks-TaskNotes与Calendar|Tasks、TaskNotes 与 Calendar]], use only this sample directory, and keep one task in exactly one source-of-truth model. Do not enable integrations, webhooks, MCP/API access, or calendar connections for this exercise.

This is a static teaching fixture. It preserves a small TaskNotes tour for reading, but it neither creates tasks nor loads a TaskNotes view from this Vault.

TaskNotes works best when three things feel connected:

1. Capture a task quickly.
2. Store the task as a normal Markdown note.
3. Review tasks through Bases views.

## 静态任务样例

以下四页保留来源样例的 YAML、日期与状态作为代码文本，只用于比较任务结构；打开它们不会创建真实任务或加载任务视图。

- [[Obsidian知识/30-实践/04-TaskNotes/Tasks/01-整理Markdown示例|整理 Markdown 示例]]
- [[Obsidian知识/30-实践/04-TaskNotes/Tasks/02-验证双向链接|验证双向链接]]
- [[Obsidian知识/30-实践/04-TaskNotes/Tasks/03-完成基础上手|完成基础上手]]
- [[Obsidian知识/30-实践/04-TaskNotes/Tasks/04-准备插件复盘|准备插件复盘]]

## Read the setup as an example

```text
Enable the Obsidian Bases core plugin.
Confirm TaskNotes has created default .base files in its own Views directory.
Open the command palette and run TaskNotes: Open tasks view.
```

These are version-sensitive setup instructions from the source sample, presented as text only. This teaching area neither creates missing files nor reads a user's real TaskNotes directory.

## 1. Create a task from the command palette

The source sample suggested running **TaskNotes: Create new task**. In this Vault, treat the following as an example title only; do not create a real task from this page.

Try a title like:

```text
Review my TaskNotes setup tomorrow #admin
```

After saving, TaskNotes creates a Markdown note for that task. Open the task note and look at the YAML properties at the top. Those properties are what Bases reads for filtering, sorting, grouping, and calendar placement.

## 2. Convert inline tasks into TaskNotes

The source sample used these ordinary Markdown task lines. They are displayed as inert text here:

```text
- [ ] Create a TaskNotes inbox task due tomorrow #admin
- [ ] Schedule a 20 minute planning task for next Monday #planning
- [ ] Make a task linked to an active project note
```

After conversion, notice a few things:

- The source line can stay in this note as context.
- The actual task now lives as its own Markdown note, so it can appear in TaskNotes views.
- The converted line links to the TaskNote. Right-click that TaskNote link to open the task menu, then try changing a property such as status, priority, due date, scheduled date, or project.

## 3. Review your tasks

The source sample embedded five dynamic TaskNotes Bases views. The default files are intentionally not copied into this teaching area because their matching source files are retained once at `TaskNotes/Views/`; the embeds are shown below as non-executing syntax.

### Task list

```text
![[tasks-default.base]]
```

Use this when you want a straightforward list of everything open.

### Agenda

```text
![[agenda-default.base]]
```

Use this when you care about due dates, scheduled dates, and what needs attention soon.

### Mini calendar

```text
![[mini-calendar-default.base]]
```

Use this when you want a compact calendar alongside your notes.

### Calendar

```text
![[calendar-default.base]]
```

Use this when you want a larger calendar for scheduled work, due dates, timeblocks, and calendar events.

### Kanban

```text
![[kanban-default.base]]
```

Use this when you want to move work through statuses like open, in progress, and done.

## 4. Adjust only what gets in your way

The defaults are enough to start. Visit settings later when you know what you want to change:

- If task files are going to the wrong place, check **Settings -> TaskNotes -> General**.
- If converted inline tasks should be created somewhere else, check **Settings -> TaskNotes -> Inline Task Settings**.
- If the task modal shows too much or too little, check **Settings -> TaskNotes -> Modal Fields**.
- If your vault uses different property names, statuses, priorities, or custom fields, check **Settings -> TaskNotes -> Task Properties**.

## 5. Make it yours

Try adding one custom property to a task, such as `energy`, `client`, or `area`. Because tasks are Markdown notes, custom properties can be used in Bases without locking you into a separate task database.

## 6. Contextual views

TaskNotes can embed Bases views inside daily notes, project notes, meeting notes, or task notes. That behavior depends on the installed plugin and its active data; this fixture does not invoke it.

TaskNotes uses this pattern for the Relationships widget in task notes. When you are ready to customize views, see the TaskNotes documentation for examples.

The source sample's next-step ideas were: make a project-specific view, group by status or priority, filter tasks due this week, and inspect project backlinks. They require a separately installed TaskNotes setup and are not actions requested by this fixture.

## More help and extensions

- Documentation: [tasknotes.dev](https://tasknotes.dev/)
- Problems or bugs: [open an issue on GitHub](https://github.com/callumalpass/tasknotes/issues)
- Companion plugins:
  - [Canvas Bases](https://tasknotes.dev/companion-plugins/canvas-bases/) adds canvas-style boards and JSON Canvas snapshots for Bases views, with optional TaskNotes badges, actions, and relationship edges.
  - [TaskNotes Workflows](https://tasknotes.dev/companion-plugins/tasknotes-workflows/) adds Markdown-defined automation for TaskNotes events, schedules, manual commands, and task actions.

## Finished

Now you know the core idea: tasks are notes, properties make them queryable, and Bases turns them into views.
