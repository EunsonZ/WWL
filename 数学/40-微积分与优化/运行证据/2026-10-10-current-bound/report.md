# #147 当前版本绑定有限实验

2026-10-10；独立执行者 A。当前默认有理数示例、固定 QP 实跑及独立数值核对通过。仅写本目录，未改课程源码、正式运行证据、环境或 Git 状态，未派生代理、安装依赖或执行 LQR 绘图/历史脚本。

入口为 `2026-10-10-current-bound.json`；`default.stdout`、`qp.stdout`、`oracle.stdout` 与各自 `.stderr` 保留原始输出；`fixed-inputs.json` 保留实际 API 的 A/B/Q/R/Qf/x0/G/M/H/f/constant、盒界与独立有理矩阵；`independent-checks.json` 保留独立核对及解释器/NumPy/Accelerate 环境。`sources/` 含两份当前规范源码与同版根 AGENTS。`run.py`、`oracle.py` 为可检查的采集器和独立 oracle，均未修改规范课程源码。

## 当前绑定

- `数学/40-微积分与优化/convex_duality_certificate.py`：SHA256 `548247d8f94cf392300088526d91adb855c3bdfe013696956f3ffeb4a5b5e097`。
- 实际导入的 `AI/45-机器人与具身智能/10-LQR与约束控制/code-sync/lqr_mpc_lab.py`：SHA256 `74df452671104f43afbee10466a99d5618d75236855d9bf7410eaf4049bf98a5`。
- 静态检查顶层的动态导入位置及模型的导入列表；这条 QP 路径没有其他库内源码依赖。oracle 的实际库内模块清单也只含该模型和 oracle 自身。两份课程源码运行前后哈希一致。
- `.venv-issues-111plus/bin/python`，Python 3.14.7、NumPy 2.5.3、macOS 27.0.1 arm64；BLAS/LAPACK 为 Accelerate。未使用旧 `.venv` 或修改系统环境。

## 结果与独立判断

默认命令耗时约 0.034 秒、QP 命令约 0.238 秒、oracle 约 0.117 秒，均 returncode 0，各设 60 秒超时。这组即为 60 秒预跑，已足够，无需扩大或全队重跑。

参数族、有限退化乘子、近端合法步长和 t=3 二周期、LP 合法/非法预算、SVM 硬间隔与 C=.1 反例均按具体输出独立核对。近端 oracle 逐步最小化分段标量二次式，LP 五个可行覆盖穷尽八个二元指派。未把脚本自报通过作为独立依据。

QP 以有理数从双积分器闭式位置/速度响应重新构造 H/f/c，和当前 API 完整矩阵差异小于 1e-14；独立坐标最小化 149 轮收敛，控制向量与实跑解差异小于 1e-10。用原始物理递推另算目标，用拉格朗日二次式最小化另算对偶值，并核对原始/对偶可行性、驻点和互补残差。

| 点 | 独立物理目标 | 独立拉格朗日下确界 | gap | 驻点残差 | 原始/对偶违规 |
| --- | ---: | ---: | ---: | ---: | ---: |
| box QP | 1.1608503889191786 | 1.160850388919179 | -4.44e-16 | 4.44e-16 | 0 / 0 |
| 无约束解剪裁 | 1.8471655856219151 | -5.701149510477821 | 7.548315096099736 | 1.4900971877364908 | 0 / 0 |

两点互补残差均为 0。剪裁点满足盒约束，但目标比 QP 高约 0.6863，驻点失败。QP 的微小负 gap 是浮点舍入层的读数；本实验没有区间算术，不能宣称严格包围浮点下界，也不能用有限运行证明一般对偶理论。理论由既有独立 review 承担。

## 资源与采集器边界

每个子进程设置 OMP/OPENBLAS/MKL/NUMEXPR/VECLIB 五类线程环境变量为 4，顺序执行，未与本任务内其他数值任务并发。RUSAGE_CHILDREN 的最终累计最大 RSS 为 34,783,232 字节，oracle 自身最大 RSS 相同，远小于 4 GiB 目标；该值为已完成子进程集合的峰值上界，不是每个子进程的独立实时曲线。

第一次采集器在启动默认命令后尝试 `ps` RSS 观察，得到 `PermissionError: [Errno 1] Operation not permitted: 'ps'`；对应原始默认输出保留为 `collector-first-attempt.stdout`，采集器尚未生成结果。不把这个采集器错误算作数学失败。第二次试加 RLIMIT_DATA，子进程在启动前报 `subprocess.SubprocessError: Exception occurred in preexec_fn.`，空输出保留为 `collector-second-attempt.stdout/.stderr`。最终移除该不可用的限制，容错保留 ps 拒绝，按超时和已完成运行峰值记录完成三项。

因此未硬限制总 RSS，未观察 OS 实际线程数，环境变量只是数值运行时的线程上限请求；没有因此请求扩大权限。本次无超时，无源码 bug。旧证据缺少历史导入模型 SHA 的事实仍保留，本结果提供的是 2026-10-10 当前字节绑定的必要补证。
