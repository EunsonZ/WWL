"""Prepare a fresh copy and run the fixed numeric protocol; never alter archived logs.

Restore receipt-checked inputs from a fixed Git commit and retained r1 bytes.
Historical observations remain separate in raw/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def digest(data):
    return hashlib.sha256(data).hexdigest()


FIXED_REF = "3f9aa24095230fd8116fc780cb00d75b9fc90a56"
RETAINED_R1 = {
    "snapshot/数学/36-拓扑学/10-覆盖空间与van-Kampen/05-普适覆盖存在与子群分类.md",
    "snapshot/数学/36-拓扑学/20-同调与上同调/03-圆周环面RP2的整数同调与挠.md",
    "snapshot/数学/36-拓扑学/20-同调与上同调/80-有限链与杯积复算.md",
}


def fresh_copy(destination, repository):
    source = Path(__file__).resolve().parent
    receipt = json.loads((source / "copy-receipt.json").read_text(encoding="utf-8"))
    helpers = {"prepare_expectations.py", "execute_oracle.py", "oracle_core.py", "verify_protocol.py"}
    selected = [e for e in receipt["files"]
                if e["original_path"].startswith(("snapshot/", "dependency152/"))
                or e["original_path"] in helpers]
    # Git accepts -C at a subdirectory; containment must use the real worktree root.
    repository = Path(subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--show-toplevel"],
        capture_output=True, check=True, timeout=60, text=True).stdout.strip()).resolve()
    # Resolve only the pinned commit; current main and local edits are not inputs.
    if destination.is_relative_to(repository):
        raise ValueError("--new-dir must be outside --repo")
    inputs = {}
    for entry in selected:
        original = entry["original_path"]
        if original == "dependency152/integer_smith.py":
            git_path = "数学/25-高等代数/50-模与有限群表示/code/integer_smith.py"
        elif original.startswith("snapshot/") and original not in RETAINED_R1:
            git_path = original.removeprefix("snapshot/")
        else:
            git_path = None
        if git_path is None:
            data = (source / entry["portable_path"]).read_bytes()
        else:
            data = subprocess.run(
                ["git", "-C", str(repository), "show", FIXED_REF + ":" + git_path],
                capture_output=True, check=True, timeout=60).stdout
        if len(data) != entry["bytes"] or digest(data) != entry["sha256"]:
            raise ValueError("fixed input byte mismatch: " + original)
        inputs[original] = data
    destination.mkdir(parents=True, exist_ok=False)
    for entry in selected:
        target = destination / entry["original_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(inputs[entry["original_path"]])
    for name in ("logs", "tmp", "state"):
        (destination / name).mkdir()
    return selected


def run_child(root, name, relative_cwd, arguments):
    out = root / "logs" / (name + ".stdout")
    err = root / "logs" / (name + ".stderr")
    rec = root / "logs" / (name + ".json")
    if any(p.exists() for p in (out, err, rec)):
        raise FileExistsError("fresh child logs already exist")
    env = os.environ.copy()
    requested = {key: "1" for key in (
        "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")}
    env.update(requested)
    env["TMPDIR"] = str(root / "tmp")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    begin = time.monotonic()
    try:
        result = subprocess.run(arguments, cwd=root / relative_cwd, env=env,
                                capture_output=True, timeout=60, check=False)
        code, stdout, stderr, status = result.returncode, result.stdout, result.stderr, "completed"
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr, status = None, exc.stdout or b"", exc.stderr or b"", "timeout"
    out.write_bytes(stdout)
    err.write_bytes(stderr)
    report = {"command": arguments, "cwd_relative": relative_cwd,
              "timeout_seconds": 60, "status": status, "exit_code": code,
              "wall_seconds": time.monotonic() - begin,
              "requested_thread_env": requested,
              "limits": "Environment requests are not OS hard limits; no aggregate measurement.",
              "stdout": {"bytes": len(stdout), "sha256": digest(stdout)},
              "stderr": {"bytes": len(stderr), "sha256": digest(stderr)}}
    rec.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if status != "completed" or code != 0:
        raise RuntimeError("child failed; inspect fresh logs/" + name + ".json and .stderr")
    if name == "unit-tests":
        decoded = stderr.decode("utf-8", errors="replace")
        found = re.search(r"Ran (\d+) tests", decoded)
        if not found or int(found.group(1)) != 7 or not decoded.rstrip().endswith("OK"):
            raise RuntimeError("child test receipt lacks seven tests and terminal OK")
    elif stderr:
        raise RuntimeError("unexpected child stderr: " + name)
    return report


def check_fresh_results(root):
    expected = json.loads((root / "expected-before-output.json").read_text())
    report = json.loads((root / "fixed-output/report.json").read_text())
    oracle = json.loads((root / "logs/independent-oracle.stdout").read_text())
    names = [e["name"] for e in expected["models"]]
    if len(names) != 7 or names != [m["name"] for m in report["models"]]:
        raise ValueError("fresh fixed model set does not match the complete expected task")
    if oracle["status"] != "PASS" or names != [m["name"] for m in oracle["models"]]:
        raise ValueError("fresh independent oracle is incomplete")
    for e, actual in zip(expected["models"], oracle["models"]):
        if [item["group"] for item in actual["H_Z"]] != e["H_Z"]:
            raise ValueError("fresh integer homology mismatch")
        if [item["group"] for item in actual["Hco_Z"]] != e["Hco_Z"]:
            raise ValueError("fresh integer cohomology mismatch")
    if oracle["AW_count"] != 625 or len(oracle["AW_cases"]) != 625:
        raise ValueError("fresh AW case set is incomplete")
    if len(oracle["W_fixed_zero_tensor_cases"]) != 625 or len(oracle["rejections"]) != 7:
        raise ValueError("fresh fixed W/rejection case set is incomplete")
    if oracle["smith152_joint_independent_check"]["torsion_orders"] != [3]:
        raise ValueError("fresh Smith joint representative does not have order three")
    no_overwrite = oracle["no_overwrite"]
    if no_overwrite["exit_code"] != 1 or no_overwrite["before_sha256"] != no_overwrite["after_sha256"]:
        raise ValueError("fresh expected failing CLI did not preserve existing output")
    return {"models": 7, "integer_H_and_Hco_groups": 42, "AW_cases": 625,
            "fixed_W_tensor_cases": 625, "rejections": 7,
            "no_overwrite_child_exit": no_overwrite["exit_code"],
            "scope": "Finite fixed numeric protocol only; SVG rendering is not part of this helper."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True,
                        help="local WWL Git repository containing the fixed commit")
    args = parser.parse_args()
    if not args.new_dir.is_absolute():
        parser.error("--new-dir must be an absolute, nonexistent directory")
    root = args.new_dir.resolve()
    inputs = fresh_copy(root, args.repo.resolve())
    children = []
    try:
        children.append(run_child(root, "prepare-expectations", ".",
                                  [sys.executable, "-B", "prepare_expectations.py"]))
        where = "snapshot/数学/36-拓扑学/20-同调与上同调"
        children.append(run_child(root, "unit-tests", where,
                                  [sys.executable, "-B", "-m", "unittest", "-v", "test_homology_lab.py"]))
        children.append(run_child(root, "fixed-cli", where,
                                  [sys.executable, "-B", "homology_lab.py", "--output-dir", str(root / "fixed-output")]))
        children.append(run_child(root, "independent-oracle", ".",
                                  [sys.executable, "-B", "execute_oracle.py"]))
        observations = check_fresh_results(root)
    except Exception as exc:
        final = {"status": "failed", "error": str(exc), "completed_children": children}
        (root / "fresh-receipt.json").write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n")
        raise
    final = {"status": "completed", "exit_code": 0, "children": children,
             "restored_from_git_ref": FIXED_REF,
             "copied_input_sha256": {e["original_path"]: e["sha256"] for e in inputs},
             "observations": observations}
    (root / "fresh-receipt.json").write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(final, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
