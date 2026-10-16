# 两资源恢复实验：事实、位置和效果分别在哪次提交后成立

主解释：[[计算机知识/55-数据库/10-系统课程/18-源位置状态快照与目标恢复|源位置、状态快照与目标恢复]]。先预测提交前后的持久状态，再运行。本实验用不可变JSON源和两个本地SQLite资源，只有Python 3.10+标准库；实际运行Python3.14.7、SQLite3.53.4、macOS27.0.1 arm64，细节见[summary](results/summary.json)。无编译、依赖安装、外部服务、消息平台、邮件或支付。

## 真源、输入和原始证据

- [source.json](source.json)：协议 `wwl-db18-source-v1`，source_id为teaching-authority-A，18项固定输入，文件原字节SHA256为 `102fa17e364a84d67fed1d00f05e19e4f7916844ffe7ba20379b5da724305666`。含同id重放、同id异payload、同version异内容、stale、换组、删除、墓碑、复活、invalid后修正同id。
- [recovery_worker.py](recovery_worker.py)：两个连接、两个资源；state中原子保存完整业务状态及源位置，sink中原子保存效果与稳定身份/指纹/权威结果。显式bad模式是教学反例，不是可选生产配置。
- [batch_oracle.py](batch_oracle.py)：从原始已接受快照历史重建每前缀实体，SQLite全量GROUP BY；相邻批量视图之差构造参考效果。没有导入worker或调用reducer作答案。
- [run_experiment.py](run_experiment.py)：父进程driver，启动自己的worker、匹配精确屏障后SIGKILL、等待−9、重开查询两库、重启以及重放；不枚举或终止用户已有进程。
- [test_recovery.py](test_recovery.py)：18个逐前缀协议/状态/效果核对、原目标结果重开复用、同身份异参数拒绝、源/角色绑定、坏文件、关键身份损坏检测。单测里的应用异常专门标为NOT a process kill；真正kill证据来自driver。
- [run-result.json](run-result.json)、[test-result.txt](test-result.txt)、[experiment-result.txt](experiment-result.txt)：本次总命令、退出码与原始标准输出。版本身份在[results/summary.json](results/summary.json)的源与四份源码/测试SHA256中；改变源码后不能继续用该结果认证新字节。
- [results/batch-truth.json](results/batch-truth.json)：独立批量参考的完整实体、身份、claims、位置裁决、11个目标效果及权威结果，非从worker终局反拷。

每个场景目录保存 `first.stdout.jsonl`、`first.stderr.txt`、`first.process.json`、`cut-observed.json`；有故障则另有restart原始输出/进程记录；正确场景还保存完成后resume与fresh_state_replay原始输出/进程记录。`final-observed.json`是新连接从两库的实际读事务快照；`result.json`保存逐个已提交检查点与批量参考的精确比较。单次stdout可能含未提交裁决，只有state_committed及重开快照可用于认证state持久结果。

原始SQLite工作文件在运行命令的独立`--work`目录保留，不放入正式正文或依赖它们才能阅读；本次实际路径见run-result和各process记录。各库的WAL/SHM由SQLite管理，禁止手动删除WAL后把剩余主文件称为同一证据。正式实践保留完整原始stdout、屏障、退出码及数据库内容快照，源码与输入可在新目录复建。

## 先写预期，再执行

B=2，前两项是f/F11与a/A10。先回答：

1. after_sink p1时，目标已提交F11/1，而state尚未提交。kill后P应为0；无去重目标重启后F22/2，正确目标仍F11/1。
2. 错序after_offset p2时，P已2而state为空，目标也空。重启从p3继续，f不会再出现，终局应少11/1；不要只检查P是否到了18。
3. 正确before_state_commit p2时，kill后state应仍P0/空，目标已有F11/1与A10/1；after_state_commit p2则state与P一起为已处理两项。两种都能恢复到25/4、11效果。

在Vault根运行，输出与工作目录必须是新目录：

```bash
recovery_run=$(mktemp -d /tmp/wwl-source-state-sink.XXXXXX)
python3 -B -m unittest discover \
  -s 计算机知识/_labs/round3/DB/source_state_sink_recovery -p test_recovery.py -v
python3 -B 计算机知识/_labs/round3/DB/source_state_sink_recovery/run_experiment.py \
  --source 计算机知识/_labs/round3/DB/source_state_sink_recovery/source.json \
  --out "$recovery_run/evidence" --work "$recovery_run/databases"
```

driver共11场景，其中7次真正SIGKILL，POSIX平台才运行。它用Popen得到自己worker的PID，核验worker输出的PID、一次性token、切面和位置，才发SIGKILL。worker在屏障后阻塞，父进程不是靠固定sleep猜时点。屏障最多等15秒，子进程收尾有超时；清理超时子进程不是成功故障证据，场景缺屏障或返回码不为−9即失败。每个正常/重启worker必须返回0。

本次正式整组经全局两槽包装器 `/private/tmp/wwl-next-context/run_local.py --timeout 300 -- <实际解释器> <argv>` 运行，CPU线程=1，墙钟上限300秒；包装器路径是本次调度设施，不是读者运行本实验的依赖。test-result为6测试、0.283秒、退出0；driver为3.686秒、退出0；含两者的总过程4.086秒。先前driver在ASCII固定日志已通过，随后仅完善屏障stdout对任意UTF-8分块的解码，当前结果已经按最终driver重跑；旧过程不充当最终字节证据。

## 11个场景具体检查什么

| 场景/结果 | 实际切面与变式 | 预期恢复/反例 |
| --- | --- | --- |
| [normal_b1](results/normal_b1/result.json)、[b2](results/normal_b2/result.json)、[b4](results/normal_b4/result.json)、[b7](results/normal_b7/result.json) | 无kill，B=1/2/4/7 | 所有已提交批尾状态等于同源前缀；最终25/4、11效果；完整检查点resume不变 |
| [kill_sink_naive](results/kill_sink_naive/result.json) | atomic state，after_sink p1；sink不去重 | −9后重启0；目标F22/2，总36/5、12效果；预期不等于批量参考 |
| [kill_sink_dedupe](results/kill_sink_dedupe/result.json) | 同切面，目标身份/指纹/原结果同事务 | −9后重启0；目标F11/1；最终25/4、11效果，原effect_seq=1复用 |
| [kill_offset_first](results/kill_offset_first/result.json) | 单独先提交P2，after_offset p2 | −9后重启0；终局少f/F11，只14/3、10效果；P虽18仍不正确 |
| [kill_atomic_before](results/kill_atomic_before/result.json) | before_state_commit p2 | −9；state旧P0/空、sink领先两效果；重启正确 |
| [kill_atomic_after](results/kill_atomic_after/result.json) | after_state_commit p2 | −9；state新P2与两事实同存；重启正确 |
| [kill_update_sink](results/kill_update_sink/result.json) | B2，after_sink p5，a更新+5 | −9；state P4、A30/2，sink A35/2；重放+5不再施加 |
| [kill_atomic_b4](results/kill_atomic_b4/result.json) | B4，before_state_commit p4 | −9；state P0/空，sink三效果A30/2、F11/1；批尾含duplicate仍恢复正确 |

每个正确场景还有两个实际变式：重开同一完整state继续消费应无新效果；新建空state从源首项全量重放到**同一个已完成sink**，所有目标收据/原result/效果账本与sum/count完全不变，重建state完全等于原完整state。不是只重复跑一个空命令。

9个正确场景全部匹配；2个反例按预期不匹配，因此总报告status=pass并不表示bad模式也正确。无去重反例的实体/视图可以正确，但目标效果与state交付结果序号已偏离正确参考；错序反例连实体、身份和位置裁决也缺失。两种不能用“最终程序返回0”认证。

## 高重要性断言、失败判据与容差

| 断言 | 为什么重要 | 命令与判据 |
| --- | --- | --- |
| state的P、实体/墓碑、seen、claims、view、裁决和交付结果属于同一已提交前缀 | P新而事实旧会跳过源，sum碰巧收敛也掩盖身份丢失 | 六测试逐18前缀＋driver每个state_committed批尾，与独立oracle逐字段相等；任何字段不同失败 |
| sink效果/收据/指纹/原result同事务，稳定业务效果身份永久保留 | 只存seen或只用唯一键无法覆盖另一个资源；unknown需查原结果 | after_sink真kill、重开同结果、同id异body冲突、fresh-state重放；正确场景账本11效果，不能多也不能少 |
| 只有精确屏障后−9才算kill证据 | 抛异常和随意时点终止不能检验所声明切面 | driver 7场景first.process含对应barrier/PID/token和returncode−9；restart必须0；缺项即失败 |
| 无去重与位置先提交确实错误 | 如果故障没有显现，可能挑了会被后续覆盖的事实或没有击中间隙 | naive目标F22/2、12效果；offset-first终局缺F11/1、10效果；都必须与参考不等 |
| 版本、历史claim、墓碑及参数指纹在恢复中不丢 | 旧版本可能复活，重放可能变新身份，同版异内容会被悄悄接受 | 固定原始log完整裁决；篡改seen/claim/positions/deliveries或目标指纹要被oracle检测 |
| 原文件版本和逻辑算法不偷换 | 同一P套到另一日志不能定义S(P) | metadata绑定源原字节hash、协议、角色与模式；修改源hash、角色或目标去重模式应拒绝复用；无自动迁移 |

比较都是整数、规范JSON文本和有序账本的**零容差**比较；不是浮点性能指标。读DB快照使用新连接、显式读事务、integrity_check=ok。source、四份源码/测试SHA256及实跑环境记录在summary；同版源码镜像在主解释。构造器模式不支持任意已有数据库、自动schema升级或追加源，运行只应指向实验新目录；当前open_resource在metadata校验前先设置PRAGMA WAL，可能持久改变外来数据库的journal_mode，因此不承诺未知库的原字节保全，也不应拿个人/业务已有库试探模式；指纹不是认证与防篡改机制。若sink的原裁决、缓存结果或被篡改的收据本身错误，幂等只稳定返回错误，不提供业务自修正；正确权威结果属于本模型前提。

作者运行与独立算法仍由作者完成，不能替代非作者独立核查。一般恢复证明及其假设在主解释中；有限场景和两个程序同意不认证全部调度、无限故障或生产吞吐。

## 真实接口仍须另验

| 未验接口 | 应提供的输入/故障点 | 必须观察的结果与前提 |
| --- | --- | --- |
| 真实可重放源 | 分区/epoch/不可变位置、保留期；目标已提交但源端确认丢失 | 原业务身份和原字节仍可读；源端确认语义不得等同本地P |
| 远端幂等sink | 稳定业务key、规范参数指纹、原权威查询结果；提交成功答复丢失 | 目标必须把身份/效果/结果原子保存，重试同参返回原结果；不具备则接受重复风险或另设计补偿 |
| 持久窗口消费者 | 第17讲W/活动窗/revision/回收/旁路及源位置 | 同一快照与输出身份策略；本次无窗state不能直接认证窗口恢复 |
| 断电/磁盘或WAL损坏 | 隔离备份、实际存储/VFS/同步设置、可恢复系统级故障 | power-loss、完整性与RPO/RTO证据；本次SIGKILL仅终止worker，操作系统活着 |
| 多分区/多worker/升级 | 一致切面、事务竞争、算法与指纹版本迁移、目标收据保留屏障 | 不能用单写者本地提交推断分布式exactly-once；也不能随TTL删除身份后沿用本证明 |

本课不修改SE82预约合同，不给真实邮件/支付做幂等承诺。返回主解释的迁移题比较提交边界，再接 [[计算机知识/55-数据库/10-系统课程/19-分析模型维度历史与变更捕获|第19讲的星型/SCD、变更捕获与分析计算成本]]；它运行的是独立本地触发器与布局实验，不扩大本课恢复范围。整课状态与远端连接器/真实引擎/持久窗口等未验接口回当前#172及各单元README。
