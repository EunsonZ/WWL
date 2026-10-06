---
type: practice
stage: 2
status: ready
difficulty: 进阶
estimated_minutes: 120
verified: 2026-09-01
topics:
  - sft
  - lora
  - qlora
  - checkpoints
  - evaluation
domain: artificial-intelligence
tags:
  - ai/practice
  - ai/llm/training
  - ai/peft
---

# SFT、LoRA 与 QLoRA 实践

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 本轮[[AI/80-实践/08-深层机制数值实验/00-数值实验导航与验收|42 项深层机制测试]]补充梯度、概率、缓存与训练状态验证；它与本页实验解决不同层的问题。先读[[AI/20-LLM/80-研究拓展/03-从论文主张到可复现实验|验证层级]]，不要把算子测试成功登记成真实模型或部署验收。


> [!important] 这是训练合同，不是一键训练器
> 本目录默认不下载模型、不安装依赖、不启动容器、不访问网络，也不训练真实权重。已实际运行的是纯标准库 LoRA 矩阵 toy、checkpoint/resume 与静态配置预检；Unsloth、Transformers/TRL、bitsandbytes 与 LLaMA-Factory 只完成离线配置准备，等待许可、版本、硬件和资源审查。

## 本实践要完成什么

从一个小型、可授权的 chat 数据合同开始，以相同提示、chat template 和固定解码参数比较 base 与 adapter；明确 LoRA 的 rank、alpha 和 target modules，QLoRA 的冻结基座量化、compute dtype 与 optimizer 状态；并把 checkpoint 恢复、adapter 保存、合并和目标格式导出分别验收。

这里的 `data/sample_chat.jsonl` 只有三条合成 CC0 教学样本，分别占据 train/dev/test；[[AI/80-实践/02-SFT-LoRA与QLoRA/data/LICENSE|样例数据许可声明]]记录适用范围和权利声明。真实数据必须另建不可变 manifest，记录来源、训练权利、去标识化、去重、切分组、哈希、保留期限与删除流程；个人资料、token、私有下载 URL、模型缓存和权重绝不进入 Git。

## 学习入口

- 方法、mask 与显存：[[AI/20-LLM/30-训练/03-SFT-LoRA与QLoRA|SFT、LoRA 与 QLoRA]]。
- 工具边界：[[AI/20-LLM/30-训练/05-Unsloth原理环境与工作流|Unsloth 工作流]]、[[AI/20-LLM/30-训练/06-LLaMA-Factory数据配置训练与导出|LLaMA-Factory 工作流]]。
- 数学：[[数学/20-线性代数与几何/04-特征值SVD与低秩近似|低秩近似]]、[[数学/60-数值计算与量化/02-量化Scale-Zero-Point-Group与误差|量化误差]]。
- 系统：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]、[[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|驱动与设备]]、[[计算机知识/20-操作系统/01-Linux/07-环境变量Shell启动与PATH|PATH]]、[[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|日志与故障排查]]。

## 1. 小数据合同与 chat template

`configs/data-contract.json` 约束记录必须有 id、messages、license、split、split_group；最后一条必须是 assistant；许可必须在显式批准清单中，每个 split_group 只能属于 train/dev/test 中一个 split，并且许可记录文件必须存在。它声明 toy-chat-v1、assistant-only loss、EOS 与“若被监督 assistant span 会被截断则拒绝样本”的策略。

JSON 外形不是训练语义。真正训练前必须以被选定基座的 tokenizer 和精确 chat template 抽查：角色控制 token、BOS/EOS 是否重复、哪些 labels 是 -100、每轮 assistant 是否正确监督，以及截断是否留下无答案的问题。不得用随机行切分近重复数据。

## 2. 三个显存档案：先预检、再测峰值

|档案|候选起点|必须测量与退让|
|---|---|---|
|8 GB|小尺寸基座的 QLoRA，512 token，micro batch 1，累积 16|先缩短序列/清异常长样本，再降 batch，之后才在支持时尝试 checkpointing|
|16 GB|小至中尺寸基座的 LoRA 或 QLoRA，1024 token，micro batch 1|常规 LoRA 加载能否成立取决于精确基座、dtype、激活和 runtime|
|24 GB|保守 QLoRA 候选，2048 token，micro batch 1|长上下文主要增加激活/attention，不可只用 4-bit 名义大小估算|

三份 JSON 档案是静态模板：configs/8gb-qlora.json、configs/16gb-lora.json、configs/24gb-qlora.json。它们的 run_enabled 均为 false，base revision、模型许可记录和 target modules 均未完成审阅。默认预检会 BLOCKED；只有明确在检查模板结构而不是批准训练时，才可加 `--allow-template-placeholders`。该开关仍不导入框架、不访问模型，输出 `STATIC VALID` 也只代表教学模板、fixture 许可和 split/group 合同通过，不代表真实基座或真实数据获准训练。

QLoRA 的 4-bit 一般只描述冻结基座的压缩存储/加载；量化元数据、反量化计算的 compute dtype、adapter、梯度、optimizer state、激活、workspace 和 allocator 要单独记录。target modules 必须由实际模型的模块名与 shape 审计决定，不能从别的架构复制。

## 3. 基线与评测合同

正式训练前在冻结 dev/test 与通用回归小集上保存 base 基线。固定 prompt、system prompt、tokenizer/template、采样参数、停止条件和评测代码；记录任务正确、结构有效、拒绝/边界处理和失败类别。随后以同一套评测比较 base、adapter、merged 与 exported artifact。训练样本的展示不能代替评测。

对于每个 target 线性层记录 din、dout、rank r、alpha、dropout、bias 和模块名。LoRA 参数量为 r(din+dout)，但整机峰值还含冻结基座与激活。运行时打印全部 trainable 参数名/数量和 total 数量；先做极小数据过拟合，才允许启动短跑。

## 4. 容器优先，原生是有条件替代

优先固定 digest 的容器，并记录镜像 digest、工具 commit、Python/PyTorch/CUDA 用户态、GPU、宿主驱动、挂载、UID/GID、网络策略、日志位置。只读挂载原始数据和基座，输出只写专用 artifacts/RUN_ID；不要挂载整个家目录、SSH 凭据、Docker socket 或 host network。

容器不会替代宿主 NVIDIA 驱动。排错顺序是 GPU/驱动与设备节点 → container runtime GPU 透传 → 容器用户态 CUDA → Python/PyTorch → 工具。Ubuntu 原生适合维护稳定组合；Arch 原生可用但滚动更新需要额外锁定 kernel、驱动、Python 与 wheel，并保留容器或虚拟环境回退。PATH 只传给当前 shell 的后代进程；不加入点号、空项或不可信目录，也不从终端 PATH 推断 IDE/服务/容器可见同一环境。

## 5. checkpoint、adapter、合并和导出

|动作|保存对象|可否等价恢复中断训练|
|---|---|---|
|checkpoint|adapter/解冻权重、optimizer、scheduler、RNG、数据顺序/游标、step、训练配置|可以，但 base revision/template/数据/精度/并行拓扑必须相同|
|adapter|adapter 权重与配置、base/tokenizer/template identity、数据和代码 manifest、哈希|通常不可以；可推理或另起训练，但缺少 optimizer 等状态|
|merge|精确基座副本、adapter、merge dtype/工具版本|不是恢复；产生新的完整权重 artifact|
|export|目标格式、tokenizer/template、量化和目标后端版本|不是恢复；需在目标运行时最小加载和同集回归|

发现 base revision、template、optimizer、数据顺序、world size 或 dtype 不一致时，一律另起 RUN_ID，写作从权重重新开始，不覆盖原 checkpoint。合并只在副本中执行。基础模型、数据、工具代码、adapter 和导出物的许可证须分别审查；小 adapter 不自动取得基座再分发权。

## 6. 纯标准库验证与静态预检

lora_toy.py 用 W0 + (alpha/r)BA 拟合固定低秩增量。它验证零初始化 B 时 base 输出不变、A/B 的低秩梯度可降低 toy loss、JSON checkpoint 可恢复并继续 step；它不是 LLM trainer，未实现 tokenizer、4-bit kernel、GPU 训练或真实评测。

preflight.py 只读取本目录 JSON/JSONL。test_practice.py 验证 toy loss、checkpoint round-trip/resume 以及预检门禁。全部源代码在 [[AI/80-实践/02-SFT-LoRA与QLoRA/01-可运行源码与配置预检|可运行源码与配置预检]] 中与同目录文件同步。

早期验证曾把两个精确命名的临时 checkpoint 写入 `/private/tmp`；它们已不再是允许的当前接口。修订后的 CLI 只接受本实践 `artifacts/toy-lora/` 内的非符号链接路径，并拒绝覆盖既有文件。当前可复现命令是：

~~~bash
python3 'AI/80-实践/02-SFT-LoRA与QLoRA/preflight.py' --config configs/8gb-qlora.json --allow-template-placeholders
python3 'AI/80-实践/02-SFT-LoRA与QLoRA/lora_toy.py' --checkpoint "$PWD/AI/80-实践/02-SFT-LoRA与QLoRA/artifacts/toy-lora/demo-run/checkpoint.json"
python3 'AI/80-实践/02-SFT-LoRA与QLoRA/lora_toy.py' --resume "$PWD/AI/80-实践/02-SFT-LoRA与QLoRA/artifacts/toy-lora/demo-run/checkpoint.json" --epochs 1 --checkpoint "$PWD/AI/80-实践/02-SFT-LoRA与QLoRA/artifacts/toy-lora/resume-run/checkpoint.json"
python3 'AI/80-实践/02-SFT-LoRA与QLoRA/test_practice.py' -v
~~~

真实 Unsloth/LLaMA-Factory/Transformers 训练是硬件与依赖跳过，而非通过。开始前固定工具 release/commit、模型 repository/revision/tokenizer/template、许可证和驱动/runtime，再分别做 token/mask 抽查、一 batch 前后向、峰值显存、短跑 checkpoint/resume 与冻结测试回归。

## 成功标准、恢复与清理

路径检查先看用户传入路径及根内父级是否有符号链接，再做 `resolve()` 与目录包含检查；只检查 resolve 后的路径会丢掉“原路径曾经过链接”的信息。指向允许目录内部的链接同样拒绝，根内目录别名也不例外。检查与打开之间仍可能有竞态，因此这是一项本机教学 CLI 政策，不是针对恶意并发修改者的完整沙盒。自检：为什么指向内部文件和外部文件的链接都应被当前政策拒绝，而一个不存在的普通输出文件可以被允许？

1. 数据合同、许可证与 template/token/labels 抽查通过，且 split 无分组泄漏。
2. base 基线保存；一 batch 前后向、trainable 参数审计、小样本过拟合、显存/磁盘/日志测量通过。
3. 同 identity checkpoint 可恢复；adapter manifest 与哈希完整。
4. base、adapter、merged、exported artifact 均用同一评测和 decode 设置比较，并保留失败类别和许可结论。

失败时停止正式训练，保留日志和最后可验证 checkpoint；回到该 checkpoint 或另建 RUN_ID。toy CLI 会把读写限制在本目录 `artifacts/toy-lora/`，并拒绝覆盖或读取符号链接；正式工具仍必须另行验证同样的不变量。仅在确认路径属于本实践且是失败输出后删除精确的 `artifacts/RUN_ID`。目录 .gitignore 排除了 checkpoints、权重、日志、缓存、W&B 和 .env；这不是访问控制或安全删除的替代。本实践没有执行 Git add/commit/push、模型下载、容器启动、网络访问或真实训练。

## 练习

1. 为一个有训练授权的任务写 manifest，按来源族切分 train/dev/test，并隔离两条近重复记录。
2. 根据实际模块清单选 target modules，计算各层和总 LoRA 参数；解释 rank 改变如何影响 optimizer state。
3. 任选 8/16/24 GB 档案，记录实际 GPU、driver/runtime、序列长度和 micro batch，短跑后按峰值修订。
4. 预先制定任务正确、结构有效、通用回归三项阈值；先记录 base，再比较 adapter/merge/export。

---

**返回**：[[AI/80-实践/00-AI实践-MOC|AI 实践 MOC]] · **训练主线**：[[AI/20-LLM/30-训练/03-SFT-LoRA与QLoRA|SFT、LoRA 与 QLoRA]] · **版本核验**：[[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]


## 双来源补充反例

从 WorkWithLLM 的既有测试提取并适配了 [[AI/80-实践/02-SFT-LoRA与QLoRA/test_path_contracts.py|test_path_contracts.py]]：1 个临时文件系统反例，核验实际路径函数对越界与符号链接的拒绝；不训练，也不向实验目录写运行产物。 原实现保持不变，来源与运行结果见 [[Logs/2026-09-08_双来源知识增量导入/artifacts/imported-tests.json|13 个反例映射与验证分层]]。

从 WWL 根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "AI/80-实践/02-SFT-LoRA与QLoRA/test_path_contracts.py"
```
