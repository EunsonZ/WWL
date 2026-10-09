# IC v1 有限容器：当前版本运行与复现

本目录记录同一教学消息 `AAAABBCD`、P/Q 码本和 IC v1 自定义容器的有限检查。规范源码为 [information_container_practice.py](../information_container_practice.py)，SHA256 固定为 `7a4d8824b776e11810038dca5010ffb31c2dd564178158a54f9e85f60d78b31d`；[实践页](../information_container_practice.md) 连接格式定义和符号账本。

首次独立执行已保存于 [historical-first-run/report.md](historical-first-run/report.md)。其中原命令的绝对候选位置、assembly/diff 快照是首次运行的来源记录；它们保持原字节，不是公开复现的运行依赖。当前目录的 [run.py](run.py) 和 [oracle.py](oracle.py) 只依赖正式库规范源码和标准库；oracle 不读取规范源码的 `EXPECTED_P/Q` 或调用其 `run()`，以单独给出的码字、逐 bit 索引打包和码字树解码核对全部字段。

<!-- portable-result-entry -->

P/Q 均为 6 byte 头、12 byte 码表、2 byte 载荷、1 byte sum8，总计 21 byte / 168 bit；有效载荷分别为 14 bit + 2 bit pad、16 bit + 0 bit pad。独立枚举覆盖 ABCD 上长度 1–4 的 340 条消息及两种码本，共 680 个完整容器/解码例；另有 25 个拒绝夹具和 4 个合法边界。Q 载荷 `00 5b` 改为 `01 5a` 仍保持 sum8，合法解出 `AAABBBCC`，说明这个弱校验不能可靠检测任意损坏。

固定账本将 168 file bit 按 R=1/2 二重复为 336 channel bit；每符号 2 bit，加 8 同步和 4 导频得到 180 symbol，在题设 1000 symbol/s 下为 0.180 s。不重复为 96 symbol / 0.096 s。这些是题设预算，没有测量物理链路、同步、调制、均衡、纠错、BER 或实际吞吐，不能代替一般编码定理。

从库根直接运行规范示例（只写 stdout）：

```bash
python3 -B 数学/50-信息论/80-运行证据/information_container_practice.py
```

完整采集在**新的空目录**运行，避免覆盖既有证据。保持目录深度，采集器才能把 `OUT.parents[3]` 解析为库根：

```bash
mkdir 数学/50-信息论/80-运行证据/information-container-new-run
cp 数学/50-信息论/80-运行证据/2026-10-10-information-container/run.py 数学/50-信息论/80-运行证据/information-container-new-run/
cp 数学/50-信息论/80-运行证据/2026-10-10-information-container/oracle.py 数学/50-信息论/80-运行证据/information-container-new-run/
.venv-issues-111plus/bin/python -B 数学/50-信息论/80-运行证据/information-container-new-run/run.py
```

该采集命令使用本次既存 Python 虚拟环境；环境本身不随 Git 交付，也没有安装新依赖。新克隆可用已有 Python 3 标准库环境，把采集器中的 `PY=ROOT/'.venv-issues-111plus/bin/python'` 明确指向该解释器后记录这项环境差异；规范示例本身不依赖虚拟环境路径。采集器保存实际解释器、命令、源码运行前后哈希和原始 stdout/stderr；stdout/stderr 用独占创建；采集器在打开这些输出前会先写 `sources/` 快照，因此不能在已含证据的本目录原地运行，应始终按上述新空目录接口保全原件。

线程环境变量请求 4，任务顺序执行并设 60 秒超时；RSS 只报告完成子进程集合峰值。没有硬内存限额或 OS 实际线程数证明。有限输入检查不认证任意输入正确性、真人学习或客户端行为。#181/#219 的下游实现与物理信号处理另由各自任务验收。
