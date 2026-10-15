from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from links import audit_tree, rewrite_tree


def write(root: Path, relative: str, content: str = "") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class RewriteTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="wwl-links-test-")
        self.stage = Path(self.temp.name)
        self.mapping = [
            {"old": "TBM/com/00-首页.md", "new": "计算机/00-首页.md", "sha256": "a", "action": "move", "role": "moc"},
            {"old": "TBM/com/01-顺序.md", "new": "计算机/01-顺序.md", "sha256": "b", "action": "move", "role": "moc"},
            {"old": "TBM/com/计算机知识/语言/C++.md", "new": "计算机/语言/C++.md", "sha256": "c", "action": "move", "role": "course"},
            {"old": "TBM/com/计算机知识/语言/A (B).md", "new": "计算机/语言/A (B).md", "sha256": "d", "action": "move", "role": "course"},
            {"old": "TBM/com/_labs/README.md", "new": "计算机/实验/README.md", "sha256": "e", "action": "move", "role": "lab"},
            {"old": "TBM/数学/README.md", "new": "数学/README.md", "sha256": "f", "action": "move", "role": "moc"},
            {"old": "TBM/数学/旧报告.md", "new": "历史/旧报告.md", "sha256": "g", "action": "move", "role": "historical"},
            {"old": "TBM/AI/指南.md", "new": "AI/指南.md", "sha256": "h", "action": "move", "role": "course"},
            {"old": "TBM/AI/图.png", "new": "AI/assets/图.png", "sha256": "i", "action": "move", "role": "asset"},
            {"old": "TBM/AI/地图.canvas", "new": "AI/地图.canvas", "sha256": "j", "action": "move", "role": "navigation"},
            {"old": "AGENTS.md", "new": "AGENTS.md", "sha256": "k", "action": "retain", "role": "governance"},
            {"old": "TBM/计算机知识/Kali/00-首页.md", "new": "计算机知识/Kali/00-首页.md", "sha256": "l", "action": "move", "role": "navigation"},
            {"old": "TBM/计算机知识/Kali/01-工具.md", "new": "计算机知识/Kali/01-工具.md", "sha256": "m", "action": "move", "role": "content"},
        ]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_rewrites_wiki_alias_embed_frontmatter_and_skips_code(self) -> None:
        write(self.stage, "计算机/00-首页.md", """---
related: "[[计算机知识/语言/C++#标题|课程]]"
---
| [[计算机知识/语言/C++#标题\\|别名]] |
![[AI/图.png]]
`[[计算机知识/语言/C++]]`
<!-- [[计算机知识/语言/C++]] -->
```md
[[计算机知识/语言/C++]]
```
""")
        write(self.stage, "计算机/语言/C++.md", "# 标题\n")
        write(self.stage, "AI/assets/图.png", "image")
        report = rewrite_tree(self.stage, self.mapping)
        result = (self.stage / "计算机/00-首页.md").read_text(encoding="utf-8")
        self.assertIn("[[计算机/语言/C++#标题|课程]]", result)
        self.assertIn("[[计算机/语言/C++#标题\\|别名]]", result)
        self.assertIn("![[AI/assets/图.png]]", result)
        self.assertEqual(result.count("[[计算机知识/语言/C++]]"), 3)
        self.assertEqual(report["references_changed"], 3)

    def test_markdown_relative_encoding_parentheses_and_reference_definition(self) -> None:
        write(self.stage, "AI/指南.md", """[课程](../com/计算机知识/语言/C++.md#标题)
[空格](../com/计算机知识/语言/A%20%28B%29.md "title")
[ref]: <../com/计算机知识/语言/C++.md#标题> "Title"
""")
        write(self.stage, "计算机/语言/C++.md", "# 标题\n")
        write(self.stage, "计算机/语言/A (B).md", "# A\n")
        report = rewrite_tree(self.stage, self.mapping)
        result = (self.stage / "AI/指南.md").read_text(encoding="utf-8")
        self.assertIn("[课程](../计算机/语言/C++.md#标题)", result)
        self.assertIn("[空格](../计算机/语言/A%20%28B%29.md \"title\")", result)
        self.assertIn("[ref]: <../计算机/语言/C++.md#标题> \"Title\"", result)
        self.assertEqual(report["references_changed"], 3)

    def test_markdown_escaped_spaces_and_parentheses_resolve(self) -> None:
        write(self.stage, "AI/指南.md", r"[空格](../com/计算机知识/语言/A\ \(B\).md)" + "\n")
        write(self.stage, "计算机/语言/A (B).md", "# A\n")
        report = rewrite_tree(self.stage, self.mapping)
        self.assertEqual(
            (self.stage / "AI/指南.md").read_text(),
            "[空格](../计算机/语言/A (B).md)\n",
        )
        self.assertEqual(report["references_changed"], 1)

    def test_com_root_navigation_and_unique_readme_resolution(self) -> None:
        write(self.stage, "计算机/01-顺序.md", "[[00-首页|首页]] [[_labs/README|同目录优先]]")
        write(self.stage, "计算机/00-首页.md", "# 首页\n")
        write(self.stage, "计算机/实验/README.md", "# 实验\n")
        write(self.stage, "数学/README.md", "# 数学\n")
        rewrite_tree(self.stage, self.mapping)
        result = (self.stage / "计算机/01-顺序.md").read_text(encoding="utf-8")
        self.assertEqual(result, "[[计算机/00-首页|首页]] [[计算机/实验/README|同目录优先]]")

    def test_explicit_wrong_directory_is_not_basename_fallback(self) -> None:
        write(self.stage, "AI/指南.md", "[[错误目录/C++|保留]] [[C++|唯一stem]]")
        write(self.stage, "计算机/语言/C++.md", "# 标题\n")
        rewrite_tree(self.stage, self.mapping)
        result = (self.stage / "AI/指南.md").read_text(encoding="utf-8")
        self.assertEqual(result, "[[错误目录/C++|保留]] [[计算机/语言/C++|唯一stem]]")

    def test_historical_and_original_entries_are_never_rewritten(self) -> None:
        write(self.stage, "历史/旧报告.md", "[[AI/指南]]")
        write(self.stage, "AI/指南.md", "# Guide\n")
        write(self.stage, "AGENTS.md", "[[AI/指南]]")
        report = rewrite_tree(self.stage, self.mapping)
        self.assertEqual((self.stage / "历史/旧报告.md").read_text(), "[[AI/指南]]")
        self.assertEqual((self.stage / "AGENTS.md").read_text(), "[[AI/指南]]")
        self.assertEqual({item["role"] for item in report["preserved"]}, {"historical", "governance"})

    def test_many_old_paths_may_merge_and_new_only_page_uses_new_space(self) -> None:
        mapping = self.mapping + [
            {"old": "TBM/副本/C++.md", "new": "计算机/语言/C++.md", "sha256": "c", "action": "merge", "role": "content"},
        ]
        write(self.stage, "计算机/语言/C++.md", "# 标题\n")
        write(self.stage, "新导航.md", "[[计算机/语言/C++|已经正确]] [[不存在/C++|不回退]]")
        report = rewrite_tree(self.stage, mapping)
        self.assertEqual(
            (self.stage / "新导航.md").read_text(),
            "[[计算机/语言/C++|已经正确]] [[不存在/C++|不回退]]",
        )
        self.assertEqual(report["references_changed"], 0)

    def test_canvas_file_nodes_are_rewritten_only(self) -> None:
        canvas = {"nodes": [
            {"id": "a", "type": "file", "file": "TBM/com/计算机知识/语言/C++.md"},
            {"id": "b", "type": "text", "text": "[[计算机知识/语言/C++]]"},
        ], "edges": []}
        write(self.stage, "AI/地图.canvas", json.dumps(canvas, ensure_ascii=False))
        write(self.stage, "计算机/语言/C++.md", "# 标题\n")
        report = rewrite_tree(self.stage, self.mapping)
        result = json.loads((self.stage / "AI/地图.canvas").read_text())
        self.assertEqual(result["nodes"][0]["file"], "计算机/语言/C++.md")
        self.assertEqual(result["nodes"][1]["text"], "[[计算机知识/语言/C++]]")
        self.assertEqual(report["references_changed"], 1)

    def test_kali_package_uses_its_distinct_old_logical_root(self) -> None:
        write(self.stage, "计算机知识/Kali/00-首页.md", "[[计算机知识/Kali/01-工具|工具]]")
        write(self.stage, "计算机知识/Kali/01-工具.md", "# 工具\n")
        report = rewrite_tree(self.stage, self.mapping)
        self.assertEqual(
            (self.stage / "计算机知识/Kali/00-首页.md").read_text(),
            "[[计算机知识/Kali/01-工具|工具]]",
        )
        # It resolves through the mapping, but its final spelling is already
        # correct and therefore does not need a textual change.
        self.assertEqual(report["references_changed"], 0)


class AuditTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="wwl-audit-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_audit_positive_negative_anchors_images_and_fences(self) -> None:
        write(self.root, "计算机知识/good.md", "# 正确标题\n段落 ^block-1\n[[#本页不存在]]\n")
        write(self.root, "assets/good image.png", "x")
        write(self.root, "active.md", """[[计算机知识/good#正确标题]]
[[计算机知识/good#错误标题]]
[[错误目录/good]]
![[assets/missing.png]]
![ok](assets/good%20image.png)
`[[no-inline]]`
<!-- [[no-comment]] -->
```md
[[no-fence]]
```
~~~python
unclosed
""")
        report = audit_tree(self.root)
        self.assertEqual(report["counts"]["anchors"], 2)
        self.assertEqual(report["counts"]["missing"], 1)
        self.assertEqual(report["counts"]["images"], 1)
        self.assertEqual(report["counts"]["fences"], 1)
        self.assertEqual(report["missing"][0]["target"], "错误目录/good")

    def test_slashless_duplicate_is_ambiguous_but_sibling_readme_wins(self) -> None:
        write(self.root, "a/README.md", "# A\n")
        write(self.root, "b/README.md", "# B\n")
        write(self.root, "a/page.md", "[[README]]\n")
        write(self.root, "page.md", "[[README]]\n")
        report = audit_tree(self.root)
        self.assertEqual(report["counts"]["ambiguous"], 1)
        self.assertEqual(report["ambiguous"][0]["path"], "page.md")

    def test_invalid_visible_json_and_canvas_and_historical_scope(self) -> None:
        write(self.root, "data.json", "{")
        write(self.root, "bad.canvas", "[]")
        write(self.root, "历史报告/old.md", "[[missing]]")
        write(self.root, ".secret/data.json", "{")
        report = audit_tree(self.root)
        self.assertEqual(report["counts"]["json"], 1)
        self.assertEqual(report["counts"]["canvas"], 1)
        self.assertEqual(report["historical_counts"]["missing"], 1)
        self.assertNotIn(".secret/data.json", str(report))

    def test_original_and_governance_diagnostics_are_not_counted_active(self) -> None:
        write(self.root, "Clippings/raw.md", "[[missing-original]]\n")
        write(self.root, "AGENTS.md", "[[missing-governance]]\n")
        report = audit_tree(self.root)
        self.assertEqual(report["active_counts"]["missing"], 0)
        self.assertEqual(report["scope_counts"]["missing"]["original"], 1)
        self.assertEqual(report["scope_counts"]["missing"]["governance"], 1)

    def test_footnote_is_not_reference_definition_and_wikilinks_are_root_relative(self) -> None:
        write(self.root, "TaskNotes/Views/tasks.base", "filters: []\n")
        write(
            self.root,
            "TaskNotes/start.md",
            "[^S01]: [Official docs](https://example.com/a_(b))\n"
            "[[TaskNotes/Views/tasks.base|view]]\n",
        )
        report = audit_tree(self.root)
        self.assertEqual(report["counts"]["missing"], 0)
        self.assertEqual(report["counts"]["ambiguous"], 0)

    def test_dotted_note_titles_try_exact_file_then_markdown_suffix(self) -> None:
        write(
            self.root,
            "AI/index.md",
            "[[AI/04-llama.cpp构建后端与调用链]]\n"
            "[[AI/evaluation-report.template]]\n",
        )
        write(self.root, "AI/04-llama.cpp构建后端与调用链.md", "# llama.cpp\n")
        write(self.root, "AI/evaluation-report.template.md", "# template\n")
        report = audit_tree(self.root)
        self.assertEqual(report["counts"]["missing"], 0)

    def test_slashless_regular_file_resolves_only_as_exact_sibling(self) -> None:
        write(
            self.root,
            "lab/index.md",
            "[[05-Python差异断言.py]]\n"
            "[[06-JavaScript差异断言.js]]\n"
            "[[错误目录/05-Python差异断言.py]]\n",
        )
        write(self.root, "lab/05-Python差异断言.py", "pass\n")
        write(self.root, "lab/06-JavaScript差异断言.js", "export {};\n")
        report = audit_tree(self.root)
        self.assertEqual(report["counts"]["missing"], 1)
        self.assertEqual(report["missing"][0]["target"], "错误目录/05-Python差异断言.py")

    def test_exact_dotted_file_wins_over_same_title_markdown_note(self) -> None:
        mapping = [
            {"old": "TBM/lab/index.md", "new": "lab/index.md", "action": "move", "role": "navigation"},
            {"old": "TBM/lab/tool.py", "new": "lab/bin/tool.py", "action": "move", "role": "code"},
            {"old": "TBM/lab/tool.py.md", "new": "lab/notes/tool.py.md", "action": "move", "role": "content"},
        ]
        write(self.root, "lab/index.md", "[[tool.py]]\n")
        write(self.root, "lab/bin/tool.py", "pass\n")
        write(self.root, "lab/notes/tool.py.md", "# tool.py note\n")
        report = rewrite_tree(self.root, mapping)
        self.assertEqual((self.root / "lab/index.md").read_text(), "[[lab/bin/tool.py]]\n")
        self.assertEqual(report["references_changed"], 1)

    def test_html_code_link_is_inactive_but_adjacent_real_link_is_audited(self) -> None:
        write(self.root, "real.md", "# Real\n")
        write(
            self.root,
            "reference.md",
            '| Link | <code>related: "[[Other Note]]"</code> | [[real]] [[missing-real]] |\n',
        )
        report = audit_tree(self.root)
        self.assertEqual(report["counts"]["missing"], 1)
        self.assertEqual(report["missing"][0]["target"], "missing-real")
        self.assertNotIn("Other Note", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
