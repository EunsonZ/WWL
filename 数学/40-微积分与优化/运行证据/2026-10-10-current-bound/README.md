# 当前源码与QP依赖绑定的有限复核

这是2026-10-10独立执行者保存的有限运行材料，原文件逐字节迁入本目录。默认有理数例、固定8步QP与独立oracle三条job均returncode 0；原始命令、环境、固定完整输入、stdout/stderr、两规范源码快照及独立核算保留。旧 `../2026-10-09-convex-independent.json` 原字节不改，其历史QP依赖未绑定的问题也不被回填成已知。

从本目录阅读：

- [实际命令、来源绑定与返回码](2026-10-10-current-bound.json)、[完整固定输入](fixed-inputs.json)、[独立检查与环境](independent-checks.json)。
- [默认原始输出](default.stdout)、[QP原始输出](qp.stdout)、[独立oracle原始输出](oracle.stdout)及同名stderr；[执行者原报告](report.md)记录失败采集尝试和资源观察边界。
- [独立oracle源码](oracle.py)、[实际采集器](run.py)、[原包文件SHA](artifact-sha256.json)；原包中的两次采集器失败输出继续保留，不作为数学失败。
- [证书源码快照](sources/数学/40-微积分与优化/convex_duality_certificate.py)、[实际导入QP模型快照](sources/AI/45-机器人与具身智能/10-LQR与约束控制/code-sync/lqr_mpc_lab.py)。当前规范真源分别为 [证书脚本](../../convex_duality_certificate.py) 与 [LQR/QP模型](../../../../AI/45-机器人与具身智能/10-LQR与约束控制/code-sync/lqr_mpc_lab.py)。

## 结果与证明边界

证书脚本SHA为 `548247d8f94cf392300088526d91adb855c3bdfe013696956f3ffeb4a5b5e097`，实际导入LQR/QP模型SHA为 `74df452671104f43afbee10466a99d5618d75236855d9bf7410eaf4049bf98a5`，运行前后相同。独立oracle从双积分器闭式响应以有理数重构H/f/c，再通过独立坐标最小化、物理状态递推和拉格朗日下确界核对输出，未调用作者QP求解器来产生独立解。

固定盒QP目标约1.1608503889191786，对偶评估约1.160850388919179，gap约−4.44e−16，驻点残差约4.44e−16，原始/对偶违规与互补残差为0；无约束解剪裁目标约1.8471655856219151，驻点残差约1.4901。微小负gap属于浮点评估层读数，没有区间误差包络，不能称为严格包围下界，也不能用有限运行证明一般弱/强对偶定理。理论条件与证明回到 [[数学/40-微积分与优化/08-凸优化对偶与最优性证书|对偶与最优性主解释]]。

默认例、QP、oracle耗时约0.034/0.238/0.117秒，各设60秒超时。记录的累计完成子进程最大RSS为34,783,232字节；这不是独立实时内存曲线或硬内存上限。五类数值线程环境变量请求4线程，没有观察OS实际线程数，也不据此认证硬线程限制。原始ps观察拒绝及RLIMIT_DATA采集失败已保留；未为采集增加系统权限。

## 从本库重新运行的接口

记录中的旧绝对argv及 `.wwl-recovery` 路径仅描述当时执行位置，是来源元数据，不是运行依赖。当前目录与原执行目录到库根的相对层级相同，采集器/oracle从自身位置推导库根；不读取隐藏恢复区。解释器和NumPy按库根 `requirements-issues-111plus.txt` 与 [已保存环境说明](../../../../scripts/ENVIRONMENT.md)准备。本次实跑环境为macOS arm64、Python3.14.7、NumPy2.5.3/Accelerate，其他环境的结果和资源单位须另行记录。

在库根直接复算当前规范脚本，只输出stdout：

```bash
.venv-issues-111plus/bin/python -B 数学/40-微积分与优化/convex_duality_certificate.py
.venv-issues-111plus/bin/python -B 数学/40-微积分与优化/convex_duality_certificate.py --qp-vault-root .
```

若还要重收完整三job及独立oracle材料，使用全新结果目录，保留本次历史文件：

```bash
task_recheck='数学/40-微积分与优化/运行证据/local-recheck-20261010'
mkdir "$task_recheck"
cp 数学/40-微积分与优化/运行证据/2026-10-10-current-bound/run.py 数学/40-微积分与优化/运行证据/2026-10-10-current-bound/oracle.py "$task_recheck/"
.venv-issues-111plus/bin/python -B "$task_recheck/run.py"
```

新目录须先不存在；若名称已占用，换一个新名称。采集器用新目录文件的排他创建保留旧材料，oracle核该目录的新stdout及当前规范QP模型。重新运行前先比较两规范源码SHA；若当前文件已改，不应把新结果当成本历史版本复跑。源码快照供核对旧输入身份，不由采集器反写规范源码。

这是已执行的固定有限例材料和可复建接口，未认证通用求解器、真实控制器、物理硬件、客户端显示或真人学习；整合者只复制材料与接口，没有再次执行本包。
