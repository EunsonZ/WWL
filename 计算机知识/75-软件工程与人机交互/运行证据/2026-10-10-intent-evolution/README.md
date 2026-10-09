# 预约 v2 与 Git 演进：有限执行及复现

本目录保存本版教学模型的实际输入和输出。主解释是 [版本协作与行为保持演进](../../07-版本协作与行为保持演进.md) 与 [v2意图恢复与演进实验](../../82-v2意图恢复与演进实验.md)；规范业务代码为 [reservation_v2.py](../../reservation_v2.py) 和 [git_evolution_lab.py](../../git_evolution_lab.py)，测试、例外与迁移合同在两页说明。

[独立执行原报告](execution-report.md)、[固定命令/环境](fixed-runs.json)、[源码清单](source-manifest.json)、[完整输入快照](snapshot/计算机知识/75-软件工程与人机交互/reservation_v2.py) 与 [运行后源身份](source-recheck.json) 固定真正执行时版本：Python 3.14.7、SQLite 3.53.4、Git 2.55.0、macOS 27.0.1 arm64。12份输入含六Python和六文档；当时82正文是 `2f0ea025...`，随后构造锁边界说明改为 `75e0c0bf...`，六Python和四镜像字节未变。快照80引用的旧原型HTML另从当前正式库复制以兑现该历史文档相对链接；它不属于12份实跑输入，没有运行HTML或客户端。正式正文接入此回执是阅读入口修订，不冒充代码重跑或改签旧快照。

固定执行得到22项单测OK、默认演示exit 0、真实新建Git实验exit 0；[单测stderr](logs/unittest.stderr) 是正常测试报告，[默认JSON](logs/default-demo.stdout) 与 [Git命令和结果](git-exercise-result.json) 保留原字节。Git JSON包含双亲提交、DAG、每条命令、1021语义错误修复前后值及BUFFER文本冲突/解决；原临时仓库不随本批发布，没有外部remote。原始Git输出还在 [git-lab.stdout](logs/git-lab.stdout)，不以模拟图代替实际合并。

[完整v1/v2可观察trace](observable-traces.json) 逐步记录返回/异常、前后状态、id、取消和错误缓冲变体；[五组受控双进程与丢回复汇总](process-summary.json) 和 [独立核对](verification.json) 连接同意图重放、相冲突决定、接受后fence、fence后旧写者、混合policy，以及三个进程重开同结果。每组SQL与monotonic事件见 `logs/` 对应JSON：第二BEGIN尝试早于第一COMMIT，第一COMMIT早于第二获得写锁。wrapper在原事务已经取得锁后设门，不替换业务SQL或判定；五组指定顺序不证明所有交错。

模式拒绝的 [SQL/表/原行/前后哈希](logs/schema-preservation.json) 和两个原数据库 [schema99](state/controlled-schema99.sqlite) / [foreign](state/controlled-foreign.sqlite) 保留：各8192byte，前后SHA相同，无新业务表。其他预约状态的完整记录在trace JSON中；临时运行树、其嵌套Git对象和环境链接不作为公开复现依赖。

首次harness在第二Authority构造前已持有写锁，真实5秒后抛初始化 `OperationalError`；[首失败stderr](logs/first-attempt-process-checks.stderr) 与 [首驱动](process_checks-first-attempt.py) 原样保留。这发生业务API之前，没有登记本次新决定，不映射为rejected或WriterFenced。成功harness先等两个构造ready，再控制业务事务；实际执行源是 [process_checks-executed.py](process_checks-executed.py)。

成功补证外层 `/usr/bin/time -l` 读取 `sysctl kern.clockrate` 被拒，外层exit 1；[原stderr](logs/process-checks.stderr) 保留工具边界。Python输出和各worker exit 0已独核，不改写外层为exit 0。后续 [process_checks.py](process_checks.py) 仅补目录glob与失败清理，静态审过但未重跑；它与实际执行源的身份分开。单独observable脚本的31,031,296byte RSS不代表整次进程树峰值或硬上限，环境线程变量不等于OS实测线程数。

复建使用已有Python 3.10+、Git 2.28+和标准库SQLite，不安装依赖。**必须使用自己拥有的新空目录**，复制快照和驱动，创建工作子目录；不要在本证据目录执行采集器，以免覆盖原日志/JSON/数据库。下面从库根创建一个唯一的新临时目录；驱动按自身目录解析快照，不依赖目录深度：

```bash
software_run=$(mktemp -d /tmp/wwl-intent-evolution.XXXXXX) &&
cp -R 计算机知识/75-软件工程与人机交互/运行证据/2026-10-10-intent-evolution/snapshot "$software_run/" &&
cp 计算机知识/75-软件工程与人机交互/运行证据/2026-10-10-intent-evolution/run_fixed.py "$software_run/" &&
cp 计算机知识/75-软件工程与人机交互/运行证据/2026-10-10-intent-evolution/process_checks.py "$software_run/" &&
cp 计算机知识/75-软件工程与人机交互/运行证据/2026-10-10-intent-evolution/observable_traces.py "$software_run/" &&
cd "$software_run" &&
mkdir home tmp empty-hooks git-scratch state logs &&
python3 -B run_fixed.py &&
python3 -B process_checks.py &&
python3 -B observable_traces.py
```

驱动只依赖同目录 `snapshot/` 的冻结源码；Git实验只新建自己的子仓库、禁外部配置/签名/hooks，无push。上述接口会产生新的本地SQLite、日志和Git实验对象；公开证据中的原绝对目录是运行来源，不是复建要求。源码、原驱动及输出的文件哈希见 [原artifact清单](artifact-manifest.json)，该清单属于当时原包；本批具体复制映射另保存于 [delivery-copy-map.json](delivery-copy-map.json)。

本轮确认有限业务规则、单机事务故障、重开持久结果、指定并发顺序和真实临时Git操作。回复丢失由fail_at注入，未模拟网络kill或断电；没有认证线上HTTP/身份协商、移动真实断网、真实通知、复制/备份恢复、生产迁移/性能、Obsidian显示、真人迁移理解或团队/SLO达标。
