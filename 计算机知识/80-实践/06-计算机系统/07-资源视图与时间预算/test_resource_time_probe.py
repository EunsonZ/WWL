import platform
import contextlib
import io
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from resource_time_probe import (
    CGROUP_ROOT,
    PROC_CGROUP,
    PROC_STATUS,
    ReadText,
    cgroup_directory,
    count_cpu_list,
    cpu_quota_equivalent,
    parse_cgroup_v2_path,
    parse_cpu_max,
    parse_proc_status,
    read_text_if_present,
    remaining_ns,
    resource_report,
    main,
    sample_clock_delta,
)


class ResourceViewTests(unittest.TestCase):
    def _report(self, cgroup_text, *, directory_exists=True):
        observed = []

        def read_fixture(path, limit=4096):
            observed.append(path)
            if path == PROC_STATUS:
                return ReadText("Cpus_allowed_list:\t0-1", False)
            if path == PROC_CGROUP:
                return cgroup_text
            if path.name == "cpu.max":
                return ReadText("150000 100000", False)
            return None

        with patch("resource_time_probe.platform.system", return_value="Linux"), \
                patch("resource_time_probe.read_text_if_present", side_effect=read_fixture), \
                patch("resource_time_probe.Path.is_dir", return_value=directory_exists):
            return resource_report(), observed

    def test_outside_namespace_path_skips_cgroup_without_reading_outside_root(self):
        lines, observed = self._report(ReadText("0::/../sub2", False))
        self.assertTrue(any("cgroup_v2=SKIP" in line and "namespace" in line for line in lines))
        self.assertIn("proc.allowed_cpu_count=2", lines)
        self.assertTrue(any(line.startswith("logical_cpus_visible=") for line in lines))
        self.assertEqual(observed, [PROC_STATUS, PROC_CGROUP])

    def test_double_slash_anchor_never_escapes_root_or_probes_a_directory(self):
        with self.assertRaises(ValueError):
            cgroup_directory(CGROUP_ROOT, "//outside")
        with patch("resource_time_probe.platform.system", return_value="Linux"), \
                patch("resource_time_probe.read_text_if_present",
                      side_effect=[None, ReadText("0:://outside", False)]) as read, \
                patch("resource_time_probe.Path.is_dir") as directory_probe:
            lines = resource_report()
        self.assertTrue(any("cgroup_v2=SKIP" in line for line in lines))
        self.assertEqual([call.args[0] for call in read.call_args_list], [PROC_STATUS, PROC_CGROUP])
        directory_probe.assert_not_called()

    def test_visible_root_and_child_keep_their_normal_mapping(self):
        for relative in ("/", "/child"):
            with self.subTest(relative=relative):
                lines, observed = self._report(ReadText(f"0::{relative}", False))
                self.assertIn(f"cgroup_v2.path={relative}", lines)
                self.assertIn("cgroup.cpu_quota_equivalent=1.500", lines)
                for path in observed[2:]:
                    self.assertEqual(path.parent, CGROUP_ROOT / relative.lstrip("/"))
                missing, reads = self._report(ReadText(f"0::{relative}", False), directory_exists=False)
                self.assertIn("cgroup_v2=SKIP reason=current cgroup directory unavailable", missing)
                self.assertEqual(reads, [PROC_STATUS, PROC_CGROUP])

    def test_missing_truncated_and_legacy_cgroup_text_keep_distinct_results(self):
        cases = (
            (None, "cgroup_v2=SKIP reason=/proc/self/cgroup unavailable"),
            (ReadText("0::/chi", True), "cgroup_v2=TRUNCATED limit=4096; path not parsed"),
            (ReadText("2:cpu:/legacy", False), "cgroup_v2=SKIP reason=unified hierarchy not visible"),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                lines, observed = self._report(value)
                self.assertIn(expected, lines)
                self.assertEqual(observed, [PROC_STATUS, PROC_CGROUP])

    def test_main_continues_to_independent_clock_report_after_namespace_skip(self):
        def read_fixture(path, limit=4096):
            if path == PROC_CGROUP:
                return ReadText("0::/../sub2", False)
            if path == PROC_STATUS:
                return None
            self.fail(f"unexpected read: {path}")

        output = io.StringIO()
        with patch("resource_time_probe.platform.system", return_value="Linux"), \
                patch("resource_time_probe.read_text_if_present", side_effect=read_fixture), \
                contextlib.redirect_stdout(output):
            main()
        self.assertIn("cgroup_v2=SKIP", output.getvalue())
        self.assertIn("deadline.budget_ns=", output.getvalue())
        self.assertIn("delta_ns=", output.getvalue())


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
        with self.assertRaises(ValueError):
            cgroup_directory(root, "relative/path")

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
        try:
            directory = cgroup_directory(CGROUP_ROOT, relative)
        except ValueError:
            self.skipTest("SKIP: current cgroup is outside the visible namespace root")
        if not directory.is_dir():
            self.skipTest("SKIP: current cgroup directory not mounted in this view")
        self.assertTrue(directory.is_dir())

    def test_resource_report_never_requires_linux_files_to_exist(self) -> None:
        lines = resource_report()
        self.assertTrue(any(line.startswith("platform=Linux") for line in lines))
        self.assertTrue(any(line.startswith(("cgroup_v2.path=", "cgroup_v2=SKIP")) for line in lines))


if __name__ == "__main__":
    unittest.main()
