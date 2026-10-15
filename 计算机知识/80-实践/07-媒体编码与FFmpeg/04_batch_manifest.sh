#!/usr/bin/env bash
set -euo pipefail

for tool in ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'SKIP: %s is not available in PATH\n' "$tool" >&2
    exit 77
  fi
done

if (( $# > 2 )); then
  printf 'usage: %s [manifest.tsv [new-output-directory]]\n' "$0" >&2
  exit 64
fi

temp_base="${TMPDIR:-/tmp}"
temp_base="${temp_base%/}"
workspace="$(mktemp -d "$temp_base/workwithllm-ffmpeg-batch.XXXXXX")"

if (( $# >= 1 )); then
  manifest="$1"
  [[ -f "$manifest" && ! -L "$manifest" ]] || {
    printf 'manifest must be a regular, non-symlink file: %s\n' "$manifest" >&2
    exit 65
  }
  manifest_dir="$(cd -- "$(dirname -- "$manifest")" && pwd -P)"
  manifest="$manifest_dir/$(basename -- "$manifest")"
  input_dir="$manifest_dir"
else
  input_dir="$workspace/input"
  mkdir -- "$input_dir"
  ffmpeg -hide_banner -loglevel warning -nostdin -n \
    -f lavfi -i 'testsrc2=size=160x120:rate=15:duration=2' \
    -f lavfi -i 'sine=frequency=440:sample_rate=48000:duration=2' \
    -map 0:v:0 -map 1:a:0 -c:v ffv1 -c:a pcm_s16le \
    "$input_dir/clip-a.mkv"
  ffmpeg -hide_banner -loglevel warning -nostdin -n \
    -f lavfi -i 'testsrc2=size=160x120:rate=15:duration=2' \
    -f lavfi -i 'sine=frequency=660:sample_rate=48000:duration=2' \
    -map 0:v:0 -map 1:a:0 -c:v ffv1 -c:a pcm_s16le \
    "$input_dir/clip-b.mkv"
  manifest="$input_dir/manifest.tsv"
  printf '%s\t%s\t%s\t%s\n' \
    'clip-a.mkv' 'clip-a.mp4' '0' '1.25' \
    'clip-b.mkv' 'clip-b.mp4' '0.25' '1.50' > "$manifest"
fi

if (( $# == 2 )); then
  output_dir="$2"
else
  output_dir="$workspace/output"
fi

[[ -n "$output_dir" && "$output_dir" != / && ! -e "$output_dir" ]] || {
  printf 'refusing existing or unsafe output directory: %s\n' "$output_dir" >&2
  exit 73
}
[[ -d "$(dirname -- "$output_dir")" ]] || {
  printf 'output parent does not exist\n' >&2
  exit 73
}

validate_row() {
  local line_number="$1" input_name="$2" output_name="$3"
  local start="$4" duration="$5" input_path size

  case "$input_name" in
    *://*|*:*|/*|*/*|*\\*|*..*)
      printf 'line %s: protocol, absolute, traversal, or nested input rejected\n' "$line_number" >&2
      return 1
      ;;
  esac
  [[ "$input_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*\.(mkv|mp4|mov)$ ]] || {
    printf 'line %s: input name or extension rejected\n' "$line_number" >&2
    return 1
  }
  [[ "$output_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*\.mp4$ ]] || {
    printf 'line %s: output must be a plain .mp4 basename\n' "$line_number" >&2
    return 1
  }
  [[ "$start" =~ ^[0-9]+([.][0-9]+)?$ ]] || {
    printf 'line %s: invalid start time\n' "$line_number" >&2
    return 1
  }
  [[ "$duration" =~ ^[0-9]+([.][0-9]+)?$ && ! "$duration" =~ ^0+([.]0+)?$ ]] || {
    printf 'line %s: invalid duration\n' "$line_number" >&2
    return 1
  }

  input_path="$input_dir/$input_name"
  [[ -f "$input_path" && ! -L "$input_path" ]] || {
    printf 'line %s: input must be a regular, non-symlink file\n' "$line_number" >&2
    return 1
  }
  size="$(wc -c < "$input_path" | tr -d ' ')"
  (( size <= 20971520 )) || {
    printf 'line %s: input exceeds the 20 MiB lab limit\n' "$line_number" >&2
    return 1
  }
  ffprobe -v error -protocol_whitelist file,pipe \
    -probesize 10000000 -analyzeduration 5000000 \
    -show_entries format=format_name,duration -of json "$input_path" >/dev/null
}

# Read the raw row; tab is whitespace in IFS and read would collapse empty fields.
parse_row() {
  local rest="$1" tab=$'\t'
  [[ "$rest" == *"$tab"* ]] || return 1
  input_name="${rest%%"$tab"*}"; rest="${rest#*"$tab"}"
  [[ "$rest" == *"$tab"* ]] || return 1
  output_name="${rest%%"$tab"*}"; rest="${rest#*"$tab"}"
  [[ "$rest" == *"$tab"* ]] || return 1
  start="${rest%%"$tab"*}"; duration="${rest#*"$tab"}"
  [[ "$duration" != *"$tab"* ]] || return 1
  # Empty fields are preserved here and rejected by each field's syntax below.
}

line_number=0
row_count=0
seen_outputs="$workspace/seen-output-names.txt"
: > "$seen_outputs"
while IFS= read -r row || [[ -n "$row" ]]; do
  line_number=$((line_number + 1))
  [[ -z "$row" || "$row" == \#* ]] && continue
  parse_row "$row" || {
    printf 'line %s: expected exactly four tab-separated fields\n' "$line_number" >&2
    exit 65
  }
  row_count=$((row_count + 1))
  (( row_count <= 100 )) || {
    printf 'manifest exceeds the 100-row lab limit\n' >&2
    exit 65
  }
  validate_row "$line_number" "$input_name" "$output_name" \
    "$start" "$duration"
  if grep -Fqx -- "$output_name" "$seen_outputs"; then
    printf 'line %s: duplicate output name rejected: %s\n' \
      "$line_number" "$output_name" >&2
    exit 65
  fi
  printf '%s\n' "$output_name" >> "$seen_outputs"
done < "$manifest"
(( row_count > 0 )) || {
  printf 'manifest contains no jobs\n' >&2
  exit 65
}

mkdir -- "$output_dir"
output_dir="$(cd -- "$output_dir" && pwd -P)"
printf '%s\n' 'WorkWithLLM FFmpeg bounded-batch lab' > "$output_dir/.lab-marker"

while IFS= read -r row || [[ -n "$row" ]]; do
  [[ -z "$row" || "$row" == \#* ]] && continue
  parse_row "$row" || {
    printf 'line %s: expected exactly four tab-separated fields\n' "$line_number" >&2
    exit 65
  }
  input_path="$input_dir/$input_name"
  output_path="$output_dir/$output_name"
  [[ ! -e "$output_path" ]] || {
    printf 'refusing to overwrite: %s\n' "$output_path" >&2
    exit 73
  }
  ffmpeg -hide_banner -loglevel warning -nostdin -n \
    -protocol_whitelist file,pipe -i "$input_path" -ss "$start" -t "$duration" \
    -map '0:v:0?' -map '0:a:0?' -sn -dn -map_metadata -1 -map_chapters -1 \
    -c:v libx264 -preset veryfast -crf 28 -pix_fmt yuv420p \
    -c:a aac -b:a 64k "$output_path"
  ffprobe -v error -show_format -show_streams -of json "$output_path" \
    > "$output_path.probe.json"
done < "$manifest"

printf 'PASS: jobs=%s output=%s\n' "$row_count" "$output_dir"
printf 'temporary-workspace=%s\n' "$workspace"
