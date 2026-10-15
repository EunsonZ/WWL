"""完全离线的受限行动 Agent 教学实验，只有标准库。

这个实验以假状态和白名单动作模拟提交物化；没有 shell、网络、文件写入或
动态工具发现。它演示授权、幂等、超时查询、ETag 漂移和部分失败怎样进入报告。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FakeStore:
    records: dict[str, tuple[str, str]] = field(default_factory=lambda: {"ticket-7": ("open", "v1")})
    # key -> (immutable action payload, receipt).  A bare key is not enough:
    # its reuse for another resource or desired state must be rejected.
    idempotency: dict[str, tuple[tuple[str, str, str], str]] = field(default_factory=dict)
    writes: int = 0

    def read(self, record_id: str) -> tuple[str, str]:
        return self.records[record_id]

    @staticmethod
    def _payload(record_id: str, new_value: str, etag: str) -> tuple[str, str, str]:
        return (record_id, new_value, etag)

    def prior_receipt(self, record_id: str, new_value: str, etag: str, idempotency_key: str) -> str | None:
        """Return a receipt only for an exactly identical retry; reject key reuse."""
        prior = self.idempotency.get(idempotency_key)
        if prior is None:
            return None
        payload, receipt = prior
        if payload != self._payload(record_id, new_value, etag):
            raise ValueError("idempotency_key_reused_with_different_action")
        return receipt

    def patch(self, record_id: str, new_value: str, etag: str, idempotency_key: str) -> str:
        prior = self.prior_receipt(record_id, new_value, etag, idempotency_key)
        if prior is not None:
            return prior
        current, current_etag = self.records[record_id]
        if current_etag != etag:
            raise ValueError("etag_mismatch")
        self.writes += 1
        receipt = f"receipt-{self.writes}"
        self.records[record_id] = (new_value, f"v{self.writes + 1}")
        self.idempotency[idempotency_key] = (self._payload(record_id, new_value, etag), receipt)
        return receipt


@dataclass(frozen=True)
class Action:
    record_id: str
    new_value: str
    etag: str
    idempotency_key: str
    material_instruction: str = ""


def submit(store: FakeStore, action: Action, *, authorized: bool, simulate_timeout: bool = False) -> dict[str, object]:
    """先授权，再提交；超时后查同一幂等键的可观察结果，而不盲目重写。"""
    if not authorized:
        return {"state": "authorization_denied", "writes": store.writes, "receipt": None}
    prior = store.prior_receipt(
        action.record_id, action.new_value, action.etag, action.idempotency_key
    )
    if prior is not None:
        return {"state": "already_materialized", "writes": store.writes, "receipt": prior}
    receipt = store.patch(action.record_id, action.new_value, action.etag, action.idempotency_key)
    if simulate_timeout:
        # An uncertain transport outcome is not an excuse to submit a second write.
        return {
            "state": "timeout_then_confirmed",
            "writes": store.writes,
            "receipt": store.prior_receipt(
                action.record_id, action.new_value, action.etag, action.idempotency_key
            ),
        }
    return {"state": "materialized", "writes": store.writes, "receipt": receipt}


def run_batch(store: FakeStore, actions: list[Action], *, authorized: bool) -> list[dict[str, object]]:
    """逐项真实报告，不能用一项成功覆盖后续拒绝或 ETag 漂移。"""
    report = []
    for action in actions:
        try:
            report.append(submit(store, action, authorized=authorized))
        except (KeyError, ValueError) as error:
            report.append({"state": str(error), "writes": store.writes, "receipt": None})
    return report
