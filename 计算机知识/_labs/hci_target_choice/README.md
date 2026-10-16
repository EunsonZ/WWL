---
type: lab
stage: 1
aliases:
  - 时段选择模型与方法实验
sources:
  - https://www.yorku.ca/mack/hci1992.html
  - https://www.yorku.ca/mack/hhci2018.html
  - https://ocw.mit.edu/courses/6-831-user-interface-design-and-implementation-spring-2011/pages/lecture-notes/
  - https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
prerequisites:
  - "[[计算机知识/75-软件工程与人机交互/08-感知注意指向选择与评价方法]]"
---
# 时段选择：模型、状态与评价证据

[[计算机知识/75-软件工程与人机交互/08-感知注意指向选择与评价方法|08主解释]]连接感知注意、心理模型、指向/选择及系统方法比较。已交[[计算机知识/_labs/hci_conflict_study/README|06冲突实践]]的3/5与4/5、配对/顺序/退出、43作者与136独立Chrome记录保持原身份，本轮不重跑它们或当新成果。这里仅新增目标/选择材料，无前端框架、服务或生产预约系统。

## 哪些是真源，哪些是构造

[target_models.py](target_models.py)是模型算术与绘图真源，[test_target_models.py](test_target_models.py)核变量、边界与描述拟合；[prototype.html](prototype.html)实现本地状态；[check_browser.mjs](check_browser.mjs)为自己的临时Chrome作CDP行为检查。[[计算机知识/_labs/hci_target_choice/源码与测试镜像|四源码镜像]]逐字同步，仅作阅读，不反写真源。

[model-inputs.json](model-inputs.json)的6条movement_s和5条reaction_s都是构造，附声明参数；另两条件速度/正确数与注意概率同样为构造。[method-records.json](method-records.json)的M1–M3动作/原话是新方法示范，不是原五条历史细节，也不是本轮真人观察。没有从模型拟合出人群定律。

固定分析输出：[model-results.json](data/model-results.json)、[models.png](data/models.png)。浏览器输出：[逐项断言/实际坐标/AX](data/browser/browser-results.json)、[真实Chrome日志](data/browser/chrome-stderr.txt)，截图[brief](data/browser/selected-brief.png)、[explicit](data/browser/selected-explicit.png)、[brief 375px](data/browser/selected-brief-375.png)、[explicit 375px](data/browser/selected-explicit-375.png)。图由同输入生成；截图为合成本地软件，不含真实人。

## 模型合同与高影响判据

D、W为一维同轴长度，0≤D≤1e9、1e−9≤W≤1e9，均排除bool/NaN/inf；ID=log2(1+D/W)。声明预测a/b非负且有限；描述OLS不裁剪负拟合，至少3条、x有变化、时间正且≤3600秒，不生成总体区间。概率有1–1024项、每项[0,1]且总和在1e−12绝对误差内为1，零项按0log0；不暗自归一。相同n也能不同熵，log2(n+1)不是等概率熵恒等式。

高重要性理由：把混合时间误当MT/RT、拿合成拟合认证人体、错用轴宽或忽略错误率，会直接改变设计判断。固定预期：ID(64,64)=1，ID(256,64)=log2(5)，同比例D/W不变；H(.25×4)=2，H(.7,.1,.1,.1)=1.35677964944704；条件注意交集.72/.588不等总体正确率；黑白21、119灰对白4.47808945不向上舍入过4.5。OLS只描述固定点：Fitts a≈.185326703,b≈.116119448,R²≈.990765652；choice a≈.307830094,b≈.146918839,R²≈.994123501。单位与假设见08，不用R²冒真人支持。

## 原型合同及预期

用浏览器打开`prototype.html?width=128&n=4&target=0&cue=explicit`。必须显式选择width64/128、n2/4/8、合法target索引0..n−1、cue brief/explicit；非法配置关闭任务、按钮不可用。没有真实服务、持久化、认证、并发或网络请求实现；刷新全复位。已有预约1固定540–600，候选从600起每30分钟一个，不冲突且在540–1020范围内。

开始前候选不可用，开始才显示指定目标；选中只改selected，确认正确目标才创建预约2。错选确认不创建且回焦该候选；正确后禁止重复确认，取消只删预约2并回起点。brief/explicit只改选中后的提示文字；W只改水平hitbox，固定n的中心不变；n改数量和列表长度。n8的滚动条可让整个内容绝对横移，当前相对首目标D不变，不能声称绝对屏幕中心跨所有条件相同。

当前原型记录实际pointer起点和endpoints，键盘没有pointer起点则null；DOM焦点不是指针位置。首目标中心和开始中心水平只支持该中心轨迹的一维几何示例，真实人未被强制点中心。浏览器内部elapsed_from_start_ms混合提示、搜索、判断与运动；全程还含确认/滚动。不把它标为人的纯RT/MT，也不拿固定target0重复当均匀选择刺激。

软件实施验证为高重要性：若只变视觉而hitbox不变，或者explicit暗中自动提交，就会污染心理操纵；若键盘不可达，会排除研究群体。实际检查12条件W×n×cue的状态、测量hitbox和相对坐标，pointer正确/错误路径；另核Tab/ShiftTab、Enter选择/确认/复位、AX名称/status、375布局和无效参数。结果通过也只说明软件合同，不证明人理解或WCAG整体符合。

## 复制到库外复算，不覆盖正式证据

在新的库外副本运行，输出目录必须尚不存在：

```sh
python3 -B -m unittest discover -s . -p test_target_models.py -v
python3 -B target_models.py --output /private/tmp/hci-models-new
node check_browser.mjs /private/tmp/hci-target-browser-new
```

Python分析逻辑用标准库，画图需requirements所列matplotlib及依赖。Node需原生fetch/WebSocket支持；无npm依赖。Chrome默认macOS路径，可用CHROME_BINARY覆盖。只启动自己的临时profile/CDP本地文件，不附着个人会话，不引远端服务。背景网络相关flags不是全机网络审计证书。

作者2026-10-17实际经共享两槽runner、线程1、timeout120运行5测试（0.000秒）PASS及CLI生成，使用主库已有Python3.14.7、matplotlib3.11.2、NumPy2.5.3；字体缓存首次另有数秒准备。原命令模式如下，COPY和NEW_OUTPUT分别替换新副本与新输出目录：

```sh
/private/tmp/wwl-next-context/run_local.py --timeout 120 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B -m unittest discover -s COPY -p test_target_models.py -v
/private/tmp/wwl-next-context/run_local.py --timeout 120 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B COPY/target_models.py --output NEW_OUTPUT
```

浏览器由环境执行者在已获准隔离环境复制同字节源运行：`run_local.py --timeout 300 -- node COPY/check_browser.mjs NEW_BROWSER`，Chrome155.0.8059.80、Node26.8.1，实际226/226、12条件PASS且exit0。本轮直接复用已知可用的sandbox外隔离方式，未重复尝试已知受限启动。上限300秒不是声称跑了300秒。输入/输出身份见[固定运行说明](运行说明.md)；算术JSON应逐字段同，PNG跨字体/版本不保证字节同。

真实中间失败也须解释：Chrome把注入的290.203125 CSS px回报为290，使最初深相等断言失败；保留两种坐标并按≤1px量化比较。n8取消按钮在视口外，旧clickCenter点了空白；先scrollIntoView再读当前rect后通过。两者修的是测试fixture，HTML业务没有改成直接调用回调；当前输出由最新驱动fresh重跑，不冒失败前结果。

## 方法与人的证据

[[计算机知识/_labs/hci_target_choice/方法对照与真人接口|方法包]]提供访谈/情境/问卷/任务分析/原型/启发式/认知走查/出声思考/控制比较的同题用法、三微比较和原始记录字段。语义、指向和选择分开，不让三改混为一因。目标序列与概率、练习映射、计时口径、帮助/退出、刺激提前暴露和滚动混合都有具体失败判据。

高影响真人层仍为0：没有真实RT/MT、注意/理解率、问卷、访谈、情境观察、AT音频、实体键盘或物理视觉/运动标定。已有软件日志和专家预测不能补这些空白。按原#173允许的设计+模拟例+边界完成教学，不自加招募作为课程验收门槛；也不称真实用户效果已测。

非作者已完成本包独立组合核查：从原始输入以Decimal高精度复算模型与OLS，新UI248项独立断言通过且exit0，作者226项原始断言一致；5测试独立复跑通过，JSON和模型图与独立重放逐字相同，4源码镜像无差异。26目标叠加当前主库核102个wiki目标/锚点及19个相对附件无问题，六既有页属性与原标题保留；10题答案、三微比较与四问走查已读，模型图和四张实际Chrome截图已目视核对。这些事实不验证真人效果：参与者仍0，真实AT/实体键盘、物理测量与Obsidian客户端视觉预览未做。独核建议本包实际发布核验后可按#173原范围关闭；issue操作仍由整合者核当前状态执行，不由本README自封。
