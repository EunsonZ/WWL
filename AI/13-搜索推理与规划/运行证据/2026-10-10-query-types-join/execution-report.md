# #212 / #216 / #222 独立执行回执

本包已完成本版固定命令与执行者独立有限 oracle，全部命令退出0，四份stderr为空。源码/正文审阅由review212216222独立承担；本包尚不等于主库落地、发布或真人学习验证。只有本新执行目录被写入，author/main/174冻结包未修改；没有Git/GH操作、派生代理、网络、安装或服务更改。

## 冻结输入与运行环境

`snapshot/`按候选原布局保留8正文、2新源码、既有symbolic_ai_lab依赖、AGENTS、HANDOFF与固定input/oracle/receipt。`source-manifest.json`逐文件保存原字节SHA；18文件规范manifest总SHA256为 `fa708ec9d5fbf87492b61c58e4d3fbc10e8c999872103f7d7ee3af5364bfa299`。收尾 `source-recheck.json`确认18文件均与作者原包同字节。

| 实际Python输入 | SHA256 |
| --- | --- |
| query_contract_examples.py | 496d45b39867fbae66630ff43878dfed099e48dcb48cda64624780768c84f10a |
| symbolic_ai_lab.py 原依赖 | 701c7c14f1d414619add9e6b6491ae90767c3327ea4ce62da0cb74281bef91a5 |
| gcounter_join_examples.py | e9baaa649e9b1ea8fb537c404d9e16522ebc4e5cb7514a66b6ec3c3079f14a16 |
| 作者交付 independent_batch_oracle.py | 72f8a169b521d997fc83e3143d38aa613dd06c91ca4bfc34bcaf7272e4e847a2 |

静态读脚本确认标准库、无网络、纯内存SQLite及有限循环。query按自身目录找到symbolic依赖；作者oracle从其路径定位同一snapshot/candidate。执行者oracle也只从本包snapshot读取被测公开操作，不依赖隐藏作者目录或主库，不调用被测main/expected/run作为预期。未运行symbolic完整搜索/CSP测试，范围只到本任务有限项统一。

`fixed-runs.json`保存真实argv/cwd、Python3.14.7、SQLite版本、平台、每条开始时刻/时长/退出码、隔离HOME/TMPDIR与4线程环境请求。三固定命令串行、每条subprocess timeout60秒，实际耗时分别约0.044/0.017/0.032秒。无依赖编译或准备。固定子进程累计resource观察ru_maxrss为26,132,480 bytes（macOS单位），执行者oracle自进程为26,230,784 bytes；这是有限进程RSS观察，不能当硬内存上限或OS线程计数认证。执行者oracle为单进程标准库、没有线程池/worker，实际耗时约0.011秒；其真实命令/退出码/环境读取另在 `executor-run.json`。

## 原输出与独立比对

`logs/query.stdout` / `query.stderr`：两个有限模型M0/M1均满足事实及全部规则实例，Anc(Cora,Ada)分别false/true。SQLite实际三行是 `[1,0,0,0]`、`[2,null,1,1]`、`[null,null,1,0]`。固定统一例原JSON保留归一变量和替换后项，Arrow三个变量成为同一自由代表，Bool题成为Bool/Bool；间接occurs、自应用type_occurs、Bool/Int冲突false。统一P(x)/P(Ada)成功，不能推断空KB蕴含P(Ada)。

`logs/gcounter.stdout` / `gcounter.stderr`：三种乱序重复状态消息都得到(2,3)/5；scalar_max3、scalar_sum7。共享身份query1与真实两次增长、状态丢失query2与真实三次增长分别不一致；未最终传播时两端不同，最终交付后(2,3)；wraparound不只上升；重复命令两次为(2,0)，重复状态为(1,0)。容量1反例两端union相同，但两条重叠预约使capacity_holds=false。

`logs/author-batch-oracle.stdout` / `.stderr`：原作者独立枚举16状态、256对上界、4096三元ACI及3消息顺序均PASS；这份脚本的作者归属明确，不冒称由执行者写成。

`executor_oracle.py` / `logs/executor-oracle.stdout`：额外执行者独立预期，未读取作者fixed-input-oracle作为计算真源，未调用被测报告方法获得期待值。

- 显式构造M0/M1并保存每个三变量赋值的规则真值；另用路径遍历独立求有限最小可达关系。结果只在有限域、互异常量、Parent事实完成、Anc最小解释/闭世界的额外合同下作为数据库否定，M1仍是原开放语义的正查询模型。
- 独立SQL三值逻辑：NULL比较为UNKNOWN、EXISTS只看TRUE见证，重算NOT IN/NOT EXISTS及外层非空守卫三行；这里实际执行的是SQLite，没有认证PostgreSQL或真实RAG后端。
- 自写递归项归一核对solver替换；直接及间接occurs、类型循环、构造器及arity冲突独立失败预期。成功Arrow解保持自由代表；4个有限ground Bool/Arrow类型的64组赋值中，解恰是alpha=beta=gamma的4组。
- 类型编码与类型替换独立构造5例，核对 `encode(θ(type))=apply(encode(type),encode(θ))`；组合顺序σ2∘σ1把alpha变Bool，反方向留下beta。空谓词单元素模型给P(Ada)反模型，不把结构统一写成语义蕴含。
- 另独立枚举16状态的全部上界，核对唯一最小上界与被测join，并从独占writer事件id集合并集计算期待计数；256对/4096三元与3种消息序列一致。报告保留p/q所有上界、最小上界、完整事件集合与每步状态，不只输出Boolean。
- 独立构造两预约记录并用资源及区间交集检出(A:1,B:1)重叠；union同值且2≤1为false。该例只反驳另造的无协调规则，没有运行reservation_v2或改约束合同。

## 复建与边界

原证据目录冻结只读。要复建，先在自己拥有的新空目录复制 `snapshot/`、`run_fixed.py`、`executor_oracle.py`，创建 `home/`、`tmp/`、`logs/` 子目录，再只在新目录运行：

```bash
python3 -B run_fixed.py
python3 -B executor_oracle.py > logs/executor-oracle.stdout 2> logs/executor-oracle.stderr
```

驱动和输入以自身位置解析，不依赖本隐藏恢复目录的绝对路径；各自日志写入新目录，不覆写原回执。每条固定命令的真实相对argv见fixed-runs。执行者oracle固定有限循环无随机性、无服务；独立重跑可套同样60秒外层限制。artifact-manifest保存脚本/报告/输出字节身份。

本轮没有执行失败或缺依赖。有限复算补充正文证明，不证明一般模型蕴含、所有统一输入、所有CRDT交错或一般收敛定理。未认证真实RAG访问/权限、PostgreSQL方言运行、HTTP/身份认证、真实网络存储、预约Authority/迁移、Obsidian显示/跳转/同步、性能或真人学习；源码内容独核和下游#172/#175/#209完整课验收由相应任务负责。
