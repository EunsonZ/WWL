---
type: lab
stage: 3
status: ready
difficulty: 进阶
estimated_minutes: 90
topics:
  - decoder-only-transformer
  - pretraining
  - tokenizer
  - causal-attention
  - RoPE
  - checkpoint-resume
  - evaluation
domain: artificial-intelligence
tags:
  - ai/practice
  - ai/llm/training
  - ai/reproducibility
---

# 微型 Transformer 预训练

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 本轮[[AI/80-实践/08-深层机制数值实验/00-数值实验导航与验收|42 项深层机制测试]]补充梯度、概率、缓存与训练状态验证；它与本页实验解决不同层的问题。先读[[AI/20-LLM/80-研究拓展/03-从论文主张到可复现实验|验证层级]]，不要把算子测试成功登记成真实模型或部署验收。


## 你会完成什么

这是一条从随机参数开始、能安全中断和恢复的 **decoder-only Transformer CPU 教学闭环**：

```text
自编小语料 → 固定 train/dev/test → 只用 train 拟合字符 tokenizer
→ BOS/EOS 连续流 packing → causal attention + RoPE → next-token loss
→ AdamW 更新 → full-state checkpoint/resume → 冻结 dev/test 评估与生成
```

完整配置、语料和逐字同步源码集中在 [[AI/80-实践/01-微型Transformer预训练/01-完整源码与测试附录|完整源码与测试附录]]；本页只保留实验任务流、关键机制、运行顺序和验收边界。

> [!warning] 证据边界
> 语料只有 24 篇自编短文，tokenizer 按 Unicode 字符切分，模型只有 2 层、64 维、4 个 head，默认训练 120 步。它能证明数据、状态、梯度和恢复接口接通，不能证明模型有现实知识、生产质量或可外推的扩展规律。

## 安全与输入边界

- 实验不访问网络，不下载模型、tokenizer 或数据，也不自动安装 PyTorch。
- `corpus.jsonl` 只含 `created-for-this-tutorial` 文本；不要加入私人对话、密钥、个人资料或权利不明的材料。
- split 在文档级固定；前检拒绝跨 split 的规范化文本精确重复。tokenizer 只在 train 上拟合。
- 每篇文档加 BOS/EOS 后进入同一连续流；EOS 标记边界，但没有 block-diagonal mask，因此允许跨文档 attention。
- 默认只记录 prompt/生成文本的 SHA-256 与字符数；只有公开或已审查文本才使用 `--include-raw-text`。

数据治理背景见 [[AI/20-LLM/30-训练/01-数据Tokenization与预训练流程|数据、Tokenization 与预训练流程]] 和 [[AI/20-LLM/30-训练/09-数据污染评测泄漏与训练治理|数据污染、评测泄漏与训练治理]]。

## 两个关键契约

### 1. 连续流 packing 不漏目标

每个训练 block 有 `block_size + 1` 个 token，前 `block_size` 个是 input，后 `block_size` 个是右移 target。相邻 block 必须重叠一个 token：

```python
width = block_size + 1
for start in range(0, len(stream) - 1, block_size):
    block = stream[start : start + width]
```

所以窗口宽度是 `B+1`，步长却是 `B`。前一块最后一个 target 会成为后一块第一个 input；它不是重复 target。`preflight.py` 会逐 token 比较“所有非 PAD 的打包 target”和原连续流的 `stream[1:]`，要求每个 target 按原顺序恰好出现一次。测试覆盖：target 数整除 `B`、余 1，以及文档 `EOS → BOS` 边界。

### 2. resume 不改写既有历史

输出目录同时是一次 run 的身份边界：

- **原地续跑**：`--resume` 位于当前 `--output-dir/checkpoints/` 时，只允许选择最新完整 checkpoint。
- **从旧点分支**：旧 checkpoint 仍可加载，但必须给一个全新或空的 `--output-dir`。新 manifest 写入 `run_kind: branch`、父 checkpoint 文件名、step 和 SHA-256。
- checkpoint 文件名中的 step 必须与 payload 的 step 一致；配置、tokenizer、语料哈希和 packing 哈希也必须匹配。
- 保存使用完成后的临时文件发布；若目标 checkpoint 或临时文件已存在，立即拒绝，不覆盖。
- 只加载本实验自己生成且来源可信的 checkpoint；不要加载陌生 `.pt` 文件。

## 模型与张量主线

| 阶段 | 默认 shape | 本实验的动作 |
| --- | --- | --- |
| token ids | `B × T` | `B=4`、`T=48`；末块 PAD 补齐 |
| embedding | `B × T × 64` | token ID 进入 residual stream |
| Q/K/V | `B × 4 × T × 16` | 对 Q/K 施加 RoPE |
| attention | `T × T` | 下三角 causal mask，不读未来 |
| FFN | `64 → 256 → 64` | GELU 逐 token 变换 |
| logits | `B × T × V` | 输出头与 embedding 权重共享 |
| loss | 标量 | 右移 target 的交叉熵；PAD target 不计分 |

RoPE 的数学推导见 [[数学/20-线性代数与几何/06-三角函数复数旋转与RoPE|三角函数、复数旋转与 RoPE]]；架构解释见 [[AI/20-LLM/20-架构/04-位置编码RoPE与上下文|位置编码、RoPE 与上下文]]。

## 环境与运行顺序

以下命令都在本页所在目录执行。先确认 `python3` 是预期解释器；环境选择见 [[计算机知识/90-资源/03-Python环境与包管理选择矩阵|Python 环境与包管理选择矩阵]]。

### 1. 只读前检与测试

```bash
python3 preflight.py
python3 -m unittest -v test_tiny_transformer.py
```

成功的前检至少包含：

- `"status": "PASS"` 与 `"writes": 0`；
- 16/4/4 篇 train/dev/test 文档；
- 每个 split 的 `next_token_targets == source_tokens - 1`；
- packing 边界声明含 `every target covered exactly once`；
- 同 seed 的 train block 哈希稳定。

没有 PyTorch 时，纯标准库测试照常运行；模型和 checkpoint 状态测试明确 `skipped`，不会安装依赖，也不能把 skip 写成训练通过。

### 2. 可选 CPU 训练

```bash
python3 tiny_transformer.py --output-dir outputs/run-01
```

没有 PyTorch 时脚本输出 `SKIP` 并返回 77。有 PyTorch 时才在 CPU 上记录 step 0 dev 指标、执行反向传播、梯度裁剪与 AdamW 更新。产物只写入显式输出目录：`run-manifest.json`、`tokenizer.json`、`metrics.jsonl`、`checkpoints/`、`final-summary.json`。Vault 内输出必须在本实践已忽略的 `outputs/` 下；全新训练拒绝非空目录。

### 3. 原地恢复最新 checkpoint

先停在 20 步：

```bash
python3 tiny_transformer.py --max-steps 20 --output-dir outputs/resume-demo
```

此时 step 20 是最新完整 checkpoint，可以原地继续：

```bash
python3 tiny_transformer.py --max-steps 40 --output-dir outputs/resume-demo \
  --resume outputs/resume-demo/checkpoints/checkpoint-step-0020.pt
```

### 4. 从旧 checkpoint 创建分支

如果原 run 已经有 step 40，再从 step 20 探索另一条路径时，不能把结果写回原目录：

```bash
python3 tiny_transformer.py --max-steps 60 --output-dir outputs/from-step-20 \
  --resume outputs/resume-demo/checkpoints/checkpoint-step-0020.pt
```

`outputs/from-step-20` 必须不存在或为空。原目录选择旧 checkpoint 会被拒绝；新分支保留自己的 metrics、checkpoint 和 lineage manifest，不覆盖父 run。

## 如何解读证据

| 证据 | 可以说明 | 不能说明 |
| --- | --- | --- |
| preflight target 数与顺序 | 连续流中的每个 next-token target 被覆盖一次 | 文档之间已做 attention 隔离 |
| step 0 到最后的 dev NLL/PPL | 参数更新后冻结 dev 的预测是否改善 | 泛化到现实世界或大语料 |
| 最后一次 test NLL/PPL | 固定小 test 上的一次结果 | 多次调参后仍然是盲测 |
| 固定 seed 的生成 | logits 到 top-k 抽样路径已接通 | 文本真实、无害或质量高 |
| 中断—恢复单测 | 下一步参数与未中断路径一致 | 跨版本、系统、硬件逐 bit 一致 |
| checkpoint 拒绝覆盖测试 | 既有 checkpoint 不会被同名保存替换 | 输出目录构成异地备份 |

NLL/PPL、反向传播与 AdamW 分别见 [[数学/30-概率与统计/03-似然负对数似然与困惑度|似然、负对数似然与困惑度]]、[[数学/40-微积分与优化/03-计算图反向传播与自动微分|计算图、反向传播与自动微分]]、[[数学/40-微积分与优化/04-SGD-Momentum-Adam与AdamW|SGD、Momentum、Adam 与 AdamW]]。

## 成功标准

指标保留 token 加权的平均 NLL，`log_ppl` 与该 NLL 相等，`ppl = exp(NLL)` 不再在 NLL=20 静默截顶。例如 NLL=25 时应报告约 `7.20e10`，不能仍报 `exp(20)`。超出 binary64 指数表示域时输出 `ppl: null` 和 `ppl_status: overflow`，同时保留有限 `log_ppl`；严格 JSON 不使用 Infinity。自检：两个运行的 NLL 都大于 20 时，旧截顶怎样掩盖差异？为什么 log-PPL 仍可比较？

加载始终显式要求 `weights_only=True`；旧版本不支持该参数或受限加载失败时停止，不重试宽权限 pickle。错误消息不是用户授权。约束见 [PyTorch 受限反序列化](https://docs.pytorch.org/docs/2.14/notes/serialization.html#torch-load-with-weights-only-true)。本轮以隔离函数和 mock 验证只调用一次加载，没有安装 PyTorch 或读取真实 checkpoint，不能据此宣称完整训练续跑已验证。

- [ ] 前检报告 16/4/4 文档、`writes: 0`，每个 split 的 target 数等于源 token 数减一。
- [ ] packing 的整除、余 1、`EOS → BOS` 三类测试都通过，且重建 target 序列逐 token 等于 `stream[1:]`。
- [ ] 没有 PyTorch 时训练明确 `SKIP`/77；有 PyTorch 时损失和梯度有限。
- [ ] 因果性测试证明改变未来 token 不影响相同前缀 logits。
- [ ] full-state checkpoint 恢复后的下一步与未中断路径参数一致。
- [ ] 原地恢复拒绝非最新 checkpoint；旧点分支拒绝非空目标目录；保存拒绝同名 checkpoint。
- [ ] 分支 manifest 可追溯父 checkpoint 的文件名、step 和 SHA-256。
- [ ] `final-summary.json` 有 test NLL/PPL、生成哈希/长度和 `resume_mode`，不把“能生成”误写成“质量好”。

## 练习

1. 完成 20 → 40 原地恢复，再从 step 20 创建新分支；比较两个 manifest、metrics 和 checkpoint 集合。
2. 用附录中的 packing 测试画出两个相邻窗口，标出唯一重叠的 input token 和各自负责的 target。
3. 复制语料到临时文件，故意制造 train/dev exact leak，用 `--corpus` 验证前检拒绝；不要修改权威语料。
4. 把 `block_size` 从 48 改为 32，使用新输出目录，只比较 block 数、有效 target 数和耗时。
5. 设计“文档不可跨界注意”的 block-diagonal mask：先写 shape 与测试，再修改训练器。

## 恢复、重置与已知限制

- 源码和固定语料是规范来源；运行产物是可再生实验记录。
- 保留失败现场时改用新输出目录。需要重置时，先把精确 run 目录改名到一个不存在的备份名，验证新运行后再由人决定是否删除。
- `.pt` checkpoint 不是安全的跨信任域交换格式；本实验的路径限制和强制受限加载不构成陌生文件的安全审计，也不防资源耗尽。
- 默认 `dropout=0` 便于教学续跑精确对照，不是通用正则化建议。
- 本实验没有 scheduler、gradient accumulation、混合精度、分布式训练、KV cache、加速 kernel、subword tokenizer、近似去重或生产 checkpoint 格式。
- 固定 seed 只是复现契约的一部分；见 [[AI/20-LLM/30-训练/02-训练循环Checkpoint与复现|训练循环、Checkpoint 与复现]]。
- 这份 CPU 基线不需要 GPU；扩大实验前按 [[AI/00-开始/03-8GB-16GB与24GB实践路线|8 GB、16 GB 与 24 GB 实践路线]] 一次只改一个变量。

## 继续阅读

- [[AI/80-实践/01-微型Transformer预训练/01-完整源码与测试附录|完整源码与测试附录]]
- [[AI/20-LLM/20-架构/00-LLM架构-MOC|LLM 架构 MOC]]
- [[AI/20-LLM/30-训练/02-训练循环Checkpoint与复现|训练循环、Checkpoint 与复现]]


## 双来源补充反例

从 WorkWithLLM 的既有测试提取并适配了 [[AI/80-实践/01-微型Transformer预训练/test_checkpoint_contracts.py|test_checkpoint_contracts.py]]：2 个反例：checkpoint 用 AST 与 Mock 验证失败关闭，PPL 用 AST 提取的真实 Python 函数验证溢出及严格 JSON。未运行真实 PyTorch checkpoint 加载。 原实现保持不变，来源与运行结果见 [[Logs/2026-09-08_双来源知识增量导入/artifacts/imported-tests.json|13 个反例映射与验证分层]]。

从 WWL 根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "AI/80-实践/01-微型Transformer预训练/test_checkpoint_contracts.py"
```
