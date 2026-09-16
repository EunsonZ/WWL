---
domain: "计算机知识"
type: "course"
stage: 3
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]"
  - "[[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curlHTTPie与接口重放]]"
sources:
  - "https://docs.openssl.org/3.5/man1/openssl-verification-options/"
  - "https://docs.openssl.org/3.5/man1/openssl-s_client/"
  - "https://www.rfc-editor.org/rfc/rfc9525.html"
  - "https://docs.openssl.org/3.5/man1/openssl-verify/"
  - "https://docs.openssl.org/master/man1/openssl-s_client/"
  - "https://www.kali.org/tools/testssl.sh/"
  - "https://www.kali.org/tools/sslyze/"
  - "https://www.rfc-editor.org/rfc/rfc8446.html"
content_status: "usable"
evidence_status: "partial"
---

# TLS证书与服务配置评估

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]；[[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curlHTTPie与接口重放]]。

## 把“HTTPS 正常”拆成可检查命题

一个 TCP 连接成功，未必完成 TLS；TLS 握手成功，未必正确认证域名；证书链可信，也不保证应用授权正确。必须分别检查协议支持、协商参数、证书链、名字、时间和业务层安全。

本包静态服务使用 HTTP，不附证书私钥或可复用 CA。下方在线连接示例属于扩展练习，需要你自己的本机 TLS 服务与受限教学 CA；离线实验 K 则自行生成一次性合成证书，不需要服务。

## TLS1.3握手中，密钥协商、签名与记录保护各做什么

在典型的证书认证、临时密钥协商握手中，密钥协商使双方得到共享秘密；证书链与服务标识验证把公钥和预期服务联系起来；对握手内容的认证与 Finished 等机制保护握手一致性；随后记录层使用派生密钥保护应用数据。不要把“证书公钥加密了全部 HTTPS 数据”当作统一模型。TLS 1.3 也存在 PSK 等模式，不能把典型证书流程说成所有握手的必经路径。[^v5-tls13]

TLS 1.3 的 cipher suite 主要指定记录保护的 AEAD 算法与密钥派生所用散列，不再像旧版命名那样把所有认证与密钥交换选择塞进一个名字。看到某个套件名称，仍不能省略签名算法、密钥交换组、身份与验证政策的检查。

前向保密关心的是长期密钥后来泄露时，过去会话是否仍受保护，其条件涉及握手模式、临时秘密和保留数据。它与“请求不会重复执行”不是同一性质；TLS 1.3 的 0-RTT 数据有重放风险，需要协议及应用层限制。[^v5-tls13] 这个区别连接 [[计算机知识/Kali/03-Web与API安全/12-现代API业务逻辑与并发边界|幂等与重复执行]]：加密传输不能自动保证业务恰好执行一次。

## SNI、HTTP Host 与 ALPN 分别做什么

SNI 在 TLS 握手中帮助服务选择名字相关配置；HTTP Host 或 HTTP/2、HTTP/3 中对应的 authority 表达应用目标；ALPN 协商应用协议。使用同一个 IP 的多个站点可能在这些层分别路由。连接 IP、验证名字和请求名字不一致时，应先解释预期拓扑，而不是看到任何不匹配就报漏洞。

`curl --resolve` 可以在保持 URL 主机名的同时指定连接地址，便于自有虚拟主机的受控实验；它不是忽略证书校验。客户端代理、TLS 终止网关和后端明文段需要分别标注观察点。

## OpenSSL s_client 的最小观察

```bash
# 可选：8443 是你自己的 TLS 服务；lab-ca.pem 只包含公开 CA 证书
# openssl s_client -connect 127.0.0.1:8443 -servername web.lab.test \
#   -verify_hostname web.lab.test -verify_return_error \
#   -CAfile lab-ca.pem </dev/null
```

`-connect` 指连接地址，`-servername` 提供 SNI，`-verify_hostname` 检查名字，`-verify_return_error` 使验证错误影响握手处理。默认的诊断客户端可能打印验证错误后仍继续某些操作，所以不能只凭“显示了证书”宣称验证通过。具体接口以安装版 OpenSSL 为准。[^s1]

查看一个公开证书文件可用：

```bash
# 只读公钥证书，不处理私钥
openssl x509 -in server-cert.pem -noout -subject -issuer -dates -ext subjectAltName
```

CN 与 Subject Alternative Name、签发者与本地信任锚、有效期与吊销状态都有不同含义。不存在一个“加密位数高，所以一定可信”的单一指标。

## 四类证书工具输出如何拼成一个判断

OpenSSL 的 `x509` 主要查看或处理证书对象；`verify` 根据明确的信任输入和策略评估证书链；`s_client` 建立诊断连接并展示协商信息。离线链校验不等于已经访问了预期网络端点，连接成功也不等于所有身份校验失败都会让诊断工具终止。适用的 `verify_hostname`、`verify_ip`、`verify_return_error` 和信任材料需要明确。[^v5-openssl-client][^v5-openssl-verify]

综合 TLS 配置扫描器适合枚举版本、算法与候选配置问题，但其多次探测可能落在不同负载均衡后端。应保留每次观察的端点、SNI、信任库、时间和工具版本，再与单次握手的证据对应。工具之间出现差异时，先比较验证输入，不要直接把某一个“绿灯”当作裁判。

本包的 [[计算机知识/Kali/07-综合实验/14-实验K离线证书链与身份校验|实验K]] 只支持它实际构造的离线证书案例；它不是本轮对外部 TLS 服务或所有 OpenSSL 版本的实测。

## 离线证书链校验与在线服务检查分开做

叶证书声明一个服务身份；中间证书连接到上级；信任锚由客户端策略预先信任，不因为服务器发送过来就自动可信。检查链还涉及用途、约束、名字和时间。下面只读公开证书文件，不需要私钥，也不会建立连接。[^v2-opensslverify]

```bash
# 扩展练习：这些固定文件名需另行准备；实验 K 会在临时目录动态生成独立证书。
# openssl verify -CAfile lab-root-public.pem \
#   -untrusted lab-intermediate-public.pem -purpose sslserver \
#   -verify_hostname web.lab.test server-cert.pem
```

把中间证书交给 `-untrusted` 是让校验器尝试构建链，不是把它单独提升为可信根。命令结果只反映给定信任库、时钟、用途及输入下的校验；没有配置吊销信息和相应检查时，不能声称“已完整核验吊销状态”。

## testssl.sh 与 SSLyze

testssl.sh 适合检查 TLS 协议、密码套件与相关配置；SSLyze 可做程序化 TLS 分析并输出结构化结果。[^s2][^s3] 它们会建立多次连接，不能把“只看证书”与“完整协议扫描”混为一谈。

```bash
# 先查询本机命令与帮助，名称可能随包打包方式变化
command -v testssl.sh
command -v testssl
testssl --help
sslyze --help
```

若本机仅有 `testssl.sh`，使用该名字查帮助。具体扫描项目按目标与授权选择，不照抄过期的 cipher 名称或默认策略。以下仅作 SSLyze 的本机扩展形态：

```bash
# sslyze --certinfo --json_out ./output/tls.json 127.0.0.1:8443
```

使用 IP 可能无法正确代表虚拟主机名，必要时查该版本的 SNI/名字参数或使用受控名字解析；不要把错误证书误判成整个服务配置错误。

## 为常见错误保留诊断分支

“unable to get local issuer”优先检查链是否缺中间证书以及信任库是否匹配；名字不匹配检查 SAN、URL 名字和 SNI；尚未生效/过期检查证书日期与客户端时钟；协议协商失败检查客户端与服务的协议交集。实际 OpenSSL 文本依版本而变，以上是问题族而非固定字符串判定器。

修复后用相同信任策略重跑，保留合法客户端通过、错误名字拒绝与无信任根拒绝等正反例。通过 `-k` 消除报错会改变要验证的命题，不是证书问题的修复。

## 把证书验收拆成独立的反例

证书链、参考身份、用途与时间分别回答不同问题。服务端把某个根证书发来，不会自动让客户端信任它；证书颁给 `web.lab.test`，也不表示它能证明 `other.lab.test`。本轮新增 [[计算机知识/Kali/07-综合实验/14-实验K离线证书链与身份校验|实验 K]]，在临时目录生成根、中间和叶证书，用真实 OpenSSL CLI 分别改变一个条件。

| 保持正确链不变后的修改 | 要检验的边界 | 不能使用的替代判断 |
| --- | --- | --- |
| 改参考 DNS 名或 IP | SAN 中对应类型的服务身份匹配 | 证书能被成功解析 |
| 移走中间证书或换信任根 | 路径构建与信任锚 | issuer 文本看起来相同 |
| 改为客户端用途 | EKU/用途约束 | 公钥强度足够 |
| 把校验时刻移到有效期外 | 时间条件 | 当前文件修改时间很新 |
| 改签名字节 | 证书签名完整性 | 名字与有效期仍能打印 |

实验使用 `-no-CAfile -no-CApath -no-CAstore` 排除默认信任来源，再显式指定教学 `-CAfile`。`-untrusted` 提供待构建路径中的中间证书，不意味着把它提升为预先信任的根。`-attime` 改的是本次校验时间，不修改操作系统时钟。[^v3-verify]

### SAN 的类型是合同的一部分

RFC 9525 将参考身份与证书中呈现的身份分开，并要求服务名称匹配使用相应 SAN 类型，而不是把 Common Name 当成通用服务身份。DNS 名与 IP 是不同类型；把 IP 作为 URL 主机使用时，不能靠证书恰好有一个解析到该 IP 的 DNS 名来替代对应匹配。具体应用协议还可增加自己的约束。[^v3-identity]

本实验的 SAN 显式包含 `DNS:web.lab.test` 与 `IP:127.0.0.1`，因此分别测试两种身份，而不是依赖实现可能保留的旧 CN 回退。标准要求与某个库兼容行为必须分别记录，不能把一次 OpenSSL 接受结果泛化成所有浏览器都接受。

### 两个“成功”反例

第一个是没有指定身份的链校验：它可以成功，却没有回答“这是不是我要找的主机”。第二个是诊断工具继续运行：`s_client` 的诊断行为允许在某些验证错误后继续，需要 `-verify_return_error` 等选项表达拒绝政策；只看到握手输出不是完整验收。[^v3-sclient]

离线 verify 也没有验证在线服务持有私钥、协议协商、应用认证、吊销或浏览器信任策略。实验 K 的通过范围是 11 个明确证书案例，不能直接写成“站点 TLS 已安全”。这条边界与 [[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curl 的传输/HTTP/业务三通道]] 是同一种证据分层。

## 风险结论需要使用场景

过时协议支持、弱算法或错误证书可能有不同影响。是否存在兼容需求、是否经过 TLS 终止代理、客户端是否允许降级，都影响优先级。TLS 1.3 的密钥协商机制与旧协议不同，不能套用旧版握手说明。[^s4]

一个服务关闭某协议后，应同时验证安全目标和正常客户端兼容性；修复不是把所有连接都断掉然后取得“扫描无风险”。记录修复前后同一 SNI、地址、时间、客户端版本和测试项目。

## 自检

`curl -k` 成功而正常校验失败，证明了什么？它支持“在放宽证书验证条件下能完成某种连接”，并不支持服务器身份可信。应检查根信任、名字、链和时间，而不是把 `-k` 加进所有脚本。

## 来源与核验范围

[^v5-tls13]: [RFC 8446：TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html)；定位：§2、§4.1.2、§4.4、§8：协商、认证、早期数据重放。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-openssl-client]: [OpenSSL 3.5 — openssl-s_client](https://docs.openssl.org/3.5/man1/openssl-s_client/)；定位：DESCRIPTION、verify_hostname、verify_return_error、servername。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-openssl-verify]: [OpenSSL 3.5 — Verification options](https://docs.openssl.org/3.5/man1/openssl-verification-options/)；定位：证书链、身份与 purpose 验证参数。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [OpenSSL 官方：s_client](https://docs.openssl.org/master/man1/openssl-s_client/)；定位：-connect / -servername / -verify_hostname / -verify_return_error。网页读取：2026-09-05。
[^s2]: [Kali 官方：testssl.sh](https://www.kali.org/tools/testssl.sh/)；定位：协议与证书检查；以本机可执行文件名为准。网页读取：2026-09-05。
[^s3]: [Kali 官方：sslyze](https://www.kali.org/tools/sslyze/)；定位：扫描项目与 --json_out。网页读取：2026-09-05。
[^s4]: [IETF RFC 8446：TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html)；定位：§2 Protocol Overview / §4 Handshake。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-opensslverify]: [OpenSSL 3.5：verify](https://docs.openssl.org/3.5/man1/openssl-verify/)；定位：Trust / Untrusted intermediates / -purpose / -verify_hostname。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-verify]: [OpenSSL 3.5：verify](https://docs.openssl.org/3.5/man1/openssl-verify/)；定位：-CAfile / -untrusted / -no-CA* / -attime / -purpose。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

[^v3-identity]: [RFC 9525：Service Identity in TLS](https://www.rfc-editor.org/rfc/rfc9525.html)；定位：§1.3；§2；§6 服务身份匹配。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

[^v3-sclient]: [OpenSSL 3.5：s_client](https://docs.openssl.org/3.5/man1/openssl-s_client/)；定位：-verify_return_error；-verify_hostname；诊断验证行为。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]