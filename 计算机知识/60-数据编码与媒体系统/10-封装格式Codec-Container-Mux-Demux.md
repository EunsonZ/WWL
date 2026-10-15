---
type: lesson
domain: computer-science
stage: 2
status: ready
difficulty: 基础到进阶
estimated_minutes: 75
verified: 2026-09-03
topics:
  - codec
  - container
  - mux-demux
  - elementary-stream
  - packet-frame
  - mp4
  - matroska
  - webm
  - mpeg-ts
tags:
  - computer-science/media
  - computer-science/containers
  - computer-science/io
---

# 封装格式：Codec、Container、Mux 与 Demux

`.mp4` 不是 H.264，`.mkv` 也不是“万能编码”。codec 规定 coded/encoded representation 与 decoded samples 之间的语法和处理；它可以有损、无损，也可以是不压缩表示。container 负责把一条或多条轨道、时间戳、初始化信息、索引和元数据组织成文件或片段。播放器必须同时支持容器、其中的 codec、所用 profile/level、像素/音频格式和加密方式。

> [!info] 事实核验边界
> 本页按 ISO Base Media File Format、Matroska/WebM、MPEG-TS 与 FFmpeg 官方资料核对至 **2026-09-03**。扩展名、品牌、codec 映射和播放器支持会变化；具体交付必须检查实际文件结构和目标平台，不以文件名猜格式。

## 本课目标

学完后，你应能：

1. 用职责边界解释 codec、container、mux、demux 与 remux；
2. 区分 elementary stream、track/stream、packet/sample 与 decoded frame；
3. 说明 MP4、Matroska/MKV、WebM 和 MPEG-TS 的结构定位与典型取舍；
4. 判断一次“换后缀”或“换容器不重编码”为什么可能成功或失败；
5. 用只读探测建立从文件字节到解码帧的证据链。

## 1. 同一播放链中的不同职责

```text
文件 / 网络字节
  ↓ demuxer 解析 container
video packet ──→ video decoder ──→ video frames
audio packet ──→ audio decoder ──→ audio frames/samples
subtitle packet ────────────────→ subtitle events
  ↓ 各轨道 PTS 进入时钟与渲染调度
同步播放
```

反方向：

```text
raw video frames → video encoder → encoded video packets ┐
raw audio samples → audio encoder → encoded audio packets ├→ muxer → container
subtitle events ──────────────────────────────────────────┘
```

- **codec**：coded/encoded representation 与 decoded samples 之间的语法和处理，例如某种视频/音频编码格式；可能有损、无损或不压缩。
- **container**：多轨结构、时间线、元数据、索引及 codec 初始化数据的组织格式。
- **mux（multiplex）**：把已经编码的各轨 packet 按容器规则交织写入。
- **demux**：读取容器，分离轨道并恢复 packet、时间戳和初始化信息。
- **remux**：通常不重新编码 payload，只把兼容的编码数据重新封装；时间戳和 bitstream framing 仍可能需要转换。
- **transcode**：至少一个媒体流经过解码/重新编码或等价编码转换，质量、速度和数据都有可能改变。

## 2. stream、packet、sample、frame 不能互换

### Elementary stream

只包含一种编码媒体语法的连续数据常称 elementary stream。它可能没有通用容器的多轨索引、语言、章节或完整时间轴。裸码流能被解码，不代表适合 seek 或音视频同步。

### Track / stream

容器里的 track/stream 是一条有类型和时间轴的媒体轨道，例如视频、音频、字幕或数据。FFmpeg 中 `AVStream` 代表 demux/mux 层的流信息，不是 C++ I/O stream，也不是“正在直播”的同义词。

### Packet / sample

demuxer 输出的 packet 携带一段 **coded payload**，并附带 stream index、PTS/DTS、duration、flags 等元数据；payload 未必经过压缩。不同 API 和容器可能称其 packet 或 sample；边界不保证等于一帧：

- 一个 packet 可能含一个或多个编码单元；
- 一个编码帧可能跨多个传输包；
- 音频 packet 常对应一组采样；
- bitstream parser 可能还要把 packet 拆/并成 decoder 可接收的访问单元。

FFmpeg 的 `AVPacket` 不是 IP/UDP/RTP packet。网络 packet 讲 MTU、序列号、丢包；容器/codec packet 讲媒体 payload 和时间戳。它们可以一对多或多对一。

### Decoded frame

decoder 输出的 frame 是可供过滤/渲染的解码数据：视频通常是多个像素平面，音频 frame 是一段 PCM 样本。由于重排与缓存，“送入一个 packet，立刻输出一个 frame”不是可靠假设；API 往往允许一次输入后输出 0、1 或多个 frame，并要求在结尾 drain。

## 3. Container 保存什么

一个通用容器可能保存：

- 文件类型/版本与 feature brand；
- 多条 track 的类型、语言、默认选择和 codec 标识；
- codec 初始化数据或 extradata；
- 每个 sample/packet 的大小、位置、PTS/DTS、duration 和随机访问标志；
- 章节、字幕、标签、封面或附件；
- seek 索引；
- 分片、加密与流媒体所需的额外结构。

容器元数据可以重复 codec bitstream 中的部分信息。二者冲突时，不同工具的优先级可能不同。必须记录“字段来自哪一层”，不能把 `ffprobe` 的一个汇总字段当作没有来源差异。

## 4. MP4：ISO BMFF 家族中的一种具体文件格式

ISO Base Media File Format（ISOBMFF）用带类型与长度的 box 组织数据，是 MP4、某些 fragmented media 和其他派生格式的基础。典型 MP4 可粗略理解为：

```text
ftyp  文件类型/兼容品牌
moov  轨道、时间表、sample 表、索引等 movie metadata
mdat  实际媒体 payload
```

这只是示意，真实文件的 box 顺序、层级和分片结构更丰富。

### `moov` 与渐进读取

非分片 MP4 的 sample 表常在 `moov`。若 `moov` 位于大文件末尾，HTTP 客户端可能需要额外 range request 或等待末尾元数据，才知道媒体数据如何定位。所谓 “fast start” 通常是把所需 movie metadata 安排到前部并修正偏移，不是改变 codec 质量。

### fragmented MP4

fMP4 将媒体分为初始化信息与 movie fragments，常作为分段传输的媒体格式。它仍是容器结构，不等于某个流媒体协议，也不限定只能装一种视频 codec。

### MP4 的定位

- 强项：标准化时间表与 sample 索引、广泛的文件/设备/分段生态；
- 约束：某个 codec 能否放入 MP4 需要对应 sample entry/mapping，能封装也不等于目标播放器实现支持；
- 故障点：`moov`/索引缺失、brand 或 sample entry 不兼容、时间表错误、非单调 DTS、初始化信息不匹配。

## 5. Matroska/MKV：EBML 上的灵活多轨容器

Matroska 使用 EBML 元素组织 `Segment`。关键结构包括：

- `Info`：Segment 的时间尺度与整体信息；
- `Tracks`：音视频字幕等 track 定义和 codec mapping；
- `Cluster`：按时间组织的 `Block`/`SimpleBlock`，承载 frame 数据；
- `Cues`：时间到 track/cluster 位置的索引，用于优化 seek；
- Chapters、Tags、Attachments 等可选结构。

Matroska 官方规范指出，非直播文件通常应有 Cues；没有 Cues 不必然“完全不能 seek”，但 reader 可能需要扫描寻找目标，速度和可靠性下降。

`.mkv` 通常指 Matroska 文件扩展名。它可映射多种 codec，但“容器允许”不等于每个电视、浏览器或硬件播放器支持该组合。

## 6. WebM：基于 Matroska 的受约束媒体容器

WebM 不是 Matroska 的另一个后缀而已。它使用 Matroska/EBML 结构并施加更窄的媒体、命名和流式使用约束，以提高 Web 互操作性。官方 WebM Container Guidelines 还定义 muxer/demuxer、HTML5 type 参数和 codec 映射等要求。

因此：

- 一个 WebM 文件可被 Matroska parser 理解，不表示任意 MKV 都是有效 WebM；
- WebM 与 VP8/VP9、AV1、Vorbis/Opus 等常见组合的精确允许范围和浏览器支持应查当前官方映射与目标平台；
- 把任意 MKV 改名为 `.webm` 不会删除其中不符合 WebM 约束的 track 或 codec。

## 7. MPEG-TS：为连续传输与快速恢复设计的 transport stream

MPEG-2 Transport Stream 将内容切成固定 188-byte TS packets。不同 PID 标识不同 packetized stream 或表；PAT/PMT 等表帮助接收端发现 program 与各 elementary stream；PCR 等时钟信息用于恢复系统时基。

它与 FFmpeg packet、RTP packet 仍不是同一个层级：一个编码访问单元可以被 PES 和多个 TS packet 承载，而 TS 又可装进 UDP/RTP 或文件。

### MPEG-TS 的定位

- 适合：连续输入、中途加入、广播/传输、周期重复关键信息和在局部损坏后继续解析；
- 代价：固定小包和重复表带来开销，文件级富元数据/精细索引不如专门文件容器自然；
- seek：本地 `.ts` 可由播放器扫描或外建索引，但不能假设容器天然有类似 MP4 sample table 或 Matroska Cues 的完整文件索引；
- 常见故障：continuity counter 异常、PAT/PMT/PCR 问题、时间戳不连续、节目/轨道选择错误。

## 8. 四种容器的学习对照

| 格式 | 结构定位 | seek/索引思路 | 常见使用方向 | 不能由格式名推出 |
| --- | --- | --- | --- | --- |
| MP4 | ISO BMFF 派生、box、track/sample 表或 fragment | `moov` sample 表、fragment/index | 本地文件、Web 渐进读取、fMP4 分段 | codec、是否 fast-start、是否加密 |
| Matroska/MKV | EBML Segment、Tracks、Clusters、Cues | Cues 定位 Cluster/Block；缺失时可能扫描 | 灵活多轨、字幕/附件、本地文件 | 目标设备一定支持全部 track |
| WebM | Matroska 的受约束 Web 媒体子集 | 基于 Cluster/Cues 与 WebM 约束 | HTML5/Web 媒体生态 | 任意 MKV 改后缀即可兼容 |
| MPEG-TS | 188-byte TS packet、PID、program/table、PES | 流式发现；文件 seek 常依赖扫描/外部索引 | 广播、连续传输、HLS TS segment 等 | 有精细文件索引、低开销、固定 codec |

选容器时先从目标播放器、协议、codec/字幕、随机访问、编辑、错误恢复和元数据需求倒推，而不是按“哪个更先进”排序。

## 9. Remux 为什么可能无需重编码，也可能失败

若输入 codec 和 metadata 可由输出容器合法承载，demuxer 可以读出 coded packet，muxer 重新写时间戳/索引和 framing：

```text
input container → demux → encoded packets → 可能的 bitstream framing 转换 → mux → output container
```

payload 通常没有经历像素域解码/有损重编码，所以速度快、不会新增量化损失。但以下情况会失败或需要额外处理：

- 输出容器没有该 codec/字幕的标准 mapping；
- codec 初始化数据布局不同；
- 输入时间戳缺失、非单调、超出目标 time scale 或存在未标记 discontinuity；
- attachment、chapter、font、rotation、HDR 或 language metadata 无法等价映射；
- 目标协议要求每段独立解码，而 GOP 跨边界引用；
- bitstream 使用 Annex B、length-prefixed NAL 或其他 framing，需要无损 bitstream filter 转换。

“stream copy 成功退出”只证明工具写出了它接受的文件，不证明所有目标播放器、seek、色彩、字幕和同步均通过。

## 10. 只读探测：分开看 format、stream、packet、frame

下面命令展示证据层次，不修改输入文件：

```text
# 容器及轨道：格式、codec、time base、时长、metadata
ffprobe -v error -show_format -show_streams -of json INPUT

# coded packet：payload 所属 stream、PTS/DTS、duration、大小与 flags
ffprobe -v error -show_packets -show_entries \
  packet=stream_index,pts_time,dts_time,duration_time,size,flags \
  -read_intervals "%+2" -of json INPUT

# 解码 frame：画面类型、呈现时间、像素格式等
ffprobe -v error -select_streams v:0 -show_frames -show_entries \
  frame=best_effort_timestamp_time,pkt_dts_time,pict_type,key_frame,width,height,pix_fmt \
  -read_intervals "%+2" -of json INPUT
```

不要把 `-show_packets` 输出条数当作帧数；需要理解 parser、decoder delay、B-frame reorder 与音频 frame 粒度。`ffprobe` 能读取的字段也取决于输入可探测程度和当前构建。

## 11. 失败诊断矩阵

| 现象 | 优先检查的层 | 常见误判 |
| --- | --- | --- |
| “Unsupported codec” | container 被识别了吗？track codec/profile/level 是什么？解码器是否存在？ | 把 `.mp4` 当作 codec |
| 改后缀后仍不能播 | magic/box/EBML 结构、实际 format、codec mapping | 认为扩展名会转换内容 |
| remux 后没声音/字幕 | track mapping、default/disposition、目标容器支持、extradata | 认为 stream copy 自动选择全部轨道 |
| 本地能播，网页不能播 | WebM/MP4 约束、MIME/codecs string、浏览器解码、CORS/range | 认为“VLC 能播”证明 Web 兼容 |
| seek 很慢 | `moov`/sample table、Cues、RAP 密度、文件是否可随机访问 | 只换 codec，不检查索引 |
| 前几秒花屏或无声 | 初始化信息、起始 RAP、priming/pre-roll、负时间戳 | 把 packet 边界等同帧边界 |

## 练习

1. 画出“MP4 中的 H.264 视频 + AAC 音频”从文件到屏幕/扬声器的组件图，至少标出两个 decoder。
2. 为什么把 `movie.mkv` 改名为 `movie.webm` 不构成转换？列出三项仍需检查的约束。
3. 某 remux 前后 codec name 相同，但文件时长不同。提出至少四个时间线层假设。
4. 分别解释 FFmpeg `AVPacket`、MPEG-TS packet 与 RTP packet；给出它们可能一对多的例子。
5. 为“seek 到 10 秒需要等待 5 秒”设计证据链：容器索引、最近 RAP、GOP 依赖和 I/O 可随机访问性各收集什么？

## 成功标准

- [ ] 能说明 codec 管 coded representation 与 decoded samples 间的语法/处理，container 管轨道/时间戳/索引/元数据；不把 codec 或 packet 自动等同于压缩。
- [ ] 不用文件扩展名推断唯一 codec，也不把 packet 数直接当帧数。
- [ ] 能解释 remux 不经像素域重编码，却仍可能转换 framing 与时间戳。
- [ ] 能给出 MP4、MKV、WebM、MPEG-TS 各自结构定位和一项关键取舍。
- [ ] 能用 format → stream → packet → frame 四层输出定位失败。

## 参考资料（verified 2026-09-03）

- [ISO/IEC 14496-12:2026 在线浏览入口](https://www.iso.org/obp/ui#iso:std:iso-iec:14496:-12:ed-8:v1:en)：ISOBMFF 的 box、track、sample、time structure 与随机访问定义。
- [Matroska Data Layout](https://www.matroska.org/technical/diagram.html)、[Matroska Cues](https://www.matroska.org/technical/cues.html) 与 [Codec Mappings](https://www.matroska.org/technical/codec_specs.html)：Segment、Cluster、Block、Cues 与 codec ID 的规范资料。
- [WebM Container Guidelines](https://www.webmproject.org/docs/container/)：WebM 相对 Matroska 的约束、mux/demux 指南和 Web 媒体映射。
- [FFmpeg formats 文档](https://ffmpeg.org/ffmpeg-formats.html)：muxer、demuxer、raw format、MOV/MP4、Matroska/WebM、MPEG-TS 与 segmenter 的当前实现文档。
- [FFmpeg `ffprobe` 文档](https://ffmpeg.org/ffprobe.html)：format、stream、packet 与 frame 的分层探测接口。

## 导航

- 上一课：[[计算机知识/60-数据编码与媒体系统/09-视频编码预测变换量化熵编码与GOP|视频编码：预测、变换、量化、熵编码与 GOP]]
- 下一课：[[计算机知识/60-数据编码与媒体系统/11-流媒体时间戳同步Seek与协议边界|流媒体：时间戳、同步、Seek 与协议边界]]
- 返回：[[计算机知识/60-数据编码与媒体系统/00-数据编码与媒体系统-MOC|数据编码与媒体系统 MOC]]
- 底层表示：[[计算机知识/30-计算机系统/01-数据表示字节序与对齐|数据表示、字节序与对齐]]
- 系统 I/O：[[计算机知识/30-计算机系统/10-IO设备总线DMA与中断|I/O、设备、总线、DMA 与中断]]
- I/O 性能：[[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/60-数据编码与媒体系统/00-数据编码与媒体系统-MOC|数据编码与媒体系统 MOC]]。网络传输相关路线：[[计算机知识/00-开始/课程地图/09-计算机网络-课程地图|计算机网络 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|网络：UDP、TCP、可靠传输与应用分帧]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
