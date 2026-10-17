# 固定成员一致读：新鲜法定人数与应用位置

读者终点是解释一次get如何跨过当前任期提交、本次多数确认与状态机应用三种不同位置，能拒绝旧主/旧票/跨任期旧下界，又能接受与新写重叠的合法旧值。一般证明、六题完整答案与业务返回在[[计算机知识/65-分布式系统/06-一致读的法定人数屏障与应用位置|06主解释]]；先独做[无答案题纸](QUESTIONS.md)。本包扩展原02/03的读断点；旧distributed_lab.py及其code-sync镜像保持原合同。

实际下层是假设满足日志匹配、固定成员多数、Leader Completeness与已提交前缀不改变的非Byzantine复制寄存器。put成功须已提交并应用。ReadIndex读不写日志，但开始前必须已有当前任期条目提交。成功读取同一状态快照中的(appliedIndex,value)，且appliedIndex≥本读捕获的readIndex。一般证明的前缀下界限于**调用前已有节点知悉提交**的位置（包括先前成功写和成功读所见）；客观已复制多数但确认暂存的在途写可以排在本次读后。有限程序不是完整Raft、认证服务或租约实现。

## 固定输入、实现和观察层

[plans.json](plans.json)是read-barrier-v1完整输入：固定A/B/C，8计划139高层动作，初始寄存器0；put7、noop、选举、复制、显式应用、探测生成/投递、停止路由、恢复与重启皆有位置。客户端逻辑序号是调度器产生的调用/返回事件，非服务器墙钟。所有值与消息均是教学数据，不接真实预约或外部业务。

| 真源/产物 | 所负责的事实 |
|---|---|
| [read_model.py](read_model.py) | term/vote/log/commit/applied/value与read context；四门与原子查询；不依赖全局时间 |
| [worker.py](worker.py) | 同协议机的实际loopback JSON RPC、每节点SQLite稳定字段与逐响应审计 |
| [run_lab.py](run_lab.py) | 固定动作、暂存应答、多角色客户端历史、路由丢弃、自有PID生命周期 |
| [history_oracle.py](history_oracle.py) | 不import协议实现；按寄存器规格、实时前驱约束及在途写扩展，动态规划找合法顺序；另查消息/索引证书 |
| [test_read_barriers.py](test_read_barriers.py) | 8项必要边界断言；不以终局x=7替代逐步读裁决 |
| [execute.py](execute.py) / [pack_evidence.py](pack_evidence.py) | 内存/进程/两层oracle/测试顺序执行；原始工作文件无损压缩与映射 |
| [plot_reads.py](plot_reads.py) | 只读正式JSON状态/客户端区间，生成两SVG，不重新求协议答案 |

内存层每动作保全部3节点状态；进程层每动作通过真实TCP到三个worker并取得状态。控制器手动推进选举和路由：`block`是控制器不发送消息，`hold`是父进程已收到真实RPC回复但延迟将其提交给leader。**不是操作系统网络分区、跨机网络或线程压力测试。** `write_poll`的`hold_client`表示逻辑客户端响应由控制器延迟释放，非一个真实远端用户停在套接字上。Node本身不是任意多线程安全对象；wrapper/worker每次串行处理一条命令。

`unsafe_local_read`是显式反例接口，故意绕过安全get门；不属于声称线性一致的API。`manual_probe`只为展示“有新确认仍缺当前任期提交”或“跨任期新票不能盖旧下界”，不替安全read上下文签发成功。

## 逐断言的重要性、预期失败和结果

全部协议/历史裁决要求精确相等；没有“数值差一点也算一致”的容差。执行耗时、PID、端口、Python patch版本、monotonic_ns是环境元数据，不要求重建相同；内存/进程semantic parity仅豁免重启动作的实际生命周期字段，保留其他逐动作/RPC/节点/历史内容。

| 断言与重要性/理由 | 输入或条件变化及独立预期 | 正式有限结果 |
|---|---|---|
| 高：新主当前任期提交门；日志含值不等于知道提交 | TermGate：B有put7但commit0；删门可回0，违背已完成写 | 安全读wait_current_term_commit；noop提交后再读7；unsafe历史失败 |
| 高：readIndex与apply分开；否则新鲜主也可读旧状态 | ApplyLag：B commit2/applied0，多数确认已到 | wait_apply不回值；应用后7/served2；unsafe0失败 |
| 高：本次nonce、同term与不同成员；缓存票不是新确认 | OldLeader：先完成新主put7，再向隔离旧主读；两次旧票 | 两次nonce_or_term_mismatch，wait_quorum；heal后更高term取消；unsafe0失败 |
| 高：整历史实时顺序；不能只查每个读与写有无重叠 | DelayedTermReply读先调用、旧term本次确认晚到；ReadReadOrder先7后0均跨在途写 | 前者合法顺序read0→put7；后者不可线性化 |
| 高：跨任期取消/重捕获；新票不能修旧readIndex | CrossTerm：term2写完成→term1捕获旧索引→term3重选 | 旧上下文取消；新读wait_apply后7；unsafe旧状态失败 |
| 高：重启丢pending且稳定字段保留；旧实例应答不得复活 | Restart：B真实回复已到父进程，但A尚未消费；此barrier后kill自有A | SIGKILL实际−9；boot1→2/follower/无pending；旧确认拒绝，新确认后7 |
| 高：逐前缀/原始RPC/状态机身份；终局一样仍可中途错误 | 两层完整417节点状态、9成功读证书，八good与五bad历史 | 两层语义完全相同；8good均合法，5bad均非法；8测试exit0 |

[正式内存结果](evidence/memory-results.json)、[进程结果](evidence/process-results.json)、[内存oracle](evidence/memory-oracle.json)、[进程oracle](evidence/process-oracle.json)、[逐层比对](evidence/parity.json)保留完整内容。batch oracle独立于增量实现，却仍是作者自查；非作者另以全排列历史、原始消息和SQLite重开独核，不能把本文件的PASS自行升级为一般证明或真人学习结果。

## 实际运行与隔离复建

需要Python3.11+标准库（正式3.14.7，sqlite3/TCP/subprocess），无第三方数值依赖。每组最多3个自有worker进程，均单线程，地址只绑定127.0.0.1、端口由系统分配；共享runner限制两个作业槽，不意味着本实验虚构为仅两个节点。父进程只终止自己Popen创建的PID，有就绪5秒、RPC2秒、worker空闲30秒、阶段60秒及外层180秒界。异常清理先正常shutdown/terminate，必要才kill自有子进程；不会按端口或进程名扫杀用户服务。

从本目录执行；`--out`必须选尚不存在的新路径。正式命令如下（环境的runner路径是本次工作台入口，脱离工作台可直接运行execute.py并自行提供同等超时）：

```sh
python3 -B /private/tmp/wwl-next-context/run_local.py --timeout 180 -- /opt/homebrew/opt/python@3.14/bin/python3.14 -B execute.py --out /private/tmp/read-barrier-rebuild-209
python3 -B pack_evidence.py --run /private/tmp/read-barrier-rebuild-209 --out /private/tmp/read-barrier-archive-209
```

实际原命令及各阶段argv、cwd、stdout/stderr、退出码见[运行记录](evidence/run-receipt.json)：原输出目录`/private/tmp/wwl-next-209-distributed/formal-run`，5阶段全部exit0，总1.463213377秒。25次worker启动，1次SIGKILL−9，24次正常exit0；最后全部当前自有监听关闭。原源码SHA与完整输入嵌在两份results中；身份绑定帮助定位版本，不是正确性证明。源代码以后若改行为，应重跑受影响组并更新绑定，不能只手改PASS。

只复查历史，不启动进程：

```sh
python3 -B history_oracle.py --results evidence/process-results.json --out /private/tmp/read-barrier-oracle-209.json
python3 -B -m unittest -v test_read_barriers.py
```

输出保护边界：execute/run_lab/pack_evidence/history_oracle拒绝已有目标；但在新目录内运行期间发生语义/I/O失败可能留下部分证据，须检查最终退出码和完整阶段记录。图程序会覆盖指定文件，应选自己的新路径。输入仅接受read-barrier-v1、≤12计划、每计划≤100动作；Node log与每boot读上下文各≤64，term/index有限，ID为≤40位ASCII白名单，整数拒bool。它是有限教学接口，不是任意大历史/任意恶意JSON服务；计划层与每命令校验分别承担边界。

## 稳定保存、kill和原始证据

每节点SQLite一行保存term/vote/log/commit/applied/value/boot，`journal_mode=WAL`、`synchronous=FULL`；影响稳定字段的RPC在对应SQLite事务commit后才发成功响应。纯读上下文是易失状态，不为每个普通读添加一次fsync；接收更高term的探测仍可能先持久化term。worker启动先读旧稳定字段、boot递增并保存，再公布READY。SQLite报错不产生有效协议成功回复。整份JSON单行是本地持久适配，**不是分布式快照、日志压缩或InstallSnapshot**。

Restart的准确barrier是“B已产生确认，父进程已收到，A尚未消费”；不是“安全读已完成但伪造未完成”。父进程SIGKILL自己创建的A，实际exit−9，再开同一A库重选。此处检查进程故障/重启；无掉电、文件系统损坏、备份回滚或已确认term丢失试验。boot不能修复稳定存储回退。

[压缩映射](evidence/compression-map.json)逐文件记录原路径/长度/原SHA和gzipSHA。73份原worker文件479136字节中48份非空无损gzip共34135字节；25个空stderr以空文件hash保留、archive=null。24份最终SQLite与24份逐RPC审计均在`evidence/workers/`（逐文件入口见[压缩映射](evidence/compression-map.json)）；启动/kill/退出/端口证据另在process-results.lifecycle，原始681审计事件可复算。gzip设置mtime0，只减少保存体积，不筛掉失败或改写协议消息。

解包时在新目录重建每个文件后核原SHA，再用SQLite只读检查；不要覆盖现有实验库。例如：

```python
import gzip, hashlib, json, pathlib, sqlite3
base = pathlib.Path('evidence')
out = pathlib.Path('/private/tmp/read-barrier-unpacked-209')
out.mkdir()  # 已存在即失败，保护他人的结果
for row in json.loads((base/'compression-map.json').read_text())['files']:
    data = gzip.decompress((base/row['archive']).read_bytes()) if row['archive'] else b''
    assert len(data) == row['size_bytes']
    assert hashlib.sha256(data).hexdigest() == row['uncompressed_sha256']
    dest = out/row['original_relative_path']
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
for db in out.rglob('*.sqlite'):
    with sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1', uri=True) as con:
        print(db.relative_to(out), con.execute('select payload from stable where id=1').fetchone()[0])
```

只对已经关闭且无-WAL/-SHM旁文件的归档库使用immutable；不能以该标志读取正在变化的生产库并声称相容快照。源码pack_evidence会拒绝未关闭的WAL旁文件。

## 同数据图与未验接口

![[计算机知识/65-分布式系统/read_barrier_lab/evidence/barriers.png]]

![[计算机知识/65-分布式系统/read_barrier_lab/evidence/histories.png]]

```sh
python3 -B plot_reads.py --results evidence/memory-results.json --out /private/tmp/read-barrier-figures-209
```

SVG是标准库从保存状态/区间生成；当前两PNG由resvg_py0.5.0及macOS PingFang字体以1600px宽栅格化，已实际查看。可用[render_figures.py](render_figures.py)与自己隔离环境中的resvg_py重建；它是可选显示依赖，协议实验不需要。字形/字体或栅格器改变可改PNG字节，SVG坐标/数据才是解释接口。未在Obsidian客户端预览，非真人迁移学习试验。

高重要性未验接口应给可核观察：真正身份/认证与固定成员配置输入；完整AppendEntries冲突回退/自动选举重试；跨机网络丢包分区及进程暂停；磁盘错误/掉电后的term/vote/log持久单调；并发状态机查询的相容(applied,value)；真实客户端调用/返回与超时重试。按本页字段采原始RPC、稳定事务位置、role/term/boot、commit/applied、客户端历史，失败判据是已完成历史不能线性化、已确认稳定状态回退或不相容读。上述不可由loopback单机kill替代。

租约必须另有时钟/暂停界；动态成员要另证跨配置交集；快照要绑定日志/提交/应用/恢复位置；Byzantine需不同身份与故障合同。它们仍是#209独立剩余，未因本包读屏障关闭。SE82业务intent/稳定决定、222合并收敛与容量安全也保持原合同；本包线性一致get不自动提供原子预约。

来源：Raft [扩展论文§8](https://raft.github.io/raft.pdf)与[作者博士论文clients章五步只读算法](https://raw.githubusercontent.com/ongardie/dissertation/master/clients/clients.tex)，以及[Herlihy–Wing历史定义§2.2](https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf)。有限实现的nonce/boot/串行SQLite适配是本教学模型的具体化，非冒称这些论文规定了同一Python接口。
