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
  output_dir="$(mktemp -d "$temp_base/workwithllm-ffmpeg-compare.XXXXXX")"
fi

output_dir="$(cd -- "$output_dir" && pwd -P)"
printf '%s\n' 'WorkWithLLM FFmpeg comparison lab' > "$output_dir/.lab-marker"
# Fixed relative filter option values need no output-path filtergraph escaping.
cd -- "$output_dir"

source_media="$output_dir/source-lossless.nut"
remuxed_media="$output_dir/remuxed.mkv"
compressed_media="$output_dir/transcoded.mp4"
cropped_media="$output_dir/trimmed-and-cropped.mp4"
for path in "$source_media" "$remuxed_media" "$compressed_media" "$cropped_media"; do
  [[ ! -e "$path" ]] || {
    printf 'refusing to overwrite: %s\n' "$path" >&2
    exit 73
  }
done

ffmpeg -hide_banner -loglevel warning -nostdin -n \
  -f lavfi -i 'testsrc2=size=320x240:rate=25:duration=4' \
  -f lavfi -i 'sine=frequency=660:sample_rate=48000:duration=4' \
  -map 0:v:0 -map 1:a:0 -c:v ffv1 -level 3 -c:a pcm_s16le \
  -shortest "$source_media"

ffmpeg -hide_banner -loglevel warning -nostdin -n \
  -i "$source_media" -map 0 -c copy "$remuxed_media"

ffmpeg -hide_banner -loglevel warning -nostdin -n \
  -i "$source_media" -map 0:v:0 -map 0:a:0 \
  -c:v libx264 -preset veryfast -crf 30 -pix_fmt yuv420p \
  -c:a aac -b:a 64k "$compressed_media"

ffmpeg -hide_banner -loglevel warning -nostdin -n \
  -i "$source_media" -ss 1 -t 1.5 \
  -map 0:v:0 -map 0:a:0 -vf 'crop=160:120:80:60' \
  -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \
  -c:a aac -b:a 64k "$cropped_media"

ffmpeg -hide_banner -loglevel info -nostdin \
  -i "$source_media" -i "$compressed_media" \
  -filter_complex \
  "[0:v]split=2[refp][refs];[1:v]split=2[distp][dists];[refp][distp]psnr=stats_file=psnr.log[p];[refs][dists]ssim=stats_file=ssim.log[s]" \
  -map '[p]' -map '[s]' -f null /dev/null \
  2> "$output_dir/metrics-summary.log"

for path in "$source_media" "$remuxed_media" "$compressed_media" "$cropped_media"; do
  base="$(basename -- "$path")"
  ffprobe -v error -show_format -show_streams -of json "$path" \
    > "$output_dir/$base.probe.json"
  bytes="$(wc -c < "$path" | tr -d ' ')"
  printf '%s bytes=%s\n' "$base" "$bytes"
done

printf 'PASS: outputs=%s\n' "$output_dir"
printf 'objective-metrics=%s\n' "$output_dir/metrics-summary.log"
