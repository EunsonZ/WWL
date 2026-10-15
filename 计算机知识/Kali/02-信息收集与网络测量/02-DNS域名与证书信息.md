---
domain: "计算机知识"
type: "course"
stage: 2
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]"
  - "[[计算机知识/Kali/02-信息收集与网络测量/01-资产范围与被动信息收集|资产范围与被动信息收集]]"
sources:
  - "https://bind9.readthedocs.io/en/latest/manpages.html"
  - "https://www.rfc-editor.org/rfc/rfc4033.html"
  - "https://www.rfc-editor.org/rfc/rfc2308.html"
  - "https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility"
  - "https://www.kali.org/tools/dnsrecon/"
  - "https://curl.se/docs/manpage.html"
content_status: "usable"
evidence_status: "partial"
---

# DNS域名与证书信息

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]；[[计算机知识/Kali/02-信息收集与网络测量/01-资产范围与被动信息收集|资产范围与被动信息收集]]。

## DNS 是可比较的查询实验

DNS 查询记录名字、记录类型、服务器、时间，并补记传输方式；具体失败判读集中在 [[#“没有地址”至少要分成四种解释|四种失败模型]]，字段阅读见 [[#读懂响应中的状态、标志和四个区段|响应字段]]。`dig` 保留 DNS 语境；`host/nslookup` 适合简查；`getent hosts` 可能使用 `/etc/hosts`，不等价于直接 DNS。[^s1]

```bash
# 示例前提：另行自建回环 5353 DNS；本包未启动，不对未授权解析器照抄。
# dig @127.0.0.1 -p 5353 web.lab.test A +noall +answer +comments
# dig @127.0.0.1 -p 5353 web.lab.test AAAA +noall +answer +comments
# dig @127.0.0.1 -p 5353 lab.test SOA
```

## 读懂响应中的状态、标志和四个区段

Question 保存问题；Answer 保存直接答案；Authority 可能给出权威或否定回答相关信息；Additional 提供其他关联记录。用 [[#“没有地址”至少要分成四种解释|四种失败模型]] 判读空 Answer，不能只把 `NOERROR` 当成有 A 地址。[^v2-dnsnegative]

`AA` 表示相应回答来自权威语境；`RD` 是请求递归的标志，`RA` 表示递归能力；`TC` 表示截断。看到截断应在授权范围内考虑 TCP 重试，不能把截断包当完整记录集。`dig +short` 适合快速看答案，却可能隐藏正是诊断所需的状态和区段，因此证据基线不要只保留 short 输出。[^v2-bindmanual]

```bash
# 仅为另行自建的 DNS 教学服务准备；本包没有启动 5353 服务。
# dig @127.0.0.1 -p 5353 lab.test SOA +noall +answer +authority +comments
# dig @127.0.0.1 -p 5353 web.lab.test A +tcp +noall +answer +comments
```

## “没有地址”至少要分成四种解释

**NXDOMAIN** 是名字不存在的否定答复；**NODATA** 不是独立的 RCODE，而是从答复推断出“名字有效，但没有所问类型的数据”；**SERVFAIL** 表示服务器未能完成处理；**超时**则连一个可用 DNS 答复都没有拿到。CNAME 链还要求核对否定针对链上的哪个名字，而不能把所有链上名称都判为不存在。[^v5-dns-negative]

设教学名称 `portal.lab.test` 有 A 记录而没有 AAAA。一次 AAAA 查询得到可确定的 NODATA，并不否定 IPv4 地址；换一个类型不是“推翻前一次 DNS”，而是在问不同问题。若答复是 SERVFAIL，则连“没有 AAAA”也尚未成立。把四者统一写成空字符串，会丢掉决定下一步的最重要信息。

负面结果也可以被缓存。RFC 2308 用 SOA 信息约束相应否定缓存的存活时间；它不是“查询为空便永久为空”。[^v5-dns-negative] 例如某记录在权威服务器刚刚新增，递归解析器仍可能持有尚未过期的否定记录。对此应比较查询时间、解析器、类型与权威答复，不先认定工具失灵或系统遭到篡改。

## TTL、否定缓存和查询时间

TTL 约束缓存使用期限，不是资产寿命。递归返回的剩余 TTL 可不同于权威初始 TTL；否定缓存与新增记录例子统一见 [[#“没有地址”至少要分成四种解释|否定回答模型]]。比较名字、类型、解析器、传输和时间后，再进入 [[#通配解析与假阳性|不存在名字的对照]]，CDN/轮询的一次 IP 变化不能直接证明不同资产。

## 同一个名字为什么在两个客户端里得到不同结果

先固定查询的名字、记录类型、解析器、传输方式和时间，再比较答案。不要只保存 `+short` 后的一行地址，因为它可能隐藏 RCODE、标志、响应来源与否定回答的上下文。`NOERROR` 不必然有你要求的记录，命令正常退出也不必然表示域名存在。

下面只供额外自建 DNS 的小范围对照：假设你已显式在回环 1053 端口配置 `lab.test` 区，本包并不启动该服务。完整域名末尾的点避免把它当作相对名字拼接搜索后缀；`+time` 和 `+tries` 限制等待与尝试。[^v3-dig]

```bash
# 扩展练习：先有自己的教学 DNS，再取消注释。
# dig @127.0.0.1 -p 1053 web.lab.test. A +time=2 +tries=1
# dig @127.0.0.1 -p 1053 web.lab.test. AAAA +time=2 +tries=1
# dig @127.0.0.1 -p 1053 web.lab.test. A +tcp +time=2 +tries=1
```

三个请求不是重复扫描：前两个比较地址族，第三个改变 DNS 传输条件。UDP 回答被截断、TCP 53 被路径规则阻断、递归服务器缓存不同，都可能造成答案差异。使用 `+tcp` 成功不能证明所有客户端自动回退正常；应保留各自行为。

系统名称服务、浏览器和显式指定解析器的 dig 不一定经过同一路径。代理在哪里解析目标名、是否使用独立缓存、是否有搜索后缀，都影响观察。排错时先写出“哪个程序问了哪个解析器”，再判断是 DNS 数据问题还是客户端路径差异；相应代理语义见 [[计算机知识/Kali/02-信息收集与网络测量/08-NetcatSocatSSH与受控代理|代理与名字解析]]。

CT 或历史 DNS 中出现过的名字只提供历史关联线索。确认一个域名当前指向你的受测服务，还需要当时的解析、TLS 名字与应用响应证据；这三条证据互补，任何一条都不自动授予测试权限。

## 通配解析与假阳性

若任意不存在名字都被解析到同一地址，一份子域名字典会制造大量“发现”。判断需要比较一个人为构造、预期不存在的随机名字与真实候选的状态、地址集合和响应行为。但随机名探测本身会发请求，应计入预算。

DNSSEC 关注签名与数据认证链，不能单独隐藏域名或修复开放服务。证书透明度、DNSSEC 和 HTTPS 证书校验分别处理不同问题，不要因为都出现“签名”就视为同一机制。

## DNSRecon 与 DNSenum

DNSRecon 支持标准记录、SRV、指定解析器等操作；其区域传送、字典枚举和额外联网选项属于不同活动。[^s2] 明确选择模式，而不是假定默认命令只有一条 A 查询。

```bash
dnsrecon -h
# 以下仅适用于书面批准的自建 DNS；先核对 NS_SERVER 与 DOMAIN
# dnsrecon -d "$DOMAIN" -n "$NS_SERVER" -t std -j ./output/dns.json
```

DNSenum 可作为同类工具比较，但也可能组合多种枚举流程；使用前检查当前帮助与默认行为。区域传送（AXFR）本来是 DNS 服务器间同步区域的机制；若需要评估其访问控制，必须是范围中特别允许的配置检查，不能把它作为所有域名的例行“顺手测试”。

## 工具选择取决于想保留哪一种信息

`dig` 适合明确记录某次查询的类型、服务器与完整答复；目录枚举工具组织的是许多查询的候选与发现；证书透明度或其他被动来源给的是其观察历史中的名字。不要用第三类来源的缺失证明第一类查询必然不存在，也不要因为证书里出现一个名字就把它加入当前授权范围。

具体查询命令见 [[#DNS 是可比较的查询实验|dig 入口]] 与 [[#同一个名字为什么在两个客户端里得到不同结果|1053 条件对照]]。理论上的下一步是把“当前可达、历史出现、名字存在、拥有有效证书、属于授权资产”分成五个命题，回到 [[计算机知识/Kali/02-信息收集与网络测量/01-资产范围与被动信息收集|资产身份与范围]] 分别核对。

## DNSSEC 和加密 DNS 保护的是不同边界

工作定义与 secure/insecure/bogus/indeterminate 统一见 [[#DNSSEC、加密 DNS 和 TLS 服务身份检查互不替代|DNSSEC 主解释]]。操作上，`dig +dnssec` 请求相关记录，不等于本机完成验证；验证失败与没有 A 记录分开，关闭验证后可解析只是区分线索，不能直接作为永久修复。[^v2-dnssec]

## DNSSEC、加密 DNS 和 TLS 服务身份检查互不替代

DNSSEC 主要提供 DNS 数据来源认证和完整性保护，并可支持经认证的不存在证明；它不负责把查询内容加密，也不保证解析出的服务安全。RFC 4033 还区分 secure、insecure、bogus 和 indeterminate：可信链验证成功、已知没有相应安全保护、应受保护但验证失败、以及缺少足够信任起点，不是四种程度的“可疑”。[^v5-dnssec]

这里的 `insecure` 是协议验证分类，不是已被入侵的诊断。`bogus` 也需要进一步查签名、时钟、链和数据，而不是直接归因于攻击。一次响应里带 AD 位，还需要信任给出该位的验证解析器及相关交付路径；不要把任意来源的一位标志当作本机亲自验证完全部链条。

加密 DNS 传输着重保护到解析服务的通道。HTTPS 的服务身份检查则比较预期服务名称和对端证书。即使 DNS 记录本身通过验证，连接端仍应完成 [[计算机知识/Kali/03-Web与API安全/10-TLS证书与服务配置评估|TLS 服务身份核验]]；反之，一个可信证书也不自动证明先前所有 DNS 查询均受完整性保护。

## 域名与证书关联的边界

A 与 AAAA 指向不同地址族；CNAME 需要继续解析；MX 和 SRV 可能指向不在本次授权内的第三方。跟随依赖不自动扩大授权。证书的主题备用名称可提供域名线索，但通配符证书不意味着每个子域都实际部署了服务。

课程例子：`web.lab.test` 返回两条 A 记录，一台响应正常、一台超时。应分别保存解析结果与每个连接目的；把一次请求结果推广为整个域名永久可用，会忽略负载均衡与路径差异。

## 连接到 HTTP 验证

本地 Web 案例可以用 curl 的 `--resolve` 在单条请求中把名字绑定到特定地址，同时保留正确的 URL 主机名；这比修改整个系统 hosts 文件更容易限定和回滚。操作见 [[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|curl 与接口重放]]。若涉及 TLS，还要检查 SNI 与证书名字，而不是只改 Host 字段。

自检：域名解析到一个云服务 IP，是否可以扫描这个 IP 的所有端口？不能，IP 可能共享，授权通常基于具体租户和服务；DNS 依赖只说明路径，不决定法律或业务范围。

## 来源与核验范围

[^v5-dns-negative]: [RFC 2308：DNS Negative Caching](https://www.rfc-editor.org/rfc/rfc2308.html)；定位：§1、§2、§5：NXDOMAIN、NODATA、negative TTL。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-dnssec]: [RFC 4033：DNS Security Introduction and Requirements](https://www.rfc-editor.org/rfc/rfc4033.html)；定位：§3.1、§3.2、§5：数据真实性、限制、响应状态。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [ISC BIND 官方：dig 手册](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility)；定位：dig query options；网页为开发版文档，参数以安装版核对。网页读取：2026-09-05。
[^s2]: [Kali 官方：dnsrecon](https://www.kali.org/tools/dnsrecon/)；定位：std / srv / -n / -t / -j。网页读取：2026-09-05。
[^s3]: [curl 官方命令手册](https://curl.se/docs/manpage.html)；定位：--connect-timeout / --max-time / --proxy / --resolve / --cacert。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-bindmanual]: [ISC BIND 官方：Manual Pages](https://bind9.readthedocs.io/en/latest/manpages.html)；定位：dig options / DNS flags / +tcp / +dnssec。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-dnsnegative]: [IETF RFC 2308：DNS Negative Caching](https://www.rfc-editor.org/rfc/rfc2308.html)；定位：§2 NXDOMAIN and NODATA / §5 caching negative answers。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-dnssec]: [IETF RFC 4033：DNSSEC Introduction](https://www.rfc-editor.org/rfc/rfc4033.html)；定位：§3 Provided Services / §5 Scope / §12 security。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-dig]: [ISC BIND dig 官方手册](https://bind9.readthedocs.io/en/latest/manpages.html)；定位：dig：server / port / +tcp / +timeout / +tries / status。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]