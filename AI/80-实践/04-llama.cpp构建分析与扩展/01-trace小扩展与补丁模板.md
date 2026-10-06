---
type: reference
stage: 5
status: ready
difficulty: 进阶
domain: artificial-intelligence
topics:
  - llama.cpp
  - trace
  - patch review
tags:
  - ai/practice/llama-cpp
  - ai/llm/observability
---

# trace 小扩展与补丁模板

本页的默认方案是使用 [[计算机知识/80-实践/03-C++/03-llama.cpp-token概率与耗时trace/README|Vault 中已有的独立 C++ example]]，以仓库外的固定 llama.cpp checkout 作为 CMake 输入。这样不复制上游仓库，也不修改 server 默认路径。

## 选择门

| 需求 | 选择 | 原因 |
| --- | --- | --- |
| 单模型、单 request、单 sequence 的 token/top-N/耗时 | 独立 example | 便于删除、测试，不触碰并发服务代码 |
| 需要观察 server queue、slot、取消或 backpressure | 默认关闭的精确小补丁 | 这些状态不在独立 example 中 |
| 修改 GGUF schema、公共 ABI、量化 kernel 或 KV cache 布局 | 停止并单独设计 | 不属于“小型 trace 扩展” |

## 独立 example 契约

- 输入只接受本地 GGUF 路径和无隐私短测试输入，不接受 URL。
- 运行前比对完整 40 位 commit 和 GGUF SHA-256。
- 输出只含 request ID、参数摘要、token ID、转义 piece、概率阶段、单调时间与 stop reason。
- 不记录 prompt 原文、模型绝对路径、Authorization header 或环境凭据。
- top-N 诊断不改变 sampler 状态；trace off/on 在固定采样设置下选择相同 token。
- GPU 计时在读取结果所需的同步点后闭合，不只计 enqueue。

## 精确补丁记录模板

在没有固定 commit 和真实源码时，不写伪造行号或假函数名。实施者必须将下表中每个字段填成可复核的真实值：

```yaml
patch_id: <local-id>
upstream_base_commit: <full-40-hex>
verified_head_before: <must-equal-base>
working_tree_before: clean
purpose: <one sentence>
scope:
  files:
    - <real/path/from-current-commit>
  symbols:
    - <real function or type>
insertion_points:
  - file: <real path>
    enclosing_symbol: <real symbol>
    before_invariant: <state before event>
    after_invariant: <state after event>
default_behavior: unchanged
privacy:
  raw_prompt_logged: false
  model_path_logged: false
  credentials_logged: false
timing:
  clock: monotonic
  backend_sync_boundary: <real symbol and reason>
sampler_non_interference:
  rng_consumed_by_trace: false
  candidate_order_mutated: false
  sampler_accept_repeated: false
tests:
  - patch_apply_from_clean_base
  - build_trace_off
  - build_trace_on
  - trace_schema
  - trace_off_on_token_sequence_equal
  - fixed_input_stop_reason_and_usage
  - malformed_input
  - patch_reverse_apply
performance:
  trace_off_baseline: <record reference>
  trace_on_samples: <record reference>
  accepted_overhead: <predeclared threshold>
patch_sha256: <64-hex-after-export>
```

## 生成可应用 patch 的流程

1. 在专用副本/worktree 中确认 HEAD 等于固定 base commit，且工作树 clean。
2. 只修改记录中列出的真实文件；默认运行参数与输出不变。
3. 运行精确目标测试、trace off/on 对比和性能开销测量。
4. 导出只包含目标文件的 unified diff，计算 SHA-256。
5. 在另一个从同一 base commit 创建的干净副本中运行 `git apply --check`、应用、构建和测试。
6. 运行 `git apply --reverse --check`，反向应用后确认工作树回到 clean base。
7. 把所有命令、退出码、日志引用与实际插入点写进 Vault 外 manifest。

> [!danger] 不得伪造可应用性
> 一份只有 `<CURRENT_FILE>`、`<CURRENT_SYMBOL>` 或伪造行号的 diff 只能叫设计草图，不能标记 patch passed。只有从相同 40 位 base 的干净副本中实际应用、构建、测试和反向应用，才能声称补丁可用。

## 默认关闭的 server trace contract

只有独立 example 无法观察的 server 生命周期才使用这个方案：

```text
request_parsed
  → queued
  → slot_assigned
  → prefill_begin/end
  → decode_begin/end (repeated)
  → stop | cancel | error
  → slot_released
```

每个 request 有独立 ID；日志线程不得反向阻塞推理线程；有界队列满时必须有显式 drop/aggregate 策略；任何 prompt、完整输出、bearer token 或模型私有路径都不进 trace。两个并发请求、一个中途断连和最终 slot 释放是最小并发验收。

## 回滚

独立 example 的回滚是删除其独立 build 目录和本次临时源文件，不触及上游 checkout。核心小补丁的回滚是在身份已核对的实验副本中反向应用已保存 patch；不用破坏性 Git 清理命令。

---

**返回**：[[AI/80-实践/04-llama.cpp构建分析与扩展/00-llama.cpp构建分析与扩展|llama.cpp 构建、分析与扩展]]
