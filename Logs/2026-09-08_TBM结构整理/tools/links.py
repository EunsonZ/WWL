"""Conservative Obsidian link migration and audit helpers.

The migration map is the authority: a link is rewritten only after its old
target has been resolved exactly (or, for a slashless wikilink, to one unique
stem) and that resolved path occurs in ``mapping``.  This intentionally leaves
unknown and ambiguous links untouched.

Only the Python standard library is required.  ``rewrite_tree`` mutates a
staging tree; it must never be pointed at the live vault by callers.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator
from urllib.parse import quote, unquote


_WIKI_RE = re.compile(r"(!?)\[\[([^\]\n]+)\]\]")
_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$")
_BLOCK_RE = re.compile(r"(?:^|\s)\^([A-Za-z0-9_-]+)\s*$")
_IMAGE_EXTENSIONS = {
    ".avif", ".bmp", ".gif", ".heic", ".jpeg", ".jpg", ".png",
    ".svg", ".tif", ".tiff", ".webp",
}
_REMOTE_SCHEMES = ("http://", "https://", "mailto:", "obsidian:", "data:")
_LOGICAL_PREFIXES = {
    "AI": "TBM/AI",
    "数学": "TBM/数学",
    "哲学与文化": "TBM/哲学与文化",
    "计算机知识": "TBM/com/计算机知识",
    "编程知识": "TBM/com/编程知识",
    "_labs": "TBM/com/_labs",
    "_meta": "TBM/com/_meta",
    "Kali": "TBM/计算机知识/Kali",
}


def _posix(value: str | os.PathLike[str]) -> str:
    text = str(value).replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    # PurePosixPath deliberately preserves ``..``; link resolution needs a
    # lexical normalization while remaining independent of filesystem state.
    normalized = posixpath.normpath(text)
    return PurePosixPath(normalized).as_posix().lstrip("/")


def _without_md(path: str) -> str:
    return path[:-3] if path.lower().endswith(".md") else path


def _split_anchor(target: str) -> tuple[str, str]:
    # Obsidian uses # both for headings and #^block-id.  Preserve it verbatim.
    if "#" in target:
        path, anchor = target.split("#", 1)
        return path, "#" + anchor
    return target, ""


def _split_alias(inner: str) -> tuple[str, str, str]:
    """Return target, delimiter, alias; an escaped table pipe is supported."""
    for match in re.finditer(r"(?<!\\)\||\\\|", inner):
        return inner[: match.start()], match.group(0), inner[match.end() :]
    return inner, "", ""


def _is_remote(target: str) -> bool:
    lower = target.strip().lower()
    return lower.startswith(_REMOTE_SCHEMES) or lower.startswith("#")


def _role_is_preserved(role: object) -> bool:
    return str(role or "").strip().lower() in {"historical", "original", "governance"}


def _historical_scope(path: str) -> str:
    lowered = path.casefold()
    name = PurePosixPath(path).name.casefold()
    if name in {"agents.md", "change.md", "newagents.md"}:
        return "governance"
    original_markers = ("/clippings/", "/原稿/", "原始上传")
    if any(marker in lowered for marker in original_markers):
        return "original"
    markers = (
        "/历史", "/归档", "/archive", "/archives", "/维护/", "/logs/",
        "历史报告", "原始材料", "原始文件", "snapshot", "baseline",
    )
    return "historical" if any(marker in lowered for marker in markers) else "active"


def _path_candidates(path: str) -> tuple[str, ...]:
    path = _posix(unquote(path.strip()))
    if not path:
        return ()
    suffix = PurePosixPath(path).suffix
    if suffix.lower() == ".md":
        return (path,)
    if suffix:
        # Obsidian note titles may contain dots (``llama.cpp`` or
        # ``evaluation-report.template``).  Prefer a real file with the exact
        # spelling, then try the Markdown note represented by that title.
        return (path, path + ".md")
    return (path, path + ".md")


class _Index:
    def __init__(self, paths: Iterable[str]) -> None:
        normalized = sorted({_posix(path) for path in paths})
        self.paths = set(normalized)
        self.casefold: dict[str, list[str]] = defaultdict(list)
        self.stems: dict[str, list[str]] = defaultdict(list)
        for path in normalized:
            self.casefold[path.casefold()].append(path)
            if PurePosixPath(path).suffix.lower() == ".md":
                self.stems[PurePosixPath(path).stem.casefold()].append(path)

    def exact(self, candidate: str) -> tuple[str | None, str]:
        candidate = _posix(candidate)
        for form in _path_candidates(candidate):
            if form in self.paths:
                return form, "exact"
            matches = self.casefold.get(form.casefold(), [])
            if len(matches) == 1:
                return matches[0], "case_mismatch"
            if len(matches) > 1:
                return None, "ambiguous"
        return None, "missing"


def _logical_candidate(target: str) -> str | None:
    parts = PurePosixPath(target).parts
    if not parts:
        return None
    root = _LOGICAL_PREFIXES.get(parts[0])
    if root is None:
        return None
    return _posix(PurePosixPath(root, *parts[1:]))


def _resolve_target(
    target: str,
    source_old: str,
    index: _Index,
    *,
    allow_unique_stem: bool = True,
    root_relative: bool = False,
) -> tuple[str | None, str]:
    decoded = unquote(target.strip())
    # Markdown permits backslash escapes in destinations.  Decode common
    # escaped filename punctuation before treating any remaining backslash as
    # a path separator from imported Windows-authored material.
    decoded = re.sub(r"\\([ ()\[\]#])", r"\1", decoded).replace("\\", "/")
    if not decoded:
        return source_old, "self"

    explicit = "/" in decoded or decoded.startswith(".")
    logical = _logical_candidate(decoded)
    candidates: list[str] = []
    if (
        source_old.startswith("TBM/计算机知识/Kali/")
        and (decoded == "计算机知识/Kali" or decoded.startswith("计算机知识/Kali/"))
    ):
        # Kali was a separate imported package under TBM/计算机知识, whereas
        # the general computer curriculum lived under TBM/com/计算机知识.
        candidates.append(_posix(PurePosixPath("TBM") / decoded))
    if decoded == "TBM" or decoded.startswith("TBM/"):
        # Mapping paths are live-vault-relative and normally retain TBM as
        # their first component.  Canvas files commonly store this form.
        candidates.append(_posix(decoded))
    elif logical:
        candidates.append(logical)
        # audit_tree may be pointed at a newly arranged tree whose root is
        # already the logical vault root.  This is still an explicit path
        # check; it does not fall back to a basename.
        candidates.append(_posix(decoded))
    elif (
        root_relative
        and "/" not in decoded
        and not decoded.startswith(".")
        and bool(PurePosixPath(decoded).suffix)
    ):
        # A slashless wikilink naming an ordinary file (for example a .py
        # fixture) first means the exact sibling beside its source note.
        # Keeping this branch slashless avoids rescuing an explicitly wrong
        # directory through a basename fallback.
        candidates.append(_posix(PurePosixPath(source_old).parent / decoded))
        candidates.append(_posix(decoded))
    elif root_relative and not decoded.startswith("."):
        # Wikilinks and Canvas file nodes use vault-root paths.  Markdown
        # destinations are passed with root_relative=False and remain relative
        # to their source document.
        candidates.append(_posix(decoded))
    elif decoded.startswith("/"):
        candidates.append(decoded.lstrip("/"))
    else:
        parent = PurePosixPath(source_old).parent
        candidates.append(_posix(parent / decoded))

        # TBM/com's 00--11 navigation pages use com-root-relative links even
        # when an author writes them from a nested page.
        first = PurePosixPath(decoded).parts[0] if PurePosixPath(decoded).parts else ""
        if source_old.startswith("TBM/com/") and re.match(r"^(?:0\d|1[01])-", first):
            candidates.append(_posix(PurePosixPath("TBM/com") / decoded))

    seen: set[str] = set()
    ambiguous = False
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        resolved, status = index.exact(candidate)
        if resolved:
            return resolved, status
        ambiguous = ambiguous or status == "ambiguous"

    if not explicit and allow_unique_stem:
        stem = PurePosixPath(decoded).stem.casefold()
        matches = index.stems.get(stem, [])
        if len(matches) == 1:
            return matches[0], "unique_stem"
        if len(matches) > 1:
            # README and other repeated names stay source-relative when that
            # exact sibling exists; otherwise they are truly ambiguous.
            sibling, status = index.exact(_posix(PurePosixPath(source_old).parent / decoded))
            if sibling:
                return sibling, status
            return None, "ambiguous"
    return None, "ambiguous" if ambiguous else "missing"


def _mapping_indexes(mapping: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str], _Index]:
    by_old: dict[str, dict[str, Any]] = {}
    candidates_for_new: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in mapping:
        if "old" not in raw or "new" not in raw:
            raise ValueError("each mapping item must contain old and new")
        item = dict(raw)
        old = _posix(item["old"])
        new = _posix(item["new"])
        if old in by_old:
            raise ValueError(f"duplicate old mapping path: {old}")
        item["old"], item["new"] = old, new
        by_old[old] = item
        candidates_for_new[new].append(item)
    # A many-to-one mapping is expected for deduplication.  The staged bytes
    # come from its non-merge (move/retain) row, so that row also supplies the
    # correct original source directory for relative-link resolution.
    rank = {"retain": 0, "move": 1, "merge": 2}
    old_for_new = {
        new: min(items, key=lambda item: (rank.get(str(item.get("action")), 1), item["old"]))["old"]
        for new, items in candidates_for_new.items()
    }
    return by_old, old_for_new, _Index(by_old)


def _relative_target(source_new: str, target_new: str) -> str:
    parent = PurePosixPath(source_new).parent.as_posix()
    relative = os.path.relpath(target_new, parent or ".").replace("\\", "/")
    return relative


def _encode_like(path: str, original: str) -> str:
    """Preserve the caller's URL-encoding convention without escaping CJK."""
    if "%" not in original:
        return path
    # If the old destination was entirely ASCII, it used full URL encoding.
    if original.isascii():
        return quote(path, safe="/._-~")
    # Mixed Markdown paths in this vault usually encode only spaces and
    # parentheses while leaving readable CJK components literal.
    encoded_ascii = {
        chr(int(match.group(1), 16))
        for match in re.finditer(r"%([0-7][0-9A-Fa-f])", original)
    }
    for char in sorted(encoded_ascii):
        path = path.replace(char, quote(char, safe=""))
    return path


def _rewrite_one_target(
    target: str,
    *,
    source_old: str,
    source_new: str,
    by_old: dict[str, dict[str, Any]],
    old_index: _Index,
    new_index: _Index | None,
    source_is_mapped: bool,
    style: str,
) -> tuple[str, str, str | None]:
    path_part, anchor = _split_anchor(target)
    if _is_remote(path_part) or (not path_part and anchor):
        return target, "external_or_local_anchor", None
    if not source_is_mapped:
        if new_index is None:
            return target, "missing", None
        resolved_new, status_new = _resolve_target(
            path_part, source_new, new_index, root_relative=style in {"wiki", "canvas"}
        )
        return target, "valid_new" if resolved_new else status_new, resolved_new

    resolved, status = _resolve_target(
        path_part, source_old, old_index, root_relative=style in {"wiki", "canvas"}
    )
    if not resolved:
        # A file copied from the old tree may already contain a link edited to
        # a valid complete destination in the new tree.  Recognize it only
        # after old-space resolution fails, preserving old relative semantics.
        if new_index is not None:
            resolved_new, status_new = _resolve_target(
                path_part, source_new, new_index, root_relative=style in {"wiki", "canvas"}
            )
            if resolved_new:
                return target, "valid_new", resolved_new
        return target, status, None
    item = by_old.get(resolved)
    if item is None:
        return target, "unmapped", resolved
    target_new = item["new"]
    if style == "wiki":
        rewritten = _without_md(target_new)
    elif style == "canvas":
        rewritten = _without_md(target_new) if not PurePosixPath(path_part).suffix else target_new
    else:
        rewritten = _relative_target(source_new, target_new)
        # Retain URL-encoded path style when the original used it.
        if "%" in path_part:
            rewritten = _encode_like(rewritten, path_part)
    return rewritten + anchor, "rewritten", resolved


def _protected_spans(line: str, in_comment: bool) -> tuple[str, list[str], bool]:
    """Replace inline code and HTML comments with collision-safe sentinels."""
    saved: list[str] = []
    out: list[str] = []
    index = 0
    while index < len(line):
        if in_comment:
            end = line.find("-->", index)
            if end < 0:
                saved.append(line[index:])
                out.append(f"\x00P{len(saved)-1}\x00")
                return "".join(out), saved, True
            end += 3
            saved.append(line[index:end])
            out.append(f"\x00P{len(saved)-1}\x00")
            index = end
            in_comment = False
            continue
        if line.startswith("<!--", index):
            in_comment = True
            continue
        if line[index] == "`":
            run = 1
            while index + run < len(line) and line[index + run] == "`":
                run += 1
            marker = "`" * run
            end = line.find(marker, index + run)
            if end >= 0:
                end += run
                saved.append(line[index:end])
                out.append(f"\x00P{len(saved)-1}\x00")
                index = end
                continue
        out.append(line[index])
        index += 1
    return "".join(out), saved, in_comment


def _restore_spans(line: str, saved: list[str]) -> str:
    for index, value in enumerate(saved):
        line = line.replace(f"\x00P{index}\x00", value)
    return line


def _iter_markdown_destinations(text: str) -> Iterator[tuple[int, int, str, bool]]:
    """Yield destination spans for inline/image Markdown links.

    A small balanced-parenthesis scanner handles filenames such as ``a (b).md``.
    The boolean says whether the syntax is an image.
    """
    index = 0
    while index < len(text):
        bracket = text.find("](", index)
        if bracket < 0:
            break
        label_start = text.rfind("[", 0, bracket)
        if label_start < 0:
            index = bracket + 2
            continue
        is_image = label_start > 0 and text[label_start - 1] == "!"
        start = bracket + 2
        depth = 1
        cursor = start
        escaped = False
        while cursor < len(text):
            char = text[cursor]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    break
            cursor += 1
        if depth:
            break
        raw = text[start:cursor]
        # Optional title follows whitespace. Angle brackets protect spaces.
        if raw.startswith("<") and ">" in raw:
            end = raw.find(">") + 1
            destination = raw[1 : end - 1]
            dest_start, dest_end = start + 1, start + end - 1
        else:
            title = re.search(r"\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\))\s*$", raw)
            destination = raw[: title.start()] if title else raw
            dest_start, dest_end = start, start + len(destination)
        yield dest_start, dest_end, destination, is_image
        index = cursor + 1


def _rewrite_markdown(
    text: str,
    *,
    source_old: str,
    source_new: str,
    by_old: dict[str, dict[str, Any]],
    old_index: _Index,
    new_index: _Index,
    source_is_mapped: bool,
) -> tuple[str, list[dict[str, Any]]]:
    changes: list[dict[str, Any]] = []
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    fence: tuple[str, int] | None = None
    in_comment = False

    for line_number, raw_line in enumerate(lines, 1):
        fence_match = _FENCE_RE.match(raw_line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = (marker[0], len(marker))
            elif marker[0] == fence[0] and len(marker) >= fence[1]:
                fence = None
            output.append(raw_line)
            continue
        if fence:
            output.append(raw_line)
            continue

        line, saved, in_comment = _protected_spans(raw_line, in_comment)

        def wiki_replace(match: re.Match[str]) -> str:
            target, delimiter, alias = _split_alias(match.group(2))
            rewritten, status, resolved = _rewrite_one_target(
                target,
                source_old=source_old,
                source_new=source_new,
                by_old=by_old,
                old_index=old_index,
                new_index=new_index,
                source_is_mapped=source_is_mapped,
                style="wiki",
            )
            if status == "rewritten" and rewritten != target:
                changes.append({
                    "line": line_number, "kind": "embed" if match.group(1) else "wikilink",
                    "old_target": target, "new_target": rewritten, "resolved_old": resolved,
                })
            return f"{match.group(1)}[[{rewritten}{delimiter}{alias}]]"

        line = _WIKI_RE.sub(wiki_replace, line)
        replacements: list[tuple[int, int, str, str, bool, str | None]] = []
        for start, end, target, is_image in _iter_markdown_destinations(line):
            if _is_remote(target):
                continue
            rewritten, status, resolved = _rewrite_one_target(
                target,
                source_old=source_old,
                source_new=source_new,
                by_old=by_old,
                old_index=old_index,
                new_index=new_index,
                source_is_mapped=source_is_mapped,
                style="markdown",
            )
            if status == "rewritten" and rewritten != target:
                replacements.append((start, end, target, rewritten, is_image, resolved))
        for start, end, old_target, new_target, is_image, resolved in reversed(replacements):
            line = line[:start] + new_target + line[end:]
            changes.append({
                "line": line_number, "kind": "image" if is_image else "markdown",
                "old_target": old_target, "new_target": new_target, "resolved_old": resolved,
            })

        # Reference definitions: [name]: destination "optional title"
        ref = re.match(r"^(\s{0,3}\[(?!\^)[^\]]+\]:\s*)(<[^>]+>|\S+)(.*)$", line)
        if ref:
            wrapped = ref.group(2).startswith("<")
            target = ref.group(2)[1:-1] if wrapped else ref.group(2)
            if not _is_remote(target):
                rewritten, status, resolved = _rewrite_one_target(
                    target, source_old=source_old, source_new=source_new,
                    by_old=by_old, old_index=old_index, new_index=new_index,
                    source_is_mapped=source_is_mapped, style="markdown",
                )
                if status == "rewritten" and rewritten != target:
                    rendered = f"<{rewritten}>" if wrapped else rewritten
                    line = ref.group(1) + rendered + ref.group(3)
                    changes.append({
                        "line": line_number, "kind": "reference",
                        "old_target": target, "new_target": rewritten,
                        "resolved_old": resolved,
                    })
        output.append(_restore_spans(line, saved))
    return "".join(output), changes


def _rewrite_canvas(
    text: str,
    *,
    source_old: str,
    source_new: str,
    by_old: dict[str, dict[str, Any]],
    old_index: _Index,
    new_index: _Index,
    source_is_mapped: bool,
) -> tuple[str, list[dict[str, Any]]]:
    data = json.loads(text)
    changes: list[dict[str, Any]] = []
    nodes = data.get("nodes", []) if isinstance(data, dict) else []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or node.get("type") != "file" or not isinstance(node.get("file"), str):
            continue
        target = node["file"]
        rewritten, status, resolved = _rewrite_one_target(
            target, source_old=source_old, source_new=source_new,
            by_old=by_old, old_index=old_index, new_index=new_index,
            source_is_mapped=source_is_mapped, style="canvas",
        )
        if status == "rewritten" and rewritten != target:
            node["file"] = rewritten
            changes.append({
                "line": None, "kind": "canvas_file", "node": index,
                "old_target": target, "new_target": rewritten,
                "resolved_old": resolved,
            })
    if not changes:
        return text, []
    trailing = "\n" if text.endswith("\n") else ""
    return json.dumps(data, ensure_ascii=False, indent=2) + trailing, changes


def rewrite_tree(stage: Path, mapping: list[dict[str, Any]]) -> dict[str, Any]:
    """Rewrite mapped internal references in an already-created staging tree.

    Mapping paths are relative POSIX paths.  ``old`` is relative to the live
    vault (normally begins with ``TBM/``); ``new`` is relative to ``stage``.
    Historical/original/governance mapping entries are inventoried but never
    rewritten.
    """
    stage = Path(stage)
    if not stage.is_dir():
        raise ValueError(f"stage is not a directory: {stage}")
    by_old, old_for_new, old_index = _mapping_indexes(mapping)
    new_index = _Index(_current_paths(stage))
    report: dict[str, Any] = {
        "schema": "wwl-link-rewrite-v1",
        "stage": str(stage),
        "files_scanned": 0,
        "files_changed": 0,
        "references_changed": 0,
        "changes": [],
        "preserved": [
            {key: item.get(key) for key in ("old", "new", "role", "sha256", "action")}
            for item in by_old.values() if _role_is_preserved(item.get("role"))
        ],
        "preserved_files": [],
        "errors": [],
    }

    for path in sorted(stage.rglob("*")):
        if not path.is_file() or any(part.startswith(".") for part in path.relative_to(stage).parts):
            continue
        rel_new = path.relative_to(stage).as_posix()
        if path.suffix.lower() not in {".md", ".canvas"}:
            continue
        source_old = old_for_new.get(rel_new, rel_new)
        mapping_item = by_old.get(source_old)
        if mapping_item and _role_is_preserved(mapping_item.get("role")):
            report["preserved_files"].append({
                "path": rel_new, "old": source_old, "role": mapping_item.get("role"),
                "sha256": mapping_item.get("sha256"), "action": mapping_item.get("action"),
            })
            continue
        report["files_scanned"] += 1
        try:
            original = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".md":
                rewritten, changes = _rewrite_markdown(
                    original, source_old=source_old, source_new=rel_new,
                    by_old=by_old, old_index=old_index, new_index=new_index,
                    source_is_mapped=mapping_item is not None,
                )
            else:
                rewritten, changes = _rewrite_canvas(
                    original, source_old=source_old, source_new=rel_new,
                    by_old=by_old, old_index=old_index, new_index=new_index,
                    source_is_mapped=mapping_item is not None,
                )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            report["errors"].append({"path": rel_new, "error": str(exc)})
            continue
        if changes:
            path.write_text(rewritten, encoding="utf-8")
            report["files_changed"] += 1
            report["references_changed"] += len(changes)
            report["changes"].append({
                "path": rel_new, "source_old": source_old, "references": changes,
            })
    return report


def _current_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        paths.append(rel.as_posix())
    return paths


def _slug(text: str) -> str:
    # A practical Obsidian-compatible comparison for explicit heading links.
    text = re.sub(r"[*_~`]", "", text.strip()).casefold()
    text = re.sub(r"[^\w\-\u4e00-\u9fff ]", "", text)
    return re.sub(r"\s+", "-", text)


def _anchors(path: Path) -> tuple[set[str], set[str]]:
    headings: set[str] = set()
    blocks: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return headings, blocks
    fence: tuple[str, int] | None = None
    for line in lines:
        match = _FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker[0], len(marker)
            elif marker[0] == fence[0] and len(marker) >= fence[1]:
                fence = None
            continue
        if fence:
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            title = heading.group(1).strip()
            headings.update({title, title.casefold(), _slug(title)})
        block = _BLOCK_RE.search(line)
        if block:
            blocks.add(block.group(1))
    return headings, blocks


def _diag(path: str, line: int | None, target: str, **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": path, "line": line, "target": target,
        "scope": _historical_scope("/" + path),
    }
    result.update(extra)
    return result


def _validate_reference(
    *,
    root: Path,
    index: _Index,
    source: str,
    line: int | None,
    target: str,
    is_image: bool,
    style: str,
    report: dict[str, Any],
) -> None:
    path_part, anchor = _split_anchor(target)
    if _is_remote(path_part):
        return
    resolved, status = _resolve_target(
        path_part, source, index, root_relative=style in {"wiki", "canvas"}
    )
    if status == "ambiguous":
        report["ambiguous"].append(_diag(source, line, target))
        return
    if not resolved:
        bucket = "images" if is_image or PurePosixPath(unquote(path_part)).suffix.lower() in _IMAGE_EXTENSIONS else "missing"
        report[bucket].append(_diag(source, line, target, reason="missing"))
        return
    if status == "case_mismatch":
        report["case_conflicts"].append(_diag(source, line, target, resolved=resolved, reason="reference_case"))
    if anchor and resolved.lower().endswith(".md"):
        headings, blocks = _anchors(root / resolved)
        value = unquote(anchor[1:])
        if value.startswith("^"):
            valid = value[1:] in blocks
        else:
            valid = value in headings or value.casefold() in headings or _slug(value) in headings
        if not valid:
            report["anchors"].append(_diag(source, line, target, resolved=resolved, reason="missing_anchor"))


def _audit_markdown(root: Path, path: Path, index: _Index, report: dict[str, Any]) -> None:
    rel = path.relative_to(root).as_posix()
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeDecodeError) as exc:
        report["missing"].append(_diag(rel, None, rel, reason=f"unreadable: {exc}"))
        return
    fence: tuple[str, int, int] | None = None
    in_comment = False
    for number, raw_line in enumerate(lines, 1):
        fence_match = _FENCE_RE.match(raw_line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker[0], len(marker), number
            elif marker[0] == fence[0] and len(marker) >= fence[1]:
                fence = None
            continue
        if fence:
            continue
        line, _, in_comment = _protected_spans(raw_line, in_comment)
        for match in _WIKI_RE.finditer(line):
            target, _, _ = _split_alias(match.group(2))
            ext = PurePosixPath(_split_anchor(unquote(target))[0]).suffix.lower()
            _validate_reference(
                root=root, index=index, source=rel, line=number, target=target,
                is_image=bool(match.group(1)) and ext in _IMAGE_EXTENSIONS,
                style="wiki",
                report=report,
            )
        for _, _, target, is_image in _iter_markdown_destinations(line):
            _validate_reference(
                root=root, index=index, source=rel, line=number, target=target,
                is_image=is_image, report=report,
                style="markdown",
            )
        ref = re.match(r"^\s{0,3}\[(?!\^)[^\]]+\]:\s*(<[^>]+>|\S+)", line)
        if ref:
            raw = ref.group(1)
            target = raw[1:-1] if raw.startswith("<") else raw
            _validate_reference(
                root=root, index=index, source=rel, line=number, target=target,
                is_image=False, report=report,
                style="markdown",
            )
    if fence:
        report["fences"].append(_diag(rel, fence[2], fence[0] * fence[1], reason="unclosed_fence"))


def _audit_canvas(root: Path, path: Path, index: _Index, report: dict[str, Any]) -> None:
    rel = path.relative_to(root).as_posix()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        report["canvas"].append(_diag(rel, None, rel, reason="invalid_json", error=str(exc)))
        return
    if not isinstance(data, dict) or not isinstance(data.get("nodes", []), list):
        report["canvas"].append(_diag(rel, None, rel, reason="invalid_shape"))
        return
    for number, node in enumerate(data.get("nodes", [])):
        if isinstance(node, dict) and node.get("type") == "file":
            target = node.get("file")
            if not isinstance(target, str):
                report["canvas"].append(_diag(rel, None, str(target), node=number, reason="invalid_file_node"))
                continue
            before = len(report["missing"])
            _validate_reference(
                root=root, index=index, source=rel, line=None, target=target,
                is_image=PurePosixPath(target).suffix.lower() in _IMAGE_EXTENSIONS,
                style="canvas",
                report=report,
            )
            if len(report["missing"]) > before:
                diagnostic = report["missing"].pop()
                diagnostic["node"] = number
                report["canvas"].append(diagnostic)


def audit_tree(root: Path) -> dict[str, Any]:
    """Read-only structural audit of visible Markdown, JSON, and Canvas files."""
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f"root is not a directory: {root}")
    paths = _current_paths(root)
    index = _Index(paths)
    report: dict[str, Any] = {
        "schema": "wwl-link-audit-v1",
        "root": str(root),
        "files_scanned": 0,
        "yaml_parser": "not_required; frontmatter wikilinks scanned as Markdown",
        "missing": [], "ambiguous": [], "anchors": [], "images": [],
        "json": [], "canvas": [], "case_conflicts": [], "fences": [],
    }
    for folded, variants in sorted(index.casefold.items()):
        if len(variants) > 1:
            for variant in variants:
                report["case_conflicts"].append(_diag(variant, None, folded, variants=variants, reason="path_collision"))
    for rel in paths:
        path = root / rel
        suffix = path.suffix.lower()
        if suffix == ".md":
            report["files_scanned"] += 1
            _audit_markdown(root, path, index, report)
        elif suffix == ".canvas":
            report["files_scanned"] += 1
            _audit_canvas(root, path, index, report)
        elif suffix == ".json":
            # Validate syntax only.  Never inspect keys/values of arbitrary JSON;
            # this keeps the audit away from hidden or embedded local secrets.
            report["files_scanned"] += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                report["json"].append(_diag(rel, None, rel, reason="invalid_json", error=str(exc)))
    report["counts"] = {
        key: len(report[key])
        for key in ("missing", "ambiguous", "anchors", "images", "json", "canvas", "case_conflicts", "fences")
    }
    report["active_counts"] = {
        key: sum(item.get("scope") == "active" for item in report[key])
        for key in report["counts"]
    }
    report["historical_counts"] = {
        key: sum(item.get("scope") == "historical" for item in report[key])
        for key in report["counts"]
    }
    report["scope_counts"] = {
        key: {
            scope: sum(item.get("scope") == scope for item in report[key])
            for scope in ("active", "historical", "original", "governance")
        }
        for key in report["counts"]
    }
    return report


__all__ = ["rewrite_tree", "audit_tree"]
