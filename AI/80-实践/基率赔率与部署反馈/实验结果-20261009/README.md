# 基率赔率与部署反馈：2026-10-09 实际执行

本次对同目录课程源码的固定版本进行了标准库精确运算；没有训练、网络部署或依赖安装。执行槽 B 复制源码后运行，独立语义核查由另一代理负责。环境为Python3.14.7、macOS27.0.1 arm64、SQLite3.53.4；线程环境上限设为1。每条命令用时不到1秒、退出码0。

## 基率赔率

输入存于 [labelshift210/inputs.json](labelshift210/inputs.json)，完整源码路径与版本摘要存于 [source_snapshot.json](labelshift210/source_snapshot.json)。源先验1/2、目标先验1/1000、TPR9/10、FPR1/100。在课程实验目录执行：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python3 -B label_shift.py > output.json
python3 -B verify_label_shift.py < output.json
```

[实际输出](labelshift210/output.json) 给出告警时正类后验90/91→10/121，未告警时正类后验10/109→10/98911，二值分数AUC189/200。目标FPR改为1/50后告警时正类后验5/116。计数表oracle实际通过，见[日志](labelshift210/verification.log)。

执行槽另写的[独立oracle](labelshift210/independent_oracle.py) 使用直接联合质量和四种正负分数配对，未导入计算实现；在本结果子目录运行 `python3 -B independent_oracle.py`，[逐项核对通过](labelshift210/independent_verification.log)。它的期望不是从作者输出抄写而来。这是已知先验与稳定类条件分布的构造例；不等于未知先验估计、真实采样或模型部署结果。

## 部署反馈

[固定输入](deployment223/inputs.json) 是起点0、10步和固定分布均值1/4、噪声1/10。在课程实验目录执行：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python3 -B deployment.py > output.json
python3 -B verify_deployment.py < output.json
```

[实际输出](deployment223/output.json) 10步终点1023/2048；稳定点1/2与其风险1/4；风险最优点1/10与其风险1/20；从该最优点再重训得3/10。固定分布对照中稳定点与最优点都为1/4、风险1/100。

[实际核对日志](deployment223/verification.log) 通过了两点结果枚举、每步均值更新、闭式序列、支持区间、二次风险最优点及固定分布对照。源码版本见[source_snapshot.json](deployment223/source_snapshot.json)。这只复算给定合成反应机制的总体量，尚无有限样本训练、真实部署、福利目标或读者理解结果。

两个子目录各留有[环境](labelshift210/environment.json)。原始运行使用仓库的 `.venv-issues-111plus/bin/python`，可在具有相同Python标准库能力的环境复算；临时来源路径只是本次快照的出处，运行不依赖该路径。
