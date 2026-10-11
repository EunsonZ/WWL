# 科学对照、性能观察与有界取消的实际运行

2026-10-11续接已签收同步切片，核心包0.1.0/API没有变化。首段 [VERIFICATION.md](VERIFICATION.md) 保留当时证据；本页记录后续实验，不能把较新的科学环境版本混入首段标准库结果。

## 实际环境与依赖复用

- 标准库实验：新的隔离 `core-env`，已有CPython **3.12.11**、SQLite **3.49.1**、macOS27.0.1 arm64。
- 科学实验：新的隔离 `science-env`，CPython **3.14.7**、SQLite **3.53.4**；通过候选环境自己的 `.pth` 只读复用主库已有 `.venv/lib/python3.14/site-packages` 的 **NumPy2.5.3**。这不是独立重装科学依赖；复建须找到已授权的可用NumPy环境。没有修改主库环境，没有安装NumPy/pandas/psutil。
- 两个新环境均用 `--no-index --no-deps` 安装首段已签收wheel，SHA-256 `6665ea22d7bf341ca498a0045ff03d16d8ca3fbbdc0586c163fe6901451c8072`。新脚本是课程源码实验，以绝对路径调用，核心模块来自新环境site-packages。
- 官方NumPy2.5文档与本机2.5.3官方docstring核对了dtype和ddof；Python3.11官方TaskGroup、resource与tracemalloc页已读取。Python3.11实际解释器仍未运行。

## 此次实际命令

下列路径是本机实验目录；读者先填并核对自己的路径，不把临时路径当安装要求。

```bash
ROOT='/private/tmp/wwl-python-next-candidate-20261011'
PROJECT="$ROOT/计算机知识/80-实践/01-Python/04-测量记录导入与分析"
PYTHON="$ROOT/core-env/bin/python"
SCIENCE_PYTHON="$ROOT/science-env/bin/python"
LAB="$ROOT/run-evidence"
cd "$LAB"
"$ROOT/core-env/bin/wwl-measurements" import "$PROJECT/data/measurements.csv" "$LAB/science.sqlite"
"$SCIENCE_PYTHON" -I -B "$PROJECT/examples/scientific_compare.py" "$LAB/science.sqlite"
"$PYTHON" -I -B "$PROJECT/examples/benchmark_import.py" --n 2000 --batch 64 --repeat 3
"$PYTHON" -I -B "$PROJECT/examples/bounded_pipeline.py" "$PROJECT/data/measurements.csv" "$LAB/pipeline.sqlite" --fail-id c
"$PYTHON" -I -B "$PROJECT/examples/bounded_pipeline.py" "$PROJECT/data/measurements.csv" "$LAB/pipeline.sqlite"
"$PYTHON" -I -B -m unittest discover -s "$PROJECT/tests" -v
"$SCIENCE_PYTHON" -I -B -m unittest discover -s "$PROJECT/tests" -v
```

`run-evidence` 预先创建；故障命令预期退出1，其他命令退出0。原始命令、cwd、stdout/stderr和退出码保存在本候选根 `run-evidence/next-commands.json`；原始日志属本机过程材料。供读者核对的固定有限结果汇合在 [reference/next-observations.json](reference/next-observations.json)，包含三实现数值、15条性能观察及故障/恢复行集。

| 实际观察 | 结果 |
| --- | --- |
| 同一已提交a–d，Fraction/独立SQL/NumPy | n4、sum20、mean5、pvar5、svar20/3、RMS²30；shape(4,)、int64码、float64电压、ddof显式0/1。另以WAL写者在两个SELECT之间提交a=9，显式读事务仍对原a=2快照计算；单行/空行分母边界也实际核对。 |
| a、b缺失、c、c重放政策例 | 有效a/c，拒绝1、重复1；mean4、pvar4、RMS²20。单纯nanmean为14/3，不能代替身份去重。 |
| 15次独立子进程性能观测 | 5类负载各3次；new/replay/append的提交计数与独立SQL总行数核对一致。秒数、Python峰值和进程峰值RSS均保留原始值。 |
| C1/B2，INSERT c后故障 | TaskGroup异常组、退出1；accounted4、joined_before_commit2、已提交a/b；生产者收到取消，两任务及资源收尾完成、关闭前无事务。 |
| 同一故障库修复重放 | 退出0；重复a/b、新增c/d，最终恰a–d。 |
| B4故障与C3正常 | B4在c后故障库为空；C3正常完成且队列高水位不超3。 |
| 外部取消未满批 | 消费第一条后取消；未启动数据批事务，最终0行；没有遗留asyncio任务，文件/连接已关闭。 |
| 标准库3.12测试 | 22项，21通过、1科学可选skip。 |
| 科学3.14测试 | 同一22项全部通过。 |

性能结果对应生成的合法Record和本机临时SQLite，不包括CSV/JSON/图/NumPy，不是生产容量或跨平台基准。RSS是子进程生命周期峰值，可能包含计时外预填，不能当作当前RSS或tracemalloc的另一种表达。异步生产者的await是教学上游模拟，SQLite仍同步执行；没有测试真实网络、远程副作用或后台线程的即时取消。

本机未执行pandas、Windows、Linux、Python3.11解释器和Obsidian实际显示，也没有验证抽样/仪器/真人理解。完整#245的指定理论返回页、跨语言同码比较与控制论/量子/半导体应用仍需各自内容与验收；这一后续片段不关闭issue。重要行为需要另由独立审阅者核对。
