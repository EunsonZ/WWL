"""Explicitly opt-in Git exercise: creates only a fresh child temporary repo.

No push, no remote, no existing checkout, no user/global Git config or hooks.
Importing this module does not execute Git or create files.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


BASE_CONFIG = "OPEN_END = 1020\nCLEANUP_LIMIT = 1020\nBUFFER = 0\n"
V2_CONFIG = "OPEN_END = 1020\nCLEANUP_LIMIT = 1030\nBUFFER = 10\n"
BASE_SERVICE = ("from config import OPEN_END, CLEANUP_LIMIT, BUFFER\n\n"
                "def valid_end(end):\n"
                "    return end <= OPEN_END and end + BUFFER <= CLEANUP_LIMIT\n")
REFACTOR_SERVICE = ("from config import CLEANUP_LIMIT\n\n"
                    "def valid_end(end):\n"
                    "    return end <= CLEANUP_LIMIT\n")


def run_lab(parent):
    parent = Path(parent).resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("parent must be an existing directory")
    root = Path(tempfile.mkdtemp(prefix="wwl-git-evolution-", dir=parent))
    hooks = root / "empty-hooks"
    hooks.mkdir()
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_TERMINAL_PROMPT="0")
    commands = []

    def git(*args, expect=0):
        argv = ["git", "-c", "user.name=WWL synthetic exercise",
                "-c", "user.email=exercise@example.invalid",
                "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false",
                "-c", f"core.hooksPath={hooks}", *args]
        result = subprocess.run(argv, cwd=root, env=environment, text=True,
                                capture_output=True, timeout=15)
        commands.append({"args": list(args), "exit": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != expect:
            raise RuntimeError(f"Git {args} returned {result.returncode}; expected {expect}")
        return result.stdout.strip()

    def commit(message):
        git("add", "--", "config.py", "service.py")
        git("commit", "-m", message)
        return git("rev-parse", "HEAD")

    def evaluate(end):
        # Re-evaluate the exact local sources, avoiding import/pyc caches.
        config = {}
        exec((root / "config.py").read_text(), config)
        service = {}
        source = (root / "service.py").read_text()
        # Replace the teaching module import with the evaluated config values.
        exec("\n".join(line for line in source.splitlines()
                       if not line.startswith("from config import ")), config, service)
        # Function globals are config (the locals retain the new function).
        return bool(service["valid_end"](end))

    git("init", "-b", "main")
    (root / "config.py").write_text(BASE_CONFIG)
    (root / "service.py").write_text(BASE_SERVICE)
    base = commit("Base: booking and cleanup share 17:00 limit")

    git("checkout", "-b", "cleanup-policy")
    (root / "config.py").write_text(V2_CONFIG)
    policy = commit("Allow ten-minute cleanup to 17:10; booking still ends 17:00")
    policy_checks = {str(end): evaluate(end) for end in (1020, 1021, 1030)}
    if policy_checks != {"1020": True, "1021": False, "1030": False}:
        raise AssertionError("policy branch violates booking close time")

    git("checkout", "-b", "simplify", base)
    (root / "service.py").write_text(REFACTOR_SERVICE)
    refactor = commit("Remove equivalent guard under v1 configuration")
    refactor_checks = {str(end): evaluate(end) for end in range(1010, 1041)}
    if any(value != (int(end) <= 1020) for end, value in refactor_checks.items()):
        raise AssertionError("refactor is not equivalent under base config")
    git("merge", "--no-ff", "cleanup-policy", "-m", "Text merge succeeds; inspect semantics")
    merged = git("rev-parse", "HEAD")
    merge_parents = git("show", "-s", "--format=%P", "HEAD").split()
    wrong = evaluate(1021)
    if not wrong:
        raise AssertionError("expected the semantic conflict witness")
    (root / "service.py").write_text(BASE_SERVICE)
    repaired = commit("Restore both guards required by new cleanup policy")
    if evaluate(1021) or not evaluate(1020):
        raise AssertionError("semantic repair failed")

    git("checkout", "-b", "text-left")
    (root / "config.py").write_text(V2_CONFIG.replace("BUFFER = 10", "BUFFER = 15"))
    left = commit("Synthetic conflicting request: buffer fifteen")
    git("checkout", "-b", "text-right", repaired)
    (root / "config.py").write_text(V2_CONFIG.replace("BUFFER = 10", "BUFFER = 20"))
    right = commit("Synthetic conflicting request: buffer twenty")
    git("merge", "--no-ff", "text-left", "-m", "Expose same-line conflict", expect=1)
    conflict_text = (root / "config.py").read_text()
    if "<<<<<<<" not in conflict_text or ">>>>>>>" not in conflict_text:
        raise AssertionError("expected explicit text conflict markers")
    # Exercise decision: neither speculative policy was approved. Keep 10.
    (root / "config.py").write_text(V2_CONFIG)
    resolved = commit("Resolve using approved ten-minute policy, not branch majority")
    graph = git("log", "--graph", "--oneline", "--all")
    result = {"root": str(root), "synthetic": True,
              "commits": {"base": base, "policy": policy, "refactor": refactor,
                          "merged": merged, "repaired": repaired, "text_left": left,
                          "text_right": right, "resolved": resolved},
              "policy_branch_checks": policy_checks,
              "refactor_branch_checks": refactor_checks,
              "merge_parents": merge_parents,
              "merged_accepts_1021_incorrectly": wrong,
              "repaired_accepts_1021": evaluate(1021),
              "text_conflict": conflict_text, "graph": graph, "commands": commands}
    (root / "exercise-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", required=True,
                        help="existing output directory; a new child repo is retained here")
    args = parser.parse_args()
    print(json.dumps(run_lab(args.parent), ensure_ascii=False, indent=2))
