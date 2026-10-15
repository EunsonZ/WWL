# #174 独立执行回执（2026-10-10）

完成范围：冻结候选的固定单测、默认 JSON 演示、新建 Git 实验仓库，以及独立双进程/完整 trace/schema 原字节补证。该目录是执行证据，不是主库发布或一般合同证明。

## 输入与安全

`source-manifest.json` 固定作者十目标文件与两个原 v1 依赖副本，共12文件；规范 JSON manifest 的 SHA256 为 `2e3d79273555ff916397af6e6318db1961e1c47af858cbcfecc80666c59401ac`。六 Python 文件均从作者候选原字节复制到 `snapshot/`，运行不会 import 主库源码。根 AGENTS 和作者交接同存。静态读取确认：Python/SQLite标准库、无网络；Git只能新建子仓库、没有remote/push、每条调用禁系统/全局配置、禁签名、使用新建空hooks。作者和主库不写。

`fixed-runs.json` 保存 Python 3.14.7、Git版本、SQLite版本、平台、隔离HOME/XDG/TMPDIR、配置、线程环境请求、真实 argv/cwd/开始时刻/时长/退出码。依赖准备：无编译、无安装、无服务更改。每命令 timeout60秒；串行执行；双进程任务最多两独立worker。本包没有硬内存限额或实际OS线程计数的认证。

收尾 `source-recheck.json` 显示11文件仍同SHA；82页面从 `2f0ea025fb9a1ce79ef060b31919d45660767776c029396741597ad2f7de41dd` 变为 `75e0c0bf89ee195f7f1fbf373d03b826533a3751c91fffb2883644318cb0503e`。root确认这是授权的启动初始化锁边界说明；六Python和四镜像未改。本文不把原12快照总SHA重签给改后页面；82说明增量由 `../../review174/` 实际独核记录接续，运行行为可复用相同Python输入。本包无需重跑纯说明差异。

## 固定执行结果

1. `run_fixed.py`：22个固定单测全部OK，0.449s；默认demo退出0，0.034s；Git lab退出0，0.272s。原 stdout/stderr 在 `logs/unittest.*`、`logs/default-demo.*`、`logs/git-lab.*`。
2. 默认demo原JSON显示A/B/C policy1、客户端reply_lost unknown、重开D690–720 accepted id4、首次sink true/重复false、epoch3旧写者fenced且四预约保存。独立读取比对在 `verification.json`。
3. Git保留仓库在 `git-scratch/`，原 `exercise-result.json` 与stdout一致。双亲为policy/refactor；1021自动合并后错误true、修复后false；BUFFER15/20生成真实文本冲突，最终按批准10解决。每条Git argv/exit/stdout/stderr、commit IDs、graph、冲突原文均保留。仓库config无remote。
4. `observable-traces.py`退出0：`observable-traces.json`保留v1原实现与重构12步完整return/exception/message/before/after/next_id trace，含相邻、非法类型、冲突、越权、取消释放、重复取消、旧快照；10分钟错误变体在570邻接抛Conflict且不耗id。还保留D630–660拒绝、D690–720 id4、丢ack后sink重开首次/重复与同id改payload冲突、epoch2旧结果在epoch3同参重放等具体JSON。

## 独立双进程实际顺序

成功运行采用两个worker先各自Authority初始化完成的ready握手，然后在原transaction的BEGIN IMMEDIATE取得锁后hold；wrapper只控制时间，不替换业务SQL或判断。第二进程进入API和BEGIN尝试后释放第一进程。`verification.json`逐组复核实际 monotonic trace：第二BEGIN尝试 < 第一COMMIT < 第二write_lock_acquired。

五组原trace、结果、最终SQLite状态：`logs/same-intent.json`、`conflicting-intents.json`、`accept-before-fence.json`、`fence-before-old-writer.json`、`mixed-policy.json`。同意图得到相同accepted id1且只有一预约/事件；相冲突意图先accepted后rejected；先接受再fence保留旧决定且epoch3；先fence再旧epoch请求抛WriterFenced且无新意图/预约；policy1新意图抛WriterFenced，当前policy2决定保留。两种fence顺序均有各自独立进程证据。

`logs/lostreply-processes.json`中三个不同worker依次提交后抛ConnectionError、重开query得到accepted、再次重开同参重放原id/event；最终只有一预约和一个pending事件。每个成功worker记录exit0并join；成功补证Python总运行约0.484秒。`process-summary.json`为机器汇总，具体trace为证据真源。

这些是有限、受控顺序，不能外推所有交错；丢回复是fail_at注入，未模拟网络、kill或断电。

## 已有模式拒绝保全

`logs/schema-preservation.json`记录实际创建SQL、异常类型/内容、before/after字节SHA、大小、表SQL和原行；最终保存的SQLite可再读。schema99仅metadata，原行(1,99)，SHA `6be18c9801bc9fef8e15fe5acc8ca232cb691343f8b39523c336b4eb5fc7bae4` 前后同值；foreign仅original，原行preserve，SHA `3c7297bd539a61e2ce93076a45ed81092e93ca2970f41a855d1eb4953073cf16` 前后同值。无新增业务表。首次目录glob写错前缀的[]不作为无journal证明；后续 `observable_traces.py` 只读实际controlled-schema99.sqlite*/controlled-foreign.sqlite*前缀补核，记录各只有本数据库。

## 错误、工具边界与可复建接口

首次双进程harness在第一事务hold后才构造第二Authority；其初始化executescript需要写锁，5秒后真实 `sqlite3.OperationalError: database is locked`，父队列10秒超时。原脚本 `process_checks-first-attempt.py` 与原stderr完整保留，未改业务源；它是初始化调用失败，不是business rejected/fenced或unknown终局。第一次父Python退出时其自有子进程随multiprocessing退出收尾；没有实际进程清单的独立证明，不能声称全系统无进程。

成功补证被 `/usr/bin/time -l` 包裹。Python已生成所有完整结果与子进程exit0记录，但计时wrapper读取sysctl kern.clockrate被沙箱拒绝，所以外层exit1；原stderr保存真实 `time: sysctl kern.clockrate: Operation not permitted`。这是计时器失败，不改写为整个命令exit0；无法提供该次全进程树RSS峰值。observable trace单独记录resource.ru_maxrss，明确只属于该Python，不充当先前任务总RSS。另一次只读ps尝试被PermissionError拒绝，记在verification，不升级为进程清单证据。

成功实际执行的harness原字节在 `process_checks-executed.py`；后续 `process_checks.py` 仅补正确目录glob和try/finally gate释放、join/只terminate自己child的失败清理，AST通过但未重新运行。驱动与结果各自SHA在 `artifact-manifest.json`。原冻结证据包只读。固定接口和补证的每次复建都应先创建自己拥有的新空执行目录，复制本包 `snapshot/` 与所需驱动 `run_fixed.py`、`process_checks.py`、`observable_traces.py`，并在新目录创建 `home/`、`tmp/`、`empty-hooks/`、`git-scratch/`、`state/`、`logs/` 子目录。然后仅在该新目录执行 `python3 -B run_fixed.py`、`python3 -B process_checks.py`、`python3 -B observable_traces.py`；各命令把新日志、SQLite状态与Git子仓库写入新目录，不在原包执行这些命令，也不覆写既有证据。本次未执行历史recipe。

源码/重要结论独核归review174；本执行者没有编辑业务源码。未认证Obsidian显示/同步、真人迁移理解、真实团队/负载/SLO、认证/HTTP、移动真实断网、真实邮件、复制/断电/备份恢复、生产迁移或性能。
