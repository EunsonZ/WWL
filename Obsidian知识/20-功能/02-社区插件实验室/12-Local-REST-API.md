---
type: plugin-lab
stage: 5
status: ready
difficulty: 挑战
estimated_minutes: 22
topics:
  - rest-api
  - mcp
  - integration-security
plugin_kind: integration-exception
plugins:
  - obsidian-local-rest-api
native_alternative:
  - obsidian-cli
  - core/uri
  - manual-editing
risk_level: critical
experiment_status: baseline-managed-read-only
verified: 2026-09-02
tags:
  - playground/plugin-lab
  - playground/integration
  - security/critical
---

# Local REST API with MCP

> [!danger] Baseline integration exception
> WorkWithLLM 历史快照曾因来源库当时协作契约的受控集成需要而默认启用本插件；这不是 WWL 状态，也不是普通新手默认推荐。不要据此在其他 Vault 自动启用 REST/MCP。

## 原生替代

普通编辑使用 Obsidian UI；跨应用打开/创建可用 Obsidian URI；受控本机自动化可优先评估 Obsidian CLI。只有确实需要结构化外部读写时才考虑 REST/MCP。

## 安装与启用状态

WorkWithLLM 快照中插件已安装并作为 integration exception 启用。对 WWL 而言，以下是条件教学要求，不是当前状态声明：

WorkWithLLM 于 2026-09-02 的历史只读复核记录的是 `5.1.0` 与当时的启用列表。WWL 于 2026-09-23 的 manifest 显示 `5.2.0`；manifest 只说明所标安装版本，不能证明 enabled、loaded、HTTPS 配置或服务可达性。

维护者于 2026-06-04 发布的 GHSA-62gx-5q78-wrvx 列明受影响版本为 `<=4.1.2`，修复版本为 `4.1.3`。`5.2.0` 不在该公告的受影响范围内；这不证明没有其他漏洞或当前配置正确。下面仍是条件化的配置要求，不是 WWL 服务运行态的证明。

- 仅 loopback。
- 使用 HTTPS 和 Bearer authentication。
- 明文 HTTP 关闭。
- API key 与证书配置不进入 Git、课程笔记、截图或剪贴板示例。
- 不连接新的 MCP client，不做端口转发、LAN 或公网暴露。

## 本课只做状态核验

不要复制或显示密钥，也不发送写请求：

1. 阅读 Settings 中的 server 状态，不展开或复制 token。
2. 确认地址是 `127.0.0.1` 的 HTTPS endpoint。
3. 确认 insecure HTTP server 关闭。
4. 确认真实配置文件被 Git ignore。
5. 阅读 [AGENTS.md](../../../AGENTS.md)，确认当前 agent 的允许范围。

成功标准：能解释为何“只监听本机”仍不是低风险；能指出身份认证、传输加密、凭据保存和 agent 授权是四个不同边界。

## 为什么风险为 critical

该接口能读取、创建、覆盖、移动、复制和删除 Vault 文件，搜索内容，并可能执行 Obsidian 命令。Bearer token 泄露相当于交出高权限 Vault 控制权；命令执行还能间接触发其他插件的能力。

课程禁止：

- 展示、复制或写入真实 API key。
- 启用 HTTP `27123`。
- 使用 curl/Postman/MCP 发送写入、删除或 command execute。
- 配置反向代理、Tunnel、端口转发或局域网访问。
- 把客户端配置、token、证书私钥提交到仓库。

## 禁用与恢复

非 Baseline 使用场景应关闭插件并断开客户端。若怀疑 token 暴露，先停止服务、轮换 key，再检查访问范围和 Git 历史；不要把旧 key 写进事故记录。禁用插件不会删除笔记。

## 官方来源

- [Local REST API with MCP](https://github.com/coddingtonbear/obsidian-local-rest-api)
- [OpenAPI specification](https://github.com/coddingtonbear/obsidian-local-rest-api/blob/main/docs/openapi.yaml)
- [Security advisory GHSA-62gx-5q78-wrvx](https://github.com/coddingtonbear/obsidian-local-rest-api/security/advisories/GHSA-62gx-5q78-wrvx)
- [Obsidian URI](https://obsidian.md/help/uri)

---

上一站：[[Obsidian知识/20-功能/02-社区插件实验室/11-Obsidian-Git|11-Obsidian-Git]] · 下一站：[[Obsidian知识/20-功能/02-社区插件实验室/13-插件实验报告|13-插件实验报告]]
