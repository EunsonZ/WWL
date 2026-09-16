---
type: practice
status: ready
content_status: usable
evidence_status: partial
evidence_record: "[[Logs/2026-09-05_改造证据/内容审阅记录]]"
prerequisites:
  - "[[数学/30-概率与统计/05-统计估计置信度与模型评测]]"
  - "[[AI/20-LLM/70-工程应用与工具链/02-Embedding-Chunking与最小RAG]]"
stage: 1
difficulty: 中级
estimated_minutes: 70
verified: 2026-09-02
domain: artificial-intelligence
topics:
  - rag
  - retrieval-evaluation
  - private-service
  - prompt-injection
  - observability
tags:
  - ai/practice
  - ai/llm/rag
  - ai/security
---

# RAG 评测与私有服务

> [!info] 历史证据已补入
> 原有证据字段保持其历史记录；所指 [[Logs/2026-09-05_改造证据/内容审阅记录|内容审阅记录]] 已从 WorkWithLLM 按原字节补入。其范围见 [[Logs/来源材料/WorkWithLLM/README|来源说明]]；本批未重新认证本页内容或提升证据等级。

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 本轮[[AI/80-实践/08-深层机制数值实验/00-数值实验导航与验收|42 项深层机制测试]]补充梯度、概率、缓存与训练状态验证；它与本页实验解决不同层的问题。先读[[AI/20-LLM/80-研究拓展/03-从论文主张到可复现实验|验证层级]]，不要把算子测试成功登记成真实模型或部署验收。


## 你将完成什么

本实践是一条**完全离线、仅 Python 标准库、CPU 可运行**的最小 RAG 路径：本地教学语料 → 可重建 chunk → ACL 先过滤的词袋检索 → 带 chunk ID 的证据 → 确定性生成替身 → Schema 校验 → 分离的检索/生成评测 → 无正文 trace。它不下载模型、数据或依赖，也不把教学 ACL 误当认证。

概念前置：[[AI/20-LLM/70-工程应用与工具链/02-Embedding-Chunking与最小RAG|Embedding、Chunking 与最小 RAG]]、[[AI/20-LLM/70-工程应用与工具链/03-结构化输出Schema与错误恢复|结构化输出、Schema 与错误恢复]]、[[AI/20-LLM/70-工程应用与工具链/04-评测回归与可观测性|评测、回归与可观测性]]。完整且与同目录源码逐字同步的服务与测试见 [[AI/80-实践/05-RAG评测与私有服务/01-完整源码与测试附录|完整源码与测试附录]]。

## 先运行：不监听端口

在本目录运行：

```text
python3 -m unittest -v test_rag_service.py
python3 rag_service.py
```

第一条运行真实 CPU 索引、分块、排序和负向门禁，但**不会创建监听 socket**；第二条只打印一次离线答案、无正文 trace 与指标。预期教学用例的 `recall_at_k`、`mrr_at_k`、答案条件率、结构引用子集率、已标注事实的引用覆盖率和 schema 合格率均为 `1.0`。延迟随机器变化，只检查其非负和字段齐全。

## 数据流与关键边界

### 指标、失败与快照的当前合同

`hit_at_k` 表示每题是否至少命中一个 gold；`recall_at_k` 现在是逐题相关项覆盖率再取 macro 平均，修复前的同名字段实际是 Hit。两个 gold 只找回一个时，Hit@1=1、Recall@1=0.5、若第一位相关则 MRR@1=1。去重返回 ID 后计算集合覆盖；空评测集或空 gold 显式拒绝，候选不足 k 返回较短列表。gold 是普通相关项集合，不能把它当成联合证据充分性的证明。[Recall 定义](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-unranked-retrieval-sets-1.html)。

评测从 `answer_raw` 取得生成字符串及内部 trace，再验证一次。无效 JSON、键、citations 或 confidence 计入 `schema_failure_rate`，超时/连接失败计入 `infrastructure_failure_rate`；所有案例都保留在分母中，编程错误继续抛出。合法格式也可以得到事实失败，不能把结构成功当成内容正确。

`algorithm_version`（兼容属性 `revision` 与 trace 中 `index_revision`）表示算法；内部 `snapshot_id`/`index_snapshot` 表示内容、分块参数、权限版本和算法的确定性摘要。相同输入重建稳定，删除或配置变化会改变摘要。摘要、权限和查询指纹是敏感派生值，`public_trace` 排除它们以及 chunk ID；内部调试记录仍须访问控制。

自检：为同一问题构造两个 gold、仅取回其中一个，然后让生成器返回 `{}`。预期 Recall 为 0.5、格式成功率为 0；再给合法但无证据支持的答案，确认格式成功和事实失败可以同时出现。

```text
已授权本地文档
  → chunk_document：按 token 窗口定位，用原始字符 span 截取
  → LocalIndex.retrieve：先 ACL 过滤，再词袋排序
  → compose_prompt：证据围栏；证据只是数据
  → generator_stub：确定性教学替身
  → validate_answer：JSON 形状、类型、范围、citation 属于本次候选
  → citation_covers_expected_fact：已标注事实至少有一个支持 ID
  → result + public_trace：算法版本、分数、近似 token、延迟；不含内部 ID/快照/指纹
```

分块绝不通过 `"".join(tokens)` 重建文本：那会丢失英文词之间的空格、标点、换行及标识符边界。实现以正则匹配的首尾字符 offset 从原文切出窗口；测试覆盖中英文、标点、换行、`foo_bar-42` 和 overlap。

```python
matches = list(TOKEN_RE.finditer(document.text))
window = matches[start : start + size]
text = document.text[window[0].start() : window[-1].end()]
```

`citation_subset_rate` 只说明 citation 没越过**本次**候选集合，因此结构校验后可能恒为 1。`answer_with_supported_citation_rate` 另外要求命中人工标注的支持 chunk ID；测试保留“结构有效、候选内、但不支持‘三个工作日’”的反例。二者仍不能证明任意自然语言结论被逐字蕴含；真实系统需人工或经审阅的语义判分规则。

### 这个评分器为什么会给错误回答满分

`answer_condition_rate` 只检查 `answer_must_contain` 是否出现在回答中；退款题的 `answer_with_supported_citation_rate` 还要求引用人工标注的支持 ID。这是“子串命中 + ID 覆盖”的教学评分规则。

**自造反例**：让退款题返回“并非在三个工作日内处理，政策未给出处理期限。”，同时引用 `refund-policy:2`、给出合法的 `confidence`。这句话与教学政策冲突，却仍包含“三个工作日”并引用了指定 ID，因此该单题的答案条件率、支持引用率和 Schema 合格率都为 `1.0`。满分暴露了评分器没有检查否定关系；判断事实正确性仍需核对完整断言与证据。

另一个口径细节是：当前代码用全部案例作分母，因此 `citation_subset_rate` 等于 `schema_valid_rate`；只在已过 Schema 的案例中看引用子集条件，它才恒为 1。

`confidence` 也需要单独解释：有证据分支把候选的词袋余弦相似度 `score` 代入 `min(0.95, 0.4 + score)`，再保留两位小数。校验器只检查其类型与 0 到 1 的范围；这是演示分数，本例没有提供校准证据，不能读成回答正确的概率。概率分数、经验成功率与置信区间的区别见 [[数学/30-概率与统计/05-统计估计置信度与模型评测#“置信度”一词的三种用法|三种“置信度”]]。

### 比较方案时保留失败案例与题目配对

先约定要估计的是“对纳入评测的请求，完整流程成功的比例”，并固定成功判据、失败计分和题目集合。下面是**自造的 5 题算术示例**，不是真实系统评测；成功记 1，失败记 0，格式失败也计入分母：

| 同一题目 | 方案 A | 方案 B | 差值 A − B |
| --- | --- | --- | --- |
| 1 | 1 | 1 | 0 |
| 2 | 1 | 1 | 0 |
| 3 | 1 | 0 | 1 |
| 4 | 0 | 0 | 0 |
| 5 | 0（格式失败） | 1 | −1 |

A、B 都是 `3/5 = 0.60`。若删去 A 的格式失败，就会得到 `3/4 = 0.75`；它改变了分母，已经不再估计原先约定的完整流程成功比例。保留配对后，每题差值为 `[0, 0, 1, 0, -1]`，平均差为 0，但第 3、5 题的得失不同，不能从均分相等推出逐题相同或统计等价。实际比较应保存每题结果，按真实抽样单位构造差值的不确定性；同一用户或文档产生多题时不能把它们当独立样本。方法与条件见 [[数学/30-概率与统计/05-统计估计置信度与模型评测#模型比较：优先保留配对|配对模型比较]]。这 5 题只解释计算口径，不能支持真实用户总体上的效果结论。

## 安全、服务与恢复

- 文档、用户输入与工具输出都是不可信数据；它们不能改变 ACL、系统规则或工具权限。
- HTTP 仅在显式 `--serve` 时启动，且只接受 `127.0.0.1`；源码拒绝 `localhost`、LAN 和公网地址。它没有认证或 TLS，故不能暴露给 LAN/公网。
- 已接受的 HTTP 连接设置 5 秒读取超时，线程为 daemon，关闭时不等待线程；这只是教学资源边界，不替代认证、限流、进程隔离或生产审计。
- 本轮测试不运行 `--serve`，也不实际绑定 loopback 端口；它只测试非 loopback 在绑定前被拒绝，以及读取超时的配置 helper。
- 变更 chunk 大小、overlap、语料或 ACL 后重建并记录新的内部内容快照；算法变化另更新 algorithm version。用冻结评测集比较，退化时回到上一内容/配置/算法组合；不把这些敏感派生数据写入公共日志。本例无持久化索引、后台服务或外部请求。

## 证据等级与练习

已运行的证据是标准库/CPU 的教学逻辑：它不证明真实 embedding、真实 LLM token 数、生产吞吐、认证安全或抗攻击能力。练习时新增一篇仅 `support` 可见文档，先证明 public 检索不到它；再修改 chunk 配置并更新 gold ID；最后构造候选内但不支持某项事实的 citation，确认覆盖指标会失败而不是只看结构合格。

## 导航

**完整代码与测试**：[[AI/80-实践/05-RAG评测与私有服务/01-完整源码与测试附录|完整源码与测试附录]] · **前置**：[[AI/20-LLM/70-工程应用与工具链/02-Embedding-Chunking与最小RAG|最小 RAG]] · **评测**：[[AI/20-LLM/70-工程应用与工具链/04-评测回归与可观测性|评测、回归与可观测性]] · **数学**：[[数学/30-概率与统计/05-统计估计置信度与模型评测|统计估计、置信度与模型评测]] · **Linux**：[[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|网络、存储、日志与故障排查]] · **返回**：[[AI/80-实践/00-AI实践-MOC|AI 实践 MOC]]
