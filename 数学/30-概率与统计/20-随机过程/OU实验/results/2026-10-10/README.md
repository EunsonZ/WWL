# OU固定运行与独立核查记录

从 [实验读者页](../../../80-OU共同噪声与强弱误差实验.md) 读误差定义和实际解释；数学证明在对应04主课。本目录保存独立执行者原输出的逐字副本，复制过程不构成重跑。

- [原执行报告](REPORT.md.txt)：固定输入、真实时长/RSS、数值结果与未验边界。
- [实际报告JSON](output/report.json)、[公共时刻轨迹CSV](output/traces.csv)、[强误差原图](output/strong-error.svg)。
- [环境](environment.json)、[实际命令/退出/资源](process-observations.json)、[测试原输出](tests.stderr)、[固定运行输出](fixed.stdout)。其它stdout/stderr完整保留，包括空输出；本次未发生数值失败或运行重试。
- [独立核查](independent-oracle.json)与[核查源码](independent_oracle.py)：70位核积分与独立加权终点计算，不导入业务源码或作者test。
- [执行前](hash-before.json)/[执行后](hash-after.json)身份、[原冻结](SOURCE_FREEZE.json)、[原产物清单](artifact-hashes.json)和[逐字复制映射](COPY-MAP.json)。原清单的REPORT.md对应本目录REPORT.md.txt，其字节未改。
- [新一般Itô来源读取范围](sources/SOURCE_READS.md.txt)与[原HTML响应及读取UTC/SHA](sources/baudoin-receipts.json)。这些支持一般定理输入，不由OU实验代证。

`snapshot/` 保留原v1实际执行的三文件，对应原六项测试。v2三份同版输入改从固定 Git 提交 `4bd34d91aa2d34fce10d4dcccf62ce719669296e` 恢复，继续核 [SOURCE_FREEZE_V2.json](v2-plot/SOURCE_FREEZE_V2.json) 与原工件清单身份；v1与v2的源码/测试不同，不能合并。历史 execute.py、finalize.py 和原命令路径仍按记录保留；原增量脚本与图检查的旧字节可从 [清理前固定提交](https://github.com/EunsonZ/WWL/tree/4bd34d91aa2d34fce10d4dcccf62ce719669296e/数学/30-概率与统计/20-随机过程/OU实验/results/2026-10-10/v2-plot) 取回。原工件清单记载当时文件和哈希，不改写成当前目录盘点。

当前正式源码的复建仍可从库根依实验读者页命令运行。需要重新执行冻结v2时，使用含固定提交的本地WWL Git仓库和已具备 NumPy/CairoSVG 的 Python，在本记录目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 /含NumPy和CairoSVG的/python -B v2-plot/execute_increment.py --repo /绝对路径/WWL --output /private/tmp/wwl-ou-v2-NEW
```

输出必须是库外全新、绝对路径目录，最终节点为符号链接（含悬空链接）也拒绝；`--repo` 可为仓库子目录，驱动按实际 Git 顶层判断库内目标。驱动先核固定提交、三个v2输入与冻结/原manifest SHA、保留v1文件的原copy-map SHA/字节数，全部读取与receipt序列化完成后才创建目标；不读取包内已撤除的v2 snapshot。目标内 `v1/` 按原相对名称恢复历史输入/报告以供完整manifest对照，`v2-plot/snapshot/` 保存固定Git取回的v2文件；保留原PLOT差异和预览包装脚本，图检查改用明确的新工作目录和v1对照路径。

新执行依次运行八项v2测试、原三种图表边界检查、两个标注预览、固定规格v2 CLI以及原独立oracle。`v2-plot/plots/` 的实际图仍来自保留的v1真实report，两个边界仍是zero MC samples的合成mock；`numeric/output/` 则是这次新的v2数值输出，两者不混称。独立oracle在 `numeric/` 读取新的snapshot、report与traces，不导入业务源；须实际退出0、94项比较全过和992条轨迹完成，才能给新运行收据。驱动顺序执行、线程环境请求1线程，测试/图/预览各60秒，CLI/oracle各300秒；工作预算不是OS硬隔离，协调者控制总并发至多2个。

准备拒绝在stderr输出结构化失败receipt，不创建或覆盖目标；创建后先写准备receipt，新stdout/stderr、环境、每child执行记录与最终 `fresh-receipt.json` 都写入新目录，失败立即停止。图文件生成与结构检查不等于实看；需要本次显示验收时另看新PNG并记观察。原目录oracle会写归档核查文件，因此复建只使用驱动在新目录复制的oracle，旧报告、原失败/UNKNOWN边界、12份图表产物、freeze与历史回执保留原字节。旧数值/图观察不被称作当前入口重跑，新执行以新目录证据核对。

有限执行和核查已完成。原v1 SVG XML保全。v2图像已独立实际渲染与查看；Obsidian显示、同步、真实金融/硬件与真人学习仍未验。

## v2仅图表与测试的增量

[增量原报告](v2-plot/REPORT.md.txt)、[新版源码身份](v2-plot/SOURCE_FREEZE_V2.json)、[独立核心字节/AST对照](v2-plot/independent-diff.txt)、[八项测试](v2-plot/tests.stderr)、[真实进程观察](v2-plot/process-observations.json)完整保留。v2 source为6eaf8e2d…，原v1固定报告中的source仍为1322dd28…；两者差异仅error_svg，采样/统计核心逐字相同，因此数值证据按相同核心复用，没有新版MC重跑。

[当前显示图PNG](v2-plot/plots/actual-v1-report-v2-plot.png)和[可导出的同图SVG](v2-plot/plots/actual-v1-report-v2-plot.svg)来自原真实report，而非新模拟。独立执行者已实际查看PNG；T=1、真实h标签、理论线和实际点正确，误差棒部分被标记覆盖。

[时间改变边界预览](v2-plot/plots/synthetic-T2-boundary-audit-preview.png)与[零误差边界预览](v2-plot/plots/synthetic-zero-boundary-audit-preview.png)可见标注SYNTHETIC / zero MC samples / mock estimates，属于独立解析mock图表检查。原未标注源SVG与标签包装图均保留。预览包装首次布局调整及后续成功渲染在原报告中如实记录。

[历史oracle调用回执](v2-plot/historical-oracle-receipt.json)保留一个明确证据边界：原shell cell退出0，但单独oracle进程退出没有被保存，记为UNKNOWN。原oracle的PASS结果、94项核对与992条轨迹检查真实存在；不伪造单独退出码，也未重跑旧oracle来填补历史记录。
