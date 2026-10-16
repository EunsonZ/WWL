# Neo4j 5.26.32：三查询、唯一性与跨语句读取

返回 [图路径实践](../README.md#真实-neo4j-52632-的本机结果) 与 [[计算机知识/55-数据库/10-系统课程/20-图模型路径语义与访问代价#约束与一致性不能由连线代办|第20讲的一致性对照]]。本目录是已有教学图的真实引擎增量证据，不代替旧Python模型/SQLite记录，也没有重跑其1080组独核。

## 固定版本和必要输入

2026-10-16，macOS arm64，Neo4j Community **5.26.32**；HTTP `CALL dbms.components()`返回实际版本/edition。JDK为Temurin **21.0.12.1+1-LTS / aarch64 macOS**，实际 [java-version.txt](java-version.txt)、[java-architecture.txt](java-architecture.txt)保留。Python使用标准库urllib，不使用驱动或云服务。本次使用transactional HTTP API（`/db/neo4j/tx`）；官方[HTTP API说明](https://neo4j.com/docs/http-api/current/query/)标记其自5.26起deprecated并推荐Query API。这里保留实际成功的版本固定接口，未来切换API需另适配与验收，不把旧响应改名为新API证据。实际执行是独立运行者在自己创建的局部实例完成，作者归纳此证据，未再启动引擎。

输入 [original-interface.cypher](original-interface.cypher) 是当时正式接口的逐字副本，SHA256 `54bee174f1e0f3050811ae4e9d35b63e845ecdf2e2f3540a1774a12a3290e238`。其首行UNEXECUTED是运行前输入的历史注释，保留原始字节；现行 [接口文件](../neo4j_5_26_interface.cypher) 也保留这份同版输入的历史注释与SHA，当前已验状态以本README及原始HTTP为准。完整typed图来自原spec：6节点8关系，T1目录，三查询仍按业务关系id比较。

[run_neo4j.py](run_neo4j.py)原样启动自有console进程、HTTP执行五语句与两个约束探针、保存响应，finally只对自己的进程组发SIGTERM并wait，超时才升级；本次两轮returncode实际均0，没有用SIGKILL或模拟恢复。部分机器可能需要调整隔离启动方式，调整后的运行应另留记录。

## 承重断言与失败判据

| 重要断言 | 为什么要实际核 | 记录中的结果／判失败条件 |
| --- | --- | --- |
| 所列Cypher在这个真实版本具有所述路径语义 | 模型正确不能保证语法/引擎结果正确 | [完整HTTP](evidence/http-history.json)的三查询全部node/edge精确对应旧独立真值，trail7/simple3/最短2跳3条；语法错误、errors非空或任一身份不符即失败 |
| 唯一性不等于属性必填 | 若只测重复id失败，会误授予存在性约束 | 重复Entity id:a报ConstraintValidationFailed；无id创建成功并返回null，明确DELETE事务回滚，最终6/8；错拒无id、未拒重复或rollback后计数改变均失败 |
| 显式事务不自动提供跨语句固定快照 | 直接照搬SQLite协议会拼出不存在的链 | [交错HTTP](snapshot-evidence/http-history.json)中同reader tx/2先s1后s3；writer一个commit请求原子删添；后续完整MATCH空。更换reader身份、writer未成功提交、响应错误或观察与记录不符时不能声称复现 |
| 没有把正常启停冒充故障实验 | 启停/端口证据只支持资源生命周期 | 两份shutdown.json记录自有组与returncode0；[port-closed.json](port-closed.json)记录退出后connect_ex=61/no_listener；未测崩溃/断电 |

路径、身份、计数和错误类别容差 **0**；比较全部结果，不仅count。transaction数字/书签/时间戳每次可能变化，复跑须从创建reader响应取得事务URL，检查后续请求复用该URL，不要求永远tx/2。启动耗时只作观察，无吞吐/延迟验收阈值。

三个查询的原始JSON在HTTP-history索引3/4/5；重复id在6，无id创建在7、回滚在8、最终计数/约束在9。这里索引从0计。最终约束实际返回 `fixture_entity_id, UNIQUENESS`，未声称关系id唯一或属性存在性约束。无id字段查询得null，不是把null作为一个普通业务标识存进图。

## 同一个reader，两次读与一次完整查询

[snapshot_probe.py](snapshot_probe.py)的完整请求均保留在 [snapshot-evidence/http-history.json](snapshot-evidence/http-history.json)：先在Scratch标签建sx→sy的s1，reader创建显式tx，首次读得s1；writer在一个 `/tx/commit` 请求中执行删s1、添sy→sz的s3两条语句；同reader tx继续读得s3。之后同reader完整 `MATCH sx-[:SCRATCH_EDGE*1..2]->sz` 返回空，最终回滚reader、清理Scratch。

s1/s3是隔离探针自己的关系名，与正文SQLite的e1/e3对应；没有更改原6节点8关系的typed图。每条响应status、errors、事务commit URL、原始Cypher均可追查。**本次同显式事务跨语句没有固定SQLite WAL式旧快照**。随后完整查询发生在writer提交之后，查询执行期间没有新写者；它返回空不能推广成所有单条Cypher的隔离保证，也没有测书签、复制、锁协议或分片。官方[并发访问说明](https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/)的默认read-committed及不可重复读说明提供背景；current文档不能取代这份5.26.32实际记录。

## 原命令、配置和来源

两轮实际外层命令分别为：

```sh
python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- python3 run_neo4j.py
python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- python3 snapshot_probe.py
```

具体引擎argv/JAVA_HOME/NEO4J_CONF在两份 [command.json](evidence/command.json) 与 [command.json](snapshot-evidence/command.json)。runner只占两个flock槽之一并固定数值线程环境1；**不是JVM单线程保证**。完整 [neo4j.conf](neo4j.conf) 原样保留：HTTP仅127.0.0.1:17471，Bolt/HTTPS禁用，临时回环实例auth/usage-report关闭，heap256–512MiB、pagecache64MiB、ActiveProcessorCount=2；这些配置未认证进程RSS或OS线程硬上限。两轮 [console.log](evidence/console.log)、[console.log](snapshot-evidence/console.log)包含实际绑定与正常退出。启动分别5.681秒、3.477秒，原数值各在startup-seconds.txt；未计下载为查询耗时。

- Neo4j固定包：[Community5.26.32 tar](https://dist.neo4j.org/neo4j-community-5.26.32-unix.tar.gz)，[官方SHA256](https://dist.neo4j.org/neo4j-community-5.26.32-unix.tar.gz.sha256)；SHA256 `d279ae6a9b38034280681a558b0cd222dce89f87cc3d9867f1f7bd28ef5ebc30`，原下载校验文本 [neo4j.sha256](neo4j.sha256)。
- JDK固定包：[Temurin21.0.12.1+1 macOS aarch64 tar](https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz)，SHA256 `3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998`；官方API原返回 [jdk-assets.json](jdk-assets.json)绑定URL、架构和checksum。
- [actual-sha256.txt](actual-sha256.txt)保留两tar和实际输入校验；[官方Java要求](https://neo4j.com/docs/operations-manual/current/installation/requirements/)供换平台时再核，本次没有使用本机既有JDK26/11代替21。

本目录不包含二进制runtime、data、database、事务日志或缓存；也不复制HTTP已有内容的拆分响应、打印summary与另一份过程报告。

## 隔离复建与离线检查

无需引擎即可核已有证据。在本目录执行：

```sh
python3 -B verify_recorded.py
```

[verify_recorded.py](verify_recorded.py)只读本目录HTTP、当前父lab的actual.json、退出/校验文本，不import旧求值器或启动服务。它核全部三查询身份、版本、约束/回滚/最终计数、同reader URL及交错响应；是作者整理检查，独立核查另直接读原始记录。不要使用Python `-O`，它会移除断言。作者本轮实际执行exit0/PASS；旧模型与SQLite未重跑。

要真实复跑，先创建**新的独占空目录**，复制本目录文件而不带旧evidence/snapshot-evidence输出（本仓保留的证据不覆盖）；下载并校验上列固定tar，再局部解包为 `neo4j-community-5.26.32/`、`jdk-21.0.12.1+1/`，把neo4j.conf复制到前者conf/。无需brew、系统JDK安装或云服务；也不要把脚本指向已有数据库。脚本以自身所在目录定位runtime/输出，故无需复用原/private/tmp路径。

确认17471没有活动监听，先在该新目录通过runner运行run_neo4j.py（首次必须全新空data），成功并确认自有服务退出后，再运行snapshot_probe.py。失败时保留HTTP/console，先查原错误，不接着将未完成结果当通过；只终止自己启动的进程组。脚本会写结果、导入数据与清理自己的Scratch，**不会自动证明目录是空的**，新空目录是运行前提。

首次第二轮预查曾被TIME_WAIT触发bare bind `Address already in use`，当时未启动第二服务；snapshot_probe.py对预查socket加SO_REUSEADDR后才成功，仍会拒绝活动监听。不要为绕过端口冲突调用全局neo4j stop或杀别人的进程。若修改端口，要同步本地配置、脚本URL及校验前提，并另记录新运行，不能把原17471证据改名充数。

剩余接口见父README：其他Neo4j语义变式/计划/性能、语句执行中更新、复制/failover/网络断开、生产压力和真实用户均未验。#171键值/宽列时序余项不由此关闭。
