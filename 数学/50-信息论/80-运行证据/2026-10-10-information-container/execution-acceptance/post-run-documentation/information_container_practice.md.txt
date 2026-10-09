---
type: practice
domain: mathematics
stage: 1
aliases:
  - 有限容器实践接口
sources:
  - https://docs.python.org/3/library/stdtypes.html#int.to_bytes
prerequisites:
  - "[[计算机知识/60-数据编码与媒体系统/04-压缩原理熵编码字典编码与有损压缩#一个可逐字节复算的教学格式]]"
---

# IC v1：同一消息的有限容器实践

问题和完整手算答案在 [[计算机知识/60-数据编码与媒体系统/04-压缩原理熵编码字典编码与有损压缩#一个可逐字节复算的教学格式|格式与成本账本]]。本入口把同一 `AAAABBCD`、P/Q 码本、格式字节与拒绝条件交给一个受限读写器；不测试网络、调制硬件或 Obsidian。

源码是真源：[information_container_practice.py](information_container_practice.py)。固定输入直接写在源码 `MESSAGE`、`PREFIX`、`FIXED`、`EXPECTED_P`、`EXPECTED_Q` 中；旧独立复算脚本 `information_finite_oracle.py` 保持原字节。载荷打包显式传入 `"big"`，对应高位先到的格式契约；Python 的字节转换规则见 [官方 int.to_bytes 文档](https://docs.python.org/3/library/stdtypes.html#int.to_bytes)。IC v1 自定义字段与 sum8 由本课给定，不借用其他容器格式名称。

从库根运行以下接口；输出只去 stdout：

```bash
python3 -B 数学/50-信息论/80-运行证据/information_container_practice.py
```

独立执行者已实际运行默认示例和独立 oracle，两项均 exit 0，源码 SHA256 为 `7a4d8824b776e11810038dca5010ffb31c2dd564178158a54f9e85f60d78b31d`。首次原始命令/环境、stdout/stderr、固定输入和独立核算见 [首次运行记录](2026-10-10-information-container/historical-first-run/report.md)；正式文件的复现接口与当前执行入口见 [运行材料与复现说明](2026-10-10-information-container/README.md)。旧 `2026-10-09-information-finite-oracle.json` 保留原字节。

已核对的有限观察：

- P/Q 均恢复 `AAAABBCD`，完整 hex 与正文一致，均为 21 byte / 168 bit。
- P 有效 14 bit、pad 2 bit；Q 有效 16 bit、pad 0 bit；二重复后均 336 个信道 bit。
- 每调制符号 2 个信道 bit，数据区 168 symbol，加 8 个同步和 4 个导频得到 180 symbol，在 1000 symbol/s 的题设下为 0.180 s。
- 未重算校验的载荷单 bit 修改拒绝；重算校验后的非零 pad、前缀冲突、错误消息数与未完成码字也拒绝；尾随 byte 拒绝。
- Q 的 `00 5b` 变为 `01 5a` 时 sum8 不变，仍可解析，却恢复 `AAABBBCC`，显示校验碰撞边界。

独立核算另覆盖两码本下 680 个完整短消息例、25 个拒绝夹具和 4 个合法边界；具体输入与结果随运行材料保存。代码中的断言和这些有限检查不证明编码定理、容量、某项误码率、真人理解或实际链路吞吐。#181/#219 的实现连接与运行证据另行验收。
