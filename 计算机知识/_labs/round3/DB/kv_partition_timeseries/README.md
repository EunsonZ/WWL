# 键值协议与分区时序：同一选课数据的两种访问

主解释 [[计算机知识/55-数据库/10-系统课程/21-键值条件更新与分区时序查询|第21讲]]。实验要检验：键是否完整表达身份；条件版本/墓碑与派生roster是否一致；缓存到期有没有误删权威；时间范围、并列游标、迟到与桶/片变化是否保持声明的答案。课程13的Mongo查询和20的图/Neo4j已交成果直接复用，本包不重跑它们。

## 输入、合同和实际层次

[spec.json](spec.json)版本 **kv-partition-v1**，20动作、5时间查询、3布局。单位为非负整数毫秒，自UTC epoch起；D=86400000，桶按整数除法，逻辑clock_ms只表示处理时钟，不是event_ms。request_id在固定输入内唯一，是命令标签/审计点id，**不承诺持久业务意图去重**；真实unknown/同意图恢复引用SE82，不重写它的合同。

CAS前提：三元键(student,term,course)，初始version0；payload为null（登记墓碑）或恰含teacher_id/grade/phone_at_enrollment三个非空字符串。拒绝顺序是payload、expected精确非负整数（bool拒）、event_ms精确非负整数、版本匹配；成功恰增1。删除仍保留版本，无TTL；即便原来不存在，expected0加null也能登记version1墓碑。未知teacher没有外键校验，投影current_phone为null，不能说库已验证引用。固定数据只引用T7。

模型cache_fill表示普通SET新投影，可选TTL；每步先按当前逻辑钟清理 `clock>=deadline` 的缓存，ttl=None覆写清TTL。没有模型NX/KEEPTTL选项；NX是另一个真实Redis探针。缓存只影响命中结果，不影响权威/墓碑。roster集合由有效选课维护；课表投影为顺序模型结果，不承诺多次GET的并发快照。

接受的10变更点作为审计，拒绝请求不占审计行。布局默认按(student,UTCday)分区、(event_ms,event_id)聚簇；另半日桶和日桶两片CRC32(id)%2。该CRC32不是Redis slot或Cassandra partitioner。每个固定前缀内全序keyset分页；不保证跨前缀迟到无遗漏，也不自动实现源到审计的跨资源事务。

| 实际层 | 这次做了什么 | 不能由此推什么 |
| --- | --- | --- |
| 本地Python3.14.7，标准库模型 | 20prefix全权威/墓碑/roster/teacher/逻辑缓存/审计，3布局×5查询完整分页 | Redis时间/内核吞吐、Cassandra存储/复制 |
| 作者独立批量oracle，SQLite3.53.4 | 每prefix从原始历史重建，再用新内存SQL全量filter/order与独立切页，300布局查询exact | SQLite是宽列引擎、一般副本一致性 |
| 真实Redis8.10.2，macOS arm64 | 14CAS完整快照（13次Lua，R19包装器拒），NX/两客户端屏障/真实TTL/错误/正常重启 | 审计同时持久提交、任意不可信payload、集群/故障/持久策略 |
| Cassandra5.0风格接口 | [cassandra_interface.cql](cassandra_interface.cql)代表表、日桶范围和tuple后续查询按官方规则核 | 本次没有启动Cassandra；不把可本机执行但未做称为外部不可验 |

计算要求Python **3.11+**，不需第三方包。主模型输入最多100动作、10查询、20条/页，范围≤100天；布局最多4种、片数1..4；每query/page预检探测分区≤1000，并以动作数×查询/布局×最坏页数估计总探测≤1000000（最坏页数由CAS总数/page_size上取整，至少1）。越限在处理动作/创建输出文件前抛partition_probe_limit或total_probe_limit，不允许用毫秒桶展开亿级空分区，也不允许多前缀/多页放大绕过单页限额；只服务此有限教学合同，不是生产存储API。JSON文件全部保留内容与身份，不是仅终局sum/count。不要开Python `-O`，它会删除断言。

## 高重要性断言、理由与结果

| 断言 | 为何承重 | 精确检查／失败条件 |
| --- | --- | --- |
| 键编码不把不同字段组合合并 | 错键会将两个业务身份写成一个 | 原始冒号碰撞两组相同，JSON/base64url不同；每个实际Rediskey与模型对应 |
| 版本/墓碑/roster保持 | 丢版本或漏索引可悄悄复活/漏课 | 每prefix裁决、完整值、版本、deleted、roster与审计身份exact；R09/10/16拒绝无状态变化，R19不登记 |
| TTL只清缓存，普通SET会清TTL | 以缓存政策回收权威会破坏版本合同 | 逻辑deadline恰等时miss；真实PX50最终PTTL=-2、authority=-1且有值；普通SET后PTTL=-1 |
| 不交错不是失败回滚 | 把Lua错误当全撤销会留下脏派生状态 | 原始WRONGTYPE响应后前SET仍在；预检已知类型错误时authority仍nil，不扩为所有错误保证 |
| 范围/全序分页保持点集合 | 同毫秒只用时间会漏/重，漏桶/片也会漏 | 全部5查询×3布局×20prefix的每页rows/id/cursor与两项cost exact；同毫秒R12/R13、迟到R14独立保留 |
| 桶/片成本不等于速度 | 只数结果或片数会虚报扩展能力 | 实际daily首3/7、half-day5/8、两片6/8；max均4，明确计数边界，不作时延阈值 |
| 极短桶/多前缀多页不能放大成无界探测 | 合法参数也可能枚举亿级空分区，影响本机可运行性 | 单页≤1000、全组保守≤1000000；固定输出逐字不变，1ms桶与100CAS多页总预算超限真实CLI均拒绝且无输出文件，见[原记录](probe-limit-result.json) |
| 没持久化的正常重启确实丢值 | 无TTL不授予持久性 | save空/AOFno，SHUTDOWN NOSAVE后同目录重启GET nil；没有故障/断电推论 |

整数/集合/完整JSON/身份/裁决/分页游标/逻辑成本容差 **0**。真实TTL中间PTTL随调度变化，不能要求逐毫秒复现；失败是有限等待内未观察过期、authority也消失、或无TTL状态不符。原实际序列保留，未把50ms当尾延迟测量。编译与启动时间只作过程事实，没有性能验收阈值。

宽列/CQL接口的结构与范围语义核查为**高重要性**，已按官方DDL/DML及独立有限模型完成；Cassandra实际计划、内部墓碑/compaction、故障与性能为后续**中重要性实现验证**，本次未做。接口具体期望：日1 `[D,D+1)` 返回R12/R13，严格tuple游标(D,R12)后LIMIT2返回R13/R15；不是通用CQL编译器或真实服务测试。

## 原始运行与独立对照

[run-result.json](run-result.json)留主模型/oracle命令、解释器、线程环境、退出码和原stdout/stderr；正式都在本机已有run_local.py双槽之一、单数值线程环境中顺序运行，常规超时120秒，本组实际远小于1秒。结果 [actual.json](actual.json)、[oracle-result.json](oracle-result.json)。规范真源 [kv_model.py](kv_model.py)、[batch_oracle.py](batch_oracle.py)、[cas.lua](cas.lua)在正文有3个逐字mirror。

[batch_oracle.py](batch_oracle.py)不import模型，逐prefix从raw历史重建，cache另从最近fill时的完整历史投影，查询使用新SQLite全量范围/排序及独立切页。它是作者自测，不代非作者独核。另一个非作者已用全历史合法版本后继、纯Python全量filter-sort路线检查固定与8变式共137prefix，未调用作者SQL或模型作答案。

[test_kv.py](test_kv.py)有6项模型行为测试：键碰撞/tag、墓碑/冲突、TTL边界与清TTL、半开/并列/晚到/布局同答案、缺字段/精确类型拒绝，以及oracle拒绝同count的内容篡改。首次6项虽exit0但发现SQLite连接ResourceWarning（`with connection`只管事务不关闭）；oracle改contextlib.closing后重跑6项exit0/无warning，初始和修正后原输出均保留在run-result，不改旧结果数值。随后核查发现极短桶探测放大，已加单页/全组预算，只复跑固定CLI逐字与两超限CLI拒绝delta，原始[probe-limit-result.json](probe-limit-result.json)保留；没有为资源预检重复成熟137prefix/Redis运行。

[Redis原始证据README](redis-run/README.md)与 [RESP记录](redis-run/evidence/protocol.jsonl)、[完整结果](redis-run/evidence/result.json)保存198条请求/响应原始base64、解码值、客户端序号与时间，以及启动配置/进程退出。每次实际14CAS的完整authority/roster已对模型逐字段相等；非作者又直接解码原始RESP并对自己的独立真值核准。[verify_redis.py](verify_redis.py)只读保存JSON作14快照复核，未启动Redis。主组实际teacher SET保留于RESP；课表投影、逻辑cache与时序表未写进真实Redis实验，不能将它们整体算作Redis已跑范围。

Redis运行者使用固定 [官方源码8.10.2](https://download.redis.io/releases/redis-8.10.2.tar.gz)，SHA与官方redis-hashes核对；实际INFO的dirty=1、arm64编译版本及binary SHA保留，**不是官方预编译binary**。实际构建-j4在纠正-j1要求到达前已结束，build.log/ENVIRONMENT如实记录，后续复建用-j1；不把它称为单线程构建，不重编造一份历史。数值正式运行经双槽runner/线程环境1，Redis io-threads1且无集群；这仍不是进程全部后台线程硬上限。

## 改输入前先预测

最终S1全范围九条顺序 `R01,R14,R08,R02,R12,R13,R15,R17,R18`。日桶首分页size2 probes/candidates=3/7；半日5/8；两片6/8，三者最大分区4。本机查询成本只记探测和拷入候选行，二分键比较、排序/合并、布局构建与写维护另计；不要除这两个数得“倍速”。

- 把R14的业务时点从50改100：它与R08并列，用id全序决定位置；`[50,100)`将不再含它。
- 修改日长/片数：完整答案应相同，分区/探测/候选与热点大小可变。换成3片/更短桶也不保证负载均衡；超过单页1000或全组保守1000000探测预算时应明确失败，不能靠超时冒充完成。
- 删除后发送expected0：墓碑还在时冲突；若把墓碑也丢掉，该前提不再成立，不能继续引用原证明。
- 把cache_fill TTL改为None：它不再自动到期，后续权威更新不会自动刷新缓存。
- 在prefix13与14之间分页：第一页面R01/R08的cursor100会越过后插R14@50；固定prefix正确与跨prefix无漏是两个合同。

[partition-order.svg](partition-order.svg)由 [render_figures.py](render_figures.py)读actual生成，有title/desc；[partition-order.png](partition-order.png)是同SVG用隔离resvg-py0.5.0/PingFang SC实际渲染，作者已目视。表头已独立定位对齐数值；横向仅顺序，不按时间比例。生成图不需第三方，PNG复看不参与计算。Obsidian客户端/实际点击与真人理解未验。

## 新目录复建模型

从此README所在目录逐条运行；上一条成功再继续，保留本包原结果：

```sh
KV_OUT=$(mktemp -d /private/tmp/kv-partition-rebuild.XXXXXX)
python3 -B kv_model.py --spec spec.json --out "$KV_OUT/actual.json"
python3 -B batch_oracle.py --spec spec.json --actual "$KV_OUT/actual.json" --out "$KV_OUT/oracle-result.json"
python3 -B test_kv.py
python3 -B verify_redis.py
python3 -B render_figures.py --actual "$KV_OUT/actual.json" --out "$KV_OUT/partition-order.svg"
```

协作宿主正式计算放在现有 `/private/tmp/wwl-next-context/run_local.py --timeout 120 -- <实际Python> ...` 后；其他宿主可采用自己的有界运行器，这个runner不是课程依赖。图PNG若需复建，在自己隔离venv装resvg-py0.5.0，调用svg_to_bytes(svg_path=...,sans_serif_family='PingFang SC',width=1600)，字体变更可能改变像素字节，先核SVG数据再看显示。

真实Redis复跑先读redis-run/README，在新的独占目录用固定源码、spec/Lua/config和REDIS_SERVER绝对路径执行run_redis.py；原evidence保留，脚本拒绝复用已存在evidence目录。默认仅127.0.0.1:16379，save空/AOFno，正常停起会丢本例值；只管理自己启动的实例，不接现有生产服务。下载/编译与运行分开留证，无需系统安装、云或GUI。原始spec/Lua副本是实际执行输入，修改主真源后不得把它们悄悄换字节仍称旧实跑。

## 实际未做的接口

Cassandra接口只代表日桶无片布局。在自己新建的keyspace导入10个accepted审计点，再执行固定CQL两查询，记录server版本/完整rows、半开和并列cursor变式，核与模型对应；跨日由应用枚举/合并。当前能本机执行但未启动Cassandra，不能声称已验其LWW、TTL/tombstone/compaction、轻量事务或副本一致性。特别是本课业务deleted墓碑/版本保留，不是Cassandra内部删除墓碑的gc_grace/repair合同。

Redis实际只无持久单节点；若未来启用RDB/AOF，需明确fsync/重启/确认/恢复输入及故障点，重新检查结果丢失边界。集群跨slot拒绝与hash tag、eviction、真正网络未知结果、replica/failover及生产压力均未做；不可把“本机可做但未做”统称外部接口，也不把一次正常重启当故障恢复。本课意图去重/跨资源恢复只引用SE82与18既有合同，不改它们实现。

## 来源与下一步

2026-10-17实际查读：[Redis SET](https://redis.io/docs/latest/commands/set/)、[PTTL](https://redis.io/docs/latest/commands/pttl/)、[Lua原子执行](https://redis.io/docs/latest/develop/programmability/eval-intro/)、[事务错误规则](https://redis.io/docs/latest/develop/using-commands/transactions/)、[Cluster hash tag](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/)；当前文档可能有更新命令，本课实际只用NX/PX/传统Lua，不以8.4新增IFEQ替换原脚本。[Cassandra5.0逻辑模型](https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/data-modeling_logical.html)、[DDL](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/ddl.html)、[DML](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html)支持所列结构与查询条件，未用文档替运行。

回第21讲五题与第08讲模型迁移，结合13文档和20图课按原#171范围判断能力；本包兑现有限键值和分区时序，不宣称所有NoSQL产品、生产故障或真人学习均已认证。
