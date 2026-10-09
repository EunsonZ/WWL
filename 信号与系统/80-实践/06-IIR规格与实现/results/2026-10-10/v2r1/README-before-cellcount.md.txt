# #178 V2 / V2R1 独立执行回执

最终 V2R1 受影响 IIR suite 的12项测试真实通过。相同业务源码的完整CLI真实运行两套machine certificate均为certified，额外独立Fraction oracle完成全部分区与Q下界/阈值核对。原V2测试10项OK、1项ERROR保留，不追改为PASS。新算法包含性的一般论证由未参与设计的recover_review147独核，本执行包不是仅以测试数替代证明。

## 版本与真正执行身份

`source-manifest.json`冻结完整V2 27目标，规范manifest aggregate SHA256 `2ca466cc79f8907fc71fbc8b18c343ab30ffdcc43f5b09a8917935c779662ba8`；原副本在snapshot/candidate-v2。作者收到真实失败后冻结V2R1，执行者复制至snapshot-r1/candidate-v2r1，`source-manifest-r1.json` aggregate为 `9110be7df660ddb81a99474ebb935462141654b966689af5d879e34bc56d4eb8`。二者格式为本执行者逐路径/sha/bytes列表，区别于作者含baseline字段的targets receipt，不混称其哈希。

- 业务源码iir_lab.py，两版完全相同：`87344dd861372a9021c7c36ea45ddbf3983b9f1c0654db8b3a6e835c45355e74`。
- 原V2测试：`4160fe8aafbeaca4e517ba41d05088ac388eb2af15fb91e7090c425a79f91703`。
- 最终V2R1测试：`10c75a22f669b8a7107df171a036a5a837bdc4af8a64ce37a4380587c94bab58`。

`final-source-bindings.json`末核两版各27文件均与相应作者冻结字节相同，V2R1源码/测试code-sync镜像逐字相等。原V1、傅里叶以及147/209证据包未改且不因本次IIR修订重跑。作者/root明确允许相同业务源复用完整CLI；`r1-test-run.json`将它标为 **REUSED_EXACT_SOURCE**，没有宣称R1重跑CLI或用新的测试SHA重签旧失败。

## 真实命令、环境与安全

静态检查：stdlib Decimal/Fraction/math/cmath/struct，源码无import时运行；CLI显式拒绝已存在目录及有AGENTS祖先的目录。完整CLI采用自己唯一新 `/private/tmp/wwl-recovery-178v2-...` 输出，遵守原guard，没有改变输出判断或算法。job结束立即逐字复制完整JSON到own durable `raw/iir-cli/results.json`，SHA256为 `62cf461be69d68ae685b1d85b54b8310381b968d6da18a5b360debdafc1f7626`，6,888,992 bytes；实际transient路径记录在cli-run。

jobs.json / cli-run.json / executor-run.json / r1-test-run.json保留每次真实argv/cwd、输入SHA、stdout/stderr位置、Python3.14.7、平台、开始时间、退出码与时长。预跑/测试timeout60秒，标准CLItimeout300秒；所有数值命令串行执行。固定job隔离HOME/TMPDIR，OMP/OPENBLAS/MKL线程环境各请求4，独立oracle实际继承环境的null字段单独保留，未混写。只有标准库、单Python主进程，没有新增numeric依赖/安装/编译/服务或派生代理。

| 真实执行 | 退出状态 | 时长 | 原始回执 |
| --- | --- | --- | --- |
| 原V2有限资源preflight |0；两模型预期false且覆盖完整|约0.030s|logs/bounded-preflight.*、jobs.json|
| 原V2 IIR 11测试 |1；10 OK、1 ERROR|约0.212s|logs/iir-tests.*、jobs.json|
| 原V2同业务源完整CLI |0|5.922s|logs/iir-cli.*、cli-run.json、raw/iir-cli/results.json|
| 独立Fraction oracle |0；PASS|1.904s|logs/executor-oracle.*、executor-run.json|
| 最终V2R1 IIR 12测试 |0；OK|约0.212s|logs-r1/iir-tests.*、r1-test-run.json|

CLI与oracle stderr为空；unittest stderr含正常测试状态及原失败trace，不把它称空。完整CLI子进程ru_maxrss观察56,688,640 bytes，oracle自进程53,166,080 bytes（macOS单位）；这是不同命令RSS观察，不是合计进程树峰值、硬内存cap或实际OS线程数认证。

## 原失败、修订与边界

原V2 `test_strict_cell_exact_rational_transfer_and_delay`在宽c=[.9,1]夹具直接索引返回None，TypeError发生L173。固定第二节的真实Q=(5/4−c)²，全区间Q≥1/16；区间Horner下界却为−3/80，保守地返回None符合拒绝合同，不能绕过该分母下界直接认证。独立oracle另核同夹具真实两节Q最小值1/4、1/16和实际None，不解引用它。

作者V2R1只改测试及镜像：窄正例[.71,.72]/[.90,.901]先assert非None再核幅度/延迟；新宽cell回归保留None。最终12项实际通过。本执行者没有更改业务源或作者测试；旧失败日志、原源码、修订后测试各自字节独立保留。

## 同固定系数的闭带结果

两套证书均为status=certified/certified=true；每套pass3734个accepted cell、7467次求值、最大深度16；stop11个accepted、21次求值、最大深度10；所有unresolved=[]，limits深度24、每带131072求值、Decimal精度80。pass覆盖声明rational c_lo到1，stop覆盖−1到1/2，精确邻接首尾全检查。表中显示缩略数值，严格比较使用原Decimal字符串转换为Fraction，完整端点在raw JSON。

| 模型 | pass幅度平方lower / upper | pass延迟lower / upper（sample） | stop幅度平方upper |
| --- | --- | --- | --- |
| binary64 SOS |0.9801074557088296 / 1.0200893215314166|19.2591371053802 / 41.60323405267965|9.695853422592237e−7|
| binary32系数 SOS |0.9801072963430193 / 1.0200896363977873|19.2591370995191 / 41.60323334928901|9.695853091117956e−7|

全部cell分别满足pass平方幅度[.9801,1.0201]、延迟[0,96]和stop平方幅度≤.000001。Nyquist平方增益精确为0；Q.lower严格正。rational通带端点确为正、精确平方≤1/2。证书对象是固定精确dyadic系数的线性有理传函，不是每次binary32运算舍入后的递归轨迹，也不是设计器理想pole模型。

## 执行者独立 Fraction 验收

executor_oracle.py不调用被测expected/report/run/design作为预期；仅导入冻结公开API作补充操作测试。读取实际机器系数，binary32期待由独立struct round生成，与所有dyadic整数分数/Decimal exact records逐节一致；Schur/Jury与binomial恒等式独立按Fraction核。

- 全部两模型7500 accepted cells，逐一检查首尾/邻接覆盖、阈值、全局min/max聚合。每cell对14节用精确二次多项式端点/内部顶点求真实Q最小值，核记录的0<Q.lower≤该精确最小值，没有仅复用source interval Horner。
- 独立由系数自相关展开P/Q。延迟用相位商导数 `degree/2−E/Q`，与source J/Q表达不同但同一固定Q，不能从ideal poles代填。每模型分布选65个pass cell及全部11个stop cell，核左右端和1/3有理内部点，共456点；全带cover/阈值则检查每个cell。报告保留边界点的完整精确Fraction、记录区间和模型身份。
- Outward精度24独立四则/跨零平方的exact corner范围；外部Decimal context精度3时输入.1仍精确dyadic、1/7仍包围；布尔/非有限输入在固定suite检查。保守wideNone、失稳/非对称/空级联/含零除法拒绝另有具体异常回执。
- max_depth1/max_cells1实际返回not_certified/false，accepted+unresolved仍覆盖闭域；两个迁移规格96k/5k实际unsupported/false，不挪用主带边。失败/未证分支不会被期待文件代写true。

有限有理抽点可以发现错误，不能替代整个闭cell包含性的源码独核。全频率断言还依赖私有有向算术、Horner包含性、同Q/J与有限覆盖的独立数学审阅；recover_review147/source-review-v2负责该层。

## 实际有限精度观察

完整同源CLI仍保留12000拍主输入、初态零、0.9V峰界的观察：binary32直接展开结构在样点425报finite_range_exceeded，前缀425拍，未称完成12000拍；其巨大前缀误差保留。升次序SOS/降次序SOS均complete12000，最大绝对误差分别约1.84887e−6V / 2.47010e−7V，内部峰值原JSON完整。

W8/F4的2V故障输入、饱和事件与各拍code输出保留，独立固定suite通过；不是0.9V主输入。N27、迁移N30/N17、固定section稳定性、Decimal模型等价、全通199sample的延迟反例仍按实际测试/JSON身份记录，普通float ideal_pole_delay_estimate只作观察，不代替机器证书。

## 新目录复建

原证据包只读。重跑先在自己拥有的新空目录复制snapshot/、snapshot-r1/及preflight.py、run_jobs.py、run_cli.py、run_tests_r1.py、executor_oracle.py，创建home/、tmp/、logs/、raw/。只在该新目录运行：

```sh
python3 -B run_tests_r1.py
python3 -B run_cli.py
python3 -B executor_oracle.py > logs/executor-oracle.stdout 2> logs/executor-oracle.stderr
```

run_cli遵守原guard，为每次复建生成新的外部/private/tmp子目录并立即durablecopy。它调用snapshot/candidate-v2的iir源；run_tests_r1显式核该源与最终snapshot-r1的源逐字相同，再声明REUSED_EXACT_SOURCE。复制的驱动依自身目录找冻结源，不依赖原隐藏candidate绝对路径。若复建原失败可另运行run_jobs.py，但会停在原V2测试ERROR；不要把它当最终R1通过接口，也不要直接从本冻结包跑写日志命令。

字节清单见artifact-manifest。未运行图渲染、Obsidian显示/同步、真实DSP/声音/硬件、真实部署或真人学习；#177不因本次IIR算法执行重复认证，#178关闭还需最终源码/测试/执行独核与正式远端交付。
