#!/usr/bin/env bash
# Fill every empty variable after consulting the fixed llama.cpp commit. This
# template only records provenance and refuses unsafe preconditions; it does
# not download, convert, quantize, compile, or overwrite files.
set -euo pipefail

RUN_ROOT="${RUN_ROOT:-}"             # Example: /Volumes/ExternalSSD/llm-runs/2026-09-01-example
SOURCE_DIR="${SOURCE_DIR:-}"         # Read-only model directory with checked provenance
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-}"   # Existing fixed llama.cpp checkout
LLAMA_CPP_COMMIT="${LLAMA_CPP_COMMIT:-}" # Exactly 40 lowercase hexadecimal characters
REQUIRED_KIB="${REQUIRED_KIB:-}"     # Conservative source + outputs + reserve total
HIGH_GGUF="${HIGH_GGUF:-}"
QUANT_GGUF="${QUANT_GGUF:-}"

require_nonempty() { test -n "$2" || { echo "missing $1" >&2; exit 2; }; }
require_nonempty RUN_ROOT "$RUN_ROOT"
require_nonempty SOURCE_DIR "$SOURCE_DIR"
require_nonempty LLAMA_CPP_DIR "$LLAMA_CPP_DIR"
require_nonempty LLAMA_CPP_COMMIT "$LLAMA_CPP_COMMIT"
require_nonempty REQUIRED_KIB "$REQUIRED_KIB"
require_nonempty HIGH_GGUF "$HIGH_GGUF"
require_nonempty QUANT_GGUF "$QUANT_GGUF"

test -d "$RUN_ROOT" && test -d "$RUN_ROOT/out" && test -d "$SOURCE_DIR" && test -d "$LLAMA_CPP_DIR" || {
  echo "run root, source, or fixed checkout does not exist" >&2; exit 2;
}
for path in "$RUN_ROOT" "$RUN_ROOT/out" "$SOURCE_DIR" "$LLAMA_CPP_DIR"; do
  test ! -L "$path" || { echo "directory must not be a symlink: $path" >&2; exit 2; }
done
canonical_dir() { (cd -P -- "$1" && pwd -P); }
path_is_within() { case "$1/" in "$2/"*) return 0 ;; *) return 1 ;; esac; }
canonical_new_file() {
  test "${1#/}" != "$1" || { echo "output path must be absolute: $1" >&2; exit 2; }
  parent="$(canonical_dir "$(dirname -- "$1")")"
  name="$(basename -- "$1")"
  test "$name" != "." && test "$name" != ".." || { echo "invalid output filename" >&2; exit 2; }
  printf '%s/%s\n' "$parent" "$name"
}
RUN_ROOT="$(canonical_dir "$RUN_ROOT")"
OUT_DIR="$(canonical_dir "$RUN_ROOT/out")"
SOURCE_DIR="$(canonical_dir "$SOURCE_DIR")"
LLAMA_CPP_DIR="$(canonical_dir "$LLAMA_CPP_DIR")"
HIGH_GGUF="$(canonical_new_file "$HIGH_GGUF")"
QUANT_GGUF="$(canonical_new_file "$QUANT_GGUF")"
SOURCE_HASHES="$RUN_ROOT/source-sha256.txt"
COMMIT_RECORD="$RUN_ROOT/llama-cpp-commit.txt"

for pair in "$RUN_ROOT|$SOURCE_DIR" "$RUN_ROOT|$LLAMA_CPP_DIR" "$SOURCE_DIR|$LLAMA_CPP_DIR"; do
  left="${pair%%|*}"; right="${pair#*|}"
  if path_is_within "$left" "$right" || path_is_within "$right" "$left"; then
    echo "run root, source, and fixed checkout must not overlap" >&2; exit 2
  fi
done
test "$HIGH_GGUF" != "$QUANT_GGUF" || { echo "output files must be distinct" >&2; exit 2; }
test "$(dirname -- "$HIGH_GGUF")" = "$OUT_DIR" || { echo "high-precision output must be directly under RUN_ROOT/out" >&2; exit 2; }
test "$(dirname -- "$QUANT_GGUF")" = "$OUT_DIR" || { echo "quantized output must be directly under RUN_ROOT/out" >&2; exit 2; }
printf '%s' "$REQUIRED_KIB" | grep -Eq '^[1-9][0-9]*$' || { echo "REQUIRED_KIB must be a positive integer" >&2; exit 2; }
test -f "$SOURCE_DIR/config.json" || { echo "source is missing config.json" >&2; exit 2; }
find "$SOURCE_DIR" -maxdepth 1 -type l -print -quit | grep -q . && {
  echo "source directory must not contain symlinked top-level inputs" >&2; exit 2;
}
find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.safetensors' -print -quit | grep -q . || {
  echo "source has no safetensors shard" >&2; exit 2;
}
find "$SOURCE_DIR" -maxdepth 1 -type f \( -name tokenizer.json -o -name tokenizer.model -o -name vocab.json \) -print -quit | grep -q . || {
  echo "source has no recognized tokenizer file" >&2; exit 2;
}
test "${#LLAMA_CPP_COMMIT}" -eq 40 && printf '%s' "$LLAMA_CPP_COMMIT" | grep -Eq '^[0-9a-f]{40}$' || {
  echo "commit must be exactly 40 lowercase hexadecimal characters" >&2; exit 2;
}
test "$(git -C "$LLAMA_CPP_DIR" rev-parse HEAD)" = "$LLAMA_CPP_COMMIT" || {
  echo "llama.cpp HEAD differs from the manifest" >&2; exit 2;
}
test -z "$(git -C "$LLAMA_CPP_DIR" status --porcelain)" || {
  echo "fixed checkout has uncommitted changes" >&2; exit 2;
}
test ! -e "$HIGH_GGUF" && test ! -L "$HIGH_GGUF" || { echo "refusing to overwrite high-precision GGUF" >&2; exit 2; }
test ! -e "$QUANT_GGUF" && test ! -L "$QUANT_GGUF" || { echo "refusing to overwrite quantized GGUF" >&2; exit 2; }
test ! -e "$SOURCE_HASHES" && test ! -L "$SOURCE_HASHES" || { echo "refusing to overwrite source hash record" >&2; exit 2; }
test ! -e "$COMMIT_RECORD" && test ! -L "$COMMIT_RECORD" || { echo "refusing to overwrite commit record" >&2; exit 2; }
AVAILABLE_KIB="$(df -Pk "$RUN_ROOT" | awk 'NR == 2 { print $4 }')"
test "$AVAILABLE_KIB" -ge "$REQUIRED_KIB" || { echo "insufficient disk space" >&2; exit 2; }

find "$SOURCE_DIR" -maxdepth 1 -type f -print0 | sort -z | xargs -0 shasum -a 256 > "$SOURCE_HASHES"
git -C "$LLAMA_CPP_DIR" rev-parse HEAD > "$COMMIT_RECORD"
