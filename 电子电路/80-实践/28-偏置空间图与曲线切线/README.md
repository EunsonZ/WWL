---
stage: 1
aliases: []
sources: []
prerequisites:
  - "[[电子电路/22-半导体与真实元件/07-正反偏空间图的共同坐标与边界]]"
  - "[[电子电路/24-MOS与BJT/07-从曲线族到负载线切线与割线]]"
---

# 偏置空间图与曲线切线的复算

本实验补齐V19的正反偏五空间量与V21三种器件的负载/Q/局部切线/割线任务，属于已发布M08/M09的图解补充；不额外增加175主题的计数。图源是原创Matplotlib绘图，可编辑SVG与360/425 PNG由相同数据生成。

`models.py`采用SI并给出有限教学域：PN固定主文掺杂/温度，$V_D\in[-2,.3]$ V、$x\in[-1,1]$ μm；二极管0–.65 V，BJT $V_{BE}\in[.5,.75]$ V/$V_{CE}\in[0,5]$ V，MOS $V_{GS}\in[0,2]$ V/$V_{DS}\in[0,5]$ V。域外或NaN/无穷/布尔拒绝，不默默裁剪成可用物理数据。`intersection`最多80步并核括区与残差。回调须是确定、连续且适合此括区法的单调端口关系；每次返回值与最终残差都检查有限实数，内点NaN/无穷或非实数会明确失败。有限守卫不证明任意回调连续、单调或根唯一。它不是任意电路求解器。

从库根运行已存在的Python环境，先创建新的库外结果目录；以下输出路径是例子，若已存在且非空，换新名：

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/28-偏置空间图与曲线切线' -v
MPLCONFIGDIR=/private/tmp/wwl-devicefig-mpl XDG_CACHE_HOME=/private/tmp/wwl-devicefig-xdg .venv/bin/python -B '电子电路/80-实践/28-偏置空间图与曲线切线/generate.py' --output /private/tmp/wwl-devicefig-output
```

运行需要已有Matplotlib，缺失时记录未运行，不安装。导入 `models`/`generate` 不读CLI、不绘图、不改绘图配置；`main(argv=None)`解析必填`--output`后才加载绘图库。`generate(output)`只接受不存在或空目录，绘图样式在上下文退出时恢复；MPLCONFIGDIR由调用者显式放库外，字体缓存属于运行环境输出，不当教学数据发布。成功输出6SVG、12PNG及results.json，SVG保留文字和坐标；无工具运行日志伪造。

六项模型CPU测试覆盖电荷中和、电场面积/势差、n/p非平衡乘积与空间导数、MOS闭式Q/BJT原端口式、局部差分偏导、割线反例及拒绝出口。运行后再用独立方法核验，例如从E的三角形面积算B，不以同一个phi实现当自己的参考。另有一项生成器状态测试，实际覆盖成功和人为渲染异常两条路径下的绘图配置与环境恢复，新增一项有效端点但非法内点的回调回归，共八项测试。

学习任务：先不看答案预测正/反偏宽度和掺杂高度；再把MOS的Q、$g_m$、$g_{ds}$各算一次；最后改变负载并说明哪条曲线固定、哪个Q必须重算。PN的耗尽rho与近似n/p在边缘不自洽，BJT无Early与MOS教学λ不是工艺模型。这些边界随图保留。

CPU、源码合同、实际图件阅读各有独立验收记录；未做TCAD、SPICE、仪器/实物、Obsidian UI或真人学习效果验证。
