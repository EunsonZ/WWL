---
type: lesson
domain: artificial-intelligence
stage: 5
status: ready
difficulty: 深入
estimated_minutes: 210
verified: 2026-09-02
topics:
  - llama.cpp
  - source reading
  - call trace
  - debugging
  - profiling
  - extension
tags:
  - ai/llm/implementation
---

# llama.cpp：源码阅读、调用链 Trace 与小型扩展

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 小改动应有可失败的回归测试和清晰计时范围。先证明输出语义，再分析拷贝、分配与算子瓶颈，避免因编译通过而跳过正确性。 深化与验证：[[AI/12-PyTorch/06-梯度诊断数值验证与自定义算子|梯度诊断数值验证与自定义算子]]；[[AI/12-PyTorch/09-性能剖析编译动态形状与内存账本|性能剖析编译动态形状与内存账本]]。


## 本课目标

本课不要求记住某一版 `llama.cpp` 的目录树。目标是学会在一个**已固定 commit** 中建立证据链：

```text
请求/命令行入口
  → 模型和 context 的所有者
  → prompt 模板与 tokenize
  → batch、position、sequence 与 decode
  → ggml graph、allocator、backend scheduler
  → logits、sampler、token piece
  → CLI 输出或 server 流式响应
```

你还会设计一个不污染主路径的最小 trace 例：逐步记录 token 概率、prefill/decode/sample/detokenize/发送耗时，并用固定输入和测试约束一处小改动。

先修：[[AI/20-LLM/50-实现/04-llama.cpp构建后端与调用链|llama.cpp 构建、后端与调用链]]、[[AI/20-LLM/50-实现/06-GGML张量计算图分配器与Backend|GGML 张量、计算图、分配器与 Backend]]、[[计算机知识/10-编程语言/02-C++/00-C++-MOC|C++ MOC]]、[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]、[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]。读取模型格式和量化实现前，先读 [[AI/20-LLM/60-模型格式与量化/03-GGUF结构转换与验证|GGUF 结构、转换与验证]] 与 [[AI/20-LLM/60-模型格式与量化/05-K-quants-IQ与Q4_K_M|K-quants、IQ 与 Q4_K_M]]。

> [!warning] 本轮固定了构建基线，但没有完成源码级 trace
> 主任务在 2026-09-01 固定并临时构建了官方 commit `8887a48f050554f0ee59f56753860c061836b02d`；CPU-only 的 `llama-cli`、`llama-bench` target 和两个定向测试结果见 [[AI/20-LLM/50-实现/04-llama.cpp构建后端与调用链#本轮临时验收记录|本轮临时验收记录]]。本页没有据此完成真实函数/文件/行号的逐层源码核验，也没有实现或运行 trace example。下面的 API 名仍只用于实施时检索；伪代码和伪补丁都明确不可编译，不能冒充真实外部源码。未来刷新从 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 进入上游，并重新固定 commit。
>
> 2026-09-02 又对同一 commit 的官方 [`include/llama.h`](https://github.com/ggml-org/llama.cpp/blob/8887a48f050554f0ee59f56753860c061836b02d/include/llama.h) 和 [`examples/simple/simple.cpp`](https://github.com/ggml-org/llama.cpp/blob/8887a48f050554f0ee59f56753860c061836b02d/examples/simple/simple.cpp) 做了静态核对，确认公共对象与最小生成时序的课程起点。这不等于已追踪 CLI/server 内部调用者，也没有新增编译、运行或 trace 证据。

## 阅读前先冻结事实

### 最小源码身份证

```text
upstream_url: <official repository URL>
base_commit: <full 40-character commit>
base_commit_date: <author/committer date as recorded>
working_tree: clean | dirty
local_patch_sha256: <if dirty>
build_dir: <isolated path>
build_type: RelWithDebInfo | Debug
cmake_options: <complete explicit list>
compiler: <path + version>
host: <OS/kernel/CPU/RAM>
accelerator: <GPU/driver/Toolkit or none>
model: <repository revision + GGUF filename + SHA-256>
```

若没有 `base_commit`，最多只能画概念图，不能写“函数 A 在文件 B 调用函数 C”。若工作树不干净，必须保存补丁摘要，避免把本地改动误读成上游设计。

### 为阅读准备两个构建目录

- `build-relwithdebinfo`：接近优化路径但保留符号，用于正常 trace 和性能观察；
- `build-debug`：断言、单步、sanitizer 和错误复现；
- CPU 与 CUDA 再分开，避免 CMake cache 残留造成“以为切了后端，实际没有”。

`CMAKE_EXPORT_COMPILE_COMMANDS=ON` 能帮助编辑器和静态检索理解真实 include、宏和编译选项。是否有项目自带的 debug/log/sanitizer 选项，必须从所选 commit 的 CMake 文件与配置摘要确认。

## 不要先读 kernel：用“三次收敛”建立仓库地图

### 第一次：从产物回到 target

先让 CMake 告诉你当前 commit 真正有哪些 target：

```bash
cmake -S . -B build-map -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build-map --target help
ctest --test-dir build-map --show-only
```

从目标二进制的 CMake target 追到源文件清单和链接依赖。不要只按文件名猜“这个一定是 server”。记录：target、入口 translation unit、直接链接库、编译宏、条件 backend。

### 第二次：从公共 API 的声明到调用者

先搜索当前源码实际存在的符号，再打开声明与所有调用者：

```bash
rg -n 'llama_backend_init|llama_model_load|llama_init_from_model' .
rg -n 'llama_tokenize|llama_decode|llama_get_logits' .
rg -n 'llama_sampler_|token_to_piece|chat.*template' .
rg -n 'ggml_backend|gallocr|graph_compute|sched' .
```

这些模式不是 API 承诺；搜索无结果时应根据头文件和入口调用更新关键词，而不是把旧名字写进代码。每个符号只记录五件事：

1. 定义在哪个层；
2. 谁拥有输入对象；
3. 返回/错误如何表达；
4. 是否改变 context、KV cache、sampler 或 buffer；
5. 哪个测试能触达它。

### 第三次：用一个实际请求缩小路径

选择一个无隐私的短 prompt、固定 seed、固定 context/batch 和固定生成长度，只追踪一次请求。不要同时追 embeddings、reranking、多模态、并发、多 GPU 等所有分支。先回答：

- 输入是 raw completion 还是 chat messages？
- chat template 在哪里应用？
- tokenize 后的 token IDs 是什么？
- prefill 是一个 batch 还是多个 chunk？
- 哪些 batch row 请求 logits？
- sampler chain 的顺序是什么？
- 新 token 何时写入 KV cache、何时发给客户端？
- 取消/错误怎样穿过队列和后台线程？

## 一张可以逐格填证据的调用链表

|层/阶段|当前 commit 的实际符号|关键输入|产生或修改|所有者/生命周期|错误与取消|测试/trace 证据|
|---|---|---|---|---|---|---|
|CLI/server 解析|待填|argv/HTTP JSON|运行参数/request state|应用层|参数错误/断连|固定请求与 schema|
|模板渲染|待填|messages/template|rendered prompt|request|模板/角色错误|渲染文本摘要|
|模型加载|待填|GGUF/model params|model/vocab/buffers|进程或共享模型|格式/内存/backend|哈希、metadata、placement|
|context 建立|待填|model/context params|context/KV/workspace|slot/sequence 池|容量/分配|内存与参数日志|
|tokenize|待填|vocab/text/policy|token vector|request|超长/编码边界|ID 与 piece|
|batch 构造|待填|tokens/pos/seq|batch rows|request/worker|shape/position|逐 row 摘要|
|decode|待填|context/batch|KV + logits|context|backend failure/cancel|prefill/decode span|
|graph 构建|待填|model tensors/KV/input|ggml graph|一次计算或缓存|shape/op/backend|op/placement 摘要|
|graph 分配与执行|待填|graph/scheduler|buffer reuse/results|backend/context|OOM/kernel/copy|allocation/compute span|
|采样|待填|logits/chain state|chosen token|request sampler|空候选/数值异常|top-N 概率|
|detokenize|待填|vocab/token|bytes/text|stream buffer|UTF-8/special|escaped piece|
|响应|待填|piece/usage/stop|JSON/SSE bytes|connection|backpressure/disconnect|send span + final event|

“待填”必须来自所选 commit，而不是从博客抄来。表中如果出现不知道的所有权，就是下一次阅读的优先问题。

## 沿对象所有权读，而不是只沿函数名读

### Model 与 vocab

模型对象通常持有架构超参数、词表/Tokenizer 语义、权重张量及其 backend buffer 关系。重点确认：

- 多个 context 是否共享同一个 model/权重；
- 文件映射与 backend buffer 谁先销毁；
- tokenizer/chat template 元数据属于 model 还是 request；
- GPU offload 后 host 映射是否仍保留；
- model 销毁是否等待异步 backend 工作结束。

### Context、KV cache 与 sequence

context 是可变推理状态，不应等同于 model。沿源码确认：

- context size、batch size、micro-batch、并发 sequence 怎样约束内存；
- KV cache 如何索引 position/sequence；
- prefill 和 decode 如何复用/更新 cache；
- server slot 重用时，旧 sequence 状态怎样清除；
- 取消请求是否只停止发送，还是也停止后端计算并释放 slot。

### Batch

batch 不只是 `vector<token>`。它还可能携带 embedding、position、sequence ID、每行是否需要 logits 等信息。trace 至少打印：row index、token/embedding mode、position、sequence IDs 和 logits flag。这样才能解释为何 logits getter 指向某一行。

在上述固定 commit 中，公共头还明确区分 `n_batch` 的逻辑最大 batch 与 `n_ubatch` 的物理 micro-batch，并说明 `llama_batch` 可包含一个或多个 sequence。因此阅读时应同时记录 `batch.n_tokens`、sequence 数、logits rows 和实际 micro-batch 切分；单写“batch size”无法还原工作形状。

### Sampler

sampler 通常有自己的随机状态和 token 历史。服务端并发时应确认每个 request/sequence 的 sampler 是否隔离，什么时候 reset、clone 或 accept token，错误重试会不会重复消耗 RNG。

## 从 decode 继续追到 ggml 和 backend

阅读 `decode/eval` 时，对每个跨层调用问四个问题：

```text
1. 此时只有“张量描述与 op”，还是已经分配真实 buffer？
2. graph 是每步新建、复用结构，还是部分缓存？
3. scheduler 根据什么把 op/张量放到 CPU 或 CUDA？
4. 哪个同步点保证 logits 在 host 读取时已经就绪？
```

遇到 `view`、stride、quantized type 或跨 backend copy 时，不要把 `tensor->data` 当作总能由 CPU 直接解引用的普通数组。完整概念见 [[AI/20-LLM/50-实现/06-GGML张量计算图分配器与Backend|GGML 张量、计算图、分配器与 Backend]]。

## 设计一个不污染主路径的最小 Trace Example

### 为什么优先独立 example

调用链学习首先需要“可删除、默认不启用、不会改变 server 正常输出”的观测点。独立 example 的优势：

- 不改变公共 API、GGUF 格式和默认日志；
- 固定单请求、单 sequence，减少并发噪声；
- 可以单独构建和测试；
- 删除 target 和单一源文件即可恢复；
- 若 API 演进，失败集中在示例边界，而不是污染核心热路径。

在固定 commit 中先找官方最小 example 和 target 命名约定；新文件名、链接库、初始化/释放 API 都必须从当前源码确定。

### Trace 输出契约

建议 JSON Lines，每行一个事件，时间用单调时钟相对 request 起点；不要把真实 prompt、模型绝对路径或访问凭据写入日志。

```json
{"schema":"llama-trace-v1","event":"request_start","request_id":"local-0001","source_commit":"<FULL_COMMIT>","model_sha256":"<SHA256>","seed":42}
{"event":"tokenize_end","elapsed_us":120,"token_count":7,"token_ids":[1,314,159,265,3,5,9]}
{"event":"prefill_end","step":0,"input_tokens":7,"elapsed_us":18340}
{"event":"sample","step":0,"elapsed_us":91,"chosen":{"id":42,"probability":0.37},"top":[{"id":42,"probability":0.37},{"id":17,"probability":0.21}]}
{"event":"piece_ready","step":0,"elapsed_us":8,"bytes":6}
{"event":"decode_end","step":0,"input_token":42,"position":7,"elapsed_us":4280}
{"event":"sample","step":1,"elapsed_us":87,"chosen":{"id":99,"probability":0.44},"top":[{"id":99,"probability":0.44},{"id":7,"probability":0.19}]}
{"event":"piece_ready","step":1,"elapsed_us":7,"bytes":6}
{"event":"request_end","stop_reason":"length","generated_tokens":2,"total_elapsed_us":27420}
```

上面的数字和 token **只是 schema 示例，不是任何模型的真实输出或性能结果**。`sample` 先只记录 token 决策；detokenize/UTF-8 缓冲完成后才记录 `piece_ready`。当前 token 可见后，只有仍需继续生成时才把它送入 `decode` 以产生下一 token 的 logits；达到 EOS、stop、取消或长度上限后不得为了 trace 多做一次无消费者的 decode。真实 trace 要额外记录：build identity、后端 placement 摘要、context/batch 配置、sampler chain、是否预热和计时定义。

### 概率到底记录哪一种

“token 概率”必须写清阶段：

1. `raw_logit`：模型原始输出；
2. `post-penalty logit`：重复/频率等处理后；
3. `candidate probability`：温度和候选过滤后，在保留候选中归一化；
4. `chosen probability`：实际抽样分布中被选 token 的概率。

如果只记录 sampler 最终候选概率，就把字段命名为 `sampling_probability`，不要写成模型“确信程度”。过滤掉的 token 最终抽样概率可能为零，即使 raw logit 很高。

对候选集合做稳定 softmax 的语言无关算法：

```text
max_logit = max(candidate.logit)
weight_i  = exp(candidate.logit - max_logit)
prob_i    = weight_i / sum(weight)
```

若当前 sampler 已经维护归一化概率，优先从经过验证的公开/内部接口读取，避免在 trace 中复制一套和真实采样顺序不一致的逻辑。若必须重算，只把它标成 `diagnostic_probability` 并写测试比较。

### 逐步耗时定义

|字段|起点|终点|是否可能含异步等待|
|---|---|---|---|
|`load_us`|开始打开/解析模型|模型和必要 backend buffer 可用|是；必须确认 backend 同步|
|`tokenize_us`|模板文本准备好|token vector 完成|通常 CPU|
|`prefill_us`|提交 prompt batch 前|logits 确实可读取|GPU 时必须包含所需同步|
|`sample_us`|取得 logits 后|chosen token 确定并 accept|通常 CPU，但依实现确认|
|`decode_us`|提交 chosen token batch 前|下一步 logits 可读取|GPU 时必须包含所需同步|
|`detokenize_us`|token 已选定|可发送的 UTF-8 bytes 就绪|可能跨多个 token 缓冲|
|`send_us`|准备写响应|写入协议层完成|不一定等于客户端已接收|

如果只计“提交 GPU 工作”的时间，会得到虚假的极短 decode；计时终点必须是结果所需同步之后。用单调时钟，记录单位和分辨率；日志 I/O 自身会扰动微秒级路径，性能基线应同时跑“trace off”和“trace on”。

### 不可编译的独立 example 伪代码

> [!danger] TEXT ONLY — NOT COMPILE-READY
> 下方没有真实 include、类型或函数签名，只能在固定 commit 中逐项映射后实现。

```text
main(args):
    cfg = parse_required_fixed_inputs(args)
    require(cfg.source_commit == build_embedded_commit)
    require(sha256(cfg.model) == cfg.expected_model_hash)

    trace.request_start(redacted_configuration(cfg))
    backend = CURRENT_COMMIT_API.initialize_backend(cfg.backend)

    timed("load"):
        model = CURRENT_COMMIT_API.load_model(cfg.model, cfg.model_params)
        ctx   = CURRENT_COMMIT_API.create_context(model, cfg.context_params)

    timed("tokenize"):
        prompt = CURRENT_COMMIT_API.apply_template_if_requested(cfg.messages)
        tokens = CURRENT_COMMIT_API.tokenize(model.vocab, prompt, cfg.special_policy)

    timed_and_synchronized("prefill"):
        CURRENT_COMMIT_API.decode(ctx, make_prefill_batch(tokens))

    for step in [0, cfg.max_new_tokens):
        logits = CURRENT_COMMIT_API.logits_for_requested_batch_row(ctx)

        timed("sample"):
            diagnostic = inspect_top_candidates_without_mutating_sampler(logits)
            chosen = CURRENT_COMMIT_API.sample_and_accept(cfg.sampler, logits)
        trace.sample(step, diagnostic, chosen)

        timed("detokenize"):
            bytes = CURRENT_COMMIT_API.token_to_piece(model.vocab, chosen)
            utf8_buffer.push(bytes)
            trace.piece_when_complete_utf8(step, utf8_buffer)

        if should_stop(chosen, utf8_buffer, cfg): break

        timed_and_synchronized("decode"):
            CURRENT_COMMIT_API.decode(ctx, make_one_token_batch(chosen, next_position))

    trace.request_end(stop_reason, usage)
```

## 如果独立 example 不够：精确核心补丁策略

只有需要观察 server 队列、slot、取消或跨 backend scheduler 时，才考虑给核心路径加**默认关闭**的 trace。不要在没有固定 commit 时写具体行号。

### Patch contract

1. 新增一个窄接口 `trace_sink`（实际命名从项目风格决定），默认是空实现；
2. 用构建选项或运行时显式参数启用，默认输出行为完全不变；
3. 只传结构化、无所有权的数据快照，不把大 tensor/logits vector 复制到日志线程；
4. 每个 request 有独立 ID，禁止记录 prompt 原文和凭据；
5. 计时使用单调时钟，GPU span 在需要结果的同步点闭合；
6. sampler 的诊断不能消费 RNG、改变候选数组顺序或重复执行 penalty；
7. 对事件 schema、trace-off 行为和固定小输入写测试；
8. benchmark 同时比较 trace off/on 的开销。

### 不可应用的伪补丁

> [!danger] PSEUDO-DIFF — DO NOT APPLY
> 文件名、类名、上下文都不存在于已核验源码；它只描述插入点和不变量。

```diff
--- a/<CURRENT_REQUEST_LOOP_FILE>
+++ b/<CURRENT_REQUEST_LOOP_FILE>
@@ request starts @@
+ trace.emit(request_start{request_id, build_id, redacted_params});

@@ after tokenization @@
+ trace.emit(tokenize_end{token_count, elapsed_us});

@@ around prefill/decode; close span only when logits are ready @@
+ trace.emit(decode_end{phase, step, batch_rows, elapsed_us});

@@ inspect sampler candidates without mutating sampler state @@
+ trace.emit(sample{step, chosen_id, sampling_probability, top_n, elapsed_us});

@@ after detokenization / protocol write @@
+ trace.emit(piece_ready{step, byte_count, elapsed_us});
```

所谓“精确”不是提前猜行号，而是实施时给每个插入点列出：固定 commit、真实文件、真实函数、前后不变量、测试、trace-off 行为和性能影响。

## 三种适合初次贡献的小型扩展

### 方案 A：独立 per-token trace example（优先）

范围：单模型、单 request、单 sequence；输出上述 JSONL。它覆盖加载、tokenize、prefill、decode、sample 和 detokenize，却不触碰 server 并发。

验收：固定 commit 和模型哈希下，事件顺序稳定；token IDs 与正常最小例一致；trace on/off 选择的 token 一致；字段无 prompt 原文/绝对路径。

### 方案 B：backend placement 摘要

范围：只读遍历已加载模型张量，按 backend/buffer type 汇总张量数与字节，并可选输出少量名称。不要改变 placement，也不要把量化块大小当作普通元素字节数。

验收：汇总字节与 allocator/backend 报告在定义范围内一致；CPU-only 与 mixed 配置差异可解释；关闭输出时无行为变化。

### 方案 C：server request 生命周期 trace

范围：request parsed → queued → slot assigned → prefill → decode steps → stop/cancel → slot released。它风险高于 A，因为涉及并发、隐私与热路径。

验收：两个并发请求的 ID 不混淆；断连触发取消并最终释放 slot；不会把 bearer token、prompt、完整输出或模型私有路径写日志；日志背压不阻塞推理线程。

第一次扩展不要修改 GGUF schema、公共 ABI、量化 kernel、KV cache 布局或默认网络协议；这些改动的兼容与测试面远大于“一个小型扩展”。

## 调试方法：先分类，再选择工具

### 构建/链接问题

证据：CMake 配置摘要、`compile_commands.json`、verbose build、动态依赖与实际加载库。常见分类：feature guard 未启用、头/库版本不匹配、ABI/运行库不一致、backend target 未链接、动态库搜索路径不同。

连接 [[计算机知识/30-计算机系统/03-ABI调用约定与静态动态链接|ABI、调用约定与链接]]。

### 内存与生命周期问题

CPU Debug 构建可使用断言、ASan/UBSan 和调试器；多线程问题再考虑 TSan，但不同 sanitizer、OpenMP/线程运行时和 CUDA 不一定可组合。定位时记录：分配者、所有者、view/backing buffer、异步操作完成点和销毁顺序。

连接 [[计算机知识/10-编程语言/02-C++/03-指针引用const与生命周期|指针、引用、const 与生命周期]] 与 [[计算机知识/10-编程语言/02-C++/04-栈堆RAII与智能指针|RAII 与智能指针]]。

### 错误 token 或概率

按层二分：

1. chat template 渲染文本是否一致；
2. token IDs/special token/position 是否一致；
3. prefill 最后 row 的 logits 是否取对；
4. CPU 与 CUDA 的 raw logits 差异是否在已定义容差；
5. sampler 处理顺序、seed、accept 历史是否一致；
6. token piece 与 UTF-8 buffering 是否一致。

不要一看到输出不同就归因于“浮点误差”。先排除模板、token、position、logits row 和 sampler state。

### CUDA 错误或退回 CPU

先证实 backend 加载、设备枚举、张量 placement 和 kernel 活动，再看：架构是否包含目标 GPU、host driver/Toolkit 是否兼容、显存是否足够、异步错误在哪个同步点显现、特定 op/type 是否有 CUDA 实现。设备工具与 profiler 方法连接 [[计算机知识/40-并行与异构计算/01-CUDA/09-Roofline与Nsight性能方法|Roofline 与 Nsight 性能方法]]。

### server 卡住或延迟尖峰

把 span 分为 queue、slot wait、prefill、decode、sample、serialization/send。检查锁、条件变量、取消标志、日志 I/O、客户端背压和 backend 同步。平均 tokens/s 会隐藏队列等待和 P99 inter-token latency。

## 性能阅读：从时间归因到数据移动

一次 token 的延迟可能由以下部分组成：

```text
调度与 batch 组装
  + graph 构建/计划
  + 权重与 KV 读取
  + CPU SIMD / GPU kernel
  + 跨 backend copy 与同步
  + logits 传回与采样
  + detokenize 与协议发送
```

先用 trace 判断时间在哪层，再使用 profiler。CPU 路径关注线程、NUMA、缓存 miss、带宽和热点；CUDA 路径关注 kernel timeline、H2D/D2H copy、launch gap、同步、占用与内存吞吐。不要从“GPU utilization 低”直接推断 kernel 差，它也可能在等待 CPU、队列、数据或串行采样。

## 测试矩阵：小改动也要跨过这些门

|层级|最小测试|失败意味着什么|
|---|---|---|
|格式/元数据|固定小 GGUF 或项目 fixture 的结构检查|加载前提已破坏|
|tokenizer|ASCII、中文、emoji、special-token 边界|文本/token 边界错误|
|确定性路径|greedy 或固定 sampler state 的短生成|调用链、状态或数值回归|
|trace schema|事件必填字段、顺序、JSON 转义|观测工具不可机器读取|
|trace non-interference|trace off/on token 序列相同|trace 改变 sampler/RNG/时序语义|
|CPU Debug|目标测试 + sanitizer（适用时）|内存/UB/断言问题|
|CPU Release|相同功能 + 性能基线|优化构建特有回归|
|CUDA|实际设备的正确性、placement 与工具检查|不能用 CPU 结果替代|
|server|并发、stream、取消、错误、usage|请求生命周期回归|

如果没有 CUDA 硬件，只能写“CUDA 未运行验证”；不能因代码通过编译或 CPU 测试而宣称 CUDA 正确。

## 代码审查清单

- [ ] 基线是完整 commit，本地补丁与 dirty 状态已记录。
- [ ] 新增 target/文件遵循该 commit 的构建和命名约定。
- [ ] trace 默认关闭，不改变正常 stdout/stderr/HTTP schema。
- [ ] trace 不改变 RNG、sampler 候选、KV cache 或同步语义。
- [ ] 不复制 logits 全词表到热路径；top-N 和详细日志有显式上限。
- [ ] 不记录 prompt、完整 response、API key、私有路径或模型下载 URL。
- [ ] 时间单位、起止点、GPU 同步边界和 logging overhead 已说明。
- [ ] CPU/CUDA 与混合 offload 的未测试组合被明确列出。
- [ ] 测试覆盖成功、错误、取消、空/极端输入和资源回收。
- [ ] 没有顺手格式化/改名无关文件，没有改 GGUF/公共 ABI。

## 练习

### 练习 1：建立符号证据表

在固定 commit 中选 CLI 或 server 之一，用本页调用链表填入真实文件、函数、对象所有者和测试。每个跨层箭头附一条 `rg`/调用者证据；不要复制大段源码。

### 练习 2：评审 trace schema

给 schema 增加 `backend_summary`、`batch_rows` 和 `stop_reason`，并回答：哪些字段可能泄露隐私？哪些计时会漏掉 GPU 异步执行？哪个动作可能意外消费 sampler RNG？

### 练习 3：写“先失败”的测试计划

在不改源码前，写出 trace 扩展的失败测试：例如 trace on/off 的 chosen token 不一致、断连后没有 `request_end/cancelled`、JSON 中出现 prompt 原文。只有能稳定观察失败，才开始实现。

### 练习 4：做一轮 CPU/CUDA 差异定位

固定 prompt tokens、batch、seed 与 sampler，逐层比较 rendered prompt → token IDs → logits row → raw top-N logits → post-sampler distribution → chosen token。把首个不一致点作为问题边界，不要只比较最终自然语言。

## 成功标准

- [ ] 我能在陌生 commit 中从 target 和公共 API 收敛到一次请求，而不是漫游所有目录。
- [ ] 我能说明 model、context、batch、graph、backend buffer 和 sampler 的所有权边界。
- [ ] 我设计的 trace 同时包含 token 的明确概率阶段与逐步耗时起止点。
- [ ] 我能解释为什么 GPU 计时要考虑异步提交与同步。
- [ ] 我能让扩展默认关闭、可独立测试、可删除，并证明它不改变采样结果。
- [ ] 没有完成固定 commit 的逐层源码核验时，我只写伪代码/伪补丁，不冒充可运行实现或给出虚假测试结果。

## 恢复与退出条件

- 独立 example 的恢复：删除新增 target、源文件和专用测试；重建独立 build 目录确认原 target 不受影响。
- 核心 trace 补丁的恢复：反向应用已保存的精确补丁或 revert 自己的独立 commit；不要覆盖同伴改动，不使用破坏性的全树重置。
- 运行中的 server：先停止并验证端口与工作线程退出；日志若含意外敏感内容，不提交，并按既定安全流程删除/轮换相关凭据。
- 模型与 build：分别保管和清理；不要把模型、build、trace 大日志纳入源码仓库。
- 遇到无法固定 revision、测试 fixture 不可获得、GPU 不可用或接口已演进时，停止宣称对应层通过，记录“未验证”和下一条可执行检查。
- 本页在 Vault 内只新增教学 Markdown；主任务虽在 Vault 外构建了固定 commit，但没有创建 trace 源文件、核心补丁或模型推理产物，不能把 build 证据升级为本页扩展已实现。

---

**上一站**：[[AI/20-LLM/50-实现/04-llama.cpp构建后端与调用链|llama.cpp 构建、后端与调用链]] · **下一站**：[[AI/20-LLM/50-实现/06-GGML张量计算图分配器与Backend|GGML 张量、计算图、分配器与 Backend]] · **C++ 阅读法**：[[计算机知识/10-编程语言/02-C++/10-阅读大型C++仓库与llama-cpp调用链|阅读大型 C++ 仓库与 llama.cpp 调用链]] · **返回**：[[AI/20-LLM/50-实现/00-LLM实现-MOC|LLM 实现 MOC]]
