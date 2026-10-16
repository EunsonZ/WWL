---
domain: "计算机知识"
type: "practice"
stage: 4
aliases: []
prerequisites:
  - "[[计算机知识/35-计算机网络/10-系统课程/现代密码学AES与分组工作模式]]"
sources:
  - "https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197-upd1.pdf"
  - "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf"
  - "https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/AES_Core128.pdf"
---

# AES128 逐轮与 ECB/CBC/CTR 公开实验

本实践支持 [[计算机知识/35-计算机网络/10-系统课程/现代密码学AES与分组工作模式|块密码与工作模式主解释]]。**重要性高**：同一份输入若装错state、末轮多混列或计数器回绕，会改变算法；CBC IV时序、CTR区间重用和未经认证的可塑性则会改变安全目标。实验因此把代数、中间状态、公开向量、变式和输入/状态拒绝分别核对，不能只用一个最终roundtrip掩盖错误。

所有 key、IV、计数输入、消息和输出均为公开 fixture。教学 Python AES 仅供阅读正逆变换与40个阶段，含数据相关分支/查表，不是生产实现，更没有常数时间保证。实际密码行为另用成熟 cryptography 库和本机 LibreSSL CLI；不接真实秘密、网络、远程服务或硬件。旧AEAD/握手源码不导入也不复制，不重跑成熟的旧向量或篡改包。

## 输入、真源与保留结果

- [public-vectors.json](public-vectors.json)：NIST SP800-38A F.1.1/F.2.1/F.5.1 的共同64byte明文、AES128 key、CBC IV、CTR首值与密文；另有NIST AES_Core128首块初始/首轮/最终定位。SHA-256为 `9cfe04641ccc3727186ed58e8220b87f5918ae71d6483a3ad1a1d84f21cf2b90`。
- [modes_lab.py](modes_lab.py)：规范源；导入仅加载标准库并定义接口，不跑实验、写入或联网，调用时才生成S-box、使用成熟库或执行CLI。纯Python正逆AES与模式清楚标作教学，不让库替代轮机制解释。
- [test_modes_lab.py](test_modes_lab.py)：域逆/S-box、128个基向量的逆变换、公开轮与模式向量、有限改动/复用、类型/长度与区间状态边界。外部路线固定本机 `/usr/bin/openssl`，换平台需提供该入口或按平台适配测试入口，不能把缺少独立路线记成通过。
- [[计算机知识/_labs/modern_crypto_modes/源码与验证|源码与验证]]：两规范源的逐字 code-sync 镜像，不能分开编辑成另一个现行实现。
- [requirements.txt](requirements.txt)：直接依赖 `cryptography==50.0.2`；不是间接依赖/平台wheel供应链锁文件。
- [[计算机知识/_labs/modern_crypto_modes/data/results.json|data/results.json]]：本次实际输出，含11轮key、首块40阶段、三模式完整64byte密文、错误传播/复用值、状态与版本。
- [[计算机知识/_labs/modern_crypto_modes/data/author-check.txt|作者运行记录]]：真实命令、7tests摘要与资源；原临时路径作历史出处，下面给正式便携入口。

`data/` 是已运行证据，不在原位重新生成覆盖。固定输入与规范源用于复算，新环境与输出留库外。原输入来自公开标准，不是由教学实现先算答案再拿来测试自己。

## 实际命令与资源

本次复用 Python3.12.11/cryptography50.0.2 隔离环境，后端 OpenSSL4.0.3；另一个实际实现是系统 `/usr/bin/openssl` 报告的 **LibreSSL3.3.6**。独立性属于这两个实际构建，而不是“名叫openssl的两条命令”天然就独立。其他平台若CLI与库共用底层实现，要保留其版本事实，仍以公开向量与独立算法核查分开计证。

以下为本机 macOS 复算示例，需要可运行的 `/usr/bin/openssl`。已经有兼容Python环境可直接用，不必重新安装；换机时可在库外创建环境：

```bash
lab="/你的知识库绝对路径/计算机知识/_labs/modern_crypto_modes"
work=$(mktemp -d "${TMPDIR:-/tmp}/wwl-modes.XXXXXX")
python3 -m venv "$work/venv"
"$work/venv/bin/python" -m pip install -r "$lab/requirements.txt"
"$work/venv/bin/python" -B -m unittest discover -s "$lab" -p test_modes_lab.py -v
"$work/venv/bin/python" -B "$lab/modes_lab.py" --openssl /usr/bin/openssl --output "$work/fresh-output"
```

CLI 的 `--openssl` 可指定兼容的本地工具路径；所有传入该命令行的key仅为公开向量。程序仅运行 `version` 与 `enc -aes-128-{ecb,cbc,ctr} -K … -nopad -nosalt`，数据经stdin，捕获stdout，不访问网络。CBC/CTR还给 `-iv`，解密加 `-d`；源码保留实际argv拼法与每次10秒子命令超时。CLI缺失/出错必须报告失败，不悄悄跳过并宣布三路线通过。

正式运行使用现有两槽 runner、单进程、线程限制1、120秒超时，预计数秒、低于5分钟；最终作者 **7tests 0.103秒 PASS**，生成exit0。本次无依赖新增，准备成本另计；用时不是密码吞吐或侧信道测量。CLI输出目录要求全新且位于源码外，先完成所有核查再创建结果目录，不覆盖已有记录。

## 事前期望、结果与失败判据

所有有限运算、原向量和关系要求精确一致，容差零。这里的错误传播观测与公式预测要区别，不能用一个差分样本估计通用概率。

| 断言 | 先推期望 | 本次结果/失败条件 |
|---|---|---|
| 域算术与S-box | 57·13=fe，S(53)=ed，256项是双射且非仿射 | 一致；0/1/2/3输出63/7c/77/7b，前三XOR68不等第四7b |
| 行列/轮key/末轮 | 列优先、11份16byte key、首块40阶段、末轮无MixColumns | 首轮key与6处NIST定位精确，全部40阶段保留；任何错值失败 |
| 三模式机制 | NIST每种64byte正/逆完全一致 | 教学AES、cryptography、LibreSSL三路线ECB/CBC/CTR正逆均符合；不是只比同一实现roundtrip |
| 尾块 | CTR前31byte结果等于全向量前31byte | 教学/库匹配，长度不扩展；ECB/CBC非整块拒绝，未自动补零/填充 |
| ECB结构泄漏 | 同一明文块重复，密文块重复 | 实际相等；置换保留等值性，不能据此称AES本身被破解 |
| CBC IV不可预测时序 | 预测新W，选Q=P XOR V XOR W使新首密文等于旧值 | 实测首密文相等；选定Q末byte35，不把IV唯一性当充分条件 |
| CBC改IV | 首block同位置精确翻，后面不变 | XOR首bit时只变零基byte0，完整输出保留 |
| CBC改C1 | P1变、P2同位置精确翻，P3/P4不变 | 本次P1改变68bit，P2首bit翻，后两不变；68不推广为一般定律 |
| CTR改密文/复用 | 翻bit只改变对应明文bit；重复密钥流泄漏明文XOR | 改零基byte17的bit2只改该位置；两公开载荷XOR都为0000000000000000080000 |
| 跨消息计数条件 | start7长32byte占[7,9)，start8长16byte冲突 | 同对象拒重叠；耗尽/错误类型/过长输入在状态修改前拒绝，新对象丢失历史 |

CBC/CTR的“篡改成功”表示 raw 解密返回改变后的字节，算法没有认证失败接口；这不保证任意上层解析都会接受这些字节。IV被改与密文被改是不同对象；CTR计数输入被改也不是密文bit错误传播的同一结论。

## 规范输入与状态合同

AES128 key与块恰16byte；公共数据至多4096byte，原生bytes才接受，bytearray/bool/None/错误长度拒绝。`gf_mul`只接原生0–255整数，不接bool、float、NaN/inf。ECB/CBC要求数据长度是16倍数，零长度允许，不加入/移除填充；CBC IV恰16byte。正逆变换标志只接原生bool。

CTR的 `start` 恰为原生非bool整数 $0\le start<2^{128}$，按完整128bit大端编码。所需块数为ceil(len/16)，区间是 `[start,start+blocks)`；若终点大于 $2^{128}$ 先拒绝。最后值可处理16byte但不能17byte；空消息不消耗区间。这里只处理byte粒度，不实现非整byte尾部。NIST允许其他满足唯一性的计数布局/模递增，本包拒回绕是选定的更严格合同，不称普遍标准要求。

`CTRRangeGuardDemo` 先验证输入、检查区间重叠，再调成熟库加密，成功后才登记非空区间。它不分配nonce，不记录持久历史，不协调其他对象/方向/进程，不擦除key，也不实现数据库事务。源码其他ECB/CBC/CTR函数为无状态机制接口，不替调用者判断历史IV/计数范围是否安全；通过静态长度检查也不能验证IV随机源的不可预测性。

## 独立核查与未覆盖接口

非作者已用另一条多项式乘积/长除路线核全部65536对byte乘法，独立求逆与仿射核256项S-box；对照NISTCore前两块80个阶段，三种38A公开向量、24组变key/block的独立AES与LibreSSL逆运算、1024个Mix逆基向量、11种CTR尾长/顶界、43个拒绝/状态保持与CBC/CTR代数均通过。完整主文、7道题答、1张 Mermaid 的机制语义、两旧页局部返程及相关路径/精确锚点也已由非作者独立核查通过；两源码镜像字节精确。独立复跑7tests 0.089秒PASS，CLI结果与正式data及作者run逐字节相同。这是内容、字节与有限行为核查，未做Obsidian实际视觉预览，也不是一般密码安全证明。

生产接口仍高重要性，且未由本包认证：秘密key生成/轮换/保管、CBC IV在选明文前的不可预测生成及其认证、跨重启/并发/多节点的CTR计数范围唯一性与耗尽、协议明确的填充/长度编码与错误信号、认证失败前的明文释放策略、成熟AEAD组合合同、硬件/缓存/功耗/常数时间以及真实传输栈。教学分支/查表不能用于真实秘密；向量通过也不是FIPS模块认证。

没有运行远程/硬件、真实TLS、Obsidian视觉或真人学习验证。分组工作模式接续已具体到本单元，签名具体数学、公钥加密与一般AKE/组合理论仍为#170后续；不在此自行关闭整课。
