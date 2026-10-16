---
domain: "计算机知识"
type: "practice"
stage: 4
aliases: []
prerequisites:
  - "[[计算机知识/35-计算机网络/10-系统课程/现代密码学RSA加密与签名编码]]"
sources:
  - "https://www.rfc-editor.org/rfc/rfc8017.html"
  - "https://www.rfc-editor.org/rfc/rfc7520.html"
  - "https://cryptography.io/en/stable/hazmat/primitives/asymmetric/rsa/"
---

# 公开 RSA：CRT、编码与成熟接口

这份实践支撑 [[计算机知识/35-计算机网络/10-系统课程/现代密码学RSA加密与签名编码|RSA 加密与签名主解释]]。**重要性高**：漏掉非互素消息、把裸幂运算当安全方案、搞错PSS高位/盐或混用加密/签名key，会改变正确性或安全目标。实验因此核代数、结构失败、编码、用途与具体拒绝路径，不只做一次roundtrip。

**全部私有参数已经公开**：两key均取RFC7520，模数都为2048bit。没有生成新key、真实凭据或生产秘密。Python pow/CRT、MGF1与编码检查只用于这些公开数学证据，不是生产密码；实际加解密/签验用成熟cryptography。没有网络、远程攻击、TLS服务或硬件。

## 输入与规范源

- [public-fixtures.json](public-fixtures.json)：Figure4的`use=sig` key、Figure73的不同`use=enc` key、Figure20的完整PS384 JWS向量，以及公开固定seed32/salt48；SHA-256=`25c576d985cf4ca8cc28327f025d91cfaf1cf5fbb32203fd02ef2c64425c6f4d`。base64url折行仅按RFC §1.1移除排版空白；没有生成另一套key。
- Figure73在原RFC用于旧RSA1_5方案；本课**只消费其公开key数字**，没有运行该旧方案，也不建议把生产旧key跨方案复用。这些已公开私有数字不在真实安全key的假设中。
- [publickey_lab.py](publickey_lab.py)：规范源；导入仅定义接口，不运行实验/联网/写入，不生成新key。教学编码与公共块检查的命名明确带`public`；成熟API包装固定用途和参数。
- [test_publickey_lab.py](test_publickey_lab.py)：全部55余数、CRT非互素点、编码边界/高位、官方向量、512个指定改动拒绝、随机样本关系、类型/长度/用途合同。
- [[计算机知识/_labs/modern_crypto_publickey/源码与验证|源码与验证]]：上述两文件逐字镜像，以Python为真源，不分叉编辑。
- [requirements.txt](requirements.txt)：直接依赖cryptography50.0.2，不是间接依赖/wheel供应链锁文件。

已有数学CRT真源只引用，旧AEAD源码只读复用规范四字段编码；实际复用SHA记于results（`7f293e4d…cdcf4f`）。没有复制/重写前几单元实现，也未重跑旧AEAD、DH或AES大实验。

## 固定结果与随机观察分开保留

- [[计算机知识/_labs/modern_crypto_publickey/data/results.json|results.json]]：固定代数、官方向量与公开固定seed/salt编码、完整EM/密文/签名、参数、版本、拒绝计数；随机部分仅记两次返回关系和本次是否不同。
- [[计算机知识/_labs/modern_crypto_publickey/data/randomized-samples.json|randomized-samples.json]]：成熟库实际生成的两份OAEP密文和两份PSS签名原始字节，消息与私有参数均公开。新执行会用新随机量，**不要求与旧samples字节相同**；应分别解密/验签，并检查固定编码结果。
- [[计算机知识/_labs/modern_crypto_publickey/data/author-check.txt|author-check.txt]]：作者实际命令、6tests、资源和证据分账。

RFC7520 Figure20是外部既有签名，可验证但不要求重新随机签出同样bytes。固定seed/salt的OAEP/PSS是本课**自建**公开编码样例，由独立规范步骤与成熟库互核，不伪装成RFC外部OAEP测试向量。随机样本两次不同也不构成随机源/熵或不可伪造性证明。

`data/`为这次已运行证据，不覆盖。复算输出应写全新的库外目录；两份随机附件字节可能不同，保留的新环境与结果也不混成旧运行身份。

## 命令、环境与预算

本次复用Python3.12.11、cryptography50.0.2，OpenSSL4.0.3后端，arm64 macOS27.0.1；未新增依赖。下面是独立环境的换机例；已有兼容环境可直接运行：

```bash
vault="/你的知识库绝对路径"
lab="$vault/计算机知识/_labs/modern_crypto_publickey"
work=$(mktemp -d "${TMPDIR:-/tmp}/wwl-rsa.XXXXXX")
python3 -m venv "$work/venv"
"$work/venv/bin/python" -m pip install -r "$lab/requirements.txt"
"$work/venv/bin/python" -B -m unittest discover -s "$lab" -p test_publickey_lab.py -v
"$work/venv/bin/python" -B "$lab/publickey_lab.py" --output "$work/fresh-output"
```

集成后自动读取相邻`modern_crypto_aead/aead_lab.py`。仅含本候选的隔离区运行时，可显式给`WWL_AEAD_SOURCE`指定可信完整库内该规范源；这是本地执行配置，不可由不可信消息设置代码路径。

正式运行经现有全局两槽runner，单进程、线程限制1、超时120秒，预计数秒且小于5分钟。作者 **6tests 0.387秒PASS**，CLI exit0；依赖准备另计，不作性能或常数时间测量。程序要求新输出目录并禁止写源码内部，先完成全部检查再建目录并写两份JSON，已有结果不覆盖。

## 事前期望、实际结果与失败判据

数学/固定向量/格式要求精确一致，容差零；随机输出只验证声明的关系，不检验字节复现。

| 支撑断言 | 独立可推的期望 | 本次结果与失败条件 |
|---|---|---|
| RSA含非互素正确性 | p5/q11/n55/λ20/e3/d7全部55余数都还原；m5→c15→5 | 全部符合，15个非单位未排除；CRT和直接pow一致 |
| textbook结构失败 | m3无回绕得c27；c23乘2³→19，解24后乘28→12；s2自造m8 | 精确符合；不是外部解密服务或真实攻击 |
| 公布key与CRT | 两RFC私有key关系/CRT参数成立，两用途模数不同 | 成熟库验证key数字；0/1/p/q/n−1等CRT与直接pow相同 |
| 外部PSS向量 | RFC7520 Figure20 PS384在Figure4 key下通过；salt48 | 验签通过，公开幂还原的EM独立检查符合；不要求重签同字节 |
| OAEP固定编码 | SHA256/MGF1SHA256/空label；k256，max190byte | 公开seed00..1f的编码被库解密为55byte规范消息；PS135；191byte先拒 |
| PSS固定编码 | SHA384/MGF1SHA384/salt48，emBits2047、emLen256 | 固定盐00..2f编码与私有CRT签名被库验过；PS158、高位1bit清零、trailerbc |
| 指定篡改 | 每byte翻最低bit；不释放OAEP明文或接受PSS错误签名 | 各256次拒绝；这是512个有限样本，不是穷举全部攻击 |
| 参数/用途错误 | OAEP错hash/非空错label，PSS错消息/错pubkey/盐47、raw s2；用途互换 | 选定例均拒绝；错label是库参数负例，不把非空label称RFC本版约定 |
| 库随机行为 | 两次公钥加密分别解密，两次签名分别验证 | 都成立，本次两对输出不同；原始字节单独保留，不能据此证明随机质量 |

本例加密载荷带`alice-to-bob`也不自动认证Alice：公开key允许任何人生成合法OAEP密文。PKE的CCA隐私、共享key AEAD的完整性、签名EUF-CMA与业务重放不是同一目标，不能为凑“全拒绝”改变定义。

## 接口合同与私有数学的边界

包装只接受已加载的**这两份公共fixture对象**；加解密要求`enc`，签验要求`sig`。key对象不是网络输入，不接受临时构造的另一份对象；这只是教学用途guard，不是HSM、权限或key管理安全边界。公开的私有对象与数字都可被观察，绝不承担秘密保管。

消息/seed/salt/EM/密文/签名要求原生bytes，拒bytearray/bool/None。OAEP消息至多190byte、seed恰32、密文恰256；PSS消息教学上限4096byte、salt策略恰48、签名恰256。范围/长度/用途错误ValueError；格式合规但无效PSS为库InvalidSignature，OAEP解码失败ValueError，不返回部分消息。

教学MGF输出长度0–512，hash只接sha256/sha384；教学PSS emBits是原生非bool整数，限定777–4096，emLen=ceil(emBits/8)，对非整byte边界也清高位。RSA代表元限定原生非bool整数0≤x<n；NaN/inf/float/bool/负数/上界均拒。OAEP检查器只处理固定256byte公共EM，PSS检查器只按本48byte盐策略；它们有数据相关分支与错误细节，不可用于真实私有解码服务。PSS标准允许其他明确盐策略，包括0，教学范围不等于标准全域。

MGF/固定编码/公开CRT是机制展示；真正加解密/签验调用成熟库。异常类别测试不验证跨错误耗时一致，RSA库/平台的blinding、故障抵抗、缓存/功耗和常数时间均未认证。生成过程只用库内部随机量生成公开消息的seed/salt，不产生新key或真实凭据。

## 独立核查与课程边界

非作者已逐原RFC抽取两key全部字段及compact向量，独立SHA/MGF/整数mask构造13组OAEP/PSS（含777/4096bit边界），核55余数/非单位与大CRT点、6实际随机样本反解编码、51个malformed/参数/用途拒绝，通过。独复跑作者6tests 0.341秒PASS，CLI固定results与作者语义相同；随机附件按其解密/验签关系核对，不要求新旧byte相同。完整主文、7道题答、1张Mermaid的机制语义、四旧页局部接续、85个wiki路径/精确锚点与两源码镜像也已由非作者独立核查通过。正式两附件与作者run字节相同；独立解码保留及fresh共8份随机样本，关系均符合合同。未做Obsidian实际视觉预览；内容、字节与有限接口核查不是一般密码安全证明。

原课程核心是安全目标与对称机制、公钥所需代数/困难假设、DH/签名/身份及TLS责任的连贯解释，不等于证明完整TLS或一般多会话AKE。更广形式模型/归约是扩展，实际部署的key生命周期、信任分发、nonce/重放持久状态/并发/事务、真实证书/远程TLS、HSM/硬件/侧信道仍各有验证接口；未做这些不应抹掉已经完成的数学与有限课程出口，也不能据课程完成声称部署安全。未做Obsidian视觉与真人学习验证。
