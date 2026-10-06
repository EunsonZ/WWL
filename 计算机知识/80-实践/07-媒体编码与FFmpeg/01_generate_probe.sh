#!/usr/bin/env bash
set -euo pipefail

for tool in ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'SKIP: %s is not available in PATH\n' "$tool" >&2
    exit 77
  fi
done

if (( $# > 1 )); then
  printf 'usage: %s [new-output-directory]\n' "$0" >&2
  exit 64
fi

if (( $# == 1 )); then
  output_dir="$1"
  if [[ -z "$output_dir" || "$output_dir" == / || -e "$output_dir" ]]; then
    printf 'refusing existing or unsafe output directory: %s\n' "$output_dir" >&2
    exit 73
  fi
  output_parent="$(dirname -- "$output_dir")"
  [[ -d "$output_parent" ]] || {
    printf 'output parent does not exist: %s\n' "$output_parent" >&2
    exit 73
  }
  mkdir -- "$output_dir"
else
  temp_base="${TMPDIR:-/tmp}"
  temp_base="${temp_base%/}"
  [[ -d "$temp_base" ]] || {
    printf 'temporary directory does not exist: %s\n' "$temp_base" >&2
    exit 73
  }
  output_dir="$(mktemp -d "$temp_base/workwithllm-ffmpeg-generate.XXXXXX")"
fi

output_dir="$(cd -- "$output_dir" && pwd -P)"
printf '%s\n' 'WorkWithLLM FFmpeg synthetic-media lab' > "$output_dir/.lab-marker"

media="$output_dir/synthetic.mp4"
probe="$output_dir/probe.json"
[[ ! -e "$media" && ! -e "$probe" ]] || {
  printf 'refusing to overwrite an output file\n' >&2
  exit 73
}

ffmpeg -hide_banner -loglevel warning -nostdin -n \
  -f lavfi -i 'testsrc2=size=320x240:rate=25:duration=3' \
  -f lavfi -i 'sine=frequency=440:sample_rate=48000:duration=3' \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 96k -shortest "$media"

ffprobe -v error -show_format -show_streams -of json "$media" > "$probe"

printf 'PASS: generated=%s\n' "$media"
printf 'probe-json=%s\n' "$probe"
printf 'inspect: ffprobe -v error -show_format -show_streams -of json %q\n' "$media"
