# 事件时间窗口实验：收件顺序不等于业务归属

回到主解释 [[计算机知识/55-数据库/10-系统课程/17-事件时间窗口水位线与迟到修订|事件时间窗口、水位线与迟到修订]]：先按表格预测，再运行。实验是一段本地内存解释器，Python 3.10+ 标准库（含 SQLite）即可；无依赖安装、Beam、消息中间件、后台线程、外部服务或网络输出。source/state/sink 的持久恢复尚未实现。

## 输入、真源与交付结果

- [events.json](events.json)：完整固定 41 项日志，协议 `event-time-windows-v1`。默认窗宽10分钟、允许迟到5分钟；原点、单位、边界和裁决顺序见主解释。
- [window_runner.py](window_runner.py)：规范增量源码，完整 after-image、旧/新窗口原子政策检查、撤旧添新、版本快照输出。每个成功的单线程调用是本模型的观察边界，没有磁盘事务。
- [batch_oracle.py](batch_oracle.py)：独立原始前缀解释器；不导入 runner、不调用 reducer、不用增量加减计算批量真值。它从被接受的原始快照历史选最高实体版本，再在独立内存 SQLite 中 `GROUP BY w,g`，从原始输入控制序列重建发布时点及版本。
- [test_windows.py](test_windows.py)：行为与政策变式；使用两程序互比之外的手算边界断言、双历史反例与报告损坏检查。源码镜像在主解释页，修改真源时同步。
- [actual.json](actual.json)：默认日志实际运行的完整前缀状态报告，包括全部身份、claim、实体/墓碑、活动窗、revision、输出与旁路。它是观察结果，不是预设金标准。
- [trace-summary.json](trace-summary.json)：上述报告的可读压缩入口，每步保留裁决、活动窗和本步输出；必要身份与旁路全文仍看 actual。
- [oracle-result.json](oracle-result.json)、[test-result.txt](test-result.txt)、[run-result.json](run-result.json)：分别为独立批量核对、测试输出、运行环境/预算/退出码/输入与源码 SHA256。run-result 标识的是这次运行字节，不代表以后改动也被覆盖。

规范文件 CLI 要求 UTF-8 JSON 数组，最多1000项，输入≤1 MB。runner 的 JSON 文件读取拒绝重复键与 NaN/Infinity：文件解析失败直接非零，尚未处理任何项；文件合法但单项 schema/type/range 不合法则逐项 invalid，不登记身份。oracle CLI用于核对这份已由 runner 读取的固定合法 JSON 日志与实际报告，不是面向任意不可信文件的通用校验器。实验没有生产容量、持久性、吞吐和时钟精度结论。

## 预测与运行

先手推 p=5、7、9、15、16、23、26：分别是哪一窗、哪个组、几条事实，发第几版，为什么接受或旁路？尤其先回答 p=16 是否可以只往新窗加7。默认预期是 p15 的0A发第9版final 6/1；p16整条expired_old，新窗不加；p23的10B发第3版late 0/0；p26的10A/10B分别第7/6版final 0/0。

在 Vault 根运行下列命令，新结果写到独立临时目录；本目录的交付观察值不被覆盖：

```bash
window_run=$(mktemp -d /tmp/wwl-event-windows.XXXXXX)
python3 -B 计算机知识/_labs/round3/DB/event_time_windows/window_runner.py \
  --input 计算机知识/_labs/round3/DB/event_time_windows/events.json \
  --out "$window_run/actual.json"
python3 -B 计算机知识/_labs/round3/DB/event_time_windows/batch_oracle.py \
  --input 计算机知识/_labs/round3/DB/event_time_windows/events.json \
  --actual "$window_run/actual.json" --out "$window_run/oracle.json"
python3 -B -m unittest discover \
  -s 计算机知识/_labs/round3/DB/event_time_windows -p test_windows.py -v
```

在课文中先算 `--lateness 0`、`--lateness 20`、`--width 5` 或 `--width 20` 的差异，再修改 runner 命令参数；oracle 从报告取得政策参数，复核时必须确认报告参数就是你要检查的口径。更改政策必须从原日志重新运行，不能在旧状态继续消费半份新政策。

## 哪些断言必须核对，为什么重要

| 高重要性断言 | 失败会造成什么 | 有限验证与容差 |
| --- | --- | --- |
| 每个前缀的活动窗口贡献等于已接受最新事实的批量GROUP BY | 无窗总和正确却撤错窗，或旧窗留数、新窗又加数 | 默认41前缀、5政策组合逐前缀全状态相等；整数与JSON内容精确，不设浮点容差 |
| stale、late、expired分别裁决 | 把新版本误丢为旧版，或把已封存旧贡献当成可撤 | t3的a/v2迟到可应用；W14仍可改；W15恰到回收界限；更高版跨窗expired_old；旧v1仍stale |
| 输出版本、phase、零条数撤回与final | 下游重复相加、保留幽灵组、把暂定说成最终 | 29完整快照逐前缀比全部字段；手算0A@9、10B@3和final零值；篡改revision/sum/phase必须被拒 |
| 原始事件身份、历史claim与旁路原因不能丢 | 重放重复旁路、同版冲突漏判、冻结实体被悄悄推进 | seen/claims/墓碑/旁路原事件全量比较；篡改side原因或删除seen必须失败；完整82项重放普通输出不变 |
| 过期旧、新窗先一起检查 | 跨窗更新只改一侧，报表同时计两次或丢一次 | expired_old/new/both都有固定项；冻结x从t2→t16 B时，不产生新窗贡献；旧实体版本不前移 |
| 摘要缺实体归窗仍不充分 | 各窗总和相同却无法删除正确窗 | H₁/H₂每窗均10/1、无窗20/2，同一delete给不同结果；这是窗口归属反例 |
| 参数改变不偷换口径 | 对不同窗口键域沿用旧revision而误合并报表 | Δ/L五组完整原始日志重算，精确比较每前缀；不能据通过推断生产W估计正确 |

作者运行记录（2026-10-16）：经全局槽2批准，CPU线程=1、墙钟上限120秒；6个行为测试退出0，unittest耗时0.244秒，`/usr/bin/time -p` real0.30秒。两个CLI均退出0，默认41前缀通过、29普通输出、4旁路；完整重放82项与5组Δ/L核对均在该测试中通过。原始测试输出和文件哈希见 run-result 与 test-result。运行未触及主库写入、真实预约合同、外部服务或引擎。

作者自测与独立批量算法有不同证据角色：两程序同意及有限测试支持实现行为，主文另给一般归纳证明；重要定义、拒绝政策和证明仍须未参与作者的独立核查，不能把作者运行称为非作者签收。

## 保留、回收与修复接口

本实验只回收 final 之后的活动聚合行，保留 entities/墓碑、seen、claims、revision、普通输出历史和旁路，因此总状态无界。过期事件登记身份与claim，但不推进实体；原id重试duplicate，不重复投旁路。若业务要求接受回收后纠正，需消费旁路原事件和权威历史，从一致的输入截止位置另建带报表代数/政策版本的旧新窗结果；本程序没有实现该批量修复接口，不把“留了旁路”称为修好了账。

可独立验收但本次没有运行的外部接口：

| 待验接口 | 最小输入与预期观察 | 证据应落哪里 |
| --- | --- | --- |
| Beam 固定窗/trigger/lateness | 独立最小管道，显式指定时间戳与触发/累积策略；核实际runner对边界与迟到pane行为 | 单独版本化的引擎运行报告；不得把本Python模拟改名Beam实测 |
| 可撤销业务消息适配 | 将entity before/after转换为旧窗撤回与新窗加入；核不同版本、重放和墓碑 | 独立适配日志及逐窗批量参考；Beam按元素归窗本身不提供本实体撤回合同 |
| 下游替换快照 | 同一(window,group,revision)重复/乱序，异版取高、同版异内容报错 | sink收据与权威状态；本实验没有实际sink |
| 跨资源恢复 | 同一事件身份、源位置、持久状态与输出版本；分别在目标已写源未确认、源已前移状态未存处中断并重放 | 后续恢复单元的原始输入、故障点、源/状态/sink证据；本次不实现 |
| 实际W来源与保留策略 | 乱序/空闲分区、网络中断、业务删除期限、可回放源屏障 | 来源端与runner的版本化观测；水位线估计不能替代身份回收证明 |

## 本次查读的官方依据与边界

2026-10-16实际查读 [Beam Basics 的 Window/Watermark/Trigger](https://beam.apache.org/documentation/basics/)，以及 [Programming Guide §8.4](https://beam.apache.org/documentation/programming-guide/#watermarks-and-late-data)、[§9.1与§9.4](https://beam.apache.org/documentation/programming-guide/#triggers)。它们支持：窗口按元素时间划分、watermark估计完整性、trigger决定pane发布、允许迟到和累积模式需要显式配置。官方模型的“超过最大时间戳加允许迟到后可能回收”不等于本分钟合同的 `W≥e+L`，也不提供本课entity版本裁决、跨窗整条拒绝、revision编号或外部sink原子性；这些是上文明确声明并由源码实现的教学政策。

下一步接 [[计算机知识/55-数据库/10-系统课程/18-源位置状态快照与目标恢复|第18讲的两资源恢复]]，它用无窗事实隔离源位置/state/sink故障，未为本窗口模型实现持久恢复；[[计算机知识/55-数据库/10-系统课程/19-分析模型维度历史与变更捕获|第19讲]] 再接星型/SCD、schema单位/本地捕获与行列/批成本。整课状态回当前#172；本实验不认证真人理解、Obsidian显示、真实业务、生产服务或硬件。
