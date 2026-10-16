---
domain: "计算机知识"
type: "practice"
stage: 4
aliases: []
prerequisites:
  - "[[计算机知识/35-计算机网络/10-系统课程/现代密码学DH中间人与认证转录]]"
  - "[[计算机知识/_labs/modern_crypto_aead/README]]"
sources:
  - "https://www.rfc-editor.org/rfc/rfc7748.html#section-6.1"
  - "https://www.rfc-editor.org/rfc/rfc8032.html#section-7.1"
  - "https://cryptography.io/en/stable/hazmat/primitives/asymmetric/x25519/"
  - "https://cryptography.io/en/stable/hazmat/primitives/asymmetric/ed25519/"
---

# 公开 DH、主动中间人与认证转录实验

先读 [[计算机知识/35-计算机网络/10-系统课程/现代密码学DH中间人与认证转录|主解释]]，预测本实践中哪些对象应一致、哪些改动应在哪个阶段拒绝。本实验重要性高：代数正确但未认证的 DH 可以让中间人各持一把合法 key，身份映射、全转录或状态阶段漏项也会改变认证含义。不能用“最后解密成功”替代这些断言。

使用成熟库 X25519/Ed25519/HKDF/HMAC/ChaCha20-Poly1305；程序只实现**离线教学协议 WWL-HS/1 的消息字节与同步状态**，没有手写曲线、签名或生产密码。没有网络、随机秘密、远程服务、真实攻击对象。所有 key、私有输入、挑战 nonce、签名与派生结果公开，因而本包不能保密。

## 规范输入与已经跑出的输出

- [public-vectors.json](public-vectors.json)：RFC 7748 §6.1 双方私有/公开值及共同值、RFC 8032 §7.1 Test1/2 原始向量；SHA-256 为 `0907d2d1607e028d86975e9d4ddca73423642b0f38a86ab1bef356355bb31e67`。
- [handshake_lab.py](handshake_lab.py)：规范源码，导入无执行/网络/写入；CLI 才运行。`small_group` 保留完整22项幂表与MITM值；`Endpoint` 为一份待处理转录的同步实例。
- [test_handshake_lab.py](test_handshake_lab.py)：公开值/有限恒等式、全部11转录字段绑定、角色反射、身份/pin/本地值、签名/Finished失败状态保持、重放与重启反例。
- [[计算机知识/_labs/modern_crypto_handshake/源码与验证|源码与验证]]：上述两规范源逐字镜像，修改真源后同步，不能分叉成另一个实现。
- [requirements.txt](requirements.txt)：本次直接依赖 cryptography 50.0.2；不是间接依赖/平台wheel的供应链锁文件。
- [[计算机知识/_labs/modern_crypto_handshake/data/results.json|data/results.json]]：本次正式默认结果，包括环境、原始向量、401字节完整转录、双签名/双Finished、四派生key、记录、MITM与X25519接受/拒绝语义。
- [[计算机知识/_labs/modern_crypto_handshake/data/author-check.txt|实际执行记录]]：作者真实输入命令、8tests与CLI结果、资源范围；本机路径只作历史出处，下面提供便携复算。

复用 **相邻已交付** `modern_crypto_aead/aead_lab.py` 的 `encode_context`、`MemoryNonceGuardDemo` 与 `ReplayLedgerDemo`，不复制或修改它。复用源SHA-256为 `7f293e4d8ed157be86f117ce2b5bfdf0563c7da7951f7b9e3afe56a6cfcdcf4f`（首单元提交2e0eeda）；结果记录实际导入身份。没有重跑旧1488改动实验，也不把旧测试计作本次新运行。

`data/` 是保留的本次输出，不在原位覆盖。源码与固定输入用于复算，环境与新结果留在库外。如果复用源以后修改，应记录新源身份和新结果，不能仍称本记录的同版重现。

## 复算入口与资源

需要 Python 3.10+ 和兼容库；本次复用隔离的 Python3.12.11/cryptography50.0.2（OpenSSL4.0.3 后端、arm64 macOS27.0.1），未另装依赖。下面示例为换机时新建库外环境。已备环境可直接指定解释器，不需重复安装：

```bash
vault="/你的知识库绝对路径"
lab="$vault/计算机知识/_labs/modern_crypto_handshake"
work=$(mktemp -d "${TMPDIR:-/tmp}/wwl-handshake.XXXXXX")
python3 -m venv "$work/venv"
"$work/venv/bin/python" -m pip install -r "$lab/requirements.txt"
"$work/venv/bin/python" -B -m unittest discover -s "$lab" -p test_handshake_lab.py -v
"$work/venv/bin/python" -B "$lab/handshake_lab.py" --output "$work/fresh-output"
```

集成后的默认依赖路径是相邻AEAD源码；在只含新文件的隔离候选测试时，可显式设置 `WWL_AEAD_SOURCE` 为可信完整库内的该规范源。这个环境变量是本地执行配置，不是网络消息提供的可加载代码路径；不要给不可信消息设置它。程序对结果目录要求全新且位于源码外，先完成运算再创建目录，不覆盖既有输出。

本次通过全局两槽 runner，单进程、线程限制1、超时120秒，预计数秒、实际远低于5分钟。最终作者 **8tests 0.035秒 PASS**，默认生成exit0。早期运行用于形成候选，最终保留的是 `author-run-final-20261016` 输出，未将旧中间结果冒作最终运行。依赖准备、测试耗时都不构成性能/常数时间测量。

## 独立预期、结果与失败判据

所有字节/整数/布尔值要求精确相等，容差为零；没有使用统计拟合“看起来相似”。

| 支撑的断言 | 先推的期望 | 实际结果与失败条件 |
|---|---|---|
| 小群代数正确但可枚举 | p23/g5阶22，a6/b15给A8/B19/Z2；484对指数均一致 | 全部符合，枚举公开表可找回6/15；任一恒等式不符失败 |
| 未认证DH允许MITM | E1=17/E2=21，双方分别与Eve为12/7 | 小群逐值符合；X25519两腿各自匹配Eve、彼此不同；Eve读到0100并另腿合法发送0900 |
| RFC7748接口 | 两公开值和双方共同值等于§6.1 | 所有32字节逐字相同；不是安全性证明 |
| RFC8032接口 | Test1空消息与Test2单字节72的公开key/64byte签名匹配 | 两例逐字相同并验证；有限成功不证明EUF-CMA |
| 固定转录 | 四块编码共401字节，全部11字段/角色均参与 | 独立手组转录相同；改字段的旧签名失败，I/R角色反射失败 |
| 认证前提 | 预期身份/pin/context、本地临时公钥和挑战一致，才承诺一份T | 错值及选定全零贡献在commit前拒绝；承诺后另一T拒绝；坏签名不派生/保存key |
| 全部认证与key确认 | 双方4key分别相等，混用MITM两转录签名失败；Finished改位/反射失败 | 全部符合；完整HMAC字节保留于results；失败不得提前置位 |
| 数据开放阶段 | 本端已经发送且验过对端Finished才开放 | 之前seal/receive拒绝；I可先confirmed而R仍authenticated，不能推出对端收到了最后消息 |
| 有限重放/新鲜性 | 本实例重复Finished/操作拒绝；新本地挑战拒旧转录；新key拒旧Finished | 符合；完全复用fixture重启仍接受旧token的反例也保留在测试，故不承诺持久重放防护 |
| X25519输入语义 | 高位别名与u=p+9可接受并得到等价值；选定低阶/等效全零输入拒绝 | 高位别名和9/p+9等价通过，u=0,1,p−1,p,p+1均ValueError；没有“一律拒非规范编码”策略 |

测试没有让真实攻击者更换本端可信身份表。修改可信表就是改变信任假设，应在迁移题另分析；一个攻击者自己的签名通过，不会自动成为对原Bob key的伪造。原包重放也不等于在新消息上赢签名EUF-CMA。

## 同步状态与公开接口

`Proposal` 为固定11字段的数据类；本协议只接受特定协议/suite与本端context。身份是非空、至多32byte的原生bytes，双方不同；xi/xr/ni/nr/vi/vr各恰32byte；context至多128byte；签名64byte，Finished32byte。role只接受原生bytes `I/R`；可变bytearray、bool、错误shape/长度先拒绝。类型/长度/阶段/预期值不符为ValueError；格式合规的错误Ed25519签名或HMAC由成熟库抛InvalidSignature。X25519选定全零贡献输入实际由exchange抛ValueError，包装另有全零检查。

`sign` 通过本地期望与零贡献检查、成功签名后才commit，随后只能重签相同T。`authenticate` 要求自己已commit，检查两角色签名后才保存派生key和数据封装。`finished` 保存本端已发送位；`accept_finished` 先HMAC验证后置对端已接收位；两位均true才confirmed。这里“发送”是函数返回一个token并记录本地意图，不是实测网络送达；“收到”是本端验证输入成功，也不证明对端知道此结果。

这里没有通用网络反序列化器。四个固定四字段块是内部规范字节，复用旧编码；主文给出可唯一解码的理由。哈希仅将完整T送进HKDF/Finished，Ed25519直接签角色前缀加完整T；并未误用Ed25519ph。

数据封装完全继承上一单元的消息4096byte、sealed4112byte、12byte nonce与四字段各128byte限制。应用operation_id仍由应用定义，内存账本不保存事务结果、不解决授权、并发和多节点同步；nonce guard也不分配或持久保存nonce。所有实例字段可供教学观察，不能当成防攻击者进程内存篡改的安全模块。

## 核查与仍未验证的高重要性接口

非作者先不import作者代码，用独立Montgomery ladder与库核RFC7748公开值/共同值、两种等价编码与5个零贡献负例；独读RFC8032并核两签名向量，小群484对等式也通过。随后独立手组401byte转录，用stdlib HMAC推4个HKDF key、双Finished及独立AEAD输出均一致；41个状态保持拒绝、33个构造非法case和11字段绑定检查通过。最终8tests独复跑0.038秒PASS，CLI与作者最终结果内容一致。完整主文、题答、两张 Mermaid 的机制语义、两旧页接续与两源码镜像也已由非作者独立核查通过；这是内容与字节层核查，未做 Obsidian 实际视觉预览。数值与有限接口检查仍不能替代一般安全证明。

高重要性但本机公开fixture未覆盖的接口逐项是：

- **秘密与生命周期**：真正的安全随机临时DH输入、签名key保管与轮换、临时秘密擦除、密钥泄漏时机；本包公开输入不存在保密性或前向保密实测。
- **身份来源**：生产身份注册、证书链/服务名/时间/用途/吊销，或其他可信key分发；本包仅预置固定映射，不运行CA/TLS服务。
- **协议状态**：挑战值跨重启与并发新鲜性、消息重传/乱序/超时、会话匹配、多用户攻击和协商降级；本包固定suite且一实例只承诺一份T。
- **记录与业务**：持久nonce唯一性、跨节点重放窗口、数据与操作去重的事务性、授权与副作用；本包仅同步内存set，不作生产部署。
- **实现/平台**：一般AKE/计算安全归约、全输入有效性分类、侧信道/常数时间、随机源与HSM/硬件行为；有限向量、拒绝和接口测试不能证明这些性质。

未运行远程服务、真实握手抓包、硬件或Obsidian预览，未声称真人学习已验。TLS1.3 CertificateVerify与Finished按各自阶段绑定此前转录，WWL-HS/1只作机制对照；不能把本包输出作为TLS互操作性或通用AKE认证。#170其余课程范围保留，不由这个单元自行结项。
