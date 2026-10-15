---
domain: "计算机知识"
type: "course"
stage: 4
prerequisites:
  - "[[计算机知识/Kali/05-密码无线与专门领域/01-哈希口令KDF与估算|哈希口令KDF与估算]]"
  - "[[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|离线实验准备与夹具说明]]"
sources:
  - "https://www.openwall.com/john/doc/FAQ.shtml"
  - "https://docs.python.org/3.13/library/unicodedata.html"
  - "https://hashcat.net/wiki/doku.php?id=hashcat"
  - "https://www.openwall.com/john/doc/EXAMPLES.shtml"
content_status: "usable"
evidence_status: "partial"
---

# HashcatJohn与离线审计

**先修关系：** [[计算机知识/Kali/05-密码无线与专门领域/01-哈希口令KDF与估算|哈希口令KDF与估算]]；[[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|离线实验准备与夹具说明]]。

## 先把格式验证正确，再讨论计算速度

Hashcat 和 John the Ripper 都可做离线口令审计，但格式名称、支持的构建、输出缓存与硬件后端不同。输入扩展名叫 `.txt` 不说明算法；64 个十六进制字符也不唯一对应“普通 SHA-256”。先用一个已知的、公开的教学口令生成摘要，确认工具能复现，再处理已授权数据。[^s1][^s2]

本包只提供两条**公开教学口令**的无盐 SHA-256 和五项候选，不含真实账户数据。SHA-256 在这里用于演示计算链，**不是推荐的口令存储方案**。先按 [[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|夹具说明]] 将资料复制到 `$HOME/kali-lab`。

## 把计算过程拆成可观察的流水线

一份离线审计至少经过输入装载、格式解析、候选生成、候选变换、算法计算、目标比较和结果记录。Hashcat 的算法模式与候选模式是不同配置轴，设备后端又是第三个轴；John 的核心版与 Jumbo 构建支持范围也不能凭同一个程序名假定一致。[^v5-hashcat][^v5-john-faq]

| 环节 | 典型工具功能 | 应解释的输出 |
| --- | --- | --- |
| 格式识别与装载 | 算法模式、格式选项、示例输入 | 装入了多少有效目标，拒绝了什么 |
| 候选构造 | 字典、规则、掩码、组合或混合 | 本次实际覆盖哪些候选，是否有重复或不适用输入 |
| 计算后端 | CPU/GPU接口、设备选择、内核 | 是否成功初始化，支持的字节长度和算法限制 |
| 结果与会话 | 恢复会话、结果缓存、展示已匹配项 | 新匹配与历史结果分别有多少，是否属于本次目标 |

工具提示“耗尽”通常描述配置的候选任务结束，不是证明口令不存在；装载零个目标、运行中止和正常耗尽必须区别。已有脚本与夹具仍只演示它们声明的玩具输入，不能将真实凭据放进共享 Vault。

## 候选生成、算法模式和设备后端互相独立

算法模式决定如何从候选及盐/参数计算目标记录；字典、规则或掩码决定候选从哪里来；后端决定计算在哪里执行。选对 GPU 不会补救选错算法，选对算法也不会创造不在候选集合中的答案。[^v2-hashcat]

字典有 5 项、每项应用 4 种规则，不代表一定得到 20 个不同候选：某些规则可能生成重复值或不满足格式限制。报告中区分原始条目数、生成次数、去重候选数、实际完成次数与未处理部分。大型规则集和掩码只作为有预算的扩展，不是本包默认实验。

## 字符看起来相同，摘要输入也可能不同

下面只用公开的原创字符例子解释输入合同，不处理真实口令。Python 中 `"Caf\u00e9"` 与 `"Cafe\u0301"` 都可能显示成 Café，但前者最后一个字符是预组合 é，后者是 e 加组合重音。它们的 UTF-8 字节串不同。Unicode 规范化可以让某些等价表示归一，但应采用哪一种形式由被审计系统的原始协议决定，不由分析者临时猜测。[^v3-unicode]

先区分三层：用户输入的字符、应用实际采用的编码/预处理、送入 KDF 或摘要的字节。若原系统不规范化，而你为了“清洗数据”规范化了候选，就改变了测试问题；若它原来规范化而你不做，也可能产生假阴性。类似地，去空格、改大小写、换行处理、前置 BOM 都需要明确合同，不能一律当成无害清洗。

本包原候选是 ASCII 合成数据，不受上述组合重音影响。拓展到 Unicode 前，先用你自己创建且知道原文的一个账户/测试记录做端到端对照，再审阅编码转换。不要用一个失败的五词样本推断“这种哈希无法恢复”。

### 把本次计算与历史缓存分开归因

Hashcat 的 potfile、John 的 pot 文件与会话恢复都会影响显示结果。记录输入摘要之外，还需记录是否使用新缓存、缓存初态与此次退出原因。`--show` 主要回答已有恢复信息与输入如何匹配，不会独立证明这些候选是在这次预算内被计算出来。[^v3-hashcat][^v3-john]

一个可区分原因的对照是：保持算法和输入不变，第一轮用新缓存；第二轮明确复用缓存；第三轮换新缓存并移除一个已知正确候选。先预测每轮差异，再读输出。如果第三轮仍显示被移除候选，回查实际读取的字典、规则和缓存位置，而不是增加算力。

审计报告应把“命中多少”“花了多久”“处理了多少候选”“哪些明文来自历史缓存”分开。此处的流程是有界教学设计，Hashcat 与 John 仍未在本容器实跑；原实验 D 的 Python 对照只验证公开小字典的计算链。

## 一组不依赖 GPU 的输入诊断

在复制出的教学目录中先检查行数、编码和摘要记录格式，确认两条摘要与五项候选符合 [[计算机知识/Kali/07-综合实验/05-实验D口令哈希与预算|实验 D]] 的预期。先用原样夹具跑纯 Python 对照，再改一个候选、使用新的 potfile 验证结果确实变化。

```bash
# 只读公开教学文本，不处理真实摘要；查看行尾/不可见字符。
wc -l "$HOME/kali-lab/fixtures/candidate-words.txt"
sed -n '1,8l' "$HOME/kali-lab/fixtures/candidate-words.txt"
```

`sed` 的展示编码依本机 locale 等因素；它是诊断线索，不是通用 Unicode 规范化。若文件含用户名、盐、分隔符或 BOM，先核对目标格式，不在不知道含义时批量删除字段。

## Hashcat：受限的字典实验

在 Bash 中执行前先读本机帮助，确认模式 1400 对应原始 SHA2-256，攻击模式 0 对应候选列表：

```bash
hashcat --version
hashcat --help
mkdir -p "$HOME/kali-lab/output"
hashcat -m 1400 -a 0 \
  "$HOME/kali-lab/fixtures/hashes-sha256.txt" \
  "$HOME/kali-lab/fixtures/candidate-words.txt" \
  --potfile-path "$HOME/kali-lab/output/toy-hashcat.pot" \
  --session toy-kali --runtime 30
hashcat -m 1400 \
  "$HOME/kali-lab/fixtures/hashes-sha256.txt" --show \
  --potfile-path "$HOME/kali-lab/output/toy-hashcat.pot"
```

`--runtime 30` 是本实验的时间边界，不是找到答案保证。Potfile 是已恢复结果缓存；旧缓存会让一次“瞬间找到”看似是本次计算成果。首次实验使用新的输出目录，复跑则明确记录复用了缓存。真实审计的 potfile 含敏感明文，需受限权限与销毁策略。

若报无 OpenCL/CUDA 设备或不支持后端，先停止，记录环境缺失。不要用 `--force` 掩盖驱动警告，也不要为完成练习安装不明驱动。虚拟机常不具备所需 GPU 通路；离线 Python 实验仍可完成机制验证，不代表已测过 Hashcat。退出码的具体含义查当前帮助，不能一概把非零都归为程序崩溃。

## John：同一数据、独立工具路径

Kali 中可用格式由安装构建决定。先检查，再运行小字典：

```bash
john --list=formats
john --format=Raw-SHA256 \
  --wordlist="$HOME/kali-lab/fixtures/candidate-words.txt" \
  --pot="$HOME/kali-lab/output/toy-john.pot" \
  --session="$HOME/kali-lab/output/toy-john" \
  "$HOME/kali-lab/fixtures/hashes-sha256.txt"
john --show --format=Raw-SHA256 \
  --pot="$HOME/kali-lab/output/toy-john.pot" \
  "$HOME/kali-lab/fixtures/hashes-sha256.txt"
```

这些格式与选项按 Jumbo 常见构建说明；上游基础版与打包版不保证完全相同。先确认 `--list=formats` 能运行，不能运行时查本机 John 文档，而不是删去格式参数赌自动识别。[^s2]

## 速度比较必须先保证实际计算的是同一个问题

Hashcat 的优化内核可能限制支持的口令长度；不能为了更高的显示速度，在未记录覆盖变化时换成另一条计算路径。[^v5-hashcat] 同一算法名称下，盐数、成本参数、候选编码、目标数量与设备设置也会改变工作量。比较必须保留这些条件，不用网上某块显卡的速率直接预测当前任务。

原创的覆盖例：字典100项、规则3项，名义组合为300，但两条规则可能生成同一字节串，另有候选超出当前内核输入限制。300是生成组合数，不必是300个不同且实际计算过的候选。报告应区分生成、拒绝、去重、计算和命中，不能把进度条当作输入合同的证明。

结果归属也要分开：两条用户记录可能共享某个相同的未加盐验证值，一次匹配可对应两条记录，但不代表工具完成了两次独立发现。反过来，独立盐使相同口令仍可能需要不同派生工作。机制回到 [[计算机知识/Kali/05-密码无线与专门领域/01-哈希口令KDF与估算|盐与候选分布]]。

## 常见失败不是同一种失败

`No hashes loaded` 首先排查分隔符、用户名字段、BOM、换行、格式及软件构建。找不到答案则核对候选编码、尾部换行是否被错误计入、大小写、盐和 KDF 参数。速度异常先排查缓存、任务规模、设备温度限制及优化条件，再比较工具。

Hashid/hash-identifier 一类工具只能给格式候选，不能从外观证实算法。CeWL 可从已授权文本提取候选，Crunch 可按规则生成组合，但大字典会让输入规模指数增长；本课无需真实个人画像或大规模字典。实际预算必须先按 [[计算机知识/Kali/05-密码无线与专门领域/01-哈希口令KDF与估算|候选空间模型]] 估算。

> [!question] 自检与迁移
> 把候选表中的 `Cedar-7!` 去掉，预期只恢复另一条教学口令。若仍显示两条，优先怀疑旧 potfile，而不是假设工具能在所给列表外“智能猜中”。此实验的完整检查点在 [[计算机知识/Kali/07-综合实验/05-实验D口令哈希与预算|实验 D]]。

## 如何解释不同的结束状态

已找到全部、候选耗尽、达到时间上限、人工中止、后端初始化失败和输入解析失败，是不同状态。前两类也不能不看缓存与候选覆盖就混称“本次审计完成”。Hashcat 的具体退出码按版本帮助核对；John 的会话与 potfile 同样会改变后续 `--show` 结果。[^v2-john]

性能比较固定算法参数、候选、目标数量、优化开关、设备、驱动和实际计时区间。五个词的小实验主要测输入流程，启动开销可能压过计算，不能据此给 GPU 品牌排名。真实审计输出的明文和恢复缓存按秘密材料处理，公共样本才可随本包分发。

## 来源与核验范围

[^v5-hashcat]: [Hashcat official wiki — hashcat](https://hashcat.net/wiki/doku.php?id=hashcat)；定位：输入模式、后端、优化内核限制和状态字段。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-john-faq]: [Openwall — John the Ripper FAQ](https://www.openwall.com/john/doc/FAQ.shtml)；定位：格式、构建差异与运行问题；首次读取成功，随后定位请求失败。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Hashcat 官方 Wiki](https://hashcat.net/wiki/doku.php?id=hashcat)；定位：hash modes / attack modes / --runtime / --potfile-path。网页读取：2026-09-05。
[^s2]: [Openwall：John usage examples](https://www.openwall.com/john/doc/EXAMPLES.shtml)；定位：wordlist、show、会话与格式。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-hashcat]: [Hashcat 官方 Wiki](https://hashcat.net/wiki/doku.php?id=hashcat)；定位：模式、字典/掩码、缓存、设备和退出状态。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-john]: [Openwall：John examples](https://www.openwall.com/john/doc/EXAMPLES.shtml)；定位：wordlist / rules / session / show。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-unicode]: [Python 3.13：unicodedata](https://docs.python.org/3.13/library/unicodedata.html)；定位：normalize；NFC / NFD 与规范等价。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

[^v3-hashcat]: [Hashcat 官方 Wiki](https://hashcat.net/wiki/doku.php?id=hashcat)；定位：--show；potfile；encoding 与会话。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

[^v3-john]: [Openwall：John usage examples](https://www.openwall.com/john/doc/EXAMPLES.shtml)；定位：--show；pot 文件；wordlist 与会话。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]