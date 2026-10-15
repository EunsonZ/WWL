---
type: lab
domain: 物理
stage: 3
aliases:
  - 球腔静电多极复算
sources:
  - https://farside.ph.utexas.edu/teaching/em/lectures/node66.html
prerequisites:
  - "[[物理/20-电磁学/13-球腔静电分离变量与多极误差]]"
---

# 球腔静电多极复算

从 [[物理/20-电磁学/13-球腔静电分离变量与多极误差#从球域分离到真实系数|带源分离变量]] 出发，保持同一SI点源、球腔、正介质和接地参考。程序分别算Legendre外支和两距离镜像势/梯度，比较截断场误差；另直接积分内壁自由面电荷的前三个矩。不同表达式有助发现源/边界误用，正式独立核查另由非作者完成。

输入是 [inputs.json](inputs.json)，规范真源是 [sphere_multipole.py](sphere_multipole.py)，全文同步镜像见 [[物理/80-实践/46-球腔静电多极/SOURCE|源码镜像]]。只有 Python 3.10+ 标准库，无安装依赖。按实际位置进入本目录后，创建一个未存在的新输出路径：

```bash
python3 -I -B sphere_multipole.py --input inputs.json --output-dir /private/tmp/my-sphere-run-01
```

输出目录已存在时退出2并保留旧内容；有效域或输入错误也先拒绝，不以覆盖旧图掩盖失败。仓库的 [assets/results.json](assets/results.json) 与CSV、SVG是作者固定卡真实预跑输出，不能把它们当作本机新运行结果。本文命令不自动启用任何插件或服务。

## 在运行前写出自己的预测

1. $q>0$ 时近侧与远侧的自由面电荷是什么符号？总量应等于镜像 $q_*$ 还是 $-q$？
2. $L=0$ 为什么没有角向变化？$L=16$ 的势误差达到0.01 V，是否足以承诺径向场1 V/m？
3. $\epsilon_r$ 从2改为4，$\phi,E,\sigma_f,Q_{\rm inner},F$ 各如何缩放？
4. 在 $r=b/2$ 强制使用外支会违反哪一个收敛条件？

先回答，再看 [[物理/80-实践/46-球腔静电多极/ANSWERS|解释性答案与撤提示迁移]]。

## 九个同源输出分别核什么

| 输出 | 量、维度与用途 |
| --- | --- |
| [fields.csv](assets/fields.csv) | 7阶×181角点=1267行；同一 $r$ 的两表达式 $\phi$（V）、$E_r,E_\theta$（V/m）及三类误差界 |
| [convergence.csv](assets/convergence.csv) | 7行；离散最大误差与覆盖全角的解析界分别保留，不将网格当全域定理 |
| [surface.csv](assets/surface.csv) | 181角点；闭式 $\sigma_f$（C/m²）、壁面 $E_r$、$L=32$ 面源及其独立界 |
| [moments.csv](assets/moments.csv) | 4096/8192面板×3阶=6行；$Q,p_z,M_2$ 各用 C、C·m、C·m² |
| [results.json](assets/results.json) | 同一卡、教学常数、probe、镜像/实际面量、反作用力能、内支probe及浮置答案 |
| [geometry.svg](assets/geometry.svg) | 真源/壁面/源球/域外数学镜像，标注外支有效区域 |
| [potential.svg](assets/potential.svg) | 同半径镜像真值与0/1/2阶角向势，单位 V |
| [convergence.svg](assets/convergence.svg) | 势与径向场误差的不同无量纲 log 比值；图例指定1 V或1 V/m |
| [surface.svg](assets/surface.svg) | 同源壁电荷角向分布，显示近壁密度集中 |

默认赤道probe为27.5449337925 V、2483.65369239 V/m、735.987731054 V/m。$L=16$ 势界0.001959136 V，径向场界1.063530588 V/m；$L=32$ 径向场界约 $2.9894\times10^{-5}$ V/m。CSV用标准库writer的CRLF；正文与源码用LF。

## 合法变卡与负对照

复制输入到新的库外卡，改 $\epsilon_r=4$ 后运行新输出目录；应观察势、场和反作用能/力减半，自由面量不变。再改 $b/a=0.7$、观测 $r/a=0.8$，曲线应更集中、同阶误差更大。将 $q$ 改为负值，势/场/面量变号，反作用力仍指向近壁，反作用能仍负；源位置不变。

数值有限卡限制 $0.05\le b/a\le0.85$、$b/a+0.02\le r/a\le0.98$、最高阶128及有限采样。它们防止本演示运算失控，不声称物理解在范围外不存在。理论允许 $0<b<a$；$b\to0$ 的中心极限可直接取 $\phi=kq(1/r-1/a)$，程序卡没有用 $q_*\to\infty$ 硬算这个极限。

拒绝 $b/a\ge1$、$r/a\le b/a$、非正介质、非有限数字、bool代整数、重复阶数、奇数Simpson面板以及已存在的输出目录。拒绝输入层只是有限程序边界，不能认证真实击穿或量子点源模型。自由点源全场自能发散，JSON只给已去裸源自能的反作用能；未做一般FEM、商业全波、材料拟合、设备或客户端实验。
