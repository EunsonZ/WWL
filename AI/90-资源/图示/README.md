---
type: resource
status: ready
---

# 本地图示说明

本目录含 19 张教学图，每张提供 PNG 与 SVG。正文统一使用相对路径嵌入 PNG，离线阅读不依赖图片网站、Graphviz 或额外 Obsidian 插件；SVG 供放大与继续编辑。文件中没有在线图片引用。

图示覆盖学习路线、张量反向传播、不等长 token 归一化、卷积互相关、感受野、残差、ViT、Transformer、MLA、状态空间、推理强化学习、在线 softmax、缓存因果掩码、测试时计算、CLIP、VLM、语音、扩散与 Flow Matching。

17 张流程图保留同名 `.dot` 源码。两张矩阵图及全部流程图可以用 `generate_figures.py` 重新生成，需要 Python、Pillow、Graphviz 和本机中文字体。默认字体为 Noto Sans CJK；矩阵绘图字体路径可通过 `AI_DIAGRAM_FONT` 环境变量指定。没有附带字体文件，也不需要重新生成才能阅读。

```bash
python generate_figures.py
# 单独修改流程图后也可重新生成：
dot -Tpng -Gdpi=145 flash.dot -o flash.png
dot -Tsvg flash.dot -o flash.svg
```

这里的图是机制示意，不是模型性能实测图。尤其是 MLA 图省略了真实实现的头布局细节，Transformer 图抽象一个可重复的 block，Flow Matching 图明确采用从噪声到数据的时间方向。定义与边界以相邻课程正文为准。

返回 [[AI/90-资源/06-修订与验收报告]]。
