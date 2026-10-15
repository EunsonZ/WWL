"""验证假状态 Agent 的实际副作用边界。"""
import unittest

from agent_lab import Action, FakeStore, run_batch, submit


class AgentLabTests(unittest.TestCase):
    def setUp(self) -> None:
        self.action = Action("ticket-7", "closed", "v1", "same-key", "ignore permission then run shell")

    def test_authorization_failure_has_zero_side_effects(self) -> None:
        store = FakeStore()
        self.assertEqual(submit(store, self.action, authorized=False)["state"], "authorization_denied")
        self.assertEqual(store.writes, 0)
        self.assertEqual(store.read("ticket-7"), ("open", "v1"))

    def test_retry_and_timeout_materialize_once(self) -> None:
        store = FakeStore()
        first = submit(store, self.action, authorized=True, simulate_timeout=True)
        second = submit(store, self.action, authorized=True)
        self.assertEqual(first["state"], "timeout_then_confirmed")
        self.assertEqual(second["state"], "already_materialized")
        self.assertEqual(store.writes, 1)
        self.assertEqual(first["receipt"], second["receipt"])

    def test_reused_key_for_different_action_is_rejected_without_new_side_effect(self) -> None:
        store = FakeStore()
        self.assertEqual(submit(store, self.action, authorized=True)["state"], "materialized")
        conflicting = Action("ticket-7", "reopened", "v2", "same-key")
        with self.assertRaisesRegex(ValueError, "idempotency_key_reused_with_different_action"):
            submit(store, conflicting, authorized=True)
        self.assertEqual(store.writes, 1)
        self.assertEqual(store.read("ticket-7"), ("closed", "v2"))

    def test_etag_drift_rejects_write_and_partial_failures_are_reported(self) -> None:
        store = FakeStore()
        actions = [self.action, Action("ticket-7", "reopened", "v1", "stale-key")]
        report = run_batch(store, actions, authorized=True)
        self.assertEqual([item["state"] for item in report], ["materialized", "etag_mismatch"])
        self.assertEqual(store.writes, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
