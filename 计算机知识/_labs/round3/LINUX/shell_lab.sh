#!/usr/bin/env bash
# All writes are confined to this script's own mktemp directory. No privileges required.
set -eu
set -o pipefail
work=$(mktemp -d)
cleanup() { if [[ -n ${work:-} && -d $work ]]; then rm -rf -- "$work"; fi; }
trap cleanup EXIT
name='a b.txt'
printf '%s' 'sample' > "$work/$name"
args=("$name" '--literal')
[[ ${#args[@]} -eq 2 && ${args[0]} == 'a b.txt' ]]
printf '%s\n' "${args[@]}" > "$work/args"
[[ $(wc -l < "$work/args") -eq 2 ]]
bash -c 'printf out; printf err >&2' > "$work/both" 2>&1
[[ $(cat "$work/both") == outerr ]]
{ bash -c 'printf out; printf err >&2' 2>&1 > "$work/out"; } > "$work/err"
[[ $(cat "$work/out") == out && $(cat "$work/err") == err ]]
if false | true; then printf '%s\n' 'pipefail did not detect failure' >&2; exit 1; fi
printf '%s\n' 'PASS: argument boundaries, redirection order, pipeline failure, scoped cleanup'
