#!/usr/bin/env bash
set -uo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "$script_dir" || {
  printf '%s\n' "probe status=FAIL reason=course-directory-unavailable" >&2
  exit 1
}
printf 'input_directory=%s\n' "$script_dir"
work_dir=""

cleanup() {
  if [[ -n "$work_dir" && -d "$work_dir" ]]; then
    rm -rf -- "$work_dir"
  fi
}
trap cleanup EXIT HUP INT TERM

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/llvm-mlir-probe.XXXXXX")" || {
  printf '%s\n' "probe status=FAIL reason=mktemp-failed" >&2
  exit 1
}
printf 'workspace=%s lifecycle=temporary\n' "$work_dir"

missing=0
failed=0
for tool_name in clang opt llc lli mlir-opt; do
  tool_location="$(command -v "$tool_name" 2>/dev/null || true)"
  if [[ -z "$tool_location" ]]; then
    printf 'tool=%s status=SKIP reason=not-found\n' "$tool_name"
    missing=1
    continue
  fi
  version_line="$("$tool_location" --version 2>&1 | sed -n '1p')"
  printf 'tool=%s status=FOUND path=%s version=%s\n' \
    "$tool_name" "$tool_location" "$version_line"
done

print_command() {
  local argument
  printf 'command='
  for argument in "$@"; do
    printf '%q ' "$argument"
  done
  printf '\n'
}

run_probe() {
  local probe_name="$1"
  local tool_name="$2"
  shift 2
  if ! command -v "$tool_name" >/dev/null 2>&1; then
    printf 'probe=%s status=SKIP reason=%s-not-found\n' "$probe_name" "$tool_name"
    return 77
  fi
  print_command "$@"
  if "$@"; then
    printf 'probe=%s status=PASS\n' "$probe_name"
    return 0
  else
    probe_status=$?
    printf 'probe=%s status=FAIL exit=%s\n' "$probe_name" "$probe_status" >&2
    failed=1
    return "$probe_status"
  fi
}

clang_path="$(command -v clang 2>/dev/null || true)"
opt_path="$(command -v opt 2>/dev/null || true)"
llc_path="$(command -v llc 2>/dev/null || true)"
lli_path="$(command -v lli 2>/dev/null || true)"
mlir_opt_path="$(command -v mlir-opt 2>/dev/null || true)"

for input_path in sample.ll sample.mlir; do
  if command -v shasum >/dev/null 2>&1; then
    input_hash="$(shasum -a 256 "$input_path" | awk '{print $1}')"
  elif command -v sha256sum >/dev/null 2>&1; then
    input_hash="$(sha256sum "$input_path" | awk '{print $1}')"
  else
    input_hash="unavailable"
  fi
  printf 'input=%s sha256=%s\n' "$(basename -- "$input_path")" "$input_hash"
done

host_target=""
target_provenance=""
if [[ -n "$clang_path" ]]; then
  host_target="$("$clang_path" -dumpmachine 2>/dev/null | sed -n '1p')"
  target_provenance="clang-dumpmachine"
  if [[ -z "$host_target" ]]; then
    host_target="$("$clang_path" -print-target-triple 2>/dev/null | sed -n '1p')"
    target_provenance="clang-print-target-triple"
  fi
fi
if [[ -z "$host_target" ]]; then
  printf '%s\n' 'target=host-default status=SKIP reason=clang-target-query-unavailable'
  missing=1
else
  printf 'target=host-default triple=%s provenance=%s\n' "$host_target" "$target_provenance"
fi

# The input LLVM IR intentionally has no target triple or data layout. Object
# generation is therefore made reproducible by supplying this recorded target.
if [[ -n "$host_target" ]]; then
  if run_probe llvm-clang clang "$clang_path" --target="$host_target" -c sample.ll -o "$work_dir/clang-sample.o"; then
    if [[ -s "$work_dir/clang-sample.o" ]]; then
      printf 'artifact=clang-sample.o status=PASS bytes=%s\n' "$(wc -c < "$work_dir/clang-sample.o")"
    else
      printf '%s\n' 'artifact=clang-sample.o status=FAIL reason=missing-or-empty' >&2
      failed=1
    fi
  fi
  if run_probe llvm-llc llc "$llc_path" -mtriple="$host_target" -filetype=obj sample.ll -o "$work_dir/llc-sample.o"; then
    if [[ -s "$work_dir/llc-sample.o" ]]; then
      printf 'artifact=llc-sample.o status=PASS bytes=%s\n' "$(wc -c < "$work_dir/llc-sample.o")"
    else
      printf '%s\n' 'artifact=llc-sample.o status=FAIL reason=missing-or-empty' >&2
      failed=1
    fi
  fi
else
  printf '%s\n' 'probe=llvm-clang status=SKIP reason=host-target-unavailable'
  printf '%s\n' 'probe=llvm-llc status=SKIP reason=host-target-unavailable'
fi

run_probe llvm-opt-verify opt "$opt_path" -passes=verify -disable-output sample.ll || true
run_probe llvm-lli lli "$lli_path" sample.ll || true
run_probe mlir-verify mlir-opt "$mlir_opt_path" --verify-each sample.mlir -o "$work_dir/verified.mlir" || true

if [[ "$failed" -ne 0 ]]; then
  printf '%s\n' "probe status=FAIL reason=installed-tool-rejected-fixed-input" >&2
  exit 1
fi
if [[ "$missing" -ne 0 ]]; then
  printf '%s\n' "probe status=SKIP exit=77 reason=incomplete-toolchain"
  exit 77
fi
printf '%s\n' "probe status=PASS exit=0"
