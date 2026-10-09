# IIR固定系数闭带与有限轨迹实际结果

最终V2R1的12项测试在2026-10-10新执行通过。生产源码SHA256为`87344dd861372a9021c7c36ea45ddbf3983b9f1c0654db8b3a6e835c45355e74`，与V2逐字相同；完整CLI与独立Fraction核算明确复用为REUSED_EXACT_SOURCE，没有R1 CLI重跑。原V2 11测试的10 OK、1 ERROR保留，宽区间Horner未证导致None的旧夹具由R1修正，不改生产分母门槛。

- [完整原JSON](v2r1/raw/iir-cli/results.json)：6888992 bytes，SHA256 `62cf461be69d68ae685b1d85b54b8310381b968d6da18a5b360debdafc1f7626`；两个模型各3734 pass+11 stop，合计7490 accepted cells，无未决区间。
- [CLI实际回执](v2r1/cli-run.json)、[独立oracle回执](v2r1/executor-run.json)、[独立完整stdout](v2r1/logs/executor-oracle.stdout)、[R1真实12测试回执](v2r1/r1-test-run.json)、[R1日志](v2r1/logs-r1/iir-tests.stderr)、[原11测试失败](v2r1/logs/iir-tests.stderr)。
- [执行者报告逐字快照](v2r1/README.md.txt)、[最终独审逐字快照](review/execution-review-v2r1.md.txt)、[一般包含性源审逐字快照](review/source-review-v2.md.txt)。快照中的相对链接是原证据位置的记录，不是本入口的导航；输入身份在同目录json。

全部cell分别满足通带平方增益[.9801,1.0201]、同SOS延迟[0,96]sample、阻带平方增益≤.000001、逐节Q.lower>0；独立Fraction核全部分区首尾与邻接、门槛、二次分母真实最小值和记录下界。有限456有理点核算只是发现错误的补充，全频率结论依赖已独立接受的向外算术包含性与完整闭cell覆盖证明。证书对象是固定binary64／binary32系数的线性传递函数；不延伸为逐步舍入非线性递归的全局证明。

两个SOS对指定0.9V峰界、12000拍输入均complete；binary32高阶直接型n=425发生finite_range_exceeded，仅425拍前缀，完整JSON保留。W8/F4的2V故障与饱和另列。96k/5k迁移仅设计/拒绝主证书，资源耗尽真实not_certified，不能外推主规格的证书。

运行环境Python3.14.7/macOS27.0.1 arm64，CLI线程环境OMP/OPENBLAS/MKL各请求4；oracle环境字段null按原回执保留。CLI child RSS观察56688640bytes，oracle自身53166080bytes，各自观测而非合计峰值、OS硬内存限制或线程计数。五SVG实际系统WebKit全幅显示证据见[旧实验与图](../../../05-Fourier表示与FFT卷积/results/2026-10-10/README.md)。Obsidian、硬件、真实部署及真人迁移未验。

原输入snapshot与snapshot-r1保留两份27目标，历史Markdown以`.md.txt`逐字保存；原驱动不改。复建使用[统一新目录驱动](../../../05-Fourier表示与FFT卷积/results/2026-10-10/rebuild.py)，只复制输入与所需原执行脚本，先CLI再R1再oracle，并解析三份实际回执。原`run_jobs.py`会在V2旧失败break且外层可能exit0，不能用它作为最终成功接口。

```sh
wwl_work="$(mktemp -d /private/tmp/wwl177178-rebuild.XXXXXX)" && python3 -B ../../../05-Fourier表示与FFT卷积/results/2026-10-10/rebuild.py --work "$wwl_work" --kind v2r1
```

驱动要求`fixed-runs.json`预期3任务齐全、全部exit0、无error／timeout，并核CLI、R1及oracle实际receipt退出结果；原失败复建接口仍留档但不加入成功集合。本次交付只核接口源码，不重跑实验。
