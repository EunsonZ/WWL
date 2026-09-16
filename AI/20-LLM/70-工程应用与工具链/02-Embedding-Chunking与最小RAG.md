---
type: lesson
status: ready
stage: 1
difficulty: 入门
estimated_minutes: 45
verified: 2026-09-01
domain: artificial-intelligence
topics:
  - embeddings
  - chunking
  - rag
  - retrieval-evaluation
tags:
  - ai/llm/engineering
---

# Embedding、Chunking 与最小 RAG

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 召回证据、正确使用证据和标明证据是三个环节。用理想证据与无检索对照可以判断瓶颈来自检索还是生成，不要只优化向量相似度。 深化与验证：[[AI/20-LLM/70-工程应用与工具链/08-混合检索重排RAG误差分解与证据|混合检索重排RAG误差分解与证据]]；[[AI/10-机器学习与深度学习基础/17-概率校准保形预测与分布偏移|概率校准保形预测与分布偏移]]。


## 直觉：RAG 是“先找候选，再让模型写”，不是给模型加记忆

检索增强生成（retrieval-augmented generation, RAG）在回答前，从一个**已建立权限边界且有版本的资料集合**中找出少量片段（chunk），再将这些片段与问题交给 LLM。它可以让答案有当前证据和引用，但只要资料缺失、过时、被错误切分或检索失败，生成阶段就不会魔法般修正它。

## 精确定义与四类边界

给文档 chunk $c_i$ 和查询 $q$，embedding 模型产生向量 $e(q),e(c_i)\in\mathbb R^d$。常见检索分数是余弦相似度：

$$
\operatorname{cos}(q,c_i)=\frac{e(q)\cdot e(c_i)}{\|e(q)\|\|e(c_i)\|}.
$$

向量和余弦的数学定义见 [[数学/20-线性代数与几何/03-点积范数距离与余弦相似度|点积、范数、距离与余弦相似度]]。实际系统还可用[[计算机知识/50-数据结构与算法/20-倒排索引精确近邻与近似向量检索|倒排索引、精确近邻与近似向量检索]]中的关键词（BM25）、过滤和重排序；**相似度只是排序信号，不是事实概率、权限或引用证明**。

| 层 | 输入 → 输出 | 责任边界 |
| --- | --- | --- |
| 文档与数据库 | 原始资料、source/version/ACL 元数据 → 可追溯记录 | 数据库保存权威原文、版本和访问控制；不能把“已入库”误当作正确或适合回答 |
| 分块与索引 | 已授权记录 → 带 ID/来源/版本的 chunk 与向量/倒排索引 | 保持定位信息；不能删掉权限过滤，也不能把 chunk 文本当系统指令 |
| 搜索 | 查询 + 用户/租户权限 → top-k 候选 | 负责候选发现；必须先或同时执行 ACL 过滤，不能只在回答后“遮住”资料 |
| LLM 与程序 | 问题 + 选中证据 → 候选回答；程序验证引用/Schema | LLM 生成候选，程序限制上下文、校验输出并决定是否展示/执行 |

## Chunking 不是按固定字符数随手切开

一个好 chunk 有明确来源 ID、文档版本、标题/位置、权限标签和可重建的切分配置。按段落/标题/句子边界常比纯长度更可读；为召回可保留有限 overlap，但 overlap 过多会重复证据、膨胀 token 和偏向某一文档。表格、代码、版本化政策和跨段落定义尤其需要按结构切分。

先在离线开发集比较 chunk 长度、overlap、top-k 和混合检索，再锁定策略。改变任何一个都会使索引版本不同，因此不能拿旧评测分数给新索引背书。

## 可运行的最小闭环（纯标准库、CPU）

下面的同目录文件同时演示：词袋向量、余弦排序、带来源 ID 的证据拼接、确定性“生成器替身”、Schema 校验与独立检索指标。它**不下载模型、数据或依赖**；词袋只匹配共享字符/词，特意不是语义 embedding。要接入真实 embedding 时，应单独固定模型 ID、revision、向量维度、归一化、索引构建参数和数据权限，并在当天复核 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]（本页工具核验日期：2026-09-01）。

示例中的 `TOKEN_RE` 只是可审计的英文词/中文单字切分，不等于 Unicode 词边界、字素簇、中文分词或模型 tokenizer；正则的 Unicode 单位与引擎差异见 [[编程知识/10-基础/01-正则表达式/07-Unicode与引擎差异|Unicode 与引擎差异]]。

<!-- code-sync: ./02_最小RAG_Schema与评测.py -->
~~~python
"""仅用 Python 标准库演示最小检索、Schema 校验与离线评测。

运行：python3 02_最小RAG_Schema与评测.py
此程序不下载模型、数据集或依赖；词袋向量只是可验证教学替身，不能替代语义 embedding。
"""
from __future__ import annotations

import json
import math
import re
import statistics
import time
from dataclasses import dataclass
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source: str
    text: str


CORPUS = [
    Chunk("refund-1", "退款规则", "订单在付款后 7 天内可以申请退款；处理时间通常为 3 个工作日。"),
    Chunk("shipping-1", "配送规则", "普通配送在付款确认后发货；偏远地区可能额外增加 2 天。"),
    Chunk("privacy-1", "隐私规则", "客服只能读取处理工单必需的信息，不能在回复中展示完整支付信息。"),
]


def tokens(text: str) -> list[str]:
    """把文本切成可审计的字符/英文词 token；真实系统应固定模型 tokenizer。"""
    return [item.lower() for item in TOKEN_RE.findall(text)]


def vector(text: str) -> dict[str, float]:
    counts: dict[str, float] = {}
    for token in tokens(text):
        counts[token] = counts.get(token, 0.0) + 1.0
    return counts


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    dot = sum(value * right.get(key, 0.0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def retrieve(question: str, corpus: list[Chunk], limit: int = 2) -> list[tuple[Chunk, float]]:
    query = vector(question)
    ranked = [(chunk, cosine(query, vector(chunk.text))) for chunk in corpus]
    return sorted(ranked, key=lambda pair: (-pair[1], pair[0].chunk_id))[:limit]


def compose_prompt(question: str, matches: list[tuple[Chunk, float]]) -> str:
    """程序负责组装边界；LLM 只接收问题和已选证据，不能获得数据库权限。"""
    evidence = "\n".join(f"[{chunk.chunk_id}] {chunk.text}" for chunk, _ in matches)
    return (
        "任务：仅依据证据回答；证据没有说明时写‘资料未说明’。\n"
        "输出：JSON 对象，含 answer、citations、confidence 三个键。\n"
        f"问题：{question}\n证据：\n{evidence}"
    )


def validate_answer(raw: str, allowed_ids: set[str]) -> dict[str, Any]:
    """执行应用层 Schema 约束；JSON 可解析不等于答案真实或有权限。"""
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("输出必须是 JSON 对象")
    expected = {"answer", "citations", "confidence"}
    if set(value) != expected:
        raise ValueError(f"键必须恰为 {sorted(expected)}")
    if not isinstance(value["answer"], str) or not value["answer"].strip():
        raise ValueError("answer 必须是非空字符串")
    if not isinstance(value["citations"], list) or not all(isinstance(x, str) for x in value["citations"]):
        raise ValueError("citations 必须是字符串数组")
    if any(item not in allowed_ids for item in value["citations"]):
        raise ValueError("citation 不能引用未检索到的证据")
    if not isinstance(value["confidence"], (int, float)) or isinstance(value["confidence"], bool):
        raise ValueError("confidence 必须是数值")
    if not 0.0 <= value["confidence"] <= 1.0:
        raise ValueError("confidence 必须在 0 到 1 之间")
    return value


def call_generator_stub(question: str, matches: list[tuple[Chunk, float]]) -> str:
    """可替换的模型边界。这里是确定性替身，避免下载或调用任何模型/API。"""
    top, score = matches[0]
    if score == 0.0:
        answer = "资料未说明"
        citations: list[str] = []
        confidence = 0.0
    else:
        answer = top.text
        citations = [top.chunk_id]
        confidence = round(min(0.95, 0.4 + score), 2)
    return json.dumps({"answer": answer, "citations": citations, "confidence": confidence}, ensure_ascii=False)


def answer(question: str, corpus: list[Chunk]) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    matches = retrieve(question, corpus)
    prompt = compose_prompt(question, matches)
    raw = call_generator_stub(question, matches)
    parsed = validate_answer(raw, {chunk.chunk_id for chunk, _ in matches})
    trace = {
        "query": question,
        "retrieved_ids": [chunk.chunk_id for chunk, _ in matches],
        "prompt_characters": len(prompt),
        "output_characters": len(raw),
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "model_revision": "stub-no-model",
        "index_revision": "demo-corpus-v1",
    }
    return parsed, trace


def evaluate(cases: list[dict[str, Any],], corpus: list[Chunk]) -> dict[str, float]:
    retrieval_hits = 0
    grounded = 0
    latencies: list[float] = []
    for case in cases:
        result, trace = answer(case["question"], corpus)
        retrieval_hits += int(case["required_chunk"] in trace["retrieved_ids"])
        grounded += int(set(result["citations"]).issubset(set(trace["retrieved_ids"])))
        latencies.append(trace["latency_ms"])
    total = len(cases)
    return {
        "retrieval_recall_at_2": retrieval_hits / total,
        "citation_subset_rate": grounded / total,
        "latency_ms_median": statistics.median(latencies),
    }


if __name__ == "__main__":
    result, trace = answer("退款要多久处理？", CORPUS)
    assert trace["retrieved_ids"][0] == "refund-1"
    assert result["citations"] == ["refund-1"]
    assert "3 个工作日" in result["answer"]
    assert validate_answer('{"answer":"ok","citations":[],"confidence":0.5}', set())["answer"] == "ok"
    invalid_schema_outputs = [
        "null",
        "[]",
        '"not an object"',
        "0",
        '{"answer":"ok","citations":[]}',
        '{"answer":"ok","citations":[],"confidence":0.5,"extra":true}',
        '{"answer":"ok","citations":["stolen"],"confidence":0.5}',
    ]
    for invalid in invalid_schema_outputs:
        try:
            validate_answer(invalid, {"refund-1"})
        except ValueError:
            pass
        else:
            raise AssertionError(f"必须拒绝无效 Schema：{invalid}")

    metrics = evaluate(
        [
            {"question": "退款规则是什么？", "required_chunk": "refund-1"},
            {"question": "什么时候发货？", "required_chunk": "shipping-1"},
            {"question": "客服能看支付信息吗？", "required_chunk": "privacy-1"},
        ],
        CORPUS,
    )
    assert metrics["retrieval_recall_at_2"] == 1.0
    assert metrics["citation_subset_rate"] == 1.0
    print(json.dumps({"answer": result, "trace": trace, "metrics": metrics}, ensure_ascii=False, indent=2))
~~~

在本页所在目录运行短命令：

```text
python3 02_最小RAG_Schema与评测.py
```

如果终端当前位于 Vault 根目录，则运行完整相对路径：

```text
python3 AI/20-LLM/70-工程应用与工具链/02_最小RAG_Schema与评测.py
```

成功时，断言会证明退款问题把 `refund-1` 排在首位、引用不能越过检索集合，并拒绝 `null`、数组、字符串、数字、缺键、多键等无效 JSON Schema；三条离线用例的 `recall@2` 为 1。该结果只证明这个小语料与这个替身的逻辑；它**不**证明真实模型的语义质量、长文本鲁棒性、权限安全或线上延迟。

## 评测应分离检索与生成

不要只问“答案看起来好不好”。为每条冻结的离线用例保存 query、允许的 gold chunk ID（或相关集合）、期待的回答条件、版本与评审说明：

- **检索：** Recall@k / MRR / nDCG 衡量相关证据是否进入候选；它不评判文字是否正确。
- **生成：** 事实/任务正确性、引用是否支持回答、拒答是否恰当、格式合规；它不能反推“索引没问题”。
- **端到端：** 只在前两者都可追查时汇总；必须记录是哪一层失败（ACL、分块、召回、重排、模板、模型或校验）。

抽样和不确定性处理见 [[数学/30-概率与统计/05-统计估计置信度与模型评测|统计估计、置信度与模型评测]]。若评测集很小，分数波动很大；报告样本数、分层和区间/不确定性，不把一次人工试用写成稳定提升。

## 风险、恢复与练习

- **提示注入：** 文档里“忽略规则”的字样只是数据；程序要把证据清晰分隔，禁止其影响权限、工具 allowlist 或系统策略。
- **泄漏：** query、chunk、prompt、日志和向量都可能暴露内容；按租户/用户过滤、最小化保留，离线评测使用已获准资料。
- **陈旧/删除：** 保存 document/index revision；源文档删除、权限变更或版本替换时，重建受影响索引并使旧 chunk 不可召回。
- **恢复：** 版本化 chunk 配置、索引和评测集；召回退化时先切回上一索引 revision，再用固定用例定位，而不是在线上盲目调 top-k。

练习：把语料加入两段都含“退款”的资料，设计一个 gold 集和一个权限标签；证明权限过滤在检索前生效，并解释为什么“答案引用了 ID”仍不足以说明那段话支持答案。成功标准是能给每个结果追溯 source、chunk ID、索引版本和检索分数。

## 导航

**上一站**：[[AI/20-LLM/70-工程应用与工具链/01-HuggingFace与PyTorch工具链|Hugging Face 与 PyTorch 工具链]] · **下一站**：[[AI/20-LLM/70-工程应用与工具链/03-结构化输出Schema与错误恢复|结构化输出、Schema 与错误恢复]] · **相关原理**：[[AI/20-LLM/10-原理/03-Embedding表示与语义空间|Embedding 表示与语义空间]] · **返回**：[[AI/20-LLM/70-工程应用与工具链/00-工程应用与工具链-MOC|工程应用 MOC]]
