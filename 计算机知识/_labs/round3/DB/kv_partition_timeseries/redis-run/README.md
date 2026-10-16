# Redis单节点真实引擎证据

本包以作者冻结spec.json/cas.lua执行选课权威记录与roster CAS，另做必要的短行为探针；不是新的课程模型。未改作者候选或主库。
原始RESP请求/响应、解析值、客户端身份/序号和monotonic_ns均见evidence/protocol.jsonl；JSON结果见evidence/result.json，服务器启停日志和自有PID退出记录一并保留。所有数据为独占合成fixture。

## 输入与环境

- spec SHA256：`0031d6c4a15d48610ca526cbdf4371074163a8219ac5b178c9da1d780dc791f3`。
- cas.lua SHA256：`2fbf682ab1b4dc2f7aca46e7f51a7409eca521839678da18aadc80269c003bb5`。
- Redis **8.10.2**，Mach-O arm64，malloc=libc，只链接libSystem；redis-version.txt、redis-architecture.txt、redis-linked-libraries.txt为实际输出。
- 官方固定源码：https://download.redis.io/releases/redis-8.10.2.tar.gz ，SHA256 `b9ffee226b5eecdba98a679260dad764b2a4ebd90dce4ad5ac9e9f3eef9c02b3`，与官方redis-hashes一致。官方hash原文快照official-hashes.txt。
- core-only实际构建：`make -j4 build redis CC=/opt/homebrew/opt/llvm/bin/clang CXX=/opt/homebrew/opt/llvm/bin/clang++ MALLOC=libc BUILD_TLS=no OPTIMIZATION=-O2`。此构建完成后才收到本任务后续-j1要求，已向作者说明；后续复建用-j1。build.log和ENVIRONMENT.md如实保留实际过程，不把编译称数值实验。
- 无模块/TLS/全局安装，Python标准库RESP2。仅127.0.0.1:16379、protected-mode yes、maxmemory64MiB/noeviction、io-threads1；save空、appendonly no，配置完整保留。

## 实际执行结果

只把spec actions中的cas/teacher送真实Redis；cache_fill与clock属于教学逻辑钟，未当作Redis服务器时钟执行。每次CAS（包括wrapper拒绝）保存完整authority及roster实际快照；roster排序仅规范集合输出。teacher命令记录在RESP日志。

14个CAS结果：R01/R02 accepted1；R08 accepted2；R09/R10 conflict2；R11 accepted1；R12 accepted2（永久tombstone）；R13 accepted3；R14 accepted3；R15 accepted4（tombstone）；R16 conflict4；R17 accepted5；R18 accepted1；R19由可信wrapper以invalid_payload拒绝，未调用Lua、未创建状态。
key编码严格按作者紧凑UTF8 JSON/base64url规则：同student/term authority和roster共用hash tag。EVAL执行原cas.lua，ARGV为expected、完整nextJSON、course、deleted标志。没有SE82请求去重；重复旧expected返回version_conflict。Lua是可信wrapper之后的教学接口，不是允许任意客户端伪造nextJSON的安全API。

受控小探针结果：
- SET NX第一client返回OK，第二client为RESP null，最终值first。只证明此key创建条件，不冒充关系级唯一性。
- 两持久client都先GET v1，再各自裸SET v2，B覆盖A，最终B；顺序barrier明确，不是压测或随机竞争采样。
- 同样先读v1，原CAS Lua使A accepted2、B version_conflict2，最终A。
- 真服务器cache SET PX50，PTTL序列 `[50,39,26,15,4,-2]`，随后cache nil而authority仍在；authority实测PTTL=-1。
- 对另key先SET PX10000再普通SET，PTTL从10000变-1，普通SET清TTL。
- 故意Lua先SET probe:partial，再对string LPUSH触发WRONGTYPE；前写仍为written-before-error。该运行说明Lua执行错误不自动回滚前写，原子执行不可混同事务回滚。
- 原作者CAS对wrong-string roster在前写前返回invalid_type，authority仍nil。此preflight缩小已知类型错误路径，不承诺OOM/所有未来脚本错误的通用回滚。
- save空/AOFno时正常SHUTDOWN NOSAVE并重启，同dir GET probe:restart与authority均nil。只测正常关闭/启动的这个配置，不声称崩溃/断电/持久策略保证。

两轮自有服务器PID16139/16140均returncode0；结束后16379拒绝连接，见port-closed.json。未连接现有实例、未开外网监听或集群。

## 复跑

新独占目录复制脚本、spec.json、cas.lua、redis.conf；保留旧evidence只读，脚本要求输出evidence目录尚不存在。下载上列固定源码并核hash，core-only构建用-j1。设置REDIS_SERVER为实际binary绝对路径（缺省脚本目录内redis-8.10.2/src/redis-server），确认16379空闲。

实际正式命令：
```
python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- python3 run_redis.py > run.stdout.log 2> run.stderr.log
```
项目runner取得两个全局flock槽之一、线程环境1；本包不复制runner或擅自扩大并发。独立移植时外层调用方须提供相同有界执行/并发约束。脚本只管理自己的进程组，优先正常SHUTDOWN NOSAVE；不会调用全局redis stop。所有输入输出精确保留，不带runtime/数据库/cache。

官方语义入口：
- 构建 https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/install-redis-from-source/
- SET/NX/PX/清TTL https://redis.io/docs/latest/commands/set/
- PTTL https://redis.io/docs/latest/commands/pttl/
- Lua原子执行 https://redis.io/docs/latest/develop/programmability/eval-intro/
- 错误处理 https://redis.io/docs/latest/develop/programmability/lua-api/
- Redis官方无rollback说明 https://redis.io/blog/you-dont-need-transaction-rollbacks-in-redis/

完整主快照应由作者/核查者对照其独立模型；本执行者不把启动成功或自断言PASS称为独立课程论证验收。未运行分片集群、真实故障/断电或生产负载。
