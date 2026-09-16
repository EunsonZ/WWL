---
type: lesson
domain: artificial-intelligence
stage: 2
status: ready
content_status: usable
evidence_status: partial
evidence_record: "[[Logs/2026-09-05_改造证据/内容审阅记录]]"
prerequisites:
  - "[[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA]]"
difficulty: 高中起点
estimated_minutes: 65
topics:
  - autoregressive-generation
  - prefill
  - decode
  - kv-cache
tags:
  - ai/llm/inference
---

# 生成循环、Prefill、Decode 与 KV Cache

> [!info] 历史证据已补入
> 原有证据字段保持其历史记录；所指 [[Logs/2026-09-05_改造证据/内容审阅记录|内容审阅记录]] 已从 WorkWithLLM 按原字节补入。其范围见 [[Logs/来源材料/WorkWithLLM/README|来源说明]]；本批未重新认证本页内容或提升证据等级。

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 缓存复用要保持 token、位置、模型/adapter 和前缀可见性一致。分页改变物理布局，滑窗改变可读取的历史，两者对数学语义的影响不同。 深化与验证：[[AI/20-LLM/40-推理/09-KV缓存分页滑窗与前缀复用|KV缓存分页滑窗与前缀复用]]；[[AI/20-LLM/20-架构/11-RoPE相对位置缓存偏移与长度外推|RoPE相对位置缓存偏移与长度外推]]。


## 本课目标

- 从 token 序列解释“逐 token 生成”；
- 区分 prefill、decode 和 tokenization；
- 解释 KV cache 为什么省计算却占内存；
- 用层数、KV 头宽、上下文、batch 和精度估算 KV cache；
- 判断首 token 慢与后续 token 慢可能来自哪里。

## 一次回答不是一次性写完

自回归语言模型每一步只给出“下一个 token”的 logits。引擎选出一个 token，把它接回上下文，再运行下一步，直到遇到停止条件。

```text
文本提示
  │ tokenizer
  ▼
[t1, t2, ..., tS] ──prefill──> 第一个新 token 的 logits
                                  │ 选择 token y1
                                  ▼
缓存历史 K/V + y1 ──decode──> y2 ──decode──> y3 ── ... ──> 停止
```

一个概念性循环如下。不同引擎会融合算子、批处理请求或并行执行，但依赖关系不变：

```python
tokens = tokenize(prompt)
logits, state = prefill(tokens)  # 处理完整提示，建立 KV cache 和首步 logits

while not finished:
    next_token = choose(logits, controls)
    tokens.append(next_token)
    finished = should_stop(tokens, next_token, limits)
    if not finished:
        logits, state = decode_one(state, next_token)
```

这里的 `state` 不只是 KV cache；真实运行时还可能含页表、序列位置、采样状态和调度元数据。

## Prefill：一次处理已有提示

prefill 把提示的多个 token 送入模型，计算每层表示，并为注意力层建立历史 Key/Value。因为提示 token 都已知，引擎通常能并行处理它们；提示越长，prefill 的计算和内存访问通常越多。

- **输入**：已有的整段提示 token；
- **输出**：最后位置的 logits，以及每层供后续使用的 KV cache；
- **用户感知**：prefill、排队、tokenization 和调度共同影响首 token 到达时间；
- **常见优化**：高效 attention kernel、prefix cache、chunked prefill、张量并行。

注意力的朴素计算会比较大量 token 对，长提示的工作量增长很快；高效 kernel 可显著减少中间内存和常数，但不会让长提示变成“免费”。

## Decode：一次只追加一个位置

第一次选出新 token 后，模型只需要计算这个新位置的 Query、Key、Value 和后续层。新 Query 仍要读取历史 Key/Value 才能关注全部上下文，因此 decode 避免了重复计算旧 token，却持续读取越来越长的 KV cache。

- **输入**：每条序列最新 token、已有 KV cache 和位置；
- **输出**：下一 token 的 logits，以及追加后的 KV cache；
- **用户感知**：影响 token 连续出现的节奏；
- **常见瓶颈**：反复读取模型权重和 KV cache，单步计算规模较小，常受内存带宽、kernel 启动和调度影响。

prefill 更像“一次阅读整份材料”，decode 更像“每写一个字都要查阅已有提纲”。二者 workload 不同，所以不能只报告一个笼统的 tokens/s。

## KV Cache 保存了什么

每个注意力层会把历史 token 投影成 Key 和 Value。没有缓存时，生成第 100 个 token 可能再次为前 99 个 token 计算 K/V；有缓存时，只计算新 token 的 K/V 并追加。

KV cache 的代价是：上下文越长、并发序列越多，缓存越大。删除请求或缩短上下文后，这部分可以释放；模型权重则通常在服务存活期间常驻。

这里的 KV cache 是推理引擎显式保留的模型中间结果。硬件 L1/L2 cache 则属于存储层级，保留近期访问数据的副本；两者处于不同层次，KV 数据本身也可能经过硬件缓存。

要区分三个长度：

- **逻辑长度**：该序列已提交、后续 query 可以看见的 token 数；
- **已用物理容量**：实际存下这些 K/V 的 block/page，会受对齐和页内碎片影响；
- **已保留容量**：分配器为 KV 池预留的空间，可能大于当前已用量。

因此“请求删除后逻辑 KV 已释放”不保证 GPU 监控的进程显存立即下降：内存可能只是回到引擎的可复用池。诊断 OOM 时要同时记录 used blocks/pages、reserved bytes 和进程/设备视图。

> [!prerequisite] 数学与系统先修
> 下方只做推理预算，不重新讲矩阵、缓存和带宽。系统层的权威入口是 [[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]；GPU 的线程、内存与后端概念见 [[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]。具体阅读 [[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]] 的工作集与算术强度部分，用它解释 decode 为何随历史 K/V 读取量增大而可能受带宽限制；具体倍数仍需实测。

## KV Cache 估算公式

对常见 decoder-only Transformer，可先用下式估算：

$$
M_{KV}\approx B\times L\times S\times 2\times H_{KV}\times b_{KV}.
$$

各项含义：

- $B$：同时驻留的序列数，近似 batch；
- $L$：Transformer 层数；
- $S$：每条序列缓存的 token 数；
- 常数 $2$：每个位置同时缓存 Key 和 Value；
- $H_{KV}=n_{KV\_heads}\times d_{head}=H_{kv}\times D_h$：每层每个 token 的一份 K 或 V 中，所有 KV 头合并后的宽度；K/V 两份另由前面的 $2$ 计入；
- $b_{KV}$：每个 KV 元素的字节数，例如 FP16/BF16 通常为 2。

这里的 $n_{KV\_heads}$、$d_{head}$ 分别对应架构先修中的 $H_{kv}$（KV 头数）、$D_h$（每头维度）。注意小写下标的 $H_{kv}$ 是头数，大写下标的 $H_{KV}$ 是合并宽度。本式沿用 K 与 V 每头维度相同、各层配置相同的简化；配置不同时须分别求和。

> [!warning] 这是主项估算，不是分配器承诺
> 实际值还受变长序列、分页单位、对齐、量化 KV、滑动窗口、跨卡切分、prefix cache、运行时元数据和实现影响。模型配置中的 `num_key_value_heads`、`head_dim`、层数与 KV dtype 必须现场核对。
>
> 对滑动窗口/局部注意力，不能无条件把 $S$ 换成窗口大小：有些层可能仍是全局注意力，而且引擎是否真的不保留窗口外 KV 也是实现事实。应按层配置和实际分配验证。

### 手算例子

假设 $B=1$、$L=32$、$S=4096$，有 $H_{kv}=8$ 个 KV 头，每头 $D_h=128$ 个元素，因此 $H_{KV}=8\times128=1024$；KV 每元素为 2 字节。这是教学假设，不代表所有模型的规格。每个 token、每层的 K/V 两份共占 $2\times1024\times2=4096$ 字节，再乘层数与缓存长度：

$$
M_{KV}\approx1\times32\times4096\times2\times1024\times2
=536{,}870{,}912\ \text{bytes}\approx512\ \text{MiB}.
$$

若 batch 变为 8，其他不变，主项约为 4 GiB。若上下文翻倍，主项也近似翻倍。

以上算的是驻留容量。估算 decode 的带宽压力，还需确定每步从哪个内存层级实际搬运多少字节：是否复用更近层级的数据、是否重复读取，以及 kernel 布局都会影响流量。在历史 K/V 需要反复从较慢层级读取且这部分访问构成主要瓶颈时，减少 KV 字节数才更可能明显降低读取时间；完整延迟还包括权重读取、计算与调度。具体判断可沿用上方系统先修中的工作集与算术强度模型。

对于 MHA，KV 头数通常接近 Query 头数；MQA 只保留一组 KV 头；GQA 位于两者之间。因此参数量相近的模型，KV cache 也可能相差很大。**不能只看“7B”就推断 KV 占用。**

## Prefill 与 Decode 的工作量差异

| 维度 | Prefill | Decode |
| --- | --- | --- |
| 一次处理的 token | 提示中的许多 token | 每条活跃序列通常 1 个新 token |
| 并行性 | 通常较高 | 单序列单步较窄，多序列可合批 |
| KV 行为 | 建立提示的缓存 | 读取历史并追加一个位置 |
| 主要体验指标 | 首 token 前的时间 | 每个输出 token 间隔 |
| 常见优化 | 高效 attention、chunked prefill、prefix cache | continuous batching、分页 KV、kernel 融合、投机解码 |

prefix cache 与 KV cache 相关但不等同：普通 KV cache 服务于一个进行中的序列；prefix cache 尝试让多个请求复用相同前缀对应的计算结果。前缀必须在 token、模型、适配器和相关执行条件上兼容，复用才安全。

## 常见误区

- **“有 KV cache 后 attention 是常数成本”**：每个新 Query 仍要读取并关注历史 K/V；上下文增长仍有代价。
- **“上下文上限就是可用上下文”**：架构支持、引擎配置、显存容量和性能可接受范围是四件事。
- **“提示长只影响第一个 token”**：它主要增加 prefill，也会留下更大的 KV cache，使后续 decode 读取更多历史。
- **“同一参数量的模型显存一样”**：层数、KV 头数、精度、上下文和运行时实现都会改变结果。
- **“流式输出让模型算得更快”**：流式传输主要让用户更早看到结果；它不会自动减少模型计算。

## 练习

1. 用自己的话解释为什么 KV cache 是“用内存换重复计算”。
2. 对 $B=2,L=24,S=2048,H_{KV}=1024,b_{KV}=2$ 估算 KV cache。
3. 上题中，只把上下文改为 8192，结果变为多少？只把 KV 精度从 2 字节改为 1 字节又如何？
4. 某服务首 token 要 4 秒，之后每 40 毫秒一个 token。分别列出三个应检查的 prefill/排队因素和三个 decode 因素。

<details>
<summary>核对提示</summary>

2. 约 384 MiB。3. 8192 上下文约 1.5 GiB；在原 2048 上下文下改为 1 字节约 192 MiB。4. 首 token 可查提示长度、排队/调度、tokenization 或 prefill kernel；decode 可查内存带宽、KV 长度、batch/调度、后端和采样开销。

</details>

## 成功标准

- 能画出 tokenization → prefill → 多次 decode → stop；
- 能解释缓存的是每层历史 K/V，而不是完整模型答案；
- 能从模型配置和请求形状代入 KV 公式，并说出公式没覆盖的开销；
- 能分别定位 TTFT 与输出 token 节奏的问题。

## 导航

- 返回：[[AI/20-LLM/40-推理/00-LLM推理-MOC|LLM 推理 MOC]]
- 下一站：[[AI/20-LLM/40-推理/02-采样停止条件与生成控制|采样、停止条件与生成控制]]
- 上级：[[AI/20-LLM/00-LLM-MOC|LLM MOC]]
- 架构先修：[[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA|注意力、MHA、MQA 与 GQA]]
