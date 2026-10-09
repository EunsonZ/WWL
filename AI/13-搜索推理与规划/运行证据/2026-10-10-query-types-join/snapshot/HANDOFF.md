# #212 / #216 / #222 完整候选交接

状态：本版作者已冻结完整候选，待独立内容核查与独立执行，未获语义ACCEPT、未落主库、未提交/推送或写GitHub。本包仅写author212216222目录。唯一主库整合者为/root/recovery_writer；父进程/root安排审阅与数值执行槽位，作者未派生代理。抢救RAW_RECOVERED、历史recipe/helper都未import或执行，原文件保持；作者用AST读取字符串作为材料，在当前main基线重建局部正文。旧缺失运行记录及旧已通过回执不继承。

## 正式主库目标与原字节依赖

实际变更10个文件（8正文、2源码），逐项列在evidence/changed-paths.txt：

- AI/13-搜索推理与规划/05-知识表示规则归结与查询.md
- AI/13-搜索推理与规划/query_contract_examples.py
- AI/20-LLM/70-工程应用与工具链/08-混合检索重排RAG误差分解与证据.md
- 计算机知识/55-数据库/10-系统课程/03-SQL查询语义与窗口函数.md
- 计算机知识/70-编译原理/10-系统课程/11-类型统一泛化与值限制.md
- 计算机知识/65-分布式系统/02-复制一致性与可见性历史.md
- 计算机知识/65-分布式系统/gcounter_join_examples.py
- 数学/12-离散数学与逻辑/02-关系函数等价类与偏序.md
- 计算机知识/70-编译原理/09-数据流分析格不动点活跃性与到达定义.md
- 计算机知识/75-软件工程与人机交互/80-一个预约服务的需求到维护案例.md

candidate/按正式路径保存完整文件，baseline/是8个当前主库页面的原字节；current-main-local.diff是基线至本候选的局部差异，evidence/receipt.json记录基线和候选身份。本次检查8个基线均与当时main字节相等，整合前仍查最新版本。80同时有author174的导航修改，writer只应用本包新增容量段，按两者最新完整候选合并，不覆盖174更改。

candidate/AGENTS.md和candidate/AI/13-搜索推理与规划/symbolic_ai_lab.py是当前主库原字节的指令/运行依赖，不是落库变更；本包没有新增统一器。evidence/independent_batch_oracle.py仅供独立验收，不进入读者首页。没有交付stream172源码或流课程正文，不能把本包称#172全课程完成。

## 改进与逐项验收接口

#212：AI05维护同题q=Anc(Cora,Ada)，完整列M0/M1与每条规则实例的满足理由，证明正负两方向均未蕴含；切换有限最小数据库时显式增加完成/闭世界、互异常量与有限论域合同。SQL三行对照保留外层非空守卫、NULL来源及方言限制；RAG三材料条件逐项给最强结论，限定访问范围与版本。哲学→RAG→AI→SQL及返回原问题的标题链真实存在。正文与JSON预期让迁移题有反模型或行结果，权限返回不泄露不可访问记录存在性。

#216：同一AI05保留现有有限项算法，新增Bool/Arrow有限类型树编码、限制项替换取值为类型签名的编码像，给出替换与编码交换的保解集理由。共同方程拆分和σ2∘σ1顺序、自由代表与最一般解完整；间接循环与自应用分别由有限树高度反证。有限项/rational tree/显式递归类型、统一/蕴含/指定类型系统判断分开，空KB反模型和换构造器迁移题有具体解或失败约束。HM11双向标题链只追加必要桥接，不改let泛化与值限制主文。

#222：复制02维护唯一增长计数主例和完整LUB/交换结合幂等证明、三种合并与重复消息反例；固定独占身份、局部原子/串行、状态保留、数学自然数、最终传播及方法终止条件明确。保序与只上升给两个反例；无限链与有限更新后收敛不混淆，有限CFG工作列表与soundness各有原文返回。容量轨迹含读取空集合、两端不同意图各自接受、union同值和2≤1失败，明确只反驳另造的无协调规则。80仅补反例出口，偏序02/数据流09选择性回链主解释。

## author174实际消费依赖与版本边界

本包引用的正式目标为计算机知识/75-软件工程与人机交互/82-v2意图恢复与演进实验.md，当前真实文件在../author174/同路径。静态核对身份为75e0c0bf89ee195f7f1fbf373d03b826533a3751c91fffb2883644318cb0503e（startup锁等待窄正文增量后）；使用该页实际已有标题“唯一业务合同：移动端与流处理共用”“接口版本与模式迁移分别管理”“故障历史、迁移与可检查范围”。writer发布前确认82正式就绪；不把目录存在等同发布，不等整个#174课程验收。

直接消费wwl-reservation-v2/1，key=(actor,intent_id)，指纹规范字段actor/end/op/policy_version/start，不含epoch或id；accepted/rejected是持久业务决定，unknown不是终局否定，WriterFenced不是业务拒绝。不同意图容量安全、同意图恢复、state join幂等各有合同，不另建预约协议。本文静态读取author174固定源码与82接口，未复制或修改174源码，174实跑由其独立执行者负责。

#172/#175消费边界为增量/重放/更新/删除、事件时间窗口/watermark/晚到乱序、offset+状态+待交付输出恢复与本地排队/权威确认；本文只写这些不能由增长join自动兑现，不审签相应课程。主库尚无正式172/175正文落点，因此没有添加虚构或旧RAW页正式链接。新课接收时从其真实查询/恢复位置消费本主解释；#209成员变更、删除、恶意节点/文本协作仍未由本例覆盖。

## 已做静态检查和当前来源

作者仅AST解析：两个新实验、原字节symbolic_ai_lab及独立batch oracle，共4文件；没有import/运行这些候选。AI05与复制02两处新code-sync镜像逐字节等于源码。现有scripts.links候选+当前main+真实author174/82 overlay定向核对113引用，0诊断；8个基线当时0漂移。报告evidence/static-checks.json。全库检查器自身测试未跑，静态绿色不代替重要推导与行为独立核查。

fresh只读GitHub #212/#216/#222的完整body/comments在evidence/issue*.json，均comments=0，包含2026-10-09共同实施追加验收。当前Stanford、Cornell、PostgreSQL17、SSS2011与RR7506必要位置已读核，evidence/primary-locations.md给准确URL及页/节。旧关于已跑PASS或缺失实验结果-20261009-GCounter的链接均未继承。

## 独立执行命令、固定输入和预期

父进程分配数值执行≤2槽；在全新冻结副本执行，保存源码/环境/原始输出。Python3.10+，标准库，无安装或外网；本候选含唯一原字节symbolic_ai_lab依赖。作者未运行以下命令：

```bash
python3 -B candidate/AI/13-搜索推理与规划/query_contract_examples.py
```

预期evidence/fixed-input-oracle.json：M0/M1均满足F1/F2/R1/R2、query分别false/true；SQL顺序[1,0,0,0],[2,null,1,1],[null,null,1,0]，末列guard。树正例atom→Ada/Ada，Arrow三变量规范化为同一自由变量（方向/名字允许不同），换Bool题→Bool/Bool；间接occurs/type_occurs/Bool-Int均false；空KB结构统一成功与语义反模型分别核。记录SQLite真实版本，不能称PostgreSQL执行或真实RAG。

```bash
python3 -B candidate/计算机知识/65-分布式系统/gcounter_join_examples.py
python3 -B evidence/independent_batch_oracle.py
```

以上三条命令均以本HANDOFF所在目录为包根。query脚本由Python按自身目录找到symbolic_ai_lab；oracle从自己的真实路径定位同版candidate源码，无硬编码/tmp或旧会话目录。

固定p=(2,0),q=(0,3),重复p，三种消息顺序→(2,3)/5，max=3，sum=7；grouped同值。共享身份query1实际2、丢状态复用身份query2实际3；末次未送达same=false后送达(2,3)；wraparound不只上升；重复command两次为(2,0)，重复state为(1,0)。预约union两端同值、capacity1、两活动、capacity_holds=false。batch oracle独立枚举16状态的256对LUB全部上界和4096三元组，事件id集合核计数，3消息顺序；预期status PASS，booking_overlap=[A:1,B:1]。有限验证不是一般收敛定理证明，也不运行权威预约源码。

重要语义、源码行为与新消费者段待独立review；本版全部实验NOTRUN。Obsidian显示/跳转、同步、真实网络/存储服务、HTTP/认证、生产迁移、真人学习效果均未验。本包正文已有固定输入及完整证明，不依赖缺失的旧运行记录；独立review通过后writer接收局部diff，独立运行结果以本版实际记录再接入，不提前写PASS。
