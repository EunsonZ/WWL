---
domain: "计算机知识"
type: "course"
stage: 5
prerequisites:
  - "[[计算机知识/Kali/02-信息收集与网络测量/05-WiresharkTcpdump与Tshark|WiresharkTcpdump与Tshark]]"
  - "[[计算机知识/Kali/06-取证逆向与检测/07-YARA日志与检测规则|YARA日志与检测规则]]"
sources:
  - "https://docs.suricata.io/en/suricata-8.0.1/rules/intro.html"
  - "https://docs.suricata.io/en/latest/rules/http-keywords.html"
  - "https://docs.zeek.org/en/current/scripts/base/protocols/http/main.zeek.html"
  - "https://docs.zeek.org/en/current/reference/logs/conn.html"
  - "https://docs.suricata.io/en/latest/output/eve/eve-json-output.html"
  - "https://docs.suricata.io/en/latest/quickstart.html"
  - "https://docs.zeek.org/en/current/quickstart.html"
  - "https://docs.suricata.io/en/latest/command-line-options.html"
content_status: "usable"
evidence_status: "partial"
---

# SuricataZeek与网络检测

**先修关系：** [[计算机知识/Kali/02-信息收集与网络测量/05-WiresharkTcpdump与Tshark|WiresharkTcpdump与Tshark]]；[[计算机知识/Kali/06-取证逆向与检测/07-YARA日志与检测规则|YARA日志与检测规则]]。

## 从“包里有什么”到“网络行为是什么”

Suricata 是网络威胁检测引擎，可按配置和规则分析流量；Zeek 更侧重协议解析与结构化日志。二者都受输入、配置、重组与解析支持限制：加密流量不提供全部应用正文，截断 PCAP 也不会因换一个工具而恢复丢失字节。[^s1][^s2]

使用本包合成 `http-lab.pcap` 做离线分析，不在网卡上启动持续监听。本包读取的 Suricata `latest` 页面实际标为开发版文档；CLI 思路有据，但本机稳定版的配置和字段仍须核对，不能把网页标识当作已安装版本。[^s1][^s3]

## 包、流、应用事务与业务动作：四个计数单位

网络检测可以对单个包、重组字节流或解析后的应用字段进行判断，而一次业务动作又可能跨多个请求。Zeek 的 HTTP 日志用连接 `uid` 与事务相关字段描述观察；`trans_depth` 是该连接中请求/响应事务的流水线深度语义，不应脱离协议和采集条件当成跨系统全局请求 ID。[^v5-zeek-http-fields]

原创例子：一个连接承载三次教学 HTTP/1.1 请求，每个请求触发两条不同规则。这里可能同时出现 1 个连接、3 个事务和 6 条告警；如果一个事务响应丢失，这些计数又可能不完整。不能把六条告警写成六个独立攻击者或六个成功业务动作。修复应改变所针对的状态或行为，不以简单减少日志行数为唯一指标。

## Sticky buffer 改变的是匹配对象，不只是速度

Suricata 的 sticky buffer（粘性缓冲区）先指定后续条件应用的协议字段。`http.uri` 与 `http.uri.raw` 分别面向规范化和未做该规范化的 URI 表示；响应体缓冲区还涉及解码与检查长度。这里的 raw 仍是解析出的字段，不等于从以太网帧开头到结尾的全部原始字节。[^v5-suricata-http]

因此，两条相同字符条件放在不同缓冲区，检验的是不同命题。若分析器将某些表示视为等价，而后端不这样解释，就产生 [[计算机知识/Kali/03-Web与API安全/13-HTTP中间层与消息解释|HTTP 中间层解释差异]] 中的同类问题。合理方法是记录实际缓冲区与后端解释的对应关系；不能笼统宣称“做了规范化所以一定与服务器一致”。加密流量还要先回答传感器是否真正能看到相关明文层，TLS 握手可见不等于 HTTP 正文可见。

## Suricata：配置检查与离线读取

```bash
suricata --build-info
mkdir -p "$HOME/kali-lab/output/suricata"
# 先确认该路径确为当前安装的配置；-T 检查不等于检测效果验证。
suricata -T -c /etc/suricata/suricata.yaml
suricata -r "$HOME/kali-lab/fixtures/http-lab.pcap" \
  -c /etc/suricata/suricata.yaml \
  -l "$HOME/kali-lab/output/suricata"
```

配置可能引用外部规则、绝对输出路径或 Lua 等功能，运行前必须审阅，不能只看命令有 `-r` 就认定没有其他副作用。我们不自动安装引擎、下载规则或启用系统服务。自有合成正常流量没有安全告警可能完全合理；先确认输入确实被处理以及输出是否启用，再讨论“没有命中”。

配置启用 EVE JSON 时，可从相应输出中查看事件类型：

```bash
jq -r '.event_type' "$HOME/kali-lab/output/suricata/eve.json" \
  | sort | uniq -c
```

HTTP、flow、stats、alert 是不同记录类别，统计这些行不能直接等于请求数或攻击次数。同一流可能关联多个事件；计数前明确 [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS#^observation-unit|观察单位]]。

## Zeek：在专用输出目录分析

```bash
mkdir -p "$HOME/kali-lab/output/zeek"
cd "$HOME/kali-lab/output/zeek"
zeek --version
zeek -r "$HOME/kali-lab/fixtures/http-lab.pcap"
```

查看实际生成的 `conn.log`、`http.log` 等；具体日志取决于脚本和识别结果。Zeek 默认文本日志带字段说明，可用 `zeek-cut` 提取字段，不能假设是 JSON 就直接给 jq。

```bash
zeek-cut id.orig_h id.resp_h service < conn.log
zeek-cut method host uri status_code < http.log
```

本包 PCAP 的校验和按生成器计算，原始值有单元测试。对真实主机捕获，网卡校验和卸载可能导致本地看到的校验字段与线上不同；不要第一时间无条件关闭校验。确需用忽略校验参数时，记录理由并比较前后解析差异。[^s2]

## 补强：跨引擎关联不能直接比较内部 ID

Suricata 的 `flow_id` 与 Zeek 的 `uid` 属于不同引擎的标识空间。前者用于关联相应 EVE 事件，后者用于关联 Zeek 的连接与事务日志；字符串或数字不同不意味着观察的是不同网络流。[^v2-suricata-eve] [^v2-zeek-conn-current]

跨引擎比较时，以相同输入 PCAP 为前提，先核对协议、双方地址端口、方向与时间范围，再核对请求方法、路径或其他应用特征。五元组也可能在长时间窗口内被重用，因此需要时间范围；时间容差必须有采集精度或时钟证据，不能无限放宽。遇到 NAT 前后两个观察点，还要建立地址转换关系，不能强行按原五元组拼接。

字节数也有层次：应用负载字节、IP 字节、帧字节不是同一个量。重传是否计入、缺失片段、连接关闭是否完整，都会影响结果。本包十个合成以太帧只表达一个 TCP 会话，不应期待十条连接日志。若输出不符，先查输入与聚合单位，再查工具配置，不要先认定引擎失效。

## 先确定连接键，再处理一对多记录

在同一次受控 Suricata 输出中，一条流可对应 HTTP、alert、flow 等多类事件；Zeek 的一个 uid 也可关联不同日志中的记录。跨文件拼接时保留采集点与运行批次，不把内部 ID 当成全局永久标识。时间、五元组和协议身份用于交叉核对，而非自动替代各引擎的关联合同。[^v3-eve][^v3-zeek]

用原创合成例子计算：某流有 2 条 HTTP 事务记录和 3 条告警。只按流键把两组表直接连接，会产生 `2×3=6` 行。这个 6 不是请求数，也不是攻击数，而是连接操作产生的行数。要分析每请求告警，需更细的事务关联字段或明确的时间/方向约束；证据不足时只能保留流级关系。

因此先写分析单位，再决定是聚合、去重、保留一对多还是无法唯一关联。不同字段缺失、同五元组重用、NAT 与合并 PCAP 都应作为显式异常，不通过删除“多余行”让数量迎合预期。相关的字节层次回到 [[计算机知识/Kali/02-信息收集与网络测量/05-WiresharkTcpdump与Tshark|重组与重传计数]]。

### ID 是标识，不是需要算术的测量值

把 flow_id 当不透明标识保存，不做浮点缩放、平均或科学计数法往返。部分 JSON 消费者把数字转换成有限精度浮点，较大整数可能无法逐个精确表示。若跨系统交换时统一转字符串，应从原始精确整数/原文转换，保留类型转换规则，不能先损失精度再 `tostring` 声称恢复。

字段抽取也应先校验类型与事件种类。`.event_type` 缺失可能是不同来源文件、坏记录或结构变化，不应悄悄统计成正常事件。[[计算机知识/Kali/01-系统与网络基础/04-Shell文件权限与文本处理|jq 的整体输入验收]] 专门补足了“最后一条正常就当全文件正常”的陷阱；它的小文件 status 检查不是可直接套用的 EVE schema，迁移时要改成当前事件合同。

此处只给关联推演，不伪造新的 Suricata/Zeek 实测日志。当前官方页面版本与本机引擎版本分开记录；本轮没有安装或运行这两个引擎。

## 补强：先确定规则集和观察方式，再解释为什么没有告警

Suricata 的 `-r` 表示读取离线 PCAP，`-T` 是配置测试；`-s` 加载额外规则，而 `-S` 使用指定规则文件作为独占规则集。后者可帮助缩小实验变量，却不能被误写成“生产规则全量评估”。配置测试通过只证明相应解析与加载阶段成功，不证明某个流量一定触发规则。[^v2-suricatacli]

要解释零告警，依次检查：PCAP 是否确含目标流量；实际载入哪些规则；规则是否被禁用；应用协议是否正确识别；检查的是请求还是响应；重组所需片段是否齐全；日志输出是否启用。加密流量不能被当成同等条件的明文 HTTP 样本。不要通过关掉校验、改变协议识别或放宽规则而不记录，就让期待的告警“出现”。

本轮查阅的 Suricata `latest` 页面显示开发版文档标识；这只是该页面的状态，不代表你安装的 Kali 软件包版本。先记录 `suricata -V` 和本机帮助，再判断具体字段和选项适用性。

## 告警、丢弃与实际阻断是三层证据

Suricata 规则的 action 可以要求告警、通过、丢弃或拒绝；`noalert` 又能抑制告警而不取消其他动作。引擎模式、规则是否加载和执行路径共同决定实际效果。[^v5-suricata-actions]

在旁路观察或离线 PCAP 中看到命中，不证明真实流量被阻断；在在线阻断部署中，动作计数也要与流量路径和端点效果核对。一条规则没有产生日志，可能是没有命中，也可能是日志政策抑制，不能跳过前面的 [[计算机知识/Kali/06-取证逆向与检测/07-YARA日志与检测规则|完成状态与检测覆盖]]。这里讲的是功能与证据关系，本轮没有部署 IDS/IPS 或发送测试流量。

## 检测与修复闭环

从 [[计算机知识/Kali/02-信息收集与网络测量/05-WiresharkTcpdump与Tshark|Wireshark]] 的单包证据出发，解释 TCP 流与 HTTP 消息，再将 Suricata/Zeek 输出连接到同一五元组和时间范围。规则没命中可能是行为正常、规则未加载、端口映射、流重组、加密或漏包等多个原因；不能直接声称环境没有威胁。

> [!question] 自检
> PCAP 有 10 帧，Zeek 只有一条连接记录，是否丢失 9 次连接？不是。包、流与连接是不同观察单位。通过 [[计算机知识/Kali/07-综合实验/03-实验B抓包重组与证据交叉验证|实验 B]] 的握手、数据、关闭过程解释它们的对应关系。

## 来源与核验范围

[^v5-zeek-http-fields]: [Zeek：HTTP::Info](https://docs.zeek.org/en/current/scripts/base/protocols/http/main.zeek.html)；定位：uid、trans_depth、request_body_len、response_body_len。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-suricata-http]: [Suricata：HTTP Keywords](https://docs.suricata.io/en/latest/rules/http-keywords.html)；定位：http.uri、http.uri.raw、http.response_body；读取为开发版文档，仅引用这些机制。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-suricata-actions]: [Suricata 8.0.1：Rules Format](https://docs.suricata.io/en/suricata-8.0.1/rules/intro.html)；定位：Action、Disabling Alerts、Modifier Keywords。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [Suricata 官方 Quickstart](https://docs.suricata.io/en/latest/quickstart.html)；定位：文档页面为开发版；安装版配置另行核对。网页读取：2026-09-05。
[^s2]: [Zeek 官方 Quick Start](https://docs.zeek.org/en/current/quickstart.html)；定位：读取 PCAP 与结构化连接日志。网页读取：2026-09-05。
[^s3]: [Suricata 官方：Command Line Options](https://docs.suricata.io/en/latest/command-line-options.html)；定位：-r / -T / -l；读取时为开发版文档。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-suricatacli]: [Suricata 命令行选项](https://docs.suricata.io/en/latest/command-line-options.html)；定位：-r 离线；-T 检查；-s 追加与 -S 独占；日志目录。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-suricata-eve]: [Suricata EVE JSON 输出](https://docs.suricata.io/en/latest/output/eve/eve-json-output.html)；定位：事件类型、flow_id 与关联字段。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-zeek-conn-current]: [Zeek conn.log 说明](https://docs.zeek.org/en/current/reference/logs/conn.html)；定位：uid、五元组、连接状态、应用字节与 IP 字节。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v3-eve]: [Suricata：EVE JSON Output](https://docs.suricata.io/en/latest/output/eve/eve-json-output.html)；定位：Event types；flow_id；event correlation。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

[^v3-zeek]: [Zeek：conn.log](https://docs.zeek.org/en/current/reference/logs/conn.html)；定位：uid；originator/responder；关联与字节字段。v3 本轮读取：2026-09-05。仅支持对应机制与接口，案例及实测范围另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]