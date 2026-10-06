---
type: lesson
domain: computer-science
sources:
  - https://www.rfc-editor.org/rfc/rfc9112.html
---

# HTTP/1.1 消息定界：长度、chunked，或明确拒绝

HTTP/1.1 消息由 start-line、header section、空行和可选 body 组成。收到 header 后才可按 RFC 9112 §6.3 的优先规则判断 body length；不能仅因为暂时没有字节就把消息当作结束。[RFC 9112 §2、§6](https://www.rfc-editor.org/rfc/rfc9112.html#section-6)

## 两条本实验实现的规则

| 字段 | 完成条件 | 例子 |
|---|---|---|
| `Content-Length: 5` | body buffer 至少有 5 octets | `hello` 才完整 |
| `Transfer-Encoding: chunked` | 逐块读 size、data、CRLF，读到 `0\r\n\r\n` | `3\r\n你(3 bytes)\r\n...` |

`chunked` 的 size 是十六进制字节数。实验中的 `你好` 分两块、每块 3 bytes，最后零块结束；它演示 transfer coding 的边界，而不是把汉字按字符数计长。定义见 [RFC 9112 §7.1](https://www.rfc-editor.org/rfc/rfc9112.html#section-7.1)。

## 一条连接上连续请求

测试在一个连接先请求 `/one`，读完 `Content-Length` 响应，再请求 `/two`，读完 chunked 响应。关键在“**先读完响应 body 再复用连接**”：若第一个 body 留在接收缓冲区，第二个 status line 会被误读。这个次序也解释了为什么生产客户端应直接采用维护完善的 HTTP 实现，而不要从本页代码扩展。

## 歧义是拒绝条件

本实验按**字段存在**而不是值的真值判断：同时出现 `Transfer-Encoding` 和 `Content-Length`（即使某个值为空）就抛出 `ProtocolError`。单独空 `Transfer-Encoding` 或空 `Content-Length` 也无效；`+2` 这类不符合 `DIGIT` / `HEXDIG` 语法的长度同样拒绝。为保持例子小，chunk extension 与 trailer 也直接拒绝，并不把它们静默当作普通 chunk size。它是保守的教学策略，避免两个解释器在同一字节流上选择不同边界；RFC 9112 对两者并存有专门的 message-length 和安全处理要求。[RFC 9112 §6.3、§7.1、§11.2](https://www.rfc-editor.org/rfc/rfc9112.html#section-6.3)

**失败例：**用 `recv()` 返回 `b""` 当作 chunked body 的结束。错误：chunked 的结束是 zero-size chunk；EOF 出现在尚未读到 zero chunk 时，是不完整消息而非正常结束。

**迁移题：**为何把 `Content-Length` 当 Unicode 字符数会错？

**答案：**HTTP framing 处理 octets。`你好` 的字符数为 2、UTF-8 byte length 为 6；按字符数读会留下 4 字节，随后破坏下一条消息的起点。
