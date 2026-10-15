"""Compare active code-sync blocks with canonical files; never execute them."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from links import Index, diagnostic, inventory, scan


def check(root, *, paths=None, notes=None):
    root = Path(root).resolve()
    paths, issues = inventory(root) if paths is None else (paths, [])
    index = Index(paths)
    if notes is None:
        notes = {}
        for path in paths:
            if path.endswith(".md"):
                try:
                    notes[path] = (root / path).read_bytes().decode("utf-8")
                except (UnicodeError, OSError):
                    issues.append(diagnostic("note_unreadable", path))
    checked, markers_seen = 0, 0
    for path, text in notes.items():
        _, fences, markers, _ = scan(text)
        for start, end, target in markers:
            markers_seen += 1
            line = text.count("\n", 0, start) + 1
            fence = next((f for f in fences if f.start >= end and not text[end:f.start].strip()), None)
            if not fence:
                issues.append(diagnostic("mirror_missing_fence", path, line, source=target))
                continue
            if target.startswith("."):
                source, status = index.exact(str(Path(path).parent / target), extension=False)
            elif "/" in target:
                source, status = index.exact(target)
            else:
                # Established contract: root first, then same-directory file.
                source, status = index.exact(target, extension=False)
                if status == "missing":
                    source, status = index.exact(str(Path(path).parent / target), extension=False)
            if not source or status not in {"exact", "self"}:
                issues.append(diagnostic("mirror_source_" + status, path, line, source=target))
                continue
            if source.endswith((".pem", ".key")):
                issues.append(diagnostic("mirror_source_not_code", path, line, source=source))
                continue
            try:
                canonical = (root / source).read_bytes().decode("utf-8")
            except (UnicodeError, OSError):
                issues.append(diagnostic("mirror_source_unreadable", path, line, source=source))
                continue
            actual = text[fence.body_start:fence.body_end]
            if fence.indent:
                actual = re.sub(r"^ {0," + str(fence.indent) + r"}", "", actual, flags=re.M)
            # Ignore only the single terminal newline needed to close a fence.
            # Extra blank lines, spaces and source contents remain significant.
            expected = canonical if canonical.endswith("\n") else canonical + "\n"
            checked += 1
            if actual != expected:
                issues.append(diagnostic("mirror_mismatch", path, line, source=source))
    return dict(checked=checked, markers=markers_seen, issues=issues)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", type=Path, help="write new evidence file outside --root")
    args = parser.parse_args(argv)
    from check_vault import write_report
    if not args.root.is_dir():
        parser.error("--root must name an existing directory")
    report = dict(schema="wwl-mirrors-v1", **check(args.root))
    try:
        write_report(report, args.root, args.json)
    except (OSError, ValueError):
        parser.error("evidence path must be a new file outside --root in an existing directory")
    print(json.dumps({"checked": report["checked"], "issues": len(report["issues"])}, ensure_ascii=False))
    return int(any(x["severity"] in {"critical", "error"} for x in report["issues"]))


if __name__ == "__main__":
    raise SystemExit(main())
