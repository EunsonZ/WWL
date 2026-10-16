# 图路径语义：从完整答案到访问与快照边界

对应 [[计算机知识/55-数据库/10-系统课程/20-图模型路径语义与访问代价|第20讲]]。读者要能在同一先修目录上分别回答可达、全部最少边数路径及长度界内 walk/trail/simple，改变平行边、标签、关系类型与目录版本后重新求解；并说明索引、唯一性与一致观察各保障什么。

实际计算只用 **Python 3.11+ 标准库**（异常 `sqlite_errorname` 需3.11+）；本次 Python **3.14.7**、SQLite **3.53.4**。`graph_model.py` 是有限本地属性图模型，不是 Redis、Neo4j 或生产数据库。`sqlite_probe.py` 实际执行SQLite表约束、访问计划与两个连接的受控交错。后续在本机独立Neo4j Community **5.26.32**／Temurin21实例完成三查询、唯一性与跨语句读取增量；[原始HTTP和隔离复建](neo4j-run/README.md)与这两个旧运行层分开记录，未验项见下文。

## 固定输入和答案身份

[spec.json](spec.json) 的 `input_version=graph-paths-v1`：6节点（5 Course、1 Teacher）、8条有身份有方向的关系、5个按edge_ids选边的变式。`core/parallel/branching/typed/without_e3` 的边数分别3/4/6/8/7。27条查询各自显式指定 source/target/out/type/node_label/min_hops/max_hops/rule，共135组完整输出。`limits` 记录教学范围；实际程序硬限制20节点、12关系、5跳，不是可通过编辑limits取消的资源参数。

[actual.json](actual.json) 保留每组 `bounded.paths` 的 node_ids/edge_ids、数量、有界最短长度与全部同最短集合；另给 `unbounded_bfs` 的可达/距离/全部最短，以及全扫/邻接的扩展前缀数与边记录检查数。路径按长度、edge_ids、node_ids排序，平行边身份不折叠。bounded严格遵守min/max及rule；unbounded忽略这三个字段，在同一类型/标签子图上含零长度最短。目标中途命中仍继续扩展，直至长度界。查询端点不存在则拒绝整个输入；端点存在但不属查询标签则无路径。输出是有限文件，不提供分页或部分成功合同。

全部边catalog=T1，本次JSON教学查询未提供catalog谓词参数；规范Cypher接口显式过滤T1。本固定输入上两者对应，修改目录属性后不能继续拿同一个JSON查询冒称已经实现目录过滤。输入不是通用Cypher或属性表达式解析器。TEACHES端点标签约束没有实现，e7刻意是可存储但业务可疑的干扰边。

## 为什么这组实验重要

| 承重断言 | 为什么必须验 | 实际验收内容与失败信号 |
| --- | --- | --- |
| 路径不是节点集合；先定重复规则 | 全局visited或终点DISTINCT可能静默漏链 | 135组逐项完整node/edge序列、最短同长集合、零长度、反方向与不可达；任一字段不等即失败 |
| 索引不改变答案，只改变指定访问工作 | 省略候选不能冒充优化；计数不能冒充速度 | 同枚举顺序scan/adj答案exact，前缀数及边检查数由raw边积独立重算；不比较时延 |
| 结构约束真的拒绝坏写入 | Python提前检查不能证明引擎约束生效 | SQLite真实5失败原因/0行变化、平行边保留、失败事务transient整条撤销；错误未抛或状态变化即失败 |
| 两跳读取可能拼出不存在的链 | 每次读合法不保证组合来自同一版本 | 两实际连接WAL交错，V0仅e1/V1仅e3均不可达，未绑定两读拼假链；固定读事务在写者commit后仍e1，新事务e3 |
| oracle不是换个名字调用实现 | 同一bug不能充当自己的答案 | `batch_oracle.py` 不import model，枚举原始edge product后过滤；测试故意篡改一条BFS距离应被拒绝 |

所有路径/身份/整数计数预期 **exact，容差0**。SQLite错误名称按所执行约束类别核，完整原消息保留但不作跨版本文字合同；EXPLAIN节点id、估计数字与排列文字也不固定，只核实际使用/未使用目标复合索引及同结果。浮点elapsed只记本次过程耗时，不设性能通过阈值，不比较解释器速度。

[batch_oracle.py](batch_oracle.py) 从原始边取笛卡尔积，后验检查连接、标签/类型及重复性；全局最短另枚举至Course数−1的simple候选，不调用求值器/BFS。可达最短的cycle-removal前提是每条边cost=1。它为作者自测，不能代非作者独立核查。

## 实际命令和原始记录

源码：[graph_model.py](graph_model.py)、[batch_oracle.py](batch_oracle.py)、[sqlite_probe.py](sqlite_probe.py)、[test_graph.py](test_graph.py)。三个承重程序在正文有逐字 `code-sync` 镜像，改真源时同步镜像。图源 [render_figures.py](render_figures.py) 只读同版spec/actual生成 [paths.svg](paths.svg)，含title/desc；[paths.png](paths.png) 是实际渲染目视用的同图。

[run-result.json](run-result.json) 留实际解释器/线程环境/每条命令/cwd/退出码/耗时/原stdout与stderr。正式运行通过本机 `/private/tmp/wwl-next-context/run_local.py --timeout 300 -- python3 ...`，自动占两个全局槽之一、五项线程环境均1；四子命令顺序运行，主组0.592秒（显示四舍五入）、均exit0，7行为测试0.326秒/OK。无外部服务、集群、GPU、网络查询或编译安装参与计算。首次规范输出即通过；后续显示调整只重生成SVG/PNG，不声称重新跑数值组。

实际五变式 a→c、1..5 的 walk/trail/simple：`2/1/1、6/4/2、9/7/3、9/7/3、3/3/1`；typed全局最短2跳/3条。typed访问计数walk200→36、trail136→20、simple56→8，只是明确的边记录检查单位，已建邻接访问不含构建/维护与路径复制/排序成本。

[sqlite-result.json](sqlite-result.json) 留真实SQLite版本、journal_mode=wal、synchronous=FULL、5次失败、完整状态计数、索引前后原计划与双连接原观察。探测库是候选区独有fresh文件，不是正文资源；复建时新建，勿把自己的现有数据库交给程序。该脚本会在自有库删边建立快照反例，结束关闭所有连接。

## 在一个新目录复建

从本README所在目录运行。下面使用新空输出目录，数据库已存在会被脚本拒绝；结果文件请留在自己的输出目录，保留本包原结果。

```sh
OUT=$(mktemp -d /private/tmp/graph-path-rebuild.XXXXXX)
python3 -B graph_model.py --spec spec.json --out "$OUT/actual.json"
python3 -B batch_oracle.py --spec spec.json --actual "$OUT/actual.json" --out "$OUT/oracle-result.json"
python3 -B sqlite_probe.py --spec spec.json --db "$OUT/graph.sqlite" --out "$OUT/sqlite-result.json"
python3 -B test_graph.py
python3 -B render_figures.py --spec spec.json --actual "$OUT/actual.json" --out "$OUT/paths.svg"
```

每条命令成功后再执行下一条。若在协作宿主正式运行，将每条计算命令置于现有runner后，不要新建第三个并发槽；脱离该宿主时按自己的资源安排运行，runner不是课程源码依赖。`-B`避免生成pyc。

SVG生成只用标准库；PNG只为显示核查，实际复用了此前候选隔离环境中的 `resvg-py==0.5.0` 与系统PingFang SC，没有改系统包。需要复建PNG时可在自有venv隔离安装同版，然后：

```python
from pathlib import Path
import resvg_py
p=Path("paths.svg")
p.with_suffix(".png").write_bytes(resvg_py.svg_to_bytes(
    svg_path=str(p), sans_serif_family="PingFang SC", width=1600))
```

字体/渲染器改变可能改变PNG字节，不改变路径数量；先核SVG数据，再实际查看是否遮字/裁切。作者已实际查看本包PNG。未在Obsidian内打开或点击，本机渲染不代UI/真人理解。

## 改变条件，应该观察什么

- 把parallel中e4移除：完整edge身份和计数回到core，最短节点序列看似一样但最短条数从2变1。
- 将b标签改成Teacher：经b的REQUIRES链全部不合格；branching仍由e5/e6到c。不能只检查端点标签。该变式已有行为测试，非作者还独立测了不同边界。
- 只将L改为1：bounded为空，unbounded仍最短2；将source=target且min=max=0：空边路径一条。
- 给目标增加回返关系：输出第一次命中后仍继续；trail/simple按各自本前缀限制，不用一个全局visited替代。
- 把错误类型改为有效类型，或给边添加费用：前者改变子图与最短候选，后者需定义新目标并改算法，当前BFS不实现加权路径。

这些是输入变化与预期，不是只改结果JSON。测试包含CLI实际退出、错误输入拒绝和oracle错误检测。

## 真实 Neo4j 5.26.32 的本机结果

2026-10-16，macOS arm64的全新Community **5.26.32** 实例，Temurin **21.0.12.1+1-LTS**，Python标准库通过回环HTTP执行原 [neo4j_5_26_interface.cypher](neo4j_5_26_interface.cypher) 的五条语句：唯一约束、完整typed建图、trail/simple/全部最短三查询。实际7/3/3条，最短2跳；完整node/edge序列与原独立真值精确对应，没有只比数量。传统5.26语法已实际运行，没有使用Cypher25新关键词。

对 `Entity.id IS UNIQUE`，重复id:a实际拒绝；无id的Entity在显式事务内创建成功，`n.id`返回null，再ROLLBACK，最终6节点8关系。这是缺属性被允许的观察，不是存了一个普通null业务id，也不增加属性存在性、关系id或先修无环约束。

同一个显式reader事务先读s1，writer另一个提交事务原子删s1添s3，reader第二条语句再读到s3。随后同reader执行完整路径MATCH返回空。完整原请求/响应与同一transaction URL保留；**本次Neo4j显式事务不提供SQLite WAL实验中的固定跨语句快照**。完整MATCH在writer提交后执行、期间无并发写；这次空集不能外推所有单条Cypher的隔离性质。

[neo4j-run/README.md](neo4j-run/README.md)保留重要性、断言、失败判据、版本/来源、完整配置与隔离复建。两轮服务均由各自脚本启动和正常关闭；只监听127.0.0.1:17471，Bolt/HTTPS关闭，结束端口关闭。数值runner线程环境1不表示JVM只有一个线程：本次JVM另声明ActiveProcessorCount=2、heap256–512MiB/pagecache64MiB；未认证严格CPU/RSS或OS线程上限。没有启动生产实例、外部集群或故障测试。

旧模型135查询/独核1080组、SQLite与图显示结果按原同版复用，未重跑。增量的原始执行来自独立运行者；本轮仅把必要证据归入此lab，并实际运行离线 [verify_recorded.py](neo4j-run/verify_recorded.py) 对完整三查询、版本/约束/同reader身份和清理记录核对，不重新启动Neo4j。

## 真实图引擎的未验接口

三固定查询与上述两个有限探针已经实跑；Neo4j实际只执行原typed输入的 `*1..5` 三条查询；尚未执行最大长度改为1等其他长度界变式、错误中间标签、反方向、相同端点、重复关系walk或加权路径。脚本中的collect展示先过滤后取min，没有做大图优化认证；没有EXPLAIN/PROFILE或索引前后延迟/DB hits测量。

后续真实验收仍应按固定server/driver/edition版本、查询文本、原始结果和具体计划核：起点id索引、出入边方向、高出度热点、构建与写维护、结果体积和延迟分位。模型36对200的逻辑边检查不能贴进Neo4j吞吐栏。其他跨语句事务协议、同一语句执行期间更新、书签/因果、复制/failover/网络断开、跨分片与生产压力全部未验。未来若另做故障测试，只操作自己创建的临时进程/数据库，记录确认与恢复边界；本次两轮正常启停不充当崩溃恢复证据。

## 依据和下一问题

[Neo4j关系唯一性](https://neo4j.com/docs/cypher-manual/5/patterns/unique-relationship-paths/)、[变长路径与过滤](https://neo4j.com/docs/cypher-manual/5/patterns/variable-length-paths/)、[索引与计划](https://neo4j.com/docs/cypher-manual/5/indexes/performance-indexes/using-indexes/)、[唯一性/存在性约束](https://neo4j.com/docs/cypher-manual/current/schema/constraints/create-constraints/)在2026-10-16实际查读；链接可能展示后续语法，传统5.26接口已按上述固定范围在5.26.32实跑。[SQLite外键](https://www.sqlite.org/foreignkeys.html)和[EXPLAIN](https://www.sqlite.org/eqp.html)支持本地探测口径。

返回第20讲迁移题和第08讲模型选择。#171的键值协议/键设计、宽列/时序完整访问单元仍未由本包兑现；已交第13讲文档查询和#172事实/窗口/恢复/分析模型不重跑或重建，不因图代表章通过就关闭整课。
