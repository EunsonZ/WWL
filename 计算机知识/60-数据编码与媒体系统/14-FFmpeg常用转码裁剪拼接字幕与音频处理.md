---
type: lesson
domain: computer-science
stage: 6
status: ready
difficulty: 中级
estimated_minutes: 90
verified: 2026-09-03
local_toolchain: FFmpeg 9.0.1 (Homebrew, macOS arm64)
topics:
  - remuxing
  - transcoding
  - seeking
  - concatenation
  - subtitles
  - audio processing
tags:
  - computer-science/media
  - computer-science/ffmpeg
  - computer-science/workflow
---

# FFmpeg 常用转码、裁剪、拼接、字幕与音频处理

可靠的 FFmpeg 操作不是背下一条“万能命令”，而是先决定哪些 streams 被选中、哪些只换容器、哪些必须进入 decoded frame/filter、输出容器接受什么，以及失败时会不会覆盖原文件。

> [!warning] 默认安全边界
> 本页所有输入/输出都是合成占位路径，并默认只处理你拥有或明确获授权的本地媒体。示例使用 global option `-n`：若输出已存在就失败。只有已经核对精确目标、保留原件且确实要覆盖时，才把它改为 `-y`；`-y` 会无询问覆盖所有输出。不要让不可信路径、URL、concat manifest 或字幕内容直接进入批处理。

> [!info] 版本证据
> 页面按 FFmpeg 官方 CLI、formats、filters 文档核对，并于 2026-09-03 在本机确认 `ffmpeg` / `ffprobe` 为 9.0.1。示例没有被宣称为在 Windows、Linux、其他构建、每种 codec/container 或真实业务素材上运行通过；执行前应先 probe 输入、列出本机构建能力，再在副本/合成样本上验收。

## 本课目标

学完后，你应该能够：

1. 在转封装（remux）与转码（transcode）之间做有证据的选择；
2. 解释 `-ss` 放在 `-i` 前后以及 stream copy 时的精度/成本差异；
3. 根据字节流可物理拼接、streams 同构或需要 frame 归一化，选择 concat protocol、concat demuxer 或 concat filter；
4. 区分软字幕复用、字幕转码和烧录字幕；
5. 安全完成音轨提取、音频转码与响度处理，并验证 streams、时长和错误。

## 1. 操作前的五问

1. 输入中有哪些 streams？用 [[计算机知识/60-数据编码与媒体系统/13-ffprobe媒体诊断与可复现检查|ffprobe 媒体诊断]]取得 index、codec、time base、duration、语言和 disposition。
2. 输出要保留哪些 streams？显式写 `-map`，不要从扩展名或自动选择猜。
3. 是否改变像素、采样、时长、速度、字幕呈现？若是，对应 stream 必须 decode/filter/encode。
4. 目标 container 能否承载保留的 codec、字幕类型、附件和时间戳？
5. 输出已存在怎么办？默认 `-n`；写到独立新文件，probe/播放验收后再由人决定归档或替换。

```bash
# 只读预检，不创建文件。
ffprobe -v error -show_format -show_streams -of json "input.example.mkv"
ffmpeg -hide_banner -encoders
ffmpeg -hide_banner -muxers
```

能力列表中出现某 encoder/muxer 只证明本机构建注册了组件，不证明目标参数与设备、许可和播放器兼容。

## 2. 转封装：复制 packet，不改变编码内容

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mkv" \
  -map 0:v:0 -map '0:a:0?' \
  -c copy \
  "remuxed.example.mkv"
```

`-c copy` 绕过 decode/filter/encode，通常快且不引入重编码损失。这里没有用 `-map 0`，是为了避免无意复制封面、附件、data、额外音轨或隐私 metadata。转封装仍可能改变 container header、stream index、interleaving、timestamps 或 bitstream framing；“媒体 payload 不重编码”不等于“文件字节相同”。

如果把输出改为 MP4，源 codec/字幕/attachment 不一定能被 MP4 muxer接受。失败时先看目标 muxer 帮助和完整错误，不要直接改后缀或盲目重编码全部 streams。

```bash
ffmpeg -hide_banner -h muxer=mp4
```

## 3. 转码：为交付规格显式选择 encoder

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mkv" \
  -map 0:v:0 -map '0:a:0?' \
  -c:v libx264 -crf 20 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  "transcoded.example.mp4"
```

这个示例把首条视频和可选首条音频转码为常见 MP4 组合；`-movflags +faststart` 调整 MP4 metadata 位置以利渐进下载。`CRF=20` 不是通用“最佳质量”，`yuv420p` 也会丢弃更高位深/更丰富色度信息。交付前必须按源色彩、HDR、alpha、音频布局、目标设备和质量要求重新选择。

本机 9.0.1 当前构建列出了 `libx264` 与 `aac` encoder，但其他机器未必如此。软件发行、商业交付和网络分发还需核对 codec、第三方库、专利/版税及内容权利；“FFmpeg 能编码”不是法律许可证明。

## 4. 时间裁剪：`-ss` 的位置会改变工作方式

### 输入 seek：先向 demuxer 请求跳转

```bash
ffmpeg -hide_banner -n \
  -ss 00:01:30 -i "input.example.mp4" \
  -t 00:00:10 \
  -map 0:v:0 -map '0:a:0?' \
  -c:v libx264 -c:a aac \
  "clip-transcoded.example.mp4"
```

`-ss` 在 `-i` 前，是 input option。多数格式只能先跳到目标之前最近的 seek point。转码且默认启用 accurate seek 时，FFmpeg 会解码并丢弃 seek point 到目标之间的片段；因此通常兼顾较快跳转与较准起点，但具体精度仍受时间戳、decoder 和滤镜影响。

### 输出 seek：从输入开始解码，再丢弃到目标

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mp4" \
  -ss 00:01:30 -t 00:00:10 \
  -map 0:v:0 -map '0:a:0?' \
  -c:v libx264 -c:a aac \
  "clip-output-seek.example.mp4"
```

`-ss` 在输入之后、输出之前，是 output option：输入会被解码并丢弃，直到 timestamp 到达目标。对很长文件可能更慢。不要仅凭两条命令的参数位置承诺逐帧完全一致；用 packet/frame PTS 与实际播放共同验收。

### Stream-copy 裁剪：快，但起点受随机访问点约束

```bash
ffmpeg -hide_banner -n \
  -ss 00:01:30 -i "input.example.mp4" \
  -t 00:00:10 \
  -map 0:v:0 -map '0:a:0?' \
  -c copy \
  "clip-copy.example.mp4"
```

stream copy 不解码目标前多余片段；官方文档说明 input seek 跳到目标之前的 seek point 时，这段前滚数据会被保留。起点可能不精确，首个 GOP 还可能依赖前置参考。需要画面级裁剪时通常选择转码，并记录可接受误差。Seek 与直播/协议边界见 [[计算机知识/60-数据编码与媒体系统/11-流媒体时间戳同步Seek与协议边界|流媒体：时间戳、同步、Seek 与协议边界]]。

## 5. 空间裁剪与缩放

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mp4" \
  -map 0:v:0 -map '0:a:0?' \
  -vf "crop=w=1280:h=720:x=(in_w-out_w)/2:y=(in_h-out_h)/2" \
  -c:v libx264 -crf 20 -preset medium \
  -c:a copy \
  "cropped.example.mkv"
```

`crop` 工作在 decoded frames 上，因此视频不能 `-c:v copy`；音频未改变，可在目标容器兼容时 copy。先确认输入宽高足够、色度采样对坐标/尺寸的对齐要求、SAR/DAR 和目标编码器的尺寸限制。若还需缩放，把 filterchain 用逗号连接：

```text
crop=w=1280:h=720:x=(in_w-out_w)/2:y=(in_h-out_h)/2,scale=w=960:h=-2
```

命令行的双引号由 shell 处理，滤镜内部还另有转义层；复杂图优先放到受版本控制、经过审阅的 filtergraph 文件或实践脚本中。

## 6. 拼接前先分清三种同名机制

FFmpeg 文档中的 “concat” 至少指三层不同机制：

| 机制 | 接口层与输入 | 适用条件 | 是否重编码 | 关键边界 |
| --- | --- | --- | --- | --- |
| concat protocol | 协议层 URL；把多个资源当成连续字节流 | 格式本身支持物理字节拼接，且时间戳/边界已可用 | 本身不决定 | 不解析/统一各段 streams，不重建 MP4 等普通容器；`\|` 还要经过 shell quoting |
| concat demuxer | `ffconcat` manifest；把各文件 packet 虚拟串接 | streams 的 codec、time base 等结构一致 | 常与 stream copy 搭配 | demuxer 会调整 timestamps；duration 错误会制造 gap/artifact |
| concat filter | 多输入的 decoded audio/video frames | 需要统一尺寸、采样率、layout 或起始 PTS | 需要相应重编码 | 每段需从 timestamp 0 开始，对应 pads/streams 参数要兼容 |

concat protocol 的 URL 形状是：

```text
concat:part-01.example.ts|part-02.example.ts
```

它只是把资源按物理字节顺序读成一个资源；只有你已证明目标格式可安全这样连接时才适用。不要把两个普通 MP4 文件直接物理拼接后期待索引、header、streams 和 timestamps 自动修复，也不要从不可信文本拼接 protocol URL。

`-safe` **只属于 concat demuxer 的私有输入选项**，写在 `-f concat` 对应的 `-i` 前。它不是 concat protocol 或 concat filter 的选项，也不是全局安全沙箱；即使使用 `-safe 1`，仍要限制 manifest 来源、资源数量/大小/时长、协议与执行权限。

### 6.1 concat demuxer + stream copy

当各段拥有相同 stream 结构、codec、time base 等参数，且目标是避免重编码时，使用 concat demuxer。先创建一个只引用当前工作目录内受信文件的 `segments.example.ffconcat`：

```text
ffconcat version 1.0
file part-01.example.mkv
file part-02.example.mkv
```

第一行必须精确出现，不能有 BOM 或多余前导内容。示例文件名只含 portable 字符，并保持相对路径，才能在默认安全规则下使用：

```bash
ffmpeg -hide_banner -n \
  -f concat -safe 1 -i "segments.example.ffconcat" \
  -map 0:v:0 -map '0:a:0?' \
  -c copy \
  "joined-copy.example.mkv"
```

官方 concat demuxer 会调整各文件时间戳，让下一段接在上一段之后；错误的 duration 可能造成 artifacts/gaps。它要求文件具有相同 streams（包括 codec、time base 等），不是“任何媒体列表拼起来”。H.264/MP4 有有限的自动 bitstream conversion，不应被推广成普适兼容。

> [!danger] 不可信 manifest
> `safe=1` 默认拒绝协议 URL、绝对路径和不安全组件。不要为方便把网上抄来的命令改为 `-safe 0`：那会扩大可访问路径/协议范围。先验证每个条目属于受控根目录、没有符号链接逃逸、数量/大小/时长有限，并在低权限隔离环境中处理。完整实践见 [[计算机知识/80-实践/07-媒体编码与FFmpeg/04-批处理Manifest与不可信输入边界|批处理 Manifest 与不可信输入边界]]。

## 7. concat filter + 重编码

当输入必须先统一分辨率、采样率或时间起点时，让每段 decode/filter 后进入 concat filter：

```bash
# 假设每个输入恰有一条视频和一条音频，且音频布局兼容。
ffmpeg -hide_banner -n \
  -i "part-01.example.mp4" \
  -i "part-02.example.mp4" \
  -filter_complex \
'[0:v:0]scale=1280:720,setsar=1,setpts=PTS-STARTPTS[v0];
 [0:a:0]aresample=48000,asetpts=PTS-STARTPTS[a0];
 [1:v:0]scale=1280:720,setsar=1,setpts=PTS-STARTPTS[v1];
 [1:a:0]aresample=48000,asetpts=PTS-STARTPTS[a1];
 [v0][a0][v1][a1]concat=n=2:v=1:a=1[vout][aout]' \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -c:a aac \
  "joined-normalized.example.mp4"
```

官方 concat filter 要求每个 segment 从 timestamp 0 开始，所以这里显式 `setpts=PTS-STARTPTS` / `asetpts=PTS-STARTPTS`。对应 streams 的分辨率等参数必须一致；filter 可协商一部分 pixel/sample format，但不会自动解决所有尺寸、布局、色彩、HDR 与语义差异。不同帧率可产生 VFR 输出，必须配置并验证目标容器/播放端。高级时间与 pad 模型见下一课。

## 8. 字幕：软字幕与烧录是两条不同路径

### 软字幕：保留为独立 stream

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mkv" \
  -i "captions.example.srt" \
  -map 0:v:0 -map '0:a?' -map 1:s:0 \
  -c:v copy -c:a copy -c:s srt \
  -metadata:s:s:0 language=zho \
  "subtitled.example.mkv"
```

播放器可开关软字幕，视频无需重编码；但字幕 codec 与 container 必须兼容。转入 MP4 时常见文本字幕 encoder 是 `mov_text`：

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mp4" \
  -i "captions.example.srt" \
  -map 0:v:0 -map '0:a?' -map 1:s:0 \
  -c:v copy -c:a copy -c:s mov_text \
  "subtitled.example.mp4"
```

样式、字体、定位和复杂 ASS 特性在字幕 codec 转换中可能丢失；语言 tag 也只是声明。交付前在目标播放器人工检查文字、时间、换行、RTL/CJK 字体与安全区。

### 烧录：把文字渲染进视频像素

```bash
# 仅在 `ffmpeg -filters` 明确列出 subtitles 时才使用。
ffmpeg -hide_banner -n \
  -i "input.example.mp4" \
  -map 0:v:0 -map '0:a:0?' \
  -vf "subtitles=filename='captions.example.srt'" \
  -c:v libx264 -c:a copy \
  "burned-in.example.mkv"
```

`subtitles` filter 依赖 libass，烧录必然使视频进入 filter 并重编码。本机 9.0.1 当前 `ffmpeg -filters` **没有列出** `subtitles` / `ass`，所以这条烧录模板没有在本机构建中宣称可用；软字幕 mux 的 `srt` / `mov_text` encoder 与 libass filter 是不同能力。字幕文本和字体也是不可信输入，渲染前限制文件来源/大小并使用隔离环境。

## 9. 音频提取、转码与响度

### 不改编码地提取首条音频

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mkv" \
  -map 0:a:0 -vn -sn -dn \
  -c:a copy \
  "audio-copy.example.m4a"
```

若源音频 codec 不适合 M4A，mux 会失败；不要把换扩展名当转换。改为兼容容器，或显式转码：

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mkv" \
  -map 0:a:0 -vn -sn -dn \
  -c:a libopus -b:a 128k \
  "audio-transcoded.example.opus"
```

### 单遍响度处理

```bash
ffmpeg -hide_banner -n \
  -i "input.example.wav" \
  -map 0:a:0 \
  -af "loudnorm=I=-16:LRA=11:TP=-1.5" \
  -c:a pcm_s24le \
  "audio-loudnorm.example.wav"
```

这是单遍 `loudnorm` 处理示例，不应被描述为“必然精确命中所有目标”。可复现交付通常先做 measurement pass，保存 integrated loudness、true peak、LRA、threshold/offset 等测量，再把这些值传给 linear/second pass；还要检查是否发生采样率变化、true-peak 过冲、声道布局误读与听感劣化。对每条节目分别测量，不把一份测量值套到其他文件。

音频码率、延迟与主观质量不能由扩展名或目标响度替代，前置见本域音频课程与 [[计算机知识/60-数据编码与媒体系统/16-媒体质量评估PSNR-SSIM-VMAF与听感边界|媒体质量评估与听感边界]]。

## 10. Metadata、附件与权利

- `-map 0` 可能复制更多 streams；显式 map 是最小披露策略。
- 默认 metadata 映射规则随输入/输出类型而异；需要去除全局自动 metadata 映射时可研究 `-map_metadata -1`，但先保存原始证据，并理解章节、stream tags、封面和附件是不同对象。
- 删除 metadata 不会证明媒体匿名：画面、声音、字幕、编码指纹和文件时间仍可能泄露信息。
- 不得移除依法/依约必须保留的署名、权利或来源信息；本页不是法律意见。
- 对外分发前核对内容授权、字体许可、字幕来源、codec/第三方库许可和目标地区义务。

## 11. 常见失败的最短路径

| 现象 | 先检查 | 常见修正方向 |
| --- | --- | --- |
| `Could not find tag for codec` | 输出 container 与该 stream codec | 换兼容容器，或只转码不兼容 stream |
| 拼接后间隙/重叠 | 每段 duration、PTS/DTS、stream 同构 | probe packets；改 duration 或走 filter normalize |
| copy 裁剪起点提前 | RAP/keyframe 与 input seek 行为 | 接受误差或转码目标段 |
| 字幕不见 | stream map、codec、disposition、播放器能力 | 显式 map；换受支持字幕 codec；目标端实测 |
| 烧录报 `No such filter` | `ffmpeg -filters`、libass 构建 | 安装/选择经批准的含 libass 构建；不要误判为字幕文件损坏 |
| 音频变短/不同步 | sample rate/layout、PTS、滤镜 latency | 比较 packet/frame timestamps 与输出时长 |
| 输出已存在 | `-n` 正常保护 | 选新文件名；核对后才明确授权覆盖 |

## 练习：同一素材做三种交付

使用实践区生成的合成素材完成：

1. 只换容器并 copy 首条视频/音频；
2. 从现有 3–4 秒合成素材中精确选取 1 秒并缩放，显式转码视频；选做扩展是自行生成或取得授权的至少 12 秒素材后再截取 10 秒；
3. 对两段素材分别判断 concat protocol、concat demuxer 与 concat filter 是否适用；用同构素材走 demuxer，再故意改变第二段分辨率，解释为什么应改走 filter；
4. 分别制作一份软字幕和一份可行时的烧录字幕，比较 stream 列表；
5. 对每个输出保存 ffprobe JSON、退出码、时长与人工检查结果。

实践入口：[[计算机知识/80-实践/07-媒体编码与FFmpeg/02-转封装转码裁剪与客观对比|转封装、转码、裁剪与客观对比]]。

### 成功标准

- 原始输入没有被覆盖或修改；
- 每个输出都能从 `-map` 解释 streams 来源；
- 能从日志证明哪些 streams copy、哪些 encode；
- 能区分 protocol 的物理字节拼接、demuxer 的 packet 虚拟串接和 filter 的 decoded-frame 串接，并让方法与输入条件匹配；
- 能说明 `-safe` 只约束 concat demuxer 的 manifest 路径/指令，不属于 protocol/filter，也不替代资源与权限隔离；
- 字幕类型、音轨、时长和起点均经 ffprobe 与目标播放器检查；
- 1 秒版的 ffprobe 时长接近 1 秒，容差由帧率、音频帧与容器 time base 决定并在报告中记录，不要无前提硬断言字节级正好 1.000000 秒；
- 报告明确记录本机能力、未验证平台、质量/许可边界与恢复方式（删除新输出即可，原件仍在）。

## 官方来源

- [FFmpeg CLI Documentation：Streamcopy、Transcoding、Options、`-ss` 与 `-map`](https://ffmpeg.org/ffmpeg.html)
- [FFmpeg Formats Documentation：concat demuxer](https://ffmpeg.org/ffmpeg-formats.html#concat)
- [FFmpeg Protocols Documentation：concat physical protocol](https://ffmpeg.org/ffmpeg-protocols.html#concat)
- [FFmpeg Filters Documentation：concat filter](https://ffmpeg.org/ffmpeg-filters.html#concat)
- [FFmpeg Filters Documentation：subtitles filter](https://ffmpeg.org/ffmpeg-filters.html#subtitles-1)
- [FFmpeg Filters Documentation：loudnorm](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)

---

**上一站**：[[计算机知识/60-数据编码与媒体系统/13-ffprobe媒体诊断与可复现检查|ffprobe 媒体诊断]] · **下一站**：[[计算机知识/60-数据编码与媒体系统/15-FFmpeg滤镜图时间基映射与硬件加速|FFmpeg 滤镜图、时间基、映射与硬件加速]] · **安全连接**：[[计算机知识/60-数据编码与媒体系统/17-媒体工程安全许可隐私与可复现性|媒体工程安全、许可、隐私与可复现性]] · **返回**：[[计算机知识/60-数据编码与媒体系统/00-数据编码与媒体系统-MOC|数据编码与媒体系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/09-计算机网络-课程地图|计算机网络 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|网络：UDP、TCP、可靠传输与应用分帧]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
