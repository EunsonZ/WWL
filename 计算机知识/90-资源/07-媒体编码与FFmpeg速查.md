---
type: reference
aliases:
  - 媒体编码与 FFmpeg 速查
domain: computer-science
stage: 90
status: ready
difficulty: 基础
estimated_minutes: 30
topics:
  - FFmpeg
  - 音视频
  - 转码
  - probe
tags:
  - computer-science/reference
  - computer-science/media
verified: 2026-09-03
---

# 媒体编码与 FFmpeg 速查

FFmpeg 命令的核心顺序是“输入 → 选择流 → 过滤/编码 → 输出封装”。选项有作用域，位置重要：全局选项先写；输入选项放在对应 `-i` 前；输出选项放在对应输出文件前。具体构建的编码器、封装器和硬件支持必须用现场 `ffmpeg -encoders`、`-muxers`、`-hwaccels` 复核。

## 选项作用域

| 作用域 | 示例 | 含义/陷阱 |
| --- | --- | --- |
| 全局 | `-hide_banner -loglevel error -nostdin -n` | 影响整个进程；`-nostdin` 防止后台任务等待交互，`-n` 在输出存在时失败。只有精确核对目标、保留原件并得到明确覆盖授权后才考虑 `-y`。 |
| 输入 | `-ss 00:01:00 -thread_queue_size N -f FORMAT -i INPUT` | 作用于下一个输入；`-ss` 放在 `-i` 前后可能走不同寻址路径，精确剪辑需复核关键帧和输出。 |
| 输出 | `-map 0:v:0 -c:v libx264 -c:a aac -movflags +faststart OUT.mp4` | 作用于下一个输出；多输出时重复写，不能把一个输出的编码器默认当成所有输出。 |
| 流级 | `-c:v`、`-b:a`、`-pix_fmt` | 冒号是 stream specifier；`-c copy` 是逐流拷贝，未必能被目标容器接受。 |

## 探测与选择

```bash
ffprobe -v error -show_format -show_streams -of json "INPUT.example.mkv"
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate -of json "INPUT.example.mkv"

# 只读 packet 路径：显式 stream copy 到 null muxer，不选择默认 encoder，也不创建媒体文件。
ffmpeg -hide_banner -v error -xerror \
  -i "INPUT.example.mkv" \
  -map '0:v?' -map '0:a?' \
  -c copy -f null -
```

`ffprobe` 的 `-show_format` 描述容器，`-show_streams` 描述每条媒体流；`-select_streams` 限定后续 stream 查询。`-map` 使用从 0 开始的输入/流索引；`?` 使可选流缺失时不报错。POSIX shell 会把裸 `?` 当通配符，因此 optional map 使用单引号；PowerShell/CMD 需要按各自引用规则改写。上面的 null-output 骨架显式 `-c copy`，只证明 demux/packet-read 路径，不执行 decode、不过滤、也不证明播放。自动选择方便但不透明，交付脚本建议显式 `-map`，并检查 `ffprobe` 输出与日志。

## 转封装、转码与典型骨架

| 任务 | 骨架 | 验收 |
| --- | --- | --- |
| 转封装（不重编码） | `ffmpeg -hide_banner -n -i "IN.example.mkv" -map 0 -c copy "OUT.example.mkv"` | 只在目标容器支持原流、时间戳和附件时可行；否则会失败或播放异常。 |
| 转码 | `ffmpeg -hide_banner -n -i "IN.example.mkv" -map 0:v:0 -map '0:a:0?' -c:v ENCODER -c:a AUDIO "OUT.example.mp4"` | `ENCODER` / `AUDIO` 必须替换为本机构建中已确认的 encoder；比较输入输出 probe。 |
| 只导出音频 | `ffmpeg -hide_banner -n -i "IN.example.mkv" -map 0:a:0 -vn -c:a ENCODER "OUT.example.m4a"` | `-vn` 排除视频；目标扩展名不能替代对 codec/container 的检查。 |
| 片段预览 | `ffmpeg -hide_banner -n -ss START -i "IN.example.mkv" -t DURATION -map 0:v:0 -map '0:a:0?' -c:v ENCODER -c:a AUDIO "OUT.example.mp4"` | `-t` 是时长；以实际时间戳和关键帧验证边界，避免把快速 seek 当逐帧精确。 |
| 过滤后编码 | `ffmpeg -hide_banner -n -i "IN.example.mkv" -vf 'scale=...' -af '...' -c:v ENCODER -c:a AUDIO "OUT.example.mkv"` | 滤镜输出必须走相应 encoder；先小样本验证色彩、音画同步和字幕。 |

## 安全与可恢复

- 不把不可信文件名直接拼入 shell；使用数组/安全 quoting，并把输出写入独立目录。
- 默认不使用 `-y`；若自动化必须覆盖，先锁定精确输出路径并保留源文件/校验和。
- 不为“修复”随意添加 `-ignore_unknown`、`-err_detect ignore_err`、`-copy_unknown` 或 bitstream filter；这些选项可能隐藏损坏或改变语义。
- 处理网络输入时设置超时、限制协议/协议白名单（按当前 FFmpeg 版本帮助确认），不要把任意 URL 当作可信媒体。
- 转码完成后重新 `ffprobe`，检查流数量、时长、编码器、像素格式、采样率、字幕/元数据，并抽样播放；退出码 0 不是画面和同步正确的充分证据。

官方核验入口（2026-09-03）：[ffmpeg 工具文档](https://ffmpeg.org/ffmpeg.html) · [ffprobe 文档](https://ffmpeg.org/ffprobe.html) · [格式、muxer 与 demuxer](https://ffmpeg.org/ffmpeg-formats.html) · [codec 选项](https://ffmpeg.org/ffmpeg-codecs.html)。

继续阅读：[[计算机知识/90-资源/08-编码格式容器与Codec选择矩阵|编码格式、容器与 Codec 选择矩阵]] · [[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]] · [[AI/20-LLM/00-LLM-MOC|LLM MOC]]

**返回**：[[计算机知识/00-开始/00-计算机知识-首页|计算机知识首页]]
