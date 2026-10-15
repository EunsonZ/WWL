# 信息论跨域探索：2026-10-10 实际客户端记录

这份记录保存一次真实 WWL Obsidian 客户端操作，供复核全库知识目录和跨学科探索练习。它记录当时的查询、落点、显示与失败，不是学习者的掌握记录，也不是当前重新执行的结果。正文练习位于 [[Obsidian知识/10-基础/02-链接与知识网络/04-全局图谱与局部图谱#在真实知识页中继续：从熵走到 KL|图谱课真实探索练习]]；候选两段增补另由发布者接收。

## 所用版本与原结果

仓库为 EunsonZ/WWL，repository id=1407214804。需求正文读取时间与各 issue 当时状态见 [read-identities.json](requirements/read-identities.json)；#128/#134 当次正文与空评论原数组同时保留。源正文、Base与样本的22个文件 SHA256 和候选 SHA256 在 [sourcefreeze.json](sourcefreeze.json)。候选正文 SHA256 为 b3b30a0bee9283bca3269e2fbdeb2b687dd4f0eabe6db245773c21c4adf4b75d。此身份属于独立核查时冻结版本；后来的文件和客户端结果不能冒充这一版本。

原官方 CLI 返回 Obsidian 1.14.4（installer 1.13.7），实际 vault 路径为当时本机 WWL。版本和目标原响应分别见 [cli-version.json](client/cli-version.json)、[cli-vault.json](client/cli-vault.json)。每个 CLI 原记录都有 args、UTC time、exit、完整 stdout/stderr；数目均为所记时点的历史观察，新增课程会改变数目。

|实际动作|原结果|证据与适用范围|
|---|---|---|
|知识目录 Base 三个视图查询|知识浏览1801、正文证据未记录1147、局部核验与待复核520行|[三视图原DOM](client/base-all-dom.json)与client/view0.json、view1.json、view2.json；query与实际切视图结果数量一致，dirty=false。截图不冒充Base画面。|
|同一组阳性/排除样本核对|既有两域正文、导航和实践按原条件出现；四个排除前缀样本均不出现；未记录/partial保持原语义|[逐路径样本及原属性](client/sample-results.json)、[各域数量](client/view-domain-counts.json)。可见不表示课程完整或已核验。|
|指定路径打开|两域正文/导航/实践及信号新课返回相同exact path；#178 IIR切source后正文和属性可见|[路径打开原响应](client/base-sample-opens.json)、[IIR source DOM](client/iir-source-settled.json)。IIR截图名不能作为IIR显示证据。|
|信息论Backlinks|17个来源文件，DOM与像素所见29处引用|[索引原响应](client/backlinks.json)、[可见上下文DOM](client/entropy-settled.json)。文件数与引用出现次数不同，虚拟DOM不等于全部源段同时可见。|
|Local graph深度及开关|depth1初始24节点、depth2为279节点，实际入链/出链/邻居边集保存|[初始图状态](client/graph-state.json)、[depth2数据](client/graph-depth2-data.json)、[四种开关](client/graph-comparisons.json)。数据来自真实renderer，像素不单独认证这些计数。|
|同一长文三个标题跳转|同一信息论path，0基cursor79/129/271，scroll top2041/3073.5/6967.5|[准确跳转原响应](client/samefile-title-jumps.json)。对应源第80/130/272行；有限码流具体段落另有独立像素签收。|
|原练习阅读模式显示|五步探索、三个来源标题链接可见，文件图和反链同窗存在|[练习DOM](client/exercise-current-state.json)与原图iir-source.png；没有真人理解证据。|
|完整悬停Page preview|两次无目标锚点；渲染后触发空popover，随后消失|[初始失败](client/hover-title.json)、[第二次失败](client/hover-title-r2.json)、[空框原响应](client/hover-title-rendered.json)、[消失原响应](client/popover-settled.json)。完整popup未验。|

实际新信号课样本：#177 为信号与系统/10-连续与离散系统/06-Fourier四种表示与FFT卷积.md，正文标题“Fourier四种表示与FFT卷积”；#178 为信号与系统/20-数字信号处理/04-IIR设计二阶节与幅相取舍.md，正文标题“IIR设计、二阶节与幅相取舍”。随机噪声样本只是额外已有电子页，不能替代#178或新增电子课。

## 截图只按实际像素解释

四张PNG保持原字节、原文件名和3456×2034画布。具体截图SHA256、对应capture原响应、像素观察及支持范围见 [screenshot-map.json](screenshot-map.json)。命名与最新DOM存在时差，按独立所见解释：

- base-partial-view.png 实际显示信息论“从平均损失到有限码流”、P/Q及AAAABBCD14/16bit段落和反链29；支持有限码流实际落点，不能称为Base截图。
- iir-source.png 实际显示原跨域练习五步、三个来源标题链接、局部图及反链29；支持原练习显示，不能称为IIR或悬停popup截图。
- entropy-title-jump.png 实际显示主文页顶、属性及密集文件图；支持文件图可见，不能称为熵标题已显示。
- title-preview-rendered.png 显示原练习及来源链接、局部图和反链，没有popup；保留预览未验的失败上下文。

独立核查原报告为 [REPORT.md](review/REPORT.md)，逐文件复核数据为 [independent-check.json](review/independent-check.json)，19链接复核为 [links-independent.json](review/links-independent.json)。报告本身保持原字节，里面的恢复目录名称指原工作位置；本记录仅按文件名将必要原输出带入正式实践目录。

## 前景激活失败及可接续的预览检查

独立核查实际确认App路径和bundle id，普通打开现有App失败 -10827；一次经自动审批允许的单一App前景激活返回exit0，后续等待1.2秒仍document.visibilityState=hidden、目标anchor=null、只有图谱路径，core page-preview为true。三份原响应分别为 [open-app.json](review/open-app.json)、[foreground-activation-escalated.json](review/foreground-activation-escalated.json)、[foreground-settled.json](review/foreground-settled.json)。命令成功不证明目标renderer可见，没有改持久权限、启插件或捕获全桌面，完整popup继续未验。

接续时先在实际可见WWL窗口打开图谱阅读模式，确认visibilityState=visible，等待“压缩中的熵与平均码长”锚点真实出现，再按现有原生modifier悬停。只在同一个稳定popup内记录目标data-href、标题、上下文、rect和相关窗口截图；确认内容对应真实文件及标题。没有稳定popup就保留未验。正文基础练习可通过准确标题跳转完成，完整悬停预览不因已启用或空框而算成功。

## 复建动作接口：本页命令未在封装时重跑

只在已安装且已开启的官方CLI、正确WWL主库和既有授权下使用以下只读查询。先确认实际vault路径；不以活动页作为查询目标。新结果保存到新目录，保留UTC时间、stdout/stderr与退出码，同时按当前源字节记录版本。不得覆盖本目录历史结果或把新数目写成原数目。

```bash
/Applications/Obsidian.app/Contents/MacOS/obsidian-cli version
/Applications/Obsidian.app/Contents/MacOS/obsidian-cli vault=WWL vault info=path
/Applications/Obsidian.app/Contents/MacOS/obsidian-cli vault=WWL base:query 'path=00-工作台/知识目录.base' 'view=知识浏览' format=json
/Applications/Obsidian.app/Contents/MacOS/obsidian-cli vault=WWL base:query 'path=00-工作台/知识目录.base' 'view=正文证据未记录' format=json
/Applications/Obsidian.app/Contents/MacOS/obsidian-cli vault=WWL base:query 'path=00-工作台/知识目录.base' 'view=局部核验与待复核' format=json
/Applications/Obsidian.app/Contents/MacOS/obsidian-cli vault=WWL backlinks 'path=数学/50-信息论/01-熵交叉熵KL散度与互信息.md' format=json
```

后续路径打开、图谱选项和标题跳转按原JSON的args及图谱练习操作：先确认本次真实活跃文件，再观察深度1/2和入/出链/邻居变化；打开同文熵、KL、有限码流准确标题并返回源段。记录预期与实际，不新增正文链接来制造通过，不改已有学习笔记或迷宫，也不把模型走读当真人理解。此复建接口不触发任何安装、激活或运行，缺客户端时直接记录not_run。

## 新电子课回归交接与issue边界

[新课存在情况](client/new-course-presence.json)保存当时五个拟建电子目标均不存在及三视图均无此路径。#128覆盖修复与既有样本已通过，新电子课回归仍待完成，issue保持open。交接给各正文作者和整合者：

|后续正文责任|建成后用作回归的准确目标|
|---|---|
|#184 完整OTA|电子电路/26-放大电路/09-完整OTA偏置共模反馈与联合设计.md|
|#185 开关电容|电子电路/42-转换器与采样时钟/08-开关电容电荷时序与离散传函.md|
|#186 有源射频|电子电路/46-电磁射频与高速/08-有源稳定与噪声匹配.md；同组另有09-LNA与混频器件设计.md、10-射频振荡与频率综合.md|

作者实际建成并经整合者接收后，按当前正文确认原证据状态，查询三个视图，保存预期/实际membership，再exact path打开并确认可见标题及正文。若正式主解释采用别的已确认路径，记录该真实路径与新版本，不用拟建路径当已存在。该回归只认证可发现性与实际打开，不认证#184–186课程完整、硬件或真人结果。不得为了关闭#128放宽原验收，也不得用旧采样页替代新增页。

#134已签收源语义、静态、真实准确跳转及原练习显示；正文增补整合后的最终字节/引用和最新远端条件由sole writer复核后决定基础任务关闭。完整popup仍未验，候选本身尚未进客户端时不能宣称新增两段已显示。#110仅消费本次可观察客户端层，同步、恢复仍not_run，不改既有两页测试笔记。本记录不代填真人掌握度、点击流畅度或学习迁移结果。
