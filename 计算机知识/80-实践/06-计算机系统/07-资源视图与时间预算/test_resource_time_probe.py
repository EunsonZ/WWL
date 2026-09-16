import platform
import tempfile
import time
import unittest
from pathlib import Path

from resource_time_probe import (
    CGROUP_ROOT,
    PROC_CGROUP,
    PROC_STATUS,
    cgroup_directory,
    count_cpu_list,
    cpu_quota_equivalent,
    parse_cgroup_v2_path,
    parse_cpu_max,
    parse_proc_status,
    read_text_if_present,
    remaining_ns,
    resource_report,
    sample_clock_delta,
)


class ParserTests(unittest.TestCase):
    def test_proc_status_selects_only_allowlisted_fields(self) -> None:
        text = "Name:\tpython\nUid:\t501\t501\t501\t501\nSeccomp:\t2\n"
        self.assertEqual(
            parse_proc_status(text, ("Uid", "Seccomp")),
            {"Uid": "501\t501\t501\t501", "Seccomp": "2"},
        )

    def test_count_cpu_list_handles_ranges_duplicates_and_singletons(self) -> None:
        self.assertEqual(count_cpu_list("0-3,2,8,10-11"), 7)
        self.assertEqual(count_cpu_list(""), 0)

    def test_count_cpu_list_rejects_descending_range(self) -> None:
        with self.assertRaises(ValueError):
            count_cpu_list("4-2")

    def test_parse_cpu_max_and_equivalent(self) -> None:
        self.assertEqual(parse_cpu_max("200000 100000"), (200000, 100000))
        self.assertEqual(cpu_quota_equivalent("200000 100000"), 2.0)
        self.assertIsNone(cpu_quota_equivalent("max 100000"))

    def test_parse_cgroup_v2_path(self) -> None:
        text = "11:memory:/legacy\n0::/user.slice/example.scope\n"
        self.assertEqual(parse_cgroup_v2_path(text), "/user.slice/example.scope")
        self.assertIsNone(parse_cgroup_v2_path("2:cpu:/legacy\n"))

    def test_cgroup_directory_stays_below_root(self) -> None:
        root = Path("/sys/fs/cgroup")
        self.assertEqual(
            cgroup_directory(root, "/user.slice/example.scope"),
            root / "user.slice" / "example.scope",
        )
        with self.assertRaises(ValueError):
            cgroup_directory(root, "/../escape")

    def test_bounded_read_reports_truncation_without_parsing_a_partial_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "io.max"
            path.write_text("8:0 rbps=1000 wbps=2000\n", encoding="utf-8")
            result = read_text_if_present(path, limit=8)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.truncated)
        self.assertEqual(result.text, "8:0 rbps")


class DeadlineTests(unittest.TestCase):
    def test_remaining_ns_saturates_at_zero(self) -> None:
        self.assertEqual(remaining_ns(1_500, 1_000), 500)
        self.assertEqual(remaining_ns(1_500, 2_000), 0)

    def test_monotonic_and_cpu_clock_deltas_are_nonnegative(self) -> None:
        delta = sample_clock_delta(sleep_seconds=0, work_iterations=1_000)
        self.assertGreaterEqual(delta.monotonic_ns, 0)
        self.assertGreaterEqual(delta.perf_counter_ns, 0)
        self.assertGreaterEqual(delta.process_cpu_ns, 0)
        if delta.thread_cpu_ns is not None:
            self.assertGreaterEqual(delta.thread_cpu_ns, 0)

    def test_realtime_delta_can_be_negative_after_a_clock_adjustment(self) -> None:
        samples = {
            "realtime": iter((10_000, 9_000)),
            "monotonic": iter((100, 140)),
            "perf_counter": iter((200, 245)),
            "process_cpu": iter((300, 320)),
            "thread_cpu": iter((400, 410)),
        }

        def fake_clock(name: str) -> int:
            return next(samples[name])

        delta = sample_clock_delta(
            sleep_seconds=0,
            work_iterations=0,
            sleeper=lambda _: None,
            clock_ns=fake_clock,
        )
        self.assertEqual(delta.realtime_ns, -1_000)
        self.assertEqual(delta.monotonic_ns, 40)
        self.assertEqual(delta.perf_counter_ns, 45)
        self.assertEqual(delta.process_cpu_ns, 20)
        self.assertEqual(delta.thread_cpu_ns, 10)

    def test_negative_experiment_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            sample_clock_delta(sleep_seconds=-1)

    def test_monotonic_clock_contract_is_reported_by_python(self) -> None:
        self.assertTrue(time.get_clock_info("monotonic").monotonic)


@unittest.skipUnless(platform.system() == "Linux", "SKIP: Linux procfs/cgroup ABI unavailable")
class LinuxReadOnlyIntegrationTests(unittest.TestCase):
    def test_proc_self_status_is_readable_or_explicitly_skipped(self) -> None:
        text = read_text_if_present(PROC_STATUS)
        if text is None:
            self.skipTest("SKIP: /proc/self/status unavailable or unreadable")
        if text.truncated:
            self.skipTest("SKIP: /proc/self/status exceeds bounded read")
        self.assertIn("Uid", parse_proc_status(text.text))

    def test_current_cgroup_v2_path_when_mounted(self) -> None:
        text = read_text_if_present(PROC_CGROUP)
        if text is None:
            self.skipTest("SKIP: /proc/self/cgroup unavailable or unreadable")
        if text.truncated:
            self.skipTest("SKIP: /proc/self/cgroup exceeds bounded read")
        relative = parse_cgroup_v2_path(text.text)
        if relative is None:
            self.skipTest("SKIP: unified cgroup v2 hierarchy not visible")
        directory = cgroup_directory(CGROUP_ROOT, relative)
        if not directory.is_dir():
            self.skipTest("SKIP: current cgroup directory not mounted in this view")
        self.assertTrue(directory.is_dir())

    def test_resource_report_never_requires_linux_files_to_exist(self) -> None:
        lines = resource_report()
        self.assertTrue(any(line.startswith("platform=Linux") for line in lines))
        self.assertTrue(any(line.startswith(("cgroup_v2.path=", "cgroup_v2=SKIP")) for line in lines))


if __name__ == "__main__":
    unittest.main()
