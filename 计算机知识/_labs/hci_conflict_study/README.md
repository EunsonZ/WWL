---
type: lab
stage: 1
aliases:
  - 预约冲突研究与比较实验
sources:
  - https://ocw.mit.edu/courses/6-831-user-interface-design-and-implementation-spring-2011/pages/lecture-notes/
  - https://www.w3.org/WAI/tutorials/forms/notifications/
prerequisites:
  - "[[计算机知识/75-软件工程与人机交互/06-认知模型用户研究与比较评价]]"
---
# 预约冲突：信息保留、顺序与退出

本实践接[[计算机知识/75-软件工程与人机交互/06-认知模型用户研究与比较评价|06主解释]]。旧04及81已含预约原型与2026-09-17的11项headless检查；本轮补的是受控AB材料与顺序/缺失的可复算分析，不把同一3/5和4/5再跑成新可用性成果。原`reservation-prototype.html`及81保持原位。这里是独立轻量本地材料，没有新服务或前端框架。

## 真源、输入与结果身份

[prototype.html](prototype.html)沿用旧原型的整数分钟/半开区间/时长和错误恢复合同；增加共同已占区间、共同预填、明确AB变体与只读实验快照。A/B唯一分歧是冲突分支清空或保留，非法时长都保留；默认`?variant=A`或B显示原值，由人主动提交。没有variant则拒绝启动；`&stage=conflict`仅用于自动检查准备恢复屏。刷新丢弃内存状态；没有真实预约、认证、持久化、并发或联网超时实现。

[legacy-outcomes.json](legacy-outcomes.json)规范化04已明确的3独立/1帮助/1失败，L标签不是原参与者ID，时间与原话未知。[comparison.json](comparison.json)是另造的固定AB、平衡AB/BA和完成者选择材料；与旧五条互不拼接。数据生成机制是教学设定，不是行为观测。退出与条件迁移变式由同输入派生，不能当额外真实样本。

[study_analysis.py](study_analysis.py)是算术与绘图真源；[test_study_analysis.py](test_study_analysis.py)核旧未知时间、帮助/退出分母、配对/顺序、df6条件区间及拒绝；[check_browser.mjs](check_browser.mjs)以原生Node WebSocket/CDP驱动自己的临时Chrome。[[计算机知识/_labs/hci_conflict_study/源码与测试镜像|四源逐字镜像]]仅供阅读，修改源码后须同步。

固定保留输出：[analysis.json](data/analysis.json)、[comparison.png](data/comparison.png)、[浏览器逐项结果与AX属性](data/browser/browser-results.json)、[实际Chrome日志](data/browser/chrome-stderr.txt)。三张真实软件截图是[A冲突](data/browser/conflict-A.png)、[B冲突](data/browser/conflict-B.png)、[B的375px布局](data/browser/conflict-B-375.png)。它们是同一本地合成场景，不是参与者图像。

## 输入命令与预期判据

先把本目录**完整复制**到新的库外目录；以下命令在该副本执行，输出路径必须尚不存在，避免覆盖本页固定证据。分析逻辑用Python标准库，生成图需要requirements所列matplotlib及其依赖；浏览器检查需支持原生WebSocket/fetch的Node与本地Chrome，无需npm安装。

```sh
python3 -B -m unittest discover -s . -p test_study_analysis.py -v
python3 -B study_analysis.py --output /private/tmp/hci-analysis-new
node check_browser.mjs /private/tmp/hci-browser-new
```

macOS默认Chrome路径在源码中；其它安装用`CHROME_BINARY`明确设置。脚本仅访问自己的本地文件、临时profile和127.0.0.1 CDP，禁用背景同步/组件更新等常见背景活动，不连接个人浏览器；这不是对操作系统全部流量的独立审计。临时Chrome和profile在退出时清理。受限制执行环境可能禁止Chrome启动；应按本机授权使用隔离启动，不把更换权限等同于产品验收。

本轮实际以主库既有`.venv/bin/python`（Python3.14.7、matplotlib3.11.2、NumPy2.5.3）运行，Node26.8.1、Chrome155.0.8059.80，macOS27.0.1 arm64。分析通过共享两槽runner、线程环境1：

```sh
MPLCONFIGDIR=/private/tmp/hci-mpl XDG_CACHE_HOME=/private/tmp/hci-cache /private/tmp/wwl-next-context/run_local.py --timeout 120 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B -m unittest discover -s COPY -p test_study_analysis.py -v
MPLCONFIGDIR=/private/tmp/hci-mpl XDG_CACHE_HOME=/private/tmp/hci-cache /private/tmp/wwl-next-context/run_local.py --timeout 120 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B COPY/study_analysis.py --output NEW_ANALYSIS
```

`COPY`/`NEW_ANALYSIS`为上面明确的新副本/输出参数，不是脚本内置参数。2026-10-17作者实跑6测试0.001秒通过、生成JSON和图成功；首次matplotlib建字体缓存另用数秒。浏览器正式由环境执行者复制同字节源码，以获准的sandbox外隔离Chrome运行：`run_local.py --timeout 300 -- node COPY/check_browser.mjs NEW_BROWSER`，实际exit0、43项通过。300秒是上限，不代表运行为300秒。具体源码身份与执行边界见[运行说明](运行说明.md)。

高影响判据：旧五条无帮助/含帮助3/5及4/5、未知时间不填0；第六开始后失败分母6，开始前技术失败单列；固定AB均差−20不识别版本效应；平衡构造效果−10、期次−20，合并方差40/3秒²、SE√(5/3)秒、条件区间[−13.1590634,−6.8409366]秒；迁移变式−16，退出7配对的直接均差−92/7、等权顺序−31/3；完成者选择反转。上述JSON确定性复算应逐字段相同，图受字体/版本影响，不要求跨环境PNG字节相同。

浏览器高影响判据：初始冲突不新增预约，A空/B570600而文字/焦点相同；只用测试键事件可创建相邻600630、取消并回到开始；非法29分钟保留两值并标结束字段；重复冲突仍仅原预约；AX名称及status存在；375px无水平文档溢出。当前43项均通过，断言细节在原始JSON。键入用CDP编辑命令与事件，不能声称实体键盘实测。

## 一次失败为什么仍需保留解释

普通sandbox中Chrome启动SIGABRT、无有效CDP结果，不能记为产品失败或PASS。环境隔离启动后，最初测试的Enter只有keyDown/up，没有字符文本，表单未提交，故“创建相邻预约”断言失败。保持HTML不变，在测试驱动的Enter keyDown补`text`与`unmodifiedText`回车字符后成功；当前固定输出由最新两源重新正式执行，非用失败截图改名。这个修正是测试fixture，不是用JavaScript直接调用submit来绕过键盘路径。

## 人的证据如何进入

[[计算机知识/_labs/hci_conflict_study/真人任务与记录|任务包]]已给参与者差异、共同原值暴露、任务脚本、计时、帮助、退出、设备/辅助技术与观察字段，可直接用于另行获准的真实任务。当前0参与者、无真实访谈、无读屏软件音频。主文的S甲/S乙也是构造示范，不是旧五条细节。

DOM/AX与截图只核软件；不能据它们宣称人的认知减负、总体B更快、完整WCAG符合性或辅助技术体验。原型同文本/焦点排除了部分操纵差异，仍未测真人对播报时机、设备熟悉度或学习的反应。真实任务也应保留失败和退出，不能通过不招募有困难的人把可访问性“验收”干净。

本包完成原#173首批，余下感知/注意、指向选择及系统方法比较继续开放。非作者已完成本包内容与行为独立核查：配对/顺序/退出及条件区间独立复算，正文7题与真人任务口径核对，修后默认共同暴露与自动stage分离；独立Chrome155的136项断言通过且exit0，作者正式43项原始断言逐项相符。6测试独立复跑通过，JSON/图与独立重放逐字一致，4源码镜像、98个wiki目标/锚点与21个相对附件核对通过；六既有页局部返回保留原属性和标题。以上不构成真人效果或总体推断的验证：真人仍为0，真实读屏输出/物理键盘与Obsidian客户端视觉预览未做，模型走读与浏览器检查均不冒充真人理解。
