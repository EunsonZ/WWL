---
domain: "计算机知识"
type: "lab"
stage: 3
prerequisites:
  - "[[计算机知识/Kali/02-信息收集与网络测量/04-Nmap服务识别NSE与结果管理|Nmap服务识别NSE与结果管理]]"
sources:
  - "https://nmap.org/book/output-formats-xml-output.html"
  - "https://docs.python.org/3/library/xml.html#xml-security"
content_status: "usable"
evidence_status: "partial"
---

# 实验 H：扫描 XML 差异与不确定性

> [!abstract] 本实验要防止的错误
> “上次开放，这次没有这一行，所以已关闭”是错误推断。本实验把显式状态、扫描范围、汇总信息和扫描是否完成分开保存。

## 1. 输入与模型范围

使用 [[计算机知识/Kali/07-综合实验/夹具/v2/scan-before.xml|scan-before.xml]]、[[计算机知识/Kali/07-综合实验/夹具/v2/scan-after.xml|scan-after.xml]] 与 [[计算机知识/Kali/07-综合实验/夹具/v2/scan-aggregate.xml|scan-aggregate.xml]]。它们由本包生成并明确标注 SYNTHETIC，不是 Nmap 执行记录。字段结构参照 Nmap XML 输出；官方格式还包含本解析器未处理的服务和脚本信息。[^v2-nmapxml]

`parse_scan_xml` 只接受 1 字节至 1 MiB 的 UTF-8 XML，根节点须为无命名空间的 `nmaprun`，最多 20000 个元素、深度 64；每个 host 恰有一个 IP 地址，允许另外有 MAC。协议只覆盖 TCP/UDP，端口文本为 1 至 5 位十进制，数值 0..65535。聚合数只允许 0..131072、最多 6 位数字。这些是教学输入合同，不是全部合法 Nmap XML 的定义。

允许 Nmap 常见的裸 `<!DOCTYPE nmaprun>`，拒绝带外部资源或内部实体声明的 DTD、UTF-16、NUL 字节和不支持的状态。通用 XML 安全还涉及实体扩展、底层解析器版本与资源限制；本模型只处理自己的小型合成文件，不能当作敌对 XML 的生产沙盒。[^v2-python-xml-security]

## 2. 先读原始字段，再看差异表

修复前：TCP 22、8000 显式开放，UDP 53 为 `open|filtered`，运行结束状态 `success`。修复后：TCP 8000 显式 `closed`，TCP 443 显式 `open`，UDP 53 未变，但结束状态是 `error`，TCP 22 不在本轮声明的 TCP 扫描范围中。

```bash
cd "$HOME/kali-lab/code"
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PYCODE'
from pathlib import Path
import json
from reasoning_lab import parse_scan_xml, compare_scans
root = Path.home() / 'kali-lab/fixtures/v2'
before = parse_scan_xml((root/'scan-before.xml').read_bytes())
after = parse_scan_xml((root/'scan-after.xml').read_bytes())
print('scope_before=', before.scan_scope)
print('scope_after=', after.scan_scope)
print(json.dumps(compare_scans(before, after), indent=2))
PYCODE
```

应有四个比较对象，键由地址、协议、端口组成，而非只有端口号：TCP 22 为 `open → not_observed`，关系 `coverage_gap`；TCP 443 为 `not_observed → open`，仍是覆盖差异；TCP 8000 为 `open → closed`，属于显式观察变化；UDP 53 的状态相同。每行仍保留后一次的 `after_finished: error`。

这支持“已有一条显式关闭观察”，不支持“全范围复测完成”。即便结束状态为 success，也只说明程序的完成状态，不保证原始授权范围、认证配置或所有业务面均被覆盖。服务产品字段没有解析出来时也不要自动认定“无产品”，本模型根本未解析它。

## 3. 聚合信息不能被悄悄铺成逐端口事实

`scan-aggregate.xml` 只有 8000 的逐端口记录，另有两个端口汇总为 closed。解析结果应保留这条聚合记录，但不能自动生成 22 与 443 的逐条观测。更完整的解析器可以在可靠范围和协议约束下推导补集，但那是需要单独验证的推导规则，不是原始逐条证据。

同一协议端口重复出现且状态不同应拒绝，避免“后写覆盖前写”。主机地址族与 addrtype 冲突应拒绝；缺少 `finished` 则保留 `unknown`。输入为空或 XML 截断是解析失败，不能变成正常的零发现结果。

## 4. 自检与复测写法

运行 `python3 -m unittest -v test_reasoning_lab.ScanTests test_reasoning_lab.FixtureV2Tests.test_scan_fixture_retains_uncertainty`。然后写一段复测结论，必须同时包含 TCP 8000 的显式变化、TCP 22 的覆盖缺口、运行未成功结束，以及补测需要保持的目标、观察点、协议和端口范围。

反例：把 after 的错误状态改成 success，但仍不扫描 22，是否足以宣称 22 已关闭？不是，完成状态不会制造缺少的端口证据。下一步连接 [[计算机知识/Kali/07-综合实验/07-实验F从发现到报告复测|实验 F 的报告与复测]]，把这些缺口写进报告而非藏在日志附件里。

## 来源与核验范围

[^v2-nmapxml]: [Nmap XML Output](https://nmap.org/book/output-formats-xml-output.html)；定位：scaninfo、host、port、extraports、runstats；XML 输出示例。本轮网页读取：2026-09-05。

[^v2-python-xml-security]: [Python XML security](https://docs.python.org/3/library/xml.html#xml-security)；定位：实体扩展、外部资源与解析器版本边界。本轮网页读取：2026-09-05。

来源支持对应机制和接口；案例为原创教学设计。命令除验收记录明确列为实测者外均为参考，不将文档读取等同于 Kali 实机验证。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]