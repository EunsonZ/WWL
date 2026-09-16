from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from validate_import import (
    audit_canvas_contracts,
    audit_hash_manifest,
    audit_path_collisions,
    audit_static_task_samples,
    audit_table_pipes,
    audit_tasknotes_preservation,
    audit_teaching_fixtures,
    classify_diagnostics,
    collect_link_diagnostics,
    diagnostic,
    fingerprint,
    find_fragment_root,
    load_baseline,
    run_format_checker,
)


def write(root: Path, relative: str, content: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class ImportValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="wwl-import-validator-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_wrong_directory_does_not_fall_back_and_fence_is_inactive(self) -> None:
        write(self.root, "right/good.md", "# Good\n")
        write(
            self.root,
            "page.md",
            "[[wrong/good]]\n```md\n[[missing-in-fence]]\n```\n",
        )
        diagnostics, _ = collect_link_diagnostics(self.root)
        missing = [item for item in diagnostics if item["rule"] == "link.missing"]
        self.assertEqual(
            [(item["path"], item["target"], item["line"]) for item in missing],
            [("page.md", "wrong/good", 1)],
        )

    def test_active_task_constructs_are_detected_but_fenced_examples_are_not(self) -> None:
        good = write(
            self.root,
            "samples/good.md",
            "```yaml\ntags:\n  - task\n```\n```md\n![[TaskNotes/Views/tasks-default.base]]\n```\n",
        )
        bad = write(
            self.root,
            "samples/bad.md",
            "---\ntags:\n  - task\n---\n![[TaskNotes/Views/tasks-default.base]]\n",
        )
        diagnostics = audit_static_task_samples(
            self.root,
            [good.relative_to(self.root).as_posix(), bad.relative_to(self.root).as_posix()],
        )
        self.assertEqual(
            {item["rule"] for item in diagnostics},
            {"tasknotes.active_task_tag", "tasknotes.dynamic_task_embed"},
        )
        self.assertTrue(all(item["path"] == "samples/bad.md" for item in diagnostics))

    def test_canvas_checks_exact_file_node_ids_and_edge_endpoints(self) -> None:
        write(self.root, "folder/Good.md", "# Good\n")
        canvas = {
            "nodes": [
                {"id": "a", "type": "file", "file": "Folder/Good.md"},
                {"id": "a", "type": "text", "text": "duplicate"},
            ],
            "edges": [
                {"id": "edge", "fromNode": "a", "toNode": "missing"},
                {"id": "edge", "fromNode": "a", "toNode": "a"},
            ],
        }
        write(self.root, "map.canvas", json.dumps(canvas))
        diagnostics = audit_canvas_contracts(self.root)
        self.assertEqual(
            {item["rule"] for item in diagnostics},
            {
                "canvas.file_target",
                "canvas.node_id",
                "canvas.edge_endpoint",
                "canvas.edge_id",
            },
        )
        self.assertIn("Folder/Good.md", {item["target"] for item in diagnostics})

    def test_exact_exception_cannot_hide_another_target_or_line(self) -> None:
        accepted = diagnostic(
            "link.missing", "fixture.md", "old-target", line=3, reason="missing"
        )
        changed_target = diagnostic(
            "link.missing", "fixture.md", "new-target", line=3, reason="missing"
        )
        changed_line = diagnostic(
            "link.missing", "fixture.md", "old-target", line=4, reason="missing"
        )
        classified = classify_diagnostics(
            [accepted, changed_target, changed_line], [], {fingerprint(accepted)}
        )
        self.assertEqual(classified["intentional"], [accepted])
        self.assertEqual(
            {(item["target"], item["line"]) for item in classified["new"]},
            {("new-target", 3), ("old-target", 4)},
        )

    def test_known_baseline_is_exact_and_cannot_suppress_integrity_rules(self) -> None:
        known_link = diagnostic(
            "link.case_mismatch", "original.md", "agents.md", line=17, reason="reference_case"
        )
        same = dict(known_link)
        different_reason = dict(known_link, reason="missing")
        canvas = diagnostic(
            "canvas.file_target", "map.canvas", "missing.md", reason="missing_exact_file_target"
        )
        classified = classify_diagnostics(
            [same, different_reason, canvas], [known_link, canvas], set()
        )
        self.assertEqual(classified["known"], [same])
        self.assertEqual(
            {item["rule"] for item in classified["new"]},
            {"link.case_mismatch", "canvas.file_target"},
        )

    def test_full_path_case_and_nfc_collisions_are_reported(self) -> None:
        composed = "资料/Café.md"
        decomposed = "资料/Cafe\u0301.md"
        diagnostics = audit_path_collisions([composed, decomposed, "A/Note.md", "a/note.md"])
        self.assertEqual(len(diagnostics), 2)
        self.assertTrue(all(item["rule"] == "path.case_nfc_collision" for item in diagnostics))

    def test_table_alias_pipe_only_flags_active_unescaped_alias(self) -> None:
        write(self.root, "good.md", "# Good\n")
        write(
            self.root,
            "table.md",
            "| formula | link |\n"
            "| --- | --- |\n"
            "| $|x|$ | [[good\\|escaped]] |\n"
            "| active | [[good|bad]] |\n"
            "```md\n| [[good|fenced]] | x |\n```\n",
        )
        diagnostics = audit_table_pipes(self.root)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["target"], "good|bad")
        self.assertEqual(diagnostics[0]["line"], 4)

    def test_callouts_inline_aliases_and_isolated_math_pipes_are_not_tables(self) -> None:
        write(
            self.root,
            "ordinary.md",
            "> [!note] [[A|一]]、[[B|二]]、[[C|三]]、[[D|四]]、[[E|五]]\n"
            "普通段落 [[A|一]] 和 [[B|二]] 不构成表格。\n"
            "孤立数学段落：|x| + |y| >= 0。\n",
        )
        self.assertEqual(audit_table_pipes(self.root), [])

    def test_borderless_markdown_table_reports_real_alias_pipe_error(self) -> None:
        write(
            self.root,
            "borderless.md",
            "name | destination\n"
            ":--- | ---:\n"
            "course | [[target|alias]]\n",
        )
        diagnostics = audit_table_pipes(self.root)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["path"], "borderless.md")
        self.assertEqual(diagnostics[0]["line"], 3)
        self.assertEqual(diagnostics[0]["target"], "target|alias")

    def test_unescaped_alias_in_table_header_is_still_detected(self) -> None:
        write(
            self.root,
            "header.md",
            "[[target|alias]] | status\n"
            "--- | ---\n"
            "target | ready\n",
        )
        diagnostics = audit_table_pipes(self.root)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["line"], 1)
        self.assertEqual(diagnostics[0]["target"], "target|alias")

    def test_fragment_root_falls_back_to_artifacts_and_baseline_parent(self) -> None:
        work = self.root / "work"
        artifacts = work / "artifacts"
        artifacts.mkdir(parents=True)
        write(artifacts, "teaching-fixtures.json", "{}")
        baseline = artifacts / "known-diagnostics.json"
        baseline.write_text("{}")
        self.assertEqual(find_fragment_root(work, baseline), artifacts.resolve())
        self.assertEqual(find_fragment_root(artifacts, baseline), artifacts.resolve())

    def test_teaching_manifest_registers_two_broken_links_one_island_and_three_snippets(self) -> None:
        write(self.root, "fixtures/a.md", "[[missing-a]]\n")
        write(self.root, "fixtures/b.md", "[[missing-b]]\n")
        write(self.root, "fixtures/island.md", "# Island\n")
        entries = [
            {
                "file": "fixtures/a.md",
                "target": "[[missing-a]] at line 1",
                "reason": "intentional unresolved-link target",
            },
            {
                "file": "fixtures/b.md",
                "target": "[[missing-b]] at line 1",
                "reason": "intentional unresolved-link target",
            },
            {
                "file": "fixtures/island.md",
                "target": "whole note intentionally has no internal incoming or outgoing links",
                "reason": "graph exercise",
            },
        ]
        for index in range(3):
            content = f"snippet-{index}\n"
            relative = f"fixtures/snippet-{index}.md"
            write(self.root, relative, content)
            entries.append(
                {
                    "file": relative,
                    "target": "lines 1-1: exact fixture",
                    "snippet_sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "reason": "exact snippet",
                }
            )
        for index in range(4):
            relative = f"Obsidian知识/Tasks/sample-{index}.md"
            write(self.root, relative, "```yaml\ntags: [task]\n```\n")
            entries.append(
                {
                    "file": relative,
                    "target": "fenced YAML block",
                    "reason": "static TaskNotes sample",
                }
            )
        diagnostics, intentional = audit_teaching_fixtures(
            self.root, {"entries": entries}
        )
        self.assertEqual(diagnostics, [])
        self.assertEqual(len(intentional), 2)

    def test_tasknotes_requires_exact_eight_files_and_original_hashes(self) -> None:
        inventory = {}
        for index in range(8):
            relative = f"TaskNotes/file-{index}.base"
            path = write(self.root, relative, f"value: {index}\n")
            inventory[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(audit_tasknotes_preservation(self.root, inventory), [])
        write(self.root, "TaskNotes/file-0.base", "changed: true\n")
        diagnostics = audit_tasknotes_preservation(self.root, inventory)
        self.assertEqual([item["rule"] for item in diagnostics], ["tasknotes.hash"])

    def test_hash_manifest_detects_changed_preserved_target(self) -> None:
        target = write(self.root, "original/raw.md", "preserved\n")
        manifest = self.root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "target": "original/raw.md",
                            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        }
                    ]
                }
            )
        )
        self.assertEqual(
            audit_hash_manifest(
                self.root,
                manifest,
                entries_key="entries",
                target_key="target",
                rule_prefix="original",
            ),
            [],
        )
        target.write_text("changed\n")
        diagnostics = audit_hash_manifest(
            self.root,
            manifest,
            entries_key="entries",
            target_key="target",
            rule_prefix="original",
        )
        self.assertEqual([item["rule"] for item in diagnostics], ["original.hash"])

    def test_ruby_checker_owns_base_yaml_syntax(self) -> None:
        write(self.root, "broken.base", "filters: [\n")
        script = Path(__file__).resolve().with_name("check_formats.rb")
        diagnostics, result = run_format_checker(self.root, script)
        self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual([item["rule"] for item in diagnostics], ["format.syntax"])
        self.assertEqual(diagnostics[0]["path"], "broken.base")

    def test_baseline_rejects_globs_and_requires_complete_fingerprint(self) -> None:
        baseline = self.root / "known-diagnostics.json"
        baseline.write_text(
            json.dumps(
                {
                    "known_diagnostics": [
                        {
                            "rule": "link.missing",
                            "path": "Clippings/*",
                            "target": "missing",
                            "line": 1,
                            "reason": "missing",
                        },
                        {
                            "rule": "link.missing",
                            "path": "original.md",
                            "target": "chenqin\u200b",
                            "line": 7,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        inventory, known, issues = load_baseline(baseline)
        self.assertEqual(inventory, {})
        self.assertEqual(known, [])
        self.assertEqual(len(issues), 2)
        self.assertTrue(all(item["rule"] == "baseline.invalid" for item in issues))


if __name__ == "__main__":
    unittest.main()
