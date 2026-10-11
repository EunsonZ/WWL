# IIR固定系数闭带与有限轨迹实际结果

最终V2R1的12项测试在2026-10-10新执行通过。生产源码SHA256为`87344dd861372a9021c7c36ea45ddbf3983b9f1c0654db8b3a6e835c45355e74`，与V2逐字相同；完整CLI与独立Fraction核算明确复用为REUSED_EXACT_SOURCE，没有R1 CLI重跑。原V2 11测试的10 OK、1 ERROR保留，宽区间Horner未证导致None的旧夹具由R1修正，不改生产分母门槛。

- [完整原JSON](v2r1/raw/iir-cli/results.json)：6888992 bytes，SHA256 `62cf461be69d68ae685b1d85b54b8310381b968d6da18a5b360debdafc1f7626`；两个模型各3734 pass+11 stop，合计7490 accepted cells，无未决区间。
- [CLI实际回执](v2r1/cli-run.json)、[独立oracle回执](v2r1/executor-run.json)、[独立完整stdout](v2r1/logs/executor-oracle.stdout)、[R1真实12测试回执](v2r1/r1-test-run.json)、[R1日志](v2r1/logs-r1/iir-tests.stderr)、[原11测试失败](v2r1/logs/iir-tests.stderr)。
- [执行者报告逐字快照](v2r1/README.md.txt)、[最终独审逐字快照](review/execution-review-v2r1.md.txt)、[一般包含性源审逐字快照](review/source-review-v2.md.txt)。快照中的相对链接是原证据位置的记录，不是本入口的导航；输入身份在同目录json。

全部cell分别满足通带平方增益[.9801,1.0201]、同SOS延迟[0,96]sample、阻带平方增益≤.000001、逐节Q.lower>0；独立Fraction核全部分区首尾与邻接、门槛、二次分母真实最小值和记录下界。有限456有理点核算只是发现错误的补充，全频率结论依赖已独立接受的向外算术包含性与完整闭cell覆盖证明。证书对象是固定binary64／binary32系数的线性传递函数；不延伸为逐步舍入非线性递归的全局证明。

两个SOS对指定0.9V峰界、12000拍输入均complete；binary32高阶直接型n=425发生finite_range_exceeded，仅425拍前缀，完整JSON保留。W8/F4的2V故障与饱和另列。96k/5k迁移仅设计/拒绝主证书，资源耗尽真实not_certified，不能外推主规格的证书。

运行环境Python3.14.7/macOS27.0.1 arm64，CLI线程环境OMP/OPENBLAS/MKL各请求4；oracle环境字段null按原回执保留。CLI child RSS观察56688640bytes，oracle自身53166080bytes，各自观测而非合计峰值、OS硬内存限制或线程计数。五SVG实际系统WebKit全幅显示证据见[旧实验与图](../../../05-Fourier表示与FFT卷积/results/2026-10-10/README.md)。Obsidian、硬件、真实部署及真人迁移未验。

两代原冻结清单各27目标仍作为历史身份记录，保留真正不同的旧V2失败测试、两代镜像、历史Markdown、图源和回执。两份相同业务源与等于正式R1的测试输入改由固定Git取回，原驱动与失败日志保持原字节；原manifest不重写成当前目录计数。旧 [执行者报告](v2r1/README.md.txt) 中的直接copy步骤属于当时复建接口，当前使用 [统一驱动](../../../05-Fourier表示与FFT卷积/results/2026-10-10/rebuild.py) 的v2r1分支，委托本组 [固定输入入口](v2r1/replay.py)。v1分支仍维持既有接口。

在本目录运行，`--work` 改为库外、全新且尚不存在的绝对路径，`--repo` 指向含固定提交 `ce0a1b02bc73499ea7eaf04dfab5e0cf6ca94eb3` 的本地WWL Git仓库（可以是仓库子目录，按实际顶层判断库内目标）：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B ../../../05-Fourier表示与FFT卷积/results/2026-10-10/rebuild.py --kind v2r1 --repo /绝对路径/WWL --work /private/tmp/wwl-iir-v2r1-NEW
```

驱动先按原source-manifest SHA/字节数恢复两代完整27目标：三份可恢复重复Python输入从固定Git的原snapshot路径导出，旧V2失败测试与其余保留输入从包内复制，历史 `.md.txt` 在新目录恢复原 `.md` 相对名称。恢复布局仍为 `snapshot/candidate-v2/` 和 `snapshot-r1/candidate-v2r1/`；它实际逐字核业务源相同、25目标相同且差异恰为测试与镜像，不把旧11项测试的失败版本合并成最终12项。独立preflight/oracle按原工件记录核身份后复制，全部读取/校验与准备receipt序列化完成才创建目标。

新执行顺序为有限preflight、完整CLI、最终R1十二项测试、原Fraction oracle。preflight仍须给两模型未认证且覆盖完整；新CLI生成 `raw/iir-cli/results.json`，oracle只核这份新JSON，其补充操作测试仍导入冻结公开API，不能说它完全不导入业务源。两模型7490cell与456有理点、保守wideNone、资源耗尽及拒绝分支必须保留，失败即停止并写新receipt。新执行直接调用冻结源码/测试，不借原wrapper的4线程请求；线程环境请求1，预跑/测试60秒，CLI/oracle300秒，协调者总并发至多2个。这些是工作预算，不是OS硬隔离或聚合内存测量。

既存输出、最终节点为符号链接（含悬空链接）、库内目标、缺固定对象或输入身份不符都拒绝；准备拒绝的结构化失败receipt在stderr且目标不创建。创建后先写准备 `fresh-receipt.json`，新环境、真实child argv/退出/超时/RSS、stdout/stderr与最终receipt留在新目录。新CLI与oracle的实际退出必须全部为0且结果完整，旧r1-test-run的REUSED_EXACT_SOURCE仍是历史事实，不改写为当时重跑。原`run_jobs.py`的V2 ERROR与外层退出不充当最终成功接口，也不要在冻结归档直接运行写日志命令。

教学SVG是解析设计链/内部尺度图源，CLI仅生成JSON；它们随保留输入复制到新布局，未冒充新的数值曲线。需要新显示验证时对照新JSON里的设计与固定位code，另用已有渲染器保存/实看新的PNG并记录观察；原五SVG的WebKit观察继续保留。新运行不自动认证Obsidian、硬件、部署或真人理解。
