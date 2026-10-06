---
domain: "计算机知识"
type: "lab"
stage: 2
prerequisites:
  - "[[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|离线实验准备与夹具说明]]"
  - "[[计算机知识/Kali/02-信息收集与网络测量/03-Nmap主机发现与端口状态|Nmap主机发现与端口状态]]"
  - "[[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]"
sources:
  - "https://docs.python.org/3/library/http.server.html"
  - "https://curl.se/docs/manpage.html"
  - "https://nmap.org/book/man-port-scanning-techniques.html"
content_status: "usable"
evidence_status: "partial"
---

# 实验A从路由到HTTP与Nmap

**先修关系：** [[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|离线实验准备与夹具说明]]；[[计算机知识/Kali/02-信息收集与网络测量/03-Nmap主机发现与端口状态|Nmap主机发现与端口状态]]；[[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP浏览器会话与信任边界]]。

## 问题与前提

目标是解释“进程监听→TCP 连接→HTTP 请求→端口状态”的因果链，而不是搜集很多开放端口。实验只访问**当前这台实验机的回环地址**，不扫描网段，不需要 root 来做 TCP connect 扫描。需要 Python 3、curl 和 Nmap；后两者未在本包构建环境运行。

先完成 [[计算机知识/Kali/07-综合实验/01-离线实验准备与夹具说明|离线准备]]。本实验会由你主动启动短期 HTTP 服务；这一步不是离线测试的一部分。服务目录只能是 `fixtures/web`，不能是 Vault 根目录、家目录或夹具总目录。

## 先记录没有启动服务时的状态

```bash
ss -ltn '( sport = :8000 or sport = :8001 )'
```

若 8000 或 8001 已有未知进程监听，停止并查明身份，不要杀掉别人的程序。清楚两端口都可用于本实验后，在终端 A 启动：

```bash
python3 -m http.server 8000 --bind 127.0.0.1 \
  --directory "$HOME/kali-lab/fixtures/web"
```

只监听 127.0.0.1，终端保持前台，结束时按 Ctrl+C。公开目录中不得加入符号链接：此服务器可能沿链接读取目录外文件。这个静态服务没有登录、参数化 SQL、用户权限或 TLS，不能用来验证这些漏洞；具体 HTTP 头与合成 PCAP 可能不同。绑定回环不会让服务成为生产级服务器，仍只用于短期实验。[^s1]

## 两种观察同一个服务

终端 B：

```bash
curl --connect-timeout 2 --max-time 5 -i http://127.0.0.1:8000/health
nmap -sT -n -Pn -p 8000,8001 --reason --max-rate 10 \
  -oA "$HOME/kali-lab/output/loopback-ports" 127.0.0.1
```

预期 8000 可建立连接并返回公开健康文本；8001 在无其他监听进程时应表现为关闭。**这是有前提的预期，不是保证每台机器出现同一输出。** 防火墙、代理、已有进程和地址族都可能改变观察。

解释顺序：`ss` 观察本机 socket；Nmap 在指定观察点尝试连接；curl 在成功连接上交换 HTTP 消息。HTTP 404 仍说明应用完成了某次 HTTP 响应，不等于 TCP 端口关闭。按 [[计算机知识/Kali/02-信息收集与网络测量/03-Nmap主机发现与端口状态#^port-state|端口状态块]] 区分。

## 改变一项条件，再复测

在终端 A 停止服务，在 B 重跑相同 Nmap 命令但将输出前缀改成 `loopback-stopped`，避免覆盖第一次结果。用 `ndiff` 比较两个 XML。若 8000 仍开放，先查原来是否有其他服务/端口转发或停错终端，不要为了吻合预期而改写记录。

补充观察可选 [[计算机知识/Kali/02-信息收集与网络测量/04-Nmap服务识别NSE与结果管理|轻量服务识别]] 与 [[计算机知识/Kali/03-Web与API安全/02-curlHTTPie与接口重放|请求重放]]；不要自动升级到所有 NSE 脚本或漏洞扫描。变化前后的同一参数和时间记录，比一个“扫描成功”截图更有解释力。

## 验收与清理

能说明 127.0.0.1 从哪台机器解释；能区分进程、连接和请求；保留前后 XML 与 curl 原始输出；确认自己的服务已停止。自检：把 curl 路径改为 `/missing`，为何 Nmap 的 8000 状态通常不变？答案在 [[计算机知识/Kali/01-系统与网络基础/07-HTTP浏览器会话与信任边界|HTTP 与传输层边界]]。

## v2 深化路径

本实验的实机步骤可与 [[计算机知识/Kali/07-综合实验/10-实验G路由与扫描状态推理|实验 G]] 配对：先手算最长前缀和状态推理，再观察真实命令。G 不发包，不能代替 A 的实际网络验证。

## 来源与核验范围

[^s1]: [Python 官方：http.server](https://docs.python.org/3/library/http.server.html)；定位：CLI / --bind / --directory / Security considerations；不使用新增TLS特性。网页读取：2026-09-05。
[^s2]: [curl 官方命令手册](https://curl.se/docs/manpage.html)；定位：--connect-timeout / --max-time / --proxy / --resolve / --cacert。网页读取：2026-09-05。
[^s3]: [Nmap 官方：Port Scanning Techniques](https://nmap.org/book/man-port-scanning-techniques.html)；定位：TCP connect、SYN 与 UDP。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]