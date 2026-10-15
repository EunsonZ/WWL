# 理想与曲线的实际有限复算

本目录保全 2026-10-10 独立执行者的实际结果。课程阅读入口是 [理想与曲线精确复算](../../80-理想与曲线精确复算.md)。[原始报告](original/REPORT.md.txt)、[全部实例](original/all-instances.json)、[环境](original/environment.json)、[288 项独立比较](original/oracle-results.json)和[90 个 API 观测](original/api-probe-stdout.json)可以分别检查结论、退出码和原始数值。原报告 SHA256 为 `b0f3be9906754312a8cbf279c9c8962e3891761ca7a3f5846a10aceec6cd4495`。

`original/` 是逐字保全的历史证据，含 35 原件和原 `artifact-hashes.json`；总计 36 文件、273955 字节。[copies.json](copies.json)记录原路径→正式副本路径、字节数与 SHA256。仅 `REPORT.md` 改名为 `REPORT.md.txt`，文本字节未改。原包含源码/输入/手写预期的 snapshot、负向输入、两版 oracle、API 驱动、原 stdout/stderr、命令/cwd/环境及资源记录，包含预期 exit1。独立 oracle 不导入业务源码；API 驱动为获取观测而导入 snapshot。r1 oracle 原执行结果保留；`independent_oracle-r1.py` 是事后逆转明确纯追加编辑恢复的副本，不能称为另一次执行源码的事前冻结。

两固定 CLI 各 exit0，stderr 空，输出同为 6908 字节且逐字相同。最终 oracle 288 项 match、failed_checks=[]；90 个 API 观测中 63 个为预期拒绝，余下为合法值或合法证书。布尔原点负向 CLI 为预期 exit1、stdout 空、stderr 含 `ValueError: integer fixed points required`。这是停止证据，不能把捕获器外层 exit0 改称子进程成功。

除法停止探针仅在已加载模块内暂设 MAX_STEPS=2/3：对 x³−1 除 x−1，2 拒绝而 3 返回 x²+x+1 和零余式，随后恢复 2000；磁盘源码未改。默认常数 2000 被核对，但没有自然构造 2001 步实例。单个子进程墙钟约 0.03–0.04 秒、RSS 18792448–21364736 bytes（约18.8–21.4 MB）；未测 A/B 聚合内存，线程环境请求也不是 OS 硬限制。这些有限观察不替代一般定理、其他特征源码行为或人已理解。

## 在新空目录复建

[rebuild.py](rebuild.py) 是本轮新增的便携复建接口，**仅静态审阅，NOTRUN**。它不调用原 capture.py：后者含此次恢复路径身份检查，只保全为历史工具。未来执行需要 Python 3.10+ 标准库；无需恢复 `.venv-issues-111plus`。在本目录运行下面命令，将示例绝对路径换成一个尚不存在的新目录：

```bash
python3 -B rebuild.py --work /absolute/path/to/new-153-run
```

脚本先核原 manifest 的 35 文件 SHA/字节，再新建工作目录，仅复制四份 snapshot 源码/输入/预期、api_probe.py、最终 independent_oracle.py 和负向输入。**不复制历史输出、execution、oracle-results 或 capture.py**；若目录已经存在即停止。独立 oracle 硬编码读取新工作目录的 fixed-cli-stdout.json 等文件，因此固定实例名保持不变，不能靠改 job 名绕过旧结果污染。

新实例按固定 CLI、examples CLI、API probe、布尔负向 CLI、最终 oracle 顺序执行。实际命令分别为 `python -B code/affine_exact.py --input code/fixed-inputs.json`、`python -B code/examples.py`（cwd=snapshot），以及 `python -B api_probe.py`、`python -B snapshot/code/affine_exact.py --input invalid-fixed-bool-point.json`、`python -B independent_oracle.py`（cwd=新工作目录）；python 是启动 helper 的同一解释器。每个实例超时60秒，原 stdout/stderr及execution JSON写入新目录；status=completed 且 exit_code 达到预期，并核 stderr 空或准确负向错误后才继续。任何不符或超时都会让 helper 非零退出，保留已获得原证据而不生成完成文件。

最后还核两个 CLI 字节相同、90 观测/63 预期拒绝、oracle checks_total=288/all_match=true/failed_checks=[]/business_api_imported=false，及复制源码与输入未漂移，才生成 REBUILD-COMPLETE.json。新 helper 不采集 RSS，未声称完成新的数值运行；即使未来复建通过，也不能把原执行环境、r1 历史恢复来源、默认2000负荷边界或理论证明改写成新观察。
