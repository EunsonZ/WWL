---
type: lab
domain: computer-science
stage: 20
status: ready
difficulty: 进阶
estimated_minutes: 45
verified_on: 2026-09-03
topics:
  - manifest
  - batch-processing
  - untrusted-input
  - sandboxing
tags:
  - computer-science/media
  - computer-science/security
  - computer-science/lab
---

# 批处理 Manifest 与不可信输入边界

## 目标

把批处理拆成“先完整预检，再创建输出目录，再逐项处理”三段。默认模式会在唯一临时 workspace 生成两个 2 秒 Matroska 小样和四列 TSV；传入自定义 manifest 时，脚本只接受与清单同目录的普通媒体文件 basename，不接受 URL、协议前缀、绝对路径、子目录、`..`、符号链接、重复输出名、超过 20 MiB 的输入或超过 100 行的任务。

生产安全背景见 [[计算机知识/60-数据编码与媒体系统/17-媒体工程安全许可隐私与可复现性|媒体工程安全、许可、隐私与可复现性]]；文件与权限基础见 [[计算机知识/20-操作系统/01-Linux/03-目录结构挂载与文件系统|目录、挂载与文件系统]]。

## 清单契约

每个非空、非注释行恰好四个 Tab 分隔字段：

```text
input-basename.mkv<TAB>output-basename.mp4<TAB>start-seconds<TAB>duration-seconds
```

输入只允许 `.mkv`、`.mp4` 或 `.mov` 的简单 ASCII basename；输出只允许简单 `.mp4` basename。数字必须是非负十进制，duration 不能为零。窄契约是教学安全选择，不是 FFmpeg 格式能力清单。

## 运行源码

先运行默认安全样例：`bash ./04_batch_manifest.sh`。再运行仓库中的纯文本拒绝夹具：

```bash
bash ./04_batch_manifest.sh ./04_unsafe_manifest.tsv /tmp/should-not-be-created
```

它应在预检阶段拒绝 `https://...`，且不创建 `/tmp/should-not-be-created`，也不会发起网络请求。若该路径本来存在，换一个明确且尚不存在的临时路径，以免把“已有目录拒绝”误当作“协议拒绝”。

重复输出名也必须在创建输出目录前被拒绝。先运行一次默认样例，记下它打印的 `temporary-workspace=` 绝对路径；将下例中的 `/实际临时路径` 替换为该值。两行都引用默认样例已经生成的普通输入，但故意写入同一个 `same.mp4`：

```bash
demo_workspace='/实际临时路径'
duplicate_manifest="$demo_workspace/input/duplicate-output.tsv"
duplicate_target="$demo_workspace/duplicate-should-not-exist"
printf '%s\t%s\t%s\t%s\n' \
  'clip-a.mkv' 'same.mp4' '0' '1' \
  'clip-b.mkv' 'same.mp4' '0' '1' > "$duplicate_manifest"
bash ./04_batch_manifest.sh "$duplicate_manifest" "$duplicate_target"
test ! -e "$duplicate_target"
```

预期脚本报告第二行的 `duplicate output name rejected` 并非零退出，最后的 `test` 成功。这里显式输出路径属于可信操作者选项；若父目录包含符号链接、由其他账号共享，或存在并发替换风险，应改用默认 `mktemp` 路径，不能把该显式选项当成不可信路径沙箱。

<!-- code-sync: ./04_batch_manifest.sh -->
```bash
#!/usr/bin/env bash
set -euo pipefail

for tool in ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'SKIP: %s is not available in PATH\n' "$tool" >&2
    exit 77
  fi
done

if (( $# > 2 )); then
  printf 'usage: %s [manifest.tsv [new-output-directory]]\n' "$0" >&2
  exit 64
fi

temp_base="${TMPDIR:-/tmp}"
temp_base="${temp_base%/}"
workspace="$(mktemp -d "$temp_base/workwithllm-ffmpeg-batch.XXXXXX")"

if (( $# >= 1 )); then
  manifest="$1"
  [[ -f "$manifest" && ! -L "$manifest" ]] || {
    printf 'manifest must be a regular, non-symlink file: %s\n' "$manifest" >&2
    exit 65
  }
  manifest_dir="$(cd -- "$(dirname -- "$manifest")" && pwd -P)"
  manifest="$manifest_dir/$(basename -- "$manifest")"
  input_dir="$manifest_dir"
else
  input_dir="$workspace/input"
  mkdir -- "$input_dir"
  ffmpeg -hide_banner -loglevel warning -nostdin -n \
    -f lavfi -i 'testsrc2=size=160x120:rate=15:duration=2' \
    -f lavfi -i 'sine=frequency=440:sample_rate=48000:duration=2' \
    -map 0:v:0 -map 1:a:0 -c:v ffv1 -c:a pcm_s16le \
    "$input_dir/clip-a.mkv"
  ffmpeg -hide_banner -loglevel warning -nostdin -n \
    -f lavfi -i 'testsrc2=size=160x120:rate=15:duration=2' \
    -f lavfi -i 'sine=frequency=660:sample_rate=48000:duration=2' \
    -map 0:v:0 -map 1:a:0 -c:v ffv1 -c:a pcm_s16le \
    "$input_dir/clip-b.mkv"
  manifest="$input_dir/manifest.tsv"
  printf '%s\t%s\t%s\t%s\n' \
    'clip-a.mkv' 'clip-a.mp4' '0' '1.25' \
    'clip-b.mkv' 'clip-b.mp4' '0.25' '1.50' > "$manifest"
fi

if (( $# == 2 )); then
  output_dir="$2"
else
  output_dir="$workspace/output"
fi

[[ -n "$output_dir" && "$output_dir" != / && ! -e "$output_dir" ]] || {
  printf 'refusing existing or unsafe output directory: %s\n' "$output_dir" >&2
  exit 73
}
[[ -d "$(dirname -- "$output_dir")" ]] || {
  printf 'output parent does not exist\n' >&2
  exit 73
}

validate_row() {
  local line_number="$1" input_name="$2" output_name="$3"
  local start="$4" duration="$5" input_path size

  case "$input_name" in
    *://*|*:*|/*|*/*|*\\*|*..*)
      printf 'line %s: protocol, absolute, traversal, or nested input rejected\n' "$line_number" >&2
      return 1
      ;;
  esac
  [[ "$input_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*\.(mkv|mp4|mov)$ ]] || {
    printf 'line %s: input name or extension rejected\n' "$line_number" >&2
    return 1
  }
  [[ "$output_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*\.mp4$ ]] || {
    printf 'line %s: output must be a plain .mp4 basename\n' "$line_number" >&2
    return 1
  }
  [[ "$start" =~ ^[0-9]+([.][0-9]+)?$ ]] || {
    printf 'line %s: invalid start time\n' "$line_number" >&2
    return 1
  }
  [[ "$duration" =~ ^[0-9]+([.][0-9]+)?$ && ! "$duration" =~ ^0+([.]0+)?$ ]] || {
    printf 'line %s: invalid duration\n' "$line_number" >&2
    return 1
  }

  input_path="$input_dir/$input_name"
  [[ -f "$input_path" && ! -L "$input_path" ]] || {
    printf 'line %s: input must be a regular, non-symlink file\n' "$line_number" >&2
    return 1
  }
  size="$(wc -c < "$input_path" | tr -d ' ')"
  (( size <= 20971520 )) || {
    printf 'line %s: input exceeds the 20 MiB lab limit\n' "$line_number" >&2
    return 1
  }
  ffprobe -v error -protocol_whitelist file,pipe \
    -probesize 10000000 -analyzeduration 5000000 \
    -show_entries format=format_name,duration -of json "$input_path" >/dev/null
}

# Read the raw row; tab is whitespace in IFS and read would collapse empty fields.
parse_row() {
  local rest="$1" tab=$'\t'
  [[ "$rest" == *"$tab"* ]] || return 1
  input_name="${rest%%"$tab"*}"; rest="${rest#*"$tab"}"
  [[ "$rest" == *"$tab"* ]] || return 1
  output_name="${rest%%"$tab"*}"; rest="${rest#*"$tab"}"
  [[ "$rest" == *"$tab"* ]] || return 1
  start="${rest%%"$tab"*}"; duration="${rest#*"$tab"}"
  [[ "$duration" != *"$tab"* ]] || return 1
  # Empty fields are preserved here and rejected by each field's syntax below.
}

line_number=0
row_count=0
seen_outputs="$workspace/seen-output-names.txt"
: > "$seen_outputs"
while IFS= read -r row || [[ -n "$row" ]]; do
  line_number=$((line_number + 1))
  [[ -z "$row" || "$row" == \#* ]] && continue
  parse_row "$row" || {
    printf 'line %s: expected exactly four tab-separated fields\n' "$line_number" >&2
    exit 65
  }
  row_count=$((row_count + 1))
  (( row_count <= 100 )) || {
    printf 'manifest exceeds the 100-row lab limit\n' >&2
    exit 65
  }
  validate_row "$line_number" "$input_name" "$output_name" \
    "$start" "$duration"
  if grep -Fqx -- "$output_name" "$seen_outputs"; then
    printf 'line %s: duplicate output name rejected: %s\n' \
      "$line_number" "$output_name" >&2
    exit 65
  fi
  printf '%s\n' "$output_name" >> "$seen_outputs"
done < "$manifest"
(( row_count > 0 )) || {
  printf 'manifest contains no jobs\n' >&2
  exit 65
}

mkdir -- "$output_dir"
output_dir="$(cd -- "$output_dir" && pwd -P)"
printf '%s\n' 'WorkWithLLM FFmpeg bounded-batch lab' > "$output_dir/.lab-marker"

while IFS= read -r row || [[ -n "$row" ]]; do
  [[ -z "$row" || "$row" == \#* ]] && continue
  parse_row "$row" || {
    printf 'line %s: expected exactly four tab-separated fields\n' "$line_number" >&2
    exit 65
  }
  input_path="$input_dir/$input_name"
  output_path="$output_dir/$output_name"
  [[ ! -e "$output_path" ]] || {
    printf 'refusing to overwrite: %s\n' "$output_path" >&2
    exit 73
  }
  ffmpeg -hide_banner -loglevel warning -nostdin -n \
    -protocol_whitelist file,pipe -i "$input_path" -ss "$start" -t "$duration" \
    -map '0:v:0?' -map '0:a:0?' -sn -dn -map_metadata -1 -map_chapters -1 \
    -c:v libx264 -preset veryfast -crf 28 -pix_fmt yuv420p \
    -c:a aac -b:a 64k "$output_path"
  ffprobe -v error -show_format -show_streams -of json "$output_path" \
    > "$output_path.probe.json"
done < "$manifest"

printf 'PASS: jobs=%s output=%s\n' "$row_count" "$output_dir"
printf 'temporary-workspace=%s\n' "$workspace"
```

## 四层边界与仍未解决的问题

1. **字符串层**：严格列数、basename、扩展名和数值语法；在第一遍预检中用普通文本集合拒绝重复 `output_name`；不拼 shell 命令，不使用 `eval`。
2. **文件系统层**：manifest 和输入必须是普通非符号链接文件；输入必须与 manifest 同目录；输出目录必须不存在。显式输出目录是可信操作者选项；父目录符号链接和共享目录竞态不在“不可信 manifest”保证内，默认 `mktemp` 路径更安全。
3. **FFmpeg 层**：`-protocol_whitelist file,pipe`、有限 probe 大小/分析时长、禁字幕/数据流/metadata/chapters、显式 map、`-nostdin -n`。
4. **工作量层**：每个输入最多 20 MiB，清单最多 100 项，默认样例极小。

这些防线仍不足以把任意未知媒体当成可信输入：脚本没有跨平台可靠的 CPU 时间、地址空间、输出字节和进程树限制；20 MiB 压缩文件仍可能触发昂贵解码；被允许的容器/codec 解析器仍可能有漏洞；输入在预检后也可能被同机其他进程替换（TOCTOU）。生产环境应在补丁及时的隔离容器/沙箱中运行，设置 CPU、内存、磁盘、进程、时限与网络命名空间配额，并对任务队列、日志、许可和隐私做独立治理。

本机 2026-09-03 使用 `ffmpeg/ffprobe 9.0.1` 真实运行默认两项批处理，并真实运行 `04_unsafe_manifest.tsv` 拒绝测试；拒绝发生在 FFmpeg 读取输入前，指定输出目录未创建。未做 fuzzing、恶意 codec 样本、沙箱逃逸、资源炸弹、并发竞态或生产负载测试。

## 练习、成功标准与恢复

复制默认 manifest 到自己的全新临时目录，逐项尝试 `../x.mkv`、`file:x.mkv`、`https://...`、额外第五列、符号链接、重复 `output_name` 和已有输出目录；每次确认脚本非零退出且没有部分输出。不要把真实未知媒体作为本练习的“攻击样本”。

- [ ] 默认两项均生成 MP4 和对应 probe JSON；
- [ ] 协议夹具在预检时被拒绝，目标输出目录没有出现；
- [ ] 两行使用同一个 `output_name` 时，第二行在第一遍预检中被拒绝，目标输出目录没有出现；
- [ ] 任意一行不合格时整批在创建输出目录前停止；
- [ ] 能列出脚本已缓解与尚未缓解的风险，不把白名单称为沙箱。

恢复时核对 `temporary-workspace=` 或 `output=` 的精确绝对路径及 `.lab-marker`，再人工删除对应唯一临时目录；拒绝夹具是课程源文件，不是输出，不要删除或改为真实 URL 请求。

---

**上一站**：[[计算机知识/80-实践/07-媒体编码与FFmpeg/03-Filtergraph时间戳与音画同步|Filtergraph 与同步]] · **返回**：[[计算机知识/80-实践/07-媒体编码与FFmpeg/00-媒体编码与FFmpeg实践-MOC|实践 MOC]] · **安全理论**：[[计算机知识/60-数据编码与媒体系统/17-媒体工程安全许可隐私与可复现性|媒体工程安全]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/09-计算机网络-课程地图|计算机网络 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|网络：UDP、TCP、可靠传输与应用分帧]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

### 当前边界回归接口

同源 `test_shell_contracts.py` 定义 stub FFmpeg/ffprobe 回归：三列、五列、尾部空列、中间空列均在探测前拒绝；`0`、`0.0`、`00`、`0.00`、`000.000` 拒绝，`0.1` 与 `1` 保持合法。原始 TSV 行恰含三个 Tab 后才逐字段校验，不依赖会折叠空字段的 Tab-IFS。比较脚本进入已独占创建的输出目录，滤镜只用固定相对 `psnr.log`/`ssim.log`，shell 引号与 filtergraph 转义分别处理。普通、空格、冒号、逗号和单引号目录名的真实 FFmpeg parser 对照与完整默认合成样本均 `not_run`；stub 只证明参数及拒绝路径，不证明解码或客观指标。
