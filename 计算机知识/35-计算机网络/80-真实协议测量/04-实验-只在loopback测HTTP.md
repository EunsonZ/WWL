---
type: lab
domain: computer-science
---

# 实验：只在 loopback 上测 HTTP/1.1 定界

## 范围和安全边界

本实验只创建 `AF_INET` listener，绑定 `127.0.0.1` 和 port `0`，让 OS 分配临时端口；客户端也只连接该端口。没有扫描、DNS、外部地址、证书、管理员权限或常驻进程。`ScriptedServer` 是 context manager：退出时关闭 listener，等待它的一个 daemon thread；测试结束后不应有监听 socket。IPv6 `::1` 属于同类 loopback 范围，但本代码为可复现性固定 IPv4。

运行：

```bash
cd '计算机知识/35-计算机网络/80-真实协议测量/code-sync'
TMPDIR="$PWD/.tmp" MPLCONFIGDIR="$PWD/.mpl" python3 -B -m unittest -v test_loopback_http_lab.py
python3 -B generate_diagrams.py
```

`TMPDIR` 和 `MPLCONFIGDIR` 指向本组运行目录；该实验没有第三方依赖，也不读取主库 venv。

## 实际可复核的状态账本

| 测试 | 输入/状态 | 期望结果 | 解释 |
|---|---|---|---|
| Content-Length | `CL=5`，服务端分 2-byte writes，客户端 `recv(3)` | `b"hello"` | 调用分块不改变 5-byte framing |
| UTF-8 chunked | 两个 `3` byte chunks 构成 `你好` | `decode()=="你好"` | 长度的单位是 bytes |
| 持久连接 | `/one` 后 `/two` 同一个 TCP connection | 两个 body 依次读完 | 完整消费前一响应才复用 |
| 截断 EOF | `CL=5`，只送 `he` 后 close | `TruncatedMessage` | EOF 不是完成证明 |
| timeout | 150 ms server delay、`total_timeout=0.02` | `socket.timeout` | 20 ms 总预算内无完整响应，不是 EOF |
| drip deadline | 每 12 ms 送一个 byte，socket timeout 40 ms | 约 40 ms 内 `socket.timeout` | 总预算不会因每次 byte 到达而重置 |
| TE + CL | 两种定界字段同时存在 | `ProtocolError` | 避免歧义解释 |
| 交叉验证 | 标准库 `http.client.HTTPConnection` 对相同 CL 服务器 | 读到 `b"hello"` | 用维护的标准库验证常规路径 |

这些数字是测试配置，不是网络性能测量：时间账本唯一的时间值是服务端主动延迟 150 ms、每 byte 12 ms 与客户端总预算 20/40 ms；没有 RTT、吞吐或 packet trace 结论。

## 源码与镜像一致性

正文所指实现位于 [[./code-sync/loopback_http_lab.py]]；同目录测试 [[./code-sync/test_loopback_http_lab.py]]直接 import 它，图形由 [[./code-sync/generate_diagrams.py]]生成。实验以小而明确的解析子集为目的，生产中应使用标准 HTTP 库（本测试以 `http.client` 交叉验证），并按自己的代理、TLS、限额、取消和日志需求选择实现。

## 观察不等于的东西

- server 的 2-byte `sendall` 切片不是 TCP segment，client 的 `recv(3)` 也不是 packet capture。
- loopback 成功不是公网路径、负载均衡器、代理或 TLS 成功。
- 完整 HTTP response 不是远端业务的持久化或幂等确认。

复查规范：[RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html)、[RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)、[RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html)、[Python socket](https://docs.python.org/3/library/socket.html)、[Python http.client](https://docs.python.org/3/library/http.client.html)。

上下文退出先请求停止，关闭 listener 与已接收连接，打断人为延迟，再等待并检查非 daemon 工作线程。主体异常保留为主异常；同时发生的 worker/收尾错误写入异常 note，无主体异常时显式抛出。半请求头、无客户端、正常响应、延迟和异常情形已有同源回归定义，本轮均 `not_run`；旧运行记录只适用于当时版本。
