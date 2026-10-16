"""Parent-owned barrier/SIGKILL/restart experiment; writes raw local evidence."""
import argparse
import codecs
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
import batch_oracle

HERE = Path(__file__).resolve().parent


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inspect(path, role):
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, isolation_level=None)
    try:
        db.execute("BEGIN")
        integrity = [r[0] for r in db.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            raise AssertionError((role, integrity))
        if role == "state":
            queries = {"entities": "SELECT id,payload FROM entities ORDER BY id",
                       "seen": "SELECT id,payload,decision FROM seen ORDER BY id",
                       "claims": "SELECT entity,v,content FROM claims ORDER BY entity,v",
                       "totals": "SELECT g,s,n FROM totals ORDER BY g",
                       "positions": "SELECT p,decision FROM positions ORDER BY p",
                       "deliveries": "SELECT id,fingerprint,result FROM deliveries ORDER BY id"}
            result = {k: [list(r) for r in db.execute(query)] for k, query in queries.items()}
            result["checkpoint"] = db.execute("SELECT p FROM checkpoint").fetchone()[0]
        else:
            result = {"effects": [list(r) for r in db.execute("SELECT seq,id,fingerprint,body,result FROM effects ORDER BY seq")],
                      "receipts": [list(r) for r in db.execute("SELECT id,fingerprint,result FROM receipts ORDER BY id")],
                      "totals": [list(r) for r in db.execute("SELECT g,s,n FROM totals ORDER BY g")]}
        db.execute("COMMIT")
        return result
    finally:
        db.close()


def launch(args, case_dir, name, state, sink, batch=2, mode="atomic", sink_mode="dedupe", fault="none", at=0):
    token = uuid.uuid4().hex
    command = [sys.executable, "-B", "-u", str(HERE / "recovery_worker.py"),
               "--source", str(args.source), "--state", str(state), "--sink", str(sink),
               "--batch-size", str(batch), "--checkpoint-mode", mode, "--sink-mode", sink_mode,
               "--fault", fault, "--at", str(at), "--token", token]
    started = time.monotonic()
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8")
    lines, observed = [], None
    try:
        if fault != "none":
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            try:
                deadline = time.monotonic() + 15
                pending = ""
                decoder = codecs.getincrementaldecoder("utf-8")()
                while time.monotonic() < deadline:
                    if not selector.select(timeout=max(0, deadline - time.monotonic())):
                        break
                    raw_chunk = os.read(proc.stdout.fileno(), 65536)
                    if not raw_chunk:
                        break
                    chunk = decoder.decode(raw_chunk)
                    lines.append(chunk)
                    pending += chunk
                    while "\n" in pending:
                        line, pending = pending.split("\n", 1)
                        event = json.loads(line)
                        if event.get("phase") == "barrier":
                            if (event.get("pid"), event.get("token"), event.get("kind"), event.get("position")) != (proc.pid, token, fault, at):
                                raise AssertionError("unrecognized barrier")
                            observed = event
                            proc.send_signal(signal.SIGKILL)  # Only this Popen-owned child.
                            break
                    if observed is not None:
                        break
            finally:
                selector.close()
            if observed is None:
                raise AssertionError("worker did not reach requested barrier; no expected cut observed")
        stdout, stderr = proc.communicate(timeout=20)
        lines.append(stdout)
    finally:
        if proc.poll() is None:
            proc.kill()  # Timeout/error cleanup is not counted as a successful fault cut.
            proc.communicate(timeout=5)
    raw = "".join(lines)
    case_dir.joinpath(name + ".stdout.jsonl").write_text(raw, encoding="utf-8")
    case_dir.joinpath(name + ".stderr.txt").write_text(stderr, encoding="utf-8")
    expected = -signal.SIGKILL if fault != "none" else 0
    if proc.returncode != expected:
        raise AssertionError((name, proc.returncode, stderr))
    record = {"command": command, "pid": proc.pid, "returncode": proc.returncode,
              "elapsed_seconds": time.monotonic() - started,
              "observed_barrier": observed, "signal": 9 if observed else None}
    write(case_dir / (name + ".process.json"), record)
    events = [json.loads(line) for line in raw.splitlines()]
    return record, events


def scenario(args, name, batch=2, mode="atomic", sink_mode="dedupe", fault="none", at=0):
    directory = args.out / name
    directory.mkdir()
    work = args.work / name
    work.mkdir()
    state, sink = work / "state.sqlite", work / "sink.sqlite"
    runs, traces = [], []
    first, events = launch(args, directory, "first", state, sink, batch, mode, sink_mode, fault, at)
    runs.append(first)
    traces.extend(events)
    cut = {"state": inspect(state, "state"), "sink": inspect(sink, "sink")}
    write(directory / "cut-observed.json", cut)
    if fault != "none":
        restarted, events = launch(args, directory, "restart", state, sink, batch, mode, sink_mode)
        runs.append(restarted)
        traces.extend(events)
    final_state, final_sink = inspect(state, "state"), inspect(sink, "sink")
    final = {"state": final_state, "sink": final_sink}
    write(directory / "final-observed.json", final)
    source = json.loads(args.source.read_text(encoding="utf-8"))
    comparison = batch_oracle.compare(source, final_state, final_sink)
    prefix_checks = []
    for event in traces:
        if event["phase"] == "state_committed":
            expected = batch_oracle.rebuild(source, event["position"])["state"]
            prefix_checks.append({"position": event["position"], "match": event["state"] == expected})
    good = mode == "atomic" and sink_mode == "dedupe"
    if good:
        if not comparison["all_match"] or not all(c["match"] for c in prefix_checks):
            raise AssertionError((name, comparison, prefix_checks))
        resumed, events = launch(args, directory, "resume_complete", state, sink, batch, mode, sink_mode)
        runs.append(resumed)
        if inspect(state, "state") != final_state or inspect(sink, "sink") != final_sink:
            raise AssertionError("completed checkpoint replay changed durable resources")
        # A fresh state rebuild replays every source item against the SAME sink receipts.
        fresh = work / "fresh_state.sqlite"
        replay, events = launch(args, directory, "fresh_state_replay", fresh, sink, batch, mode, sink_mode)
        runs.append(replay)
        if inspect(fresh, "state") != final_state or inspect(sink, "sink") != final_sink:
            raise AssertionError("stable authority results did not survive full source replay")
    elif comparison["all_match"]:
        raise AssertionError("counterexample was not observed")
    result = {"name": name, "batch_size": batch, "checkpoint_mode": mode, "sink_mode": sink_mode,
              "fault": fault, "at": at, "runs": runs, "comparison": comparison,
              "committed_prefix_checks": prefix_checks,
              "cut_checkpoint": cut["state"]["checkpoint"],
              "cut_state_totals": cut["state"]["totals"], "cut_sink_totals": cut["sink"]["totals"]}
    if mode == "offset_first_bad":
        if cut["state"]["checkpoint"] != 2 or cut["state"]["totals"] != []:
            raise AssertionError("bad offset cut not exposed")
        if final_state["totals"] != [["A", 7, 2], ["B", 7, 1]]:
            raise AssertionError("missing fixed f fact was not observed")
    if sink_mode == "naive_bad":
        if final_sink["totals"] != [["A", 7, 2], ["B", 7, 1], ["F", 22, 2]]:
            raise AssertionError("duplicate fixed f effect was not observed")
    write(directory / "result.json", result)
    return result


def run(args):
    if os.name != "posix":
        raise RuntimeError("this SIGKILL experiment requires POSIX")
    args.source = args.source.resolve()
    args.out = args.out.resolve()
    args.work = args.work.resolve()
    args.out.mkdir()
    args.work.mkdir()
    started = time.monotonic()
    specs = [("normal_b1", 1, "atomic", "dedupe", "none", 0),
             ("normal_b2", 2, "atomic", "dedupe", "none", 0),
             ("normal_b4", 4, "atomic", "dedupe", "none", 0),
             ("normal_b7", 7, "atomic", "dedupe", "none", 0),
             ("kill_sink_naive", 2, "atomic", "naive_bad", "after_sink", 1),
             ("kill_sink_dedupe", 2, "atomic", "dedupe", "after_sink", 1),
             ("kill_offset_first", 2, "offset_first_bad", "dedupe", "after_offset", 2),
             ("kill_atomic_before", 2, "atomic", "dedupe", "before_state_commit", 2),
             ("kill_atomic_after", 2, "atomic", "dedupe", "after_state_commit", 2),
             ("kill_update_sink", 2, "atomic", "dedupe", "after_sink", 5),
             ("kill_atomic_b4", 4, "atomic", "dedupe", "before_state_commit", 4)]
    results = [scenario(args, *spec) for spec in specs]
    expected = batch_oracle.rebuild(json.loads(args.source.read_text(encoding="utf-8")))
    write(args.out / "batch-truth.json", expected)
    summary = {"protocol": "wwl-db18-recovery-v1", "python": platform.python_version(),
               "sqlite": sqlite3.sqlite_version, "platform": platform.platform(),
               "cpu_threads": 1, "wall_clock_limit_seconds": 300,
               "elapsed_seconds": time.monotonic() - started,
               "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
               "source_files_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in (HERE / "recovery_worker.py", HERE / "batch_oracle.py", HERE / "test_recovery.py", Path(__file__).resolve())},
               "scenarios": [{"name": r["name"], "fault": r["fault"], "at": r["at"],
                              "returncodes": [p["returncode"] for p in r["runs"]],
                              "comparison": r["comparison"], "cut_checkpoint": r["cut_checkpoint"],
                              "cut_state_totals": r["cut_state_totals"], "cut_sink_totals": r["cut_sink_totals"]}
                             for r in results],
               "controlled_sigkills": sum(r["fault"] != "none" for r in results),
               "correct_scenarios": sum(r["comparison"]["all_match"] for r in results),
               "intentional_counterexamples": sum(not r["comparison"]["all_match"] for r in results),
               "status": "pass"}
    write(args.out / "summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("status", "controlled_sigkills", "correct_scenarios", "intentional_counterexamples", "elapsed_seconds")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=HERE / "source.json")
    parser.add_argument("--out", type=Path, required=True, help="new evidence directory")
    parser.add_argument("--work", type=Path, required=True, help="new directory for disposable SQLite resources")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
