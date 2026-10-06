"""Read-only Markdown/Obsidian reference checks (standard library).

Adapted from the vault's 2026-09-08 TBM links.py: fence state, balanced
destinations, exact paths before short names. Historical migration aliases,
rewrite operations and scope-based exemptions are deliberately not inherited.
This is a bounded static parser, not Obsidian's renderer; see CHECKS.md.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import os
import posixpath
import re
import unicodedata
from urllib.parse import unquote


def diagnostic(rule, path, line=None, severity="error", **details):
    return dict(rule=rule, severity=severity, path=path, line=line, **details)


def inventory(root):
    """Inventory visible files without following directory/file symlinks."""
    paths, issues = [], []
    for folder, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(d for d in directories if not d.startswith("."))
        for name in list(directories) + sorted(names):
            if name.startswith("."):
                continue
            path = Path(folder) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                issues.append(diagnostic("symlink_not_read", rel, severity="review"))
                if name in directories:
                    directories.remove(name)
            elif path.is_file():
                paths.append(rel)
    return sorted(paths), issues


@dataclass(frozen=True)
class Fence:
    start: int
    body_start: int
    body_end: int
    end: int
    indent: int


def scan(text, *, inline=True):
    """Blank code/comments without shifting offsets; also locate mirror blocks.

    A code-sync marker is active only as its own HTML comment on a line.
    Comments and code spans are consumed before scanning their inner content.
    """
    masked = list(text)
    fences, markers, issues = [], [], []
    cursor = 0

    def blank(start, end):
        for i in range(start, end):
            if text[i] != "\n":
                masked[i] = " "

    while cursor < len(text):
        line_start = cursor == 0 or text[cursor - 1] == "\n"
        if line_start:
            opening = re.match(r" {0,3}(`{3,}|~{3,})([^\n]*)(?:\n|$)", text[cursor:])
            container_prefix = ""
            container = re.match(r"((?: {0,3}>[ \t]?)+[ \t]*| {4,})(`{3,}|~{3,})([^\n]*)(?:\n|$)", text[cursor:])
            if not opening and container:
                container_prefix = container[1]
                # Preserve offsets by matching the opening after the prefix.
                opening = re.match(r"(`{3,}|~{3,})([^\n]*)(?:\n|$)", text[cursor + len(container_prefix):])
            if opening and not (opening[1][0] == "`" and "`" in opening[2]):
                token = opening[1]
                body_start = cursor + len(container_prefix) + opening.end()
                prefix_pattern = re.escape(container_prefix) if container_prefix else " {0,3}"
                close = re.compile(r"^" + prefix_pattern + re.escape(token[0]) + "{" + str(len(token)) + r",}[ \t]*\r?$", re.M).search(text, body_start)
                if close:
                    end = close.end() + (close.end() < len(text) and text[close.end()] == "\n")
                    fences.append(Fence(cursor, body_start, close.start(), end,
                                        len(opening[0]) - len(opening[0].lstrip(" "))))
                else:
                    end = len(text)
                    issues.append(("unclosed_fence", text.count("\n", 0, cursor) + 1))
                blank(cursor, end)
                cursor = end
                continue
        if text.startswith("<!--", cursor) or text.startswith("%%", cursor):
            html = text.startswith("<!--", cursor)
            terminator = "-->" if html else "%%"
            close = text.find(terminator, cursor + (4 if html else 2))
            end = len(text) if close < 0 else close + len(terminator)
            comment = text[cursor:end]
            prior = text[text.rfind("\n", 0, cursor) + 1:cursor]
            next_break = text.find("\n", end)
            after = text[end:next_break if next_break >= 0 else len(text)]
            marker = re.fullmatch(r"<!--\s*code-sync:\s*([^\n]+?)\s*-->", comment)
            if marker and not prior.strip() and not after.strip():
                markers.append((cursor, end, marker[1]))
            if close < 0:
                issues.append(("unclosed_comment", text.count("\n", 0, cursor) + 1))
            blank(cursor, end)
            cursor = end
            continue
        html_code = re.match(r"<(code|pre)(?:\s[^>]*)?>", text[cursor:], re.I)
        if html_code:
            closing = re.compile(r"</" + html_code[1] + r"\s*>", re.I).search(text, cursor + html_code.end())
            if closing:
                blank(cursor, closing.end())
                cursor = closing.end()
                continue
        if text[cursor] == "`" and (cursor == 0 or text[cursor - 1] != "\\"):
            run = re.match(r"`+", text[cursor:])[0]
            closing = re.compile(r"(?<!`)" + re.escape(run) + r"(?!`)").search(text, cursor + len(run))
            if closing and not re.search(r"\n[ \t]*\r?\n", text[cursor:closing.start()]):
                if inline:
                    blank(cursor, closing.end())
                cursor = closing.end()
                continue
        # An escaped punctuation cannot open syntax (including comments).
        cursor += 2 if text[cursor] == "\\" and cursor + 1 < len(text) else 1
    return "".join(masked), fences, markers, issues


def split_frontmatter(text):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text, 0
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            return "".join(lines[1:index]), "".join(lines[index + 1:]), index + 1
    return "", text, -1


def simple_aliases(text):
    """Read only plain/quoted scalar alias lists; never claim YAML validation.

    Complex YAML aliases require the optional full YAML layer. Unknown forms
    return no aliases plus a review diagnostic, rather than guessing values.
    """
    front, _, _ = split_frontmatter(text)
    if front is None:
        return [], False
    match = re.search(r"^aliases:[ \t]*(.*)$", front, re.M)
    if not match:
        return [], False
    tail = match[1].strip()
    if tail.startswith("[") and tail.endswith("]"):
        inner = tail[1:-1]
        parts = re.findall(r'''"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^,]+''', inner)
    elif not tail:
        parts = []
        for line in front[match.end():].splitlines():
            if not line.strip():
                continue
            item = re.match(r"^[ \t]*-[ \t]+(.*?)\s*$", line)
            if not item:
                break
            parts.append(item[1])
    else:
        return [], True
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith('"'):
            import json
            try:
                part = json.loads(part)
            except (ValueError, TypeError):
                return [], True
        elif part.startswith("'") and part.endswith("'"):
            part = part[1:-1].replace("''", "'")
        elif any(x in part for x in ("#", "&", "*", "{", "}", "[", "]", ": ")):
            return [], True
        if not isinstance(part, str):
            return [], True
        result.append(part)
    return result, False


def _normal(path):
    return posixpath.normpath(path)


class Index:
    def __init__(self, paths, aliases=None):
        self.paths = set(paths)
        self.names = defaultdict(list)
        self.folded = defaultdict(list)
        self.aliases = aliases or {}
        self.anchor_cache = {}
        for path in sorted(paths):
            self.names[PurePosixPath(path).name].append(path)
            if path.endswith(".md"):
                self.names[PurePosixPath(path).stem].append(path)
            self.folded[unicodedata.normalize("NFC", path).casefold()].append(path)

    def exact(self, target, *, extension=True):
        target = _normal(target)
        if target == ".." or target.startswith("../") or target.startswith("/"):
            return None, "outside_root"
        forms = [target] + ([target + ".md"] if extension and not target.endswith(".md") else [])
        for form in forms:
            if form in self.paths:
                return form, "exact"
            hits = self.folded.get(unicodedata.normalize("NFC", form).casefold(), [])
            if hits:
                return (hits[0], "case_or_unicode_mismatch") if len(hits) == 1 else (None, "ambiguous")
        return None, "missing"

    def resolve(self, raw, source, style="wiki"):
        target = unquote(re.sub(r"\\([ ()\[\]#])", r"\1", raw.strip()))
        if not target:
            return source, "self"
        if re.match(r"[a-zA-Z][\w+.-]*:", target) or target.startswith("//"):
            return None, "external"
        if "\\" in target:
            return None, "noncanonical_path"
        parent = str(PurePosixPath(source).parent)
        if style == "markdown":
            # Markdown never falls back to a global stem or a root basename.
            candidate = target.lstrip("/") if target.startswith("/") else parent + "/" + target
            return self.exact(candidate)
        if target.startswith("."):
            return self.exact(parent + "/" + target)
        if "/" in target:
            return self.exact(target.lstrip("/"))
        # Short wiki references: local sibling before unique global name.
        found, status = self.exact(parent + "/" + target)
        if found or status != "missing":
            return found, status
        hits = sorted(set(self.names.get(target, [])))
        by_alias = not hits
        if not hits:
            hits = sorted(set(self.aliases.get(target, [])))
        if len(hits) == 1:
            return hits[0], "alias_candidate" if by_alias else "unique_name"
        return None, "ambiguous" if hits else "missing"


def markdown_destinations(text):
    """Balanced destination scanner derived from the existing TBM parser."""
    cursor = 0
    while cursor < len(text):
        marker = text.find("](", cursor)
        if marker < 0:
            return
        label = text.rfind("[", cursor, marker)
        if label < 0 or (label > 0 and text[label - 1] in "\\["):
            cursor = marker + 2
            continue
        start = marker + 2
        current, depth, angle, title_quote = start, 1, False, None
        while current < len(text):
            char = text[current]
            if char == "\\":
                current += 2
                continue
            if title_quote:
                if char == title_quote:
                    title_quote = None
            elif not angle and char in "\"'" and current > start and text[current - 1].isspace():
                title_quote = char
            elif current == start and char == "<":
                angle = True
            elif angle and char == ">":
                angle = False
            elif not angle and char == "(":
                depth += 1
            elif not angle and char == ")":
                depth -= 1
                if depth == 0:
                    break
            current += 1
        if depth:
            cursor = marker + 2
            continue
        raw = text[start:current].strip()
        if raw.startswith("<") and ">" in raw:
            target = raw[1:raw.find(">")]
        else:
            title = re.search(r'''\s+(?:"[^"]*"|'[^']*'|\([^)]*\))\s*$''', raw)
            target = raw[:title.start()] if title else raw
        yield label, target, label > 0 and text[label - 1] == "!"
        cursor = current + 1


def references(text):
    clean, _, _, _ = scan(text)
    for match in re.finditer(r"(?<![\\\[])!?\[\[([^\]\n]+)\]\]", clean):
        target = re.split(r"\\\||(?<!\\)\|", match[1], maxsplit=1)[0].strip()
        yield text.count("\n", 0, match.start()) + 1, target, "wiki", match[0].startswith("!")
    for start, target, embedded in markdown_destinations(clean):
        yield text.count("\n", 0, start) + 1, target, "markdown", embedded
    # Definitions are checked once, regardless of how many reference uses.
    for match in re.finditer(r"^ {0,3}\[(?!\^)[^\]\n]+\]:\s*(<[^>\n]+>|\S+)", clean, re.M):
        yield text.count("\n", 0, match.start()) + 1, match[1].strip("<>"), "markdown", False


def title_text(value):
    value = re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])", r"\1", value)
    value = re.sub(r"!?\[\[([^]|]+)(?:\|([^]]+))?\]\]", lambda m: m[2] or m[1], value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[*_~`]", "", value)
    return value.strip()


def slug(value):
    value = re.sub(r"[^\w\- ]", "", title_text(value).casefold())
    return re.sub(r"\s", "-", value)


def anchors(text):
    _, body, _ = split_frontmatter(text)
    clean, _, _, _ = scan(body, inline=False)
    syntax, _, _, _ = scan(body)
    titles, blocks, slugs = set(), set(), set()
    duplicates = Counter()
    lines = clean.splitlines()
    syntax_lines = syntax.splitlines()
    for number, line in enumerate(lines):
        is_heading = re.match(r"^ {0,3}#{1,6}[ \t]+", syntax_lines[number])
        match = re.match(r"^ {0,3}#{1,6}[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$", line) if is_heading else None
        if match:
            title = title_text(match[1])
        elif number and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", syntax_lines[number]) and syntax_lines[number - 1].strip():
            title = title_text(lines[number - 1])
        else:
            title = None
        if title:
            titles.add(title)
            base = slug(title)
            suffix = "" if not duplicates[base] else "-" + str(duplicates[base])
            slugs.add(base + suffix)
            duplicates[base] += 1
        block = re.search(r"(?:^|\s)\^([A-Za-z0-9_-]+)\s*$", syntax_lines[number])
        if block:
            blocks.add(block[1])
    return titles, blocks, slugs


def check_reference(index, notes, source, line, target, style="wiki", embedded=False):
    path, sep, anchor = target.partition("#")
    if style == "markdown":
        path = path.split("?", 1)[0]
    resolved, status = index.resolve(path, source, style)
    if status == "external":
        return [], None
    details = dict(target=target, resolved=resolved, kind="embed" if embedded else style)
    if not resolved:
        severity = "review" if status == "ambiguous" else "error"
        return [diagnostic("link_" + status, source, line, severity, **details)], None
    issues = []
    if status == "alias_candidate":
        issues.append(diagnostic("alias_target_needs_ui_review", source, line, "review", **details))
    if status == "case_or_unicode_mismatch":
        issues.append(diagnostic("link_" + status, source, line, **details))
    if sep and resolved in notes:
        if resolved not in index.anchor_cache:
            index.anchor_cache[resolved] = anchors(notes[resolved])
        titles, blocks, slugs = index.anchor_cache[resolved]
        value = unquote(anchor)
        if "#" in value and not value.startswith("^"):
            issues.append(diagnostic("heading_path_not_checked", source, line, "review", **details))
            return issues, resolved
        if value.startswith("^") and not re.fullmatch(r"[A-Za-z0-9-]+", value[1:]):
            issues.append(diagnostic("block_id_syntax_not_checked", source, line, "review", **details))
            return issues, resolved
        valid = value[1:] in blocks if value.startswith("^") else value in titles or (style == "markdown" and value in slugs)
        if not valid:
            issues.append(diagnostic("link_missing_anchor", source, line, **details))
    elif sep and not resolved.endswith(".md"):
        issues.append(diagnostic("attachment_anchor_not_checked", source, line, "review", **details))
    return issues, resolved


def table_wiki_alias_issues(text, path):
    """Flag an alias separator only inside a header+delimiter Markdown table."""
    syntax, _, _, _ = scan(text, inline=True)
    lines = syntax.splitlines()
    delimiter = re.compile(r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$")
    alias = re.compile(r"(?<!\\)\[\[[^\]\n]*?(?<!\\)\|[^\]\n]*?\]\]")
    active = set()
    for index, line in enumerate(lines):
        if not delimiter.fullmatch(line) or index == 0:
            continue
        header = lines[index - 1]
        if not header.strip() or "|" not in header:
            continue
        active.add(index - 1)
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].strip() and "|" in lines[cursor]:
            active.add(cursor)
            cursor += 1
    for index in sorted(active):
        if alias.search(lines[index]):
            yield diagnostic("table_wiki_alias_unescaped", path, index + 1)


def read_notes(root, paths):
    """Load visible Markdown once and keep unreadable-file diagnostics separate."""
    root = Path(root).resolve()
    notes, issues = {}, []
    for path in paths:
        if path.endswith(".md"):
            try:
                notes[path] = (root / path).read_bytes().decode("utf-8")
            except (UnicodeError, OSError):
                issues.append(diagnostic("note_unreadable", path))
    return notes, issues


def audit(root, paths=None, aliases=None, *, notes=None, note_issues=()):
    """Audit links, optionally reusing one already loaded Markdown snapshot."""
    root = Path(root).resolve()
    paths, issues = inventory(root) if paths is None else (paths, [])
    if notes is None:
        notes, loaded_issues = read_notes(root, paths)
        issues.extend(loaded_issues)
    else:
        issues.extend(note_issues)
    alias_map = defaultdict(list)
    for path, text in notes.items():
        extracted, unsupported = simple_aliases(text)
        if aliases is not None:
            extracted = aliases.get(path, [])
            unsupported = False
        if unsupported:
            issues.append(diagnostic("alias_syntax_not_checked", path, severity="review"))
        for alias in extracted:
            alias_map[alias].append(path)
    index = Index(paths, alias_map)
    for hits in index.folded.values():
        if len(hits) > 1:
            issues.append(diagnostic("path_case_or_unicode_collision", hits[0], variants=hits))
    resolved_links, checked = [], 0
    for path, text in notes.items():
        _, _, _, syntax = scan(text)
        issues.extend(diagnostic(rule, path, line) for rule, line in syntax)
        issues.extend(table_wiki_alias_issues(text, path))
        for line, target, style, embedded in references(text):
            checked += 1
            found, resolved = check_reference(index, notes, path, line, target, style, embedded)
            issues.extend(found)
            if resolved:
                resolved_links.append(dict(path=path, line=line, target=target, resolved=resolved))
    return dict(checked=checked, markdown_files=len(notes), issues=issues,
                resolved_links=resolved_links), notes, index
