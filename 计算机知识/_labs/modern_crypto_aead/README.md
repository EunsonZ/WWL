---
domain: "计算机知识"
type: "practice"
stage: 4
aliases: []
prerequisites:
  - "[[计算机知识/35-计算机网络/10-系统课程/现代密码学安全目标与组合]]"
sources:
  - "https://www.rfc-editor.org/rfc/rfc8439.html#section-2.8.2"
  - "https://www.rfc-editor.org/rfc/rfc5869.html#appendix-A.1"
  - "https://cryptography.io/en/stable/hazmat/primitives/aead/"
---

# 公开向量、有限安全游戏与 AEAD 字节边界

本实践回答一个明确问题：四行 OTP 表、认证解密的失败、nonce 复用、上下文与重放，分别改变了哪一项可检查结果？先读 [[计算机知识/35-计算机网络/10-系统课程/现代密码学安全目标与组合|主解释]] 并预测，再复算。所有 key、nonce、消息、HKDF IKM 与 salt 都是公开教学输入；没有真实秘密、网络目标、认证请求或攻击服务。

**实验重要性高**：nonce 复用、认证前释放明文、字段边界歧义或把无状态解密当成防重放，都会改变受保护消息的含义。验证因此同时保留原始公开向量、精确概率、拒绝行为与状态改变次序。所调用的成熟 AEAD/HKDF 库处理密码运算，本目录没有手写生产算法；演示内存 guard/ledger 也不是可部署的信道组件。

## 输入、规范源码与保留输出

- [public-vectors.json](public-vectors.json)：RFC 8439 §2.8.2 与 RFC 5869 A.1 的公开输入和期望输出，含原始出处。向量文件 SHA-256 为 `82d2e4feebbae5c0f1b335f95a3e0fe3a0ae7342ef34452571da34f2923037d2`。
- [aead_lab.py](aead_lab.py)：规范源码；导入只加载标准库，不运行实验，不联网。`finite_games` 用精确分数；`library_checks` 调用成熟库做有限 API 检查。
- [test_aead_lab.py](test_aead_lab.py)：后验、复用/翻位、概率、编码、公开向量、类型/长度、失败认证不污染 ledger 等回归。
- [[计算机知识/_labs/modern_crypto_aead/源码与验证|源码与验证]]：上述两个 Python 文件的逐字 `code-sync` 镜像，供库内阅读；不能把镜像当成另一个可编辑真源。
- [requirements.txt](requirements.txt)：本次直接依赖 `cryptography==50.0.2`；不是软件供应链锁定文件，平台 wheel 与间接依赖由实际环境记录约束。
- [[计算机知识/_labs/modern_crypto_aead/data/results.json|data/results.json]]：2026-10-16 本次实测输出，含 Python、库、OpenSSL 后端、平台和向量 SHA；保留为历史证据，不在原位复算覆盖。
- [[计算机知识/_labs/modern_crypto_aead/data/author-check.txt|作者运行记录]]：实际命令、测试摘要与资源范围。它不替代非作者独核，也不是通用安全认证。

固定输入和规范源码可用于重新运行；`data/` 是已经跑出的结果。复算环境与结果写全新的库外目录，避免让一次新执行覆盖旧证据。无须复制执行环境、uv 缓存或临时过程材料进知识库。

## 复算命令与资源

需要 Python 3.10+ 和上述 `cryptography` 版本。若复用已有相容环境，可直接指定其 Python；下面展示独立临时环境。示例使用 `mktemp` 创建唯一的库外父目录，`fresh-output` 本身尚不存在，满足程序不覆盖的合同。

```bash
lab="/你的知识库绝对路径/计算机知识/_labs/modern_crypto_aead"
work=$(mktemp -d "${TMPDIR:-/tmp}/wwl-crypto.XXXXXX")
python3 -m venv "$work/venv"
"$work/venv/bin/python" -m pip install -r "$lab/requirements.txt"
"$work/venv/bin/python" -B -m unittest discover -s "$lab" -p test_aead_lab.py -v
"$work/venv/bin/python" -B "$lab/aead_lab.py" --output "$work/fresh-output"
```

上述命令安装依赖与本地运行；不启动远程任务或硬件。并行课程实验可采用现有全局两槽 runner，单进程、线程 1，超时 120 秒；源码本身不用并行数值库。此次环境为 Python 3.12.11、cryptography 50.0.2、arm64 macOS 27.0.1；后端实际报告 OpenSSL 4.0.3。作者 7 tests 0.037 秒通过，生成命令也 exit 0。环境准备与依赖下载不计作课程数值实验，测试耗时也不是密码操作性能或侧信道测量。

CLI 要求新输出目录，不接受已存在目录，也不允许写在源码目录内；先完成全部运算再创建结果目录。失败退出应保留异常，不应被改成“部分通过”。不同版本可另建环境复验，但不能用新版本结果悄悄替换本记录的身份。

## 先写期望，再检查结果

| 检查对象 | 独立可推的期望 | 本次实测与失败判据 |
|---|---|---|
| 2-bit OTP | 四行各为 00–11 的排列；任意先验在看到单个密文后不变 | 精确表匹配；先验 $(1,2,3,4)/10$ 后验不变。后验改变即失败 |
| 左右消息游戏 | 均匀 key 单挑战成功率 1/2；偏置 key 为 3/4；两消息同 key 为 1，独立 key 为 1/2 | 四个精确分数一致，无浮点容差 |
| 确定性明文标签的比较攻击 | 理想随机两位标签有 32 种等可能情形，成功 28 次，即 7/8 | 精确一致；此例不是安全 MAC 的实现 |
| RFC 8439 | 114 字节明文，114 字节密文与 16 字节 tag；公开值应逐字节一致 | 130 字节完全一致；tag=`1ae10b594f09e26a7e902ecbd0600691`，任何字节偏差失败 |
| 有限篡改拒绝 | 固定公开样本改动后不释放明文 | key 256、nonce 96、AAD 96、密文含 tag 1040 次逐位改动全部 InvalidTag；130 种较短前缀全部拒绝。一次接受即失败 |
| 公开 nonce 复用误用 | 去掉 tag 后两密文 XOR 等于两明文 XOR | 均为 `0000000000080000`；不宣称实测了 Poly1305 伪造 |
| 上下文边界 | 朴素拼接 AB/C 与 A/BC 为相同字节；长度前缀编码不同 | 前者用另一语义字段仍成功，后者 InvalidTag；625 个有限 tuple 无碰撞，通用单射性由固定长度解码论证 |
| 无状态与应用重放 | 原三元组两次解密均成功；已见操作再次登记应拒绝 | 原语两次返回同明文；ledger 第二次拒绝，认证失败不预占 operation_id；新 nonce 的同 operation 也拒绝 |
| nonce guard | 同对象重复 nonce 拒绝；新对象丢失历史 | 两者均符合预测；后者说明它不能承诺持久唯一性 |
| RFC 5869 A.1 | PRK 与 42 字节 OKM 与公开 SHA-256 向量一致 | 两值逐字节相同；两个公开方向派生样例不同，不据此宣称一般密钥独立性 |

上表改 key 的 256 次是**错误密钥拒绝的接口一致性检查**，不是攻击者可以给实际接收方更换秘密 key 的 INT 游戏。单 bit 检查只是选定样本；没有穷举全部有效 tag、全部输入或真实密钥分布。认证成功的原包重放不算新伪造，不能为了让检查表“全拒绝”而篡改这一结果。

## 输入和状态合同

`MemoryNonceGuardDemo` 与 `open_record` 仅接受原生 `bytes`：key 恰 32 字节、nonce 恰 12 字节、消息至多 4096 字节、sealed 至多 4112 字节。上下文是恰四项的 list/tuple，每项 bytes 且至多 128 字节。类型/边界错误为 `ValueError`；格式合规但认证不通过为库的 `InvalidTag`。空消息/AAD 字段可表示，短于 tag 的 sealed 由库认证解密拒绝。长度是 byte，不是 Unicode 字符个数。程序不替网络文本归一化、不推测编码，也不接受 bytearray 暗示可变输入。

sender 全部输入校验并成功加密后才记录 nonce；receiver 固定预期协议/会话/方向，认证成功之后才检查并登记 operation_id、向调用者返回明文。失败输入不会留下“已经使用”状态。这只是同步单进程顺序，不涵盖并发原子性和业务副作用。`MemoryNonceGuardDemo` 不持久保存，不分配 nonce；`ReplayLedgerDemo` 不保存事务、身份和授权。不要直接把本练习封装装到服务端。

上下文编码的四字段顺序是协议本身的一部分；换协议版本、改字段个数、采用自由拼接均属新合同，不能只修改一端。HKDF 例也使用同一明确字段编码，但以不同前缀字段值表示用途；实际协议应把派生信息结构固定在双方共同认可的版本里。

## 核查和未覆盖项

非作者核查者已先独立实现 oracle，再读作者封装：公开 RFC 8439 全向量、上述 1488 个单 bit 改动与 130 截断、RFC 5869 的 stdlib HMAC 推导均符合期望；还独立核对 OTP 非均匀后验与复用/翻位。随后对作者候选做 89 个边界/状态拒绝检查、9 个空/最大长度互操作检查、625 个 tuple 编码及失败认证不污染 ledger 的检查，7 tests 独立复跑通过（0.048 秒）。安全游戏、组合前提、完整主文与 TLS/KDF 两处局部返程也已由非作者独立核对；单候选完整性界的 $q_d$ 损失与 bit-guess 优势约定已对照教材，EtM 的 nonce/PRF/独立 key/编码条件已对照原论文。源码镜像与本次保留结果另核身份一致。这些内容与有限行为均已完成相应独核，有限测试本身仍不能替代一般安全证明。

本实践没有证明计算安全、常数时间、功耗/缓存/错误通道抗性、随机源质量或一般的标签不可伪造性；没有运行 HSM、TLS 抓包、CA 链、握手或远程服务。高重要性的生产接口还包括：可靠秘密生成与保管、密钥认证与轮换、跨设备和重启的 nonce 唯一性、受认证字段的实际网络编码、持久/并发去重、业务事务与授权、库构建与平台侧信道。这些需要各自模型、审计或真实环境验证，不能由公开 fixture 替代。

本次也不宣布 #170 完课：DH/签名/握手认证及更广的构造仍保留后续单元。读者能复算本例不等于已经观察到真人理解；主文题目可用于自检，未记录真人学习结果。
