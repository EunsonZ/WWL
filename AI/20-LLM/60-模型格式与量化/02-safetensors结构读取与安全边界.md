---
type: lesson
domain: artificial-intelligence
stage: 4
status: ready
difficulty: 入门到进阶
estimated_minutes: 55
verified: 2026-09-02
topics:
  - safetensors
  - tensor-container
  - binary-format
  - untrusted-files
tags:
  - ai/llm/formats
  - ai/llm/security-boundary
---

# safetensors 结构读取与安全边界

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 避免执行序列化代码只是安全边界的一部分；仍应核验文件来源、资源尺寸和后续执行权限。可解析文件不等于模型被授权或行为可信。 深化与验证：[[AI/20-LLM/60-模型格式与量化/08-量化误差传播校准目标与端到端评测|量化误差传播校准目标与端到端评测]]；[[AI/20-LLM/70-工程应用与工具链/09-Agent状态机幂等执行与提示注入边界|Agent状态机幂等执行与提示注入边界]]。


## 本课目标

- 按字节位置说清 safetensors 的长度字段、JSON header 与 tensor data buffer；
- 解释 `dtype`、`shape` 和 `data_offsets` 如何一起限定张量；
- 区分“不用 pickle 执行任意对象”与“权重可信/资源安全/许可合规”；
- 对多分片 safetensors、索引、config 和 tokenizer 做完整性盘点。

## 1. 一个文件的三段布局

以 2026-09-02 核对的 safetensors 仓库状态 `6eb4dc9a28ebce297606e0f4836bbf28839cacef` 下 [`README.md#format`](https://github.com/huggingface/safetensors/blob/6eb4dc9a28ebce297606e0f4836bbf28839cacef/README.md#format) 为准。这是当前格式说明的实际路径；不存在的 `docs/format.md` 不应被当成可追溯引用。固定 ref 表示文档快照，不表示该提交本身修改了格式：

```text
字节 0..7          N：8 字节无符号小端 uint64，表示 header 字节数
字节 8..8+N-1    N 字节 UTF-8 JSON header，首字节必须是 "{"
字节 8+N..末尾    张量数据 buffer
```

header 的概念形状如下（这是结构示意，不是本 Vault 生成的真实权重文件）：

```json
{
  "embedding.weight": {
    "dtype": "F16",
    "shape": [4, 8],
    "data_offsets": [0, 64]
  },
  "__metadata__": {
    "format": "pt"
  }
}
```

`[0, 64]` 是相对**tensor data buffer 起点**的半开区间：包含偏移 0，不包含 64。它不是相对整个文件的绝对偏移。4×8 个 F16 值每个 2 字节，所以数据长度是 64 字节。

先用这个示意完成一次定位：读取器按 `embedding.weight` 找到张量，按 `[4,8]` 与 F16 算出 64 字节，再把相对区间 `[0,64)` 加到文件内的 `8+N` 起点。只把 `dtype` 改成 F32 而保留 shape 与区间，所需长度就变成 128 字节，原声明不再一致；只改张量名则可能仍通过字节结构检查，却不再满足架构需要的那份名称映射。这里核对的是容器描述与张量身份，不是在测量化误差。下一页用已有真实生成的 [[AI/20-LLM/60-模型格式与量化/03-GGUF结构转换与验证#2. 从文件起点到张量字节|GGUF toy 字节串]]追踪相同问题：仍需名称、shape、类型和相对 offset，但布局与对齐规则改变；它不是把本页示意实际转换后的产物。

> [!note] `__metadata__` 不是任意 JSON 仓库
> 规范允许 `__metadata__` 保存字符串到字符串的映射。它不等价于 Hugging Face 模型仓库的 `config.json`、tokenizer 文件或模型卡，也不应被当成可执行配置。

## 2. header 能告诉你什么

每个张量项主要提供：

- `dtype`：数据类型，例如 F16、BF16 或 F32；可接受集合是版本化规范，不要靠猜测扩展。
- `shape`：各维长度，空 shape `[]` 表示标量；某维为 0 的空张量可以存在且不占 tensor data。
- `data_offsets: [BEGIN, END]`：字节区间，总长度是 `END - BEGIN`。

规范还要求 tensor data buffer 被完整索引、不留洞，以避免把其他文件藏进未引用字节区域的 polyglot 技巧。张量以紧密 C/row-major 布局保存，不序列化任意 stride；当前规范说明的字节序是小端。小于 1 字节的 dtype 会带来额外的位对齐约束，验证器应依据当时的库实现而不是直接套用“元素数×整字节”。

## 3. 不加载全部权重时的结构检查

对不可信文件，应先在资源受限的环境读取最少字节，再逐层检查。一个验证器的逻辑顺序是：

1. 先取文件实际字节数 `F`，确认 `F ≥ 8`。
2. 只读前 8 字节并按无符号小端 64 位整数解析 `N`；先检查 `N ≤ F - 8`。
3. 对 `N` 另设严格的本地上限，然后才分配内存并读 header。官方实现在本次快照中提及 100 MB header 上限，它是实现的 DoS 缓解而不是“所有读取器必然一样”。
4. 检查 header 首字节为 `{`，按 UTF-8 与受限 JSON 对象解析，拒绝重复键。不同通用 JSON 库对重复键的默认处理可能不同，不能默认“后一个覆盖前一个”。
5. 对每个张量检查 dtype、非负 shape、偏移顺序、区间不越过 data buffer，且长度与 shape/dtype 一致。
6. 检查所有非空区间不重叠，排序后覆盖整个 data buffer，没有未索引洞。
7. 再对张量名、shape 和 config 的架构预期；格式合法不代表它们组成了目标模型。

这里故意不放可直接运行的解析程序：自写 parser 很容在整数溢出、重复 JSON 键、小于 1 字节 dtype 和资源上限上发生安全错误。真实实施应使用锁定版本的官方库或经审计工具，同时保留上述外层资源限制。

## 4. safetensors 比 pickle 安全的精确含义

| 边界 | safetensors 带来的保护 | 仍需独立验证 |
| --- | --- | --- |
| 反序列化 | 格式只描述张量字节和受限元数据，不恢复任意 Python 对象图 | 库实现自身的漏洞与版本 |
| 资源 | 明确长度/偏移，可先检查 header；官方实现设有 header 上限 | 超大合法张量仍可耗尽磁盘、RAM/VRAM 或计算时间 |
| 数值 | dtype/shape/偏移可检查 | 数据中可存在 NaN、±Inf、极端值或恶意模型行为 |
| 来源 | 文件可密码学哈希，字节可复现 | 哈希要与可信发布源/revision 绑定；后缀可伪造 |
| 权利 | 格式本身有工具许可 | 模型权重、训练数据、派生模型和分发条款分开判断 |

> [!warning] 安全格式 ≠ 安全模型
> safetensors 主要缩小“解析文件即执行攻击者 Python 对象”的攻击面。它不分析模型是否包含后门、是否会生成危险内容，也不代替模型卡、签名/来源、任务评测与许可审查。

## 5. 多分片仓库的完整关系

大模型常用多个 `.safetensors` 分片。一个典型输入集合有：

```text
config.json
model.safetensors.index.json
model-00001-of-000NN.safetensors
...
model-000NN-of-000NN.safetensors
tokenizer.json / tokenizer.model / vocab + merges
tokenizer_config.json / special_tokens_map.json / chat_template
模型卡、许可证与来源 revision
```

分片索引建立“张量名 → 分片文件”的映射。仅通过“文件名从 1 连续到 NN”不能证明索引完整；还要检查每个索引目标存在，每个张量只映射一次，且分片的 header 真正含有对应张量。完整集合应从同一个固定 revision 取得，不得把不同日期/分支的 config、tokenizer 和 weights 拼在一起。

最小索引的结构形状如下（名称与数字是虚构的）：

```json
{
  "metadata": {"total_size": 1600},
  "weight_map": {
    "model.embed_tokens.weight": "model-00001-of-00002.safetensors",
    "lm_head.weight": "model-00002-of-00002.safetensors"
  }
}
```

`total_size` 是索引元数据中的声明，不是信任根。验证时应从每个分片 header 独立重建 `tensor_name → file/dtype/shape/range`，再与 `weight_map`、实际文件字节数和 config 的架构期望交叉比对。

## 练习：手算 header 区间

某虚拟文件长 1048 字节，前 8 字节解析出 `N = 240`。header 中有两个 F16 张量：

| 张量 | shape | data_offsets |
| --- | --- | --- |
| `a` | `[10, 20]` | `[0, 400]` |
| `b` | `[8, 25]` | `[400, 800]` |

1. 计算 tensor data buffer 的文件内绝对起点与长度。
2. 检查两个张量的 shape、dtype 和区间长度是否一致。
3. 如果 `b` 改为 `[500, 900]`，指出所有区间问题。
4. 说明这些检查为何仍不能证明权重属于某个真实模型。

### 参考结果与成功标准

- tensor data 起点是 `8 + 240 = 248`，长度是 `1048 - 248 = 800` 字节。
- 两个张量都有 200 个 F16 值，各需 400 字节；区间相邻、不重叠且完整覆盖 buffer。
- 改为 `[500, 900]` 后，`a=[0,400]` 与 `b=[500,900]` 不重叠；但中间 `[400,500]` 是未索引的洞，而终点 900 越过了 800 字节 buffer。因此它同时有洞与越界。
- [ ] 我能分清 data offset 相对 buffer 起点，不是文件起点。
- [ ] 我会先检查长度再分配 header 缓冲区。
- [ ] 我不把格式合法、哈希一致或“不执行 pickle”写成整体安全结论。

## 恢复与版本边界

结构检查应只读，不就地修改或“补齐”上游权重。若转换后才发现分片、tokenizer 或 config 不一致，隔离派生产物，从经验证的同一 revision 重建；不应直接改动原始分片来迎合转换器。官方规范入口与核验方法见 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 与 [[AI/20-LLM/60-模型格式与量化/07-一手来源快照与现场复核清单|本模块一手来源快照]]；上限、dtype 列表和库 API 都要在实施当天对应固定 commit 重查。

---

**上一站**：[[AI/20-LLM/60-模型格式与量化/01-编码序列化与数值表示的三层边界|三层边界]] · **下一站**：[[AI/20-LLM/60-模型格式与量化/03-GGUF结构转换与验证|GGUF 结构、转换与验证]] · **返回**：[[AI/20-LLM/60-模型格式与量化/00-模型格式与量化-MOC|模型格式与量化 MOC]]
