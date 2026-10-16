# 分析建模实验：同一事实、历史维度、CDC与行列批计算

先读 [[计算机知识/55-数据库/10-系统课程/19-分析模型维度历史与变更捕获|第19讲]] 的预测题。这里实际运行新SQLite源触发器、一次单位/schema迁移、当前事实消费、SCD as-of归属、星型SQL和同一整数工作负载的行/列/批计算；不把Python计数当真实列式引擎加速。

计算代码需要Python3.10+标准库，以及SQLite的JSON函数（触发器使用json_object）。本次实际Python3.14.7、SQLite3.53.4、macOS27.0.1 arm64。没有运行Debezium、Kafka、远端CDC、DuckDB/X100、邮件或支付；本课只读既有SE82合同，未修改它。计算不需第三方Python包；PNG渲染单列在后文。

## 固定输入、真源与实际输出

| 文件 | 对象与证据 |
| --- | --- |
| [spec.json](spec.json) | 唯一固定输入：17项source_operations（15业务变更、1迁移、1回滚探针）、4份维度snapshot、30项delivery_plan、复制/查询/批大小参数 |
| [capture_source.py](capture_source.py) | 在新SQLite库创建权威版本表、facts及AFTER触发器；源事务内一起写changes，迁移把minutes乘60变成duration_seconds |
| [capture/capture-observed.json](capture/capture-observed.json) | 实际源操作提交/回滚trace、15条捕获before/after、最终源行/版本表与integrity=ok |
| [capture/captured_changes.json](capture/captured_changes.json)、[delivery_log.json](capture/delivery_log.json) | 前者为真实触发器捕获；后者按明确plan加重放、旧版、schema/身份压力与模拟传输tombstone，不能混称真实连接器输出 |
| [analytics_runner.py](analytics_runner.py)、[actual.json](actual.json) | 已知schema解码成秒单位；30个完整前缀：业务事实/墓碑、seen原payload、claims规范内容、quarantine原因/原事件、as-of候选sk与桶；并给4维度revision重算 |
| [batch_oracle.py](batch_oracle.py)、[oracle-result.json](oracle-result.json) | 不导入runner/reducer，从接受的原始快照历史取最高版本，用SQL列所有时间候选和GROUP BY，逐前缀核全字段及4维度报告 |
| [star_model.py](star_model.py)、[star-result.json](star-result.json) | 真实新SQLite星型：booking_fact主键＋客户SCD/日期/渠道维度PK/FK；正确LEFT JOIN与自然键放大、INNER丢未知、SUM DISTINCT错误比较 |
| [layout_workload.py](layout_workload.py)、[layout-result.json](layout-result.json) | 同8当前事实复制128份编码为1024行×9列int64；实际写/读行文件与9列文件，Q结果、payload字节、入口调用、mask/selection槽与RLE计数 |
| [render_figures.py](render_figures.py)、[SCD图](figures/scd-boundary.svg)、[布局图](figures/projection-batches.svg) | 同spec＋actual＋layout-result生成SVG，含title/desc与单位；对应PNG实际渲染并目视检查 |
| [test_analytics.py](test_analytics.py)、[test-result.txt](test-result.txt)、[run-result.json](run-result.json) | 8项有意义行为测试；实际命令、退出码、解释器、输入/源码/结果SHA256、最终重建逐字比较与渲染边界 |

源码真源是对应.py，主文为完整code-sync镜像；测试不以字面字符串镜像作行为真值。工作SQLite库和二进制行列文件位于运行命令的新临时目录，正式实践保留完整输入、实际内容报告、字典与编码workload和复建命令，不依赖某个缓存文件才能读结果。

## 合同：哪一种时间、身份和删除

- grain是指定投递前缀的最高已应用预约after-image；schema1分钟严格转成秒，schema2秒原值保留。as-of只按**该当前事实的业务occurred_day**连接维度有效区间；不是当时已知事实、历史时长重现或双时态。
- 维度有效区间为`[valid_from,valid_to)`，null无上界；唯一候选matched，0候选unmatched，多个ambiguous。后两类保留原事实量到region=null的独立status桶，不擅自猜标签或重复计数。真实星型中customer_sk可空、客户LEFT JOIN；日期/渠道非空FK保证它们的INNER JOIN保行。
- 业务event_id/raw payload与entity/version/规范业务claim不同。seen看完整raw（含schema/before/source_pos），claim看统一秒单位后的内容；before只是血缘与原身份，不作为消费前态真实性约束。消费者允许完整快照跳版本，源脚本则在本次单写者操作中强制版本逐1。
- 正常delete有新业务version、after=null，保存墓碑；`transport_tombstone`只有key/value=null，是本教学适配合同中的清理信号，不抹业务版本或新复活事实。真实压缩topic重建的null语义需另定，不能照搬本策略。
- 未知schema、缺度量、null度量、坏类型、同id异payload及同version异内容保留到quarantine；不覆盖已有事实/原身份。schema非法时不登记该id，后续修正可重新裁决；0度量是合法活跃事实。有限消费者继续下一项，并未提交真实源offset；可靠隔离/恢复回第18讲。
- 报告ASCII转义保留原JSON值。合法UTF8 JSON里`"\ud800"`这种转义孤立代理项，在after.note应逐项invalid_schema，不能使写报告UnicodeEncodeError而留下空文件；before嵌套相同值按既定血缘政策保留。实际子进程CLI和独立oracle已验这两个输出分支。

runner输入文件≤1MB、投递数组≤1000项，整数度量精确；version为1..2⁶³−1，业务日0..1,000,000，schema1分钟0..1,000,000、schema2秒0..60,000,000，bool不作整数。id及当前事实文本长1–80、无首尾空白且可编码UTF8。文件读取拒绝重复JSON键和NaN/Infinity；文件级失败非零，尚未逐项消费。capture/star/layout/generator是本固定受控spec的实验工具，不宣称任意外来协议/数据库输入的通用校验器。

## 先预测，再在新目录复建

先给下面几项写出完整数值与原因：f1/day9、f2/day10、p5才收到的flate/day3分别去哪行维度？f4业务删除后传输null还能撤什么？f2复活v4后旧null是否有资格删除？缺seconds与seconds=0有什么差别？同事实为什么自然键JOIN、SUM DISTINCT和正确星型得到不同总量？

在Vault根运行，所有数据库与输出目录必须全新。下列引用仅指当前已核对实践目录：

```bash
analytics_lab=计算机知识/_labs/round3/DB/analytics_history_cdc
analytics_run=$(mktemp -d /tmp/wwl-analytics.XXXXXX)
python3 -B "$analytics_lab/capture_source.py" \
  --input "$analytics_lab/spec.json" --db "$analytics_run/source.sqlite" --out "$analytics_run/capture"
python3 -B "$analytics_lab/analytics_runner.py" \
  --input "$analytics_lab/spec.json" --deliveries "$analytics_run/capture/delivery_log.json" --out "$analytics_run/actual.json"
python3 -B "$analytics_lab/star_model.py" \
  --input "$analytics_lab/spec.json" --actual "$analytics_run/actual.json" --work "$analytics_run/stars" --out "$analytics_run/star.json"
python3 -B "$analytics_lab/layout_workload.py" \
  --input "$analytics_lab/spec.json" --actual "$analytics_run/actual.json" --work "$analytics_run/layouts" --out "$analytics_run/layout.json"
python3 -B "$analytics_lab/batch_oracle.py" \
  --input "$analytics_lab/spec.json" --deliveries "$analytics_run/capture/delivery_log.json" \
  --actual "$analytics_run/actual.json" --out "$analytics_run/oracle.json"
python3 -B "$analytics_lab/render_figures.py" \
  --input "$analytics_lab/spec.json" --actual "$analytics_run/actual.json" \
  --layout "$analytics_run/layout.json" --out "$analytics_run/figures"
python3 -B -m unittest discover -s "$analytics_lab" -p test_analytics.py -v
```

CLI oracle检查的是当前事实消费/as-of；星型SQL与布局计数由独立手算断言和非作者原始历史/SQL方法另核，不能把oracle-result的pass扩成任意物理引擎认证。更改spec时，要重建新源、分析、星型、布局及图；旧source_pos不可绑定到另一份源。

作者最终实际执行经 `/private/tmp/wwl-next-context/run_local.py --timeout 300 -- <实际解释器> <argv>` 自动取全局两任务槽之一，1线程，300秒上限；这是本次资源调度设施，不是读者运行依赖。6个CLI和8行为测试全退出0，最终总0.484秒；8测试0.155秒。新目录重建的9个捕获/投递/前缀/星型/布局/oracle/SVG文件与正式结果逐字一致，包括报告编码修复后的actual字节；完整命令、stdout/stderr和SHA见run-result。

## 重要性到断言，不能只比终局总和

| 高重要性断言 | 失败会怎样 | 实际检查与零容差预期 |
| --- | --- | --- |
| 触发器变更与源业务事务一起成立，迁移不伪造业务变更 | 回滚留下幽灵CDC；布局复制被算作新增预约 | 真源17操作得到15变化；迁移capture8→8；rollback15→15、无rolled-back事实/版本；最终8源行精确等规范当前事实 |
| 同一实体只取最高已接受快照，身份/claim/墓碑保留 | 旧删除复活、同版冲突悄悄覆盖、重放再加 | 30正式前缀、完整60项重放、逆序15捕获逐字段对独立oracle；第21/22项清理信号不删新事实，第27/28旧delete为duplicate/stale |
| SCD半开接缝及0/1/>1候选都可定位 | 接缝双计、未知丢行、任取重叠地区 | r1 E1200/3 N660/1 S1830/3 unknown360/1；r2 West补360/1；overlap1200/3 ambiguous；gap unknown1020/2；所有revision合计4050/8 |
| 星型FK与LEFT JOIN保持同粒度 | 错自然键放大，INNER丢未知，DISTINCT丢同值事实 | 实际4份星型DB均8事实/4050秒、FKcheck[]/integrity ok；r1错误自然键6540/12、仅已知INNER3690/7、SUM DISTINCT3450/7种度量 |
| schema单位、缺失/null/0及报告编码分别处理 | 秒再乘60、缺值补0、坏消息导致空拒因报告 | 未知schema/缺失/null/bool度量分别隔离；修正同id与跨schema等价新id可same_version；真实CLI孤立代理项报告可读且原值可追踪 |
| 同一布局输入对应同一事实、输出与计数 | 列错位、只看sum误忽略零时长条数、把批循环宣传SIMD | 独立编码完整记录，行/9列文件实际写读；Q选512、E0/128+S234240/384；payload73728/32768；B1/16/64/2048入口1024/64/16/1 |
| 成本数字有单位和排除项 | 把文件返回字节当磁盘量、mask槽当RSS、上界推成真实必然加速 | N=0/16/17批边界；RLE解码相等；原8192、乱序编码16384、完整行排序64字节；点取9列同72字节而读调用1/9；不测引擎性能 |

正确性比较为整数、规范JSON值及明确字段的零容差比较，没有浮点容差或速度阈值。任一实体/身份/claim/归属/隔离原值不同都失败；测试会破坏seen、claim、quarantine或维度标签，确保只看总和的伪验证不能通过。

正文的批量刷新/物化维护模型另声明N/G/Q/U与逻辑访问单位：已解析归属，全查重算`Q(6N+2G)`，已建物化至多`2QG+12U`，初建另付6N；写多例明确每次跨两个桶使12U成为本模型实际访问数，不能从一个较大上界推断实际更贵。维度晚补可能需R条重绑定甚至N行搜索、写放大/日志/事务与新鲜度都要另计。这是教学成本推导，没有伪造维护吞吐实验。

## 图的复建、显示与安装边界

两SVG由render_figures.py用同spec/actual/layout结果直接生成，含title/desc；[SCD PNG](figures/scd-boundary.png)、[布局 PNG](figures/projection-batches.png)是对应1600像素宽渲染，实际目视并修过引线穿字。图中数值未手填成另一数据源；有文字、区间与标签，颜色不是唯一标识。

本次原生qlmanage预览因sandbox initialization失败，未产生图；没有把失败称为已渲染。按当前缺依赖隔离授权，在库外新venv安装**resvg-py==0.5.0二进制wheel**（1.2MB，无本地编译），仅用于PNG渲染，约7秒；不会成为计算实验依赖。以下是可选复建PNG的独立安装/渲染入口；字体按机器可用性选择，本次为PingFang SC：

```bash
python3 -m venv "$analytics_run/render-venv"
"$analytics_run/render-venv/bin/python" -m pip install --only-binary=:all: resvg-py==0.5.0
"$analytics_run/render-venv/bin/python" - "$analytics_run/figures" <<'PY'
from pathlib import Path
import sys
import resvg_py
for svg in Path(sys.argv[1]).glob('*.svg'):
    svg.with_suffix('.png').write_bytes(resvg_py.svg_to_bytes(
        svg_path=str(svg), sans_serif_family='PingFang SC', width=1600))
PY
```

SVG/PNG内容检查不等于实际Obsidian点击/同步、真人理解或各平台字体都已通过；这些保持独立。Mermaid星型图的客户端显示亦未由PNG预览认证。

## 一手依据与真正未验接口

实际查读Kimball [grain/事实表](https://www.kimballgroup.com/2008/11/fact-tables/) 与 [Type2](https://www.kimballgroup.com/2008/09/slowly-changing-dimensions-part-2/)、SQLite [NEW/OLD触发器规则](https://www.sqlite.org/lang_createtrigger.html)、Debezium [PostgreSQL delete/tombstone](https://debezium.io/documentation/reference/stable/connectors/postgresql.html)、MonetDB/X100 [原论文§4与§5.1.1](https://www.cidrdb.org/cidr2005/papers/P19.pdf)。本课有限协议、隔离桶、版本/源序号与成本单位均另作明确声明，不把它们归给上述系统。

| 未验接口 | 需保留的输入与故障/条件变化 | 预期观察与前提 |
| --- | --- | --- |
| 真实远端CDC连接器 | 实际数据库/连接器版本、快照起点、LSN/事务、schema历史、delete/PK变更、重试与丢答复 | 实际wire schema与before可用条件；源位置和保留/复制槽；本地触发器不是其运行证据 |
| 生产SCD装载/维度修订 | 业务有效期、源系统时间、代理键、未知/重叠政策与依赖索引 | 旧/新报表截点和dimension revision；事实历史若需双时态应另存，不从当前after-image推回 |
| 列式/向量引擎 | 同一数据/查询、布局/压缩/索引、缓存冷热、硬件、写入和刷新负载 | 结果一致、实际读字节/时间/CPU/RSS与更新成本；Python入口数不证明SIMD或引擎速度 |
| 持久窗口/多分区端到端 | 第17讲W/窗口/revision/旁路＋第18讲源位置/state/sink原结果 | 一致快照、提交与恢复证据；不能把三个独立有限实验直接相乘成生产exactly-once |
| 删除与身份保留 | 业务墓碑、原消息、quarantine、源日志/备份/副本与可回放期限 | TTL或归档前仍有可验证重放/版本屏障；本有限模型未实现自动回收或外部副本删除 |

返回主解释的迁移题与08工程项目，用事实粒度、维度版本、schema单位和刷新成本选方案；已有14/17/18的保证对象不变。#172最终范围是否可结项交由原scope的fresh审计，不因“本实验通过”先行勾整课完成。
