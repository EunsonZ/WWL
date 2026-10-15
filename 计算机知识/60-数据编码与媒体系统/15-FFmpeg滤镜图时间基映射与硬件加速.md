---
type: lesson
domain: computer-science
stage: 6
status: ready
difficulty: 进阶
estimated_minutes: 105
verified: 2026-09-03
local_toolchain: FFmpeg 9.0.1 (Homebrew, macOS arm64)
topics:
  - filtergraph
  - PTS
  - time base
  - stream mapping
  - frame rate
  - hardware frames
  - hardware acceleration
tags:
  - computer-science/media
  - computer-science/ffmpeg
  - computer-science/heterogeneous-computing
---

# FFmpeg 滤镜图、时间基、映射与硬件加速

复杂 FFmpeg 管线的难点通常不是某个滤镜参数，而是三类边界同时出现：**图的 pad 如何连接、每条 frame 的时间如何解释、frame 当前位于系统内存还是硬件 surface**。只盯最终 encoder 名称，会漏掉自动 stream selection、帧率修改、隐式格式转换和 CPU↔设备搬运。

> [!info] 证据边界
> 稳定概念来自 FFmpeg 官方 filtergraph、CLI 和硬件设备 API 文档。2026-09-03 本机实查为 FFmpeg 9.0.1 Homebrew arm64；`-hwaccels` 只列出 `videotoolbox`，filters 列出 `hwupload`、`hwdownload`、`scale_vt`，encoders 列出 `h264_videotoolbox`、`hevc_videotoolbox`、`prores_videotoolbox`。这仍不证明硬件、OS 会话与任意 codec/profile 可用。本页明确记录一次成功的软件对照与硬件失败，不把组件枚举当成端到端通过。

## 本课目标

学完后，你应该能够：

1. 用 filter、pad、link、chain 与 graph 解释 `-vf` / `-filter_complex`；
2. 为复杂图的输入/输出加 label，并用 `-map` 精确消费输出；
3. 用 `time = PTS × time_base` 分析 `setpts`、`asetpts`、trim 与 concat；
4. 区分 `fps` filter、`-fps_mode` 与旧教程的 `-vsync`；
5. 画出 device context、hardware frames、upload/download、hardware filter 与 encoder；
6. 设计不会静默降级的硬件尝试与独立软件 fallback。

## 1. Filtergraph 是有向图

FFmpeg 官方定义中，filtergraph 是由 filters 和 links 组成的有向图。每个 filter 有零个或多个 input/output **pads**；source 没有 input pad，sink 没有 output pad。

一般图的邻接、遍历、环与拓扑概念可回看 [[计算机知识/50-数据结构与算法/07-图的表示BFS-DFS与拓扑排序|图的表示、BFS、DFS 与拓扑排序]]。但 FFmpeg filtergraph 还带有 media type、pad 数量、label、format 协商与 time-base 契约；一般图算法只是理解结构的前置，不能替代 FFmpeg CLI 的连接、转义、映射和时间轴规则。

文本语法的最小规则：

```text
[input_labels]filter=arguments[output_labels]

filter_a,filter_b       # comma: 同一 chain，前者输出接后者输入
chain_a;chain_b         # semicolon: 两条 chain
[label]                 # 给 link 命名，跨 chain 或供 -map 使用
```

例如：

```text
[0:v:0]scale=1280:-2,format=yuv420p[vsmall]
```

- `[0:v:0]` 引用第 0 个输入的第一条视频；
- `scale` 的 output pad 自动连到 `format` 的 input pad；
- `[vsmall]` 是最终 output link label；
- 命令行还需 `-map "[vsmall]"` 把它变成输出 stream。

`-vf` / `-af` 是恰有一个同类型输入和输出的 simple filtergraph；跨多个输入、分支、overlay、mix、concat 或多输出通常使用 `-filter_complex`。

## 2. 为什么复杂图要把每个边标出来

```bash
ffmpeg -hide_banner -n \
  -i "main.example.mp4" \
  -i "overlay.example.webm" \
  -filter_complex \
'[0:v:0]setpts=PTS-STARTPTS[base];
 [1:v:0]setpts=PTS-STARTPTS[mark];
 [base][mark]overlay=x=W-w-32:y=H-h-32:eof_action=pass[vout]' \
  -map "[vout]" -map '0:a:0?' \
  -c:v libx264 -c:a copy \
  "composited.example.mkv"
```

这个图有两条 source link、两个 `setpts` 实例和一个双输入 `overlay`。显式 label 能回答每条边来自哪里、进入哪个 pad、最终被哪个 output 消费。`eof_action=pass` 表示 overlay 输入结束后让 main 继续；仍需检查实际时间轴与目标长度。

复杂 filtergraph 的无标签 output 可能被自动加入第一个输出文件，且会影响 stream selection。为避免“多出一条视频”“第一个输出格式不接受该流”等意外：

1. 给需要输出的每个 pad 唯一 label；
2. 用 `-map "[label]"` 明确消费；
3. 不让同一 labeled output 被 map 两次；
4. 用 ffmpeg 启动日志和 ffprobe 输出复核 mapping。

## 3. 三层转义：shell、graph、filter option

`drawtext`、字幕路径和表达式常包含 `: , ; [ ] ' \`。它们可能依次经过：

1. shell 参数解析；
2. filtergraph 语法解析；
3. 具体 filter option 解析。

因此“加一条反斜杠”没有跨 shell 的万能答案。POSIX shell 示例尽量让整张 graph 用单引号包围，并使用无空格、无冒号的合成相对路径；PowerShell/CMD 要按各自规则改写。复杂生产图宜使用 FFmpeg 支持的 filtergraph file option，并把文件当不可信代码配置审阅，而不是从外部文本拼接。

## 4. Time base 是 tick 单位，PTS 是 tick 数

基本换算：

```text
presentation time in seconds = PTS × time_base
```

同一个 2 秒时刻可以表示为：

```text
time_base = 1/1000,  PTS = 2000
time_base = 1/90000, PTS = 180000
```

FFmpeg 管线中可能同时出现 demuxed stream time base、decoded frame time base、filter link time base、encoder time base 与 muxed stream time base。跨边界要 rescale；不能复制一个整数 PTS 到另一 time base 后仍声称时间没变。

时间轴前置见 [[计算机知识/60-数据编码与媒体系统/08-数字视频帧率扫描色彩采样与时间基|数字视频：帧率、扫描、色彩采样与时间基]] 与 [[计算机知识/60-数据编码与媒体系统/11-流媒体时间戳同步Seek与协议边界|流媒体：时间戳、同步、Seek 与协议边界]]。

## 5. `setpts` / `asetpts` 改的是呈现时间

官方 `setpts` 为每个视频 frame 计算新 PTS，`asetpts` 对音频 frame 做同类工作。

### 归零起点

```text
video: setpts=PTS-STARTPTS
audio: asetpts=PTS-STARTPTS
```

这对 concat filter 很重要，因为每个 segment 必须从 timestamp 0 开始。归零不是“校准音画”：如果输入本来有语义明确的相对 offset，对两条流分别减各自 `STARTPTS` 可能消除它。先决定目标时间线，再重写。

### Trim 后显式归零

`trim` / `atrim` 选择区间，但官方文档说明它们不会自动修改 timestamps：

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mkv" \
  -filter_complex \
'[0:v:0]trim=start=5:end=15,setpts=PTS-STARTPTS[vout];
 [0:a:0]atrim=start=5:end=15,asetpts=PTS-STARTPTS[aout]' \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -c:a aac \
  "trimmed.example.mkv"
```

此例假设音视频都存在；缺少音频时 `[0:a:0]` 会失败，应在生成图之前根据 probe 结果构造另一条明确管线，而不是让任意字符串静默改变 graph。

### 加速与减速

把视频时间压缩为原来的 `1/1.25`：

```text
setpts=PTS/1.25
```

这不会凭空合成更流畅运动，只是改变 frame 的 timestamps；输出帧率策略还可能丢帧/复制。音频若要保持音高地改变 tempo，通常用：

```text
atempo=1.25
```

不要把 `asetpts=PTS/1.25` 当作通用音频变速：它只重写时间戳，不重采样/时伸音频内容，可能造成重叠、间隙或 mux/sync 问题。

### 从固定帧序号生成时间戳

```text
setpts=N/(25*TB)
```

`N` 是从 0 开始的输入 frame 计数，`TB` 是 filter 的 time base；该表达式生成 25 fps 时间间隔。它会丢弃原始采集时间变化，只适合你明确要构造新 CFR timeline 的场景。

## 6. `fps` filter、`-fps_mode` 与 `-vsync`

三者位于不同语义层：

| 机制 | 位置/作用 | 典型行为 |
| --- | --- | --- |
| `fps=fps=25` | filtergraph | 通过丢弃/复制 decoded frames 形成指定 CFR |
| `-fps_mode:v cfr` | output、per-stream | 输出同步策略为 CFR，必要时丢弃/复制 |
| `-fps_mode:v vfr` | output、per-stream | 保留时间戳，必要时避免同 timestamp 冲突 |
| `-fps_mode:v passthrough` | output、per-stream | 把 frame timestamps 传给 muxer；muxer仍可能调整 |
| `-fps_mode:v auto` | output、per-stream | 按 muxer 能力选择 CFR/VFR，是默认策略 |

当你要在 graph 中明确得到 25 fps frames，使用 `fps=25` 并 probe 输出；当你只需声明 output sync policy，使用 `-fps_mode`。不要同时堆叠 `fps`、output `-r` 和 `-fps_mode cfr` 而不解释哪一层负责时间轴。

旧教程常写 `-vsync 0/1/2`。本机 FFmpeg 9.0.1 的 `-h full` 已不列出 `-vsync`，一次最小 null-output 调用返回 `Unrecognized option 'vsync'`（exit 8）；相同规模的 `-fps_mode:v cfr` 调用成功（exit 0）。因此本课程新命令只使用 `-fps_mode`。其他 FFmpeg 版本必须查自己的 `ffmpeg -h full`，不能把本机结论倒推到旧版。

## 7. Hardware acceleration 有四个独立问题

“用了 GPU”至少要拆成：

1. **hardware decode**：压缩 packet 由何 decoder/accelerator 处理？
2. **frame location**：decoded frame 在系统内存还是 hardware surface？
3. **filter**：每个 filter 接受 software frames 还是特定 hardware frames？
4. **hardware encode**：最终 encoder 是否为硬件实现，是否又把 frame 上传？

```text
compressed packets
  ├─ software decoder → software AVFrame ── software filters ── software encoder
  │                                  └─ hwupload → HW filter → hwdownload ─┘
  └─ hardware decoder → hardware AVFrame ── compatible HW filters ── HW encoder
                                    └─ hwdownload → software filter ...
```

硬件 encoder 名称只证明最后一段的选择；不能证明 decode/filter 零拷贝。`-hwaccel` 是 input/per-stream decode 选项，不等于硬件编码。

## 8. Device context 与 hardware frames context

FFmpeg 的硬件 API 把“设备”和“设备上的 frame 池/格式”分开：

- `AVHWDeviceContext`：一种硬件设备/后端的上下文；
- `AVHWFramesContext`：与 device 关联的 hardware frame pool，描述 hardware format、software-visible format、尺寸等；
- `-init_hw_device type=name...`：建立命名 device；
- `-filter_hw_device name`：把 device 提供给需要它的 filters；
- `-hwaccel_device name`：为 hardware decode 选择 device；
- `-hwaccel_output_format`：选择 hardware decode 的 frame output format；
- `hwupload`：software frame → hardware surface；
- `hwdownload`：hardware surface → software frame。

`hwupload` 前常需要 `format` 确保软件 pixel format 被目标后端接受；`hwdownload` 后也常需要 `format` 选取可用的 software layout。不同硬件后端的 frames 不能仅凭“都在 GPU”直接互连，某些情况要 `hwmap` 或显式 download/upload。

## 9. 先做只读能力检查

```bash
ffmpeg -hide_banner -version
ffmpeg -hide_banner -hwaccels
ffmpeg -hide_banner -decoders
ffmpeg -hide_banner -encoders
ffmpeg -hide_banner -filters
ffmpeg -hide_banner -pix_fmts
ffmpeg -hide_banner -h encoder=h264_videotoolbox
ffmpeg -hide_banner -h filter=scale_vt
```

这些命令不处理输入、不创建输出。仍要区分三层：

```text
registered in build ≠ runtime device available ≠ target pipeline passed
```

驱动、权限、OS session、codec/profile/level、bit depth、pixel format、尺寸、并发 session 与 surface pool 都可能让运行失败。

## 10. 本机 VideoToolbox：一次失败比列表更有信息

本机 2026-09-03 的只读列表显示：

```text
-hwaccels: videotoolbox
hardware pixel format: videotoolbox_vld
filter: scale_vt
encoders: h264_videotoolbox, hevc_videotoolbox, prores_videotoolbox
```

随后用 FFmpeg 自带 `lavfi testsrc2` 生成 1 秒、320×180、24 fps 的 H.264 合成输入，并尝试：

```bash
# 这是已尝试但在当前执行环境失败的管线形状，不是可复制的成功配方。
ffmpeg -hide_banner -n \
  -hwaccel videotoolbox \
  -hwaccel_output_format videotoolbox_vld \
  -i "synthetic-input.example.mp4" \
  -vf "scale_vt=w=160:h=90" \
  -c:v h264_videotoolbox -b:v 400k -an \
  "hardware-output.example.mp4"
```

当前环境返回了 hardware decode setup failure，随后 hardware/software frame format 无法接到 `scale_vt`。另一次 software decode/filter → `h264_videotoolbox` encode 尝试在创建 compression session 时返回 `-12903`，并建议 `-allow_sw 1`。本次没有启用 `-allow_sw 1`，因为那会改变“必须证明硬件编码”的验收含义。

对照管线改用 software `libx264`，在同一合成输入上成功输出 H.264 160×90 `yuv420p`：

```bash
ffmpeg -hide_banner -n \
  -i "synthetic-input.example.mp4" \
  -vf "scale=w=160:h=90,format=yuv420p" \
  -c:v libx264 -crf 23 -an \
  "software-output.example.mp4"
```

这里的结论严格限于：**该软件对照在本次 1 秒合成样本上成功，而 VideoToolbox 两条尝试在当前执行环境失败。** 它不证明这台 Mac 永远不能用 VideoToolbox，也不证明 software 在真实性能/质量上更好；OS 会话、沙箱、并发占用和参数都需进一步定位。

## 11. 不静默降级的 fallback 设计

不要写这种管线：

```text
try hardware; if anything fails, silently run software to the same output name
```

这样最终文件存在，却无法证明来自哪个 path。可审计做法：

1. hardware 与 software 使用不同输出名，例如 `result.hardware.example.mp4` / `result.software.example.mp4`；
2. 保存完整版本、命令、stderr、exit code；
3. hardware path 明确指定 backend、frame format/filter/encoder，不使用无法辨认结果的“auto + 允许软件”组合；
4. hardware 失败后，由编排层记录 failure reason，再独立启动 software fallback；
5. ffprobe 输出 codec/pixel format；日志证明 encoder/decoder/filter；性能/质量另测；
6. 只有通过既定验收的那份输出才进入交付，另一份保留或删除都由明确策略决定。

例如软件 fallback 可使用独立文件：

```bash
ffmpeg -hide_banner -n \
  -i "input.example.mp4" \
  -map 0:v:0 -map '0:a:0?' \
  -vf "scale=w=1280:h=-2,format=yuv420p" \
  -c:v libx264 -crf 20 -c:a aac \
  "result.software.example.mp4"
```

不要用 shell 的 `||` 把硬件与软件两条命令压成一行；那会让日志、退出码、部分文件清理和选择策略难以审计。

## 12. Hardware frame 搬运是 I/O，不是免费箭头

即使硬件 filter/encoder 更快，`hwupload` / `hwdownload`、像素格式转换、同步和 surface 等待也可能吞掉收益。尤其“小分辨率、短片段、只做一个简单 filter”时，固定启动和数据移动成本可能占主导。

测量至少分开：

- 端到端 wall time 与吞吐，而不是只看 kernel/encoder 内部；
- CPU 使用、设备使用、读写带宽与内存/显存峰值；
- upload/download 次数和 software↔hardware 边界；
- 输出码率、帧数、timestamps、色彩/音频 metadata；
- 在可比码率/质量约束下的客观指标与人工观看/聆听。

系统层连接：[[计算机知识/30-计算机系统/10-IO设备总线DMA与中断|I/O 设备、总线、DMA 与中断]]、[[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]]、[[计算机知识/40-并行与异构计算/01-CUDA/01-CPU与GPU异构执行模型|CPU 与 GPU 异构执行模型]]。Linux 上的 VAAPI/QSV/CUDA/NVENC 等还牵涉驱动、device nodes、容器设备映射与用户态库，部署边界见 [[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]]。

## 13. 未验证平台清单

本页没有运行：

- Linux VAAPI、NVIDIA NVDEC/NVENC/CUDA、Intel QSV 或 Vulkan/OpenCL filter；
- Windows D3D11VA/DXVA2、Media Foundation/厂商 encoder；
- AMD AMF、独显/多 GPU device selection；
- 10-bit/HDR、4:2:2/4:4:4、alpha、interlaced、B-frame 重排的硬件全链路；
- live capture/streaming、容器化硬件映射、多并发 session；
- 真实内容质量、功耗、长期稳定性或跨播放器兼容。

这些不是“预计会通过”的待勾选项，而是需要各自官方文档、目标版本和真实设备实验的新证据层。

## 14. 故障定位矩阵

| 症状 | 可能边界 | 先收集什么 |
| --- | --- | --- |
| `No such filter` | 构建未注册 filter | `-filters`、完整 `-version` |
| `Impossible to convert between formats` | software/hardware frame 或 pixel format 不匹配 | 图中每条边的 format、自动插入 filter 日志 |
| device creation failed | 驱动/权限/device name/backend | `-init_hw_device` 错误、OS/driver、device nodes |
| hardware decoder setup failed | codec/profile/format/session | stream profile/level/pix_fmt、decoder help |
| compression session failed | encoder/OS session/参数/并发 | encoder help、完整错误；不要先开软件 fallback |
| `Non-monotonous DTS` | timeline/rescale/mux | input/output packet PTS/DTS/time base |
| 帧数或时长改变 | fps mode/filter/trim/setpts | graph、`-fps_mode`、frame timestamps/count |
| GPU 使用低且更慢 | upload/download/同步/工作量小 | 端到端时间和每个内存边界，不只看 utilization |

## 练习：画出图和内存域

使用合成实践素材：

1. 为“两输入 overlay + 原输入音频”画 pads/labels，并与实际 `-filter_complex` 一一对应；
2. 对实践入口约 4 秒的合成素材，trim 1–3 秒，先不加 `setpts/asetpts` 观察 timestamps，再归零并比较；这个区间位于视频及 3.6 秒音频的有效范围内，不需要另换长素材；
3. 分别使用 `fps=25` 与 `-fps_mode:v cfr`，保存 frame PTS/数量，解释两层差异；
4. 在目标机器只读列出 hardware components，再设计硬件/软件两个独立输出名；
5. 若硬件尝试失败，把失败当结果记录，不开启静默 software option；跑独立软件对照并比较。

实践入口：[[计算机知识/80-实践/07-媒体编码与FFmpeg/03-Filtergraph时间戳与音画同步|Filtergraph、时间戳与音画同步]]。

### 成功标准

- graph 中每个 pad 都已连接，每个输出 label 都有明确 `-map`；
- 能把至少两个 PTS 按各自 time base 换算为秒；
- trim/concat 后的音视频起点与目标 offset 符合设计；
- 能说明实际使用的是 `fps` filter 还是 output `-fps_mode`；
- 日志能区分 software/hardware decode、frame location、filter 与 encode；
- hardware 与 fallback 使用不同文件名、日志和退出码，不会把降级伪装成硬件成功；
- 报告列出本机证据、未验证平台、性能/质量边界和恢复方式。

## 官方来源

- [FFmpeg Filters Documentation：Filtergraph description](https://ffmpeg.org/ffmpeg-filters.html#Filtergraph-description)
- [FFmpeg Filters Documentation：`setpts` / `asetpts`](https://ffmpeg.org/ffmpeg-filters.html#setpts_002c-asetpts)
- [FFmpeg Filters Documentation：`fps`](https://ffmpeg.org/ffmpeg-filters.html#fps-1)
- [FFmpeg Filters Documentation：`hwupload` / `hwdownload`](https://ffmpeg.org/ffmpeg-filters.html#hwupload)
- [FFmpeg CLI Documentation：`-fps_mode`、timestamp 与 hardware acceleration options](https://ffmpeg.org/ffmpeg.html)
- [FFmpeg Doxygen：Hardware device / frames API](https://ffmpeg.org/doxygen/trunk/hwcontext_8h.html)
- [FFmpeg Doxygen：libavfilter public API](https://ffmpeg.org/doxygen/trunk/avfilter_8h.html)

---

**上一站**：[[计算机知识/60-数据编码与媒体系统/14-FFmpeg常用转码裁剪拼接字幕与音频处理|FFmpeg 常用操作]] · **下一站**：[[计算机知识/60-数据编码与媒体系统/16-媒体质量评估PSNR-SSIM-VMAF与听感边界|媒体质量评估]] · **实践**：[[计算机知识/80-实践/07-媒体编码与FFmpeg/00-媒体编码与FFmpeg实践-MOC|媒体编码与 FFmpeg 实践 MOC]] · **返回**：[[计算机知识/60-数据编码与媒体系统/00-数据编码与媒体系统-MOC|数据编码与媒体系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/60-数据编码与媒体系统/00-数据编码与媒体系统-MOC|数据编码与媒体系统 MOC]]。网络传输相关路线：[[计算机知识/00-开始/课程地图/09-计算机网络-课程地图|计算机网络 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|网络：UDP、TCP、可靠传输与应用分帧]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
