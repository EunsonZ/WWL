# OU固定运行与独立核查记录

从 [实验读者页](../../../80-OU共同噪声与强弱误差实验.md) 读误差定义和实际解释；数学证明在对应04主课。本目录保存独立执行者原输出的逐字副本，复制过程不构成重跑。

- [原执行报告](REPORT.md.txt)：固定输入、真实时长/RSS、数值结果与未验边界。
- [实际报告JSON](output/report.json)、[公共时刻轨迹CSV](output/traces.csv)、[强误差原图](output/strong-error.svg)。
- [环境](environment.json)、[实际命令/退出/资源](process-observations.json)、[测试原输出](tests.stderr)、[固定运行输出](fixed.stdout)。其它stdout/stderr完整保留，包括空输出；本次未发生数值失败或运行重试。
- [独立核查](independent-oracle.json)与[核查源码](independent_oracle.py)：70位核积分与独立加权终点计算，不导入业务源码或作者test。
- [执行前](hash-before.json)/[执行后](hash-after.json)身份、[原冻结](SOURCE_FREEZE.json)、[原产物清单](artifact-hashes.json)和[逐字复制映射](COPY-MAP.json)。原清单的REPORT.md对应本目录REPORT.md.txt，其字节未改。
- [新一般Itô来源读取范围](sources/SOURCE_READS.md.txt)与[原HTML响应及读取UTC/SHA](sources/baudoin-receipts.json)。这些支持一般定理输入，不由OU实验代证。

`snapshot/` 是原v1实际执行的三文件，对应原六项测试；当前v2的三文件位于 `v2-plot/snapshot/`，对应八项测试。历史execute.py、finalize.py和原命令路径保留原字节，用作记录。它们含恢复区路径，不作为正式复建入口。

需要复建时，从库根依实验读者页命令在一个新空目录运行正式ou_lab.py及固定输入；正式v2的八项test另行执行。也可以另建一个新空目录：将v2-plot/snapshot中的三份v2文件放在新目录/snapshot/子目录，将independent_oracle.py放在新目录根。调用新目录/snapshot/ou_lab.py时指定 `--config 新目录/snapshot/fixed-input.json --output 新目录/output`；测试发现目录指定 `-s 新目录/snapshot -p test_ou_lab.py`。确认CLI退出0、report的diagnostics_pass为true且八项v2测试实际成功后，再调用新目录/independent_oracle.py；它按自身所在目录读取snapshot/fixed-input.json与output/report.json。原目录的independent_oracle.py会写本目录核查文件，因此不要直接在这份归档中运行。新复建是操作接口，作者没有执行它；应保存新的命令、环境、退出与输出身份。

有限执行和核查已完成。原v1 SVG XML保全。v2图像已独立实际渲染与查看；Obsidian显示、同步、真实金融/硬件与真人学习仍未验。

## v2仅图表与测试的增量

[增量原报告](v2-plot/REPORT.md.txt)、[新版源码身份](v2-plot/SOURCE_FREEZE_V2.json)、[独立核心字节/AST对照](v2-plot/independent-diff.txt)、[八项测试](v2-plot/tests.stderr)、[真实进程观察](v2-plot/process-observations.json)完整保留。v2 source为6eaf8e2d…，原v1固定报告中的source仍为1322dd28…；两者差异仅error_svg，采样/统计核心逐字相同，因此数值证据按相同核心复用，没有新版MC重跑。

[当前显示图PNG](v2-plot/plots/actual-v1-report-v2-plot.png)和[可导出的同图SVG](v2-plot/plots/actual-v1-report-v2-plot.svg)来自原真实report，而非新模拟。独立执行者已实际查看PNG；T=1、真实h标签、理论线和实际点正确，误差棒部分被标记覆盖。

[时间改变边界预览](v2-plot/plots/synthetic-T2-boundary-audit-preview.png)与[零误差边界预览](v2-plot/plots/synthetic-zero-boundary-audit-preview.png)可见标注SYNTHETIC / zero MC samples / mock estimates，属于独立解析mock图表检查。原未标注源SVG与标签包装图均保留。预览包装首次布局调整及后续成功渲染在原报告中如实记录。

[历史oracle调用回执](v2-plot/historical-oracle-receipt.json)保留一个明确证据边界：原shell cell退出0，但单独oracle进程退出没有被保存，记为UNKNOWN。原oracle的PASS结果、94项核对与992条轨迹检查真实存在；不伪造单独退出码，也未重跑旧oracle来填补历史记录。
