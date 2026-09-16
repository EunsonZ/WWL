# 本轮自绘图示

本目录包含 12 张图的 PNG、SVG 和 Graphviz `.dot` 源文件。正文使用本地 PNG，SVG 用于放大与编辑。没有在线图片依赖，也没有打包字体文件。图中结构与例子对应各深化课的定义与边界，不作为真实模型性能图。

`generate_figures.py` 使用本机 Graphviz 的 `dot` 生成图，不访问网络。重生成需要安装 Graphviz 和可显示中文的字体；脚本默认请求 Noto Sans CJK SC，系统可自行回退。现成 PNG 无需安装字体即可显示。

```bash
python generate_figures.py
```

图谱入口：[[AI/00-开始/05-问题驱动知识图谱与难点导航]]。验收说明：[[AI/90-资源/08-本轮深化修订与验收报告]]。
