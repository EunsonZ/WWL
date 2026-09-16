---
domain: "计算机知识"
type: "course"
stage: 2
aliases:
  - "抓包"
  - "Wireshark"
  - "PCAP分析"
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]"
  - "[[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]"
sources:
  - "https://wiki.wireshark.org/CaptureSetup/Offloading"
  - "https://www.wireshark.org/docs/wsug_html_chunked/ChAdvReassemblySection.html"
  - "https://www.rfc-editor.org/rfc/rfc9293.html"
  - "https://www.wireshark.org/docs/man-pages/tshark.html"
  - "https://www.kali.org/tools/tcpdump/"
content_status: "usable"
evidence_status: "partial"
---

# WiresharkTcpdump与Tshark

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]；[[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]。

## 抓包是观察，不是全知视角

PCAP/PCAPNG 保存捕获到的数据包及元信息。某个采集点看不到的流量，可能被其他接口处理、被加密、在别的命名空间中，或因采集丢包而缺失。抓到包也不保证应用真正处理了它。

Wireshark 适合交互式分层查看与流重组；tcpdump 适合受控采集和快速阅读；Tshark 适合可重复的字段提取。采集权限应尽量交给专门组件，不让整个 GUI 以管理员身份处理任意文件。工具接口见官方手册。[^s1][^s2]

## 捕获、重组、解析、显示是四道不同的门

**捕获**决定哪些数据进入证据文件；**重组**把分片或流中的片段放回可供上层处理的顺序；**协议解析**把字节解释成字段；**显示与导出**决定最后看到什么。前一道缺失的信息，后一道通常不能凭空恢复。抓包工具、解析器与显示过滤表达式因此不是可互换的概念。[^v5-tshark][^v5-ws-reassembly]

设一帧原始长度 1500 byte，但抓取上限只保留 96 byte。后续即使显示出 IP 与 TCP 字段，也不能宣称完整 HTTP 正文已检查；在保存下来的 96 byte 里没有敏感词，不能证明未保存的部分没有。反过来，显示过滤器暂时隐藏一帧，不等于原 PCAP 删除了它。复核时必须区分“原始输入不在”“输入在但没重组”“已解析但显示过滤掉”。

`tcpdump` 适合围绕采集与简要解码保留输入；`dumpcap` 着重采集；Tshark 把 Wireshark 的解析能力带到命令行；Wireshark GUI 便于互动追踪关系。二次解析、首选项和字段多值导出会改变可用上下文与呈现方式，因此两份 CSV 的差异未必来自不同网络事实。具体参数承接前文，额外关键条件是相同输入与相同解析设置。[^v5-tshark]

## 捕获过滤器与显示过滤器

捕获过滤器在采集阶段决定哪些包进入文件，通常使用 BPF 语法；显示过滤器在已有数据上按解析字段选择显示。二者不能互换。

| 目的 | 捕获过滤器示例 | 显示过滤器示例 |
| --- | --- | --- |
| TCP 8000 | `tcp port 8000` | `tcp.port == 8000` |
| 一个 IPv4 地址 | `host 192.0.2.10` | `ip.addr == 192.0.2.10` |
| HTTP 请求 | 通常不能用 HTTP 解析字段表达 | `http.request` |
| SYN 且非 ACK | 需基于字节/标志写 BPF | `tcp.flags.syn == 1 && tcp.flags.ack == 0` |

IP `192.0.2.x` 在此仅存在于教学文件，不要求实际发包。捕获时丢弃的数据无法靠显示过滤器恢复；展示时隐藏的数据仍可能存在于文件里，分享前不能只截一张“干净截图”就上传整包。

## 分层阅读与流重组

先确认帧时间与接口，再看以太网/IP/TCP，最后解释 HTTP。Wireshark 的 Follow TCP Stream 可重组字节流，但“能看见文本”仍需对应方向和连接。TLS 流量通常只能直接观察握手及加密记录等元数据，不能从端口号或大小单独推断具体内容。

使用 `tcp.stream` 标识同一解析会话，但它是工具本次分析赋予的索引，不是线上协议字段。不同文件合并或不同解析设置可能改变编号。

```bash
tshark -r http-lab.pcap -Y 'tcp.stream == 0' \
  -T fields -e frame.number -e tcp.seq -e tcp.ack -e tcp.len
```

默认相对序号与包中的原始序号不是同一显示方式。需要精确核对时记录 Wireshark/Tshark 的 TCP 相对序号设置。

## 重组成功与应用当时看到什么仍不是同一句话

重组需要相关片段、序号关系和足够完整的采集。中途开始抓包、捕获丢包、乱序或首选项差异，都可能导致上层被显示为延续数据、未知记录，或把完整消息呈现在后来的某一帧上。Wireshark 文档明确说明部分乱序重组与二次解析的表现受这些条件影响。[^v5-ws-reassembly]

因此“HTTP 在第 50 帧显示出来”不必然表示服务器直到第 50 帧才第一次处理消息；那也可能是解析器在该处终于拿到足够上下文。需要时把序号、实际到达时序、应用日志与解析显示分开。TCP 字节空间已在本页前文解释；跨代理的应用身份则继续到 [[计算机知识/Kali/03-Web与API安全/13-HTTP中间层与消息解释|HTTP 中间层]]。

> [!question] 迁移检查
> 同一 PCAP 在两个首选项配置下，一份出现 HTTP 记录，一份只显示 TCP 数据，能否说业务流量发生变化？不能。输入未变，先比较重组、解码、解密材料和显示过滤器；这是解释过程变化的候选证据。

## 先离线阅读，再显式采集

本包带有完全合成的 `http-lab.pcap`，不包含真实用户流量。进入 [[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|实验夹具目录]] 后：

```bash
capinfos http-lab.pcap
tcpdump -nn -r http-lab.pcap
tshark -r http-lab.pcap -Y 'http.request' \
  -T fields -e frame.number -e ip.src -e http.request.method -e http.request.uri
```

`-r` 读取文件，不启动在线采集。`-nn` 避免名字与服务名解析，保留数值地址/端口。数据包文件本身也可能是恶意解析器输入，真实取证应使用隔离环境与更新后的解析软件。

需要自己的回环抓包时，在另一个终端显式启动并手动停止：

```bash
# 只捕获自建回环 8000 服务；按 Ctrl-C 结束，不等待 50 个包一定出现
sudo tcpdump -i lo -nn -s 0 -c 50 \
  -w "$HOME/kali-lab/output/loopback.pcap" 'tcp port 8000'
```

`-s 0` 请求捕获完整包（仍受工具/链路等实际上限影响），文件可能含敏感内容。`-c` 限制包数，不是墙钟时间；没有足够流量时会继续等待。采集仅对获准的接口与数据进行。

## 从文件完整性到字段导出的具体顺序

先用 `capinfos` 看文件格式、封装类型、时间范围与包数，再用 `tshark -n` 禁止名字解析。`frame.cap_len` 是捕获到的长度，`frame.len` 是记录的原始帧长度；前者更小提示截断，不能将缺失负载解释为线上真的没有数据。

```bash
# 在原有合成夹具目录内执行；全部为离线读取。
tshark -n -r http-lab.pcap -T fields \
  -E header=y -E separator=, -E quote=d \
  -e frame.number -e frame.time_epoch -e frame.cap_len -e frame.len \
  -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport -e tcp.len

tshark -n -r http-lab.pcap -q -z conv,tcp
tshark -n -r http-lab.pcap -q -z follow,tcp,ascii,0
```

`-E quote=d` 给字段加双引号；一个包中某字段可能重复，导出后的字段不一定就是一个原子值。字段型 CSV 的统计仍须定义多值政策。会话统计与流跟踪是两种视图，不应把两个输出相加当请求数。[^v2-tshark]

## 协议没有被识别时，不要先改结论

非标准端口、截断、缺少握手或解析设置，都可能让 HTTP 字段为空。已知本文件 8000 是教学 HTTP，可进行显式 Decode As：

```bash
tshark -n -r http-lab.pcap -d tcp.port==8000,http \
  -Y 'http.request or http.response' -T fields \
  -e frame.number -e http.request.method -e http.request.uri -e http.response.code
```

`-d` 是你告诉解析器如何解释，不是工具独立确认了协议；应在记录中标出。`-2` 可做两遍分析，但不能创造缺失包，某些实时或输出场景也不适用。更换设置后保留原始 PCAP 和解析命令，不能覆盖原始证据。[^v2-tshark]

## 重组、重传和抓包方向的反例

若请求分两段且第一段漏采，即使 TCP 总体成功，分析端也可能无法恢复完整 HTTP。若同一包在多个接口被重复捕获，简单相加会重复计数。若网卡卸载尚未计算传输校验和，发送侧观察到的异常不必等于接收侧异常。

Wireshark 的专家提示是可调查线索，不是最终因果判决。查找“重传”后至少看原始序号、ACK、时间差和对端日志，并明确该标记是分析器推断。解密 TLS 需要适当会话密钥材料且具有授权；密钥日志和解密后的包都应按敏感资料处理，不能为了课程展示上传真实会话。

## 重传字节不能当成新的业务数据

用一个不涉及序号回绕的原创例子手算：同一方向两次捕获的 TCP 负载区间分别是 `[1,101)` 和 `[51,151)`。这里左闭右开，长度均为 100 字节。逐包相加是 200，已观察到的不同序号位置只有 150，重复覆盖 50。若只统计 `tcp.len` 总和，就把重传或重叠部分再次计入了。

这个集合计算仍不等于恢复了 150 字节可信应用内容。两个区间的重叠字节可能一致，也可能冲突；接收端如何处理、抓包是否遗漏其他段、应用层是否压缩或加密，还需单独核对。SYN/FIN 会消耗序号空间，却不是这两个负载区间中的应用字节。[^v3-tcp]跨连接不能直接合并同样的序号，跨方向也不能混算。

接着观察累计 ACK。它能帮助判断对端 TCP 对字节序列的确认进展，但不等于应用已经授权、写盘或提交事务。HTTP 响应、应用事件与数据库状态才是其他层的证据。[[计算机知识/Kali/07-综合实验/15-实验L事务幂等与并发控制|实验 L]] 中提交失败后回滚的情形，就不能靠“对端 ACK 了请求”来排除。

### 解析设置也是输入的一部分

导出字段前可用本机 `tshark -G fields` 核对名称，用 `tshark -G currentprefs` 留下需要的解析设置；不要直接公开全部配置输出。TCP 相对序号、重组、Decode As、解密材料等都会改变可见字段。`-T fields` 中同一帧的多次字段出现需声明选取规则，不能假定 CSV 一格永远对应一个协议对象。[^v3-tshark]

一个实际检查表只需围绕三个数：包/帧数、唯一传输字节范围、业务请求数。它们必须分别定义计数单位，再解释差别。本包 `http-lab.pcap` 用来练习字段与请求对应；上述重叠区间是纸面推演，**没有把原夹具改造成重传抓包，也未在本环境运行 Tshark**。把案例出处写清楚，是避免“示意数据看起来像实测”的必要步骤。

## 为什么本机看到的坏校验和不一定在线路上也是坏的

某些网卡卸载机制把校验和计算或分段工作推迟到采集点之后完成。主机抓到的是尚未由硬件完成处理的数据表示，于是可能出现部分校验和或看起来超过链路 MTU 的大块数据。[^v5-ws-offload] 这不是许可我们无条件忽略异常，而是增加一个需要区分的解释。

原创比较：发送主机的捕获标出 checksum 异常，接收端对应数据却正常且 TCP 流推进。该组合支持“发送侧观察位置与卸载有关”的假说；若线路观察与接收端也显示失败，则应考虑真实损坏。单端截图无法区分两者。不要为了让界面变绿就直接修改生产网卡设置；本轮仅解释机制，不进行此类配置变更。

## 常见误判

校验和异常可能来自网卡卸载和采集位置，不一定是传输损坏。重传标记可能是网络重传，也可能与漏采、乱序或解析状态有关。TCP 分段卸载与聚合可能让宿主机采集看到的段大小不同于物理线上真实帧。应结合另一侧抓包或应用日志交叉判断。

`capinfos` 的包数、`tshark -Y http.request` 的请求数、访问日志行数可能不同，首先检查 [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS#^observation-unit|观察单位]]，不要立即认定某个工具错了。

自检：显示过滤器隐藏了 Cookie 包，原 PCAP 是否已脱敏？没有。必须产生审阅后的脱敏副本，并说明删减对证据解释的影响。

## 证据质量的三个检查点

采集是否覆盖正确接口和时间；文件是否被截断、损坏或过滤；解析器是否采用了预期版本与设置。这三题都回答之后，才能把包级结论迁移到 [[计算机知识/Kali/06-取证逆向与检测/08-SuricataZeek与网络检测|流与检测日志]]。一张 Follow Stream 截图不应代替全部三题。

## 来源与核验范围

[^v5-tshark]: [Wireshark：tshark(1)](https://www.wireshark.org/docs/man-pages/tshark.html)；定位：capture filter / display filter / -2 / -T fields / occurrence。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-ws-reassembly]: [Wireshark：Packet Reassembly](https://www.wireshark.org/docs/wsug_html_chunked/ChAdvReassemblySection.html)；定位：TCP reassembly；重组依赖与设置。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-ws-offload]: [Wireshark：CaptureSetup/Offloading](https://wiki.wireshark.org/CaptureSetup/Offloading)；定位：Checksum offload / segmentation offload。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Wireshark 官方：tshark(1)](https://www.wireshark.org/docs/man-pages/tshark.html)；定位：-r / -f / -Y / -T fields / -e。网页读取：2026-09-05。
[^s2]: [Kali 官方：tcpdump](https://www.kali.org/tools/tcpdump/)；定位：命令帮助与依赖；上游站点读取失败后使用此源。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-tshark]: [Wireshark 官方：tshark 手册](https://www.wireshark.org/docs/man-pages/tshark.html)；定位：-n / -2 / -Y / -T fields / -E / -d / -z。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-tshark]: [Wireshark：Tshark 官方手册](https://www.wireshark.org/docs/man-pages/tshark.html)；定位：-G fields / currentprefs；-T fields；-E occurrence。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

[^v3-tcp]: [RFC 9293：TCP](https://www.rfc-editor.org/rfc/rfc9293.html)；定位：§3.4 序号空间、确认与 SYN/FIN。v3 读取：2026-09-05；数值区间为原创推演。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]