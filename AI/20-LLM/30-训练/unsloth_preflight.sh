#!/bin/sh
set -eu

if [ "${UNSLOTH_PREFLIGHT:-}" = "1" ] \
  && [ -n "${LOCAL_RUN_DIR:-}" ] \
  && [ -d "$LOCAL_RUN_DIR" ]; then
  printf 'run_dir=%s\n' "$LOCAL_RUN_DIR"
  unsloth --help
else
  printf '%s\n' 'Set UNSLOTH_PREFLIGHT=1 and LOCAL_RUN_DIR=/absolute/local/run-dir for a local preflight.' >&2
  exit 2
fi
