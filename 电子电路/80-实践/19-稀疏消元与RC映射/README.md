---
type: experiment
domain: electronics
stage: 3
content_status: usable
evidence_status: partial
aliases: []
sources: []
prerequisites:
  - "[[电子电路/14-网络建模与仿真/01-图论电路与关联矩阵]]"
---

# 四节点精确消元：存储关系改变，电路没有新增导线

读者任务：先预测中心先消与叶先消分别产生几条填充，亲自更新右端，再比较两个注入位置的物理解。正文在[[电子电路/14-网络建模与仿真/01-图论电路与关联矩阵#消元为什么让稀疏矩阵变密|具体网络与Schur补]]。这里的源码只服务固定、严格正电导、接地四节点星形，矩阵单位S、注入A、电位V；不承诺通用稀疏LU、数值选主元或大规模性能。

从库根运行，输出目录请使用新建的库外目录：

```bash
python3 -B -m unittest discover -s '电子电路/80-实践/19-稀疏消元与RC映射' -p 'test_sparse_demo.py' -v
python3 -B '电子电路/80-实践/19-稀疏消元与RC映射/sparse_demo.py' --output /private/tmp/wwl-sparse-check-new
python3 -B '电子电路/80-实践/19-稀疏消元与RC映射/generate_diagram.py' --output /private/tmp/wwl-sparse-check-new
```

`results.json`保存精确分数字符串，包含中心/叶注入、两种消元顺序、每步pivot、剩余矩阵、新右端、填充对、电位和功率。中心先消第一次得到三条新非对角项；叶先消无填充。三个不同注入（含负注入）遍历24种顺序，与独立原支路KCL公式和六支路功率对照。仅结果恰好相等还不够：删掉右端更新便得到违反KCL的反例。

源码为[唯一模型](sparse_demo.py)、[测试](test_sparse_demo.py)与[原创图生成器](generate_diagram.py)。模型只接受四个int/Fraction电流和四节点排列；bool、float、重复节点拒绝。原结果不依赖NumPy或Matplotlib；两个模块导入不解析命令行、不写图或缓存，CLI缺少`--output`时退出且不写文件。已给出的输出路径会写入同名产物，实验应使用新的库外目录；它不会自动分辨人的旧结果。

一般卷积与初态两项复用[[信号与系统/10-连续与离散系统/02-冲激卷积与零状态响应#非零初值的另一份责任|信号主解释]]，一般强迫项的初值公式复用[[数学/46-数理方程/14-Fourier-Laplace变换解数理方程#自测与解答|数学自测公式]]。带SI单位的电路映射由[[电子电路/12-交流与变换域/09-传递函数零状态与初始响应#H的定义与初值项|已存在的RC两项解]]承担；本实验没有另复制RC模型或图，原电子实验继续承担时间响应复算。

验证证据按实际发布记录定位。这里是教学CPU与静态图源，不代表SPICE、生产求解器、硬件、Obsidian客户端或真人学习验收，也不增加另一项完整L实验信用。
