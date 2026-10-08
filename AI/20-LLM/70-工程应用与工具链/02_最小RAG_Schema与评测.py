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
    if not matches:
        return json.dumps(
            {"answer": "资料未说明", "citations": [], "confidence": 0.0},
            ensure_ascii=False,
        )
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
