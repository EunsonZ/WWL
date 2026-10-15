---
type: course
stage: 0
aliases: []
prerequisites: []
sources:
  - https://html.spec.whatwg.org/multipage/form-control-infrastructure.html
  - https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics/Box_model
  - https://www.w3.org/TR/mediaqueries-3/#units
  - https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Flexible_box_layout/Basic_concepts
  - https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout/Basic_concepts_of_grid_layout
---
# HTML语义、表单与CSS布局：先建立能操作的文档

**为什么一个看起来像按钮的矩形，不一定能可靠提交查询？** 浏览器解释元素的语义，矩形的外观只是一层样式。项目用 `main` 承载主任务，`form` 定义查询，`label for="query"`关联输入，`button type="submit"`表达提交，两个有标题的 `section`区分查询结果与阅读列表。标题层次是h1→h2→h3；列表使用ul/li。使用原生button可保留其键盘激活行为，无须给div重新拼装整套控件机制。

## 表单先表达约束，再处理意图

`id`让label、脚本与说明找到同一控件；`name="q"`定义提交时的字段名。二者用途不同。`required`挡住空字符串，`maxlength="80"`限制用户输入长度；它们不能认出只有空格的业务无效关键词，所以提交监听器仍调用 `normalizeQuery`，去两端空白后检查JavaScript字符串长度1–80。本课单位是UTF-16代码单元，不是“可见字符”：`Web`长3，常见单个中文字符长1，`😀`长2，40个这种emoji长80。选择这个口径是为了与HTML文本输入上限一致，真实产品可以另选字素规则。[HTML控件基础规范](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#attr-fe-maxlength)说明长度与提交/验证机制。

原生交互提交先经过适用的约束验证，合法时触发submit；监听器取消导航，用Fetch更新当前页。直接调用 `form.submit()`绕过交互验证和submit事件；需要程序请求相同流程时用 `requestSubmit()`。`maxlength`也不能替服务器验证脚本生成的输入。服务端重复检查上限，避免只信页面属性。[HTML form API](https://html.spec.whatwg.org/multipage/forms.html#dom-form-requestsubmit-dev)支持这个区分。

**反例：**只有查询按钮click监听器，人在输入框按Enter时可能走默认提交而整页导航；只有红色边框又不能说明哪条规则失败。项目监听form的submit，同时保留label、说明文字、`aria-invalid`和可修正的错误文字。动态错误不抹掉输入，键盘焦点回到输入。无JavaScript时原生form仍向API导航显示JSON；这是有限退化行为，不是完整的无脚本课程浏览页。

## 用盒模型解释窄屏，而不是猜宽度

普通 `content-box`下，外部边框盒宽为内容宽＋左右padding＋左右border，margin在盒外。若容器内容宽320 CSS px，控件内容宽320、左右padding各8、border各1，则边框盒为338，已溢出18。`border-box`把padding/border纳入指定宽度，同样width=320时内容宽302；项目全局设置它，让 `input {width:100%}`更易预测。320是教学假设宽度，不是实测设备像素。[MDN盒模型](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics/Box_model)支持这个计算口径。

动作按钮主要排成一行，并在不够宽时换行，用Flex的 `flex-wrap`和gap。结果与阅读列表是二维区域，用Grid的 `minmax(0,2fr) minmax(0,1fr)`分配可用空间，窄于45rem时切成单列；minmax的0下限和section的min-width:0允许轨道收缩，长词用overflow-wrap折行。在假设布局中的根computed字号16 CSS px、可用宽960、gap为1rem即16时，两轨道分别 `(960−16)×2/3≈629.3` 与314.7 CSS px。媒体查询中的45rem采用初始字号值，不取 `html`样式声明后的computed字号：浏览器初始字号16时阈值为720 CSS px，写 `html {font-size:32px}`会改变普通布局的1rem间距，却不会把媒体查询阈值改成1440。用户默认字号设置可改变初始值；浏览器缩放还会改变CSS视口，应分别观察。[W3C Media Queries 3 §6](https://www.w3.org/TR/mediaqueries-3/#units)明确媒体查询相对单位与样式声明分离。Flex主要围绕一个主轴分配，Grid同时描述行列；二者不构成“哪种更高级”。[MDN Flex](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Flexible_box_layout/Basic_concepts)、[MDN Grid](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout/Basic_concepts_of_grid_layout)。

CSS不会改变本项目的DOM阅读顺序：查询→结果→阅读列表。不要用 `order`让视觉顺序与Tab顺序相互打架。`:focus-visible`给键盘位置画明确轮廓，skip link允许直接进入查询。标题 `tabindex="-1"`可接收脚本恢复焦点，却不会额外挤进普通Tab序列。焦点如何随着列表删除变化，下一页会接着解释。

## 跟算与练习

把两门Web课程加入，35＋50=85分钟。缩到窄屏后仍应看到两个结果与85分钟，并按原顺序Tab到控件；布局变化不能偷偷修改数据。**练习：**若content-box输入width=280、两侧padding=12、border=2，边框盒多宽？若加入margin各8呢？答案：308；占据的水平空间324。改成border-box width=280时内容宽252，占据空间296。margin仍在宽度之外。

实际验证要记录视口CSS像素、缩放、Tab路径与溢出，不能凭这段手算写浏览器通过。下一步读 [[计算机知识/63-Web平台开发/02-DOM事件委托与界面状态|事件和状态]]，看同一控件如何驱动模型；原生控件与用户任务研究的更广边界去读 [[计算机知识/75-软件工程与人机交互/04-交互任务反馈可用性与无障碍|HCI主课]]。返回 [[计算机知识/63-Web平台开发/00-Web平台开发-MOC|本路线入口]]。
