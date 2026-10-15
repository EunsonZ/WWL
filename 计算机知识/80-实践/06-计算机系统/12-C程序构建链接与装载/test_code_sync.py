import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MIRROR = ROOT / "源码与测试镜像.md"
SYNCED = ("sum.h", "sum.c", "main.c", "duplicate_sum.c", "build_trace.py", "test_build_trace.py")


class CodeSyncTests(unittest.TestCase):
    def test_every_declared_source_matches_its_markdown_block(self) -> None:
        mirror = MIRROR.read_text(encoding="utf-8")
        for name in SYNCED:
            marker = re.escape(f"<!-- code-sync: ./{name} -->")
            pattern = marker + r"\n```[^\n]*\n(.*?)\n```"
            match = re.search(pattern, mirror, flags=re.DOTALL)
            self.assertIsNotNone(match, name)
            self.assertEqual(match.group(1), (ROOT / name).read_text(encoding="utf-8").rstrip("\n"), name)


if __name__ == "__main__":
    unittest.main()
