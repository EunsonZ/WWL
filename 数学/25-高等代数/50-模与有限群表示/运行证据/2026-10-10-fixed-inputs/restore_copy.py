"""Restore a new historical execution layout; never run experiments or overwrite files."""
import hashlib
import json
from pathlib import Path
import shutil
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 -B restore_copy.py /absolute/new-empty-directory")
    root = Path(__file__).resolve().parent
    dest = Path(sys.argv[1]).expanduser().resolve()
    if dest == root or root in dest.parents or dest.exists():
        raise SystemExit("choose a new directory outside the read-only evidence package")
    mapping = json.loads((root / "copy-map.json").read_text())
    validated = []
    for item in mapping["files"]:
        relative = Path(item["source"])
        copy = root / item["copy"]
        if relative.is_absolute() or ".." in relative.parts or not copy.is_relative_to(root):
            raise SystemExit("unsafe copy mapping")
        raw = copy.read_bytes()
        if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise SystemExit("evidence byte check failed: " + item["source"])
        validated.append((copy, relative))
    dest.mkdir(parents=True, exist_ok=False)
    for copy, relative in validated:
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(copy, target)
    for name in ("home", "tmp", "state", "logs"):
        (dest / name).mkdir(exist_ok=True)
    print("Restored " + str(len(validated)) + " byte-identical historical files; no experiment executed.")
    print("Historical logs were restored. Prepare a separate empty work copy without any logs before a rerun.")
    print("Do not merely change job names: the oracle reads logs/fixed-cli.stdout. See the portable README.")


if __name__ == "__main__":
    main()
