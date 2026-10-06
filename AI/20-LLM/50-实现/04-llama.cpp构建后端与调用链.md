---
type: lesson
domain: artificial-intelligence
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 180
verified: 2026-09-02
topics:
  - llama.cpp
  - GGUF
  - CPU backend
  - CUDA backend
  - tokenizer
  - sampler
  - server
tags:
  - ai/llm/implementation
---

# llama.cpp：构建、后端与完整调用链

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 构建成功、算子运行和质量/性能复现是不同验收层。保留后端、编译选项、运行输入和基线，避免把某台机器的结果写成通用结论。 深化与验证：[[AI/12-PyTorch/09-性能剖析编译动态形状与内存账本|性能剖析编译动态形状与内存账本]]；[[AI/20-LLM/80-研究拓展/03-从论文主张到可复现实验|从论文主张到可复现实验]]。


## 本课目标

本课把 `llama.cpp` 当作一套**会快速变化的推理系统**，而不是一组可以永久背诵的文件名和命令。完成后，你应当能：

1. 为一次实验固定源码 commit，并记录 CMake、编译器、系统、硬件和日志；
2. 分开验证纯 CPU、CUDA 和 CPU/GPU 混合 offload，而不是只看“命令没有报错”；
3. 从 GGUF 文件加载一直追到 tokenize、decode、sample 和 server 响应；
4. 说清模型权重、KV cache、计算图、临时 buffer 和后端各自在哪里；
5. 用可复现证据比较正确性、首 token 延迟、逐 token 延迟、吞吐和内存，而不是引用别人的单个跑分。

先修连接：[[计算机知识/10-编程语言/02-C++/00-C++-MOC|C++ MOC]]、[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]、[[计算机知识/30-计算机系统/03-ABI调用约定与静态动态链接|ABI、调用约定与静态动态链接]]、[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]。格式与量化的权威课程是 [[AI/20-LLM/60-模型格式与量化/03-GGUF结构转换与验证|GGUF 结构、转换与验证]] 和 [[AI/20-LLM/60-模型格式与量化/05-K-quants-IQ与Q4_K_M|K-quants、IQ 与 Q4_K_M]]。

> [!warning] 本页的实际验证边界
> 主任务在 2026-09-01 做了一个**仓库外的临时源码验收**，固定官方仓库当时的 HEAD：`8887a48f050554f0ee59f56753860c061836b02d`。在 Darwin arm64、AppleClang 21、CMake 4.4.3 上，关闭 Metal 和 CUDA 后端，`llama-cli` 与 `llama-bench` target 构建成功，`test-unicode` 与 `test-sampling` 为 2/2 通过。这里的“构建成功”不等于运行 benchmark：本轮没有下载模型、没有加载/推理、没有性能数字，也没有 CUDA、Metal 或混合 offload 验证。文中的其余命令仍是实验设计模板；快速变化的官方入口统一见 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]。

## 固定 commit 的官方源码核验

2026-09-02 重新打开了官方 `ggml-org/llama.cpp` 中与本页相同的固定 commit，只用下列一手源码确认调用链：

- [`include/llama.h` @ `8887a48f...`](https://github.com/ggml-org/llama.cpp/blob/8887a48f050554f0ee59f56753860c061836b02d/include/llama.h)：公共对象、context/batch 参数、加载、tokenize、decode 与 sampler 声明；
- [`examples/simple/simple.cpp` @ `8887a48f...`](https://github.com/ggml-org/llama.cpp/blob/8887a48f050554f0ee59f56753860c061836b02d/examples/simple/simple.cpp)：同一 commit 下 `backend load → model → vocab/tokenize → context → sampler → prompt batch → llama_decode → sample → one-token batch` 的可定位最小示例。

这一次是**静态源码核对**，不是新的构建或模型运行证据。特别注意：该示例使用 `ggml_backend_load_all()` 加载动态后端，公共头中另有 `llama_backend_init()`；两者不应被模糊地合并成一个“后端初始化”函数。在固定 target 中要追它实际调用哪一条路径。

## 先建立五层系统地图

```text
CLI / benchmark / HTTP server
        │ 参数、请求、prompt、sampling 配置
        ▼
llama 公共接口与运行时对象
        │ model、vocab、context、batch、sampler
        ▼
模型实现与 GGUF 加载
        │ 元数据、张量、聊天模板、tokenizer、KV cache
        ▼
ggml 张量与计算图
        │ op、依赖、view、graph、allocator、scheduler
        ▼
CPU / CUDA / 其他 backend
          buffer、线程、SIMD、kernel、host-device copy
```

这五层不是五个永远不变的目录。判断一个符号属于哪层，要看它的职责：

- **应用层**决定参数、HTTP 协议、输出格式和循环何时停止；
- **llama 层**表达模型、词表、context、batch、decode 与 sampler 语义；
- **加载层**把 GGUF 元数据和张量映射为运行时模型；
- **ggml 层**表达张量、算子 DAG、内存计划和跨后端调度；
- **backend 层**真正持有 buffer 并执行 CPU 或设备 kernel。

## 第一原则：实验必须固定 commit

只写“llama.cpp 最新版”无法复现。源码、CMake 选项、二进制名、CLI 参数、server 路由、GGUF 兼容性和 backend 行为都会改变。一个合格的实验目录应至少保存：

```text
experiment/
├── REVISION.txt          # 完整 40 位 commit、来源 URL、获取日期
├── ENVIRONMENT.md        # OS、内核/容器、编译器、CMake、CPU、RAM、GPU、driver、Toolkit
├── configure-cpu.log     # CPU 配置命令与完整配置摘要
├── build-cpu.log         # 构建日志
├── test-cpu.log          # 测试命令、退出码、失败列表
├── configure-cuda.log
├── build-cuda.log
├── run-cpu.log           # 脱敏后的最小加载/推理日志
├── run-cuda.log
├── bench.jsonl           # 每条记录含 commit、参数、输入摘要和测量定义
└── SHA256SUMS             # 模型与关键输入的摘要；不保存私有 URL/token
```

### 实施时怎样取得可复现 revision

在**你已经获准获取**的工作副本中执行只读确认：

```bash
git status --short --branch
git rev-parse HEAD
git describe --tags --always --dirty
git show -s --format='%H%n%aI%n%s' HEAD
```

记录完整哈希，而不是短哈希；记录 `dirty` 状态。若需要实验补丁，保留“上游基线 commit”和“本地补丁 commit/补丁文件”两个身份。不要先改代码再猜基线。

> [!important] 本轮固定基线与未来复现
> 本轮真实基线是 `8887a48f050554f0ee59f56753860c061836b02d`，不是示例占位，也不表示未来的 HEAD。下文 `<FULL_COMMIT>` 是给下一次实验填写的模板；实施者必须替换为自己现场核验的完整 commit。若要复现本轮，应检出上面的完整哈希，而不是再次使用会漂移的分支名。

### 本轮临时验收记录

|字段|实际记录|能证明什么|仍不能证明什么|
|---|---|---|---|
|source|官方仓库当时 HEAD `8887a48f050554f0ee59f56753860c061836b02d`，核验日 2026-09-01|源码身份已固定|未来 HEAD 或其他 tag 行为相同|
|环境|Darwin arm64；AppleClang 21；CMake 4.4.3；本页未取得精确芯片、RAM、generator、build type 与并行 jobs|这组已知工具链参与了构建|完整硬件复现、Ubuntu、Arch、容器或其他编译器兼容|
|CPU 配置|`GGML_METAL=OFF`、`GGML_CUDA=OFF`|显式排除了两种 GPU backend|其他可选 backend/库全部关闭|
|targets|`llama-cli`、`llama-bench` 构建通过|这两个 target 在该配置可编译链接|CLI 已加载模型；benchmark 已执行|
|tests|`test-unicode`、`test-sampling`：2/2 通过|这两个定向测试通过|全量测试、模型正确性、server 并发|
|运行时后端证据|设备/后端枚举只见 CPU 路径与 Accelerate BLAS|这次没有 Metal/CUDA 执行证据|Linux CPU 路径或任一 GPU/offload 行为|
|server 第一次尝试|关闭 server 的全量构建中，`test-chat` 因缺少 `mtmd.h` 失败|该配置组合存在可复现构建缺口|server 本身一定失败|
|server 定向重试|启用 server 后，`llama-server` 指定 target 构建通过；配置/构建期间临时下载了 llama-ui assets|server target 能在该条件下完成构建|server 已启动、接口正确、离线构建成立|

llama-ui assets 位于临时验收区域，不在 Vault 中；但它是一次真实外部下载副作用，复现实验必须保存 URL/版本或摘要、日志和网络边界，不能把它省略成“纯离线构建”。完整配置/构建命令和外部日志路径没有复制进本笔记；因此本表是**验收摘要**而非独立可重放档案，正式实验仍须按上面的目录契约保存命令、cache 和日志。

## 环境记录：同一命令在三种环境中不是同一实验

### 公共记录字段

```text
source_commit: <FULL_COMMIT>
source_dirty: false | true + patch digest
cmake_version: <cmake --version>
generator: Ninja | Unix Makefiles | ...
c_compiler: <path + version>
cxx_compiler: <path + version>
build_type: Release | RelWithDebInfo | Debug
cmake_cache: <仅保存非敏感的 -L/-LAH 摘要>
os_release: <发行版与版本>
kernel: <host kernel；容器还要记录 image digest>
cpu: <型号、核心/线程、ISA；虚拟机需注明>
ram: <容量；NUMA 拓扑如相关>
gpu: <型号、显存、计算能力>
nvidia_driver: <host 驱动版本>
cuda_toolkit: <nvcc/toolkit 版本；与驱动分开>
model: <来源仓库/revision、文件名、sha256、GGUF 元数据摘要>
run_command: <完整参数，删除私有路径和 token>
```

### Ubuntu 主机

Ubuntu 常用 `apt` 提供编译器、CMake/Ninja 和基础开发包；CUDA Toolkit 的支持矩阵、仓库来源与 host compiler 上限必须按目标 Toolkit 的官方文档复核。不要把 `nvidia-smi` 显示的“CUDA Version”误当作本机 `nvcc` 版本：前者主要反映驱动可支持的 API 上限，后者才是用于编译的 Toolkit。

路径差异常见于：

- 系统编译器通常位于 `/usr/bin`，另装版本可能通过 alternatives 或显式 `CC`/`CXX` 选择；
- CUDA Toolkit 可能在 `/usr/local/cuda-*`，也可能来自发行版或容器；不得假定固定路径；
- 动态库搜索由链接器、RPATH/RUNPATH、`ldconfig` 与运行环境共同决定，不能只靠交互式 shell 的 `PATH`。

### Arch Linux 主机

Arch 是滚动发行版，编译器、glibc、CMake 和 CUDA 包可能比某个 llama.cpp commit 的测试矩阵更新。记录精确包版本比只写“Arch”重要：

- 使用 `pacman -Q` 记录直接相关包；不要把整台机器的包清单公开；
- 若 CUDA 对 host compiler 有版本上限，选择受支持工具链并显式记录，不要全局替换系统编译器；
- 包安装位置通常遵循 `/usr` 前缀，和 NVIDIA 官方 runfile 的 `/usr/local/cuda-*` 布局不同；
- 滚动升级前后的结果不能合并成同一基线。

### NVIDIA 容器

容器解决的是用户态环境固定，不会把 GPU 内核驱动装进容器。可复现实验必须同时记录：

- image **digest**，不要只写会漂移的 tag；
- host 驱动、GPU 和设备注入方式；
- 容器内 Toolkit、编译器和 CMake；
- 挂载的源码、模型和输出目录；
- 是否限制 CPU、内存、共享内存、GPU 设备和网络；
- 容器 UID/GID，避免生成只能由 root 删除的构建产物。

```text
host kernel + NVIDIA driver + physical GPU
                 │ device/capability injection
                 ▼
container: compiler + CUDA userspace + llama.cpp build + model mount
```

同一个 image 在两台 host 上不一定等价，因为 host 驱动、GPU 架构、功耗/频率、CPU、NUMA 和挂载文件系统仍不同。进一步阅读 [[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]]。

## 构建：先让配置输出成为证据

配置、编译、链接与启动失败的分层判定见 [[计算机知识/10-编程语言/02-C++/01-编译链接与CMake|编译、链接与 CMake]]；先固定失败发生的阶段，再判断它是否与 llama.cpp 的后端或模型有关。

以下命令只展示“隔离 build 目录 + 显式选项 + 保存日志”的形状。`GGML_CUDA`、target 名和其他选项必须在固定 commit 中查证，不能从本页直接认定存在。

### 发现当前 commit 的选项与 target

```bash
cmake -S . -B build-discovery -DCMAKE_BUILD_TYPE=Release
cmake -LAH -N build-discovery
cmake --build build-discovery --target help
ctest --test-dir build-discovery --show-only
```

检查配置摘要中实际启用的 backend、编译器、架构/ISA、依赖和警告。只看 shell 退出码不够；CMake 可能在找不到可选依赖时自动降级。

### 纯 CPU 基线

```bash
cmake -S . -B build-cpu \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=OFF \
  -DGGML_METAL=OFF
cmake --build build-cpu --config Release -j <JOBS>
ctest --test-dir build-cpu --output-on-failure
```

实施时补充决定可移植性和性能的选项：是否为本机 ISA 优化、是否启用外部 BLAS、线程后端、动态或静态链接等。不要为了跑分快而在未说明的情况下编译成本机专用二进制；也不要假设启用 BLAS 会改善 decode 阶段，收益取决于矩阵形状、批量和具体路径。

CPU 验证证据至少包含：

- 配置摘要明确没有 CUDA backend；
- 运行日志列出实际 CPU/ISA/线程信息（字段名以 commit 为准）；
- GPU 监控没有该进程的显存占用或 kernel；
- 同一固定输入的 token 序列或概率检查符合预期容差；
- benchmark 明确区分 prompt processing 与 token generation。

本轮只满足其中的“配置/target 构建”和两个定向测试：`llama-bench` **只构建、未运行**；因为没有模型，也没有 token 序列、概率、内存或吞吐证据。`GGML_METAL=OFF` 是在 macOS 上建立纯 CPU 基线所必需的显式边界；Ubuntu/Arch 没有 Metal，但仍要按各自固定 commit 的配置摘要关闭所有不希望参与比较的加速后端。

### CUDA 构建

```bash
cmake -S . -B build-cuda \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON
cmake --build build-cuda --config Release -j <JOBS>
ctest --test-dir build-cuda --output-on-failure
```

需要记录 CUDA 架构选择、是否编译多个架构、Toolkit 与 host compiler。配置成功不代表设备路径已运行；至少再验证：

1. 运行时枚举到期望 GPU；
2. 日志确认 CUDA backend 被加载；
3. 模型层或张量确实 offload；
4. GPU 显存增加并出现计算活动；
5. 输出正确性/概率差异在已定义容差内；
6. 没有因 OOM 或不支持算子悄悄退回一个你未记录的路径。

### Debug 与可诊断构建

Release 用于最终性能基线；源码阅读和错误定位另建目录：

```bash
cmake -S . -B build-debug \
  -DCMAKE_BUILD_TYPE=Debug \
  -DGGML_CUDA=OFF \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build-debug -j <JOBS>
ctest --test-dir build-debug --output-on-failure
```

Sanitizer、额外断言和日志选项应从该 commit 的 CMake 定义中现场找出。CPU 的 AddressSanitizer/UndefinedBehaviorSanitizer 结果不能证明 CUDA kernel 内存安全；GPU 路径需要对应设备工具和同步后的错误检查。

## 从 GGUF 文件到运行时模型

[[AI/20-LLM/60-模型格式与量化/03-GGUF结构转换与验证|GGUF]] 是容器格式；`Q4_K_M` 是整模型的混合量化预设，具体张量的数值存储由 tensor info 中的 `Q4_K`、`Q6_K` 等实际 type 描述，详见 [[AI/20-LLM/60-模型格式与量化/05-K-quants-IQ与Q4_K_M|K-quants、IQ 与 Q4_K_M]]。容器、预设和张量 type 都不是模型身份或可信来源的证明。

### 加载阶段的概念顺序

```text
打开文件 / 分片
  → 检查 GGUF 结构、版本与范围
  → 读取 metadata：architecture、超参数、tokenizer、chat template 等
  → 建立运行时模型和词表
  → 读取张量目录：name、shape、type、offset
  → 为各 backend 规划 buffer / 映射文件页
  → 把张量加载、映射或上传到目标 buffer
  → 创建 context、KV cache 与计算工作区
```

实施时分别保存四类证据：

|证据|能证明什么|不能证明什么|
|---|---|---|
|来源仓库、revision、文件 SHA-256|你使用了哪组字节|权重无后门、许可自动满足|
|GGUF 元数据与张量目录|格式可解析、架构/tokenizer 声明与张量布局|每个张量数值正确|
|最小加载日志|该 commit 能在该环境建立模型对象|推理质量、长上下文、服务稳定|
|固定 prompt 的 token/probability 记录|该路径在固定参数下可比较|跨硬件逐位相同、模型整体能力|

### 内存映射不是“模型已全部进 RAM”

文件映射把文件页映射进进程虚拟地址空间；页可能按需进入 page cache/RSS。GPU offload 又可能把选定权重复制到 VRAM。要分别观察：

- 文件大小与映射区；
- 进程虚拟内存、RSS/PSS 与 page fault；
- 锁页或 staging 内存（如有）；
- GPU 已分配/保留显存；
- KV cache 与计算 buffer。

这也是为什么“GGUF 是 4 GB”不能直接推出“只需 4 GB 内存”。系统概念见 [[计算机知识/30-计算机系统/02-进程虚拟地址空间与内存映射|进程虚拟地址空间与内存映射]]。

## Tokenizer：字符串不是直接进入模型

tokenizer 通常由 GGUF 中的词表与相关元数据驱动；聊天模型还可能需要 chat template 把角色消息渲染为实际文本/token 序列。完整检查顺序是：

1. 确认模型与 tokenizer 来自同一已固定 revision/转换产物；
2. 明确输入是 raw prompt 还是结构化 chat messages；
3. 记录是否应用 chat template、模板来源和 BOS/EOS 等 special-token 策略；
4. tokenize 后保存 token ID、可显示 piece 和总 token 数；
5. detokenize 时处理字节片段、Unicode 边界和 special token，不假设“一 token 等于一个字符/单词”。

边界测试至少覆盖：空串、ASCII、中文、emoji、组合字符、换行、前导空格、包含 special-token 字面文本的输入和超过 context 的输入。原理连接 [[AI/20-LLM/10-原理/01-文本Unicode-Token与词表|文本、Unicode、token 与词表]]。

## 完整调用链：load → tokenize → decode → sample → response

下表给出稳定职责与常见 API 名的**检索起点**。其中列出的主要名称已在上述固定 commit 核对，但不是对任意 commit 的保证；必须在实验源码中确认声明、调用者和所有权。

|阶段|常见检索起点|输入|输出/状态|最容易漏掉的证据|
|---|---|---|---|---|
|初始化/加载 backend|`llama_backend_init`、`ggml_backend_load_all` 等起点|进程/设备配置|可用 backend 与设备|实际 target 调用哪个，动态 backend 真正加载了哪些|
|加载模型|`llama_model_load_from_file` 一类入口|GGUF 路径、模型参数|model、vocab、权重 buffer|commit、文件哈希、offload 计划|
|创建 context|`llama_init_from_model` 一类入口|model、context 参数|context、KV cache、工作区|context/batch/sequence 参数与内存|
|渲染聊天输入|chat template 相关符号|messages、template|rendered prompt|模板来源和 special token|
|tokenize|`llama_tokenize` 一类入口|vocab、文本、BOS/special 策略|token IDs|Unicode、长度与截断策略|
|准备 batch|batch/sequence API|token IDs、positions、seq IDs|一次 prefill/decode 输入|哪些位置请求 logits|
|decode/eval|`llama_decode` 一类入口|context、batch|更新 KV cache；产生 logits/embeddings|prefill 与单 token decode 的时序|
|取得 logits|logits getter 一类入口|context、batch row|词表长度的分数|取的是哪个 token/sequence|
|sample|`llama_sampler_*` 一类入口|logits、采样链状态|chosen token|seed、温度、top-k/p 等顺序|
|接受 token|sampler accept 一类入口|chosen token|更新 repetition 等状态|采样器状态何时更新|
|detokenize|token-to-piece 一类入口|token ID|字节片段/文本|UTF-8 不完整片段与 special token|
|停止|EOS/stop/length/cancel|生成状态|终止原因|区分模型 EOS、用户 stop、长度和错误|
|server 响应|HTTP/streaming 层|token/piece、usage、错误|JSON 或 SSE 等响应|断连、取消、backpressure、最终 usage|

### Prefill 与 decode 是同一 API 的不同工作形状

- **prefill** 通常把一批 prompt token 送入 context，建立 KV cache；吞吐受大矩阵、batch 和内存带宽影响；
- **decode** 通常每轮为每个活跃序列处理一个或少量新 token；关注单步延迟和 KV cache 访问；
- “调用一次 decode”不等于“生成一个 token”：是否产出 logits、哪些 batch row 产出 logits、是否有多个 sequence，都由 batch 配置决定。

> [!warning] 示例 helper 不等于长期 API 方向
> 固定 commit 的 `simple.cpp` 使用 `llama_batch_get_one`，但同 commit 的公共头明确把它标为过渡 helper，并提示避免在新设计中依赖。教学时可用它读懂最小时序；要实现多 sequence、自定义 position 或精确 logits row 时，应从当前 commit 的 batch 结构/构造 API 重新设计，不要盲抄示例。

### 一次生成循环的语言无关伪代码

> [!note] 这是不可编译伪代码
> 它只表达职责和测量边界，不声称匹配任何真实头文件或函数签名。

```text
revision = require_full_commit_from_experiment_manifest()
backend  = initialize_requested_backends()
model    = load_pinned_gguf(model_path, expected_sha256, model_params)
context  = create_context(model, context_params)
sampler  = build_sampler_chain(seed, temperature, top_k, top_p, ...)

rendered_prompt = render_chat_template_if_requested(messages)
tokens = tokenize(model.vocab, rendered_prompt, special_token_policy)

time_span("prefill"):
    batch = make_batch(tokens, positions, sequence_id, logits_on_last_row=true)
    require_ok(decode(context, batch))

repeat until stop:
    logits = get_logits_for_requested_row(context)
    token  = sample(sampler, logits)
    accept(sampler, token)
    piece  = detokenize_one_token_with_utf8_buffering(model.vocab, token)
    emit_piece(piece)

    if eos_or_stop_or_cancel_or_limit(token, emitted_text): break

    time_span("decode_step"):
        batch = make_one_token_batch(token, next_position, sequence_id)
        require_ok(decode(context, batch))

finalize_response_with_usage_and_stop_reason()
```

一个常见时序陷阱是把“本轮采样出的 token”送进下一次 decode 后，才产生“再下一个 token”的 logits。画出 position、KV cache 与 logits 所属 token，能避免 off-by-one。

## Sampler：logits 到 token 的决策链

logits 是未归一化分数。sampler chain 可能依次做惩罚、温度缩放、候选裁剪、归一化和随机抽样；**顺序会改变结果**。实施记录必须包括：

- 所有采样器及其顺序；
- seed 以及随机状态是否按 request 独立；
- temperature、top-k、top-p、min-p、penalty 等当前 commit 支持的精确参数；
- greedy 是否通过独立 sampler 实现；
- sampler 接受历史 token 的时机；
- server 默认值是否和 CLI 默认值相同。

为了调试，可以对选定步记录 top-N token：`token_id`、转义后的 piece、原始 logit、经采样链处理后的概率和是否被选中。不要默认记录完整词表，也不要把真实私密 prompt/response 写入日志。

数值上应使用稳定 softmax：先减去候选中的最大 logit，再指数化和归一化。概率日志只用于解释该步决策；它不是模型置信度或事实正确率。数学连接 [[数学/50-信息论/02-指数对数Softmax与LogSumExp|Softmax 与 LogSumExp]]。

## CPU、CUDA 与混合 offload

### 三种模式不是简单的“慢、中、快”

|模式|权重/计算位置|主要成本|必须收集的证据|
|---|---|---|---|
|CPU-only|权重映射/驻留在 host；算子走 CPU backend|CPU SIMD、线程、内存带宽、NUMA|backend 列表、线程/ISA、GPU 无活动、RSS、prompt/decode 指标|
|尽量 CUDA|大量权重/算子在 GPU；仍有 host 控制与可能的 CPU 工作|VRAM、kernel、同步、剩余 CPU op|offload 数量、tensor placement、VRAM、GPU timeline、fallback|
|混合 offload|一部分层/张量在 GPU，其余留 CPU|跨后端切分、拷贝、同步、两侧带宽|每层/张量 backend、跨 backend copy、CPU/GPU 利用率、稳定态延迟|

层 offload 的 CLI 参数名、单位和“0/最大值”的含义可能变化，常见的 `-ngl`/`--n-gpu-layers` 只能作为固定 commit 中的搜索线索，不能脱离 `--help` 复制。某些小张量、输出层、KV cache 或算子可能有独立 placement 选项；“offload N 层”也不保证所有计算都在 GPU。

### 证明混合 offload 的证据链

1. 保存固定 commit 下目标二进制的 `--help`，确认选项语义；
2. 配置日志证明 CPU 和 CUDA backend 都被构建/加载；
3. 模型加载日志显示 offload 的层/张量数量和目标设备；具体文本以 commit 为准；
4. 在加载前后采集 host RSS/PSS 与 GPU 显存；
5. 生成期间同时观察 CPU 线程与 GPU kernel/利用率；
6. 若调试日志可输出 tensor placement，保存名称、shape、type、backend；
7. 与 CPU-only 和另一 offload 配置使用同一模型哈希、prompt tokens、sampler 和上下文；
8. 报告失败或 fallback，不筛掉较慢样本。

只有 `nvidia-smi` 中出现显存占用，最多说明进程申请了 VRAM；只有日志写了“CUDA”，最多说明 backend 可用。二者加上 placement、kernel 活动和端到端结果，才形成较完整证据。

## CLI、server 与 benchmark 的责任边界

### CLI 冒烟

CLI 适合验证单请求的加载、tokenization、decode、sampling 和输出。固定一个**无隐私、小而明确**的 prompt，并记录：

- 完整参数与默认值快照；
- prompt 经模板后文本的安全摘要和 token IDs；
- seed 与采样链；
- stop reason、输出 token 数；
- load、prefill、每步 decode/sample 和总耗时。

本轮 `llama-cli` 仅完成 target 构建。没有模型就没有 CLI 冒烟结果；不能把“二进制生成”写成“调用链已运行”。

### Server 冒烟

server 还增加网络与并发状态：请求解析、模板、队列、slot/sequence、取消、streaming、usage、超时和 backpressure。建议只绑定 loopback，使用非敏感测试输入，不在课程中写 API key。验证：

1. `/health` 或当前 commit 提供的等价健康语义；
2. 一个非流式请求的状态码、schema、usage 和 stop reason；
3. 一个流式请求能按协议结束，并在断连时取消后端工作；
4. 非法参数、超长输入和模型错误返回稳定错误，不泄露绝对路径/内部栈；
5. 两个并发请求不会共享 sampler 随机状态或混淆 sequence/KV cache；
6. 进程退出后端口释放、子线程结束、资源回收。

server 的 OpenAI 风格接口是兼容层，不应假定与任一云 API 在全部字段、流式事件、错误或 tokenizer 计数上逐字一致。路由和 schema 必须从固定 commit 的文档与测试确认。

本轮 server 证据是“失败被保留、定向 target 后续能构建”：第一次在 server 关闭的配置做全量构建时，`test-chat` 因缺少 `mtmd.h` 失败；随后启用 server，指定 `llama-server` target 构建成功，并发生 llama-ui assets 的临时下载。没有启动 server、绑定端口或发送 HTTP 请求，因此上面的六项 server 冒烟仍全部未验证。这个差异还提示：全量默认构建、指定 target 构建和实际服务验收是三层不同证据。

### Benchmark 不是随手跑一次

固定 commit 中常见 `llama-bench` 一类工具，但 target 与参数必须现场查证。至少把测量分成：

- **加载时间**：冷 page cache 与热 cache 分开；
- **prompt processing/prefill**：固定 prompt token 数与 batch；
- **token generation/decode**：固定生成 token 数、并发/sequence 数；
- **time to first token**：包含或排除加载必须写清；
- **inter-token latency**：报告分布，不只平均值；
- **内存**：host RSS/PSS、VRAM、KV cache 配置；
- **能耗/频率条件**：如参与比较，记录功耗限制、温度与稳定态。

先做预热，保存每次独立样本，报告中位数和离散程度；CPU/GPU 混合比较必须使用同一输入 token 数，而不是同一可见字符串但不同 chat template。

本轮 `llama-bench` 只有构建证据，没有执行证据；因此没有 load、prefill、decode、TTFT、内存或能耗数据。

## 一份可直接填的实验清单

### A. 身份与环境

- [ ] `source_commit` 是完整哈希，并记录 dirty/patch 状态。
- [ ] 模型仓库 revision、GGUF 文件名和 SHA-256 已记录。
- [ ] OS、容器 digest、编译器、CMake、CPU/RAM 已记录。
- [ ] 若用 CUDA，host driver、Toolkit、GPU/显存/计算能力已分别记录。

### B. 构建

- [ ] CPU 和 CUDA 使用不同 build 目录。
- [ ] 保存 CMake 配置摘要、cache 中相关选项和 target 列表。
- [ ] 保存 build/test 命令、退出码和失败项。
- [ ] Release 用于性能；Debug/诊断构建用于调试。

### C. 加载与调用链

- [ ] GGUF 元数据、张量目录和 tokenizer/chat template 已核对。
- [ ] 记录 model/context/batch/KV cache 的关键参数。
- [ ] token IDs、positions、sequence IDs 与 logits row 可追踪。
- [ ] sampler 顺序、参数、seed 与 stop reason 可追踪。

### D. 后端与性能

- [ ] CPU-only、CUDA/mixed 的 backend 和 tensor placement 有日志证据。
- [ ] host memory、VRAM、GPU kernel 和 fallback 有证据。
- [ ] prefill、decode、sample、server serialization 分开计时。
- [ ] 比较使用相同 commit、模型哈希、token 输入和测量定义。

## 练习：设计三组不下载模型也能评审的实验

### 练习 1：写 revision manifest

新建一个**仓库外的临时实验目录**，先只写字段模板，不填假值。让同伴检查：缺少任一 commit、编译器、硬件、模型 hash 或命令字段时，是否会误把两个环境当成同一实验。

### 练习 2：纸上判断 offload 证据

对以下三条分别判定“能证明什么”：

1. 日志显示发现 CUDA 设备；
2. `nvidia-smi` 显示 3 GiB 显存；
3. placement 日志显示选定张量在 CUDA buffer，profile 出现相应 kernel，输出也通过固定检查。

正确结论应是：前两条都是局部证据，第三条才接近“计算确实 offload”的完整链条，但仍不自动证明性能更优或全部算子在 GPU。

### 练习 3：画一个 token 的时序

从 prompt 最后一个 token 开始，画出：prefill 产生 logits → sampler 选择 token A → 输出 A → decode A 更新 KV 并产生下一组 logits → 选择 token B。标出每一步的 position、sequence、logits row 和计时边界。

## 成功标准

- [ ] 我能解释 Ubuntu、Arch 和容器分别需要记录哪些不同证据。
- [ ] 我不会把 driver、Toolkit、容器 CUDA 或 Python 框架 runtime 混为一谈。
- [ ] 我能从 GGUF metadata/tensors 追到 model、context、batch、graph、backend 和 sampler。
- [ ] 我能用 placement、显存和 kernel 活动共同证明混合 offload，而不是只引用一行日志。
- [ ] 我能解释 prefill 与 decode、logits 与概率、token 与文本片段的边界。
- [ ] 我能把“target 构建”“定向测试”“模型推理”“server 请求”和“benchmark”分成五层证据。
- [ ] 没有真实 commit/源码/日志时，我会写“未实际构建”，不会补一个看似可信的结果。

## 恢复与清理

- 构建产物应全部位于精确的 `build-*` 目录；确认目录无源码、模型和唯一日志后，才能删除并重新配置。
- 模型文件、实验日志和源码工作副本应分开；清理 build 不应删除模型，清理模型缓存也不应由构建脚本顺带执行。
- server 实验结束后主动停止进程并验证 loopback 端口已释放；不要为了方便绑定公网地址。
- 若实验修改源码，恢复优先使用独立 branch/worktree 或反向应用已保存补丁；不要用 `git reset --hard` 或 `git clean` 清理含有未知工作成果的目录。
- 本页在 Vault 内只新增教学文档；主任务的临时源码、build 与 llama-ui assets 位于 Vault 外。没有下载模型、推理、开端口或安装系统软件。恢复本文只需删除或用 Git 还原这一 Markdown 文件；清理外部临时验收区前必须先解析其精确路径并保留需要的日志，不能用宽泛递归清理命令。

---

**上一站**：[[AI/20-LLM/50-实现/03-训练循环Generation与KV-Cache实现|训练循环、Generation 与 KV Cache]] · **下一站**：[[AI/20-LLM/50-实现/05-llama.cpp源码阅读与小型扩展|llama.cpp 源码阅读与小型扩展]] · **深入内存与调度**：[[AI/20-LLM/50-实现/06-GGML张量计算图分配器与Backend|GGML 张量、计算图、分配器与 Backend]] · **返回**：[[AI/20-LLM/50-实现/00-LLM实现-MOC|LLM 实现 MOC]]
