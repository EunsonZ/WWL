# CRC固定输入：2026-10-10实际执行证据

[返回CRC实验](../../CRC.md)。本目录逐字保存独立执行者A的48件原材料；[copy-map.json](copy-map.json)对应原路径、目标路径与SHA256，[原清单](artifact-sha256.json)保持原字节。历史Markdown统一加`.txt`，包括[snapshot/AGENTS.md.txt](snapshot/AGENTS.md.txt)：它只保存当时指令，不是当前规则或根AGENTS发布目标。历史快照CRC.md.txt中“尚未运行”保留原文，当前实际状态以本入口为准。

实际命令、工作目录、超时、子进程退出与环境见逐任务receipt及[environment.json](environment.json)。当时cwd为恢复区`experiments219`，与`snapshot/计算机知识/_labs/cross_crc_causality/`源码目录分开；不是声称脱离实验包运行。[report.json](report.json)汇集回执，[report.md.txt](report.md.txt)保存执行者报告原文。

| 任务 | 真实退出 | 原始输出与错误 |
| --- | --- | --- |
| 业务CRC | 0 | [crc.stdout](crc.stdout)、[crc.stderr](crc.stderr)、[receipt](crc-receipt.json) |
| 作者提供的独立公式oracle | 0 | [stdout](author-verify.stdout)、[stderr](author-verify.stderr)、[receipt](author-verify-receipt.json) |
| A初次独立oracle | 1 | [stdout](independent.stdout)、[stderr](independent.stderr)、[receipt](independent-receipt.json) |
| A修正自己的fixture后独立oracle | 0 | [stdout](independent-retry.stdout)、[stderr](independent-retry.stderr)、[receipt](independent-retry-receipt.json) |
| 固定接口检查 | 0 | [stdout](interface.stdout)、[stderr](interface.stderr)、[receipt](interface-receipt.json) |

初次失败是A自己构造的TINY字面十六进制字符串长度为奇数；[oracle.py](oracle.py)与失败错误原文完整保留。[oracle-retry.py](oracle-retry.py)只修该fixture，课程源码、输入、实际业务输出均未改变。各项退出和输出逐一核过，不能以外层supervisor退出代表所有子任务成功。

[运行前独立预期](expectations-before-run.json)与[最终独立结果](independent-results.json)核出127个非零7位错误、23个跨度≤3的短突发全部检出、15个非零核元素；另核16384对线性关系与三个CRC32载荷。七个单错定位结果来自额外的至多一位错误模型和译码表，不是CRC标志自带任意纠错。[接口结果](interface-results.json)仅含12种拒绝与零消息正常输入。有限执行不能替代正文任意长度证明。

[published-TINY-source.md.txt](published-TINY-source.md.txt)是当时已发布布局原文；[tiny-original.bin](tiny-original.bin)与[tiny-forged-recomputed.bin](tiny-forged-recomputed.bin)为按它构造的本地26字节对象。载荷覆盖[24,26)，`hi`的D8932AAC存为AC2A93D8；改为`ho`并重算31F08F99存为998FF031仍匹配CRC。此观察说明可重算的无密钥CRC不能认证来源；没有运行正式TINY解析器、真实链路或设备。Python与库版本及资源观察见环境/回执；线程环境请求4不证明线程数或硬限额，RSS是测量而非内存上限。没有真人理解证据。

## 从新空目录复建（本作者只静态检查，未执行）

[rebuild.py](rebuild.py)要求明确给一个**不存在的新目录**，先验证来源SHA，仅复制源码与固定输入；不复制旧stdout、预期结果、receipt或完成状态。默认使用修正后的独立oracle，失败原版只供历史查阅。准备预期→业务→作者oracle→A独立oracle→接口共五任务，先逐项检查实际child退出/error、非空stdout/空stderr及预期任务数量和集合，再进入下一层。任何失败立即停，查看新目录中该任务原始两流及receipt；只有最终五任务集合完整才产生新completion。

```sh
python3 -B rebuild.py /明确路径/尚不存在的新空CRC工作目录
```

上述新recipe未经运行；原[execute.py](execute.py)只作历史命令证据，不作新复建入口。新执行不会复用2026-10-10的运行成功声明，也不会替代独立语义核查或课程证明。
