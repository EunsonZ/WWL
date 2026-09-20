---
type: lesson
domain: computer-science
prerequisites:
  - "[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|TCP 与应用分帧]]"
---

# TCP 字节流：`recv()` 返回的是目前可交付的字节

TCP 给应用的是有序字节流，不给应用“第几次 `send`”或“第几个 HTTP 消息”的标签。`recv(n)` 最多请求 `n` 字节；返回 1 个字节、半个 header，或两条消息粘在一起，都必须由调用者处理。它不能作为 framing 规则。

![recv 分块与应用消息](./_assets/framing.svg)

## 增量解析的最小状态

把所有新字节追加到缓冲区；如果 header 的 `\r\n\r\n` 还未出现，就继续读。出现后先**以字节**解析 header，再依据 body 定界规则计算需要多少字节。够了才移出一条消息；如果缓冲区还留着后续字节，下一轮继续解析。这正是 `code-sync/loopback_http_lab.py` 的 `read_response` 所演示的模式。

一个容易漏掉的点是 UTF-8：`"你好".encode("utf-8")` 是 6 个字节、两个字符。`Content-Length` 的单位是八位组（octet），不是 Python 字符串长度；先在 bytes 上完成 HTTP framing，再按内容的 charset 解码。RFC 9112 要求以 octet 序列解析 HTTP 消息，避免把 Unicode 文本处理带进 framing。[RFC 9112 §2.2](https://www.rfc-editor.org/rfc/rfc9112.html#section-2.2)

## 可检查例子

测试服务器把每个响应故意按 2 字节切片 `sendall`，客户端又用 `recv(3)` 累积。这并没有制造或观察 TCP 报文边界；它只强迫解析器面对任意 API 返回分块。一个 `Content-Length: 5` 响应即使被分成 `H`、`TTP`、……，仍在收满五个 body 字节后才交付 `b"hello"`。

## 边界与反例

- `sendall` 成功也不证明远端应用已处理，更不证明业务提交；它只是本地 socket API 的成功返回。
- TCP 的可靠、有序交付不替应用定义“消息完整”或“请求可安全重试”。TCP 的抽象和 FIN 的语义见 [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html)。
- 这个小解析器有意不支持所有 HTTP（首部重复、trailer、请求 body、代理等），它是教学对照，不是生产 HTTP 栈。

**迁移题：**自定义协议用 4-byte length prefix 时，如何处理一次 `recv` 得到 `2-byte header + 17-byte body + next header`？

**答案：**缓冲所有 19 字节，头部未完整前不解码；读到完整头部后验证长度上限；只消费本帧的 `4+n` 字节，把 next header 留在缓冲区。EOF 前仍不足 `4+n` 则是截断，不是完整帧。
