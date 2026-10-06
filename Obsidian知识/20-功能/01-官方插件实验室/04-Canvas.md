---
type: lesson
stage: 4
status: ready
difficulty: 入门
estimated_minutes: 20
topics:
  - Canvas
  - JSON Canvas
  - 视觉思考
tags:
  - playground/core-plugins
  - core/canvas
---

# 04 · Canvas

> [!info] 身份卡
> Canvas 是第一方核心插件，用开放的 JSON Canvas 格式把笔记、附件、网页和文本卡片放进无限二维空间。

## 目标

- 创建一个 `.canvas` 文件。
- 添加笔记、文本、媒体与网页卡片。
- 用带方向和标签的连线表达关系。
- 理解 Canvas 文本卡片与 Markdown 文件在反向链接上的区别。

## 动手

### 1. 建立一张研究问题地图

通过 File explorer 或命令面板创建 `Canvas-研究地图.canvas`，然后加入：

- 中央：本页 `[[04-Canvas]]`
- 左侧：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
- 右侧：下一课 [[Obsidian知识/20-功能/01-官方插件实验室/05-Bases|05-Bases]]
- 一张纯文本卡片：“Canvas 是视图，Markdown 笔记是可复用知识单元”
- 一张公开网页卡片：[Canvas 官方帮助](https://obsidian.md/help/plugins/canvas)

把卡片分成三个 Group：

- Evidence
- Ideas
- Outcome

用连线连接它们，并给线加上“支持”“引出”“待验证”等标签。

### 2. 做一次反向链接对照

1. 在纯文本卡片里写 `[[05-Bases]]`。
2. 打开 `05-Bases` 的 Backlinks，观察这张纯文本卡片不会出现。
3. 右键纯文本卡片，执行 **Convert to file**。
4. 再次查看 Backlinks。

这个实验说明：空间上的文本卡片很适合临时思考，但要参与长期搜索、反链和知识网络，应该把它转换成 Markdown 文件。

### 3. 在笔记中嵌入 Canvas

在任意练习笔记中输入：

```markdown
![[Canvas-研究地图.canvas]]
```

再直接打开 Canvas，对比“嵌入预览”和“完整画布编辑”两种体验。

## 成功标准

- [ ] 我创建了一个 `.canvas` 文件
- [ ] 画布中至少有笔记卡片、文本卡片和网页或媒体卡片
- [ ] 我建立了带标签的连线和至少一个 Group
- [ ] 我验证了纯文本卡片不会进入 Backlinks
- [ ] 我把一张文本卡片转换成了文件

## 限制与边界

- 文本卡片不是 Markdown 文件，不会出现在 Backlinks；需要时用 **Convert to file**。
- Canvas 表达的是你手工布置的空间关系，不会自动推断语义关系。
- `.canvas` 使用开放的 JSON Canvas 格式，但其他应用能否支持所有显示细节取决于其实现。
- Canvas 可以嵌入笔记，但完整编辑仍应直接打开画布。
- 不要假定 Canvas 已能完整发布到 Obsidian Publish；发布支持以官方 Roadmap 和 Publish limitations 为准。

## 官方文档链接

- [Canvas](https://obsidian.md/help/plugins/canvas)
- [JSON Canvas](https://jsoncanvas.org/)
- [Embed files](https://obsidian.md/help/embeds)
- [Obsidian roadmap](https://obsidian.md/roadmap/)

---

**上一站**：[[Obsidian知识/20-功能/01-官方插件实验室/03-Daily Notes|03-Daily Notes]] · **下一站**：[[Obsidian知识/20-功能/01-官方插件实验室/05-Bases|05-Bases]] · **返回 MOC**：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]


需要查阅来源中的函数目录或 JSON 示例时，见 [[Clippings/AGoodStart101/原稿索引#普通语法参考|普通语法参考原稿]]。这些是版本相关的参考样例，核心规则以官方说明和本库实际验证为准。
