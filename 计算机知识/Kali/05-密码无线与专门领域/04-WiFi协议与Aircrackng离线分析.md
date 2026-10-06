---
domain: "计算机知识"
type: "course"
stage: 4
prerequisites:
  - "[[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]"
  - "[[计算机知识/Kali/02-信息收集与网络测量/05-WiresharkTcpdump与Tshark|WiresharkTcpdump与Tshark]]"
  - "[[计算机知识/Kali/05-密码无线与专门领域/01-哈希口令KDF与估算|哈希口令KDF与估算]]"
sources:
  - "https://www.rfc-editor.org/rfc/rfc8110.html"
  - "https://wiki.wireshark.org/HowToDecrypt802.11"
  - "https://w1.fi/wpa_supplicant/"
  - "https://www.aircrack-ng.org/doku.php?id=aircrack-ng"
  - "https://www.kali.org/tools/hcxtools/"
content_status: "usable"
evidence_status: "partial"
---

# WiFi协议与Aircrackng离线分析

**先修关系：** [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|TCPIP路由DNS与TLS]]；[[计算机知识/Kali/02-信息收集与网络测量/05-WiresharkTcpdump与Tshark|WiresharkTcpdump与Tshark]]；[[计算机知识/Kali/05-密码无线与专门领域/01-哈希口令KDF与估算|哈希口令KDF与估算]]。

## 把链路接入和应用安全分开

Wi-Fi 是无线链路。成功接入一个网络，不等于拥有其中每台主机、每条应用会话或捕获他人通信的许可。802.11 管理帧、控制帧与数据帧承担不同职责；SSID 是网络名称，BSSID 通常标识一个基本服务集。信道、频段和网卡工作模式决定能观察到什么，抓不到包不自动表示现场没有通信。

Aircrack-ng 套件包括网卡/捕获相关工具和离线口令验证工具。管理模式用于常规连接；监控模式用于读取适配器支持的无线帧，但受芯片、驱动、虚拟机透传及当地无线规则限制。只改变 Kali 软件无法创造硬件能力。[^s1]

## 先辨认帧类型，再解释认证材料

管理帧帮助发现、关联与管理连接，控制帧参与介质访问，数据帧承载上层流量。抓包文件还可能带 Radiotap 之类无线元数据头，不能把第一个字节按以太网固定偏移解释。链路封装、信道、适配器模式和采集时段是输入合同的一部分。

WPA/WPA2 的接入通常包含发现/关联、相应身份认证与密钥协商等步骤；Personal 与企业 EAP 场景在认证和密钥来源上不同。wpa_supplicant 承担客户端侧协商，接入点侧常见 hostapd；它们与 Aircrack-ng 离线分析处于不同职责。[^v2-wpasupplicant]

## 握手为什么可能支持离线猜测

对某些 WPA/WPA2-Personal 捕获，握手记录提供验证候选共享口令所需的公开参数；工具对候选派生密钥并比较认证结果。这仍是 [[计算机知识/Kali/05-密码无线与专门领域/01-哈希口令KDF与估算|验证猜测]]，不是从“抓到一次握手”直接读出明文口令。握手完整性、网络标识、认证类型与捕获质量是前提。WPA3-Personal 的 SAE 采用不同认证机制，不能直接把这一结论推广到所有 WPA3 模式、混合部署或实现问题。

企业认证、访客隔离、受保护管理帧、证书验证分别处理不同边界，不能由一个“WPA”标签推断整个网络安全。对于具体硬件与 WPA3 条件，本包未实机验证，需结合产品和协议文档另行核查。

## 四次握手究竟提供了什么证据

在典型 WPA2-Personal 分析模型中，共享秘密派生的主密钥并不作为明文口令在握手中发送；握手中的随机数、端点标识与消息认证信息帮助双方派生/确认会话相关密钥。离线验证使用捕获信息检验某候选是否产生一致结果。这里只说明模型，不给出干扰连接或收集他人凭据的步骤。[^v2-aircrack]

“有四个 EAPOL 帧”不必然意味着属于同一可用交换；重传、不同客户端、缺失帧和时间混合都需区分。反过来，工具支持的某些有效验证材料也不应被简单规则“必须恰好四帧”机械拒绝。按工具实际识别结果、协议字段与捕获来源交叉核对。

## PMK、PTK与认证信息：不要把所有密钥叫作WiFi密码

在典型 WPA2-Personal 的简化层次中，口令及网络相关参数参与生成主密钥材料；会话派生结合双方身份与随机数形成临时密钥材料；相应密钥再分别用于确认握手与保护链路数据。主密钥、会话派生材料和某条消息的认证值不是同一个对象。客户端协商由 wpa_supplicant 这类组件处理，Aircrack-ng 的离线功能是在已有适用捕获上检验候选。[^v5-supplicant][^v5-aircrack]

为什么认证值能验证猜测却不直接暴露口令？在本页抽象模型中，每个候选都决定一组派生材料，再决定一个可比较结果。比较一致给出候选与记录相容的证据；这不是将认证值“解密回口令”。实际还要满足算法、捕获关联与字节编码前提，详见 [[计算机知识/Kali/05-密码无线与专门领域/02-HashcatJohn与离线审计|验证流水线]]。

## 密钥派生和保护范围的边界

无线链路加密只覆盖相应无线段；上游路由器、DNS、TLS 与应用授权仍有独立安全边界。企业 EAP 方法和服务器证书校验方式也影响身份保证，不因名称中有 Enterprise 就自动证明所有客户端配置正确。

WPA3-Personal/SAE 与 WPA2-PSK 的离线猜测条件不同；混合模式、终端实际协商结果和实现版本必须明确。不要从扫描列表的 WPA3 标签推断某个客户端此刻实际使用了哪条路径，也不以旧 WPA2 教程推导所有新模式。

## 口令已知、链路解密与应用明文仍是三个问题

Wireshark 对无线解密的输入条件与 Aircrack-ng 的候选验证条件不同，不能把某工具认定可用的材料直接当成另一个工具足够恢复全部会话。尤其在 WPA3 的按连接密钥模型下，网络口令和四次握手并不足以直接解密对应流量；需要相应会话的密钥材料，且不能推广到其他连接。[^v5-wlan-decrypt]

就算受授权的无线链路数据已经解密，其中仍可能是 TLS 密文。无线层的解密成功并不替代应用层身份、TLS 会话密钥或对象授权。此处只讲不同秘密的作用范围，不提供收集或导出其他设备密钥的步骤。

## 加密、对端身份与可用性要分别评价

OWE 提供开放网络场景下的机会式无线加密，但没有因此建立预先可信的对端身份；加密存在与“连接到正确接入点”不能画等号。[^v5-owe] 同样，链路防护也不能保证射频媒介永远可用。评价无线配置时，应分别列链路机密性、对端认证、管理交互保护、客户端实际协商与网络隔离，而不是只打一个 WPA 等级标签。

这一分解与 [[计算机知识/Kali/03-Web与API安全/10-TLS证书与服务配置评估|TLS信任链与服务身份]] 平行：能建立加密通道，不等于已经正确验证通信对象。

## 仅分析自有、已经取得授权的捕获

本包未附无线握手，合成 `http-lab.pcap` 也不是 802.11 数据，不能用于以下步骤。自备数据必须来自专门实验接入点和自己的客户端，不靠干扰周边设备制造握手。

```bash
aircrack-ng --help
# 只读检查自有实验捕获中可识别的网络与握手信息：
aircrack-ng own-wifi-lab.cap
# 只使用你自己设定的小型公开测试候选列表：
aircrack-ng -w own-toy-words.txt own-wifi-lab.cap
```

出现多个网络时，只选择事先授权的那一个。输出有网络条目不意味着具备足够验证材料；先解释捕获缺口，再决定是否需要在独立环境正常连接自有客户端重新生成。

Hcxtools 的 `hcxpcapngtool` 可将适用捕获转换为 Hashcat 支持的格式。应先读 `hcxpcapngtool -h`，确认输入质量与输出模式；例如常见的 `-o own.22000 own-wifi-lab.pcapng` 是格式转换，不是修补缺失握手。原始捕获、转换参数、统计与输出摘要应共同保存。[^s2]

## 套件中高影响工具如何定位

Airmon-ng、Airodump-ng 用于适配器和捕获工作流；Aireplay-ng 可主动注入帧，其某些功能会干扰连接；Wifite 会编排多个步骤，Reaver/Bully 面向 WPS 相关测试。名字并不决定风险，实际行为才决定。此包不提供去认证、WPS 穷举、仿冒接入点或捕获邻居凭据的操作链；独立无线课程应先准备屏蔽/隔离条件和书面范围。这里的实操深度限于文件分析。

> [!question] 自检
> 把一个成功连接的有线网卡抓包改名为 `.cap`，为什么不能让 Aircrack-ng 分析 WPA 握手？文件后缀不是链路类型，也不会生成未被采集的无线认证帧。先用 [[计算机知识/Kali/02-信息收集与网络测量/05-WiresharkTcpdump与Tshark|抓包基础]] 检查封装与观察点。

## 一个有界的离线报告结构

记录捕获来源与授权、哈希、链路类型、允许分析的 BSSID/自有客户端、时间/信道覆盖、握手判定依据、转换统计和候选预算。未知字段标未知；若混有周边流量，先做数据最小化而非直接将完整捕获加入 Vault。

本包仍不含无线捕获、不运行无线发射/采集；这里新增的是协议和判读深度。已有有线 HTTP 夹具不能被拿来伪造无线实验通过记录。

## 来源与核验范围

[^v5-supplicant]: [wpa_supplicant official overview](https://w1.fi/wpa_supplicant/)；定位：WPA/WPA2/WPA3、802.1X与客户端协商职责。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-aircrack]: [Aircrack-ng official — aircrack-ng](https://www.aircrack-ng.org/doku.php?id=aircrack-ng)；定位：WPA/WPA2-PSK候选验证与捕获输入条件。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-wlan-decrypt]: [Wireshark Wiki — How to Decrypt 802.11](https://wiki.wireshark.org/HowToDecrypt802.11)；定位：WPA/WPA2 Enterprise/Rekeys、WPA3 Per-Connection Decryption。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-owe]: [RFC 8110 — Opportunistic Wireless Encryption](https://www.rfc-editor.org/rfc/rfc8110.html)；定位：§1、§4、§7：无身份认证的无线加密及安全边界。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Aircrack-ng 官方：aircrack-ng](https://www.aircrack-ng.org/doku.php?id=aircrack-ng)；定位：离线分析、-w、握手质量与失败条件。网页读取：2026-09-05。
[^s2]: [Kali 官方：hcxtools](https://www.kali.org/tools/hcxtools/)；定位：hcxpcapngtool / 文件转换与握手数据。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-wpasupplicant]: [wpa_supplicant 官方：功能与流程](https://w1.fi/wpa_supplicant/)；定位：WPA/WPA2/WPA3 / EAP / key negotiation。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-aircrack]: [Aircrack-ng 官方](https://www.aircrack-ng.org/doku.php?id=aircrack-ng)；定位：捕获质量、离线输入和候选条件。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]