---
type: lesson
domain: computer-science
stage: 6
status: ready
difficulty: 中级
estimated_minutes: 70
verified: 2026-09-03
local_toolchain: ffprobe 9.0.1 (Homebrew, macOS arm64)
topics:
  - ffprobe
  - JSON
  - media diagnostics
  - packets
  - frames
  - reproducibility
tags:
  - computer-science/media
  - computer-science/ffmpeg
  - computer-science/diagnostics
---

# ffprobe 媒体诊断与可复现检查

`ffprobe` 适合回答“容器宣称有什么”“某条 stream 的参数是什么”“packet/frame 时间戳呈现出什么模式”。它不是播放器，也不是完整质量验收器。诊断的核心不是把全部输出贴出来，而是先提出问题，再选择足够小的 section 和 field。

> [!info] 核验边界
> 2026-09-03 本机实查 `/opt/homebrew/bin/ffprobe -version` 为 9.0.1，和本机 `ffmpeg` 共用 FFmpeg 9.0.1 的 Homebrew arm64 构建与库版本。下面的 section/writer 模型来自 FFmpeg 官方 `ffprobe` 文档；字段是否存在、类型和语义仍取决于版本、demuxer、codec 与输入。Windows、Linux、其他构建和真实业务媒体未在本页验证。

## 本课目标

学完后，你应该能够：

1. 用 JSON writer 提取 format、stream、packet、frame/subtitle 与 error section；
2. 区分容器级、stream 级、packet 级和 decoded frame 级证据；
3. 解释 `r_frame_rate`、`avg_frame_rate`、`time_base`、PTS/DTS 为什么不能互相替代；
4. 构造一个包含输入 hash、工具版本、命令、退出码和有限输出的复现记录；
5. 明确 ffprobe 不能证明完整解码、播放兼容、主观质量和音画同步体验。

## 1. 一条最小、机器可读的起点

```bash
# 路径是合成占位名；命令只读输入，并把 JSON 写到标准输出。
ffprobe -v error \
  -show_format -show_streams -show_chapters \
  -of json \
  "input.example.mkv"
```

- `-v error` 抑制普通 banner/log，让标准输出更适合交给 JSON parser；
- `-show_format` 输出容器/输入级 `FORMAT` section；
- `-show_streams` 为每条媒体 stream 输出 `STREAM` section；
- `-show_chapters` 只在输入确有 chapter 时产生内容；
- `-of json` 选择 JSON writer，不是让源媒体变成 JSON。

不要把诊断输出和错误日志混成一个不可解析文件。自动化时分别保存 stdout、stderr 和退出码；即使 stdout 是合法 JSON，非零退出码也不能忽略。

## 2. Section 是证据层，不是“详细程度”按钮

```text
FORMAT    container/input-level declaration
  └─ STREAM   one logical video/audio/subtitle/data stream
       ├─ PACKET   compressed unit from demuxer
       └─ FRAME | SUBTITLE   decoded frame or subtitle record
ERROR     probe failure information when requested
```

| Section | 常见问题 | 成本与边界 |
| --- | --- | --- |
| `FORMAT` | 格式名、总时长、大小、整体码率、全局 tags | 时长可能来自 header、索引或估算，不一定等于逐 packet 真值 |
| `STREAM` | codec、分辨率、采样率、channel layout、time base、语言/disposition | 多为声明与探测结果，不证明整条流可解码 |
| `PACKET` | PTS/DTS、duration、size、key flag、交错顺序 | 输出可极大；仍是压缩层，不等于显示帧 |
| `FRAME` | decoded frame 的 PTS、format、picture type、采样数 | 需要解码，慢且可能暴露内容相关 metadata |
| `SUBTITLE` | decoded subtitle record 与显示时序 | `-show_frames` 也可能产生此 section；不是普通音视频 `FRAME` |
| `ERROR` | 打开/探测失败的结构化线索 | 只描述本次失败，不自动给根因或修复方案 |

`-show_packets` 和 `-show_frames` 对长媒体可产生海量输出，不应作为默认“体检”。先用 `-select_streams` 与 `-read_intervals` 限定范围，再决定是否扫描全文件。

## 3. 精确选择 fields

```bash
ffprobe -v error \
  -show_entries \
'format=format_name,start_time,duration,size,bit_rate:stream=index,codec_type,codec_name,profile,width,height,pix_fmt,color_range,color_space,color_transfer,color_primaries,sample_rate,channels,channel_layout,time_base,r_frame_rate,avg_frame_rate,duration,nb_frames:stream_tags=language,title' \
  -of json \
  "input.example.mkv"
```

外层使用单引号保护 `:`、`,` 等参数字符，输入路径单独双引号引用。不同 shell 的引用规则不同；PowerShell/CMD 不应照搬 POSIX shell 的单引号语义。

这个查询不会保证每个 key 都出现：

- 视频通常没有 `sample_rate`，音频通常没有 `width`；
- container/codec 未提供时，`duration`、`nb_frames`、color metadata 或 channel layout 可以缺失；
- 某些值在 JSON 中仍以字符串表示，例如 `"48000"`、`"30000/1001"` 或 `"N/A"`；
- `tags.language` 是 metadata 声明，可能拼写错误或与实际内容不符；
- 不应把“字段缺失”强行转换为数值 0，0 与 unknown 不是同一事实。

### 一个只看首条视频的查询

```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_entries \
'stream=index,codec_name,profile,width,height,pix_fmt,time_base,r_frame_rate,avg_frame_rate,duration,nb_frames:stream_tags=language,title' \
  -of json=compact=1 \
  "input.example.mkv"
```

`-select_streams v:0` 只影响与 stream 相关的查询；它不是 FFmpeg 输出命令中的 `-map`。`-of json=compact=1` 只改变排版，不改变取证层级。

## 4. 怎样读 format 与 stream

### 容器层

| 字段 | 可支持的结论 | 不能单独支持的结论 |
| --- | --- | --- |
| `format_name` | demuxer 识别为哪些格式名/别名 | 扩展名、codec 或所有播放器兼容性 |
| `start_time` | demuxer 报告的输入起始时间 | 第一帧一定恰好在该时间显示 |
| `duration` | demuxer 报告/估算的整体时长 | 所有 streams 都同长、尾部无损坏 |
| `size` | ffprobe 所见输入大小（适用时） | 有效媒体载荷大小或内容 hash |
| `bit_rate` | 可用时的整体平均码率线索 | 瞬时峰值、质量或编码复杂度 |
| `tags` | 容器声明的 metadata | 真实作者、版权归属或内容语言 |

### Stream 层

- `index` 是该输入内的 stream index，可供 `-map 0:<index>` 使用；换一个输入或重新复用后 index 可能改变。
- `codec_name` 说明探测到的 codec，不说明本机构建必有可成功处理全部数据的 decoder/encoder。
- `profile`、`level`、`pix_fmt`、color metadata 要一起看；缺少 color 字段不代表“默认一定正确”。
- 音频至少联合检查 `sample_rate`、`sample_fmt`（若选择）、`channels` 与 `channel_layout`。声道数相同不保证布局相同。
- `disposition.default` 是播放选择提示，不是“质量最好”或“语言正确”的证明。

视频声明应与 [[计算机知识/60-数据编码与媒体系统/08-数字视频帧率扫描色彩采样与时间基|数字视频：帧率、扫描、色彩采样与时间基]]、[[计算机知识/60-数据编码与媒体系统/09-视频编码预测变换量化熵编码与GOP|视频编码：预测、变换、量化、熵编码与 GOP]] 中的信号模型一起解释；容器/stream 层次见 [[计算机知识/60-数据编码与媒体系统/10-封装格式Codec-Container-Mux-Demux|封装格式：Codec、Container、Mux 与 Demux]]。

## 5. 帧率字段与 time base 不可互换

假设 `time_base="1/90000"`，某 packet 的 `pts=180000`，其呈现时间可换算为：

```text
180000 ticks × (1 / 90000 second per tick) = 2 seconds
```

`time_base` 是 timestamp tick 的单位，不是 FPS。`r_frame_rate` 是 stream 的“real base frame rate”线索，`avg_frame_rate` 是平均帧率；它们是有理数表示，不能在所有 demuxer/内容上当作采集帧率、恒定输出帧率或逐帧间隔。VFR 内容必须检查实际 timestamps/durations，而不是只看一个 `30/1`。

基础 time base/PTS 模型见 [[计算机知识/60-数据编码与媒体系统/08-数字视频帧率扫描色彩采样与时间基|数字视频：帧率、扫描、色彩采样与时间基]]；跨流同步、seek 与 discontinuity 见 [[计算机知识/60-数据编码与媒体系统/11-流媒体时间戳同步Seek与协议边界|流媒体：时间戳、同步、Seek 与协议边界]]。

## 6. 有限 packet 检查

```bash
# 从约 10 秒处尝试读取 2 秒区间，只显示第一条视频的关键时间字段。
ffprobe -v error \
  -read_intervals '10%+2' \
  -select_streams v:0 \
  -show_packets \
  -show_entries 'packet=stream_index,pts_time,dts_time,duration_time,size,flags' \
  -of json \
  "input.example.mkv"
```

`10%+2` 表示从 10 秒附近 seek，并在读取区间达到约 2 秒后结束。官方文档特别提醒：seek 通常不精确，实际起点取决于可 seek 点；相对结束是从实际 seek 到的位置计算。因此该命令适合看局部模式，不是精确裁剪器。

从输出可检查：

- 在单一 stream 的 demux/decode 顺序中，DTS 是否缺失、跳变或违反预期 decode 顺序；
- DTS 与 PTS 是否因 B-frame 等编码重排而不同；
- `flags` 中何处出现关键 packet 标记；
- duration 是否稳定或呈现 VFR；
- packet size 是否剧烈变化。

`-show_packets` 按 demuxer 读出的 packet 顺序报告；有重排的视频中，这个顺序不是显示顺序，**不要求 packet PTS 单调**。若要检查呈现顺序，应再解码并观察 `FRAME` 的 PTS；即使 DTS 看似回退，也要先排除 seek 起点、discontinuity、timestamp wrap、缺失时间戳与 demuxer 修正，再判断损坏。不要仅凭前 2 秒宣布整条文件 timeline、GOP 或内容完整。

## 7. `-show_frames` 的 FRAME / SUBTITLE、计数与成本

```bash
# 解码一个有限区间，只观察第一条视频的 frame 级字段。
ffprobe -v error \
  -read_intervals '0%+1' \
  -select_streams v:0 \
  -show_frames \
  -show_entries 'frame=media_type,pts_time,duration_time,pict_type,key_frame,width,height,pix_fmt:frame_side_data=' \
  -of json \
  "input.example.mkv"
```

`FRAME` section 比 packet 更接近 decoder 输出，却仍不证明播放器的渲染、色彩管理、音频设备或同步策略。`-show_entries` 中的 `frame_side_data=` 带有 `=` 和空字段列表：按官方语法，它选择嵌套 section，但不输出该 section 的本地字段。本机 FFmpeg 9.0.1 对一帧含 H.264 user-data side data 的合成样本实测输出为 `frames[].side_data_list=[{}]`；改为 `frame_side_data=side_data_type` 才在该样本中出现类型名称。这只证明本次 JSON writer 的嵌套 shape，不能承诺其他版本、writer、codec 一定使用相同 key、数组或字段；解析器必须容忍 `side_data_list` 缺失、为空或含多个对象，也不能把空对象解释成“没有 side data”。

对字幕 stream，`-show_frames` 产生的顶层记录可以是 `SUBTITLE` 而不是 `FRAME`；选择器与 JSON shape 仍须在目标版本和输入上实测。对整文件使用 `-count_frames` / `-count_packets` 会强制读取大量数据：

```bash
ffprobe -v error \
  -select_streams v:0 \
  -count_frames -count_packets \
  -show_entries 'stream=nb_read_frames,nb_read_packets' \
  -of json \
  "input.example.mkv"
```

只在你拥有输入、接受完整扫描的 I/O/CPU 成本且已限定资源预算时运行。网络 URL、管道和无限 live stream 还需要超时与协议白名单；本课程示例默认本地普通文件。

## 8. Probe 成功到底证明了什么

分层写结论：

| 观察 | 可以说 | 不可以说 |
| --- | --- | --- |
| `-show_format/-show_streams` 成功 | header/探测足以识别格式与 streams | 全文件无损坏、所有 frame 可解码 |
| 局部 packet JSON 正常 | 被读取区间出现这些 timestamps/flags | 全片 timeline 正确 |
| 局部 frame JSON 正常 | 指定 decoder 在该区间产出 frames | 每个平台播放器兼容、色彩/音质正确 |
| 全文件 decode 无错误 | 该构建按本次映射走完 decode path | 主观质量、A/V lip-sync、硬件路径或另一版本兼容 |
| 输出 hash 相同 | 输出字节相同 | 两个不同字节输出感知质量一定不同 |

若需要单独检查音视频能否走完全文件 decode，可把输出丢到 null muxer：

```bash
# 不写媒体文件，但会完整读取并解码所选音视频，可能很耗时。
ffmpeg -hide_banner -v error -xerror \
  -i "input.example.mkv" \
  -map '0:v?' -map '0:a?' \
  -f null -
```

该命令不覆盖文件；它仍会消耗 CPU/GPU、磁盘读带宽并可能读取敏感内容。成功也只证明**这一本机构建、本次选择与本次输入**的 decode/null-output 路径，不证明显示或听感。

## 9. 可复现证据包

一次可复查的媒体诊断至少记录：

1. 输入的可公开标识与字节 hash；不要把私人文件名、路径或内容上传到公开日志；
2. `ffprobe -version` 的完整首段，包括 configuration 与库版本；
3. 完整命令，含引用、stream 选择、section/field、区间；
4. stdout JSON、stderr 和进程退出码分开保存；
5. 操作系统/架构、文件来源、检查日期；
6. 明确是 header probe、局部 packet、局部 frame 还是全文件 decode；
7. 任何资源限制、超时、硬件路径与未验证部分。

macOS 可只读计算文件 hash：

```bash
shasum -a 256 "input.example.mkv"
```

GNU/Linux 常用 `sha256sum`，Windows PowerShell 可用 `Get-FileHash`；先用本机帮助确认。`ffprobe -show_data_hash sha256` 结合 packet/stream section 计算的是 payload 或 extradata 的 hash，不等于整个输入文件 hash，不能互换。

### 隐私与不可信 metadata

- tags、chapter title、文件名、encoder string、GPS/设备信息可能含私人数据；
- JSON 字符串仍是不可信输入，展示到 HTML/终端/数据库时要转义并限制大小；
- `-show_data` 会输出 packet payload 或 codec extradata 的十六进制/ASCII dump，通常没有必要，可能让报告巨大并暴露内容；
- 不要为了“可复现”把原始私人媒体提交到 Git；使用合成素材和经过授权的小样本。

相关边界见 [[计算机知识/80-实践/07-媒体编码与FFmpeg/04-批处理Manifest与不可信输入边界|批处理 Manifest 与不可信输入边界]]。

## 10. 诊断决策表

| 问题 | 最小工具/section | 下一步 |
| --- | --- | --- |
| 容器里有哪些 streams？ | `-show_format -show_streams` | 明确 index 后再 `-map` |
| 为什么自动选错语言？ | stream tags + disposition | 不信任标签内容，人工确认后显式 map |
| VFR 还是 CFR？ | avg/r rate 作为线索 + 有代表性的 packet/frame timestamps | 检查全片分布与源生成规则 |
| seek 后为何不是精确帧？ | key packet、PTS/DTS、time base | 区分 input seek、output seek、copy 与 transcode |
| 文件是否尾部损坏？ | 全文件 decode / packet scan | 保存退出码与首个错误位置，不等同播放器 QA |
| 为什么两次输出不同？ | 输入 hash、完整版本/配置、命令、encoder 日志 | 固定线程/metadata/时间来源后再比较 |

## 练习：设计三层检查

使用实践区的合成媒体，不用私人素材：

1. 输出 format + streams 的精简 JSON，并写出每个字段属于哪一层；
2. 选择第一条视频的 1 秒 packet 区间，记录 demux 顺序中的 DTS、PTS/DTS 差异与 key flag，不要求 packet PTS 单调；
3. 对同一区间输出 frame JSON，以 decoded-frame PTS 补足呈现顺序证据，并比较 packet 数与 frame 数，不预设一一对应；
4. 保存输入 hash、完整工具版本、三条命令、退出码与结论边界。

实践入口：[[计算机知识/80-实践/07-媒体编码与FFmpeg/01-生成合成音视频并用ffprobe诊断|生成合成音视频并用 ffprobe 诊断]]。

### 成功标准

- 输出可被 JSON parser 读取，stderr 没有混进 JSON；
- 能解释缺失字段、`N/A` 与 0 不同；
- 能用 time base 把至少一个整数 PTS 换算成秒；
- 能用 DTS/PTS 差异解释重排，并明确 packet PTS 非单调本身不是损坏结论；
- 能指出 `FRAME` / `SUBTITLE` 与 `frames[].side_data_list[]` 的证据边界，不把某次 JSON shape 当跨版本 schema；
- 能分别陈述 probe、局部 decode、全文件 decode 各证明到哪一层；
- 复现记录不包含私人路径、payload dump 或未授权媒体。

## 官方来源

- [ffprobe Documentation：Main options、`-show_entries`、sections 与 writers](https://ffmpeg.org/ffprobe.html)
- [ffprobe Documentation：`-read_intervals`](https://ffmpeg.org/ffprobe.html#read_005fintervals)
- [FFmpeg CLI Documentation：stream specifiers 与 stream selection](https://ffmpeg.org/ffmpeg.html#Stream-specifiers-1)
- [FFmpeg Formats Documentation：demuxer probe 与 format options](https://ffmpeg.org/ffmpeg-formats.html)

---

**上一站**：[[计算机知识/60-数据编码与媒体系统/12-FFmpeg架构Demux-Decode-Filter-Encode-Mux|FFmpeg 架构]] · **下一站**：[[计算机知识/60-数据编码与媒体系统/14-FFmpeg常用转码裁剪拼接字幕与音频处理|FFmpeg 常用转码、裁剪、拼接、字幕与音频处理]] · **I/O 连接**：[[计算机知识/30-计算机系统/11-存储设备块层页缓存与持久化|存储设备、块层、页缓存与持久化]] · **返回**：[[计算机知识/60-数据编码与媒体系统/00-数据编码与媒体系统-MOC|数据编码与媒体系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/09-计算机网络-课程地图|计算机网络 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|网络：UDP、TCP、可靠传输与应用分帧]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
