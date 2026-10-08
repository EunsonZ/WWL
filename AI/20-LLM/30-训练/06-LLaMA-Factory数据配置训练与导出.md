---
type: lesson
stage: 1
status: ready
difficulty: 进阶
estimated_minutes: 80
verified: 2026-09-01
topics:
  - llm-training
  - llama-factory
  - datasets
  - export
domain: artificial-intelligence
tags:
  - ai/llm/training
  - ai/toolchain
---

# LLaMA-Factory：数据、配置、训练与导出

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 配置文件应明确记录模板、标签掩码、长度处理和恢复语义。不同前端配置看似相同，也可能对应不同有效 token 权重，导出成功不等于训练目标一致。 深化与验证：[[AI/12-PyTorch/05-变长批处理Packing与有效Token归一化|变长批处理Packing与有效Token归一化]]；[[AI/12-PyTorch/07-完整训练状态恢复与可复现实验|完整训练状态恢复与可复现实验]]。


LLaMA-Factory 为多类语言/视觉语言模型的训练阶段、数据集、参数高效微调、评测与导出提供统一工作流。它降低的是常见路径的编排成本，而不是替代数据治理、token 级检查、显存预算或独立评测。真正可复现的对象不是“我用了 LLaMA-Factory”，而是一个包含工具 commit、模型 revision、模板、数据 manifest、配置、硬件与输出哈希的实验记录。

> [!warning] 当前性与证据边界
> 具体数据 schema 名称、模板名、CLI/Web UI 参数、Docker 标签、支持模型和导出后端都可能变化。本页以 **2026-09-01** 为核验日，只给出概念与审计方法；实施前必须从 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 打开官方仓库/文档，固定 release 或 commit 后再对照实际版本。本文没有安装、下载、训练、评测、合并或导出任何模型。

## 连接到方法、数学与系统

- 训练方法：[[AI/20-LLM/30-训练/03-SFT-LoRA与QLoRA|SFT、LoRA 与 QLoRA]]；成对或二元反馈的目标与边界：[[AI/20-LLM/30-训练/04-偏好优化RLHF-DPO-ORPO与KTO|偏好优化]]。
- 低秩更新：[[数学/20-线性代数与几何/04-特征值SVD与低秩近似|特征值、SVD 与低秩近似]]；量化配置不可脱离误差讨论：[[数学/60-数值计算与量化/02-量化Scale-Zero-Point-Group与误差|量化、Scale、Zero Point、Group 与误差]]。
- 容器/宿主机边界：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]、[[计算机知识/20-操作系统/01-Linux/02-启动链Kernel与systemd|Kernel 与 systemd]]、[[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|驱动与 udev]]、[[计算机知识/20-操作系统/01-Linux/07-环境变量Shell启动与PATH|PATH]]、[[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|日志与故障排查]]。

## 数据格式的关键不是 JSON，而是“最终 token 序列”

LLaMA-Factory 通常以数据集注册信息将本地数据映射到某个 prompt / messages / preference 等格式，再由所选模型的 template 变成 token。不同版本所接受的字段与 `dataset_info` 写法可能不同，因而不能复制网上的 YAML 后假定语义相同。每个数据集应有一个不可变 manifest，至少包含：

- 本地文件的相对/受控绝对位置、内容哈希、记录数与 schema 版本；不要把私有 URL、token 或个人路径写进可共享配置。
- 来源、许可证、同意/去标识化状态，以及过滤、去重、语言/领域/风险标签。
- SFT 的 `messages` 或等价输入—输出映射；偏好训练的同 prompt `chosen/rejected`，或 KTO 的单条标签；每种目标都要有明确准则版本。
- 精确聊天模板、tokenizer revision、最大 token 长度、截断/packing 策略，以及训练/验证/测试的分组切分规则。

一条看似正确的示意记录（字段名须以固定版本文档为准）是：

```json
{
  "id": "example-001",
  "messages": [
    {"role": "user", "content": "用一句话解释梯度累积。"},
    {"role": "assistant", "content": "它把多个微批次的梯度累加后再更新一次参数。"}
  ],
  "license": "reviewed-local",
  "split_group": "source-a"
}
```

在真正训练前，人工抽查 template 渲染后的 token：system/user token 是否被错误计入 loss、assistant 边界是否正确、EOS 是否重复、长样本截断的是输入还是答案。只有这些问题清楚后，`stage: sft` 或类似字段才有意义。

还要区分三个层次：**原始业务 schema**（团队数据长什么样）、**数据集注册/字段映射**（工具怎样找到字段）、**模型模板渲染后的 token/labels**（优化器真正看见什么）。Web UI 中“预览正常”只能证明当前界面展示；必须把最终运行使用的注册文件、配置和渲染抽样导出到 run manifest。UI 默认值、浏览器状态或一次点击不应成为实验唯一记录。

## 配置应被当作实验合同

将配置拆成四个逻辑部分，而不是用一次性命令留下不可解释的状态：

|部分|必须固定的内容|常见误解|
|---|---|---|
|模型与模板|repo ID、revision、tokenizer、template、trust/remote-code 策略、许可证|模型名相同就能替换 tokenizer 或模板|
|数据与目标|dataset manifest、字段映射、stage、masking、长度/packing、split|JSON 可解析就表示 labels 正确|
|计算与优化|LoRA/QLoRA 配置、dtype、micro-batch、梯度累积、学习率、scheduler、checkpoint 间隔|有效 batch 相同就完全等价于相同训练|
|输出与可审计性|run ID、输出目录、日志、随机种子、resume 策略、评测配置、artifact manifest|有一个 `output_dir` 就足以恢复实验|

以下只展示结构，不是可直接执行的“万能配置”；精确键名和可选值必须以固定版本的官方 schema 为准。尤其不要把 `latest`、裸模型名或未固定的数据路径当成可复现输入。

```yaml
# reviewed-run.yaml — 示意，不含下载/安装动作
model:
  repo_id: organization/model-name
  revision: pinned-commit-or-tag
  template: pinned-template-name
data:
  manifest: /absolute/local/reviewed-data-manifest.json
  split: train
training:
  stage: sft
  finetuning_type: lora
  max_length: reviewed-token-limit
  output_dir: /absolute/local/new-run-id
audit:
  tool_commit: pinned-commit
  base_model_hash: recorded-separately
  allow_network: false
```

## SFT、LoRA 与 QLoRA 的组合关系

SFT 是目标：对期望输出 token 最大化条件概率。LoRA/QLoRA 是参数和内存策略，可与 SFT 或部分偏好目标组合；不能把它们当成互斥的训练“档位”。

- **SFT + LoRA：** 冻结底座、训练低秩 adapter。优先保存 adapter 与其底座/模板关联，便于审计和复用。
- **SFT + QLoRA：** 底座低比特加载，adapter 与部分计算状态使用适当精度。量化节省底座驻留，但 activation、长序列 attention、梯度累积和优化器仍是显存主要来源。
- **全参微调：** 只有在预算、数据规模、分布式策略和恢复计划都足够时再选；它不是“效果更好”的默认答案，也使 checkpoint 和导出成本急剧上升。

LoRA target modules、rank、alpha、dropout 和是否训练 embedding/输出层都应进入配置与结果表。不要只保存最终 adapter 而遗漏底座 revision、量化方式和 tokenizer；这样即使文件存在，也未必能恢复其语义。

## 容器优先环境与 Ubuntu/Arch 的差异

优先把 LLaMA-Factory 放入固定容器或其他隔离环境中，固定镜像 digest、工具 commit、Python/PyTorch/CUDA 用户态库，并明确挂载只读数据/模型与可写的专用输出目录。容器不应默认拥有 host network、端口发布、Docker socket、整個家目录、SSH 凭据或未筛选的云同步目录。容器启动时仍依赖宿主机 kernel、GPU driver、设备节点和 runtime；“镜像能拉取”或“Python 能 import”均不证明训练可用。

|环境|优势|需要额外控制的失败面|
|---|---|---|
|容器（优先）|依赖、配置和 manifest 容易固定；较易迁移和回滚|GPU runtime 与宿主驱动、挂载权限、镜像 tag 漂移、日志/网络暴露|
|Ubuntu 原生|常能直接匹配上游文档示例与稳定驱动栈|系统包、CUDA/Python 环境污染；升级后 wheel 组合变化|
|Arch 原生|适合能维护滚动系统且需要较新 kernel/driver 的使用者|内核/模块/Python 快速漂移；需在每次升级后重新验证并保留回滚路径|

无论 Ubuntu 或 Arch，先检查磁盘空间、文件系统挂载、UID/GID、`PATH` 指向的解释器、GPU 设备权限与系统日志。Arch 的滚动更新尤其要求把 kernel、NVIDIA module、用户态驱动与训练环境一起记录；Ubuntu 上也不能把“LTS”当作兼容性证明。出现失败时从驱动/设备、容器 runtime、Python/PyTorch 后端、工具模型支持、数据模板依次收敛，避免反复安装覆盖证据。

## 显存策略与 checkpoint 恢复

显存预算先按序列长度做，而不是先看参数量广告。峰值通常来自底座权重、adapter/优化器、激活、attention 临时张量和 batch。安全的调节顺序是：

1. 清理或单独处理异常长样本，降低最大长度；
2. 降低 micro-batch，再用梯度累积调整有效 batch，并记录吞吐/更新节奏变化；
3. 采用 LoRA；资源不足时评估 QLoRA 的兼容与数值影响；
4. 在小样本验证后再启用 gradient checkpointing 或特定 attention 后端；
5. 将 offload 视为存储/吞吐/故障面的权衡，而非免费显存。

周期 checkpoint 必须包含：模型或 adapter、配置、优化器/scheduler、随机状态、数据游标/epoch、分布式 world size、tokenizer/template 和日志指针。恢复前逐项比对 manifest；若只剩 adapter，能重新加载并不等于能无缝续训。遇到不匹配时复制为新 run，从可解释的起点重启，绝不把新状态写回原输出目录。

## 评测：训练 loss 只回答训练目标

评测集须在数据策划阶段冻结，并按 prompt/source 分组隔离。为每次 run 记录：基线模型、adapter 模型、合并模型（若有）在相同模板、解码参数和固定提示上的结果；同时查看目标任务正确性、格式遵循、事实性、长度、拒答、语言/领域切片、提示攻击与人工盲评。对于偏好训练，胜率也必须配合校验器或人工审查；“更受偏好”不等于“更真实”。

当生成质量变差时，先对比模板渲染、数据样本、长度分布、label mask、学习率/训练 token 数、checkpoint 以及基线，而不是立刻更换工具。评测脚本、数据和 decode 参数也要版本化；测试集不能被反复手工挑选后再作为“独立证明”。

## 保存、合并、导出与验收

|动作|产物与用途|必须保留的证据|最小验证|
|---|---|---|---|
|保存 adapter|小型可组合更新|base repo/revision、adapter config、tokenizer/template、训练 manifest、哈希|在隔离本地环境按同一底座加载|
|合并 adapter|单一 checkpoint，供某些后端消费|输入 artifact 哈希、合并工具/version、dtype/量化说明、输出哈希|固定提示下比较加载结构与输出格式|
|导出到目标格式|目标运行时所需文件集合|转换版本、模型/config/tokenizer/template、量化和运行时兼容性|目标运行时的最小本地加载；不只看后缀|

导出后要重新看许可证：工具代码许可、底座模型许可、adapter 数据许可和导出物的再分发条件不相互继承。不要因为文件由本地生成就默认可公开发布。

## 与 Unsloth、Transformers / TRL 的选择矩阵

|场景|优先选择|原因|要保留的判断|
|---|---|---|---|
|多模型、常见 SFT/偏好阶段、希望配置驱动且有明确数据注册|LLaMA-Factory|集中表达 dataset、template、stage、PEFT、日志与导出流程|配置层隐藏不了 token 化与版本差异；先审计实际渲染|
|受支持的本地微调组合，关注特定集成优化|[[AI/20-LLM/30-训练/05-Unsloth原理环境与工作流\|Unsloth]]|针对部分组合提供高层训练/导出路径|支持范围与性能结论必须按版本和机器复核|
|自定义 loss、非标准模型 patch、数据 map 或深入研究训练循环|Transformers + TRL 直接使用|可以逐层检查 log-prob、reference、rollout、callback 与分布式行为|灵活性把恢复、模板、评测和安全边界责任交还给你|
|高风险、事实性或工具执行任务|先建立独立评测/审核链|任何训练前端都不能作为能力、安全或合规的证明|不要用 UI 可启动替代产品验收|

## 受环境变量门禁的只读预检

下面命令不会安装、下载、训练或读取数据正文。它只有在你显式允许本地预检、提供已审核的 manifest 与既有运行目录时才运行；`--help` 仅确认当前解释器可找到入口，不能证明 CUDA、模型或配置可用。

```bash
if [ "${LLAMA_FACTORY_PREFLIGHT:-}" = "1" ] \
  && [ -n "${DATA_MANIFEST:-}" ] \
  && [ -f "$DATA_MANIFEST" ] \
  && [ -n "${LOCAL_RUN_DIR:-}" ] \
  && [ -d "$LOCAL_RUN_DIR" ]; then
  if ! jq -e 'has("schema_version") and has("datasets")' "$DATA_MANIFEST" >/dev/null; then
    printf '%s\n' 'DATA_MANIFEST must be valid JSON with schema_version and datasets.' >&2
    exit 2
  fi
  llamafactory-cli --help
else
  printf '%s\n' 'Set LLAMA_FACTORY_PREFLIGHT=1, DATA_MANIFEST=/absolute/local/manifest.json, and LOCAL_RUN_DIR=/absolute/local/run-dir.' >&2
  exit 2
fi
```

真正启动训练另需经审阅的固定配置、专用输出目录与显式 `ALLOW_LOCAL_TRAINING=1` 决策。训练会产生大量 checkpoint/日志、占用 GPU/磁盘，并可能处理敏感数据；它不应由教程中的粘贴命令无意触发。

## 复核清单、恢复与限制

实施当天复核：LLaMA-Factory release/commit 与官方文档、模型架构是否受支持、基础 checkpoint/tokenizer/template/revision、Docker digest 或原生 Python/PyTorch/driver、数据格式/参数 schema、量化和 attention 后端、导出目标的运行时与许可证。把这些证据、失败日志路径（不含数据正文）和验收结果写入 run manifest。

2026-09-02 的只读资料抽查只确认：[官方数据说明](https://github.com/hiyouga/LlamaFactory/blob/main/data/README.md) 将自定义数据文件与 `dataset_info.json` 注册分开，[官方 Web UI 文档](https://llamafactory.readthedocs.io/en/latest/getting_started/webui.html) 将训练、评测/预测、聊天和导出作为不同界面。这不证明当前 `main` 与某个已安装 release 完全一致，也不证明 UI 中选择的模板、mask、resume 或导出在本机正确；实际实验必须以固定 commit 的 schema、运行配置和产物读回为准。

成功标准是数据与模板抽查通过、小样本前后向通过、训练 checkpoint 可用同一 manifest 恢复、基线与产物在冻结评测中有记录、导出 artifact 完成哈希和最小加载检查。未测试的规模、长上下文、并发、安全、偏差和跨平台兼容性必须明确保留为未验证。恢复时选择最后一个可验证 checkpoint 或删除本次新建的专用输出目录；不要为解决一个训练 run 删除模型缓存、数据集、系统驱动或其他 run。

## 练习

1. **追踪一条样本：** 从业务 JSON 字段开始，依次写出注册映射、chat template 文本、token IDs、labels、loss mask 与截断结果；任何一步无法展示都标为阻塞项。
2. **审阅一份配置 diff：** 假设 Web UI 把 `max_length`、template 和 packing 改了，但输出目录仍相同。说明为什么不能续写旧 run，并列出新的 run ID、配置哈希、基线和恢复要求。
3. **设计导出验收：** 分别为 adapter、合并权重和目标格式写出输入身份、输出哈希、最小加载、固定提示回归、许可证与未验证项。

### 练习成功标准

- 能把业务 schema、数据注册、template 与 token/labels 四层逐项对齐；
- 能从一份配置还原 base、数据、训练目标、精度/PEFT、checkpoint 与输出身份；
- 能说明 Web UI/CLI 只是入口，运行配置与实际 artifact 才是证据；
- 能在不覆盖旧 run 的前提下恢复或重启，并区分保存、合并和导出验收。

---

**上一站**：[[AI/20-LLM/30-训练/05-Unsloth原理环境与工作流|Unsloth]] · **下一站**：[[AI/20-LLM/30-训练/07-模型对齐拒答方向与Heretic|模型对齐、拒答方向与 Heretic]] · **方法**：[[AI/20-LLM/30-训练/04-偏好优化RLHF-DPO-ORPO与KTO|偏好优化]] · **Python 数据/环境**：[[计算机知识/10-编程语言/01-Python/05-异常文件IO与上下文管理|文件 I/O]]、[[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|依赖锁定与迁移]] · **返回**：[[AI/20-LLM/30-训练/00-LLM训练-MOC|LLM 训练 MOC]]
