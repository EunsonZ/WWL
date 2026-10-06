# Obsidian 从零入门：一套简单、规范、能长期扩展的使用方法

这次先不从插件开始。先把最基础的笔记创建、Markdown、图片、表格、链接、属性和数据库视图真正用顺。否则笔记还没写几篇，插件设置先繁殖成了一个小型行政机构。

下面以桌面版为主，按截至 **2026 年 8 月 30 日**的 Obsidian 官方中英文帮助编写。Windows/Linux 使用 `Ctrl`，macOS 对应使用 `Cmd`。

最终要建立的不是复杂的“第二大脑”，而是下面这个简单闭环：

```text
快速创建笔记
    ↓
写清楚主要结论
    ↓
插入图片、表格和来源
    ↓
用内部链接连接相关知识
    ↓
用 Properties 保存结构化字段
    ↓
用 Bases 自动生成文献表、项目表
    ↓
定期处理 Inbox
```

---

# 一、先理解 Obsidian 中的三种东西

在真正动手之前，先分清三个概念。

## 1. Vault：仓库

Vault 本质上就是计算机上的一个普通文件夹。

这个文件夹中包含：

```text
Markdown 笔记
图片
PDF
音频
白板
数据库视图
Obsidian 设置
```

它不是某种神秘的云端封闭数据库。Obsidian 的主要笔记是普通 `.md` 文件，图片和 PDF 也是普通文件，所以即使以后不用 Obsidian，内容仍能被其他软件访问。([Obsidian](https://obsidian.md/help/Files%20and%20folders/Manage%20vaults?utm_source=chatgpt.com "Manage vaults - Obsidian Help"))

## 2. Note：笔记

一篇 Obsidian 笔记，就是一个 Markdown 文件，例如：

```text
认知负荷理论.md
毕业论文.md
2026-08-30.md
Smith 2025 - Working Memory.md
```

通常界面不会显示 `.md` 后缀，但文件实际存在于你的仓库文件夹中。

## 3. Attachment：附件

图片、PDF、音频、视频等不是写进 Markdown 文件本身，而是作为独立文件保存在 Vault 中，然后被笔记引用或嵌入。

例如：

```markdown
![[认知负荷-实验流程-01.png]]
```

这行文字的意思是：在当前位置显示那张图片。

---

# 二、第一件事不是写笔记，而是建立最小规范

规范过少，内容膨胀后会混乱；规范过多，你会每天维护分类系统，仿佛笔记需要接受户籍管理。

推荐只建立以下七个文件夹：

```text
00-Inbox
10-Daily
20-Notes
30-Projects
40-Sources
90-Attachments
99-Templates
```

它们分别负责：

|文件夹|放什么|
|---|---|
|`00-Inbox`|刚创建、尚未整理的笔记|
|`10-Daily`|每日记录|
|`20-Notes`|概念、方法、观点、知识笔记|
|`30-Projects`|有明确目标和结果的项目|
|`40-Sources`|论文、书籍、网页、课程等来源笔记|
|`90-Attachments`|图片、PDF、音频等附件|
|`99-Templates`|笔记模板|

数字前缀只是为了让文件夹始终按照固定顺序排列。

初期不要再增加“心理学、统计学、计算机科学、课程、研究、阅读”之类的多层目录。一个知识点可能同时属于多个学科，而文件夹只能把它塞进一个地方。文件夹树并不会因为长得像大学院系网站，就自动产生知识。

---

## 1. 文件夹、属性和链接分别负责什么

这是整套规范里最重要的一条：

```text
文件夹：表示笔记是什么类型、处于什么位置
属性：表示可筛选和排序的结构化信息
链接：表示知识之间有什么关系
正文：保存解释、证据和推理
```

例如，一篇论文笔记：

```text
文件夹：40-Sources
属性：type=source，year=2025，status=active
链接：[[工作记忆]]、[[认知负荷]]
正文：研究问题、方法、结果、局限
```

不要同时使用文件夹、标签、属性和文件名前缀表示同一件事。例如下面这种写法毫无必要：

```text
40-Sources/论文/#论文/type: paper/PAPER-Smith-2025.md
```

这不是严谨，是同一个分类被重复登记了四次。

---

## 2. 笔记命名规范

文件名应当做到三点：

```text
看见名字就知道内容
容易搜索
多年后仍然成立
```

### 知识笔记

使用明确的概念、问题或结论：

```text
贝叶斯更新
认知负荷会降低复杂任务表现
选择偏差
混合效应模型中的随机斜率
```

避免：

```text
一些想法
学习笔记
重要内容
笔记1
今天想到的
```

### 项目笔记

直接使用项目名称：

```text
毕业论文
心理统计课程期末项目
睡眠与记忆实验
Obsidian 学习计划
```

### 来源笔记

推荐格式：

```text
作者 年份 - 简短标题
```

例如：

```text
Sweller 1988 - Cognitive Load During Problem Solving
Smith 2025 - Sleep Restriction and Memory
周志华 2016 - 机器学习
```

### 每日笔记

统一使用：

```text
YYYY-MM-DD
```

例如：

```text
2026-08-30
```

这种格式按文件名排序时，也会按照时间自然排序。

### 避免特殊字符

笔记标题中最好避免：

```text
# | ^ : %% [[ ]]
```

这些字符在 Obsidian 链接语法中有特殊含义，可能造成链接解析问题。([Obsidian](https://obsidian.md/zh/help/links "内部链接 - Obsidian 中文帮助"))

---

## 3. 一篇笔记解决一个主要问题

不必把每个句子拆成所谓“原子笔记”。那会把正常写作变成笔记碎纸机。

更实用的原则是：

> 一篇笔记应当有一个明确的主问题、主概念或主结论。

例如：

```text
认知负荷理论
```

可以包含：

```text
定义
三种负荷类型
测量方式
支持证据
争议和局限
相关理论
```

但不应同时塞入：

```text
认知负荷理论
本周课程安排
Python 安装方法
导师会议记录
晚餐购物清单
```

人类确实有能力把任何容器变成杂物抽屉，Obsidian 也不例外。

---

# 三、创建 Vault 和文件夹

## 1. 创建 Vault

打开 Obsidian 后：

1. 点击左下角的 Vault 图标。
    
2. 选择“管理仓库”。
    
3. 在“创建新仓库”右侧点击“创建”。
    
4. 输入仓库名称，例如：
    

```text
Knowledge
Research
学习与研究
```

5. 选择存储位置。
    
6. 点击创建。
    

Vault 就是那个实际文件夹。不要在一个 Vault 里面再创建另一个 Vault。([Obsidian](https://obsidian.md/help/Files%20and%20folders/Manage%20vaults?utm_source=chatgpt.com "Manage vaults - Obsidian Help"))

## 2. 创建文件夹

在左侧文件列表顶部点击“新建文件夹”，依次建立：

```text
00-Inbox
10-Daily
20-Notes
30-Projects
40-Sources
90-Attachments
99-Templates
```

也可以右键某个文件夹，在其中新建子文件夹、笔记或数据库。左侧文件浏览器支持创建、删除、重命名、拖放和移动文件。([Obsidian](https://obsidian.md/help/plugins/file-explorer?utm_source=chatgpt.com "File explorer - Obsidian Help"))

初期只建议在两个地方建立子文件夹：

```text
30-Projects/_Archive
40-Sources/_Archive
```

而且可以等真正出现已完成内容后再创建。

---

# 四、第一次使用前，把这些设置调整好

点击左下角齿轮进入“设置”。

## 1. 编辑器设置

进入：

```text
设置 → 编辑器
```

建议设置：

```text
新标签页默认视图：编辑视图
默认编辑模式：实时预览
显示行内标题：开启
自动配对 Markdown 语法：开启
智能列表：开启
```

“实时预览”让你一边输入 Markdown，一边看到接近最终效果的内容。

开启“显示行内标题”后，文件名会显示在笔记顶部，充当 Obsidian 中的视觉标题，但这个标题不会真正写入 Markdown 文件。([Obsidian](https://obsidian.md/help/settings?utm_source=chatgpt.com "Settings - Obsidian Help"))

因此，本指南采用以下规则：

```text
文件名 = 笔记标题
正文从二级标题 ## 开始
```

例如文件名是：

```text
认知负荷理论
```

正文写：

```markdown
## 一句话结论

## 核心机制

## 证据

## 局限
```

不必再重复写：

```markdown
# 认知负荷理论
```

需要将笔记单独导出为正式 Markdown 文档时，再补一个一级标题即可。

---

## 2. 文件与链接设置

进入：

```text
设置 → 文件与链接
```

设置如下：

```text
新建笔记的默认位置：
指定文件夹 → 00-Inbox
```

这样，使用快捷方式创建的新笔记会先进入 Inbox，而不是散落在仓库根目录。

附件设置：

```text
附件默认存放位置：
指定的附件文件夹 → 90-Attachments
```

链接设置：

```text
新链接格式：尽可能使用最短路径
使用 [[Wiki 链接]]：开启
自动/始终更新内部链接：开启
```

自动更新内部链接开启后，当你重命名或移动一篇笔记时，Obsidian 会更新指向它的内部链接。Wiki 链接比普通 Markdown 链接更短，也更适合初学者直接输入。([Obsidian](https://obsidian.md/help/settings?utm_source=chatgpt.com "Settings - Obsidian Help"))

删除设置建议选择：

```text
移动到系统回收站
```

或者：

```text
移动到 Obsidian 回收站
```

不要设置成永久删除。人的误操作能力，通常比自己的记忆力可靠得多。

---

## 3. 开启本指南要使用的核心插件

进入：

```text
设置 → 核心插件
```

确保开启：

```text
文件列表
搜索
快速切换
命令面板
反向链接
出链
大纲
属性列表
模板
数据库（Bases）
日记
文件恢复
```

这些都是 Obsidian 自带的核心功能，不需要从社区插件市场安装。([Obsidian](https://obsidian.md/help/plugins?utm_source=chatgpt.com "Core plugins - Obsidian Help"))

然后进入：

```text
设置 → 核心插件 → 模板
```

将模板文件夹设置为：

```text
99-Templates
```

核心模板支持日期和时间变量，例如：

```text
{{date:YYYY-MM-DD}}
```

([Obsidian](https://obsidian.md/help/plugins/templates?utm_source=chatgpt.com "Templates - Obsidian Help"))

---

# 五、怎样创建第一篇文档

## 方法一：使用左侧“新建笔记”

1. 点击左侧文件列表顶部的“新建笔记”。
    
2. 输入文件名：
    

```text
认知负荷理论
```

3. 按 Enter。
    
4. 笔记会按照前面的设置进入 `00-Inbox`。
    

## 方法二：在指定文件夹中创建

如果你已经知道这是一篇知识笔记：

1. 右键 `20-Notes`。
    
2. 选择“新建笔记”。
    
3. 输入：
    

```text
工作记忆
```

这种方式可以直接在指定文件夹中创建文件。([Obsidian](https://obsidian.md/help/plugins/file-explorer?utm_source=chatgpt.com "File explorer - Obsidian Help"))

## 方法三：使用快速切换

按：

```text
Ctrl+O
```

macOS：

```text
Cmd+O
```

输入一篇已有笔记的名称即可打开。如果没有匹配结果，按 Enter 可以直接用这个名称创建新笔记。([Obsidian](https://obsidian.md/help/plugins/quick-switcher?utm_source=chatgpt.com "Quick switcher - Obsidian Help"))

这是以后最常用的打开和创建方法，因为当仓库有几百篇笔记后，用鼠标展开文件夹寻找文件，是一种相当原始的娱乐活动。

## 方法四：从链接创建

在一篇笔记中输入：

```markdown
[[双重编码理论]]
```

如果这篇笔记还不存在，链接会显示为未创建状态。点击它，Obsidian 就会创建名为“`双重编码理论`”的新笔记。

这非常适合在写作过程中先建立关系，再补充内容。

---

# 六、Markdown 最基础的写法

Markdown 的基本思想是：

> 使用少量符号表示标题、列表、粗体、链接和代码，而不是不断点工具栏按钮。

Obsidian 支持 CommonMark、GitHub Flavored Markdown，以及内部链接、嵌入、标注、数学公式等扩展语法。([Obsidian](https://obsidian.md/help/obsidian-flavored-markdown?utm_source=chatgpt.com "Obsidian Flavored Markdown - Obsidian Help"))

---

## 1. 段落与换行

普通文字直接输入即可：

```markdown
认知负荷理论关注工作记忆容量有限这一事实。

当任务同时要求处理过多信息时，学习和问题解决表现可能下降。
```

两个段落之间留一个空行。

不要只按一次 Enter 来分段，因为标准 Markdown 中，单次换行在阅读模式下可能仍然被视为同一段。最稳妥的规则是：

```text
新段落：按两次 Enter，留一个空行
同一段内换行：使用 Shift+Enter
```

Markdown 对单次换行、尾随空格和空行的处理不同，因此养成“段落之间留空行”的习惯最可靠。([Obsidian](https://obsidian.md/zh/help/syntax "基本格式语法 - Obsidian 中文帮助"))

---

## 2. 标题

标题前使用 `#`：

```markdown
# 一级标题
## 二级标题
### 三级标题
#### 四级标题
```

本指南采用“文件名作为标题”的规则，所以正文通常从 `##` 开始：

```markdown
## 一句话结论

## 定义

## 证据

### 支持证据

### 反面证据

## 局限

## 关联笔记
```

标题层级不要跳跃：

```text
正确：## → ###
不推荐：## → #####
```

标题不仅改变字体大小，也会出现在右侧“大纲”中，并能作为链接目标。

---

## 3. 加粗、斜体、高亮和删除线

```markdown
**加粗内容**

*斜体内容*

==高亮内容==

~~删除内容~~
```

适合这样使用：

```markdown
**核心结论：** 工作记忆容量有限。

该机制在复杂任务中可能更加明显，但这一解释仍需==更多实验验证==。

早期版本认为该结果完全由注意力解释，现已将这一判断~~视为确定结论~~修改为暂定假设。
```

不要把整篇笔记全部加粗或高亮。高亮越多，最终越接近什么都没突出。

---

## 4. 无序列表

输入短横线和空格：

```markdown
- 工作记忆容量有限
- 任务复杂度会影响认知负荷
- 先验知识可以降低部分负荷
```

嵌套列表使用 Tab：

```markdown
- 认知负荷
  - 内在负荷
  - 外在负荷
  - 生成性负荷
```

使用 `Shift+Tab` 可以减少缩进。

---

## 5. 有序列表

```markdown
1. 提出研究问题
2. 搜索文献
3. 提取证据
4. 比较相互冲突的结论
5. 形成暂定判断
```

即使源码中都写成 `1.`，Markdown 也可以自动编号：

```markdown
1. 第一步
2. 第二步
3. 第三步
```

不过初学阶段直接写正常数字更直观。

---

## 6. 任务列表

```markdown
- [ ] 阅读论文方法部分
- [ ] 检查样本排除标准
- [x] 下载补充材料
```

显示效果是可勾选的任务。

嵌套任务：

```markdown
- [ ] 完成论文复现
  - [x] 下载数据
  - [ ] 清理变量
  - [ ] 运行模型
  - [ ] 比较结果
```

普通任务不需要插件。插件只是在任务数量变多后，帮助跨笔记聚合和筛选。

---

## 7. 引用

```markdown
> 这是一段引用内容。
```

多行引用：

```markdown
> 研究者认为该结果支持工作记忆限制假说。
>
> 但样本量较小，置信区间较宽。
```

引用适合放原文摘录；你自己的总结最好放在引用外，以免三个月后分不清哪些是作者说的，哪些是当时的自己脑补的。

---

## 8. 标注框

Obsidian 支持 Callout，也就是标注框：

```markdown
> [!note] 研究笔记
> 这里记录需要保留的补充说明。
```

警告：

```markdown
> [!warning] 方法学问题
> 研究没有预注册主要结局。
```

结论：

```markdown
> [!summary] 暂定结论
> 当前证据支持弱到中等效应，但异质性较高。
```

标注框适合强调少量重要内容，不适合把每个段落都装进不同颜色的盒子。([Obsidian](https://obsidian.md/help/callouts?utm_source=chatgpt.com "Callouts - Obsidian Help"))

---

## 9. 行内代码和代码块

行内代码使用一个反引号：

```markdown
使用 `pandas.read_csv()` 读取数据。
```

代码块使用三个反引号：

````markdown
```python
import pandas as pd

data = pd.read_csv("data.csv")
print(data.head())
```
````

第一个反引号后写语言名称，可以启用语法高亮。Obsidian 使用代码块语法显示代码。([Obsidian](https://obsidian.md/help/syntax?utm_source=chatgpt.com "Basic formatting syntax - Obsidian Help"))

---

## 10. 数学公式

行内公式：

```markdown
效应量记为 $d = 0.42$。
```

独立公式：

```markdown
$$
\bar{x} = \frac{1}{n}\sum_{i=1}^{n}x_i
$$
```

Obsidian 使用 MathJax 和 LaTeX 语法显示数学公式。([Obsidian](https://obsidian.md/help/advanced-syntax?utm_source=chatgpt.com "Advanced formatting syntax - Obsidian Help"))

---

# 七、一篇合格的普通笔记应该怎么写

假设创建一篇：

```text
认知负荷理论
```

推荐结构：

```markdown
## 一句话结论

人的工作记忆容量有限，任务中同时需要处理的信息越多，学习和问题解决越容易受到影响。

## 定义

认知负荷指完成特定认知任务时，对有限工作记忆资源的占用程度。

## 核心机制

- [[工作记忆]]容量有限。
- 新手缺少可以直接调用的知识结构。
- 复杂任务会同时占用多个加工环节。
- [[先验知识]]可能通过组块化降低实际加工负担。

## 证据

### 支持证据

- 实验研究观察到复杂材料会降低正确率。
- 分步呈现可能改善部分学习任务表现。

### 反面证据

- 部分结果可能受到任务熟悉度影响。
- 认知负荷的自我报告测量可能不够稳定。

## 我的判断

目前最可信的部分是工作记忆受限这一基础假设。

不同负荷类型的精确区分，以及某些教学设计原则的普遍性，仍需结合具体任务判断。

## 待解决问题

- [ ] 不同认知负荷量表之间的一致性如何？
- [ ] 生理测量是否比主观量表更可靠？

## 关联笔记

- [[工作记忆]]
- [[组块化]]
- [[先验知识]]
- [[双重编码理论]]
```

这里最重要的不是格式，而是笔记同时保留了：

```text
结论
定义
机制
证据
反证
判断
未解决问题
关系
```

这比单纯摘抄教材更有长期价值。

---

# 八、怎么插入图片

## 1. 首先确认附件位置

前面已经设置：

```text
设置 → 文件与链接
→ 附件默认存放位置
→ 指定的附件文件夹
→ 90-Attachments
```

以后粘贴或拖入的图片，就不会散落在仓库根目录。Obsidian 支持直接粘贴附件，也可以从系统文件管理器拖入；文件会被复制到默认附件位置，并自动嵌入当前笔记。([Obsidian](https://obsidian.md/zh/help/attachments "附件 - Obsidian 中文帮助"))

---

## 2. 粘贴截图

先截图，然后在笔记中将光标放到目标位置，直接粘贴。

Obsidian 会自动插入类似：

```markdown
![[Pasted image 20260830142530.png]]
```

图片已经被复制到：

```text
90-Attachments
```

建议立即在左侧文件列表中找到它并重命名，例如：

```text
认知负荷-理论结构-01.png
```

开启自动更新内部链接后，重命名附件时，笔记中的链接也会被更新。

推荐附件命名格式：

```text
主题-用途-序号.扩展名
```

例如：

```text
认知负荷-实验流程-01.png
睡眠研究-结果图-02.png
毕业论文-变量关系-01.svg
```

---

## 3. 拖入图片

从 Windows 文件资源管理器或 macOS Finder 中，将图片拖到笔记编辑区域。

Obsidian 会：

```text
复制图片到附件文件夹
+
在当前笔记中插入嵌入语法
```

注意，它通常是复制，而不是仅仅引用外部原始文件。([Obsidian](https://obsidian.md/help/drag-and-drop?utm_source=chatgpt.com "Drag and drop - Obsidian Help"))

---

## 4. 图片链接与图片嵌入的区别

只链接图片：

```markdown
[[认知负荷-理论结构-01.png]]
```

显示为一个可点击的文件链接。

直接显示图片：

```markdown
![[认知负荷-理论结构-01.png]]
```

前面的 `!` 表示嵌入内容。

这个规则也适用于笔记和 PDF：

```text
[[文件]]   只是链接
![[文件]]  显示文件内容
```

---

## 5. 调整图片大小

只指定宽度：

```markdown
![[认知负荷-理论结构-01.png|600]]
```

图片宽度显示为 600 像素，并保持原始比例。

同时指定宽度和高度：

```markdown
![[认知负荷-理论结构-01.png|600x400]]
```

官方支持在嵌入链接中使用 `|宽度` 或 `|宽度x高度` 调整图片。([Obsidian](https://obsidian.md/zh/help/embeds "插入文件 - Obsidian 中文帮助"))

通常只指定宽度更安全，避免图片变形：

```markdown
![[认知负荷-理论结构-01.png|500]]
```

---

## 6. 给图片添加图注

Obsidian 没有强制的标准图片标题语法，最简单的做法是在图片下面写一行斜体：

```markdown
![[认知负荷-理论结构-01.png|600]]

*图 1. 认知负荷理论中的主要变量关系。*
```

正式科研笔记还应补充来源：

```markdown
![[认知负荷-理论结构-01.png|600]]

*图 1. 认知负荷理论结构。根据 [[Sweller 1988 - Cognitive Load During Problem Solving]] 整理。*
```

这样未来看到图片时，知道它不是某次凌晨两点从互联网捡回来的无主图像。

---

## 7. 插入网络图片

语法是：

```markdown
![图片说明|600](https://example.com/image.png)
```

但重要图片建议保存到本地附件文件夹。

外部图片可能因为网页删除、地址变化、权限限制而失效。本地保存虽然占空间，但更可靠，也更适合长期研究记录。

---

# 九、怎么插入 PDF

将 PDF 拖入笔记，或者先放进 `90-Attachments`。

嵌入完整 PDF：

```markdown
![[Smith-2025-Sleep-Memory.pdf]]
```

直接跳到第 3 页：

```markdown
![[Smith-2025-Sleep-Memory.pdf#page=3]]
```

指定嵌入阅读器高度：

```markdown
![[Smith-2025-Sleep-Memory.pdf#height=500]]
```

Obsidian 官方支持嵌入 PDF、指定页码和阅读器高度。([Obsidian](https://obsidian.md/zh/help/embeds "插入文件 - Obsidian 中文帮助"))

只创建可点击链接，不在正文展开：

```markdown
[[Smith-2025-Sleep-Memory.pdf]]
```

科研笔记中通常不必把整篇 PDF 嵌入正文。更好的方式是：

```markdown
## 原始文件

[[Smith-2025-Sleep-Memory.pdf]]

## 关键页

- 方法：![[Smith-2025-Sleep-Memory.pdf#page=4]]
- 主要结果：![[Smith-2025-Sleep-Memory.pdf#page=8]]
```

---

# 十、怎么创建普通表格

## 1. 使用命令插入

按：

```text
Ctrl+P
```

macOS：

```text
Cmd+P
```

输入：

```text
插入表格
```

选择对应命令。

命令面板可以搜索并执行 Obsidian 中的命令，不需要记住菜单具体藏在哪个角落。([Obsidian](https://obsidian.md/help/plugins/command-palette?utm_source=chatgpt.com "Command palette - Obsidian Help"))

在实时预览模式中，也可以右键正文：

```text
插入 → 表格
```

---

## 2. 表格的 Markdown 语法

```markdown
| 研究 | 年份 | 样本量 | 主要结论 |
|---|---:|---:|---|
| [[Smith 2025]] | 2025 | 120 | 睡眠限制降低延迟回忆 |
| [[Lee 2024]] | 2024 | 86 | 效应只出现在复杂任务中 |
```

第一行是列名：

```markdown
| 研究 | 年份 | 样本量 | 主要结论 |
```

第二行定义表头和对齐：

```markdown
|---|---:|---:|---|
```

后面是数据。

官方表格语法使用竖线分隔列，使用短横线定义表头；在实时预览中，可以右键表格添加、删除、排序或移动行列。([Obsidian](https://obsidian.md/help/advanced-syntax?utm_source=chatgpt.com "Advanced formatting syntax - Obsidian Help"))

---

## 3. 对齐方式

左对齐：

```markdown
|:---|
```

居中：

```markdown
|:---:|
```

右对齐：

```markdown
|---:|
```

例如：

```markdown
| 变量 | 均值 | 说明 |
|:---|---:|:---|
| 年龄 | 23.4 | 岁 |
| 正确率 | 0.81 | 比例 |
```

---

## 4. 表格中插入链接

```markdown
| 概念 | 定义 |
|---|---|
| [[工作记忆]] | 临时保存和加工信息的认知系统 |
| [[认知负荷]] | 任务对有限加工资源的占用 |
```

如果链接使用了自定义显示文字，链接中的竖线要转义：

```markdown
[[认知负荷理论\|CLT]]
```

因为表格本身也使用 `|` 分隔列。

---

## 5. 表格中插入图片

```markdown
| 图像 | 说明 |
|---|---|
| ![[实验流程.png\|200]] | 实验流程 |
```

同样需要把图片大小语法中的竖线写成：

```text
\|
```

([Obsidian](https://obsidian.md/help/advanced-syntax?utm_source=chatgpt.com "Advanced formatting syntax - Obsidian Help"))

---

## 6. 表格什么时候适用

Markdown 表格适合：

```text
比较 3 到 10 个理论
列出少量变量
展示固定结果
整理不会频繁变化的信息
```

例如：

```markdown
| 方法 | 优点 | 局限 |
|---|---|---|
| 横断面研究 | 快速、成本低 | 难以判断时间顺序 |
| 队列研究 | 可以观察时间顺序 | 成本较高 |
| 随机试验 | 因果识别较强 | 伦理和外部效度受限 |
```

Markdown 表格不适合：

```text
管理 100 篇论文
追踪几十个项目
频繁更新状态
复杂筛选和排序
批量计算
```

这些情况应该使用 Properties 和 Bases，而不是把一张 Markdown 表格手工维护到退休。

---

# 十一、怎么做内部链接

内部链接是 Obsidian 最核心的写作习惯。

## 1. 链接到另一篇笔记

输入：

```markdown
[[工作记忆]]
```

输入 `[[` 后，Obsidian 会弹出已有笔记建议，选择后按 Enter。

---

## 2. 修改链接显示文字

文件名是：

```text
认知负荷理论
```

正文希望显示为“CLT”：

```markdown
[[认知负荷理论|CLT]]
```

显示出来是：

```text
CLT
```

但实际仍然链接到“认知负荷理论”。

---

## 3. 链接到某个标题

链接到另一篇笔记中的“证据”部分：

```markdown
[[认知负荷理论#证据]]
```

链接到当前笔记中的某个标题：

```markdown
[[#研究局限]]
```

输入 `[[笔记名称#` 后，Obsidian 会列出该笔记中的标题供选择。([Obsidian](https://obsidian.md/help/links?utm_source=chatgpt.com "Internal links - Obsidian Help"))

---

## 4. 嵌入另一篇笔记的某个部分

普通链接：

```markdown
[[认知负荷理论#一句话结论]]
```

嵌入显示：

```markdown
![[认知负荷理论#一句话结论]]
```

例如，在项目笔记中：

```markdown
## 理论基础

![[认知负荷理论#一句话结论]]

![[工作记忆#容量限制]]
```

这样，原始知识笔记内容更新后，项目笔记中嵌入的内容也会同步更新。Obsidian 使用在内部链接前加 `!` 的方式嵌入笔记、标题、块、图片和其他支持的文件。([Obsidian](https://obsidian.md/zh/help/embeds "插入文件 - Obsidian 中文帮助"))

---

## 5. 外部网页链接

```markdown
[网页名称](https://example.com)
```

例如：

```markdown
[项目主页](https://example.com/project)
```

建议不要直接贴一长串裸网址。给链接写清楚显示名称，以后才知道它到底是什么。

---

## 6. 使用别名处理中英文名称

假设笔记文件名是：

```text
认知负荷理论
```

但你希望搜索以下名称时都能找到它：

```text
Cognitive Load Theory
CLT
认知负荷
```

在笔记顶部添加 `aliases` 属性：

```yaml
---
aliases:
  - Cognitive Load Theory
  - CLT
  - 认知负荷
---
```

以后输入：

```markdown
[[CLT]]
```

在建议中选择别名后，Obsidian 会生成：

```markdown
[[认知负荷理论|CLT]]
```

别名尤其适合：

```text
中英文术语
缩写
旧名称
同义词
全称与简称
```

官方要求 `aliases` 使用列表格式保存。([Obsidian](https://obsidian.md/help/aliases?utm_source=chatgpt.com "Aliases - Obsidian Help"))

---

## 7. 正确的链接方式

不要只在笔记末尾堆放：

```markdown
- [[工作记忆]]
- [[认知负荷]]
- [[学习效果]]
```

更有价值的是在句子中说明关系：

```markdown
[[工作记忆]]容量有限，因此复杂任务可能产生更高的[[认知负荷]]，进而影响[[学习效果]]。
```

或者：

```markdown
[[先验知识]]可能通过组块化降低任务对[[工作记忆]]的占用。
```

链接的价值不只是“这两个词有关”，而是保留“它们为什么有关”。

---

# 十二、Properties：怎么给笔记添加结构化数据

Properties 中文界面通常显示为“属性”。

属性不是正文，而是笔记顶部的结构化字段，例如：

```text
类型
状态
日期
年份
评分
所属项目
主题
来源网址
```

属性可以是文本、列表、数字、复选框、日期、日期时间或标签。每个属性名称在整个 Vault 中会采用一致的类型，所以最好一开始就统一命名。([Obsidian](https://obsidian.md/zh/help/properties "属性 - Obsidian 中文帮助"))

---

## 1. 添加属性

打开一篇笔记，按：

```text
Ctrl+;
```

macOS：

```text
Cmd+;
```

也可以：

1. 点击笔记右上角三点。
    
2. 选择“增加笔记属性”。
    

或者直接在文件最开头输入：

```markdown
---
```

Obsidian 会进入属性编辑区域。([Obsidian](https://obsidian.md/zh/help/properties "属性 - Obsidian 中文帮助"))

初学阶段推荐使用图形界面添加属性，不必先研究 YAML 缩进这种计算机专门设计来惩罚空格错误的传统。

---

## 2. 最小属性规范

不需要每篇笔记都有十几个字段。

建议所有正式笔记只保留两个基本属性：

```text
type
created
```

只有需要管理流程时，再增加：

```text
status
topics
project
source
year
rating
due
aliases
```

推荐字段如下：

|属性|类型|用途|
|---|---|---|
|`type`|文本|笔记类型|
|`created`|日期|创建日期|
|`status`|文本|处理状态|
|`topics`|列表|涉及的主要主题|
|`project`|列表|所属项目|
|`source`|文本/URL|原始来源|
|`year`|数字|发表或出版年份|
|`rating`|数字|主观价值评分|
|`due`|日期|项目截止日期|
|`aliases`|列表|别名、缩写、中英文名称|

---

## 3. 固定可选值

`type` 只使用：

```text
note
source
project
daily
```

分别表示：

```text
note：知识笔记
source：来源笔记
project：项目笔记
daily：每日笔记
```

`status` 只使用：

```text
inbox
active
done
archived
```

不要今天写：

```text
active
```

明天写：

```text
working
```

后天又写：

```text
in progress
```

这三个词对人类来说意思差不多，对数据库筛选来说是三个毫无关系的值。

---

## 4. 普通知识笔记的属性

```yaml
---
type: note
created: 2026-08-30
topics:
  - "[[认知科学]]"
project:
  - "[[毕业论文]]"
aliases:
  - Cognitive Load Theory
  - CLT
---
```

解释：

```text
type：这是知识笔记
created：创建日期
topics：所属主题
project：与哪个项目有关
aliases：其他名称
```

---

## 5. 来源笔记的属性

```yaml
---
type: source
status: active
created: 2026-08-30
year: 2025
rating: 4
topics:
  - "[[睡眠]]"
  - "[[记忆]]"
project:
  - "[[毕业论文]]"
source: https://example.com/article
---
```

这里：

```text
rating: 4
```

必须设置为数字属性，而不是文本。

`topics` 和 `project` 是列表。原始 YAML 中的内部链接需要用引号包围；使用属性图形界面输入时，Obsidian 通常会自动处理。([Obsidian](https://obsidian.md/help/properties?utm_source=chatgpt.com "Properties - Obsidian Help"))

---

## 6. 属性和正文分别放什么

适合放在属性里的内容：

```text
年份
日期
评分
状态
类型
项目
作者
是否完成
```

适合放在正文里的内容：

```text
研究结果为什么可信
作者采用了什么推理
有哪些方法学问题
你自己的判断
证据之间如何冲突
```

不要把长段落放进属性。Obsidian 属性本来就是为较小、原子化、可供人和机器读取的信息设计的，而且属性中的 Markdown 不会正常渲染。([Obsidian](https://obsidian.md/zh/help/properties "属性 - Obsidian 中文帮助"))

---

# 十三、Bases：怎么建立真正可管理的数据表

Obsidian 的 Bases 在中文帮助中称为“数据库”。

它的基本逻辑是：

```text
一篇笔记 = 一行
一个属性 = 一列
一个 Base = 对这些笔记的筛选和展示方式
```

例如，`40-Sources` 中每一篇论文是一篇独立笔记：

```text
Smith 2025 - Sleep Restriction and Memory.md
Lee 2024 - Working Memory Under Load.md
Zhang 2026 - Meta-analysis of Sleep Duration.md
```

每篇笔记有自己的属性：

```yaml
---
type: source
status: inbox
year: 2025
rating: 4
---
```

Base 可以自动把它们显示成：

|文件|状态|年份|评分|
|---|---|--:|--:|
|Smith 2025|inbox|2025|4|
|Lee 2024|done|2024|5|
|Zhang 2026|active|2026|4|

这些数据仍然保存在各自的 Markdown 文件里。Base 只是负责查看、编辑、筛选和排序，并不会把你的笔记搬进另一个封闭数据库。([Obsidian](https://obsidian.md/zh/help/bases "Bases 简介 - Obsidian 中文帮助"))

---

## 1. 先创建三篇来源笔记

在 `40-Sources` 中创建：

```text
Smith 2025 - Sleep Restriction and Memory
Lee 2024 - Working Memory Under Load
Zhang 2026 - Meta-analysis of Sleep Duration
```

分别添加属性。

第一篇：

```yaml
---
type: source
status: inbox
created: 2026-08-30
year: 2025
rating: 4
topics:
  - "[[睡眠]]"
  - "[[记忆]]"
---
```

第二篇：

```yaml
---
type: source
status: done
created: 2026-08-30
year: 2024
rating: 5
topics:
  - "[[工作记忆]]"
---
```

第三篇：

```yaml
---
type: source
status: active
created: 2026-08-30
year: 2026
rating: 4
topics:
  - "[[睡眠]]"
  - "[[元分析]]"
---
```

---

## 2. 创建 Base

确认核心插件“数据库/Bases”已经开启。

然后：

1. 右键 `40-Sources`。
    
2. 选择“新建数据库”或“New base”。
    
3. 命名为：
    

```text
文献库
```

也可以按 `Ctrl+P` 或 `Cmd+P`，搜索：

```text
Bases: Create new base
```

官方支持通过命令面板、文件列表右键或左侧功能区创建 Base。([Obsidian](https://obsidian.md/help/bases/create-base?utm_source=chatgpt.com "Create a base - Obsidian Help"))

---

## 3. 添加筛选条件

新建的 Base 默认可能显示整个 Vault 中的文件，因此需要添加筛选条件。

点击顶部“筛选”，添加：

```text
属性：type
条件：等于
值：source
```

最终逻辑是：

```text
只显示 type 为 source 的笔记
```

也可以使用文件夹筛选：

```text
文件所在文件夹为 40-Sources
```

推荐优先使用：

```text
type = source
```

因为即使某篇来源笔记暂时放在 Inbox，只要属性正确，它仍然可以进入文献视图。

Base 没有筛选时会包含整个仓库中的文件；筛选可以基于属性、标签和文件夹等条件。([Obsidian](https://obsidian.md/help/bases/views?utm_source=chatgpt.com "Views - Obsidian Help"))

---

## 4. 选择显示列

点击顶部“属性”，选择：

```text
文件名
status
year
rating
topics
project
```

不需要显示：

```text
created
aliases
source
```

除非确实需要。

Base 的目的不是展示所有可能信息，而是展示当前决策所需的信息。

---

## 5. 排序

点击“排序”，设置：

```text
year：从新到旧
rating：从高到低
```

这样，最新且评分较高的论文更容易出现在前面。

Base 可以按照文本、数字、日期和公式等属性排序，也可以按一个属性分组。([Obsidian](https://obsidian.md/help/bases/views?utm_source=chatgpt.com "Views - Obsidian Help"))

---

## 6. 创建多个视图

点击左上角视图名称，选择“添加视图”。

建立三个视图。

### 待处理

筛选：

```text
status = inbox
```

### 进行中

筛选：

```text
status = active
```

### 已完成

筛选：

```text
status = done
```

所有视图共享：

```text
type = source
```

每个视图再添加自己的状态筛选。

这样就不需要维护三张表。修改某篇笔记的 `status`，它就会自动从一个视图移动到另一个视图。

---

## 7. 在 Base 中直接修改数据

在表格中点击 `status`、`rating` 或 `year` 的单元格，可以直接修改。

修改后，实际变化会写回对应 Markdown 笔记顶部的 Properties。

这意味着：

```text
Base 不是数据副本
Base 是笔记属性的一个视图
```

---

## 8. 把 Base 嵌入普通笔记

例如建立：

```text
Home.md
```

在里面写：

```markdown
## 当前文献

![[文献库.base]]
```

也可以嵌入特定视图：

```markdown
![[文献库.base#进行中]]
```

Base 文件使用 `.base` 扩展名，并可以通过普通嵌入语法插入笔记。([Obsidian](https://obsidian.md/help/bases/create-base?utm_source=chatgpt.com "Create a base - Obsidian Help"))

---

# 十四、普通表格、Properties 和 Bases 到底怎么选

使用下面这个判断标准：

|需求|使用什么|
|---|---|
|比较几个固定概念|Markdown 表格|
|管理几十或几百篇论文|Properties + Bases|
|记录一篇论文的详细内容|Markdown 正文|
|保存年份、评分、状态|Properties|
|自动筛选、排序和分组|Bases|
|分析大型数值数据|Excel、R、Python、SPSS 等|

例如：

## 情况一：比较三种研究设计

用 Markdown 表格：

```markdown
| 设计 | 优点 | 局限 |
|---|---|---|
| 横断面 | 快速 | 时间顺序不明 |
| 队列 | 可观察时间顺序 | 成本较高 |
| 随机试验 | 因果推断较强 | 伦理限制 |
```

## 情况二：管理 150 篇论文

每篇论文建立一篇来源笔记，使用 Properties 和 Bases。

## 情况三：分析 10 万行实验数据

不要把 10 万行数据写进 Markdown 表格。

将原始数据保存在：

```text
CSV
Parquet
Excel
R Project
Python 项目
统计软件文件
```

Obsidian 负责保存：

```text
数据说明
变量字典
版本记录
清理规则
排除标准
分析决策
模型结果解释
```

例如在项目笔记中写：

```markdown
## 数据集

- 数据文件：`data/raw/experiment-2026-08.csv`
- 数据版本：v1.2
- 样本量：N = 428
- 主要结局：delayed_recall
- 主要暴露：sleep_duration
- 分析脚本：`analysis/model-01.py`

## 数据清理规则

- 删除重复 participant_id。
- 年龄小于 18 岁的记录不纳入分析。
- 缺失主要结局的记录不进入主分析。
- 极端值处理见 [[异常值处理原则]]。

## 分析决策

- 主模型使用线性混合效应模型。
- 随机截距设为 participant_id。
- 是否加入随机斜率将在敏感性分析中检验。
```

Obsidian 很适合记录“数据意味着什么”和“分析为什么这样做”，但不是用来代替专业统计环境的。终于有一个软件不必假装自己能解决人类全部问题。

已有的 CSV 目录型数据也可以通过官方 Importer 导入；官方导入器会把每一行转换为一篇带 Properties 的 Markdown 笔记，并创建相应 Base。这个方法适合“每一行都值得成为独立对象”的数据，例如书籍、文献、项目或联系人，而不适合大型观测数据。([Obsidian](https://obsidian.md/help/import/csv?utm_source=chatgpt.com "Import CSV files - Obsidian Help"))

---

# 十五、建立模板，避免每次重新写格式

模板的核心用途不是让笔记看起来华丽，而是确保属性名称和正文结构始终一致。

## 1. 普通知识笔记模板

在 `99-Templates` 中创建：

```text
普通笔记模板
```

内容：

```markdown
---
type: note
created: {{date:YYYY-MM-DD}}
topics: []
project: []
aliases: []
---

## 一句话结论

用自己的话写出这篇笔记最重要的结论。

## 定义与范围

这个概念是什么？不是什么？适用范围是什么？

## 机制或推理

为什么会出现这一现象？

## 证据

### 支持证据

### 反面证据

## 局限与不确定性

哪些条件下这个结论可能不成立？

## 我的判断

目前最可信的部分是什么？仍然存疑的部分是什么？

## 关联笔记

- 
```

这份模板强调结论、证据、反证和不确定性，适合科研与学习，而不是把笔记降级成摘抄仓库。

---

## 2. 来源笔记模板

创建：

```text
来源笔记模板
```

内容：

```markdown
---
type: source
status: inbox
created: {{date:YYYY-MM-DD}}
authors: []
year:
topics: []
project: []
source:
rating:
---

## 来源信息

- 标题：
- 作者：
- 年份：
- 类型：
- 原始链接：

## 这项来源试图回答什么

## 核心结论

不要复制摘要。用自己的话写。

## 方法

- 研究设计：
- 样本：
- 主要变量：
- 测量方法：
- 分析方法：

## 关键结果

尽量记录效应大小、不确定性和样本量，而不只写“显著”或“不显著”。

## 局限

- 选择偏差：
- 测量误差：
- 混杂：
- 多重比较：
- 外部效度：

## 我的判断

### 我相信什么

### 我不确定什么

### 什么证据会改变我的判断

## 可提炼的知识笔记

- [[待创建的概念笔记]]
```

---

## 3. 项目笔记模板

创建：

```text
项目笔记模板
```

内容：

```markdown
---
type: project
status: active
created: {{date:YYYY-MM-DD}}
due:
topics: []
---

## 项目目标

最终要产生什么可观察、可验收的结果？

## 完成标准

- 
- 
- 

## 当前状态

## 下一个行动

- [ ] 

## 关键问题

- 

## 相关资料

- 

## 决策记录

### {{date:YYYY-MM-DD}}

- 决策：
- 原因：
- 依据：
- 后续影响：

## 项目结果

## 复盘

- 哪些做法有效？
- 哪些判断错误？
- 下次应当改变什么？
```

---

## 4. 每日笔记模板

创建：

```text
每日笔记模板
```

内容：

```markdown
---
type: daily
created: {{date:YYYY-MM-DD}}
---

## 今日三个主要结果

- [ ] 
- [ ] 
- [ ] 

## 快速记录

## 学习与研究

### 新证据

### 新问题

### 被修正的认识

## 今日完成

## 明日承接
```

然后进入：

```text
设置 → 核心插件 → 日记
```

设置：

```text
新建日记位置：10-Daily
日期格式：YYYY-MM-DD
模板文件位置：99-Templates/每日笔记模板
```

核心日记插件可以按照日期生成笔记，并使用指定模板。([Obsidian](https://obsidian.md/help/plugins/daily-notes?utm_source=chatgpt.com "Daily notes - Obsidian Help"))

---

## 5. 使用模板

创建一篇空白笔记后：

1. 按 `Ctrl+P` 或 `Cmd+P`。
    
2. 输入“插入模板”。
    
3. 选择对应模板。
    

模板中的属性会被添加到笔记顶部；如果笔记已经有属性，Obsidian 会将模板属性与现有属性合并。([Obsidian](https://obsidian.md/help/plugins/templates?utm_source=chatgpt.com "Templates - Obsidian Help"))

后续可以给“插入模板”设置快捷键，但先不必折腾二十组组合键。人的手指还没有严重到需要航空驾驶舱式配置。

---

# 十六、建立一个不会膨胀失控的日常流程

目录和属性只能降低混乱，真正防止失控的是固定处理流程。

推荐使用四步法：

```text
捕获
整理
连接
使用
```

## 1. 捕获

在上课、阅读、会议或思考时，不要立即纠结应该放在哪个目录。

可以：

```text
建立一篇笔记进入 00-Inbox
或者写进当天 Daily Note
```

例如每日笔记中：

```markdown
## 快速记录

- 10:20 需要核查 [[认知负荷]] 是否有统一的操作化定义。
- 13:40 Smith 2025 的样本排除标准似乎不够透明。
- 16:10 [[工作记忆]]可能是当前实验结果的替代解释。
```

## 2. 整理

每天或每周固定处理 Inbox。

每篇 Inbox 笔记只做以下决定之一：

```text
删除
保留为每日记录
转成知识笔记
转成项目笔记
转成来源笔记
合并到已有笔记
```

正式保留时：

```text
修改为明确文件名
插入相应模板
添加必要属性
移动到对应文件夹
```

## 3. 连接

正式保留的笔记至少检查一次：

```text
它与哪些已有知识有关？
它支持什么观点？
它反驳什么观点？
它属于哪个项目？
```

通常添加一到三个有意义的链接就够了。

不要为了让关系图看起来繁荣而每段添加十几个链接。图谱节点数量不是学术产出指标。

## 4. 使用

项目笔记应当引用知识笔记和来源笔记：

```markdown
## 理论依据

[[工作记忆]]容量有限，因此高复杂度任务可能造成更高的[[认知负荷]]。

支持这一判断的证据包括：

- [[Smith 2025 - Sleep Restriction and Memory#关键结果]]
- [[Lee 2024 - Working Memory Under Load#关键结果]]

但 [[Zhang 2026 - Meta-analysis of Sleep Duration#异质性]] 表明效应在不同任务之间差异较大。
```

此时 Obsidian 不再只是储存资料，而是在支持实际写作、研究和决策。

---

# 十七、内容增多后怎么查找

内容规模增大以后，不要主要依赖浏览文件夹。

## 1. 按文件名打开

按：

```text
Ctrl+O
```

macOS：

```text
Cmd+O
```

输入文件名或别名。

例如输入：

```text
CLT
```

可以找到拥有该别名的：

```text
认知负荷理论
```

([Obsidian](https://obsidian.md/help/plugins/quick-switcher?utm_source=chatgpt.com "Quick switcher - Obsidian Help"))

## 2. 全文搜索

Windows/Linux：

```text
Ctrl+Shift+F
```

macOS：

```text
Cmd+Shift+F
```

搜索某个词：

```text
工作记忆
```

搜索完整短语：

```text
"随机斜率"
```

搜索特定文件夹：

```text
path:"40-Sources"
```

搜索特定属性：

```text
[type:source]
```

搜索状态：

```text
[status:active]
```

同时组合：

```text
[type:source] [status:active] 睡眠
```

搜索未完成任务：

```text
task-todo:
```

Obsidian 官方搜索支持路径、文件名、正文、标签、任务以及 `[property:value]` 形式的属性查询。([Obsidian](https://obsidian.md/help/plugins/search "Search - Obsidian Help"))

## 3. Base 和搜索怎么分工

```text
经常重复查看的列表：Base
临时寻找某个内容：搜索
已知文件名：快速切换
探索知识关系：链接和反向链接
```

例如：

```text
“所有未完成文献” → Base
“哪里提到了随机斜率” → 搜索
“打开毕业论文” → 快速切换
“哪些笔记引用认知负荷” → 反向链接
```

---

# 十八、一个完整的实际例子

假设你正在上课，老师展示了一张认知负荷模型图。

## 第一步：在每日笔记快速记录

```markdown
## 快速记录

老师提到[[认知负荷理论]]可以解释复杂任务中的表现下降。

![[认知负荷-课程幻灯片-01.png|600]]

需要核查：
- [ ] 三类认知负荷的原始定义
- [ ] 是否存在可靠的客观测量
```

## 第二步：点击链接创建正式笔记

点击：

```markdown
[[认知负荷理论]]
```

创建新笔记。

## 第三步：插入普通笔记模板

在新笔记中插入：

```text
普通笔记模板
```

填写：

```markdown
## 一句话结论

任务对有限工作记忆资源的要求越高，学习和问题解决表现越可能受到影响。

## 机制或推理

复杂任务要求同时保存中间结果、处理新信息并选择操作，这些过程共同占用[[工作记忆]]。

## 证据

### 支持证据

[[Smith 2025 - Working Memory Under Load]]报告，高复杂度条件下正确率下降。

### 反面证据

部分研究无法稳定区分不同认知负荷类型。

## 我的判断

工作记忆容量受限这一基础机制可信度较高，但三种负荷类型的精确测量仍有争议。
```

## 第四步：创建来源笔记

在 `40-Sources` 新建：

```text
Smith 2025 - Working Memory Under Load
```

插入来源笔记模板，填写方法、结果、局限。

属性设置：

```yaml
---
type: source
status: done
created: 2026-08-30
year: 2025
rating: 4
topics:
  - "[[认知负荷理论]]"
  - "[[工作记忆]]"
project:
  - "[[课程期末论文]]"
---
```

## 第五步：Base 自动收录

因为该笔记满足：

```text
type = source
```

它会自动出现在“文献库”中。

不需要再手工把它复制到某张文献总表里。

## 第六步：用于项目

在项目笔记“课程期末论文”中写：

```markdown
## 理论基础

[[认知负荷理论]]认为，复杂任务会占用有限的[[工作记忆]]资源。

主要支持证据来自：

- [[Smith 2025 - Working Memory Under Load#关键结果]]

但目前仍存在以下问题：

- 不同研究对认知负荷的操作化并不一致。
- 主观负荷量表可能受到任务难度预期影响。
```

到这里，一条完整链路已经形成：

```text
课程截图
→ 每日记录
→ 知识笔记
→ 来源笔记
→ 文献数据库
→ 项目写作
```

---

# 十九、什么时候再安装社区插件

完成上面的流程之前，不建议先安装大量社区插件。

真正出现以下需求后再扩展：

```text
每次创建笔记都要重复填写很多内容
→ 使用 Templater

捕获笔记需要连续点击多个步骤
→ 使用 QuickAdd

大量管理 Zotero 文献和批注
→ 使用 ZotLit

普通复选框无法集中管理
→ 使用 Tasks 或 TaskNotes
```

前面建立的文件夹、属性名称和模板结构不需要推倒重来。插件只是帮你自动完成相同步骤，而不是另建一套互不兼容的系统。

这才是先建立规范的意义：插件可以换，数据结构尽量不要换。

---

# 二十、最容易犯的错误

## 1. 文件夹过多

错误：

```text
20-Notes/
  心理学/
    认知心理学/
      工作记忆/
        认知负荷/
          课程/
            第一周/
```

推荐：

```text
20-Notes/认知负荷理论.md
```

然后用：

```yaml
topics:
  - "[[认知心理学]]"
  - "[[工作记忆]]"
```

## 2. 属性太多

不要一开始设计：

```text
importance
priority
maturity
certainty
confidence
review-status
review-date
next-review
stage
level
quality
usefulness
```

正式使用两周后，其中大部分字段通常都是空的，或者每次填写时都要重新思考定义。

先使用：

```text
type
created
status
topics
project
```

已经足够。

## 3. 同一个字段有多个名字

错误：

```text
project
projects
related-project
belongs-to
项目
所属项目
```

选择一个：

```text
project
```

然后始终使用它。

## 4. 把摘抄当作笔记

只有原文：

```markdown
> 作者说了一大段话……
```

至少补充：

```markdown
## 我的理解

这段话的核心主张是什么？

## 证据

作者凭什么得出这个结论？

## 局限

有什么替代解释？

## 与已有知识的关系

它支持或反驳了哪些笔记？
```

## 5. 图片不改名

不要长期保留：

```text
Pasted image 20260830123847.png
Pasted image 20260830123902.png
Pasted image 20260830124119.png
```

改为：

```text
认知负荷-模型-01.png
认知负荷-实验结果-01.png
认知负荷-测量工具-01.png
```

## 6. 用表格管理大量动态内容

Markdown 表格不会因为你盯着它，就自动更新。

需要持续管理的对象，应当拆成独立笔记，通过 Properties 和 Bases 汇总。

---

# 二十一、第一小时照着做

## 前 10 分钟

创建 Vault 和七个文件夹：

```text
00-Inbox
10-Daily
20-Notes
30-Projects
40-Sources
90-Attachments
99-Templates
```

## 第 10 到 20 分钟

设置：

```text
新笔记 → 00-Inbox
附件 → 90-Attachments
实时预览 → 开启
Wiki 链接 → 开启
自动更新内部链接 → 开启
模板目录 → 99-Templates
```

## 第 20 到 35 分钟

创建三个模板：

```text
普通笔记模板
来源笔记模板
项目笔记模板
```

## 第 35 到 45 分钟

创建三篇笔记：

```text
工作记忆
认知负荷理论
毕业论文
```

建立关系：

```markdown
[[工作记忆]]容量有限，因此复杂任务可能产生更高的[[认知负荷理论|认知负荷]]。

该问题与项目[[毕业论文]]有关。
```

## 第 45 到 50 分钟

粘贴一张图片，重命名为：

```text
认知负荷-结构图-01.png
```

调整大小：

```markdown
![[认知负荷-结构图-01.png|600]]
```

## 第 50 到 55 分钟

创建一个 Markdown 表格：

```markdown
| 概念 | 核心含义 |
|---|---|
| [[工作记忆]] | 临时保存和处理信息 |
| [[认知负荷理论]] | 描述任务对有限认知资源的要求 |
```

## 第 55 到 60 分钟

给三篇笔记添加：

```text
type
created
topics
project
```

然后创建一个 Base，筛选：

```text
type = note
```

显示：

```text
文件名
created
topics
project
```

完成后，你已经拥有一个足够简单、但可以扩展到数千篇笔记的基础系统：

```text
统一入口
统一文件结构
统一命名
统一属性
统一附件位置
明确的链接规则
可自动更新的数据视图
```

接下来最重要的不是继续装修 Obsidian，而是用它完成一次真实的课程、研究或项目流程。知识管理系统的价值最终要在输出中体现，而不是在设置截图里体现。
# Obsidian 深化指南：模板、文档生命周期、自动化、知识连接与 PDF 研究工作流

下面把前面那套“能正常使用的仓库”，继续升级成一套可以长期运行的知识生产系统。

本文主要核对了截至 **2026 年 8 月 30 日**的英文官方文档、插件文档和研究资料。核心目标不是多安装几个插件，而是让每一份内容都沿着一条明确路径流动：

```text
捕获
  ↓
规范化
  ↓
理解与加工
  ↓
连接到已有知识
  ↓
进入项目或输出
  ↓
复查与归档
```

Obsidian 中各部分的职责应当严格分开：

```text
Markdown 正文：保存解释、证据、推理和判断
Properties：保存状态、日期、类型等可筛选数据
链接：表达知识之间的关系
Bases：显示需要处理的对象
自动化：消灭重复操作
```

Obsidian 的 Properties 会在整个仓库中保持统一的数据类型，Bases 则直接读取这些 Markdown 文件中的属性，不会把内容搬进另一个封闭数据库。模板还可以将属性合并进新笔记。因此，真正需要先设计的是少量稳定字段，而不是一堆花哨面板。([Obsidian Help](https://help.obsidian.md/bases "https://help.obsidian.md/bases"))

---

# 一、先确定系统边界

沿用前面的目录：

```text
00-Inbox
10-Daily
20-Notes
30-Projects
40-Sources
90-Attachments
99-Templates
```

现在只增加几个必要的子目录：

```text
90-Attachments/
├── Images/
├── PDF/
└── Other/

99-Templates/
├── Note.md
├── Source.md
├── Project.md
├── MOC.md
├── Daily.md
├── _partials/
└── _scripts/
```

其中：

```text
_partials：保存可被多个模板复用的片段
_scripts：保存经过检查的 Templater JavaScript
```

目录只表达“这是什么对象”：

```text
20-Notes：知识
30-Projects：项目
40-Sources：来源
```

状态不要靠移动文件表示。比如一篇论文从“待读”变成“已处理”，仍然放在 `40-Sources`，只修改：

```yaml
status: inbox
```

为：

```yaml
status: processed
```

否则文件会在十几个文件夹之间不断迁徙，内部组织看似繁忙，实际只是电子版搬家。

---

# 二、建立一个最小属性字典

## 1. 所有正式笔记的基础字段

推荐固定使用：

```yaml
---
type:
status:
created:
aliases: []
topics: []
project: []
---
```

含义如下：

|字段|类型|含义|
|---|---|---|
|`type`|文本|这是什么对象|
|`status`|文本|当前生命周期状态|
|`created`|日期|创建日期|
|`aliases`|列表|中英文名称、缩写、旧称|
|`topics`|列表|涉及的主要主题|
|`project`|列表|当前服务于哪些项目|

不要手动维护：

```yaml
updated:
```

Bases 可以直接读取文件的：

```text
file.ctime
file.mtime
```

分别表示文件创建和修改时间。手动维护 `updated` 很容易忘记，最终得到一列看起来精确、实际完全不可信的日期。Bases 还可以读取 `file.links`、文件夹、标签和其他文件属性。([Obsidian](https://obsidian.md/help/bases/syntax "https://obsidian.md/help/bases/syntax"))

## 2. 按笔记类型增加条件字段

知识笔记可以增加：

```yaml
review:
confidence:
```

来源笔记可以增加：

```yaml
authors: []
year:
citekey:
doi:
source:
rating:
```

项目笔记可以增加：

```yaml
due:
owner:
```

不要让所有笔记都带着所有字段。普通概念笔记不需要 DOI，项目笔记也没有必要填写期刊年份。人类表格设计的常见冲动，是把所有可能字段都提前建好，然后永远不填。

## 3. 固定状态值

### 知识笔记

```text
seed
developing
stable
```

含义：

```text
seed：只有想法、定义或初步材料
developing：已有证据、解释和连接
stable：已经能够被项目或写作直接调用
```

### 来源笔记

```text
inbox
reading
processed
synthesized
```

含义：

```text
inbox：只完成收集
reading：正在阅读
processed：方法、结果和局限已经处理
synthesized：已经提炼进知识笔记或项目
```

### 项目笔记

```text
active
waiting
done
archived
```

同一个 `status` 属性始终保持文本类型，只是不同 `type` 使用不同的允许值。Properties 的类型在整个 Vault 中是一致的，而且当前不支持嵌套属性，因此字段设计应保持扁平、稳定。([Obsidian Help](https://help.obsidian.md/properties "https://help.obsidian.md/properties"))

---

# 三、模板不是格式，而是一套质量控制协议

一份好模板应当同时完成三件事：

```text
1. 自动填写机器能够确定的内容
2. 提醒人完成真正需要判断的内容
3. 给后续检索、连接和使用留下接口
```

模板不应试图替代思考。

最合理的分工是：

```text
机器维护区：type、created、文件路径、文件名、来源元数据
人工写作区：结论、证据、反证、局限、关系、决策
```

## 1. 四种模板工具怎样分工

### 核心 Templates

适合：

```text
简单固定结构
插入当前日期和时间
不需要条件判断
```

它支持：

```text
{{title}}
{{date}}
{{time}}
```

模板中的 Properties 会与已有 Properties 合并。([Obsidian Help](https://help.obsidian.md/plugins/templates "https://help.obsidian.md/plugins/templates"))

### QuickAdd

适合：

```text
询问标题
创建文件
指定目录
应用模板
把新笔记链接回当前笔记
打开创建后的笔记
向已有笔记追加内容
```

QuickAdd 的 Template Choice 可以控制模板、文件名、保存路径、是否打开文件及是否把新文件链接到当前位置；Capture 可以不打开目标文件，直接把内容写入指定标题下。Macro 还能按顺序组合多个动作。([QuickAdd](https://quickadd.obsidian.guide/docs/Choices/TemplateChoice "https://quickadd.obsidian.guide/docs/Choices/TemplateChoice"))

### Templater

适合：

```text
日期计算
条件分支
弹出选择菜单
移动或重命名文件
复用模板片段
执行少量 JavaScript
```

Templater 可以使用 `tp.date`、`tp.file`、`tp.system` 等函数，也可以为不同文件夹或文件名规则配置不同模板。它同时可以运行任意 JavaScript 和系统命令，所以只应使用自己理解或来自可信来源的脚本。([Silent Void](https://silentvoid13.github.io/Templater/settings.html "https://silentvoid13.github.io/Templater/settings.html"))

### ZotLit 和 Web Clipper

它们各自使用自己的模板系统：

```text
Web Clipper：变量和 Filters
ZotLit：Liquid 或 Eta
```

不要把 `<% tp... %>`、`{{VALUE}}`、Web Clipper 变量和 ZotLit Liquid 混在同一模板里。它们长得都像双括号家族成员，但并没有亲属互认协议。

---

# 四、设计知识笔记模板

在 `99-Templates/Note.md` 中写：

```markdown
---
type: note
status: seed
created: {{DATE:YYYY-MM-DD}}
aliases: []
topics: []
project: []
review:
---

## 核心命题

用一句可以判断真假的话，写出这篇笔记最重要的主张。

## 用自己的话解释

不看原文，解释这个概念或主张是什么意思。

## 机制或推理链

它为什么可能成立？

1. 
2. 
3. 

## 证据

### 支持证据

- 

### 反面证据

- 

### 替代解释

- 

## 边界条件

- 在什么条件下成立：
- 在什么条件下可能失败：
- 是否只适用于特定人群、任务或环境：

## 与已有知识的关系

- 上位概念：
- 下位概念：
- 可能机制：
- 相似观点：
- 相反观点：
- 可应用项目：

## 我的当前判断

- 最可信的部分：
- 最不确定的部分：
- 当前置信程度及原因：

## 闭卷自测

- 问题：
- 不看笔记时的回答：

## 下一步

- [ ] 
```

这里故意没有自动填写 `confidence`。置信程度应当有依据，而不是创建文件时滑动一个精美的数字控件，给猜测套上一件实验室白大褂。

## 为什么要有“核心命题”

下面这样的标题：

```text
睡眠
工作记忆
选择偏差
```

适合建立概念入口。

但很多真正有价值的知识，更适合写成命题：

```text
睡眠限制可能降低延迟回忆表现
随机斜率可以吸收个体之间的效应异质性
选择偏差可能反转观察研究中的关联方向
```

命题笔记更容易被：

```text
支持
反驳
限定
应用
```

也更容易直接进入论文、报告或研究决策。

## 为什么要有“闭卷自测”

把资料链接在一起，并不自动等于学会了。关系图再漂亮，也只是软件发现你打了很多双方括号。

检索练习要求主动从记忆中提取信息。在 Karpicke 与 Blunt 的实验中，检索练习产生的学习效果超过了精细学习中的概念图活动，不过这种结果不能机械推广到所有材料和场景。生成式学习研究也强调，自我解释、绘图和把新材料联系到已有知识，通常比单纯重读或高亮包含更多认知加工。([Science](https://www.science.org/doi/abs/10.1126/science.1199327 "https://www.science.org/doi/abs/10.1126/science.1199327"))

因此，稳定知识笔记至少应该有一个可以闭卷回答的问题。

---

# 五、使用 QuickAdd 创建知识笔记

## 1. 建立 Template Choice

进入：

```text
设置
→ QuickAdd
→ Add Choice
→ Template
```

命名：

```text
新建知识笔记
```

设置：

```text
Template Path：
99-Templates/Note.md

File Name Format：
{{VALUE:title|label:请输入明确的笔记标题|trim}}

Create in folder：
20-Notes

Open：
开启
```

QuickAdd 的命名变量可以重复使用，还支持文本、多行文本、数字、滑块和复选框等输入类型。当前版本也会在执行后续副作用前检查无效文件名，减少创建了一半才发现名称不合法的尴尬。([QuickAdd](https://quickadd.obsidian.guide/docs/Choices/TemplateChoice "https://quickadd.obsidian.guide/docs/Choices/TemplateChoice"))

## 2. 开启“链接到当前文件”

当你在来源笔记或项目笔记中创建知识笔记时，可以开启：

```text
Link to created file
```

将链接插入当前光标处。

例如你正在阅读：

```text
Smith 2025 - Sleep Restriction and Memory
```

在“可提炼的知识”下调用 QuickAdd：

```markdown
## 可提炼的知识

- [[睡眠限制可能损害记忆巩固]]
```

新笔记创建后，来源和知识之间的第一条连接已经建立，不需要事后回忆“这篇笔记到底是从哪里长出来的”。

---

# 六、使用 Templater 深化模板

QuickAdd 负责“创建动作”，Templater负责“动态内容”。两者可以合作，但不要让两者同时负责文件移动和命名，否则出错时会像两个过度热情的搬运工，各自把箱子送到不同楼层。

## 1. 动态日期

Templater 写法：

```yaml
created: <% tp.date.now("YYYY-MM-DD") %>
review: <% tp.date.now("YYYY-MM-DD", 14) %>
```

这会把复查日期设置为创建日期后的 14 天。`tp.date.now()` 支持格式和日期偏移。([Silent Void](https://silentvoid13.github.io/Templater/internal-functions/internal-modules/date-module.html "https://silentvoid13.github.io/Templater/internal-functions/internal-modules/date-module.html"))

## 2. 弹出类型选择

```yaml
subtype: <% await tp.system.suggester(
  ["概念", "命题", "方法"],
  ["concept", "claim", "method"]
) %>
```

创建笔记时会弹出菜单。

不过不要为每个字段都弹窗。创建一篇笔记前连续回答八个对话框，会把快速记录变成海关申报。

## 3. 设置光标位置

在模板中写：

```markdown
## 核心命题

<% tp.file.cursor(1) %>
```

插入模板后，光标会移动到该位置。([Silent Void](https://silentvoid13.github.io/Templater/internal-functions/internal-modules/file-module.html "https://silentvoid13.github.io/Templater/internal-functions/internal-modules/file-module.html"))

## 4. 复用模板片段

建立：

```text
99-Templates/_partials/证据审计.md
```

内容：

```markdown
## 证据审计

- 证据类型：
- 样本与代表性：
- 测量可靠性：
- 效应大小：
- 不确定性：
- 主要混杂：
- 替代解释：
- 可能推翻结论的证据：
```

在其他模板中插入：

```markdown
<% await tp.file.include("[[99-Templates/_partials/证据审计]]") %>
```

Templater 可以嵌入其他笔记或其中的特定章节，因此多个模板共用的“方法审计”“决策记录”“复查问题”不必复制多份。([Silent Void](https://silentvoid13.github.io/Templater/internal-functions/internal-modules/file-module.html "https://silentvoid13.github.io/Templater/internal-functions/internal-modules/file-module.html"))

## 5. 文件夹自动模板

Templater 可以开启：

```text
Trigger Templater on new file creation
```

然后配置：

```text
20-Notes → Note.md
30-Projects → Project.md
40-Sources → Source.md
```

规则重叠时，更深层文件夹的规则优先。还可以排除：

```text
99-Templates
90-Attachments
40-Sources/Zotero
```

建议先通过命令手动插入模板。连续正常使用一两周后，再开启自动触发。因为自动触发不仅会执行模板，也可能执行其中的脚本或系统命令。Templater 官方文档明确提醒，未知模板代码可能是不安全的。([Silent Void](https://silentvoid13.github.io/Templater/settings.html "https://silentvoid13.github.io/Templater/settings.html"))

---

# 七、来源与 PDF 笔记模板

在 `99-Templates/Source.md` 中建立：

```markdown
---
type: source
status: inbox
created: {{DATE:YYYY-MM-DD}}
authors: []
year:
citekey:
doi:
source:
rating:
aliases: []
topics: []
project: []
---

## 为什么保存或阅读

这项来源与哪个问题、假设或项目有关？

## 来源试图回答什么

## 一句话结论

关闭原文后，用自己的话写。

## 方法审计

- 研究设计：
- 样本与纳入标准：
- 主要变量：
- 测量方法：
- 分析方法：
- 对照或比较条件：
- 预注册情况：
- 缺失数据处理：

## 主张与证据

| 作者的主张 | 证据位置 | 数据或效应 | 不确定性 | 我的判断 |
|---|---|---|---|---|
|  |  |  |  |  |

## 关键结果

### 结果 1

- 结果：
- 效应大小：
- 置信区间或其他不确定性：
- 页面或注释链接：

### 结果 2

- 结果：
- 效应大小：
- 置信区间或其他不确定性：
- 页面或注释链接：

## 局限与替代解释

- 选择偏差：
- 测量误差：
- 混杂：
- 多重比较：
- 外部效度：
- 与其他证据的冲突：

## 我的判断

### 我接受什么

### 我暂不接受什么

### 什么证据会改变判断

## 可提炼的知识笔记

- [[ ]]

## 可用于写作的综合表述

使用自己的话写一段可以进入论文或报告的综合，而不是复制摘要。

## 下一步

- [ ] 
```

## 来源状态的退出标准

不能仅凭“看完 PDF”把状态改成 `processed`。

建议使用以下标准：

|状态|退出标准|
|---|---|
|`inbox`|已决定确实值得阅读|
|`reading`|已完成方法、结果和局限处理|
|`processed`|已写出自己的判断和可提炼命题|
|`synthesized`|至少一个结果已经进入知识笔记或项目|

`finished` 和 `synthesized` 必须区分：

```text
finished：眼睛已经扫过
synthesized：内容已经进入自己的知识结构
```

这两个状态之间，通常隔着真正的学习工作。

---

# 八、项目模板

在 `99-Templates/Project.md` 中写：

```markdown
---
type: project
status: active
created: {{DATE:YYYY-MM-DD}}
due:
aliases: []
topics: []
---

## 最终交付物

这个项目最终会产生什么？

## 完成标准

- [ ] 
- [ ] 
- [ ] 

## 核心问题或假设

1. 
2. 
3. 

## 当前判断

## 证据地图

| 主张 | 支持证据 | 反面证据 | 当前判断 |
|---|---|---|---|
|  |  |  |  |

## 相关知识

- 

## 相关来源

- 

## 下一步行动

- [ ] 

## 决策记录

## 风险与阻塞

## 输出草稿

## 项目复盘

- 哪些假设正确：
- 哪些假设错误：
- 哪些流程有效：
- 下次应改变什么：
```

项目模板应围绕“输出”和“决策”，而不是围绕“收藏了多少笔记”。

项目笔记是知识系统的消费端：

```text
Sources 提供证据
Notes 提供解释和命题
Project 把它们组合成结果
```

---

# 九、MOC 模板：手工建立知识地图

MOC 可以理解为 Map of Content，即主题导航或综合入口。

在 `99-Templates/MOC.md` 中写：

```markdown
---
type: moc
status: active
created: {{DATE:YYYY-MM-DD}}
aliases: []
topics: []
project: []
---

## 范围

这个主题包含什么，不包含什么？

## 核心概念

- 

## 主要机制

- 

## 关键命题

### 相对稳定的结论

- 

### 尚有争议的结论

- 

### 已被削弱或推翻的结论

- 

## 证据地图

| 命题 | 支持来源 | 反面来源 | 当前可信度 |
|---|---|---|---|
|  |  |  |  |

## 方法与测量问题

- 

## 开放问题

- 

## 相关项目

- 
```

MOC 不是另一套层级目录。

创建 MOC 的实际触发条件可以是：

```text
某个主题已经有约 8 到 15 篇相关笔记
你频繁在这些笔记之间来回导航
你需要比较不同观点或证据
你正在围绕该主题写作
```

这个数量只是实用启发，不是宇宙法则。只有三篇笔记时建立一个“宏大知识地图”，通常只是给空房间安装导览牌。

---

# 十、建立清晰的文档生命周期

推荐流程如下：

```text
00-Inbox
   ↓
分类与命名
   ↓
20-Notes / 30-Projects / 40-Sources
   ↓
加工与连接
   ↓
项目使用
   ↓
复查或归档
```

## 阶段 1：捕获

捕获时只要求：

```text
内容没有丢
知道它来自哪里
知道为什么值得保留
```

不要求立刻填写所有属性。

可以进入：

```text
00-Inbox
```

或者当天的 Daily Note。

## 阶段 2：分流

每天或每周处理 Inbox。

每一项只能做以下决定之一：

```text
删除
合并到已有笔记
转成知识笔记
转成来源笔记
转成项目笔记
保留在 Daily Note
```

不要建立“可能以后有用”“暂时不知道”“以后再说”三个不同文件夹。它们是同一种状态，名字叫拖延。

## 阶段 3：规范化

正式保留时完成：

```text
明确文件名
插入正确模板
填写 type
填写 status
移动到永久目录
保留来源或上下文
```

文件只在这一阶段移动一次。

## 阶段 4：加工

知识笔记至少回答：

```text
它主张什么？
为什么可能成立？
证据是什么？
什么会反驳它？
与哪些已有知识有关？
```

来源笔记至少回答：

```text
研究问题是什么？
方法可靠吗？
结果有多大？
不确定性是多少？
有什么替代解释？
```

## 阶段 5：连接

一篇知识笔记进入 `stable` 前，建议至少具有：

```text
一个来源或证据连接
一个概念、命题或项目连接
```

这不是形式检查，而是防止生成大量孤立摘要。

## 阶段 6：使用

只有进入以下场景，知识才真正产生价值：

```text
论文
报告
实验设计
决策
课程输出
代码或分析说明
```

项目笔记中应直接链接或嵌入相关知识，而不是再次手工复制一份。

## 阶段 7：复查

复查不等于从头重读。

一次复查可以只做：

```text
闭卷回答问题
检查是否出现新证据
修改当前判断
补充反面链接
确认该笔记是否仍服务于项目
```

## 阶段 8：归档

项目完成后：

```yaml
status: done
```

复盘完成后：

```yaml
status: archived
```

知识笔记一般不需要移动进 Archive。知识不是项目结束后就突然失去公民身份。

---

# 十一、用 Bases 让流程自动显现

Bases 可以建立多个表格、列表或卡片视图，并按属性、文件夹和公式进行筛选、排序和分组。一个 Base 可以包含多个视图，也可以嵌入普通笔记。([Obsidian Help](https://help.obsidian.md/bases/views "https://help.obsidian.md/bases/views"))

建议建立：

```text
Knowledge System.base
```

里面只需要五个视图。

## 1. Inbox

筛选条件：

```text
文件位于 00-Inbox
```

显示：

```text
文件名
创建时间
修改时间
```

## 2. 正在阅读

筛选：

```text
type = source
status = reading
```

显示：

```text
文件名
authors
year
topics
project
rating
file.mtime
```

## 3. 综合债务

筛选：

```text
type = source
status = processed
```

这里显示的是：

> 已经阅读和分析，但还没有进入知识或项目的来源。

这是一种真正需要处理的积压，比“未读论文数量”更有意义。

## 4. 活跃项目

筛选：

```text
type = project
status = active
```

显示：

```text
文件名
due
topics
file.mtime
```

按 `due` 升序。

## 5. 连接不足

Bases 可以计算 `file.links.length`。下面是一个可选的 `.base` 文件示例：

```yaml
filters:
  and:
    - 'file.ext == "md"'
    - 'type == "note"'

formulas:
  outgoing_links: 'file.links.length'

properties:
  formula.outgoing_links:
    displayName: 出链数

views:
  - type: table
    name: 连接不足
    filters:
      and:
        - 'formula.outgoing_links < 2'
    order:
      - file.name
      - status
      - topics
      - formula.outgoing_links
      - file.mtime
```

这里不是说每篇笔记必须达到一个神圣的链接配额，而是把可能孤立的笔记暴露出来，供人工检查。Bases 的文件对象提供 `file.links`，列表支持 `.length`；它也支持 `file.hasLink()`、文件夹判断和日期函数。([Obsidian](https://obsidian.md/help/bases/syntax "https://obsidian.md/help/bases/syntax"))

不要在大型 Vault 中到处用 `file.backlinks` 计算所有反向链接。官方文档指出它的反向查找开销较高，而且刷新行为有限。需要在某篇笔记中显示“哪些文件链接到当前笔记”时，更适合使用：

```text
file.hasLink(this.file)
```

作为嵌入 Base 的筛选条件。([Obsidian](https://obsidian.md/help/bases/syntax "https://obsidian.md/help/bases/syntax"))

最后在 `Home.md` 中嵌入：

```markdown
## 当前阅读

![[Knowledge System.base#正在阅读]]

## 等待综合

![[Knowledge System.base#综合债务]]

## 活跃项目

![[Knowledge System.base#活跃项目]]

## 连接检查

![[Knowledge System.base#连接不足]]
```

Base 支持通过 `![[文件.base#视图名称]]` 嵌入特定视图。([Obsidian Help](https://help.obsidian.md/bases/views "https://help.obsidian.md/bases/views"))

---

# 十二、用 QuickAdd 建立四条自动化

自动化应遵循一条规则：

> 只有当某个步骤已经重复出现，而且规则稳定，才自动化它。

不要自动化尚未理解的流程。否则只是更快地产生错误。

## 自动化 1：快速捕获到 Daily Note

QuickAdd Choice 类型：

```text
Capture
```

目标：

```text
当天 Daily Note
```

插入标题：

```markdown
## 快速记录
```

格式：

```markdown
- {{DATE:HH:mm}} {{VALUE:entry|label:记录内容|type:multiline|trim}}
```

开启：

```text
如果标题不存在则创建
插入到该标题末尾
```

QuickAdd Capture 可以定位标题、在标题下插入内容，并可按正序或倒序组织条目。([QuickAdd](https://quickadd.obsidian.guide/docs/Choices/CaptureChoice "https://quickadd.obsidian.guide/docs/Choices/CaptureChoice"))

最终只需要一个快捷键：

```text
按快捷键
→ 输入内容
→ Enter
```

## 自动化 2：新建知识笔记

前面已经配置：

```text
Template Choice
→ Note.md
→ 20-Notes
→ 自动打开
→ 链接回当前笔记
```

适合从来源笔记、项目或 Daily Note 中提炼概念。

## 自动化 3：新建来源笔记

File Name Format 可以使用：

```text
{{VALUE:first_author|label:第一作者|trim}} {{VALUE:year|label:年份|trim}} - {{VALUE:short_title|label:短标题|trim}}
```

模板：

```text
99-Templates/Source.md
```

目录：

```text
40-Sources
```

创建后自动打开。

不要在 QuickAdd 中要求填写二十项文献信息。作者、年份和标题足够完成文件创建，其余元数据在真正处理来源时填写。

## 自动化 4：追加项目决策

建立 Capture：

```markdown
### {{DATE:YYYY-MM-DD HH:mm}}

- 决策：{{VALUE:decision|label:做出了什么决定|type:multiline|trim}}
- 依据：{{VALUE:evidence|label:依据是什么|type:multiline|optional}}
- 被否决方案：{{VALUE:rejected|label:放弃了什么方案|type:multiline|optional}}
- 复查条件：{{VALUE:revisit|label:何时需要重新考虑|type:multiline|optional}}
```

插入项目笔记的：

```markdown
## 决策记录
```

研究项目中，“为什么采用这个模型”“为什么排除这些数据”“为什么修改主要结局”往往比最终文件本身更重要。自动记录这些决策，能减少事后合理化和记忆重写。

## Macro 应该做什么

可以建立一个每周复查 Macro：

```text
创建本周复查笔记
→ 打开 Home
→ 打开 Inbox Base
→ 打开综合债务视图
→ 打开活跃项目视图
```

Macro 可以串联 QuickAdd 动作、Obsidian 命令和脚本，并在动作之间共享变量。推荐保持模块化，不要一开始编写一个负责创建、重命名、移动、打标签、调用 AI、归档并发送通知的万能宏。万能工具在人类历史上通常只万能地制造维护工作。([QuickAdd](https://quickadd.obsidian.guide/docs/Choices/MacroChoice "https://quickadd.obsidian.guide/docs/Choices/MacroChoice"))

---

# 十三、Web Clipper 自动进入来源流程

Obsidian Web Clipper 的模板可以：

```text
创建新笔记
追加到已有笔记
追加到 Daily Note
根据网页 URL 或 Schema 自动选择模板
```

模板变量可以用于文件名、目录、Properties 和正文。常用变量包括标题、作者、发布日期、网址、正文、选中文字和高亮内容；Filters 可以清理文件名、格式化日期或将内容转换为 Markdown。([Obsidian Help](https://help.obsidian.md/web-clipper/templates "https://help.obsidian.md/web-clipper/templates"))

## 推荐网页模板

文件名：

```text
{{title|safe_name}}
```

目录：

```text
40-Sources/Web
```

属性：

```yaml
type: source
status: inbox
source: {{url}}
author: {{author}}
published: {{published}}
captured: {{date}}
topics: []
project: []
```

正文：

```markdown
## 为什么保存

## 当前相关问题

## 选中内容

{{selection}}

## 网页高亮

{{highlights}}

## 网页内容

{{content}}

## 我的初步判断

- 主要主张：
- 提供的证据：
- 可信度问题：
- 需要核查：
- 可连接笔记：
```

Web Clipper 自带高亮器，可以将选中内容保存到模板变量中。([Obsidian Help](https://help.obsidian.md/web-clipper/highlight "https://help.obsidian.md/web-clipper/highlight"))

网页正文不要一剪了之。保存后仍然应经过：

```text
inbox
→ processed
→ synthesized
```

否则 Web Clipper 只是一个速度更快的数字垃圾抽屉。

对于标题、作者、URL 这类页面已经明确提供的信息，优先使用确定性变量。没有必要调用模型“猜测”页面标题，不仅更慢，还会额外引入费用、隐私和错误来源。

---

# 十四、Linter 只负责格式，不负责知识

Linter 适合：

```text
统一 YAML 键顺序
补充 YAML 后的空行
删除行尾空格
规范标题前后空行
确保文件末尾换行
```

建议初始规则：

```text
YAML key sort
YAML title alias
Blank line after YAML
Heading blank lines
Trailing spaces
Paragraph blank lines
Final newline
```

开始时不要启用：

```text
保存时自动执行全部规则
整个 Vault 批量格式化
不理解的标题和列表重写规则
```

Linter 文档明确指出，部分规则组合后可能相互冲突或产生非预期结果，应逐条启用并在测试笔记中检查。([GitHub](https://github.com/platers/obsidian-linter "https://github.com/platers/obsidian-linter"))

特别注意：

```text
ZotLit 管理区
Web Clipper 生成区
复杂代码块
数学公式
```

先验证不会被 Linter 错改，再纳入自动运行。

---

# 十五、怎样深化知识之间的连接

## 1. 建立三层连接模型

推荐把信息分成三层：

```text
第一层：来源
PDF、论文、网页、书籍、课程、访谈

第二层：知识
概念、命题、方法、机制、证据判断

第三层：使用
项目、论文、报告、实验、决策
```

正确流动方式：

```text
PDF 中的结果
→ 来源笔记中的证据
→ 知识笔记中的综合命题
→ 项目中的实际使用
```

不推荐：

```text
PDF 高亮
→ 另一堆高亮
→ 更多高亮
→ 某天突然期待它们自己写成论文
```

## 2. 在句子中表达关系

弱连接：

```markdown
相关：
- [[睡眠限制]]
- [[记忆巩固]]
- [[工作记忆]]
```

强连接：

```markdown
[[睡眠限制]]可能通过干扰[[记忆巩固]]降低延迟回忆表现，但在高复杂度任务中，[[工作记忆]]负荷也可能构成替代解释。
```

后一种写法保留了：

```text
方向
机制
条件
替代解释
```

## 3. 建立一套关系语法

不必安装专门的“关系类型”插件，可以直接在自然语言中使用：

```text
分类关系：
[[随机斜率]]是一种[[随机效应]]。

机制关系：
[[睡眠限制]]可能通过[[记忆巩固受损]]影响延迟回忆。

支持关系：
[[Smith 2025]]支持[[睡眠限制降低延迟回忆]]。

反驳关系：
[[Lee 2024]]没有复现[[睡眠限制降低延迟回忆]]。

边界关系：
[[任务复杂度]]可能是该效应的边界条件。

测量关系：
[[反应时任务]]被用于操作化[[加工速度]]。

应用关系：
[[层级模型]]可用于项目[[毕业论文]]中的重复测量数据。
```

## 4. 每篇知识笔记保留证据链

例如：

```markdown
## 证据链

### 支持

- [[Smith 2025 - Sleep Restriction and Memory#关键结果]]
  - 实验设计支持时间顺序。
  - 效应量中等。
  - 样本量较小。

### 反面

- [[Lee 2024 - Replication Study#关键结果]]
  - 没有观察到主效应。
  - 任务复杂度较低。

### 当前综合

效应可能依赖任务复杂度，而不是对所有记忆任务普遍存在。
```

这样，知识笔记不是“某篇论文的摘要”，而是多个证据之间的裁决场。

## 5. 使用别名统一中英文和缩写

```yaml
aliases:
  - Cognitive Load Theory
  - CLT
  - 认知负荷
```

别名可用于内部链接搜索和替代显示名称。([Obsidian Help](https://help.obsidian.md/aliases "https://help.obsidian.md/aliases"))

中文主文件名建议保留：

```text
认知负荷理论
```

英文名和缩写放进 `aliases`。除非主要写作语言是英语，否则不必为同一概念建立两篇平行笔记。

## 6. 定期检查未链接提及

Outgoing Links 面板不仅显示当前笔记已有出链，也可以显示与现有笔记标题或别名匹配、但尚未建立链接的未链接提及。([Obsidian Help](https://help.obsidian.md/plugins/outgoing-links "https://help.obsidian.md/plugins/outgoing-links"))

每周可以检查一次：

```text
当前重要笔记
→ Outgoing Links
→ Unlinked mentions
```

但不要看到每个匹配词就立刻链接。“模型”“研究”“方法”这类普通词没有必要全部变成蓝色交通枢纽。

## 7. 图谱只用于审计

Local Graph 可以围绕当前笔记显示一定深度的邻接关系。([Obsidian Help](https://help.obsidian.md/plugins/graph "https://help.obsidian.md/plugins/graph"))

推荐用途：

```text
检查是否只有来源，没有综合笔记
检查项目是否连接到实际证据
发现某个主题被错误拆成多个名称
发现完全孤立的笔记
```

不推荐把全局图谱的节点数量当作进步指标。细菌培养皿也能快速增加节点，并不代表它写得出毕业论文。

---

# 十六、PDF 管理先做一个关键选择

PDF 有两种合理管理模式。

## 模式 A：Zotero 管理学术 PDF

适合：

```text
论文
书籍章节
会议论文
预印本
需要引用的研究来源
```

分工：

```text
Zotero：条目、PDF、注释、全文检索、引用信息
Obsidian：阅读目的、方法审计、证据综合、知识连接、项目写作
```

## 模式 B：Obsidian 管理独立 PDF

适合：

```text
课程讲义
内部报告
产品说明书
政策文件
不需要正式文献管理的材料
```

分工：

```text
90-Attachments/PDF：保存文件
40-Sources：保存配套来源笔记
PDF++：可选的深度阅读和选区链接工具
```

不要把所有 Zotero PDF 再复制一份到 Obsidian。重复文件会导致：

```text
两个版本
两套注释
两个备份位置
不知道哪份是最新
```

数字文件虽然不会抱怨，但非常擅长安静地制造版本灾难。

---

# 十七、Zotero + ZotLit 的完整学术 PDF 流程

## 1. 让 Zotero 成为 PDF 的权威存储位置

Zotero 区分：

```text
Stored files：复制并存储在 Zotero 数据目录
Linked files：链接到外部文件位置
```

对大多数用户，Zotero 官方更推荐 Stored files，因为它们更容易通过 Zotero 自身同步和管理。Linked files 需要自己设计外部文件同步方案。([Zotero](https://www.zotero.org/support/attaching_files "https://www.zotero.org/support/attaching_files"))

因此推荐：

```text
论文 PDF → Zotero Stored Attachment
Obsidian Vault → 不再存第二份 PDF
```

需要分别备份：

```text
Obsidian Vault
Zotero 数据目录
```

只备份 Obsidian，不等于备份了 Zotero 中的论文和注释。Zotero 官方也建议对数据目录进行独立备份。([Zotero](https://www.zotero.org/support/zotero_data "https://www.zotero.org/support/zotero_data"))

## 2. 先修正元数据

导入后检查：

```text
标题
作者
年份
期刊
DOI
条目类型
citation key
```

不要等到论文写完才发现作者字段里混入了实验室名称，年份来自网页访问日期，标题全部是大写。引用管理软件也会忠实保存错误，忠诚得令人不安。

## 3. 第一遍阅读：判断是否值得深读

只看：

```text
摘要
研究问题
主要图表
结论
方法概况
```

然后决定：

```text
放弃
保留备用
精读
```

这一遍不要大量高亮。

## 4. 第二遍阅读：提取证据

建议最多使用四种颜色：

|颜色|功能|
|---|---|
|黄色|作者的核心主张|
|蓝色|方法、样本、测量和统计|
|红色|局限、矛盾和风险|
|绿色|可用于自己综合或写作的内容|

颜色只是功能标签，不应代表“我相信”或“我不相信”。真正的判断写在注释文本里。

每条重要高亮尽量补一句注释：

```text
为什么重要
支持哪个问题
可能有什么局限
准备连接到哪篇笔记
```

Zotero 的注释默认保存在数据库中，而不是直接改写 PDF，这有利于同步和注释管理；注释可以被拖入 Zotero 笔记，并保留页面链接和引用信息。([Zotero](https://www.zotero.org/support/pdf_reader "https://www.zotero.org/support/pdf_reader"))

## 5. 用 ZotLit 创建一对一文献笔记

ZotLit 会基于 Zotero 条目创建 Markdown 文献笔记，并使用 `zotero-key` 识别一对一对应关系。它支持独立管理区，只更新 Zotero 派生的内容，而保留你在管理区之外的写作。([ZotLit](https://zotlit.aidenlx.site/docs/how-to/configure-frontmatter-properties "https://zotlit.aidenlx.site/docs/how-to/configure-frontmatter-properties"))

推荐结构：

```markdown
---
type: source
status: reading
zotero-key:
citekey:
title:
authors: []
year:
doi:
topics: []
project: []
rating:
---

## 我的阅读目的

## 一句话结论

## 方法审计

## 主张与证据

## 局限与反证

## 我的判断

## 可提炼的知识笔记

## 可用于写作的综合

[ZotLit managed region]
```

ZotLit 管理区中可以放：

```text
Zotero 元数据
附件链接
注释
高亮
Zotero collections
```

管理区外放：

```text
自己的问题
方法判断
证据综合
知识链接
写作草稿
```

不要手动改写管理区标记。否则下一次更新时，你会和自动化进行一场没有裁判的领土争端。

## 6. 设置 Frontmatter 合并策略

建议分成两类。

### Zotero 权威字段

```text
title
authors
year
doi
citekey
zotero-key
```

更新策略：

```text
Replace
```

### Obsidian 人工字段

```text
status
topics
project
rating
```

更新策略：

```text
Keep existing
或 Append
```

ZotLit 的 Frontmatter 模板支持将 Zotero 数据映射到 YAML，并为字段选择不同合并策略。([ZotLit](https://zotlit.aidenlx.site/docs/how-to/customize-a-template "https://zotlit.aidenlx.site/docs/how-to/customize-a-template"))

## 7. 使用 ZotLit Annotations View

ZotLit 的注释侧栏可以显示当前 Zotero 条目的注释，并允许拖入 Obsidian 笔记。([ZotLit](https://zotlit.aidenlx.site/docs/how-to/use-annotation-view "https://zotlit.aidenlx.site/docs/how-to/use-annotation-view"))

不要把所有高亮一次性导入正文。

推荐流程：

```text
选中一条与当前问题有关的注释
→ 拖入“主张与证据”
→ 写出自己的解释
→ 补充方法限制
→ 链接到知识笔记
```

每篇论文最终提炼出一到三条真正有用的知识命题，通常已经足够。这个数量是工作流启发，不是强制比例。

## 8. 关闭 PDF 后写结论

完成阅读后先关闭 PDF，写：

```markdown
## 一句话结论

作者发现了什么？
证据强度如何？
最重要的限制是什么？
```

然后重新打开 PDF 核对。

这个步骤迫使自己进行检索和重构，而不是把作者原句稍微换几个连接词。检索练习的实验研究为这种“先回忆，再核对”的做法提供了学习科学上的依据。([Science](https://www.science.org/doi/abs/10.1126/science.1199327 "https://www.science.org/doi/abs/10.1126/science.1199327"))

## 9. 从来源笔记提炼知识笔记

来源笔记：

```text
Smith 2025 - Sleep Restriction and Memory
```

可以产生：

```text
睡眠限制可能损害记忆巩固
睡眠研究中的自我报告测量存在系统误差
任务复杂度可能调节睡眠与记忆的关系
```

知识笔记中写：

```markdown
[[睡眠限制]]可能通过干扰[[记忆巩固]]降低延迟回忆。

支持证据：
- [[Smith 2025 - Sleep Restriction and Memory#关键结果]]

反面或限制性证据：
- [[Lee 2024 - Replication Study#关键结果]]

当前综合：
效应可能在复杂任务中更明显，因此[[任务复杂度]]可能是边界条件。
```

完成后将来源状态改为：

```yaml
status: synthesized
```

## 10. 写作和引用

ZotLit 支持插入 Pandoc 风格引用：

```markdown
睡眠限制可能损害延迟回忆表现 [@smith2025sleep]。
```

它还支持通过 Pandoc 工作流导出带格式化引用和参考文献的 Word 文档，同时不需要永久改写原始 Markdown。([ZotLit](https://zotlit.aidenlx.site/docs/tutorial/write-and-export-cited-note "https://zotlit.aidenlx.site/docs/tutorial/write-and-export-cited-note"))

---

# 十八、在 Obsidian 内直接管理 PDF

对于课程讲义、报告等独立 PDF：

```text
90-Attachments/PDF/2026-Agency-Report-Short-Title.pdf
```

配套建立：

```text
40-Sources/Agency 2026 - Short Title.md
```

属性：

```yaml
---
type: source
status: reading
created: 2026-08-30
source:
pdf: "[[2026-Agency-Report-Short-Title.pdf]]"
topics: []
project: []
---
```

## 1. 核心 PDF 链接

普通链接：

```markdown
[[2026-Agency-Report-Short-Title.pdf]]
```

嵌入 PDF：

```markdown
![[2026-Agency-Report-Short-Title.pdf]]
```

打开或嵌入指定页：

```markdown
![[2026-Agency-Report-Short-Title.pdf#page=17]]
```

设置嵌入高度：

```markdown
![[2026-Agency-Report-Short-Title.pdf#height=500]]
```

Obsidian 原生支持 PDF 嵌入、页码定位和阅读器高度设置。([Obsidian Help](https://help.obsidian.md/embeds "https://help.obsidian.md/embeds"))

## 2. 使用 PDF++ 建立文本选区链接

PDF++ 比较有价值的模式是：

```text
在 PDF 中选择文字
→ 复制选区链接
→ 粘贴到来源或知识笔记
→ PDF 中相应位置显示高亮
```

其反向链接高亮模式可以通过指向 PDF 文本选择的 Markdown 链接显示高亮，而不直接修改 PDF。这样，注释和解释仍保存在 Markdown 中。([GitHub](https://github.com/ryotaushio/obsidian-pdf-plus "https://github.com/ryotaushio/obsidian-pdf-plus"))

例如：

```markdown
## 关键证据

> 原文选区链接

我的解释：
该结果支持 [[任务复杂度调节工作记忆负荷]]。

方法限制：
样本只包含大学生，外部效度有限。
```

## 3. 谨慎使用“直接写入 PDF”

PDF++ 也提供直接把注释写入 PDF 的模式，使它们能在其他 PDF 阅读器中显示。

但是：

```text
该功能具有实验性
会修改原始 PDF
需要可靠备份
插件使用部分 Obsidian 私有 API
Obsidian 更新后可能出现兼容性问题
```

因此默认推荐：

```text
PDF 保持不变
注释和判断保存在 Markdown
选区通过链接关联
```

只有明确需要跨软件共享 PDF 注释时，才考虑直接写入。([GitHub](https://github.com/ryotaushio/obsidian-pdf-plus "https://github.com/ryotaushio/obsidian-pdf-plus"))

---

# 十九、PDF 全文检索应该在哪里完成

Obsidian 原生搜索主要搜索笔记和 Canvas，并不把 PDF 全文作为原生搜索主体。([Obsidian Help](https://help.obsidian.md/plugins/search "https://help.obsidian.md/plugins/search"))

因此推荐：

```text
学术论文全文检索：Zotero
Markdown 知识检索：Obsidian
```

Zotero 可以为 PDF、EPUB、HTML 和文本附件建立全文索引，并搜索附件内容。([Zotero](https://www.zotero.org/support/searching "https://www.zotero.org/support/searching"))

Obsidian 中可以选装：

```text
Omnisearch
Text Extractor
```

Text Extractor 会提取并缓存部分 PDF、图片和 Office 文档文本，供其他插件使用。但 PDF 提取可能失败，移动端通常不能执行提取，缓存还需要考虑同步。它适合作为便利工具，不适合作为唯一的学术全文检索系统。([GitHub](https://github.com/scambier/obsidian-text-extractor "https://github.com/scambier/obsidian-text-extractor"))

对于扫描版 PDF，如果页面本质上只是图片，需要先进行 OCR，才能可靠搜索和选择文字。

---

# 二十、PDF 阅读时使用“三遍法”

## 第一遍：相关性判断

只回答：

```text
这项来源与我的问题有关吗？
它大概声称什么？
证据类型是什么？
是否值得精读？
```

输出：

```yaml
status: inbox
```

或：

```yaml
status: reading
```

## 第二遍：证据审计

重点阅读：

```text
方法
样本
测量
结果
图表
敏感性分析
局限
```

填写：

```text
主张与证据表
方法审计
替代解释
```

## 第三遍：综合

关闭 PDF 后写：

```text
一句话结论
最强证据
最大局限
与已有知识的关系
能否用于当前项目
```

然后创建知识笔记或更新 MOC。

这种流程能把：

```text
阅读活动
```

转变成：

```text
可检查的判断
```

---

# 二十一、怎样避免“高亮仓库”

高亮之后必须进行至少一种转换：

```text
原文 → 自己的解释
原文 → 证据判断
原文 → 方法限制
原文 → 知识命题
原文 → 项目决策
```

推荐格式：

```markdown
> 原文或 PDF 选区链接

**我的解释：**

**它支持什么：**

**它没有证明什么：**

**方法限制：**

**相关笔记：**
```

直接引文和自己的表述必须分开。

不要写：

```markdown
作者认为这项结果非常重要，而且说明了……
```

却在三个月后无法判断前半句是原文、自己的转述，还是当时心情较好产生的过度解读。

---

# 二十二、每周维护流程

每周只需要完成以下五步。

## 1. 清空 Inbox

每一项：

```text
删除
合并
转为正式笔记
转为来源
转为项目
```

## 2. 检查综合债务

打开：

```text
type = source
status = processed
```

选择最重要的来源，至少提炼一个知识命题或项目结论。

## 3. 检查活跃项目

每个项目必须有：

```markdown
## 下一步行动

- [ ] 一个具体、可执行的动作
```

“继续研究”“多看一些资料”不算动作。它们只是拖延穿上了学术服装。

## 4. 检查连接不足

对于出链较少的知识笔记，判断：

```text
应该删除？
应该合并？
缺少来源？
缺少上位概念？
缺少项目应用？
```

不是机械补链接。

## 5. 做一次闭卷复查

从一篇重要知识笔记中，只看标题和自测问题，先回答，再打开正文核对。

---

# 二十三、推荐的最终自动化结构

```text
输入层
├── QuickAdd Capture
├── Web Clipper
├── Zotero
└── Daily Notes

创建层
├── QuickAdd Template Choice
├── Core Templates
└── Templater

管理层
├── Properties
├── Bases
└── Linter

连接层
├── Internal Links
├── Aliases
├── Backlinks
├── Outgoing Links
└── MOC

PDF 层
├── Zotero + ZotLit
└── 或 Obsidian + PDF++

输出层
├── Project Notes
├── Pandoc citations
└── Word / Markdown / reports
```

---

# 二十四、实施顺序

不要一次全部实施。按下面顺序，系统更容易稳定。

## 第一阶段：模板和字段

完成：

```text
统一 type
统一 status
建立 Note.md
建立 Source.md
建立 Project.md
```

先手动使用一周，删除没有实际填写价值的字段。

## 第二阶段：QuickAdd

配置：

```text
快速捕获
新建知识笔记
新建来源笔记
追加项目决策
```

## 第三阶段：Bases

建立：

```text
Inbox
正在阅读
综合债务
活跃项目
连接不足
```

## 第四阶段：连接体系

开始使用：

```text
命题式标题
句子中的关系链接
来源 → 知识 → 项目
MOC
闭卷自测
```

## 第五阶段：PDF

学术研究采用：

```text
Zotero + ZotLit
```

独立文件采用：

```text
Obsidian + PDF++
```

明确文件权威位置，避免双份 PDF。

## 第六阶段：高级自动化

只有在流程稳定后再启用：

```text
Templater 文件夹自动模板
QuickAdd Macro
Linter 保存时运行
自定义 JavaScript
```

---

# 最终原则

一套长期有效的 Obsidian 系统，应当满足：

```text
任何内容都有明确入口
任何正式笔记都有稳定类型
任何状态都能通过 Properties 表达
任何积压都能在 Bases 中看见
任何重要结论都能追溯到证据
任何来源都能进入知识或项目
任何自动化都能减少重复动作
任何 PDF 都只有一个权威版本
```

最重要的连接不是：

```text
笔记 A ↔ 笔记 B
```

而是：

```text
证据
→ 支持或反驳某个命题
→ 改变当前判断
→ 影响具体项目和输出
```

当 Obsidian 能稳定保存这条链路时，它才从“Markdown 文件管理器”变成真正可审计、可复用、可扩展的研究系统。