---
type: lab
domain: computer-science
stage: 20
status: ready
difficulty: 入门
estimated_minutes: 25
verified_on: 2026-09-03
topics:
  - FFmpeg
  - ffprobe
  - JSON
tags:
  - computer-science/media
  - computer-science/ffmpeg
  - computer-science/lab
---

# 生成合成音视频并用 ffprobe 诊断

## 目标

用固定的 `testsrc2` 视频和 440 Hz 正弦波生成 3 秒 MP4，再把 format 与 streams 完整写为 JSON。你会看到“一个文件”其实包含容器级信息和两条不同 codec 的流，而扩展名本身不能回答全部问题。

你可以先直接运行本实验；看到 JSON 后，再读 [[计算机知识/60-数据编码与媒体系统/12-FFmpeg架构Demux-Decode-Filter-Encode-Mux#1. 先把五个动作放到一张图里|架构课的第 1 节]] 与 [[计算机知识/60-数据编码与媒体系统/13-ffprobe媒体诊断与可复现检查#1. 一条最小、机器可读的起点|诊断课的第 1 节]] 解释结果。

> [!note] 最小词典
> - **container**：把多路流、时间戳和元数据组织成文件；本实验是 MP4。
> - **stream**：容器中一条连续媒体轨；本实验有视频和音频两条。
> - **codec**：解释压缩帧/样本的规则；它不等于容器后缀。
> - ffprobe JSON 的 **format** 是容器级证据，**streams** 列出各轨道的 codec 与时间属性，**time_base** 是把整数时间戳换成秒的单位。

## 运行

在本目录执行 `bash ./01_generate_probe.sh`。若想指定位置，只能传入一个尚不存在、父目录已存在的目录，例如 `bash ./01_generate_probe.sh /tmp/my-ffmpeg-lab-01`。脚本不接受媒体 URL 或用户文件作为输入。

<!-- code-sync: ./01_generate_probe.sh -->
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
```

## 观察与练习

打开 `probe.json`，定位：`format.format_name`、`format.duration`、视频流的 `codec_name`/`width`/`height`/`r_frame_rate`/`time_base`，以及音频流的 `codec_name`/`sample_rate`/`channels`。然后把视频尺寸改为 `160x120`、音频频率改为 `880`，在另一个新临时目录运行，比较哪些 JSON 字段改变；波形频率不会直接出现在常规 stream 元数据中，这是“编码参数”与“内容测量”的边界。

本机 2026-09-03 使用 `ffmpeg/ffprobe 9.0.1` 真实生成 3 秒小样并解析 JSON；这验证了当前构建的 H.264/AAC 路径，不证明其他编码器、硬件加速或真实损坏文件可用。

## 成功标准与恢复

- [ ] JSON 可解析，恰有一条视频流与一条音频流；
- [ ] 视频为 320×240、25 fps，音频采样率为 48000 Hz；
- [ ] 能解释 MP4 是容器，H.264/AAC 是两条流的 codec；
- [ ] 二次运行使用新目录，向已有目录运行会被拒绝。

恢复方式见 [[计算机知识/80-实践/07-媒体编码与FFmpeg/00-媒体编码与FFmpeg实践-MOC#完成标准与恢复|实践 MOC 的统一恢复边界]]。这里只删除终端打印且带正确 `.lab-marker` 的精确临时目录。

---

**返回**：[[计算机知识/80-实践/07-媒体编码与FFmpeg/00-媒体编码与FFmpeg实践-MOC|实践 MOC]] · **下一站**：[[计算机知识/80-实践/07-媒体编码与FFmpeg/02-转封装转码裁剪与客观对比|转封装、转码与对比]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/09-计算机网络-课程地图|计算机网络 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|网络：UDP、TCP、可靠传输与应用分帧]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
