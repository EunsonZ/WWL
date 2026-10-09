# 阻尼摆相图的生成依据

`pendulum-phase.svg` 由上一级 `dynamics_lab.py` 的 `phase_svg(config)` 生成，固定参数在 `fixed-inputs.json` 的 `phase_svg` 对象。图形包含方程方向场、零流线、能量 $V=1$ 的解析轮廓与四条 RK4 近似轨迹。SVG 内保留 title/desc，颜色之外另用虚线、点线、实线、圆与初值方块区分对象；左右边界是圆柱接缝。

从课程目录运行 `python3 -B dynamics_lab.py --output-dir /tmp/一个尚不存在的新目录`；结果保存在这个外部目录。确认输出来源、数值检查和渲染后，才将该 SVG 作为静态课程附件接收。生成过程不修改课程目录，不把有限轨迹认证为一般稳定定理。
