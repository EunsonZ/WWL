---
type: resource
domain: signal
course: 信号与系统
---

# 两模态热反演运行结果

2026-10-12，未参与作者实现的执行者从固定 `inputs.json` 与最终 `thermal_inverse.py` 实际运行，默认输出为 [精确JSON](results/results.json)、[六行CSV](results/estimates.csv)、[同源SVG](results/thermal_inverse.svg)。这些三个文件直接复用该次真实输出，未由作者手填结果。主课推导与表的解释见 [[信号与系统/50-通信与反演/02-前向算子反卷积与正则化重建|反演课]]。

## 同版与命令

源码 SHA256 为 `c291c788ae045c8b7cb0938bb910f56603301df31652730fcaf6e7f6f3a21b90`。执行者使用 Python 3.14/macOS arm64；源码仅标准库，图的独立渲染使用其临时环境的 CairoSVG 2.9.1。可移植的读者复算命令为：

```bash
python3 -B thermal_inverse.py --input inputs.json --out /tmp/thermal-inverse-recheck
```

输出目录须不存在。独立执行用 `/private/tmp/numerical_guard.py --threads 1 --timeout 60 --lock-timeout 60` 约束子进程，然后运行自有 `run_checks_v2.py`；该脚本通过独立 oracle 与实际 CLI 核对，未导入候选源码作为答案来源。完整本地证据入口是 `/private/tmp/wwl-stage-thermal-inverse-runner-20261012/REPORT.md` 和 `v2/execution.json`；它们是本次执行过程记录，读者复算只需本实践保留的源码、输入及结果。

| 正式输出 | SHA256 |
| --- | --- |
| results.json | `20fa02263e32c23a2d742cd08d80e8d933415d354df00dd82bd0c9dcdf42c2a8` |
| estimates.csv | `1ff483f0811b0cac01b0aff190b8a599ec98db78733da1bf98b76190bfe7deab` |
| thermal_inverse.svg | `e8965903bf3af22a151cb623bd0e468c8f7f4a05c4a6668f88e9c3724906bbf0` |

## 实际核对支持什么

独立执行共16次：默认、现存输出目录保护、改变时刻／真值／观测／D/S、合法极端及密集输入，以及11个非法输入。保护拒绝后旧输出逐哈希不变；非法输入未生成输出目录。先于候选运行的独立有理数／解析核对确认以下结论：

- Neumann 两模态直接代入、归一 Gram 与物理时间尺度，$A=\operatorname{diag}(1,.01)$、$\kappa_2=100$ 的有限范围。
- 主观测直接逆 $(1,2)$、岭 $(10000/10001,1)$；改观测后直接逆 $(1,11/10)$、岭 $(10000/10001,11/20)$，总误差平方分别 $1/100$ 与 $81/400+1/100020001$。
- A/B 均值相同、后验协方差相差4倍；A 的 $m=1,2,4$ 弱方向方差为 $1/2,1/3,1/5$，零方向仍为先验方差1，B 对应值均乘4。
- 参数与观测尺度变换携带矩阵、噪声和先验协方差后，均值与协方差回映精确等于原结果。

最终默认、改变条件、极端尺度／长情景名、8情景／32重复次数四幅 SVG 均实际 Cairo 渲染并查看；标题、刻度、图例、模型卡与曲线在画布内。初版存在的标签重叠／裁切已修正，并以最终源码重新执行和渲染，正式结果是最终版。全文镜像必须与这个源码身份相同。

这份运行核对有限教学模型和其真实产物，没有验证真实温度仪器／数据、实际 Obsidian 显示或真人学习。一般卷积／边界伴随、二维 PSF、稀疏先验、独立参数选择与 #183 的完整课程责任仍按主课保留；没有重跑成熟全库实验。
