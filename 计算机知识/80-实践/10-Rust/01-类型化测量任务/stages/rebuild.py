"""Build one genuinely new Cargo project through three small teaching steps.

Usage: python3 stages/rebuild.py /absolute/path/to/nonexistent/project
Source is the small stage snapshots, never the final measurement component.
No deletion, dependency installation, network access, or existing-tree overwrite.
"""
from pathlib import Path
import shutil
import subprocess
import sys

stages = Path(__file__).resolve().parent
project = Path(sys.argv[1]).resolve()
if project.exists():
    raise SystemExit("destination must not exist; existing files are preserved")


def run(args, *, data=None, expected=0):
    result = subprocess.run(args, cwd=project, input=data, text=True, capture_output=True)
    print("$", " ".join(args), flush=True)
    print(result.stdout, end="", flush=True)
    print(result.stderr, end="", flush=True)
    if result.returncode != expected:
        raise SystemExit(f"expected exit {expected}, got {result.returncode}")
    return result


subprocess.run(
    ["cargo", "new", "--name", "measurement-step", "--bin", "--edition", "2021", "--vcs", "none", str(project)],
    check=True,
)
run(["cargo", "run", "--offline"])
for stage in ("typed", "library", "cli"):
    source = stages / stage
    shutil.copyfile(source / "Cargo.toml", project / "Cargo.toml")
    for name in ("lib.rs", "main.rs"):
        file = source / "src" / name
        if file.exists():
            shutil.copyfile(file, project / "src" / name)
    print(f"STEP {stage}: teaching snapshot only", flush=True)
    run(["cargo", "fmt", "--check"])
    run(["cargo", "test", "--locked", "--offline"])
    if stage == "typed":
        assert "Ok((20, Some(5.0)))" in run(["cargo", "run", "--locked", "--offline"]).stdout
        assert "outside" in run(["cargo", "run", "--locked", "--offline", "--", "2", "4096"], expected=1).stderr
    elif stage == "library":
        assert "twice_mV=[2, 6, 10, 14]" in run(["cargo", "run", "--locked", "--offline"]).stdout
    else:
        assert "sum_mV=20 mean_mV=Some(5.0)" in run(["cargo", "run", "--locked", "--offline"], data="2 4 6 8\n").stdout
        bad = run(["cargo", "run", "--locked", "--offline"], data="2 4096\n", expected=2)
        assert not bad.stdout and "outside" in bad.stderr
        assert "mean_mV=None" in run(["cargo", "run", "--locked", "--offline"], data="").stdout
print("empty-directory -> typed -> library -> CLI: passed", flush=True)
