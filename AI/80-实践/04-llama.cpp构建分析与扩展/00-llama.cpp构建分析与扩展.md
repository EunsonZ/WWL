---
type: practice
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 240
domain: artificial-intelligence
topics:
  - llama.cpp
  - GGUF
  - build reproducibility
  - inference tracing
  - benchmarking
  - loopback server
tags:
  - ai/practice/llama-cpp
  - ai/llm/inference
  - ai/llm/observability
---

# llama.cpp 构建、分析与扩展

> **先做离线理解。** [[计算机知识/80-实践/03-C++/03-llama.cpp-token概率与耗时trace/README|C++ trace 实践]]可在不提供 llama.cpp checkout 或 GGUF 时单独运行 softmax/top-k 数学测试；它的完成条件是概率与输入边界的理解，不是 API、模型、trace、benchmark 或后端验收。需要真实源码或模型时，再按本页固定 commit、资产身份、构建和分层记录要求操作。

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 本轮[[AI/80-实践/08-深层机制数值实验/00-数值实验导航与验收|42 项深层机制测试]]补充梯度、概率、缓存与训练状态验证；它与本页实验解决不同层的问题。先读[[AI/20-LLM/80-研究拓展/03-从论文主张到可复现实验|验证层级]]，不要把算子测试成功登记成真实模型或部署验收。


这个实践不复制 llama.cpp 仓库，也不把模型或真实提示词放进 Vault。它把一次可复现的本地实验拆成七层证据：

```text
固定源码身份
  → CPU / 可选 CUDA 构建
  → 本地 GGUF 加载
  → CLI / benchmark / loopback server 冒烟
  → 调用链追踪
  → token 概率与逐步耗时 trace
  → 补丁、测试、回滚与可审计记录
```

原理先读 [[AI/20-LLM/50-实现/04-llama.cpp构建后端与调用链|llama.cpp 构建、后端与调用链]] 和 [[AI/20-LLM/50-实现/05-llama.cpp源码阅读与小型扩展|llama.cpp 源码阅读与小型扩展]]。可编译的 C++ API 观察骨架不在这里重写，而是复用 [[计算机知识/80-实践/03-C++/03-llama.cpp-token概率与耗时trace/README|C++ 实践：llama.cpp token 概率与耗时 trace]]。

> [!warning] 本页的当前证据边界
> 本页编写者没有自行下载 llama.cpp，没有构建外部源码，也没有加载模型、跑 benchmark 或启动 server。主 Agent 在 Vault 外的临时目录做了下述固定 commit CPU 层验收；它不包含 GGUF、生成、benchmark 测量、server 运行或 trace 验收。同目录 manifest 仍是不含真实结果的 `planned` 模板；未来的完整验收记录必须保存在 Vault 外，不得将模型、提示原文、私有路径或凭据提交到这里。

## 已完成的临时 CPU 验收快照

下表是 2026-09-01 在 Vault 外临时树实际获得的窄证据，不得外推为本页所有阶段都已通过：

| 字段 | 已验收值 |
| --- | --- |
| 上游固定 commit | `8887a48f050554f0ee59f56753860c061836b02d` |
| 获取日期 | `2026-09-01` |
| 环境 | macOS Darwin arm64 |
| 编译器 | AppleClang `21.0.0.21000101` |
| CMake | `4.4.3` |
| 配置 | Release；`GGML_METAL=OFF`、`GGML_CUDA=OFF`、`LLAMA_BUILD_TESTS=ON`、`LLAMA_BUILD_EXAMPLES=ON`、`LLAMA_BUILD_TOOLS=ON`、`LLAMA_BUILD_SERVER=ON`、`BUILD_SHARED_LIBS=OFF` |
| 构建通过的指定 target | `llama-cli`、`llama-bench` |
| 目标测试 | `test-unicode`、`test-sampling`，`2/2` 通过 |
| CLI 身份 | `0.3.0-dev build 10743 commit 8887a48f0` |
| 设备枚举 | `llama-bench --offline --list-devices` 只列出 BLAS Accelerate |

这次验收同时暴露了两个必须保留的失败/副作用证据：

1. 首次使用 `LLAMA_BUILD_SERVER=OFF` 的全量构建在 `test-chat` 因缺少 `mtmd.h` 失败；改为 `LLAMA_BUILD_SERVER=ON` 后，上表列出的指定 target 和目标测试通过。这只能记为“指定 CPU 层验收通过”，不能写成“全量构建无失败”。
2. 配置 server 时，临时树自动从 Hugging Face 获取 `llama-ui`：首个 `b10743` URL 失败，随后 `latest` 成功。该网络获取和产物都只发生在临时树，没有进入 Vault。这说明“构建”不一定无网络副作用；未来的离线/供应链验收必须单独控制 UI 资产、下载源与哈希。

未下载模型，未加载 GGUF，未运行生成、真实 benchmark、server 请求或 token trace。`--offline --list-devices` 只是设备枚举，不是性能测量。

## 实验产物与隔离边界

Vault 只保存通用教程、模板、验证器和不含真实结果的补丁模板。真实实验应放在一个仓库外、可整体删除的目录：

```text
<EXPERIMENT_ROOT>/
├── manifest.json
├── source/                  # 单独的 llama.cpp checkout；不进 Vault
├── build-cpu/
├── build-cuda/             # 没有合适 GPU 时不创建
├── logs/
│   ├── cpu-configure.log
│   ├── cpu-build.log
│   ├── cpu-test.log
│   ├── gguf-load.log
│   ├── bench.jsonl
│   ├── server-redacted.log
│   └── trace.jsonl
├── patches/
│   └── trace-extension.patch
└── private/                 # 本地 GGUF 和提示；不同步、不上传
```

记录里用 GGUF SHA-256、提示 SHA-256 和安全摘要关联输入，不要把提示原文、模型 URL、本地用户名路径、Authorization header 或 API key 复制到日志。

## 1. 先固定完整 40 位 commit

只在已获授权、已准备好的本地仓库中操作。本页不提供浮动分支的一键下载命令；获取外部源码必须是独立授权的步骤。不要直接把用户正在使用的 checkout 切成 detached HEAD；默认在实验根目录下创建一个专用 worktree。

```bash
export LLAMA_REPOSITORY='/absolute/path/to/reviewed/llama.cpp'
export LLAMA_COMMIT='replace-with-reviewed-40-hex-commit'
export EXPERIMENT_ROOT='/absolute/path/to/llama.cpp-experiment'
export LLAMA_SRC="$EXPERIMENT_ROOT/source"

test -d "$LLAMA_REPOSITORY/.git"
test ! -e "$LLAMA_SRC"
printf '%s\n' "$LLAMA_COMMIT" | grep -Eq '^[0-9a-f]{40}$'
git -C "$LLAMA_REPOSITORY" cat-file -e "${LLAMA_COMMIT}^{commit}"
git -C "$LLAMA_REPOSITORY" status --short --branch
test -z "$(git -C "$LLAMA_REPOSITORY" status --porcelain)"
git -C "$LLAMA_REPOSITORY" worktree add --detach "$LLAMA_SRC" "$LLAMA_COMMIT"
test "$(git -C "$LLAMA_SRC" rev-parse HEAD)" = "$LLAMA_COMMIT"
test -z "$(git -C "$LLAMA_SRC" status --porcelain)"
git -C "$LLAMA_SRC" show -s --format='%H%n%aI%n%s' HEAD
```

将 `base_commit` 和 `verified_head` 都记为同一个小写 40 位哈希，同时记录 `LLAMA_REPOSITORY` 只是来源仓库、`LLAMA_SRC` 才是本次专用工作区。若来源仓库或专用 worktree 并非 clean：

1. 停止把结果当成上游基线；
2. 保存最小 patch，记录 patch SHA-256；
3. manifest 中写 `dirty: true`；
4. 测试报告同时列出 base commit 和 patch 身份。

不允许用 tag、分支名、短 SHA、“当前最新”或日期代替这个字段。

## 2. 记录 Ubuntu、Arch 和容器的不同边界

| 环境 | 必填身份 | 常见混淆 | 额外验收 |
| --- | --- | --- | --- |
| Ubuntu 主机 | `/etc/os-release`、kernel、精确 compiler/CMake 版本、CPU/RAM | 把 `nvidia-smi` 的 CUDA 上限当成本地 Toolkit | 记录包来源与 compiler 路径 |
| Arch 主机 | kernel、`pacman -Q` 中直接相关包、compiler/CMake | 忽略滚动升级使实验基线发生变化 | 重跑时重新记录包版本，不沿用旧环境标签 |
| NVIDIA 容器 | image digest、host driver/GPU、容器 Toolkit/compiler、设备注入方式 | 以为容器包含 host kernel driver | 记录 mount、UID/GID、CPU/内存/GPU 限制与网络模式 |

容器 tag 会漂移，必须记录 digest。容器里的 CUDA userspace 和宿主机 driver 分开记录。没有 GPU 或兼容 Toolkit 时，CUDA 阶段写 `skipped` 和具体理由，不用 CPU 成功替代它。

## 3. CPU 构建是必过基线

为了避免把旧 CMake cache 误当成新配置，CPU、CUDA、Debug 永远使用不同目录。先从固定 commit 现场发现选项、target 和测试：

```bash
cmake -S "$LLAMA_SRC" -B "$EXPERIMENT_ROOT/build-cpu" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=OFF \
  -DGGML_METAL=OFF
cmake -LAH -N "$EXPERIMENT_ROOT/build-cpu"
cmake --build "$EXPERIMENT_ROOT/build-cpu" --target help
ctest --test-dir "$EXPERIMENT_ROOT/build-cpu" --show-only
cmake --build "$EXPERIMENT_ROOT/build-cpu" --parallel <JOBS>
ctest --test-dir "$EXPERIMENT_ROOT/build-cpu" --output-on-failure
```

不把“构建命令返回 0”当作全部证据。CPU 通过至少需要：

- CMake 配置摘要明确 CUDA 未启用；
- 真实 target 清单、编译器与编译选项已保存；
- 构建与项目自带测试的退出码、日志和失败列表已记录；
- 实际加载/运行时的 backend 日志与 CPU 设置一致；
- Release 用于性能，Debug/RelWithDebInfo 用于阅读和诊断，数字不混报。

## 4. CUDA 是可选、独立的硬件门

只有在 host GPU、driver、Toolkit 与目标 commit 的工具链都已确认时才运行：

```bash
cmake -S "$LLAMA_SRC" -B "$EXPERIMENT_ROOT/build-cuda" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON
cmake -LAH -N "$EXPERIMENT_ROOT/build-cuda"
cmake --build "$EXPERIMENT_ROOT/build-cuda" --parallel <JOBS>
ctest --test-dir "$EXPERIMENT_ROOT/build-cuda" --output-on-failure
```

CUDA 验收不止于编译：运行时必须枚举到目标 GPU，日志必须说明实际 offload/placement，必须有显存与 kernel 活动证据，并且固定输入的正确性在预先定义的容差内。只出现“发现 CUDA”或显存佔用都不足以证明目标计算真正在 GPU 上执行。

## 5. 加载本地 GGUF，不泄露模型与输入

只用已有、获准使用的本地 GGUF。先记录：

- 模型来源 revision 和文件 SHA-256；
- GGUF 版本、architecture、tokenizer/chat template 摘要与张量目录检查结果；
- 输入类型（raw completion 或 chat）、模板身份、渲染后 token 数和安全 SHA-256；
- context、batch、sequence、KV cache、线程和 offload 参数；
- 目标二进制的 `--help` 快照。

二进制名、参数和 GGUF 检查命令都必须从当前 commit 的 target 和 `--help` 确认，不盲从别的版本。最小加载成功只能证明该字节文件在该环境能建立模型/context；它不证明质量、许可、来源安全或长上下文稳定性。

## 6. benchmark 与 server 分开验收

### Benchmark

先用 target 列表找到当前 commit 的 benchmark 工具，再根据它的 `--help` 记录完整命令。最小比较表必须共用同一：

- 40 位 commit 与 patch SHA；
- GGUF SHA-256；
- 渲染后 token 数，不只是可见字符串；
- context/batch/sequence、线程、offload 和 sampler 参数；
- 预热次数、样本次数、冷/热 cache 定义；
- load、prefill/prompt processing、decode/token generation、TTFT、inter-token latency 的边界。

保存每次原始样本，报告中位数与离散程度，不只保存最快一次或一个均值。trace on/off 必须分开跑，因为日志 I/O 自身会扰动热路径。

### Loopback server

启动前先从当前 `--help` 确认 host/port 参数和路由。无论参数名如何，绑定地址必须是：

```text
127.0.0.1
```

不用 `0.0.0.0`、`::`、宿主机局域网 IP 或容器对外端口映射。验收顺序：

1. 启动日志确认实际监听 `127.0.0.1:<PORT>`；
2. 当前 commit 定义的 health 语义成功；
3. 一个非流式请求返回状态码、schema、usage 和 stop reason；
4. 一个流式请求正常终止；
5. 中断客户端后，后端最终取消请求并释放 slot；
6. 非法参数与超长输入不泄露私有路径或堆栈；
7. 正常停止进程后，相同 loopback 端口可再次绑定。

server 请求使用无隐私的固定测试输入；保存输入哈希和 token 数，不保存用户真实提示。

## 7. 从入口追到 backend：用当前符号填表

不背文件名，也不从新版博客猜旧 commit。对固定源码做三次收敛：

1. 从 CMake target 回到入口 translation unit 和链接依赖；
2. 从当前公共 API 声明追到所有调用者；
3. 用一个固定的短请求穿过真实运行路径。

| 阶段 | 当前 commit 的真实文件/符号 | 输入 | 产生/修改 | 所有者与生命周期 | 同步/取消点 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| CLI/server 入口 | 待现场填 | argv/HTTP | config/request | 应用层 | 参数错误/断连 | target + 请求 |
| 模板与 tokenize | 待现场填 | messages/text/vocab | rendered text/tokens | request | 长度/编码 | token IDs |
| GGUF/model load | 待现场填 | file/model params | model/vocab/buffers | process/model | I/O/backend | hash + metadata |
| context/KV | 待现场填 | model/context params | context/KV/workspace | slot/sequence | capacity/reset | memory record |
| batch/decode | 待现场填 | token/pos/seq/logits flag | KV/logits | context | backend sync | row trace |
| graph/scheduler | 待现场填 | tensors/ops | plan/buffers/results | backend/context | copy/kernel/OOM | placement/profile |
| sampler | 待现场填 | logits/history/RNG | chosen token/state | request | accept/reset | top-N + seed |
| detokenize/response | 待现场填 | token/piece | bytes/JSON/SSE | stream/connection | UTF-8/backpressure | escaped piece/span |

每个“待填”都必须有 `rg` 命中、声明/定义与运行 trace 三者中至少两层证据。如果不知道谁销毁 model/context/batch/sampler/buffer，就不能把该格标记完成。

## 8. token 概率与逐步耗时 trace

首选独立 example，不改 server 主路径。从已有 [[计算机知识/80-实践/03-C++/03-llama.cpp-token概率与耗时trace/README|C++ trace 示例]] 起步：它已把 llama.cpp 作为仓库外、固定 commit 的 CMake 输入，并且不会自动下载源码或模型。

一条可审计的逐 token trace 至少有这些事件：

```text
request_start
tokenize_end
prefill_end
sample(step=0, top_n, chosen)
piece_ready(step=0)
decode_end(step=0)       # 为chosen token 更新 KV，产生下一步 logits
sample(step=1, ...)
...
request_end(stop_reason, usage, total_elapsed)
```

概率字段必须标准确阶段：

- `raw_logit`：模型原始分数；
- `diagnostic_probability`：对指定集合重算的诊断 softmax；
- `sampling_probability`：penalty、temperature 和候选过滤后真实抽样分布；
- `chosen_probability`：被选 token 在实际抽样分布中的概率。

不要把任意一种写成“模型置信度”。诊断 top-N 不得消耗 RNG、重复 accept token、改变候选排序或修改 sampler history。

| span | 起点 | 终点 | 必须说明 |
| --- | --- | --- | --- |
| `load_us` | 开始读 GGUF | model/context 和必要 backend buffer 可用 | mmap/page cache 边界 |
| `tokenize_us` | 模板文本完成 | token vector 完成 | special token 策略 |
| `prefill_us` | 提交 prompt batch 前 | logits 可读 | 需要的 backend 同步 |
| `sample_us` | 取得 logits | chosen token 确定并 accept | sampler 链与 top-N 成本 |
| `decode_us` | 提交 chosen token 前 | 下一步 logits 可读 | GPU 不能只计 enqueue |
| `piece_us` | token 已选 | 可发送 UTF-8 bytes 就绪 | 跨 token 字节缓冲 |
| `send_us` | 开始写协议 | 写入协议层完成 | 不等于客户端已收到 |

详细扩展契约、实施后才能填的精确插入点以及补丁验证见 [[AI/80-实践/04-llama.cpp构建分析与扩展/01-trace小扩展与补丁模板|trace 小扩展与补丁模板]]。

## 9. 分阶段测试矩阵

| 门 | 最小测试 | 通过证据 | 不能替代 |
| --- | --- | --- | --- |
| manifest | 模板离线校验 | 退出 0 与状态输出 | 外部构建 |
| CPU configure/build/test | 固定 commit + CUDA/Metal off | 命令、日志、退出码、结构化 backend/runtime/target 证据 | GGUF 加载 |
| GGUF load | 本地文件建立 model/context | hash、metadata、backend 日志 | 生成正确性 |
| 固定短生成 | 同 token 输入与 sampler | tokens、stop reason、usage | 模型整体质量 |
| trace schema | JSONL/CSV 可解析、必填字段齐全 | schema 测试 | trace 无扰动 |
| trace non-interference | trace off/on 的 token 序列一致 | 固定输入对比 | 性能开销合格 |
| CPU Debug | 目标测试 + 可用 sanitizer | 失败为 0 或分类 | CUDA 内存安全 |
| CPU Release benchmark | 预热+多样本 | 原始样本+统计 | server 并发 |
| CUDA | 真实 GPU 正确性与 placement | runtime + profiler 证据 | CPU 成功 |
| server | health、stream、cancel、错误、端口释放 | 脱敏请求/日志 | CLI 成功 |

可逐项勾选的记录见 [[AI/80-实践/04-llama.cpp构建分析与扩展/02-验证清单与记录规范|验证清单与记录规范]]。

## 练习

### 练习 A：只做无网络记录门

1. 把 `experiment-manifest.template.json` 复制到 Vault 外的实验目录；
2. 保持 `status: planned`，运行校验器；
3. 把 `runs.server.host` 改成 `0.0.0.0`，确认校验失败；
4. 恢复 `127.0.0.1`，再把 `status` 改成 `partial` 但不填 commit，确认校验失败。

### 练习 B：CPU 验收

在获准的固定 checkout 中完成 CPU configure/build/test。macOS CPU 基线必须同时显式设置 `GGML_CUDA=OFF` 与 `GGML_METAL=OFF`；还要在该固定 commit 现场枚举实际可用的其他后端选项，记录配置摘要、运行时设备枚举和具体 configured/built/tested targets。后端名称会随 commit 与平台变化，本文不猜测一份永久列表。把这些结构化证据与真实命令、日志引用、退出码写进 Vault 外 manifest，然后运行：

```bash
python3 validate_manifest.py --require-cpu-acceptance /absolute/path/to/manifest.json
```

如果没有本地 GGUF，就停在 `partial`；不得把 GGUF、benchmark、server 或 trace 填成 passed。

### 练习 C：调用链与 trace

1. 完成上文的调用链表；
2. 用 C++ 独立 example 运行一个公开、无隐私的短输入；
3. 保存输入哈希和 token 记录，不保存用户真实提示；
4. 比较 trace off/on token 序列；
5. 将每个耗时字段的起止和同步点写入 manifest；
6. 只有规格、无扰动与性能开销都有证据时，才把 trace 写为 passed。

## 成功标准

- [ ] 源码身份是实际核验的完整 40 位 commit，HEAD 逐字匹配，dirty/patch 状态明确。
- [ ] CPU 配置明确关闭 CUDA 与 Metal，并有固定 commit 的后端选项清单、运行时 CPU 设备证据及 configured/built/tested target 记录；命令、日志和退出码也齐全。
- [ ] CUDA 有真实硬件证据，或被明确标记 `skipped` 并写明理由。
- [ ] GGUF 只在本地使用，来源 revision、SHA-256、metadata/tokenizer 与加载日志可对应。
- [ ] benchmark 区分 load、prefill、decode、TTFT 和 inter-token latency，有预热、原始样本和统计定义。
- [ ] server 只监听 `127.0.0.1`，health、非流式、流式、取消、错误与端口释放均有证据。
- [ ] 真实 commit 的入口、model/context/batch/KV、graph/backend、sampler 和 response 调用链已填写。
- [ ] token 概率标准确阶段，逐步耗时标准确起止和同步点，trace off/on token 序列一致。
- [ ] 独立 example 或精确小补丁可从干净基线应用、构建、测试和反向应用，且默认行为不变。
- [ ] manifest 通过对应阶段的验证模式，且不含模型、真实提示、凭据、私有绝对路径或伪造结果。

## 恢复与清理

1. 先停止 server，确认它只曾监听 loopback，并验证端口已释放。
2. 如果应用过 trace patch，优先在专用 worktree 中用保存的 patch 反向应用，再校验 HEAD 和工作树；不用 `git reset --hard` 或 `git clean`。
3. 只删除已确认为本次实验、且不含源码/模型/唯一日志的 `build-cpu` 或 `build-cuda` 目录。
4. 模型与实验日志分开处理；清理 build 不得顺带删模型。
5. 若要移除专用 worktree，先确认 `git -C "$LLAMA_SRC" status --porcelain` 为空，已把唯一 patch/日志移出 `source/`，再从来源仓库执行 `git -C "$LLAMA_REPOSITORY" worktree remove "$LLAMA_SRC"`。该命令默认会拒绝移除 dirty worktree；不使用 `--force`。
6. 最后记录哪些目录被删除、哪些私有产物仍保留，以及是否存在可恢复 patch。因为从未改变来源 checkout 的分支，不需要猜测或“恢复”它原来的 ref。

如果只想恢复本教学实践，删除本目录新增的 Markdown、JSON 模板和校验器即可；这不会触及仓库外的 llama.cpp checkout 或本地 GGUF。

---

**返回**：[[AI/80-实践/00-AI实践-MOC|AI 实践 MOC]] · **实现原理**：[[AI/20-LLM/50-实现/00-LLM实现-MOC|LLM 实现 MOC]] · **C++ 独立示例**：[[计算机知识/80-实践/03-C++/03-llama.cpp-token概率与耗时trace/README|token 概率与耗时 trace]]
