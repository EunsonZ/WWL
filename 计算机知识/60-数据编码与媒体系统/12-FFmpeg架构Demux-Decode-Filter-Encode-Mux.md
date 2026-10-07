---
type: lesson
domain: computer-science
stage: 6
status: ready
difficulty: 中级
estimated_minutes: 75
verified: 2026-09-03
local_toolchain: FFmpeg 9.0.1 (Homebrew, macOS arm64)
topics:
  - FFmpeg
  - libavformat
  - libavcodec
  - libavfilter
  - stream selection
  - transcoding
tags:
  - computer-science/media
  - computer-science/ffmpeg
  - computer-science/systems
---

# FFmpeg 架构：Demux → Decode → Filter → Encode → Mux

FFmpeg 不是“一个视频格式”，也不只是一条转码命令。它同时包含命令行工具和可复用库。理解 **packet（压缩包）怎样变成 frame（解码帧），又怎样回到 packet**，能把大多数命令行错误从“玄学参数问题”还原成明确的数据流问题。

> [!info] 本页的证据分层
> - **稳定模型**：库的职责、packet/frame 边界、stream copy 与 transcoding 的差异，来自 FFmpeg 官方文档与公开 API。
> - **当前 CLI 快照**：2026-09-03 在本机实查 `/opt/homebrew/bin/ffmpeg -version` 与 `ffprobe -version`，二者均为 9.0.1；本机构建为 macOS arm64 Homebrew 包。
> - **没有验证**：本页没有据此声称 Windows/Linux、其他 FFmpeg 版本、其他编译选项或任意输入文件会产生相同能力列表与输出。

## 本课目标

学完后，你应该能够：

1. 画出 demux、decode、filter、encode、mux 的数据流；
2. 区分 `AVPacket`、`AVFrame`、container、codec 与 stream；
3. 把 `libavformat`、`libavcodec`、`libavfilter` 映射到 CLI 的对应阶段；
4. 正确解释输入选项、输出选项、stream specifier 与 `-map` 的作用域；
5. 在日志中判断一条流是在 stream copy，还是经过了解码与重编码。

## 1. 先把五个动作放到一张图里

```text
input URL / file
      │ bytes
      ▼
demuxer (libavformat)
      │ compressed AVPacket, each belongs to one stream
      ▼
audio/video decoder (libavcodec)
      │ decoded AVFrame: video pixels / audio samples
      ▼
filtergraph (libavfilter)
      │ transformed AVFrame
      ▼
audio/video encoder (libavcodec)
      │ compressed AVPacket
      ▼
muxer (libavformat)
      │ interleaved container bytes
      ▼
output URL / file
```

**Demux（解复用）**读取容器或输入协议，把交错存储的音频、视频、字幕、数据等拆成各自 stream 的压缩 packet。上图的 decode → `AVFrame` → filter → encode 主链**只描述音频和视频**：视频 frame 通常承载像素平面，音频 frame 承载一批采样。**Filter（滤镜）**处理这些 decoded frames，而不是任意压缩 packet。**Mux（复用）**按目标容器规则写 header、stream 描述、时间戳与交错 packet。

其他 stream type 不能硬塞进这条 `AVFrame` 主链：

```text
subtitle packet
  ├─ stream copy ───────────────────────────────► muxer
  └─ subtitle decoder → AVSubtitle/字幕表示
                         → subtitle encoder ────► muxer

data / attachment stream
  └─ packet 或 stream header/extradata/metadata
                         → 显式选择/复制 ────────► muxer
```

FFmpeg 的公开字幕 API 仍有独立的 `AVSubtitle` / subtitle decode-encode 表示，并不承诺走 `avcodec_receive_frame()` 的音视频 `AVFrame` 接口。CLI 的软字幕 copy/转码也是独立字幕流；而 `subtitles` filter 的“烧录”是把字幕渲染成**视频像素**后再进入视频 filter/encoder，属于另一条路径。data/attachment 通常不做音视频意义上的 decode/filter，能否复制由目标容器、codec parameters、extradata 与具体 muxer 决定。

因此，容器不等于 codec：Matroska、MP4 等容器可以承载多条不同 codec 的流；H.264、AV1、AAC、Opus 等 codec 定义压缩表示。前置概念见 [[计算机知识/60-数据编码与媒体系统/10-封装格式Codec-Container-Mux-Demux|封装格式：Codec、Container、Mux 与 Demux]]。

## 2. Packet 与 frame 是关键边界

| 对象 | 所在阶段 | 典型内容 | 重要字段/关系 |
| --- | --- | --- | --- |
| `AVPacket` | demuxer→decoder，encoder→muxer | 压缩字节及其旁路信息 | stream index、PTS/DTS、duration、flags |
| `AVFrame` | audio/video decoder→filter→encoder | 解码后的像素或音频采样 | format、尺寸/采样率、channel layout、PTS、time base |
| `AVSubtitle` | 字幕 decode/encode 分支 | 文本或位图矩形及显示时序 | `rects`、`start_display_time`、`end_display_time`、PTS；不是普通音视频 `AVFrame` |
| `AVStream` | container 内的一条逻辑流 | codec 参数、时间基、metadata、disposition | index 只在对应输入/输出中有意义 |
| `AVFormatContext` | 输入/输出容器会话 | streams、demuxer/muxer、I/O 状态 | 不是 codec decoder 本身 |
| `AVCodecContext` | 某条流的编解码器实例 | codec 配置、状态、缓冲 | 一般按需要解码/编码的 stream 建立 |

data 与 attachment 是 `AVStream` 的媒体类型分支，不对应一种“data frame”或“attachment frame”。它们可能由 packet、codec parameters、extradata 或 metadata 承载；必须针对具体 demuxer/muxer 检查，不能套用下面的 audio/video send/receive 伪流程。

packet 与 frame 不是一一对应的可靠契约：一个 packet 可能含一个或多个编码帧，一帧也可能需要多个 packet；编解码器还可能内部缓冲并重排。因此库 API 使用“送入，再尽可能取出”的模型，而不是假定每送一个 packet 就立刻得到一个 frame。

官方 API 的典型**音视频转码**生命周期可以概念化为：

```text
avformat_open_input → avformat_find_stream_info
  loop av_read_frame(packet)
    selected audio/video stream:
      avcodec_send_packet
      loop avcodec_receive_frame(frame)
        av_buffersrc_add_frame → av_buffersink_get_frame
        avcodec_send_frame → avcodec_receive_packet
        rescale timestamps → av_interleaved_write_frame
  flush decoder / filters / encoder
av_write_trailer → release contexts
```

这不是可直接复制的完整 C 程序：错误处理、资源所有权、`EAGAIN`/EOF、flush、时间基换算和每条 stream 的状态都不能省略。它只用来把 CLI 的**音视频**日志映射回公开 API；字幕要走字幕 API/CLI 分支，data/attachment 要按容器分支处理。官方可编译参考见文末 `transcode.c`。

## 3. 三个核心库怎样分工

### `libavformat`：格式、stream、packet 与 I/O

- 输入侧探测/打开格式，发现 streams，读取交错 packet；
- 输出侧创建 streams，写 header，交错写 packet，写 trailer；
- 通过 AVIO 连接普通文件或受支持的 URL/protocol；
- 不负责把 H.264 packet 还原为像素。

官方 demuxing API 用 `avformat_open_input()` 打开输入，以 `av_read_frame()` 读取下一个 packet，最后 `avformat_close_input()` 清理。名称中的 `read_frame` 是历史 API 名称；它返回的是 `AVPacket`，不要因此把它误当解码帧。

### `libavcodec`：音视频 packet ↔ `AVFrame`，字幕另有表示

- audio/video decoder 消费压缩 packet，产生 decoded `AVFrame`；
- audio/video encoder 消费 `AVFrame`，产生压缩 packet；
- 字幕 codec 使用独立的字幕表示/API；不能把 `AVSubtitle` 当成音视频 `AVFrame`；
- codec 是否可用取决于具体构建、外部库与平台后端；
- `avcodec_send_packet()` / `avcodec_receive_frame()` 与反向的 send-frame / receive-packet 体现缓冲式接口。

### `libavfilter`：以音视频 frame 为边的图

- filter 实例由 input/output pads 连接；
- `buffer` / `abuffer` 可把应用提供的 frame 送入图，sink 取出结果；
- 尺寸、像素格式、采样格式、采样率、channel layout 和 time base 会参与协商；
- filtergraph 只要改变 frame 内容或时间，就不能与同一条流的 `-c copy` 共存。

缩放/像素格式转换常会使用 `libswscale`，重采样常会使用 `libswresample`。它们是相关库，但不要把所有自动协商都简单称为“filter 自己零成本完成”。格式转换、缓冲和数据搬运都可能是性能与质量决策。

## 4. Stream copy 是五段流水线的旁路

```text
demuxer ── compressed packets ──► muxer
           no decode/filter/encode
```

`-c copy`（也可按类型写 `-c:v copy`、`-c:a copy`）选择 **stream copy**。它通常很快且没有重编码损失，但目标容器必须能接受相关 codec 参数、extradata、时间戳和 packet 布局。它也不能执行缩放、裁剪、烧录字幕、混音等 frame 级处理。

```bash
# 示例路径均为合成占位名；只对自己拥有的本地文件运行。
# -n 在目标存在时直接失败，不会覆盖。
ffmpeg -hide_banner -n \
  -i "input.example.mkv" \
  -map 0:v:0 -map '0:a:0?' \
  -c copy \
  "output.example.mkv"
```

`0:v:0` 表示“第 0 个输入中的第 0 条视频流”；`'0:a:0?'` 的尾部 `?` 表示没有匹配音频时忽略这一条 map，而不是忽略不存在的输入文件。POSIX shell 会把未引用的 `?` 当通配符，zsh 还可能直接报 `nomatch`，所以命令中的 optional map 要用单引号保护。明确 `-map` 可排除没有选择的附件、数据流和额外音轨，但小写 `v` 仍包括 attached picture，`0:v:0` 可能选中封面。[官方 stream specifiers](https://ffmpeg.org/ffmpeg.html#Stream-specifiers) 中大写 `V` 才排除附图、缩略图和封面；需要运动视频时可用 `0:V:0`，或先 probe disposition 再指定确认的 stream index。选流也不自动清理 metadata：默认 global metadata 来自首输入，per-stream metadata 随流复制，显式 metadata 策略见 [[计算机知识/60-数据编码与媒体系统/14-FFmpeg常用转码裁剪拼接字幕与音频处理#2. 转封装：复制 packet，不改变编码内容|常用处理：转封装中的 metadata 映射与隐私边界]]。

## 5. Transcoding 才走 decode → filter → encode

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mkv" \
  -map 0:v:0 -map '0:a:0?' \
  -vf "scale=w=1280:h=-2" \
  -c:v libx264 -crf 20 -preset medium \
  -c:a aac -b:a 192k \
  "output.example.mp4"
```

这条命令是教学模板，不是跨机器能力承诺：运行前用 `ffmpeg -encoders` 确认 `libx264`、`aac`，再用目标播放器/系统的兼容性要求选择像素格式、profile、level、音频布局和容器。`-vf` 处理 decoded video frame，因此视频必须重编码；音频没有滤镜，但此例仍显式选择 AAC 编码。

## 6. 选项顺序就是作用域

FFmpeg 的一般规则是：**选项作用于它后面的下一个输入或输出，并在文件边界重置；global option 例外。** 先把命令拆成块：

```text
global options
  input options  -i input-0
  input options  -i input-1
  output options    output-0
  output options    output-1
```

```bash
ffmpeg -hide_banner -n \
  -ss 00:00:10 -i "camera.example.mp4" \
  -i "narration.example.wav" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -c:a aac \
  "lesson.example.mp4"
```

- `-ss` 在第一个 `-i` 之前，是第一个输入的 seek 选项；
- 第二个 `-i` 建立输入 1，`1:a:0` 才指向其第一条音频；
- `-map`、`-c:v`、`-c:a` 位于输出 URL 之前，是这个输出的选项；
- `-n` 是 global option，目标已存在时失败；不要把 `-y` 写进可随手复制的教学模板，`-y` 会无询问覆盖全部输出。

同一命令有多个输出时，每个输出分别选择 streams 与 codecs：

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mkv" \
  -map 0:v:0 -c:v libx264 -an "video-only.example.mp4" \
  -map 0:a:0 -c:a flac -vn "audio-only.example.flac"
```

第一个输出的 `-an`、`-c:v` 不应被想当然地套用到第二个输出。读命令时始终从每个 output URL 向左找到属于它的选项块。

## 7. 自动 stream selection 与手动 `-map`

未对某个输出使用 `-map` 时，FFmpeg 会按输出容器可接受的类型自动选择视频、音频和字幕；data/attachment 不会自动选择。自动规则方便交互尝试，但课程、批处理和可复现实验更适合显式 map。

常用写法：

| 写法 | 含义 | 边界 |
| --- | --- | --- |
| `-map 0` | 输入 0 的全部 streams | 可能带入附件、data 或不需要的 metadata |
| `-map 0:v:0` | 第一条视频 | 若没有视频则失败 |
| `-map '0:a?'` | 输入 0 的全部音频，可缺省 | 单引号保护 shell 中的 `?`；不是“第一条音频” |
| `-map 0 -map -0:a:1` | 全选后排除第二条音频 | 负 map 依赖前面已有选择 |
| `-map "[vout]"` | 选择 complex filtergraph 的标记输出 | label 必须存在且恰好被消费一次 |

使用 `-map` 会关闭该输出的默认选择。复杂 filtergraph 的**无标签输出 pad**有额外自动路由规则，容易进入第一个输出甚至导致格式错误；详见 [[计算机知识/60-数据编码与媒体系统/15-FFmpeg滤镜图时间基映射与硬件加速|FFmpeg 滤镜图、时间基、映射与硬件加速]]。

## 8. 从日志读回真实管线

FFmpeg 启动时通常打印 stream mapping，例如：

```text
Stream #0:0 -> #0:0 (h264 (native) -> h264 (...))
Stream #0:1 -> #0:1 (copy)
```

应把它读成“视频被解码后重新编码，音频 packet 被直接复制”。日志中的 encoder/decoder 名称、像素格式变换、自动插入的 scale/aresample、硬件后端与 fallback 才是实际选择证据；仅看到输出扩展名不能证明 codec，看到 `-hwaccel` 也不能证明全链路都在硬件中。

### 常见症状定位

| 症状 | 优先检查的阶段 | 证据 |
| --- | --- | --- |
| `Invalid data found` / 无法识别输入 | AVIO、probe、demux | 完整错误、输入 hash、`ffprobe -show_error` |
| `Decoder not found` | decode | `ffmpeg -decoders`、输入 stream codec |
| filter 不接受像素/采样格式 | filter 协商 | filtergraph、自动转换日志、frame format |
| `Encoder not found` | encode | `ffmpeg -encoders`、本机构建配置 |
| codec/container 不兼容 | mux | 目标 muxer 帮助与 codec tag/extradata |
| `Non-monotonous DTS` | 时间戳/重排/mux | packet PTS/DTS/time base，而非只看 nominal FPS |

## 9. 本机 2026-09-03 快照

实际执行并读到：

```text
ffmpeg version 9.0.1
ffprobe version 9.0.1
Apple clang 21.0.0
libavutil 61.1.101
libavcodec 63.1.101
libavformat 63.1.101
libavfilter 12.1.101
```

构建配置包含 `libx264`、`libx265`、`libopus`、`videotoolbox` 与 `audiotoolbox` 等，但这只是**本机构建时能力**。它没有验证具体文件、所有 profile/pixel format、驱动/设备运行路径、性能、质量或其他操作系统。复现时必须保存完整 `ffmpeg -version`，不要只保存“9.0.1”这一行。

## 练习：先画图，再写命令

1. 输入文件含 1 条 H.264 视频、2 条 AAC 音频和 1 条字幕。目标是保留视频 packet、只保留第二条音频并写入新 Matroska。画出实际经过的阶段，再写带 `-n` 的 `-map` / `-c copy` 命令。
2. 把同一视频缩小到宽 1280，并保留第一条音频 packet。解释为什么只能对音频使用 copy，视频必须 decode/filter/encode。
3. 给一条含两个输入、两个输出的命令加括号，标出每个 input/output 的 options。故意把一个 `-ss` 移到 `-i` 两侧，预测成本与精度差异，下一课用 probe 验证。

可运行合成素材与检查流程见 [[计算机知识/80-实践/07-媒体编码与FFmpeg/01-生成合成音视频并用ffprobe诊断|生成合成音视频并用 ffprobe 诊断]]；本页不另建重复脚本。

### 成功标准

- 能明确说出 packet 与 frame 的边界，并拒绝“一 packet 必然一 frame”的假设；
- 能从命令判断每条输出 stream 是 copy 还是 transcode；
- 能解释 `-map '0:a:0?'` 中三个索引/类型部分、`?` 的 optional 语义与 shell 引用要求；
- 能把音视频 `AVFrame` 主链与 `AVSubtitle`、data、attachment 分支分开画出，不声称所有 stream 都经过 send/receive-frame 与 filtergraph；
- 能为每个选项指出 global、input、output 或 per-stream 作用域；
- 能用日志或 probe 证据确认真实选择，而不是从扩展名猜测。

## 诊断清单

```bash
# 只读能力与帮助；不会处理媒体或写输出。
ffmpeg -hide_banner -version
ffmpeg -hide_banner -formats
ffmpeg -hide_banner -decoders
ffmpeg -hide_banner -encoders
ffmpeg -hide_banner -filters
ffmpeg -hide_banner -h demuxer=matroska
ffmpeg -hide_banner -h muxer=mp4
```

长列表会随构建变化。保存时记录日期、路径与完整版本配置；不要把“列表中存在”升级成“该设备上的目标媒体已成功通过端到端验收”。

## 官方来源

- [FFmpeg CLI Documentation：Synopsis、Streamcopy、Transcoding、Filtering、Stream selection 与 Options](https://ffmpeg.org/ffmpeg.html)
- [FFmpeg Formats Documentation：libavformat、demuxers 与 muxers](https://ffmpeg.org/ffmpeg-formats.html)
- [FFmpeg Doxygen：Demuxing API](https://ffmpeg.org/doxygen/trunk/group__lavf__decoding.html)
- [FFmpeg Doxygen：`avcodec_send_packet()` / decode implementation reference](https://ffmpeg.org/doxygen/trunk/decode_8c.html)
- [FFmpeg Doxygen：`AVSubtitle` 字幕表示](https://ffmpeg.org/doxygen/trunk/structAVSubtitle.html)
- [FFmpeg Doxygen：官方 `transcode.c` 示例](https://ffmpeg.org/doxygen/trunk/transcode_8c-example.html)
- [FFmpeg Filters Documentation：Filtergraph description](https://ffmpeg.org/ffmpeg-filters.html#Filtergraph-description)

---

**上一站**：[[计算机知识/60-数据编码与媒体系统/11-流媒体时间戳同步Seek与协议边界|流媒体：时间戳、同步、Seek 与协议边界]] · **下一站**：[[计算机知识/60-数据编码与媒体系统/13-ffprobe媒体诊断与可复现检查|ffprobe 媒体诊断与可复现检查]] · **容器前置**：[[计算机知识/60-数据编码与媒体系统/10-封装格式Codec-Container-Mux-Demux|封装格式：Codec、Container、Mux 与 Demux]] · **I/O 连接**：[[计算机知识/30-计算机系统/10-IO设备总线DMA与中断|I/O 设备、总线、DMA 与中断]] · **返回**：[[计算机知识/60-数据编码与媒体系统/00-数据编码与媒体系统-MOC|数据编码与媒体系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/60-数据编码与媒体系统/00-数据编码与媒体系统-MOC|数据编码与媒体系统 MOC]]。网络传输相关路线：[[计算机知识/00-开始/课程地图/09-计算机网络-课程地图|计算机网络 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|网络：UDP、TCP、可靠传输与应用分帧]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
