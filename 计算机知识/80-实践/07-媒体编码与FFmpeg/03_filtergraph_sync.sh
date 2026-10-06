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
  [[ -n "$output_dir" && "$output_dir" != / && ! -e "$output_dir" ]] || {
    printf 'refusing existing or unsafe output directory: %s\n' "$output_dir" >&2
    exit 73
  }
  [[ -d "$(dirname -- "$output_dir")" ]] || {
    printf 'output parent does not exist\n' >&2
    exit 73
  }
  mkdir -- "$output_dir"
else
  temp_base="${TMPDIR:-/tmp}"
  temp_base="${temp_base%/}"
  output_dir="$(mktemp -d "$temp_base/workwithllm-ffmpeg-sync.XXXXXX")"
fi

output_dir="$(cd -- "$output_dir" && pwd -P)"
printf '%s\n' 'WorkWithLLM FFmpeg timestamp lab' > "$output_dir/.lab-marker"

misaligned="$output_dir/misaligned.mkv"
corrected="$output_dir/corrected.mp4"
[[ ! -e "$misaligned" && ! -e "$corrected" ]] || {
  printf 'refusing to overwrite an output file\n' >&2
  exit 73
}

ffmpeg -hide_banner -loglevel warning -nostdin -n \
  -f lavfi -i 'testsrc2=size=320x240:rate=25:duration=4' \
  -f lavfi -i 'sine=frequency=880:sample_rate=48000:duration=3.6' \
  -filter_complex '[1:a]asetpts=PTS+0.4/TB[late]' \
  -map 0:v:0 -map '[late]' -c:v libx264 -preset veryfast -crf 20 \
  -pix_fmt yuv420p -c:a pcm_s16le "$misaligned"

ffprobe -v error -read_intervals '0%+1' -show_packets \
  -show_entries packet=codec_type,stream_index,pts_time,dts_time,duration_time,flags \
  -of json "$misaligned" > "$output_dir/timestamps-before.json"

ffmpeg -hide_banner -loglevel warning -nostdin -n -i "$misaligned" \
  -filter_complex \
  '[0:v]setpts=PTS-STARTPTS,split=2[left][right_source];[right_source]hflip[right];[left][right]hstack=inputs=2,fps=25,format=yuv420p[v];[0:a]asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0,apad,atrim=duration=4[a]' \
  -map '[v]' -map '[a]' -t 4 \
  -c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 96k "$corrected"

ffprobe -v error -read_intervals '0%+1' -show_packets \
  -show_entries packet=codec_type,stream_index,pts_time,dts_time,duration_time,flags \
  -of json "$corrected" > "$output_dir/timestamps-after.json"
ffprobe -v error -show_entries stream=index,codec_type,start_time,duration \
  -show_entries format=start_time,duration -of json "$misaligned" \
  > "$output_dir/streams-before.json"
ffprobe -v error -show_entries stream=index,codec_type,start_time,duration \
  -show_entries format=start_time,duration -of json "$corrected" \
  > "$output_dir/streams-after.json"

printf 'PASS: corrected=%s\n' "$corrected"
printf 'compare=%s and %s\n' \
  "$output_dir/streams-before.json" "$output_dir/streams-after.json"
