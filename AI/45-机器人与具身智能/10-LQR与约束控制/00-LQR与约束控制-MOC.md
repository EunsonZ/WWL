---
type: moc
domain: artificial-intelligence
stage: 2
content_status: draft
evidence_status: unreviewed
aliases:
- LQR与MPC
sources:
- https://underactuated.mit.edu/lqr.html
- https://underactuated.mit.edu/trajopt.html
- https://ee363.stanford.edu/archive/lectures/dlqr.pdf
prerequisites:
- '[[AI/45-机器人与具身智能/03-配置空间轨迹与反馈控制]]'
- '[[数学/20-线性代数与几何/15-谱定理二次型与正定矩阵]]'
- '[[数学/80-跨学科专题与综合练习/09-多元优化与变分法补充]]'
---

# LQR 与约束控制：从代价到可执行动作

**读者问题：** 已经写出动力学、单位和“状态误差与控制用量谁更贵”的代价后，怎样推出反馈增益？执行器到达上限时为何不能把 LQR 动作简单剪裁？MPC 什么时候真的能兑现约束？

本小课沿用[[AI/45-机器人与具身智能/01-坐标变换与平面运动学#运动学说明怎样走，动力学说明怎样改变速度|原课程的双积分器动力学]]，只取一个世界轴做可手算切片。连续模型仍是 $\dot p=v,\dot v=u$；为让八步例可读，这里独立取 $\Delta t=0.2\ \mathrm s$，并不把原闭环实验的 0.05 s 控制器参数直接搬过来。状态

$$
\begin{aligned}
x_k&=\begin{bmatrix}p_k\\v_k\end{bmatrix},\\
A&=\begin{bmatrix}1&0.2\\0&1\end{bmatrix},\\
B&=\begin{bmatrix}0.02\\0.2\end{bmatrix},\\
x_{k+1}&=Ax_k+Bu_k.
\end{aligned}
$$

$p$ 用 m，$v$ 用 m/s，$u$ 用 m/s²。贯穿数值例取 $x_0=(0.5,0)^T$、$N=8$、$|u_k|\le0.8\ \mathrm{m/s^2}$，并用尺度 $p_s=1\ \mathrm m$、$v_s=1\ \mathrm{m/s}$、$u_s=1\ \mathrm{m/s^2}$ 把代价归一为无量纲：$Q=\operatorname{diag}(1,0.1)$、$R=0.05$、$Q_f=\operatorname{diag}(8,2)$。权重表达偏好，不是传感噪声协方差；后者仍由[[AI/45-机器人与具身智能/02-Bayes滤波与Kalman状态估计|Kalman 页]]承担。

| 卡点 | 主解释 | 可检查结果 |
| --- | --- | --- |
| 怎样从代价推出反馈？ | [[AI/45-机器人与具身智能/10-LQR与约束控制/01-从Bellman配方到Riccati递推\|Bellman 配方与 Riccati 递推]] | 两步手算；八步 Riccati 与堆叠二次型同解 |
| DARE 残差小就稳定吗？ | [[AI/45-机器人与具身智能/10-LQR与约束控制/02-无限时域稳定化解残差与极点\|稳定化解、残差与极点]] | 一个零残差却不稳定的标量反例 |
| 为什么 clip 不是约束最优？ | [[AI/45-机器人与具身智能/10-LQR与约束控制/03-从LQR剪裁反例到约束QP\|剪裁反例与有限时域 QP]] | $J_{clip}=1.8472>J_{QP}=1.1609$，并验 KKT |
| MPC 怎样保证下一步仍可解？ | [[AI/45-机器人与具身智能/10-LQR与约束控制/04-MPC何时兑现约束与递归可行性\|终端条件与递归可行性]] | 终端等式移位构造；列出证明失效边界 |
| 我要复算代码和图 | [[AI/45-机器人与具身智能/10-LQR与约束控制/80-LQR与约束控制复现实验\|复现实验]] | 7 项单测、三张同例 SVG、JSON 数值摘要 |

这组内容不重复 PID 的误差项、anti-windup 或 Kalman 推导。PID 与采样极点见[[AI/45-机器人与具身智能/03-配置空间轨迹与反馈控制#用估计误差形成PID动作|原反馈课]]；估计误差与真实状态的区别见[[AI/45-机器人与具身智能/04-闭环仿真扰动恢复与模型边界|原闭环边界课]]。这里把“模型和代价如何决定动作”与“约束如何进入同一个优化”补完整。

当速度等状态不能直接测量时，继续[[AI/45-机器人与具身智能/20-状态估计与LQG/00-状态估计与LQG-MOC|状态估计与LQG]]，检查Kalman条件化、分离原理以及饱和与硬安全边界；LQR的Riccati推导仍以本课为主解释。

完成后应能区分三层结论：有限时域无约束 LQR 的精确最优性；带线性动力学和凸二次代价、盒约束时 QP 的有限问题最优性；带合适终端集合/控制律且初始可行、模型精确时 MPC 的递归可行性。它们都不自动证明真实机器人全局稳定、饱和非线性全局稳定、连续时间碰撞安全或带未知扰动的硬约束安全。
