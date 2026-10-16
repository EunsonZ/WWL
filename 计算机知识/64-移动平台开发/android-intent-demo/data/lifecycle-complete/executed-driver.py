#!/usr/bin/env python3
"""Synthetic dedicated emulator only: actual process kill/relaunch and durable-identity checks.
No install/clear, no device discovery or global adb shutdown. Output must be a new directory.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
import subprocess
import time

PACKAGE = "org.wwl.intentdemo"
COMPONENT = PACKAGE + "/.MainActivity"
FIRST = "android-D-recovery-1"
NEXT = "android-D-next-1"
FP = "d644656f03ece17dcce05e3855ec43ae1c4b50186e8b58c631c77ed2f846a867"


def run(adb, serial, output, resume_from=None):
    output.mkdir(parents=True, exist_ok=False)
    commands = []
    checks = []
    rotation = None

    def call(*args, binary=False, allow_fail=False):
        argv = [adb, "-s", serial, *args]
        proc = subprocess.run(argv, capture_output=True, timeout=25)
        commands.append({"argv": argv, "returncode": proc.returncode,
                         "stdout": "<binary>" if binary else proc.stdout.decode(errors="replace"),
                         "stderr": proc.stderr.decode(errors="replace")})
        if proc.returncode and not allow_fail:
            raise RuntimeError(commands[-1])
        return proc.stdout if binary else proc.stdout.decode(errors="replace").strip()

    def check(label, condition):
        checks.append({"label": label, "pass": bool(condition)})
        if not condition:
            raise AssertionError(label)

    def read(name):
        return json.loads(call("exec-out", "run-as", PACKAGE, "cat", "files/" + name + ".json"))

    def wait(predicate, seconds=12):
        deadline = time.monotonic() + seconds
        last = None
        while time.monotonic() < deadline:
            try:
                state, ui = read("store-state"), read("ui-state")
                if predicate(state, ui):
                    return state, ui
                last = (state, ui)
            except (ValueError, RuntimeError, KeyError, TypeError):
                pass  # Export files may be between writes; the SQLite stores are the business source.
            time.sleep(.08)
        raise AssertionError("readiness timeout: " + repr(last))

    def command(value=None, **extras):
        args = ["shell", "am", "start", "-W", "-n", COMPONENT]
        if value is not None:
            args += ["--es", "lab_command", value]
        for key, val in extras.items():
            args += ["--es", key, str(val)]
        call(*args)

    def current(s):
        return s["client"]["current"]

    def snap(label, predicate):
        state, ui = wait(predicate)
        (output / (label + ".json")).write_text(json.dumps({"store": state, "ui": ui}, ensure_ascii=False, indent=2) + "\n")
        return state, ui

    def screen(label):
        (output / (label + ".png")).write_bytes(call("exec-out", "screencap", "-p", binary=True))

    try:
        check("explicit emulator serial", serial.startswith("emulator-"))
        check("Android emulator qemu property", call("shell", "getprop", "ro.kernel.qemu") == "1")
        versions = {k: call("shell", "getprop", k) for k in
                    ["ro.build.version.sdk", "ro.build.version.release", "ro.product.cpu.abi"]}
        command()
        state, _ = wait(lambda s, u: s["pid"] == u["pid"] and u["foreground"])
        if resume_from is not None:
            prior_queued = json.loads((resume_from / "01-queued.json").read_text())
            prior_unknown = json.loads((resume_from / "02-committed-reply-lost.json").read_text())
            prior_current = prior_unknown["store"]["client"]["current"]
            check("resume only this fixed committed/unknown identity", current(state) is not None and
                  (current(state)["actor"], current(state)["intent_id"], current(state)["fingerprint"], current(state)["start"], current(state)["end"], current(state)["phase"], current(state)["result"]) == ("D", FIRST, FP, 690, 720, "unknown", None))
            check("resume prefix queued same immutable parameters", all(prior_queued["store"]["client"]["current"][k] == current(state)[k] for k in ["actor", "intent_id", "start", "end", "fingerprint"]) and prior_queued["store"]["client"]["current"]["phase"] == "queued")
            check("resume prefix original unknown and authority unchanged", all(prior_current[k] == current(state)[k] for k in ["actor", "intent_id", "start", "end", "fingerprint", "phase", "result"]) and state["mock_authority"] == prior_unknown["store"]["mock_authority"])
            check("resume prefix has original one effect/event", len(state["mock_authority"]["bookings"]) == 4 and len(state["mock_authority"]["outbox"]) == 1)
            provenance = {}
            (output / "prefix").mkdir()
            for name in ["01-queued.json", "01-queued.png", "02-committed-reply-lost.json", "02-unknown.png", "commands.json", "assertions.json", "executed-prefix-driver.py"]:
                source = resume_from / name
                shutil.copyfile(source, output / "prefix" / name)
                provenance[name] = hashlib.sha256(source.read_bytes()).hexdigest()
            (output / "resume-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
            unknown = state
            original = next(x for x in unknown["mock_authority"]["intents"] if x["intent_id"] == FIRST)
        else:
            check("fresh mock has three legacy bookings", len(state["mock_authority"]["bookings"]) == 3)
            check("fresh mock outbox empty", state["mock_authority"]["outbox"] == [])
            check("fixed public lab IDs unused", all(x["intent_id"] not in (FIRST, NEXT) for x in state["client"]["intents"]))

            command("queue", intent_id=FIRST, start_raw=690, end_raw=720)
            queued, _ = snap("01-queued", lambda s, u: current(s) is not None and current(s)["intent_id"] == FIRST and u["intent_id"] == FIRST and u["phase"] == "queued")
            check("queued exact durable identity and normalized parameters", (current(queued)["actor"], current(queued)["intent_id"], current(queued)["start"], current(queued)["end"], current(queued)["fingerprint"]) == ("D", FIRST, 690, 720, FP))
            check("queue is not a service commitment", current(queued)["result"] is None and len(queued["mock_authority"]["bookings"]) == 3)
            screen("01-queued")

            # This SAME fixed business intent must cross a real configuration change before kill/recovery.
            original_mode = call("shell", "wm", "user-rotation")
            check("known wm user-rotation mode", original_mode == "free" or re.fullmatch(r"lock [0-3]", original_mode) is not None)
            before_display = call("shell", "dumpsys", "window", "displays")
            old_rotation = int(re.search(r"\bmRotation=ROTATION_(0|90|180|270)\b", before_display).group(1))
            target_rotation = 90 if old_rotation in (0, 180) else 0
            old_instance = read("ui-state")["activity_instance"]
            try:
                call("shell", "wm", "user-rotation", "lock", str(target_rotation // 90))
                rotated, rotated_ui = snap("01b-same-intent-rotated", lambda s, u: u["activity_instance"] != old_instance and u["foreground"] and current(s)["intent_id"] == u["intent_id"] == FIRST and u["phase"] == "queued")
                after_display = call("shell", "dumpsys", "window", "displays")
                actual_rotation = int(re.search(r"\bmRotation=ROTATION_(0|90|180|270)\b", after_display).group(1))
                check("actual display rotation changed, with a new Activity instance", actual_rotation == target_rotation and actual_rotation != old_rotation and rotated_ui["activity_instance"] != old_instance and rotated["pid"] == queued["pid"] == rotated_ui["pid"])
                check("same intent parameters/fingerprint and draft survived rotation", (current(rotated)["actor"], current(rotated)["intent_id"], current(rotated)["start"], current(rotated)["end"], current(rotated)["fingerprint"], rotated_ui["start_raw"], rotated_ui["end_raw"]) == ("D", FIRST, 690, 720, FP, "690", "720"))
                check("rotation did not send or create a new business effect", len(rotated["mock_authority"]["bookings"]) == 3 and rotated["mock_authority"]["outbox"] == [] and current(rotated)["phase"] == "queued")
                (output / "rotation-before.txt").write_text(before_display + "\n")
                (output / "rotation-after.txt").write_text(after_display + "\n")
                rotation = {"original_mode": original_mode, "pid_unchanged": rotated["pid"], "before_degrees": old_rotation, "after_degrees": actual_rotation,
                            "old_instance": old_instance, "rotated_instance": rotated_ui["activity_instance"], "intent_id": FIRST, "fingerprint": FP}
                time.sleep(.25)  # Let the display's transition frame settle; not a timing-performance assertion.
                screen("01b-same-intent-rotated")
            finally:
                call("shell", "wm", "user-rotation", *original_mode.split(), allow_fail=True)
            restored, restored_ui = snap("01c-same-intent-orientation-restored", lambda s, u: u["foreground"] and u["activity_instance"] != rotated_ui["activity_instance"] and current(s)["intent_id"] == u["intent_id"] == FIRST and u["phase"] == "queued")
            check("restored only this emulator's prior rotation mode", call("shell", "wm", "user-rotation") == original_mode)
            rotation["restored_instance"] = restored_ui["activity_instance"]
            (output / "rotation.json").write_text(json.dumps(rotation, indent=2) + "\n")

            command("drop")
            unknown, _ = snap("02-committed-reply-lost", lambda s, u: current(s)["phase"] == u["phase"] == "unknown")
            original = next(x for x in unknown["mock_authority"]["intents"] if x["intent_id"] == FIRST)
            check("authority accepted but client does not infer it", original["status"] == "accepted" and current(unknown)["result"] is None)
            check("original effect and event created once", len(unknown["mock_authority"]["bookings"]) == 4 and len(unknown["mock_authority"]["outbox"]) == 1)
            screen("02-unknown")
        old_pid = unknown["pid"]
        call("shell", "input", "keyevent", "KEYCODE_HOME")
        time.sleep(.3)
        call("shell", "am", "kill", PACKAGE)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and call("shell", "pidof", PACKAGE, allow_fail=True):
            time.sleep(.1)
        am_kill_removed = not bool(call("shell", "pidof", PACKAGE, allow_fail=True))
        termination = {"am_kill_removed": am_kill_removed, "fallback": None}
        if not am_kill_removed:
            # am kill is advisory: a previous/LAST process can be retained by Android's safe-kill policy.
            check("explicit termination targets the same single synthetic PID", call("shell", "pidof", PACKAGE) == str(old_pid))
            cmdline = call("exec-out", "run-as", PACKAGE, "cat", f"/proc/{old_pid}/cmdline", binary=True)
            check("same-UID target cmdline is precisely our synthetic package", cmdline.split(b"\0")[0] == PACKAGE.encode())
            call("shell", "run-as", PACKAGE, "kill", "-9", str(old_pid))
            termination["fallback"] = "run-as own-package SIGKILL; not force-stop or low-memory selection"
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline and call("shell", "pidof", PACKAGE, allow_fail=True):
                time.sleep(.1)
        check("the background process actually exited", not call("shell", "pidof", PACKAGE, allow_fail=True))
        command()
        restarted, _ = snap("03-new-process-unknown", lambda s, u: s["pid"] != old_pid and u["pid"] == s["pid"] and current(s)["phase"] == u["phase"] == "unknown" and u["intent_id"] == FIRST)
        check("new process recovered original intent", (current(restarted)["intent_id"], current(restarted)["fingerprint"], current(restarted)["start"], current(restarted)["end"]) == (FIRST, FP, 690, 720))
        check("unknown restart did not publish an old success", current(restarted)["result"] is None and "未知" in read("ui-state")["message"])

        command("recover")
        recovered, _ = snap("04-recovered-original-result", lambda s, u: current(s)["phase"] == u["phase"] == "accepted")
        check("query recovered the exact original result, not a replacement", current(recovered)["result"] == original)
        check("result identity and effect preserved", original["intent_id"] == FIRST and original["fingerprint"] == FP and original["booking"]["id"] == 4)
        screen("04-confirmed")
        command("normal")
        replay, _ = snap("05-replay", lambda s, u: current(s)["phase"] == u["phase"] == "accepted")
        check("same-ID replay returns original accepted result", current(replay)["result"] == original)
        check("replay has one original effect and event", len(replay["mock_authority"]["bookings"]) == 4 and len(replay["mock_authority"]["outbox"]) == 1)

        command("delay")
        wait(lambda s, u: any(x["kind"] == "reply_held" and x["detail"] == FIRST for x in s["client"]["trace"]))
        command("queue", intent_id=NEXT, start_raw=810, end_raw=840)
        wait(lambda s, u: current(s)["intent_id"] == u["intent_id"] == NEXT and u["phase"] == "queued")
        late, ui = snap("06-old-reply-new-screen", lambda s, u: current(s)["intent_id"] == u["intent_id"] == NEXT and any(x["kind"] == "ui_ignored" and x["detail"].startswith("reply:") and x["detail"].endswith(":" + FIRST) for x in s["client"]["trace"]))
        old_row = next(x for x in late["client"]["intents"] if x["intent_id"] == FIRST)
        check("old response persisted under its original identity", old_row["result"] == original)
        check("late old success cannot publish into newer intent", current(late)["phase"] == ui["phase"] == "queued" and current(late)["result"] is None and "尚无服务承诺" in ui["message"])
        check("new intent did not erase old record", {FIRST, NEXT} <= {x["intent_id"] for x in late["client"]["intents"]})

        command("edit", start_raw="bad", end_raw="840")
        wait(lambda s, u: u["start_raw"] == "bad")
        command("queue", intent_id="must-not-persist-invalid", start_raw="bad", end_raw="840")
        invalid, _ = snap("07-invalid-preserves-draft", lambda s, u: "输入错误" in u["message"] and u["start_raw"] == "bad")
        check("invalid input preserves current durable intent", current(invalid)["intent_id"] == NEXT and not any(x["intent_id"] == "must-not-persist-invalid" for x in invalid["client"]["intents"]))
        command("save_draft")
        wait(lambda s, u: s["client"]["draft"]["start_raw"] == "bad" and "草稿已落盘" in u["message"])
        before_stop_pid = int(call("shell", "pidof", PACKAGE))
        call("shell", "am", "force-stop", PACKAGE)
        check("explicit force-stop removed process", not call("shell", "pidof", PACKAGE, allow_fail=True))
        command()
        durable, ui = snap("08-force-stop-durable-draft", lambda s, u: s["pid"] != before_stop_pid and s["pid"] == u["pid"] and u["start_raw"] == "bad" and u["intent_id"] == NEXT)
        check("explicit saved raw draft survives force-stop", durable["client"]["draft"] == {"start_raw": "bad", "end_raw": "840"} and ui["start_raw"] == "bad")
        check("editing draft did not mutate pending normalized intent", (current(durable)["start"], current(durable)["end"], current(durable)["phase"]) == (810, 840, "queued"))
        check("all original effects and old accepted outcome still present", len(durable["mock_authority"]["bookings"]) == 4 and next(x for x in durable["client"]["intents"] if x["intent_id"] == FIRST)["result"] == original)
        screen("08-new-pending-saved-error")
        # Read database files only after stopping this synthetic package. Verify the exported contents separately.
        call("shell", "am", "force-stop", PACKAGE)
        for name in ["client.db", "mock-authority.db"]:
            (output / name).write_bytes(call("exec-out", "run-as", PACKAGE, "cat", "databases/" + name, binary=True))
        report = {"scope": "synthetic single-device function/JSON mock; no actual network or human task", "versions": versions,
                  "old_pid": old_pid, "new_pid": restarted["pid"], "termination": termination, "continued_prefix": resume_from is not None, "rotation_same_intent": rotation, "checks": checks,
                  "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "not_tested": ["low-memory killer selection", "real HTTP interruption", "device loss or power loss", "two-device capacity", "permissions/background jobs", "human/assistive technology"]}
        (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(f"PASS {len(checks)} lifecycle/identity assertions; process {old_pid} -> {restarted['pid']}")
    finally:
        (output / "commands.json").write_text(json.dumps(commands, ensure_ascii=False, indent=2) + "\n")
        (output / "assertions.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume-from", type=Path, help="Only a preserved failed prefix for this exact fixed unknown intent; never clears data")
    args = parser.parse_args()
    run(args.adb, args.serial, args.output, args.resume_from)
