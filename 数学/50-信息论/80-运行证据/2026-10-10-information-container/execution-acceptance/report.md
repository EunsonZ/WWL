# IC v1 正式复现接口独立执行验收

2026-10-10；执行者 A。**正式路径布局的独立副本真实运行通过。** 未改规范候选、业务源码、主库、Git/GitHub、系统或环境，未派生或安装。

候选部署位置为 `assembled-candidates/information-r1/数学/50-信息论/80-运行证据/2026-10-10-information-container/`。拟发布正式位置为 `数学/50-信息论/80-运行证据/2026-10-10-information-container/`。本次只写实验目录 `experiments-a/2026-10-10-information-portable-acceptance/`；真实运行根为其 `formal-overlay/`，其中仅复制正式业务 .py/.md、run.py、oracle.py 和同版 AGENTS，未放 assembly、incremental.diff、历史16份或任何 `.wwl-recovery` 运行目录。唯一外部运行资源是指向既存 `.venv-issues-111plus` 的解释器环境链接，业务及 oracle 使用标准库。

## 字节绑定与静态增量

| 文件 | 字节 | SHA256 |
| --- | ---: | --- |
| 业务 information_container_practice.py | 6076 | 7a4d8824b776e11810038dca5010ffb31c2dd564178158a54f9e85f60d78b31d |
| portable run.py | 2827 | aea3ce0fe7002e377b4ecddcf3111f5c5173d16d667fb1135e975db86f674fb2 |
| portable oracle.py | 7801 | 3eb934305f52d46677ab7f8c15c4c791baad50055b70efcd8da417d5731c562d |
| 执行时实践 .md | 2534 | 665ae5b74e64fa87b2de95c1868bf7db7700114116b1602ae1ebf36893bb8f62 |

上述输入在执行前后及副本中一致。`oracle.py.adaptation.diff` 显示且程序精确断言：oracle 仅改 SOURCE 为正式业务路径，独立预期/码本、逐位打包、码字树、全部680/25/4断言均未改变，未读取规范源码的 EXPECTED_P/Q 或调用 run()。`run.py.adaptation.diff` 显示采集器仅改 CAND=ROOT、去私有AGENTS/assembly/diff依赖，并以已签业务 SHA 常量替代私有 assembly gate。三个 Python 文件的导入列表均为标准库；唯一运行时业务导入指向 overlay 正式源码。

首次16个原材料作为 provenance 已逐项核对，与 candidate 的 historical-first-run/ 副本字节完全相同，见 `historical-provenance-check.json`；本次没有把它们复制进实际运行根，也没有执行其中脚本。两次实验是不同实际调用，历史输出不替代本次输出。

## 实际命令与结果

在独立 formal-overlay 根执行：

```bash
.venv-issues-111plus/bin/python -B 数学/50-信息论/80-运行证据/2026-10-10-information-container/run.py
```

外层实际命令、cwd、环境、exit、耗时及所有字节绑定见 `portable-acceptance.json`；完整外层 stdout/stderr 为 `portable-command.stdout/.stderr`。采集器输出、固定输入/预期/结果、内部原始 stdout/stderr、业务快照与 portable 两脚本均在 `formal-overlay/数学/50-信息论/80-运行证据/2026-10-10-information-container/`，可由整合写者逐字节接入正式结果目录。

外层采集命令 returncode0、耗时约0.149s、设置60s超时；内部默认与oracle两任务均returncode0。P/Q完整容器、sum8碰撞AAABBBCC、所有符号预算一致；680短消息、25拒绝和4合法边界通过。新 `fixed-inputs-and-results.json` 与首次实验解析后的完整结果完全相同，新默认 stdout 与首次原始 stdout 逐字节相同；检查的是实际新输出，没有调用历史oracle作替代。

五类线程环境均4，任务顺序执行；完成子进程集合累计峰值 RSS 为21,774,336字节，远小于4GiB目标。未观测OS实际线程数，未硬限制RSS；这些资源缺口与标准库范围明确保留。模型预算180symbol/0.180s及96symbol/0.096s不认证物理通信、纠错、误码率或实际吞吐；有限例不证明任意输入一般正确性或编码定理。

## 文档后续字节与复现约束

运行结束后 writer 将实践 .md 更新为2914字节、SHA `9d241c40d11459c84f3fc8b703812da83d2a0f10630ea33412453dc6719dfc56`，仅把待执行文字改成首次实跑回执、680/25/4范围及正式README入口；未改业务.py和portable两脚本。本证据保留真正执行时的旧 .md 快照，后续文档单独保存为 `post-run-documentation/information_container_practice.md`，不把新文档SHA冒充运行输入。collector读取 .md 只为快照/哈希，不用它决定任何算法或预期。

已只读核对 writer 的 README 草稿，它明确给出保持深度的新空目录、复制 run.py/oracle.py 后执行的完整命令，说明 x 模式不覆盖、既存venv前提、历史材料仅provenance及无硬RSS/OS线程证明。固定采集目录一旦含stdout/stderr，原地重复执行会触发独占创建错误；这是已明确的证据保护契约，复现入口应使用README的同深度新空目录步骤。正式README最后的结果链接及后续文档字节由下一独立review核对，本次没有认证尚未发布的远端或真人/客户端结果。
