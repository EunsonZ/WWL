---
domain: "计算机知识"
type: "course"
stage: 2
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]"
  - "[[计算机知识/Kali/02-信息收集与网络测量/05-WiresharkTcpdump与Tshark|WiresharkTcpdump与Tshark]]"
sources:
  - "https://scapy.readthedocs.io/en/latest/usage.html"
  - "https://www.kali.org/tools/nmap/"
content_status: "usable"
evidence_status: "partial"
---

# ScapyNping与协议实验

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]；[[计算机知识/Kali/02-信息收集与网络测量/05-WiresharkTcpdump与Tshark|WiresharkTcpdump与Tshark]]。

## 从报文格式理解工具输出

Scapy 把协议层表示为对象，用层叠组合构造报文，也能把字节重新解析成字段。它同时具备离线构造与发包能力；本章先使用不联网的构造/读取操作，避免把“调用库”误当成“不会产生网络行为”。[^s1]

```python
# 说明性片段：需要事先安装 Scapy；这里只构造字节，不调用 send/sr
from scapy.all import Ether, IP, TCP, raw
packet = Ether(src='02:00:00:00:00:10', dst='02:00:00:00:00:20')/IP(src='192.0.2.10', dst='192.0.2.20')/TCP(
    sport=40000, dport=8000, flags='S', seq=1000
)
blob = raw(packet)
parsed = Ether(blob)
print(parsed.summary())
print(parsed[IP].len)
```

显式写出源和目的地址，避免库为了自动填地址而查询路由。`raw` 序列化时会计算某些自动字段；`show` 与 `show2` 的显示阶段不完全相同。逐层检查字段比只看一行 `summary()` 更能发现长度和校验和问题。

## 长度与序号必须有单位

IP 总长度包含 IP 首部及其负载；TCP 数据偏移描述 TCP 首部长度；TCP 序号按字节而非包数前进。一个以太网帧长度还包含链路层字段，某些采集文件不保存物理前导码或 FCS。把这些数直接相减之前，必须明确各自边界。

课程夹具中，一个请求放在一个 TCP 数据段里，是为便于手算，不代表互联网请求总是一包。[[计算机知识/Kali/07-综合实验/03-实验B抓包重组与证据交叉验证|实验 B]] 要求对照请求字节数和确认号，检查你是否把协议段当成业务消息。

## 读取 PCAP 与最小推断

```python
# 说明性片段；只读教学文件
from scapy.all import rdpcap, IP, TCP
for packet in rdpcap('http-lab.pcap'):
    if IP in packet and TCP in packet:
        print(packet[IP].src, packet[TCP].sport, packet[TCP].flags)
```

对于大文件，整批 `rdpcap` 可能占用大量内存；应考虑流式读取。过滤后只见 TCP，不说明源文件不存在其他协议，因为条件已经排除了它们。解析失败也不应被静默忽略成“无异常”。

## Nping 与 hping3 的定位

Nping 用于受控地构造探测并比较响应、往返时间等；hping3 也是报文构造/探测工具。它们很容易放大发包量，因此本课程仅给回环、小次数示意：

```bash
# 自建回环 HTTP 已启动；使用普通 TCP connect 模式，不伪造来源
nping --tcp-connect -p 8000 -c 3 127.0.0.1
```

Nping 的参数及模式见当前 Kali 帮助。[^s2] 不把此类工具用于洪泛、来源伪造或第三方压力测试。几次连接的响应时间不是稳定的服务性能基准；系统调度、首次连接与缓存都会影响它。

## 反例与迁移

“我用 Scapy 造了一条 SYN 包，因此服务端已经建立了可用 HTTP 会话。”不成立，构造字节并未发出；即使发送了 SYN，也还缺握手状态和应用交换。手工构造与内核维护 TCP 状态不同。

自检：如何区分离线构造失败与网络丢包？前者应先检查序列化字节、长度和本地解析；后者需要发送记录与接收/采集证据。不要从终端没有输出直接跳到“目标防火墙拦了”。

## 序列化之后才检查自动字段

构造对象时留空的长度或校验和，可能在序列化阶段才由工具计算。不能直接读取构造对象中的 `None` 就认定包无效。可靠的离线检查顺序是：显式填关键端点和协议字段 → 序列化成字节 → 从字节重新解析 → 比对长度与校验和。[^v2-scapy]

前面的唯一构造片段已同时指定合成 IP 与以太网 MAC，避免把链路地址隐式补全混入离线实验。`02:` 开头在此作为本地管理的教学 MAC 值。重新解析后还可读取 `parsed[TCP].dataofs * 4` 检查 TCP 首部的字节长度；`dataofs` 的计数单位不是字节，而是 32 位字。保留一个完整构造示例，避免两个版本相互漂移。

## 校验和为什么还包含伪首部

TCP 校验和不只是 TCP 负载的摘要，它还包括 TCP 首部及来自 IP 层的伪首部字段，用于让端点地址与协议等信息参与检查。它用于传输错误检查，不是密码学认证；能重新计算校验和的人仍能构造新包。不要把“校验和正确”推成“来源可信”。

本包生成器用独立字节构造合成 PCAP，旧测试直接核对总长度、序号和校验和。新知识页不把 Scapy 解析成功伪称成这些字节测试的替代品。二者若不一致，应保留双方结果并检查封装、字节序和填充，再处理问题。

## 从整包加载迁移到有界读取

`rdpcap` 适合小型夹具；大文件应考虑 `PcapReader` 一类逐包读取接口，给出包数和资源预算。逐包读取节省整文件驻留内存，不意味着协议重组不再需要状态。流的数量和长度仍可能使分析资源增加，必须限制输入规模，而不是只把函数名换成“stream”就宣布可处理任意文件。[^v2-scapy]

## 来源与核验范围

[^s1]: [Scapy 官方 Usage](https://scapy.readthedocs.io/en/latest/usage.html)；定位：Stacking layers / Reading PCAP / raw / show2。网页读取：2026-09-05。
[^s2]: [Kali 官方：nmap 包及当前帮助](https://www.kali.org/tools/nmap/)；定位：Packages and Binaries：nmap / ncat / ndiff / nping。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-scapy]: [Scapy 官方：Usage](https://scapy.readthedocs.io/en/latest/usage.html)；定位：packet construction / raw bytes / reading PCAP。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]