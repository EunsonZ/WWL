#!/usr/bin/env python3
"""Read-only acceptance audit for the isolated WWL dual-source import stage.

Known diagnostics are matched by the complete tuple
``rule, path, target, line, reason``.  Baselines and teaching exceptions never
accept globs or directory-wide waivers.  Import-integrity diagnostics (hashes,
TaskNotes preservation, teaching fixtures, and Canvas graph structure) cannot
be suppressed by a known-diagnostics file.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import unicodedata
from typing import Any, Iterable, Iterator

import check_mirrors
import links


FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
WIKI_RE = re.compile(r"(!?)\[\[([^\]\n]+)\]\]")
LOCAL_MARKDOWN_RE = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
TASK_TAG_RE = re.compile(r"(?<![\w/-])#task(?:\b|/)", re.IGNORECASE)
DYNAMIC_BASE_EMBED_RE = re.compile(r"!\[\[[^\]\n]*\.base(?:[#|\\][^\]\n]*)?\]\]", re.IGNORECASE)
LINE_RANGE_RE = re.compile(r"lines?\s+(\d+)-(\d+)")

LINK_BUCKET_RULES = {
    "missing": "link.missing",
    "ambiguous": "link.ambiguous",
    "anchors": "link.missing_anchor",
    "images": "link.missing_image",
    "json": "json.invalid",
    "fences": "markdown.unclosed_fence",
}

# Only inherited structural debt may be acknowledged by an exact baseline.
# Import-integrity and fixture rules remain failing even if somebody puts them
# in the baseline file.
SUPPRESSIBLE_RULES = {
    "link.missing",
    "link.ambiguous",
    "link.missing_anchor",
    "link.missing_image",
    "link.case_mismatch",
    "json.invalid",
    "markdown.unclosed_fence",
    "format.syntax",
    "mirror.missing",
    "mirror.mismatched",
    "mirror.unparsed",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def visible_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not any(
            part.startswith(".") or part == "__pycache__"
            for part in path.relative_to(root).parts
        )
    )


def diagnostic(
    rule: str,
    path: str,
    target: str,
    *,
    line: int | None = None,
    reason: str,
    **details: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "rule": rule,
        "path": PurePosixPath(path).as_posix(),
        "target": str(target),
        "line": line,
        "reason": reason,
    }
    result.update(details)
    return result


def fingerprint(item: dict[str, Any]) -> tuple[str, str, str, int | None, str]:
    return (
        str(item.get("rule", "")),
        PurePosixPath(str(item.get("path", ""))).as_posix(),
        str(item.get("target", "")),
        item.get("line"),
        str(item.get("reason", "")),
    )


def _mask_inline_and_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    output: list[str] = []
    cursor = 0
    while cursor < len(line):
        if in_comment:
            end = line.find("-->", cursor)
            if end < 0:
                return "".join(output), True
            cursor = end + 3
            in_comment = False
            continue
        if line.startswith("<!--", cursor):
            in_comment = True
            cursor += 4
            continue
        if line[cursor] == "`":
            width = 1
            while cursor + width < len(line) and line[cursor + width] == "`":
                width += 1
            marker = "`" * width
            end = line.find(marker, cursor + width)
            if end >= 0:
                output.append(" " * (end + width - cursor))
                cursor = end + width
                continue
        output.append(line[cursor])
        cursor += 1
    return "".join(output), in_comment


def active_markdown_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield lines outside fenced code, inline code, and HTML comments."""
    fence: tuple[str, int] | None = None
    in_comment = False
    for number, raw in enumerate(text.splitlines(), 1):
        match = FENCE_RE.match(raw)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = (marker[0], len(marker))
            elif marker[0] == fence[0] and len(marker) >= fence[1]:
                fence = None
            continue
        if fence is not None:
            continue
        masked, in_comment = _mask_inline_and_comments(raw, in_comment)
        yield number, masked


def collect_link_diagnostics(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    report = links.audit_tree(root)
    diagnostics: list[dict[str, Any]] = []
    for bucket, rule in LINK_BUCKET_RULES.items():
        for item in report.get(bucket, []):
            diagnostics.append(
                diagnostic(
                    rule,
                    item.get("path", ""),
                    item.get("target", ""),
                    line=item.get("line"),
                    reason=str(item.get("reason", bucket)),
                    scope=item.get("scope"),
                    resolved=item.get("resolved"),
                )
            )
    for item in report.get("case_conflicts", []):
        reason = str(item.get("reason", "reference_case"))
        if reason == "reference_case":
            diagnostics.append(
                diagnostic(
                    "link.case_mismatch",
                    item.get("path", ""),
                    item.get("target", ""),
                    line=item.get("line"),
                    reason=reason,
                    scope=item.get("scope"),
                    resolved=item.get("resolved"),
                )
            )
        # Path collisions are checked below with NFC plus case folding over the
        # complete relative path, so the links.py case-only copy is omitted.
    return diagnostics, report


def audit_path_collisions(paths: Iterable[str]) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for raw in paths:
        path = PurePosixPath(str(raw)).as_posix()
        key = unicodedata.normalize("NFC", path).casefold()
        groups[key].append(path)
    diagnostics: list[dict[str, Any]] = []
    for canonical, variants in sorted(groups.items()):
        unique = sorted(set(variants))
        if len(unique) > 1:
            diagnostics.append(
                diagnostic(
                    "path.case_nfc_collision",
                    unique[0],
                    canonical,
                    reason="multiple_full_paths_share_casefolded_NFC_identity",
                    variants=unique,
                )
            )
    return diagnostics


def _exact_canvas_target(
    root: Path, target: str, exact_paths: set[str] | None = None
) -> Path | None:
    normalized = target.replace("\\", "/").lstrip("/")
    candidate = PurePosixPath(normalized)
    if not normalized or ".." in candidate.parts:
        return None
    forms = [candidate]
    if candidate.suffix == "":
        forms.append(PurePosixPath(str(candidate) + ".md"))
    if exact_paths is None:
        exact_paths = {
            path.relative_to(root).as_posix() for path in visible_files(root)
        }
    for form in forms:
        if form.as_posix() not in exact_paths:
            continue
        path = root.joinpath(*form.parts)
        if path.is_file():
            return path
    return None


def audit_canvas_contracts(root: Path) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    files = visible_files(root)
    exact_paths = {path.relative_to(root).as_posix() for path in files}
    for path in files:
        if path.suffix.lower() != ".canvas":
            continue
        rel = path.relative_to(root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            diagnostics.append(
                diagnostic(
                    "canvas.invalid_json", rel, rel, reason="invalid_json", error=str(error)
                )
            )
            continue
        if not isinstance(data, dict):
            diagnostics.append(
                diagnostic("canvas.invalid_shape", rel, rel, reason="root_must_be_object")
            )
            continue
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        if not isinstance(nodes, list) or not isinstance(edges, list):
            diagnostics.append(
                diagnostic(
                    "canvas.invalid_shape",
                    rel,
                    rel,
                    reason="nodes_and_edges_must_be_arrays",
                )
            )
            continue

        node_ids: set[str] = set()
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                diagnostics.append(
                    diagnostic(
                        "canvas.node_shape",
                        rel,
                        str(index),
                        reason="node_must_be_object",
                    )
                )
                continue
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                diagnostics.append(
                    diagnostic(
                        "canvas.node_id", rel, str(node_id), reason="missing_or_non_string_node_id", node=index
                    )
                )
            elif node_id in node_ids:
                diagnostics.append(
                    diagnostic(
                        "canvas.node_id", rel, node_id, reason="duplicate_node_id", node=index
                    )
                )
            else:
                node_ids.add(node_id)
            if node.get("type") == "file":
                target = node.get("file")
                if not isinstance(target, str) or _exact_canvas_target(root, target, exact_paths) is None:
                    diagnostics.append(
                        diagnostic(
                            "canvas.file_target",
                            rel,
                            str(target),
                            reason="missing_exact_file_target",
                            node=index,
                        )
                    )

        edge_ids: set[str] = set()
        for index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                diagnostics.append(
                    diagnostic(
                        "canvas.edge_shape", rel, str(index), reason="edge_must_be_object"
                    )
                )
                continue
            edge_id = edge.get("id")
            if not isinstance(edge_id, str) or not edge_id:
                diagnostics.append(
                    diagnostic(
                        "canvas.edge_id", rel, str(edge_id), reason="missing_or_non_string_edge_id", edge=index
                    )
                )
            elif edge_id in edge_ids:
                diagnostics.append(
                    diagnostic(
                        "canvas.edge_id", rel, edge_id, reason="duplicate_edge_id", edge=index
                    )
                )
            else:
                edge_ids.add(edge_id)
            for field in ("fromNode", "toNode"):
                endpoint = edge.get(field)
                if not isinstance(endpoint, str) or endpoint not in node_ids:
                    diagnostics.append(
                        diagnostic(
                            "canvas.edge_endpoint",
                            rel,
                            str(endpoint),
                            reason=f"{field}_does_not_reference_existing_node",
                            edge=index,
                        )
                    )
    return diagnostics


def _table_cells(line: str) -> list[str] | None:
    """Split a possible table row on unescaped pipes, with optional borders."""
    text = line.strip()
    if not text:
        return None
    if text.startswith("|"):
        text = text[1:]
    if re.search(r"(?<!\\)\|\s*$", text):
        text = re.sub(r"(?<!\\)\|\s*$", "", text)
    cells = re.split(r"(?<!\\)\|", text)
    return [cell.strip() for cell in cells] if len(cells) >= 2 else None


def _table_structure_cells(line: str) -> list[str] | None:
    """Count structural cells while protecting pipes inside link/math content."""
    protected = re.sub(
        r"\${1,2}.*?\${1,2}",
        lambda match: match.group(0).replace("|", r"\|"),
        line,
    )
    protected = WIKI_RE.sub(
        lambda match: match.group(0).replace("|", r"\|"),
        protected,
    )
    return _table_cells(protected)


def _is_table_separator(line: str) -> bool:
    cells = _table_cells(line)
    return bool(
        cells
        and len(cells) >= 2
        and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)
    )


def _markdown_table_rows(lines: list[tuple[int, str]]) -> set[int]:
    """Return physical line numbers belonging to real Markdown tables.

    A table starts only when a header is immediately followed by a delimiter
    row.  Body rows must remain physically contiguous and contain an unescaped
    pipe.  This prevents paragraphs, callouts, and isolated math bars from
    becoming tables merely because they contain multiple ``|`` characters.
    """
    rows: set[int] = set()
    for index, (number, line) in enumerate(lines):
        if not _is_table_separator(line) or index == 0:
            continue
        header_number, header = lines[index - 1]
        header_cells = _table_structure_cells(header)
        separator_cells = _table_cells(line)
        if (
            header_number != number - 1
            or header_cells is None
            or separator_cells is None
            or len(header_cells) != len(separator_cells)
        ):
            continue
        rows.add(header_number)
        cursor = index + 1
        previous_number = number
        while cursor < len(lines):
            row_number, row = lines[cursor]
            if row_number != previous_number + 1 or _table_cells(row) is None:
                break
            rows.add(row_number)
            previous_number = row_number
            cursor += 1
    return rows


def audit_table_pipes(root: Path) -> list[dict[str, Any]]:
    """Detect wikilink alias pipes that split Markdown table cells.

    Ordinary table separators, math absolute-value bars, and fenced teaching
    examples are not diagnostics.  Only an unescaped alias pipe inside a
    wikilink on an active table row is rejected.
    """
    diagnostics: list[dict[str, Any]] = []
    for path in visible_files(root):
        if path.suffix.lower() != ".md":
            continue
        rel = path.relative_to(root).as_posix()
        active_lines = list(active_markdown_lines(path.read_text(encoding="utf-8")))
        table_rows = _markdown_table_rows(active_lines)
        for number, line in active_lines:
            if number not in table_rows:
                continue
            # Math spans may contain arbitrary bars and do not define table
            # columns.  Removing them also avoids treating examples inside math
            # as wikilinks.
            inspect = re.sub(r"\${1,2}.*?\${1,2}", "", line)
            for match in WIKI_RE.finditer(inspect):
                inner = match.group(2)
                if re.search(r"(?<!\\)\|", inner):
                    diagnostics.append(
                        diagnostic(
                            "table.unescaped_wikilink_pipe",
                            rel,
                            inner,
                            line=number,
                            reason="wikilink_alias_pipe_must_be_escaped_in_table",
                        )
                    )
    return diagnostics


def find_fragment_root(work: Path, baseline_path: Path) -> Path:
    """Find import manifests in development ``fragments`` or final ``artifacts``."""
    candidates = [
        work / "fragments",
        work / "artifacts",
        work,
        baseline_path.parent,
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "teaching-fixtures.json").is_file():
            return candidate
    # Retain a deterministic path so missing-manifest diagnostics remain
    # reviewable instead of silently choosing an unrelated directory.
    return (work / "fragments").resolve()


def audit_static_task_samples(root: Path, sample_paths: Iterable[str]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for relative in sorted(set(sample_paths)):
        path = root / relative
        if not path.is_file():
            diagnostics.append(
                diagnostic(
                    "fixture.static_task_missing",
                    relative,
                    relative,
                    reason="declared_static_task_sample_missing",
                )
            )
            continue
        active = list(active_markdown_lines(path.read_text(encoding="utf-8")))
        in_frontmatter = False
        tags_block = False
        for number, line in active:
            stripped = line.strip()
            if number == 1 and stripped == "---":
                in_frontmatter = True
                continue
            if in_frontmatter and stripped == "---":
                in_frontmatter = False
                tags_block = False
                continue
            if TASK_TAG_RE.search(line):
                diagnostics.append(
                    diagnostic(
                        "tasknotes.active_task_tag",
                        relative,
                        "#task",
                        line=number,
                        reason="active_task_tag_in_static_sample",
                    )
                )
            if in_frontmatter:
                tags_match = re.match(r"^\s*tags\s*:\s*(.*)$", line, re.IGNORECASE)
                if tags_match:
                    tags_block = True
                    if re.search(r"(?:^|[\[\s,])task(?:$|[\]\s,])", tags_match.group(1), re.IGNORECASE):
                        diagnostics.append(
                            diagnostic(
                                "tasknotes.active_task_tag",
                                relative,
                                "frontmatter:task",
                                line=number,
                                reason="active_task_frontmatter_in_static_sample",
                            )
                        )
                elif tags_block and re.match(r"^\s*-\s*task\s*$", line, re.IGNORECASE):
                    diagnostics.append(
                        diagnostic(
                            "tasknotes.active_task_tag",
                            relative,
                            "frontmatter:task",
                            line=number,
                            reason="active_task_frontmatter_in_static_sample",
                        )
                    )
                elif tags_block and re.match(r"^\S", line):
                    tags_block = False
            if DYNAMIC_BASE_EMBED_RE.search(line):
                diagnostics.append(
                    diagnostic(
                        "tasknotes.dynamic_task_embed",
                        relative,
                        DYNAMIC_BASE_EMBED_RE.search(line).group(0),
                        line=number,
                        reason="active_dynamic_base_embed_in_static_sample",
                    )
                )
    return diagnostics


def _active_link_targets(path: Path) -> Iterator[tuple[int, str, str]]:
    for number, line in active_markdown_lines(path.read_text(encoding="utf-8")):
        for match in WIKI_RE.finditer(line):
            target, _, _ = links._split_alias(match.group(2))
            yield number, target, "wiki"
        for match in LOCAL_MARKDOWN_RE.finditer(line):
            target = match.group(1).split(maxsplit=1)[0].strip("<>")
            if not links._is_remote(target):
                yield number, target, "markdown"


def audit_teaching_fixtures(
    root: Path, fragment: dict[str, Any]
) -> tuple[list[dict[str, Any]], set[tuple[str, str, str, int | None, str]]]:
    diagnostics: list[dict[str, Any]] = []
    entries = fragment.get("entries", []) if isinstance(fragment, dict) else []
    broken: list[tuple[dict[str, Any], str]] = []
    islands: list[dict[str, Any]] = []
    snippets: list[dict[str, Any]] = []
    static_samples: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        target_text = str(entry.get("target", ""))
        match = re.search(r"\[\[([^\]]+)\]\]", target_text)
        if match and "intentional unresolved-link" in str(entry.get("reason", "")):
            broken.append((entry, match.group(1)))
        if "whole note intentionally has no internal incoming or outgoing links" in target_text:
            islands.append(entry)
        if "snippet_sha256" in entry:
            snippets.append(entry)
        if "/Tasks/" in str(entry.get("file", "")):
            static_samples.append(str(entry["file"]))

    if len(broken) != 2:
        diagnostics.append(
            diagnostic(
                "fixture.manifest_shape",
                "fragments/teaching-fixtures.json",
                str(len(broken)),
                reason="exactly_two_intentional_broken_links_required",
            )
        )
    if len(islands) != 1:
        diagnostics.append(
            diagnostic(
                "fixture.manifest_shape",
                "fragments/teaching-fixtures.json",
                str(len(islands)),
                reason="exactly_one_intentional_island_required",
            )
        )
    if len(snippets) != 3:
        diagnostics.append(
            diagnostic(
                "fixture.manifest_shape",
                "fragments/teaching-fixtures.json",
                str(len(snippets)),
                reason="exactly_three_hashed_fixture_snippets_required",
            )
        )
    if len(static_samples) != 4:
        diagnostics.append(
            diagnostic(
                "fixture.manifest_shape",
                "fragments/teaching-fixtures.json",
                str(len(static_samples)),
                reason="exactly_four_static_TaskNotes_samples_required",
            )
        )

    intentional: set[tuple[str, str, str, int | None, str]] = set()
    for entry, target in broken:
        relative = str(entry["file"])
        path = root / relative
        expected_line_match = re.search(r"line\s+(\d+)", str(entry.get("target", "")))
        expected_line = int(expected_line_match.group(1)) if expected_line_match else None
        present = False
        if path.is_file():
            for line, observed, style in _active_link_targets(path):
                if style == "wiki" and observed == target and (expected_line is None or line == expected_line):
                    present = True
                    expected_line = line
                    break
        if not present:
            diagnostics.append(
                diagnostic(
                    "fixture.broken_link_missing",
                    relative,
                    target,
                    line=expected_line,
                    reason="declared_intentional_broken_link_not_found_exactly",
                )
            )
        intentional.add(
            fingerprint(
                diagnostic(
                    "link.missing",
                    relative,
                    target,
                    line=expected_line,
                    reason="missing",
                )
            )
        )

    all_paths = [path.relative_to(root).as_posix() for path in visible_files(root)]
    index = links._Index(all_paths)
    for entry in islands:
        relative = str(entry["file"])
        island_path = root / relative
        if not island_path.is_file():
            diagnostics.append(
                diagnostic(
                    "fixture.island_missing", relative, relative, reason="declared_island_file_missing"
                )
            )
            continue
        outgoing = list(_active_link_targets(island_path))
        if outgoing:
            diagnostics.append(
                diagnostic(
                    "fixture.island_has_links",
                    relative,
                    outgoing[0][1],
                    line=outgoing[0][0],
                    reason="declared_island_has_active_outgoing_link",
                )
            )
        for other in visible_files(root):
            if other.suffix.lower() != ".md" or other == island_path:
                continue
            source = other.relative_to(root).as_posix()
            for line, target, style in _active_link_targets(other):
                resolved, _ = links._resolve_target(
                    links._split_anchor(target)[0],
                    source,
                    index,
                    root_relative=style == "wiki",
                )
                if resolved == relative:
                    diagnostics.append(
                        diagnostic(
                            "fixture.island_has_links",
                            source,
                            target,
                            line=line,
                            reason="declared_island_has_active_incoming_link",
                        )
                    )

    for entry in snippets:
        relative = str(entry["file"])
        match = LINE_RANGE_RE.search(str(entry.get("target", "")))
        if not match:
            diagnostics.append(
                diagnostic(
                    "fixture.snippet_manifest",
                    relative,
                    str(entry.get("target", "")),
                    reason="snippet_line_range_missing",
                )
            )
            continue
        start, end = (int(value) for value in match.groups())
        path = root / relative
        if not path.is_file():
            observed = None
        else:
            lines_with_endings = path.read_text(encoding="utf-8").splitlines(keepends=True)
            snippet = "".join(lines_with_endings[start - 1 : end])
            observed = hashlib.sha256(snippet.encode("utf-8")).hexdigest()
        expected = str(entry["snippet_sha256"])
        if observed != expected:
            diagnostics.append(
                diagnostic(
                    "fixture.snippet_hash",
                    relative,
                    f"lines:{start}-{end}",
                    line=start,
                    reason="declared_fixture_snippet_changed",
                    expected=expected,
                    actual=observed,
                )
            )

    diagnostics.extend(audit_static_task_samples(root, static_samples))
    return diagnostics, intentional


def audit_tasknotes_preservation(
    root: Path, inventory: dict[str, str]
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    expected = {path: digest for path, digest in inventory.items() if path.startswith("TaskNotes/")}
    current = {
        path.relative_to(root).as_posix(): path
        for path in visible_files(root)
        if path.relative_to(root).as_posix().startswith("TaskNotes/")
    }
    if len(expected) != 8:
        diagnostics.append(
            diagnostic(
                "tasknotes.baseline_count",
                "TaskNotes",
                str(len(expected)),
                reason="baseline_must_define_exactly_eight_TaskNotes_files",
            )
        )
    for relative in sorted(set(expected) - set(current)):
        diagnostics.append(
            diagnostic(
                "tasknotes.file_set",
                relative,
                relative,
                reason="baseline_TaskNotes_file_missing",
            )
        )
    for relative in sorted(set(current) - set(expected)):
        diagnostics.append(
            diagnostic(
                "tasknotes.file_set",
                relative,
                relative,
                reason="unexpected_TaskNotes_file_added",
            )
        )
    for relative in sorted(set(expected) & set(current)):
        observed = sha256_file(current[relative])
        if observed != expected[relative]:
            diagnostics.append(
                diagnostic(
                    "tasknotes.hash",
                    relative,
                    relative,
                    reason="TaskNotes_file_changed_from_original_WWL_baseline",
                    expected=expected[relative],
                    actual=observed,
                )
            )
    return diagnostics


def audit_hash_manifest(
    root: Path,
    fragment_path: Path,
    *,
    entries_key: str,
    target_key: str,
    rule_prefix: str,
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if not fragment_path.is_file():
        return [
            diagnostic(
                f"{rule_prefix}.manifest_missing",
                fragment_path.name,
                fragment_path.name,
                reason="required_hash_manifest_missing",
            )
        ]
    try:
        payload = json.loads(fragment_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return [
            diagnostic(
                f"{rule_prefix}.manifest_invalid",
                fragment_path.name,
                fragment_path.name,
                reason="required_hash_manifest_invalid",
                error=str(error),
            )
        ]
    entries = payload.get(entries_key, [])
    if not isinstance(entries, list):
        return [
            diagnostic(
                f"{rule_prefix}.manifest_invalid",
                fragment_path.name,
                entries_key,
                reason="manifest_entries_must_be_array",
            )
        ]
    for entry in entries:
        if not isinstance(entry, dict) or target_key not in entry or "sha256" not in entry:
            diagnostics.append(
                diagnostic(
                    f"{rule_prefix}.manifest_invalid",
                    fragment_path.name,
                    str(entry),
                    reason="manifest_entry_requires_target_and_sha256",
                )
            )
            continue
        relative = str(entry[target_key])
        path = root / relative
        actual = sha256_file(path) if path.is_file() else None
        expected = str(entry["sha256"])
        if actual != expected:
            diagnostics.append(
                diagnostic(
                    f"{rule_prefix}.hash",
                    relative,
                    relative,
                    reason="preserved_target_hash_mismatch",
                    expected=expected,
                    actual=actual,
                )
            )
    return diagnostics


def run_format_checker(root: Path, script: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    command = ["ruby", str(script), str(root)]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    result: dict[str, Any] = {
        "command": command,
        "exit_code": completed.returncode,
        "stderr": completed.stderr.strip(),
    }
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        result["parse_error"] = str(error)
        return [
            diagnostic(
                "format.runner",
                script.name,
                "ruby",
                reason="format_checker_did_not_return_JSON",
                exit_code=completed.returncode,
            )
        ], result
    result["report"] = report
    diagnostics = [
        diagnostic(
            "format.syntax",
            str(item.get("path", "")),
            str(item.get("type", "format")),
            line=item.get("line"),
            reason=str(item.get("message", "syntax_error")),
        )
        for item in report.get("errors", [])
    ]
    return diagnostics, result


def collect_mirror_diagnostics(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    report = check_mirrors.check(root)
    diagnostics: list[dict[str, Any]] = []
    for bucket in ("missing", "mismatched", "unparsed"):
        for item in report.get(bucket, []):
            diagnostics.append(
                diagnostic(
                    f"mirror.{bucket}",
                    str(item.get("path", "")),
                    str(item.get("source", "")),
                    line=item.get("line"),
                    reason=bucket,
                )
            )
    return diagnostics, report


def _known_from_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in ("known_diagnostics", "diagnostics", "known"):
        if isinstance(payload.get(key), list):
            return list(payload[key])
    # Also accept an earlier links.audit_tree JSON as a migration input.
    result: list[dict[str, Any]] = []
    for bucket, rule in LINK_BUCKET_RULES.items():
        for item in payload.get(bucket, []) if isinstance(payload.get(bucket), list) else []:
            result.append(
                {
                    "rule": rule,
                    "path": item.get("path", ""),
                    "target": item.get("target", ""),
                    "line": item.get("line"),
                    "reason": str(item.get("reason", bucket)),
                }
            )
    for item in payload.get("case_conflicts", []) if isinstance(payload.get("case_conflicts"), list) else []:
        if item.get("reason") == "reference_case":
            result.append(
                {
                    "rule": "link.case_mismatch",
                    "path": item.get("path", ""),
                    "target": item.get("target", ""),
                    "line": item.get("line"),
                    "reason": "reference_case",
                }
            )
    return result


def load_baseline(path: Path) -> tuple[dict[str, str], list[dict[str, Any]], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    inventory: dict[str, str] = {}
    known = _known_from_payload(payload)
    issues: list[dict[str, Any]] = []

    def add_inventory(items: Any) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
                inventory[item["path"]] = item["sha256"]

    if isinstance(payload, list):
        add_inventory(payload)
    elif isinstance(payload, dict):
        add_inventory(payload.get("files"))
        add_inventory(payload.get("inventory"))
        inventory_path = payload.get("inventory_path")
        if isinstance(inventory_path, str):
            candidate = Path(inventory_path)
            if not candidate.is_absolute():
                candidate = path.parent / candidate
            add_inventory(json.loads(candidate.read_text(encoding="utf-8")))
        elif path.name != "baseline.json" and (path.parent / "baseline.json").is_file():
            add_inventory(json.loads((path.parent / "baseline.json").read_text(encoding="utf-8")))

    validated_known: list[dict[str, Any]] = []
    for index, item in enumerate(known):
        if not isinstance(item, dict):
            issues.append(
                diagnostic(
                    "baseline.invalid",
                    path.name,
                    str(index),
                    reason="known_diagnostic_must_be_object",
                )
            )
            continue
        required = ("rule", "path", "target", "line", "reason")
        if any(key not in item for key in required):
            issues.append(
                diagnostic(
                    "baseline.invalid",
                    path.name,
                    str(index),
                    reason="known_diagnostic_requires_rule_path_target_line_reason",
                )
            )
            continue
        if any(any(token in str(item[key]) for token in ("*", "?")) for key in ("path", "target")):
            issues.append(
                diagnostic(
                    "baseline.invalid",
                    path.name,
                    str(index),
                    reason="known_diagnostic_must_not_use_glob_patterns",
                )
            )
            continue
        validated_known.append(
            diagnostic(
                str(item["rule"]),
                str(item["path"]),
                str(item["target"]),
                line=item["line"],
                reason=str(item["reason"]),
            )
        )
    return inventory, validated_known, issues


def classify_diagnostics(
    current: Iterable[dict[str, Any]],
    known: Iterable[dict[str, Any]],
    intentional: set[tuple[str, str, str, int | None, str]],
) -> dict[str, list[dict[str, Any]]]:
    known_map = {fingerprint(item): item for item in known}
    current_list = list(current)
    current_keys = {fingerprint(item) for item in current_list}
    classified = {"new": [], "known": [], "intentional": [], "resolved": []}
    for item in current_list:
        key = fingerprint(item)
        if key in intentional:
            classified["intentional"].append(item)
        elif item["rule"] in SUPPRESSIBLE_RULES and key in known_map:
            classified["known"].append(item)
        else:
            classified["new"].append(item)
    for key, item in known_map.items():
        if key not in current_keys:
            classified["resolved"].append(item)
    for bucket in classified.values():
        bucket.sort(key=lambda item: fingerprint(item))
    return classified


def validate(root: Path, baseline_path: Path, work: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    baseline_path = baseline_path.resolve()
    work = (work or baseline_path.parent).resolve()
    fragments = find_fragment_root(work, baseline_path)
    inventory, known, baseline_issues = load_baseline(baseline_path)

    teaching_path = fragments / "teaching-fixtures.json"
    if teaching_path.is_file():
        teaching_payload = json.loads(teaching_path.read_text(encoding="utf-8"))
        fixture_diagnostics, intentional = audit_teaching_fixtures(root, teaching_payload)
    else:
        fixture_diagnostics = [
            diagnostic(
                "fixture.manifest_missing",
                teaching_path.name,
                teaching_path.name,
                reason="teaching_fixture_manifest_missing",
            )
        ]
        intentional = set()

    link_diagnostics, link_report = collect_link_diagnostics(root)
    current_link_keys = {fingerprint(item) for item in link_diagnostics}
    for expected in sorted(intentional):
        if expected not in current_link_keys:
            rule, path, target, line, _ = expected
            fixture_diagnostics.append(
                diagnostic(
                    "fixture.broken_link_not_unresolved",
                    path,
                    target,
                    line=line,
                    reason="intentional_broken_link_target_now_resolves_or_changed",
                    expected_rule=rule,
                )
            )

    relative_paths = [path.relative_to(root).as_posix() for path in visible_files(root)]
    format_diagnostics, format_result = run_format_checker(root, Path(__file__).with_name("check_formats.rb"))
    mirror_diagnostics, mirror_report = collect_mirror_diagnostics(root)

    diagnostics: list[dict[str, Any]] = []
    diagnostics.extend(link_diagnostics)
    diagnostics.extend(audit_path_collisions(relative_paths))
    diagnostics.extend(audit_canvas_contracts(root))
    diagnostics.extend(audit_table_pipes(root))
    diagnostics.extend(format_diagnostics)
    diagnostics.extend(mirror_diagnostics)
    diagnostics.extend(baseline_issues)
    diagnostics.extend(fixture_diagnostics)
    diagnostics.extend(audit_tasknotes_preservation(root, inventory))
    diagnostics.extend(
        audit_hash_manifest(
            root,
            fragments / "raw-originals.json",
            entries_key="entries",
            target_key="target",
            rule_prefix="original",
        )
    )
    diagnostics.extend(
        audit_hash_manifest(
            root,
            fragments / "pdf-catalog.json",
            entries_key="items",
            target_key="target",
            rule_prefix="pdf",
        )
    )
    diagnostics.extend(
        audit_hash_manifest(
            root,
            fragments / "imported-tests.json",
            entries_key="created_files",
            target_key="path",
            rule_prefix="imported_test",
        )
    )

    # Deduplicate identical observations produced by independent read-only
    # passes while preserving the first, more detailed record.
    unique: dict[tuple[str, str, str, int | None, str], dict[str, Any]] = {}
    for item in diagnostics:
        unique.setdefault(fingerprint(item), item)
    classified = classify_diagnostics(unique.values(), known, intentional)
    return {
        "schema": "wwl-import-validation-v1",
        "root": str(root),
        "baseline": str(baseline_path),
        "summary": {
            "new": len(classified["new"]),
            "known": len(classified["known"]),
            "intentional": len(classified["intentional"]),
            "resolved": len(classified["resolved"]),
            "passed": not classified["new"],
        },
        "diagnostics": classified,
        "checks": {
            "fragment_root": str(fragments),
            "visible_files": len(relative_paths),
            "baseline_inventory_files": len(inventory),
            "known_fingerprints": len(known),
            "link_counts": link_report.get("counts", {}),
            "mirror": mirror_report,
            "format": format_result,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="isolated stage root to audit")
    parser.add_argument("--baseline", type=Path, required=True, help="exact known diagnostics or original file inventory")
    parser.add_argument("--work", type=Path, help="work root containing fragments; defaults to baseline parent")
    parser.add_argument("--output", type=Path, help="optional JSON report path outside the stage")
    arguments = parser.parse_args(argv)
    report = validate(arguments.root, arguments.baseline, arguments.work)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
