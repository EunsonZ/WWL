"""Bounded capability checks; exit 77 is an explicit unsupported branch."""
from pathlib import Path
import subprocess
import sys
build=Path(sys.argv[1]).resolve()
skips=[]
instrumented = "--instrumented" in sys.argv[2:]
for name in ["probe","thread_queue","test_fixed","abi_consumer"]:
    result=subprocess.run([str(build/name)],capture_output=True,text=True,timeout=15)
    print(result.stdout,end="")
    if result.stderr: print(result.stderr,end="",file=sys.stderr)
    if result.returncode==77 and name in {"probe","thread_queue"}: skips.append(name)
    elif result.returncode: raise SystemExit(f"FAIL {name} exit={result.returncode}")
# Symbol check applies to the plain freestanding object. Sanitizers legitimately
# add runtime symbols and cannot serve as the zero-runtime-reference artifact.
result=subprocess.run(["/usr/bin/nm","-u",str(build/"fixed.o")],capture_output=True,text=True,check=True)
print("fixed_undefined_symbols="+(result.stdout.strip() or "NONE"))
if result.stdout.strip() and not instrumented:
    raise SystemExit("Unexpected freestanding runtime reference")
if instrumented: print("zero_runtime_reference_claim=NOT_APPLICABLE_INSTRUMENTED_OBJECT")
print("stage4_host_checks=PASS; unsupported="+(",".join(skips) or "NONE"))
