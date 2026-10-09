# 2026-10-10固定分布的独立执行与可复建输入

本目录已逐字接收独立执行者的21个冻结文件，核对见 [copy-receipt.json](copy-receipt.json)；原执行包的20项身份在 [artifact-hashes.json](artifact-hashes.json)。新增的本入口与复制回执不冒充原包已有文件。作者供件时的 [运行前解析预期](analytic-expected-before-run.json) 也随本入口交付。原回执 [REPORT.md](REPORT.md) 保持历史字节，其末段“待复制”描述执行者交接时状态；复制至这条正式课程路径已由本目录回执另行记录。

业务源码/输入快照在 [snapshot/learning_theory.py](snapshot/learning_theory.py) 与 [snapshot/inputs.json](snapshot/inputs.json)，SHA分别为 `3d9b9e02590f6833a8804db213aff5c0ad271183a5c3455ee8aec4363802def8`、`263d889a428142306075532f104118cb75f6760f129f9b55d1f86e8310aa3f1e`，与当前课程实验源码相同。[independent_oracle.py](independent_oracle.py) 不导入业务实现，通过原四点分布256个有序n4样本、完整目标驻点/边界比较及直接测试积分，另以矩公式和二元串判据核更大n、增长与复制行。

macOS 27.0.1 arm64、Python 3.14.7下，直接业务命令退出0，墙钟0.045730秒，子进程峰值RSS21,708,800字节；测量版独立oracle退出0，0.637854秒、RSS22,904,832字节，全部2820字段/性质比较匹配。环境、原命令、输出与资源在 [environment.json](environment.json)、[execution-direct.json](execution-direct.json)、[stdout-direct.json](stdout-direct.json)、[stderr-direct.txt](stderr-direct.txt)、[oracle-execution.json](oracle-execution.json)、[oracle-stdout.json](oracle-stdout.json)、[oracle-stderr.txt](oracle-stderr.txt)、[oracle-results.json](oracle-results.json)。该计数不等于独立理论证明数量。

首次 `/usr/bin/time -l` 观测器因sandbox的 `sysctl kern.clockrate` 拒绝返回1；完整 [execution.json](execution.json)、[stdout.json](stdout.json)、[stderr-time.txt](stderr-time.txt) 保留。直接执行重试得到业务真实exit0，两次stdout的SHA相同。不能把观测器失败当业务失败，也不能删去失败记录伪造全绿路径。60秒子进程停止机制属于该次执行；线程环境请求4并非OS硬限制，逐进程RSS也没有认证A/B聚合峰值或8GiB硬cap。

原捕获脚本保留其历史绝对路径与环境身份，只作来源记录。重建时使用本目录快照和以下新目录接口，不需要隐藏恢复区。先进入本结果目录；命令只静态审阅，本次交接未另重跑：

```bash
task_learning_run="$(mktemp -d)" &&
mkdir "$task_learning_run/snapshot" &&
cp snapshot/learning_theory.py snapshot/inputs.json "$task_learning_run/snapshot/" &&
cp independent_oracle.py "$task_learning_run/" &&
python3 -B "$task_learning_run/snapshot/learning_theory.py" --input "$task_learning_run/snapshot/inputs.json" > "$task_learning_run/stdout.json" 2> "$task_learning_run/stderr.txt" &&
cp "$task_learning_run/stdout.json" "$task_learning_run/stdout-direct.json" &&
python3 -B "$task_learning_run/independent_oracle.py" > "$task_learning_run/oracle-stdout.json" 2> "$task_learning_run/oracle-stderr.txt"
```

所有后续步骤以先前退出0为门；若业务失败不会复制输出或执行oracle。oracle核对两份输出的身份，因此新运行明确复用同一业务输出的两个文件名，并不模拟原来time观测器失败。记录新命令、源码/输入身份、环境、时间及退出码。

运行前声明有条件继续，业务失败时不执行复制/oracle；oracle失败保留新目录及所有输出。这里的普通命令不自动强制线程/资源/60秒停止，也不冒称具备原捕获器的资源测量；需这些层时由已授权执行通道设置并记录。课程一般证明、Obsidian渲染/同步和真人学习不由有限运行认证。

回 [[AI/10-机器学习与深度学习基础/30-统计学习理论/80-有限分布复算与条件破坏|解析答案与条件破坏]]，再到 [[AI/10-机器学习与深度学习基础/30-统计学习理论/03-正则化稳定性与范数复杂度|稳定性/复杂度主解释]]核对有限实验怎样对应一般条件。
