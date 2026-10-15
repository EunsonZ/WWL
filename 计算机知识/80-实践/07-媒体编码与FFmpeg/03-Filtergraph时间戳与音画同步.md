---
type: lab
domain: computer-science
stage: 20
status: ready
difficulty: 进阶
estimated_minutes: 40
verified_on: 2026-09-03
topics:
  - filtergraph
  - PTS
  - time-base
  - audio-video-sync
tags:
  - computer-science/media
  - computer-science/ffmpeg
  - computer-science/lab
---

# Filtergraph、时间戳与音画同步

## 目标与受控假设

本实验故意把合成音频的 PTS 推迟 0.4 秒，记录修正前后的 packet 与 stream 时间，再用显式标签 filtergraph 复制视频、水平翻转右半边、横向拼接，并把音频时间线归零。因为延迟是我们亲手注入的，才知道应如何修正；面对真实文件时，`asetpts=PTS-STARTPTS` 只能改变时间戳，不能自动判断口型、事件或录制时钟哪个才是正确基准。

先读 [[计算机知识/60-数据编码与媒体系统/11-流媒体时间戳同步Seek与协议边界|时间戳、同步与 Seek]] 和 [[计算机知识/60-数据编码与媒体系统/15-FFmpeg滤镜图时间基映射与硬件加速|滤镜图、时间基与映射]]。采样和波形背景见 [[数学/70-信号处理与多模态数学/02-采样定理波形STFT与Mel频谱|采样、波形、STFT 与 Mel 频谱]]。

## 运行源码

在本目录执行 `bash ./03_filtergraph_sync.sh`。

<!-- code-sync: ./03_filtergraph_sync.sh -->
```bash
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
```

## 读 filtergraph 与时间线

把第二条 graph 画成数据流：视频 `[0:v]` 先 `setpts`，经 `split` 形成左右两支，右支 `hflip`，再由 `hstack` 合成 640×240 输出 `[v]`；音频 `[0:a]` 独立经过 `asetpts`、异步重采样、补齐和截断成为 `[a]`。分号连接多条滤镜链，方括号标签连接输出与下一个输入，`-map` 决定哪些端点进入输出文件。

对比 `streams-before.json` 与 `streams-after.json` 的 stream `start_time`，再从两份 packet JSON 中分别找最早的视频/音频 `pts_time`。PTS 是呈现时间，DTS 是解码时间，二者可能因帧重排不同；`TB` 是表达 PTS 的时间基，不是秒值本身。不要用“第 N 个包”替代时间戳对齐。

本机 2026-09-03 使用 `ffmpeg/ffprobe 9.0.1` 真实生成受控 0.4 秒偏移，并输出修正前后 JSON 与 4 秒同步样片。该结果只证明这条合成时间线按预期处理；没有主观播放验收，也未覆盖可变帧率、B 帧重排异常、采集时钟漂移、断续直播或真实口型校准。

## 练习、成功标准与恢复

把延迟改为 0.8 秒并使用新目录运行，预测修正前音频 start time；随后移除音频 `asetpts`，观察输出时间线。每次只改一个变量。

- [ ] 能用带标签的数据流解释每条链，而非只复制一行命令；
- [ ] 能从 JSON 指出修正前音频晚于视频、修正后两者从共同时间线开始；
- [ ] 能解释 PTS、DTS 与 time base 的区别；
- [ ] 明确知道“时间戳归零”不等于真实内容一定同步。

恢复方式见 [[计算机知识/80-实践/07-媒体编码与FFmpeg/00-媒体编码与FFmpeg实践-MOC#完成标准与恢复|统一恢复边界]]。

---

**上一站**：[[计算机知识/80-实践/07-媒体编码与FFmpeg/02-转封装转码裁剪与客观对比|转封装、转码与对比]] · **下一站**：[[计算机知识/80-实践/07-媒体编码与FFmpeg/04-批处理Manifest与不可信输入边界|Manifest 与不可信输入]] · **返回**：[[计算机知识/80-实践/07-媒体编码与FFmpeg/00-媒体编码与FFmpeg实践-MOC|实践 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/09-计算机网络-课程地图|计算机网络 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|网络：UDP、TCP、可靠传输与应用分帧]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
