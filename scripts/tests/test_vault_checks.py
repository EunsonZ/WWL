"""Independent fixtures for the static checker's positive and failure paths."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_mirrors
import check_vault
from links import Index, anchors, audit, references, scan


class VaultFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wwl-checks-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "vault"
        self.root.mkdir()

    def write(self, path, text):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        return dest

    def report(self):
        return audit(self.root)[0]


class LinkTests(VaultFixture):
    def test_t29_workbench_home_resolves_exact_root_readme(self):
        self.write("README.md", "# 学科首页\n")
        self.write("00-工作台/README.md", "[学科首页](../README.md#学科首页)\n[[README#工作台]]\n# 工作台\n")
        report = self.report()
        self.assertFalse(report["issues"])
        self.assertEqual([x["resolved"] for x in report["resolved_links"]],
                         ["00-工作台/README.md", "README.md"])

    def test_t29_ambiguous_short_term_is_not_silently_selected(self):
        self.write("a/词.md", "# A\n")
        self.write("b/词.md", "# B\n")
        self.write("entry.md", "[[词]]\n[[wrong/词]]\n")
        report = self.report()
        self.assertEqual([x["rule"] for x in report["issues"]], ["link_ambiguous", "link_missing"])
        self.assertEqual([x["severity"] for x in report["issues"]], ["review", "error"])

    def test_t29_moved_note_cannot_use_old_relative_path(self):
        self.write("old/topic.md", "# 目标\n")
        self.write("moved/deep/note.md", "[old](../topic.md)\n[correct](../../old/topic.md#目标)\n")
        report = self.report()
        self.assertEqual([x["target"] for x in report["issues"]], ["../topic.md"])
        self.assertEqual(report["resolved_links"][0]["resolved"], "old/topic.md")

    def test_exact_wiki_root_relative_and_local_relative(self):
        self.write("a/topic.md", "# A\n")
        self.write("b/a/topic.md", "# B\n")
        self.write("b/note.md", "[[a/topic#A]]\n[[./a/topic#B]]\n[a](a/topic.md#B)\n")
        report = self.report()
        self.assertFalse(report["issues"])
        self.assertEqual([x["resolved"] for x in report["resolved_links"]], ["a/topic.md", "b/a/topic.md", "b/a/topic.md"])

    def test_markdown_missing_name_does_not_fall_back_to_global(self):
        self.write("a/topic.md", "# A\n")
        self.write("b/n.md", "[bad](topic.md)\n[[topic]]\n")
        report = self.report()
        self.assertEqual(len(report["issues"]), 1)
        self.assertEqual(report["issues"][0]["kind"], "markdown")

    def test_headings_blocks_setext_slug_and_duplicate_slug(self):
        self.write("target.md", "# Hello `world`!\n# Hello `world`!\nSetext\n======\nparagraph ^block-1\n````md\n# Hidden\ntext ^hidden\n````\n")
        self.write("n.md", "[[target#Hello world!]]\n[[target#Setext]]\n[[target#^block-1]]\n[a](target.md#hello-world-1)\n[[target#Hidden]]\n[[target#^hidden]]\n")
        report = self.report()
        self.assertEqual([x["target"] for x in report["issues"]], ["target#Hidden", "target#^hidden"])

    def test_aliases_display_alias_and_table_pipe(self):
        self.write("a/topic.md", '---\naliases:\n  - 概念别名\n  - "第二别名"\n---\n# 好标题\n')
        self.write("n.md", "[[概念别名#好标题|显示名]]\n| [[第二别名\\|表格名称]] |\n")
        report = self.report()
        self.assertEqual({x["rule"] for x in report["issues"]}, {"alias_target_needs_ui_review"})
        self.assertEqual({x["resolved"] for x in report["resolved_links"]}, {"a/topic.md"})

    def test_table_alias_requires_escape_but_non_table_and_code_do_not(self):
        self.write("target.md", "# target\n")
        self.write("n.md", """| name | target |
| --- | --- |
| ok | [[target\\|display]] |
| bad | [[target|display]] |

normal [[target|display]] text
| value | $a|b$ |
`| [[target|code]] |`
```md
| [[target|fence]] |
```
""")
        report = self.report()
        hits = [x for x in report["issues"] if x["rule"] == "table_wiki_alias_unescaped"]
        self.assertEqual([(x["path"], x["line"] ) for x in hits], [("n.md", 4)])

    def test_table_alias_requires_real_context_and_accepts_no_outer_pipe(self):
        self.write("target.md", "# target\n")
        self.write("n.md", """H | V
--- | ---
[[target|display]] | x

| lone | [[target|display]] |

| H | V |
| -- | -- |
| [[target|display]] | x |

| H | V |

| --- | --- |
| [[target|display]] | x |
""")
        hits = [x for x in self.report()["issues"] if x["rule"] == "table_wiki_alias_unescaped"]
        self.assertEqual([(x["path"], x["line"]) for x in hits], [("n.md", 3)])

    def test_inline_alias_list_and_dotted_note(self):
        self.write("a/llama.cpp.md", '---\naliases: ["别名 A", \'别名 B\', plain]\n---\n')
        self.write("n.md", "[[别名 A]] [[别名 B]] [[plain]] [[a/llama.cpp]]")
        self.assertEqual(len(self.report()["issues"]), 3)

    def test_markdown_extensionless_target_is_only_same_local_candidate(self):
        self.write("a/topic.md", "# Topic\n")
        self.write("a/n.md", "[topic](topic)\n[missing](../wrong/topic)\n")
        report = self.report()
        self.assertEqual(report["resolved_links"][0]["resolved"], "a/topic.md")
        self.assertEqual([x["target"] for x in report["issues"]], ["../wrong/topic"])

    def test_nested_heading_and_nonstandard_block_id_are_explicit_review(self):
        self.write("t.md", "# Parent\n## Child\nparagraph ^with_underscore\n")
        self.write("n.md", "[[t#Parent#Child]]\n[[t#^with_underscore]]\n")
        issues = self.report()["issues"]
        self.assertEqual({x["rule"] for x in issues}, {"heading_path_not_checked", "block_id_syntax_not_checked"})
        self.assertEqual({x["severity"] for x in issues}, {"review"})

    def test_attachments_percent_encoding_and_balanced_destinations(self):
        self.write("assets/a (b).png", "fake attachment")
        self.write("assets/x.py", "pass\n")
        self.write("n.md", "![one](assets/a%20(b).png)\n![two](<assets/a (b).png> \"title\")\n![[assets/a (b).png|200]]\n[[assets/x.py]]\n![[assets/missing.png]]")
        report = self.report()
        self.assertEqual([x["target"] for x in report["issues"]], ["assets/missing.png"])
        self.assertEqual(len(report["resolved_links"]), 4)

    def test_teaching_code_comments_and_escaped_links_are_not_live(self):
        self.write("n.md", """`[[inline]]` `` `[[long-inline]]` ``
`multiline
[[not-live]]`
<!--
```
[[comment]]
-->
%% [[obsidian-comment]] %%
````markdown
<!-- code-sync: ./missing.py -->
```md
[[example]]
```
````
\\[[escaped]]
[[real-missing]]
""")
        report = self.report()
        self.assertEqual([x["target"] for x in report["issues"]], ["real-missing"])

    def test_fence_close_with_info_does_not_close(self):
        self.write("n.md", "```md\n[[hidden]]\n```not-a-close\n[[still-hidden]]\n")
        report = self.report()
        self.assertEqual([x["rule"] for x in report["issues"]], ["unclosed_fence"])

    def test_quote_and_indented_container_fences_are_not_live_links(self):
        self.write("n.md", "> ~~~md\n> [[quoted-example]]\n> ~~~\n\n1. example:\n    ~~~md\n    [[list-example]]\n    ~~~\n")
        self.assertEqual(self.report()["checked"], 0)
        self.assertFalse(self.report()["issues"])

    def test_dangling_backtick_cannot_consume_another_paragraph(self):
        self.write("n.md", "A dangling ` character.\n\n[[real-missing]]\n\n`another span`\n")
        report = self.report()
        self.assertEqual(report["checked"], 1)
        self.assertEqual(report["issues"][0]["target"], "real-missing")

    def test_parenthesis_inside_markdown_quoted_title_is_not_a_destination(self):
        self.write("n.md", '[bad](missing.md "A (title")\n')
        self.assertEqual(self.report()["issues"][0]["target"], "missing.md")

    def test_reference_definitions_and_footnotes(self):
        self.write("t.md", "# Title\n")
        self.write("n.md", "[example][ref]\n[ref]: t.md#Title \"optional title\"\n[^1]: [Source](https://example.com/a_(b))\n")
        report = self.report()
        self.assertFalse(report["issues"])
        self.assertEqual(report["resolved_links"][0]["resolved"], "t.md")

    def test_html_code_and_multiline_code_do_not_define_anchors(self):
        self.write("target.md", "# 1\\. Escaped\n`multiline\n# fake heading\ntext ^fake\n`\n")
        self.write("n.md", '<code>[[Other Note]]</code>\n<pre>[[Example]]</pre>\n'
                   '[[target#1. Escaped]]\n[[target#fake heading]]\n[[target#^fake]]\n')
        report = self.report()
        self.assertEqual([x["target"] for x in report["issues"]], ["target#fake heading", "target#^fake"])

    def test_explicit_typo_and_case_remain_diagnostics(self):
        self.write("a/Topic.md", "# title\n")
        self.write("n.md", "[[a/topic]]\n[[wrong/Topic]]\n")
        self.assertEqual([x["rule"] for x in self.report()["issues"]],
                         ["link_case_or_unicode_mismatch", "link_missing"])

    def test_symlink_is_never_read_or_used_as_resolved_file(self):
        self.write("a.md", "content")
        (self.root / "linked.md").symlink_to(self.root / "a.md")
        self.write("n.md", "[[linked]]")
        self.assertEqual({x["rule"] for x in self.report()["issues"]},
                         {"symlink_not_read", "link_missing"})

    def test_traversal_is_reported(self):
        self.write("n.md", "[outside](../../outside.md)")
        self.assertEqual(self.report()["issues"][0]["rule"], "link_outside_root")

    def test_historical_and_governance_links_are_not_exempt(self):
        self.write("Logs/history.md", "[[missing-history]]")
        self.write("AGENTS.md", "[[missing-governance]]")
        self.assertEqual(len(self.report()["issues"]), 2)


class MirrorTests(VaultFixture):
    def test_matching_source_and_final_newline_policy(self):
        self.write("a.py", "print(1)")
        self.write("n.md", "<!-- code-sync: ./a.py -->\n```python\nprint(1)\n```\n")
        report = check_mirrors.check(self.root)
        self.assertEqual(report["checked"], 1)
        self.assertFalse(report["issues"])

    def test_mirror_preserves_crlf_and_detects_line_ending_mismatch(self):
        source = self.write("a.py", "pass\n")
        source.write_bytes(b"pass\r\n")
        note = self.write("n.md", "<!-- code-sync: ./a.py -->\n```python\npass\n```\n")
        self.assertEqual(check_mirrors.check(self.root)["issues"][0]["rule"], "mirror_mismatch")
        note.write_bytes(b"<!-- code-sync: ./a.py -->\r\n```python\r\npass\r\n```\r\n")
        self.assertFalse(check_mirrors.check(self.root)["issues"])

    def test_source_mismatch_blank_line_missing_and_no_fence(self):
        self.write("a.py", "pass\n\n")
        self.write("n.md", "<!-- code-sync: ./a.py -->\n```python\npass\n```\n<!-- code-sync: ./missing.py -->\n```python\npass\n```\n<!-- code-sync: ./a.py -->\nNo fence\n")
        report = check_mirrors.check(self.root)
        self.assertEqual([x["rule"] for x in report["issues"]],
                         ["mirror_mismatch", "mirror_source_missing", "mirror_missing_fence"])

    def test_inline_and_fenced_markers_are_not_contracts(self):
        self.write("n.md", '`<!-- code-sync: ./missing.py -->`\n'
                   'Use <!-- code-sync: ./missing.py --> in this sentence.\n'
                   '````md\n<!-- code-sync: ./missing.py -->\n```py\npass\n```\n````\n')
        report = check_mirrors.check(self.root)
        self.assertEqual(report, {"checked": 0, "markers": 0, "issues": []})

    def test_longer_closing_fence_is_accepted(self):
        self.write("a.py", "pass\n")
        self.write("n.md", "<!-- code-sync: ./a.py -->\n~~~python\npass\n~~~~~\n")
        self.assertFalse(check_mirrors.check(self.root)["issues"])

    def test_explicit_wrong_source_directory_has_no_basename_fallback(self):
        self.write("a.py", "pass\n")
        self.write("n.md", "<!-- code-sync: wrong/a.py -->\n```python\npass\n```\n")
        self.assertEqual(check_mirrors.check(self.root)["issues"][0]["rule"], "mirror_source_missing")

    def test_source_is_never_imported_or_executed(self):
        self.write("a.py", "raise RuntimeError('MUST NOT EXECUTE')\n")
        self.write("n.md", "<!-- code-sync: ./a.py -->\n```python\nraise RuntimeError('MUST NOT EXECUTE')\n```\n")
        self.assertFalse(check_mirrors.check(self.root)["issues"])

    def test_markdown_template_is_a_supported_canonical_file(self):
        self.write("report.template.md", "# Report\n")
        self.write("n.md", "<!-- code-sync: ./report.template.md -->\n```markdown\n# Report\n```\n")
        self.assertFalse(check_mirrors.check(self.root)["issues"])


class CheckerTests(VaultFixture):
    def test_t1_single_markdown_read_feeds_final_alias_audit_and_mirrors(self):
        self.write("target.md", "---\naliases: [alias-name]\n---\n# Anchor\n")
        self.write("snippet.py", "print(1)\n")
        self.write("n.md", "[[alias-name#Anchor]]\n"
                   "<!-- code-sync: ./snippet.py -->\n"
                   "```python\nprint(1)\n```\n")
        unreadable = self.write("unreadable.md", "# unreadable\n").resolve()
        resolved_root = self.root.resolve()
        original_read_bytes = Path.read_bytes
        reads, seen_notes = [], []

        def guarded_read_bytes(path):
            if path.suffix == ".md":
                reads.append(path.relative_to(resolved_root).as_posix())
            if path == unreadable:
                raise OSError("simulated unreadable note")
            return original_read_bytes(path)

        def parsed_aliases(notes, _yaml):
            seen_notes.append(notes)
            return [], {}, {"target.md": ["alias-name"], "n.md": []}

        with mock.patch.object(check_vault, "load_yaml", return_value=object()), \
             mock.patch.object(check_vault, "yaml_check", side_effect=parsed_aliases), \
             mock.patch.object(check_vault, "audit", wraps=check_vault.audit) as audited, \
             mock.patch.object(Path, "read_bytes", guarded_read_bytes):
            report = check_vault.check(self.root)

        self.assertEqual(audited.call_count, 1)
        self.assertIs(audited.call_args.kwargs["notes"], seen_notes[0])
        self.assertEqual(sorted(reads), ["n.md", "target.md", "unreadable.md"])
        self.assertEqual(
            report["resolved_links"],
            [{"path": "n.md", "line": 1, "target": "alias-name#Anchor",
              "resolved": "target.md"}],
        )
        rules = [item["rule"] for item in report["issues"]]
        self.assertEqual(rules.count("note_unreadable"), 1)
        self.assertIn("alias_target_needs_ui_review", rules)
        self.assertNotIn("link_missing_anchor", rules)
        self.assertEqual(report["scope"]["mirrors_checked"], 1)

    def test_missing_yaml_is_partial_or_error_not_pass(self):
        self.write("README.md", "# Home\n")
        with mock.patch.object(check_vault, "load_yaml", return_value=None):
            partial = check_vault.check(self.root)
            required = check_vault.check(self.root, True)
        self.assertEqual(partial["status"], "partial")
        self.assertEqual(required["status"], "failed")
        self.assertEqual(required["layers"]["yaml_properties"], "not_run_missing_PyYAML")

    def test_no_yaml_still_fails_unclosed_frontmatter(self):
        self.write("n.md", "---\naliases: [name]\n")
        with mock.patch.object(check_vault, "load_yaml", return_value=None):
            report = check_vault.check(self.root)
        self.assertIn("frontmatter_unclosed", {x["rule"] for x in report["issues"]})

    def test_safe_json_scope_plugin_presence_and_secret_not_read(self):
        self.write(".obsidian/community-plugins.json", '["demo"]')
        self.write(".obsidian/plugins/demo/manifest.json", '{"id":"demo"}')
        secret = self.write(".obsidian/plugins/demo/data.json", "private malformed data")
        self.write(".obsidian/app.json", "{")
        original = Path.read_text
        def guarded(path, *args, **kwargs):
            if path == secret:
                raise AssertionError("plugin private data was read")
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, "read_text", guarded):
            report = check_vault.check(self.root)
        self.assertIn("config_json_invalid", {x["rule"] for x in report["issues"]})
        self.assertIn("enabled_plugin_file_missing_or_symlink", {x["rule"] for x in report["issues"]})
        self.assertNotIn("private malformed data", json.dumps(report))

    def test_json_duplicates_and_nonfinite_are_rejected(self):
        for value in ('{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', '{"a": 1e999}'):
            with self.assertRaises(ValueError):
                check_vault.strict_json(value)

    def test_templates_config_is_checked(self):
        self.write(".obsidian/templates.json", "{")
        report = check_vault.check(self.root)
        self.assertIn(".obsidian/templates.json", {x["path"] for x in report["issues"] if x["rule"] == "config_json_invalid"})

    def test_dangling_configuration_link_is_diagnosed_without_reading(self):
        self.write(".obsidian/types.json", '{"types":{}}')
        target = self.root.parent / "absent-private-config.json"
        link = self.root / ".obsidian" / "app.json"
        link.symlink_to(target)
        original = Path.read_text

        def guarded(path, *args, **kwargs):
            if path in (link, target):
                raise AssertionError("linked configuration was read")
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", guarded):
            report = check_vault.check(self.root)
        self.assertIn(
            ("config_symlink_not_read", ".obsidian/app.json"),
            {(x["rule"], x["path"]) for x in report["issues"]},
        )
        self.assertFalse(target.exists())

    def test_dangling_configuration_directory_is_diagnosed(self):
        target = self.root.parent / "absent-private-directory"
        (self.root / ".obsidian").symlink_to(target, target_is_directory=True)
        issues, count = check_vault.config_check(self.root, [], None, {}, None)
        linked = {x["path"] for x in issues if x["rule"] == "config_symlink_not_read"}
        self.assertEqual(linked, {
            ".obsidian/" + name + ".json"
            for name in ("app", "appearance", "graph", "types", "templates",
                         "core-plugins", "community-plugins")
        })
        self.assertEqual(count, 0)
        self.assertFalse(target.exists())

    def test_configuration_shapes_and_declared_type_contract(self):
        self.write(".obsidian/app.json", "[]")
        self.write(".obsidian/types.json", '{"types":{"stage":"text", "property":"nonexistent"}}')
        report = check_vault.check(self.root)
        rules = {x["rule"] for x in report["issues"]}
        self.assertTrue({"config_json_invalid", "property_declaration_unknown_type", "property_declaration_contract"}.issubset(rules))
        self.write(".obsidian/types.json", "[]")
        report = check_vault.check(self.root)
        self.assertIn(".obsidian/types.json", {x["path"] for x in report["issues"] if x["rule"] == "config_json_invalid"})

    def test_canvas_file_targets_and_wrong_shape(self):
        self.write("a.md", "# A\n")
        self.write("ok.canvas", json.dumps({"nodes": [{
            "id": "file-a", "type": "file", "file": "a.md", "subpath": "#A",
            "x": 0, "y": 0, "width": 200, "height": 100,
        }]}))
        self.write("bad.canvas", "[]")
        report = check_vault.check(self.root)
        self.assertEqual([x["path"] for x in report["issues"] if x["rule"] == "canvas_invalid"], ["bad.canvas"])

    def test_canvas_optional_collections_extensions_and_order(self):
        self.write("background.png", "image")
        canvas = {
            "metadata": {"extension": "kept"},
            "nodes": [
                {
                    "id": "group", "type": "group",
                    "x": 0, "y": 0, "width": 800, "height": 600,
                    "label": "Group", "background": "background.png",
                    "backgroundStyle": "cover",
                    "extension": {"collapsed": False},
                },
                {
                    "id": "text", "type": "text",
                    "x": 20.0, "y": 30, "width": 200, "height": 100,
                    "text": "**Text**", "color": "#abc",
                },
                {
                    "id": "link", "type": "link",
                    "x": 250, "y": 30, "width": 200, "height": 100,
                    "url": "https://example.com",
                },
            ],
            "edges": [{
                "id": "edge", "fromNode": "text", "toNode": "link",
                "fromSide": "right", "fromEnd": "none",
                "toSide": "left", "toEnd": "arrow",
                "color": "6", "label": "next", "extension": True,
            }],
        }
        original = json.dumps(canvas, ensure_ascii=False)
        path = self.write("extended.canvas", original)
        self.write("empty.canvas", "{}")
        report = check_vault.check(self.root)
        self.assertFalse([x for x in report["issues"] if x["rule"] == "canvas_invalid"])
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_canvas_rejects_invalid_ids_references_geometry_and_types(self):
        def node(node_id, node_type="text", **values):
            result = {
                "id": node_id, "type": node_type,
                "x": 0, "y": 0, "width": 100, "height": 50,
            }
            if node_type == "text":
                result["text"] = "text"
            result.update(values)
            return result

        def edge(edge_id="edge", **values):
            result = {"id": edge_id, "fromNode": "a", "toNode": "b"}
            result.update(values)
            return result

        pair = [node("a"), node("b", x=200)]
        invalid = {
            "bad-nodes-shape.canvas": {"nodes": {}},
            "bad-edges-shape.canvas": {"edges": {}},
            "bad-node-id.canvas": {"nodes": [node("same"), node("same")]},
            "bad-node-geometry.canvas": {"nodes": [node("a", x=True)]},
            "bad-node-fractional-geometry.canvas": {"nodes": [node("a", width=100.5)]},
            "bad-node-type.canvas": {"nodes": [node("a", "video")]},
            "bad-text-node.canvas": {"nodes": [node("a", text=3)]},
            "bad-file-node.canvas": {"nodes": [{
                "id": "a", "type": "file", "x": 0, "y": 0, "width": 100, "height": 50,
            }]},
            "bad-file-subpath.canvas": {"nodes": [{
                "id": "a", "type": "file", "file": "a.md", "subpath": "Heading",
                "x": 0, "y": 0, "width": 100, "height": 50,
            }]},
            "bad-link-node.canvas": {"nodes": [node("a", "link")]},
            "bad-group-node.canvas": {"nodes": [node("a", "group", backgroundStyle="stretch")]},
            "bad-node-color-type.canvas": {"nodes": [node("a", color=1)]},
            "bad-edge-id.canvas": {"nodes": pair, "edges": [edge(), edge()]},
            "bad-edge-reference.canvas": {"nodes": [node("a")], "edges": [edge(toNode="missing")]},
            "bad-edge-fields.canvas": {"nodes": pair, "edges": [edge(fromSide="center", label=3)]},
        }
        for path, data in invalid.items():
            self.write(path, json.dumps(data))
        report = check_vault.check(self.root)
        self.assertEqual(
            {x["path"] for x in report["issues"] if x["rule"] == "canvas_invalid"}, set(invalid),
        )

    @unittest.skipUnless(check_vault.load_yaml() is not None,
                         "PyYAML unavailable; Base syntax checks not run")
    def test_base_yaml_duplicate_keys_are_invalid_without_semantic_execution(self):
        self.write(
            "valid.base",
            "defaults: &defaults\n  type: table\n  limit: 10\n"
            "views:\n  - <<: *defaults\n    limit: 20\n    name: Main\n",
        )
        self.write("duplicate.base", "views: []\nviews: []\n")
        self.write("nested-duplicate.base", "views:\n  - type: table\n    name: First\n    name: Second\n")
        report = check_vault.check(self.root)
        self.assertEqual(
            [x["path"] for x in report["issues"] if x["rule"] == "base_yaml_invalid"],
            ["duplicate.base", "nested-duplicate.base"],
        )
        self.assertEqual(report["layers"]["base_syntax"], "checked_yaml_only")

    def test_t28_checker_does_not_require_change_and_detects_active_dependency(self):
        self.write("README.md", "[Maintenance](CHANGES.md)\n")
        self.write("CHANGES.md", "# Actual results\n")
        self.assertNotIn("link_missing", {x["rule"] for x in check_vault.check(self.root)["issues"]})
        self.write("README.md", "[Required](CHANGE.md)\n")
        self.assertIn("link_missing", {x["rule"] for x in check_vault.check(self.root)["issues"]})

    def test_t27_reruns_are_read_only_and_do_not_duplicate_outputs(self):
        path = self.write("README.md", "Human addition\n")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        first, second = check_vault.check(self.root), check_vault.check(self.root)
        self.assertEqual(first, second)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_output_is_private_new_external_file_and_never_overwrites(self):
        output = self.root.parent / "evidence.json"
        check_vault.write_report({"status": "partial"}, self.root, output)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            check_vault.write_report({}, self.root, output)
        with self.assertRaises(ValueError):
            check_vault.write_report({}, self.root, self.root / "pollution.json")

    def test_cli_help_success_and_failure_examples(self):
        script = Path(check_vault.__file__)
        for name in ("check_vault.py", "check_mirrors.py"):
            help_run = subprocess.run([sys.executable, "-B", str(script.parent / name), "--help"], capture_output=True, text=True)
            self.assertEqual(help_run.returncode, 0)
            self.assertIn("--root", help_run.stdout)
        self.write("README.md", "# home\n")
        ok = subprocess.run([sys.executable, "-B", str(script), "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0)
        self.write("README.md", "[[missing]]\n")
        failed = subprocess.run([sys.executable, "-B", str(script), "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1)
        missing_yaml = subprocess.run([sys.executable, "-B", "-S", str(script), "--root", str(self.root), "--require-yaml"], capture_output=True, text=True)
        self.assertEqual(missing_yaml.returncode, 1)
        self.assertIn("not_run_missing_PyYAML", missing_yaml.stdout)

    @unittest.skipUnless(check_vault.load_yaml() is not None, "PyYAML unavailable; metadata semantic checks not run")
    def test_yaml_properties_valid_invalid_duplicate_and_prerequisites(self):
        yaml = check_vault.load_yaml()
        notes = {"ok.md": '---\nstage: 1\naliases: [name]\nprerequisites: ["[[pre]]"]\n---\n',
                 "bad.md": '---\nstage: true\nsources: wrong\nsubject_note: plain text\n---\n',
                 "duplicate.md": '---\nstage: 1\nstage: 2\n---\n'}
        issues, _, _ = check_vault.yaml_check(notes, yaml)
        self.assertIn("yaml_invalid", {x["rule"] for x in issues})
        self.assertIn("property_link_required", {x["rule"] for x in issues})
        self.assertIn("property_type_conflict", {x["rule"] for x in issues})
        self.assertEqual(len([x for x in issues if x["rule"] == "property_type"]), 2)


    @unittest.skipUnless(check_vault.load_yaml() is not None, "PyYAML unavailable; metadata semantic checks not run")
    def test_iso_date_text_is_representation_review_while_real_conflicts_remain(self):
        notes = {
            "native.md": "---\nupdated: 2026-09-22\ncaptured: 2026-09-22T10:30:00+08:00\nrevision: 2\ncheckpoint: 2026-02-28\n---\n",
            "quoted.md": '---\nupdated: "2026-09-22"\ncaptured: "2026-09-22T10:30:00+08:00"\nrevision: 2026-09-22\ncheckpoint: "2026-02-30"\n---\n',
            "ordinary.md": '---\ntitle: "2026-09-22"\n---\n',
            "ordinary-2.md": "---\ntitle: ordinary text\n---\n",
        }
        issues, _, _ = check_vault.yaml_check(notes, check_vault.load_yaml())
        representations = [x for x in issues if x["rule"] == "property_representation_variant"]
        conflicts = {x["field"] for x in issues if x["rule"] == "property_type_conflict"}
        self.assertEqual({x["field"] for x in representations}, {"updated", "captured"})
        self.assertEqual({x["severity"] for x in representations}, {"review"})
        self.assertEqual(conflicts, {"checkpoint", "revision"})
        self.assertNotIn("title", {x["field"] for x in representations})

    @unittest.skipUnless(check_vault.load_yaml() is not None, "PyYAML unavailable; metadata semantic checks not run")
    def test_template_values_are_pending_without_directory_or_syntax_exemption(self):
        notes = {
            "actual.md": "---\nrating: 5\nmalformed_placeholder: 1\nbroken_placeholder: 2\n---\n",
            "Obsidian知识/90-资源/01-模板/核心模板/placeholders.md": (
                '---\nrating: ""\ncreated: "{{date}} {{time}}"\n'
                'verified_on: "<% tp.date.now(\'YYYY-MM-DD\') %>"\nstage: "{{stage}}"\n---\n'),
            "Obsidian知识/90-资源/01-模板/核心模板/malformed.md": (
                '---\nmalformed_placeholder: "prefix {{date}}"\nbroken_placeholder: "{{date}"\n---\n'),
            "Obsidian知识/90-资源/01-模板/核心模板/duplicate.md": (
                '---\ncreated: "{{date}}"\ncreated: "{{date}}"\n---\n'),
        }
        issues, _, _ = check_vault.yaml_check(notes, check_vault.load_yaml())
        self.assertEqual({x["field"] for x in issues if x["rule"] == "property_template_pending"},
                         {"created", "rating", "stage", "verified_on"})
        self.assertEqual({x["field"] for x in issues if x["rule"] == "property_type_conflict"},
                         {"broken_placeholder", "malformed_placeholder"})
        self.assertNotIn("stage", {x["field"] for x in issues if x["rule"] == "property_type"})
        self.assertEqual({x["path"] for x in issues if x["rule"] == "yaml_invalid"},
                         {"Obsidian知识/90-资源/01-模板/核心模板/duplicate.md"})

    @unittest.skipUnless(check_vault.load_yaml() is not None, "PyYAML unavailable; metadata semantic checks not run")
    def test_declared_dates_are_strict_and_plain_empty_number_is_not_pending(self):
        self.write(".obsidian/types.json", json.dumps({"types": {
            "valid_date": "date", "invalid_date": "date", "valid_datetime": "datetime",
            "invalid_datetime": "datetime", "pending_date": "date", "rating": "number",
            "template_rating": "number"}}))
        self.write("dates.md", '---\nvalid_date: "2026-02-28"\ninvalid_date: "2026-02-30"\n'
                   'valid_datetime: "2026-02-28T10:30:00+08:00"\n'
                   'invalid_datetime: "2026-02-28 at noon"\npending_date: "{{date}}"\nrating: ""\n---\n')
        self.write("00-工作台/模板/pending.md", '---\ntemplate_rating: ""\n---\n')
        report = check_vault.check(self.root)
        self.assertEqual({x["field"] for x in report["issues"] if x["rule"] == "declared_property_type"},
                         {"invalid_date", "invalid_datetime", "rating"})
        pending = {x["field"] for x in report["issues"] if x["rule"] == "property_template_pending"}
        self.assertTrue({"pending_date", "template_rating"}.issubset(pending))
        self.assertNotIn("rating", pending)


if __name__ == "__main__":
    unittest.main()
