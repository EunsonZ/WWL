import mmap
import tempfile
import unittest
from pathlib import Path

from system_observer import (
    MAPPING_BYTES,
    discover_linux_topology,
    observe_mapping,
    parse_cpu_list,
    read_linux_process_memory,
)


class SystemObserverTests(unittest.TestCase):
    def test_parse_cpu_list(self) -> None:
        self.assertEqual(parse_cpu_list("0-3,8,10-11\n"), (0, 1, 2, 3, 8, 10, 11))
        with self.assertRaises(ValueError):
            parse_cpu_list("4-2")

    def test_discovers_fixture_topology(self) -> None:
        with tempfile.TemporaryDirectory(prefix="topology-fixture-") as directory:
            root = Path(directory)
            for cpu, package, core in ((0, 0, 0), (1, 0, 0), (2, 0, 1), (3, 0, 1)):
                topology = root / "cpu" / f"cpu{cpu}" / "topology"
                topology.mkdir(parents=True)
                (topology / "physical_package_id").write_text(str(package), encoding="utf-8")
                (topology / "core_id").write_text(str(core), encoding="utf-8")
            node = root / "node" / "node0"
            node.mkdir(parents=True)
            (node / "cpulist").write_text("0-3\n", encoding="utf-8")

            observed = discover_linux_topology(root)
            self.assertIsNotNone(observed)
            assert observed is not None
            self.assertEqual(observed.logical_cpus_observed, 4)
            self.assertEqual(observed.cores_observed, 2)
            self.assertEqual(observed.packages_observed, 1)
            self.assertEqual(observed.nodes, (("node0", (0, 1, 2, 3)),))

    def test_parses_linux_status_fixture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="status-fixture-") as directory:
            status = Path(directory) / "status"
            status.write_text("Name:\tpython\nVmSize:\t1234 kB\nVmRSS:\t567 kB\n", encoding="utf-8")
            memory = read_linux_process_memory(status)
            self.assertEqual(memory.virtual_kib, 1234)
            self.assertEqual(memory.resident_kib, 567)

    def test_mapping_is_small_and_touched_once_per_page(self) -> None:
        size = 1024 * 1024
        before, after_map, after_touch, checksum = observe_mapping(size)
        self.assertEqual(checksum, len(range(0, size, mmap.PAGESIZE)))
        self.assertLessEqual(size, MAPPING_BYTES)
        for snapshot in (before, after_map, after_touch):
            self.assertTrue(snapshot.virtual_kib is None or snapshot.virtual_kib >= 0)
            self.assertTrue(snapshot.resident_kib is None or snapshot.resident_kib >= 0)

    def test_rejects_large_mapping(self) -> None:
        with self.assertRaises(ValueError):
            observe_mapping(MAPPING_BYTES + 1)


if __name__ == "__main__":
    unittest.main()
