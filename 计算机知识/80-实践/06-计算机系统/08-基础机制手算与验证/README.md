---
domain: computer-science
type: practice
prerequisites:
  - "[[计算机知识/30-计算机系统/10-组成原理系统课程/01-布尔逻辑与时序电路|布尔逻辑与时序电路]]"
  - "[[计算机知识/30-计算机系统/10-组成原理系统课程/05-缓存地址划分与AMAT|缓存地址划分与 AMAT]]"
sources: []
content_status: usable
evidence_status: partial
---

# 基础机制手算与验证

本实践把多页反复使用的五个小模型集中成一个标准库脚本：重叠序列检测器、定宽加减、组相联 LRU、toy DRAM 地址拆分、两阶段地址翻译。先在正文纸算，再让脚本复核；若结果不同，先检查位宽、初始状态、映射与替换策略是否一致。

> [!note] 证据范围
> 脚本只复核候选正文中明示的合成输入与纯函数性质。它不是 HDL 仿真器、cache simulator、DRAM controller、MMU、hypervisor 或性能 benchmark；成功运行不能证明 Obsidian 渲染、真实 ISA、内核或硬件行为。当前候选须先经独立代码审阅，再按本批验证记录决定是否运行。

## 对应关系

| 函数 | 对应正文 | 固定问题 |
| --- | --- | --- |
| `detect_101` | [[计算机知识/30-计算机系统/10-组成原理系统课程/01-布尔逻辑与时序电路\|布尔逻辑与时序电路]] | Moore FSM 怎样保留可重叠后缀 |
| `ripple_add` | [[计算机知识/30-计算机系统/10-组成原理系统课程/02-整数浮点与算术电路\|整数、浮点与算术电路]] | carry、定宽结果与 signed overflow 怎样分开 |
| `trace_lru_cache` | [[计算机知识/30-计算机系统/10-组成原理系统课程/05-缓存地址划分与AMAT\|缓存地址划分与 AMAT]] | tag/index/offset 与 true LRU 淘汰怎样逐地址变化 |
| `decode_toy_dram` | [[计算机知识/30-计算机系统/23-DRAM组织行缓冲刷新与ECC\|DRAM 组织、行缓冲、刷新与 ECC]] | 声明过的 16-bit toy 映射如何拆位 |
| `translate_two_stage` | [[计算机知识/30-计算机系统/24-虚拟化执行地址翻译与虚拟IO推演\|虚拟化执行、地址翻译与虚拟 I/O 推演]] | GVA→GPA→HPA 如何保留 page offset |

脚本拒绝一部分无效输入，例如非二进制状态机字符串、非正二次幂 line size、越界定宽整数和缺页映射。这种拒绝用于防止算例静默换模型，不代表真实硬件采用 Python 异常。

## 审阅后运行

在本目录执行：

```bash
python3 -B -m unittest -v test_verify_foundations.py
python3 -B verify_foundations.py
```

第二条只打印固定示例，便于和正文表格逐项对照；测试包含已知结果和边界拒绝。运行记录应包含 Python 版本、候选文件哈希、退出码与 stdout，不能只写“测试通过”。

## 成功标准

- `10101` 的检测输出发生在第 3、5 个输入 bit 之后；重叠命中不能丢失第二次前缀。
- 4-bit `7+1` 得到 `1000` 且 signed overflow 为真；`15+1` 得到 `0000`、carry-out 为真而 signed overflow 为假。
- 地址序列 `0x00,0x10,0x40,0x00,0x80,0x40` 在 4-set、2-way、16-byte-line cache 上得到正文相同的 miss/hit 与淘汰。
- DRAM toy 映射把 `0x1234/0x123c/0x1274/0x1334` 分到正文声明的 row、bank、column、offset。
- `0xAC` 在两阶段 toy 映射中得到 `GPA=0x5C,HPA=0x9C`，offset 始终为 `0xC`。

若这些检查通过，只说明小模型实现与固定期望一致。状态机门延迟、CPU cycle、真实 cache policy、DRAM hash、TLB cache、VM exit 与 virtqueue 屏障仍需相应层级的证据。

---

**返回课程**：[[计算机知识/30-计算机系统/10-组成原理系统课程/00-计算机组成原理系统课程索引|计算机组成原理课程索引]] · **返回系统域**：[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]
