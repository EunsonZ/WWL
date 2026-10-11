---
课程: "C++"
类型: "可运行累计实践"
stage: 3
aliases: []
sources:
  - https://timsong-cpp.github.io/cppwp/n4861/views.span
  - https://cmake.org/cmake/help/latest/guide/importing-exporting/index.html
prerequisites:
  - "[[计算机知识/10-编程语言/02-C++/10-系统课程/12-值类型泛型算法与数值应用]]"
---

# 测量分析组件：从第一程序到可安装库

[[计算机知识/10-编程语言/02-C++/10-系统课程/12-值类型泛型算法与数值应用|正文]] 给出每一步的机制、物理意义和练习。C++20；无需模型、GPU、网络服务。源码文件是唯一代码真源，本文只给运行接口和数学合同。

## 文件和累计交付

| 文件 | 本阶段增加的责任 |
| --- | --- |
| [第一程序](stage0/first_measurement.cpp) | 输入词、范围、分支、循环、函数、string/vector 和错误退出；无需借用/模板先修 |
| [公共头文件](include/wwl/measurement.hpp) | RawCode、Calibration、Batch 值类型，借用合同，受约束 sum_codes，单位结果 |
| [实现](src/measurement.cpp) | 解析与提交、统计，直接消费原 TensorBuffer 和原归约真源 |
| [CLI](src/cli.cpp) | 拥有文件流，捕获失败、诊断、退出码 2；空记录显式无统计 |
| [测试](tests/tests.cpp) | 正常/范围/解析/事务失败/shape/类型拒绝/归约模型；显式失败计数 |
| [独立消费工程](consumer/CMakeLists.txt) | 只消费安装后的公开 API 和导出目标，不能靠项目私有 include 偶然通过 |

固定输入 [codes.txt](data/codes.txt) 是 `2 4 6 8`；[boundaries.txt](data/boundaries.txt) 是 `0 4095`；[invalid.txt](data/invalid.txt) 含 `4oops`；[empty.txt](data/empty.txt) 为空。参考首行：

```text
count=4 sum_mV=20 mean_mV=5 population_variance_mV2=5 rms_squared_mV2=30
```

`stage0` 的固定增益为 1 mV/码；库 API 允许整数微伏标定及偏置，CLI 的初始版本使用默认标定。没有把任意命令行参数悄悄当作伏特或秒。

## 干净目录构建与测试

在本实践目录执行。`WWL_CPP_LABS` 默认是本目录的父目录，所以整合回库后直接复用 02 的 `tensor_buffer.hpp` 和 04 的 `layout_math.hpp`。隔离候选没有复制这两个实现，验证时用 `-DWWL_CPP_LABS=/实际库/计算机知识/80-实践/03-C++` 指向原真源。

```bash
cmake -S . -B build-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug -j 4
ctest --test-dir build-debug --output-on-failure
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release -j 4
ctest --test-dir build-release --output-on-failure
./build-release/measurement_cli data/codes.txt
./build-release/first_measurement < data/codes.txt
```

首段四项 CTest 核对 API 合同、CLI 固定值、CLI 空记录和 CLI/初学程序错误退出；累计窗口段另加 window_report_contracts 和 report_cli，合计六项。编译期断言只检验类型约束；运行时测试没有 `assert`，Release 仍执行失败判断。归约测试检查 binary32/binary64 与当前 FE_TONEAREST 是否适用；不适用时明确失败并输出模型限制，不用跳过整个合同测试来冒充通过。`-fno-fast-math -ffp-contract=off`（MSVC 对应 `/fp:strict`）固定本例要求；仍需记录真实编译器的浮点实现。

## 安装并让独立工程使用

每种配置分别安装到新 prefix；不要覆盖系统目录。例中 `PWD` 是本实践目录，实际可选库外临时前缀。

```bash
cmake --install build-release --prefix "$PWD/install-release"
cmake -S consumer -B consumer-build-release -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$PWD/install-release"
cmake --build consumer-build-release -j 4
ctest --test-dir consumer-build-release --output-on-failure
```

consumer 输出 `consumer: sum=20 mV, mean=5 mV`。Debug 同理使用独立 prefix 和构建目录。导出目标的安装 include 路径使用 `${CMAKE_INSTALL_INCLUDEDIR}`，因此自定义 `-DCMAKE_INSTALL_INCLUDEDIR=public-api` 后，头文件安装和 consumer 包含路径会一起指向 `public-api`。公开头文件仅依赖标准库；TensorBuffer/布局头文件是库实现的私有构建依赖，不会被安装成新的同义真源。导出目标和版本文件使用 [CMake 官方导入/导出方式](https://cmake.org/cmake/help/latest/guide/importing-exporting/index.html)。这证明本机同工具链静态库可消费，未认证跨编译器 ABI 或跨平台。

## 输入、空值、形状与资源合同

- RawCode 是 `[0,4095]` 整数；最多 65536 个，词必须是完整十进制 int，不接受部分解析、浮点、NaN、Inf。
- Calibration 增益 `[1,1000] µV/码`，偏置 `[-1000000,1000000] µV`；实际电压在 `[-1000,5095] mV`。Seconds 在 `(0,86400]` 且有限。
- Batch 允许空记录；describe 返回空 optional。n=1 只有样本方差为空。空批次的归约和为 0，仍拒绝 worker_count=0。
- channel_means 要求非空通道、每路非空、相同长度及间隔。复用 TensorBuffer 的非零 rank/extent 合同，先拒绝空值再构造内部输入张量 `[通道,样本]`，row-major stride `[样本数,1]`。返回值是拥有的一维 `vector<Millivolts>`，长度为通道数，`result[channel]` 是该通道的均值；输出没有样本轴。
- Calibration 仅含两个 int，`calibration()` 按值返回，不借用 Batch 成员；从临时 Batch 链式取得标定后仍是独立的值。Batch 拥有码数组；codes 返回只读 span，只允许左值拥有者调用。借用期间禁止拥有者析构、赋值、移动、swap、replace；随后重新取得。channels 参数借用的 Batch 在同步函数整个期间保持。
- compare_reductions 内部 values 拥有标定后的 float；原并行实现持有它的 span，并在返回前 join 全部 jthread。局部 partial 独立写入，join 后读取，不依赖一次发布 flag。线程创建中途失败时已有 jthread 析构等待，数组晚于线程容器析构；调用方收到异常。
- replace_from_stream 先读完整候选再 swap 提交。解析错误和真实流 badbit 测试保留旧 Batch；读位置不回滚。已构造 vector 由 RAII 清理的依据是 [N4861 except.ctor](https://timsong-cpp.github.io/cppwp/n4861/except.ctor)。原有结果PMR实验的计数域不包括普通allocator；本页“普通分配失败”另用独立进程检验指定解析、复制和派发路径，不能把任一组证据称为全部资源路径实测。

## 合法测量归约的绝对误差界

仅在 binary32/binary64、最近偶数舍入、无重结合、无溢出/下溢的模型下使用。令真实标定电压为 `x_i=整数微伏/1000`，`S=Σ|x_i|`，`u32=2^-24`，`u64=2^-53`，`γ_n=n·u64/(1−n·u64)`。整数微伏和/绝对和在 int64 中精确，小于 `2^39`；参考值是这个精确整数和除以 1000 的 binary64 结果。最小非零电压为 0.001 mV，不接近 subnormal。

先以 double 除以 1000，再转 float，绝对转换误差由 `(u32+2u64)|x_i|` 保守覆盖；归约中任何一项到根最多经过 n 次加法，因此串行及原连续分块实现的计算误差均由 `γ_n(1+u32+2u64)S` 覆盖，参考值最后一次舍入也计入前一保守项。库返回：

`B=[u32+2u64+γ_n(1+u32+2u64)]·S`，单位 mV。

实现另加 `1+32u64` 的向上裕量并用 `nextafter` 朝正无穷取下一值，覆盖计算这个界本身的有限次舍入。验证是 `abs(actual-reference)<=B`，不要求 serial==parallel。输入符号消去不会使 S 减小；参考和接近零时仍按绝对界，不改成误导的相对界。n=0 和 S=0 时精确值是 0，实现可给极小非负界。

[[计算机知识/80-实践/03-C++/04-布局缓存与并行归约/README#三条路径比较什么|原布局实验]] 的分块、等待、SIMD 和计时边界继续有效。此项目验证数值；下节对报告任务做本机轻量分布观察；原布局归约仍未新增优化报告。

## 描述统计的误差边界

describe 使用精确整数原码总量及微伏和，不从 float 归约结果反推统计。以下是模型推导的保守绝对界，u=u64，γ_k=k·u/(1−k·u)。设 `m=E[c]`、`q=E[c²]`、`a=增益/1000`、`z=E[x]`；m,q 是精确实数定义，可用独立高精度或有理数算例核对。

- 和：`u·|Σx|` mV；均值：`γ_2·|z|` mV（精确微伏和再两次除法）。
- 描述性方差：`γ_8·a²(q+m²)` mV²，覆盖 q,m 的除法、平方、差及 gain 的两次参与与乘法；截为 0 不扩大相对非负真实方差的绝对误差。该界可大于真实方差，不许改读成相对精度保证。
- RMS²：若方差界为 Bv、均值界为 Bm，则 `Bv + 2|z|Bm + Bm² + γ_2(|variance|+z²+Bv+2|z|Bm+Bm²)` mV² 是保守传播界。
- n>1 的样本方差：`[n/(n−1)]Bv + γ_2·[n/(n−1)](variance+Bv)` mV²。这是数值传播，不认证无偏估计所需统计假设。

固定整数小例的输出恰好精确（20/3 仍是舍入值）；未知标定练习应从自己的参数求各自的界。本轮测试实测了和的界与固定统计量；尚未把以上每个统计界做全输入参考试验。channel_means 是 double 行归约，另有至多 `γ_(n+2)·Σ|x|/n` mV 的保守界，不能套 float 归约 B。

## 归约次序反例和读者验收

tests.cpp 用原归约代码验证 `[2^54,1,−2^54,1]` 的受控结果 `serial=1 parallel=0 exact_real=2`。逐步舍入解释见正文；这组数超出本应用范围，承担反例责任而非合法测量误差测试。FE_TONEAREST 与 digits 会打印到测试输出，可用 `ctest -V` 查看。

读者应完成正文的新标定输入、替换后旧 view、错位采样通道和 Release 测试迁移题。本实践现在通过下一节继续窗口算法、文本/chrono/filesystem组合、应用参数及结果PMR资源计数；普通allocator的指定输入路径现由下方独立故障实验接续，OS及其他未选路径仍缺逐点证据。下节交付有界工作队列/取消/关闭及本机性能观察；高级 modules/协程/ABI 分支未交付。返回 [[计算机知识/10-编程语言/02-C++/10-系统课程/00-C++系统课程索引|唯一系统索引]]。


## 窗口报告：完整应用参数与逐点资源故障

本段正文是 [[计算机知识/10-编程语言/02-C++/10-系统课程/13-可交付组件与并发测量工程|窗口、文件、时间与失败提交]]。窗口阶段组件版本为1.1.0（本页后续有界任务增至1.2.0），旧API和初学程序继续保留；describe委托新增describe_codes(span,Calibration)，每个窗口消费同一统计真源。新[公开接口](include/wwl/report.hpp)、[实现](src/report.cpp)、[完整CLI](src/report_cli.cpp)、[资源/窗口测试](tests/report_tests.cpp)和[独立报告consumer](consumer/report.cpp)均正常参与原CMake。

默认报告命令（在本目录，使用上文构建结果）：

```bash
./build-release/measurement_report --input data/codes.txt --window 2 --hop 1 --gain-uv 1000 --offset-uv 0 --interval-ms 1000 --label adc
```

参考全文见 [report-reference.txt](data/report-reference.txt)；改标定的文件对应 [report-calibrated-reference.txt](data/report-calibrated-reference.txt)，CLI测试逐字核对两份全文。窗口均值3/5/7 mV、描述性方差各1 mV²、RMS²为10/26/50 mV²。改标定与时间，并交付一个实际文件：

```bash
./build-release/measurement_report --input data/codes.txt --window 2 --hop 1 --gain-uv 500 --offset-uv 1000 --interval-ms 250 --label sensor-A --output build-release/sensor-A.txt
```

`--output`会覆盖指定文件；它省略时写stdout。元数据含原码数、毫秒间隔、微伏标定、窗口和hop。成对参数拒绝未知/重复/缺值，整数必须完整解析；window/hop范围[1,65536]，interval-ms范围[1,86400000]，label限1–40个ASCII字母、数字、_、-。gain/offset沿用原Calibration合同。输入流错误、输出open/write/flush/close错误传播至最外层，CLI返回2；成功返回0。本机filesystem路径能运行不认证跨平台文件名编码。

窗口为`[begin,end)`，只输出完整窗口。n<w或空记录产生windows=0。K=`1+(n−w)/hop`（n>=w，整数向下取整），第k个begin=`k·hop`；末时间=`(end−1)·interval_ms`。新WindowStatistics保存索引、整数chrono相对时间和拥有的Statistics值；它不保存Batch的span。窗口结果借用通过ReportSession::windows() const&取得，文本通过text() const&取得，两者都拒绝从右值Session取得；成功replace或析构后重新取得，失败保持旧Snapshot和旧借用。settings()/label()返回拥有值。

内存提交过程是“先解析、完整构造候选Snapshot、全部窗口与文本，再无抛交换拥有指针”。ReportSession单拥有者、禁止复制/移动；调用方memory_resource必须活得更久，不允许nullptr。Snapshot对象、窗口pmr::vector、报告pmr::string走该资源；旧Batch的std::vector、解析/路径/label临时string和测试辅助存储不在计数域。资源故障测试先测一次真实成功路径A次allocate，再对k=1…A依次注入bad_alloc，检查旧参数/结果/窗口地址以及live_blocks/live_bytes恢复旧值。无故障提交成功后，Session析构计数归零。这验证的是**指定资源及输入路径**，不声明所有普通allocator/OS失败都已经逐点测试。

测试并核对重叠窗、短尾舍弃、单样本、空报告、非法宽度/间隔/label、解析和badbit失败、参数诊断、输出错误及实际文件内容。本机Debug/Release打印`PMR allocation failure points=10 live_blocks=0 live_bytes=0 failures=0`，不同标准库可能有不同A。没有assert作为运行时判断。安装后consumer CTest从一项增至两项，第二项验证变标定/时间的窗口报告；命令仍使用上文find_package和导出目标。

参考实现O(Kw)扫描，结果空间O(K)，无需每窗复制原码vector。每窗继承上文统计误差界，必须用该窗的n,m,q；浮点归约次序反例及TensorBuffer多通道消费保留原真源。文本由to_chars输出数字，简单key=value协议没有宣称通用序列化格式。资源内强保证不回滚输入流位置；磁盘输出不是原子/持久事务，写失败可能留下部分文件。下一节继续同一结果对象的生产队列、取消/关闭与本机分布观察。


## 普通分配失败：候选、队列与线程分别保留什么

[allocation_faults.cpp](tests/allocation_faults.cpp)是单独的测试可执行文件，仅在UNIX目标加入CTest；它不会进入库、安装头或消费者。测试替换普通/数组/对齐及nothrow的全局new/delete，开关是线程局部的；固定大小记录和原子活计数不申请堆空间。每个申请块附带本次是否计数的标记，关闭开关或移交线程后释放仍能减去原计数。malloc、系统内部申请与未开启的线程不在注入域内，这不是实际耗尽操作系统内存。

先在同一输入上关闭故障跑完一条成功路径，得到A；对k=1…A每次建立全新的旧状态，仅第k个请求抛bad_alloc，其余请求正常。输入、旧对象、需申请C++堆的比较副本、任务和测试launcher在开启前准备；故障域内仍做不申请C++堆的条件检查，条件失败时可即时fprintf诊断，末尾汇总打印在关闭后进行；待被测对象和结果析构后，注入域live_blocks/live_bytes必须为0。不能在开关打开时把测试记录push到vector，让测试自身扩容占用故障编号。

| 指定路径 | 本机观察请求数A | 失败后实际核对 |
| --- | ---: | --- |
| 256码的replace_from_stream | 9 | 原Batch码值、标定、间隔、span地址保持；候选vector释放 |
| 非空Batch值复制 | 1 | 新副本构造失败，来源及其span保持；成功副本拥有独立数组 |
| 同码ReportSession替换，w4/h2、40字符label | 10 | 旧settings、窗口内容/地址、文本/借用保持；候选普通资源释放，PMR块/字节回旧值 |
| 队列推进512项，始终只保留一个旧任务 | 2 | 失败push不改变旧队首、载荷、open状态或等待计数；随后close排空 |
| 单worker、两个任务的管理线程 | 9 | 派发层bad_alloc经cancel、全部已启动线程退出并join后重抛 |
| 同执行器的工作线程 | 46 | 含输入解析、new_delete_resource及最终拥有文本复制；失败只记录该任务，另一任务完成；返回前线程退出 |

数字是AppleClang21/libc++本机Debug/Release观察，测试不硬编码这些A。管理线程的计数包括内部测试launcher正常构造真实jthread的包装申请；工作线程关闭主线程注入，反向实验关闭工作线程注入，不将跨线程不稳定次序拼成一个全局序号。工作线程的PMR默认new_delete_resource也经new，故这46点**不是纯普通allocator计数**；前面Session实验另用malloc转发PMR资源及独立计数，明确隔离出普通vector/label路径。两个实验相互补充，原PMR十点实验仍独立保留。

队列槽位少不代表push不会申请内存：本机初始块足够容纳8项，只测“填满容量”实际没有新申请。测试持续pop旧项、push下一项，使deque推进到真实块/映射扩展；未发生失败的先前操作不会被回滚，保证对象是失败push前的那个队首。失败push按值接收的入参可能已经移动或销毁，强保证不承诺恢复调用方的被移交任务。

流也有自己的异常层次：长非法token迫使string扩容，第一个请求失败时，默认istream异常掩码将bad_alloc变成badbit，本实现随后抛runtime_error；设置exceptions(badbit)则本机实际传播原bad_alloc。两种情况旧Batch均保持，但读取位置及流状态不回滚。此负例只核首个token扩容失败，不宣称所有流实现内部申请都受控。

```bash
ctest --test-dir build-debug -R ordinary_allocation_faults -V
ctest --test-dir build-release -R ordinary_allocation_faults -V
cmake -S . -B build-asan -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer" \
  -DCMAKE_EXE_LINKER_FLAGS="-fsanitize=address,undefined"
cmake --build build-asan -j 2
ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  ctest --test-dir build-asan --output-on-failure
```

本段Debug/Release及AddressSanitizer+UndefinedBehaviorSanitizer完整CTest各9/9；显式失败计数在NDEBUG下仍执行。ThreadSanitizer另跑普通分配和已有队列合同2/2，未报告数据竞争；这只覆盖本次调度，不是所有调度的证明。macOS本次关闭LeakSanitizer，只用注入域及独立PMR计数核释放；这不等于整个进程的泄漏认证。测试不注入filesystem路径、真实OS线程/同步原语耗尽、文件内部malloc、所有输入和所有调度；不验证自定义allocator、故障中再次故障或实时停止上界。计数说明这些被观察并重放的请求有正确收尾，不能推成任意类型/allocator的强保证。

## 有界任务与性能观察

本段对应[[计算机知识/10-编程语言/02-C++/10-系统课程/14-有界任务关闭取消与性能证据|第14讲]]，版本1.2.0。[report_queue.hpp](include/wwl/report_queue.hpp)是公开合同，[report_queue.cpp](src/report_queue.cpp)是队列与执行器真源，[queue_tests.cpp](tests/queue_tests.cpp)和[batch_cli.cmake](tests/batch_cli.cmake)做真实线程/命令路径验证；内部启动器故障缝隙不安装。[queue.cpp](consumer/queue.cpp)从安装包独立消费公共API。

```bash
./build-release/measurement_batch --workers 2 --capacity 1 data/codes.txt data/invalid.txt data/codes.txt
./build-release/report_benchmark > build-release/benchmark.csv
```

第一条结果依序成功/失败/成功，整体退出2；不因第二份解析失败取消其他任务。任务拥有string和ReportSettings，worker单独拥有ReportSession，结果复制文本后返回。1–3个worker加调用线程最多4个，容量1–8，批次<=64，输入各<=512 KiB，保留结果各<=32 MiB。close拒绝新任务并排空，cancel清待取任务并唤醒两侧；外部stop_token通过stop_callback发出cancel。成功pop后看到stop=false定义已开始，此后取消允许该任务完成。返回/重抛之前全部join；无停止时长上界。CLI读取有字节限额、选项完整解析、按输入序号输出；取消目前由公开API支持，没有OS信号转换入口。

测试验证实际满队列生产者等待、pop释放容量后FIFO接续、close与cancel唤醒满/空两侧、已取WorkItem在cancel后仍拥有输入、1/2/3worker下报告一致、单任务错误隔离、预取消、真实stop_source取消尚未开始任务（gate保持worker未执行；满队列实际等待另由队列测试验证）、部分启动失败后已启动线程均join、坏launcher收尾。普通分配的指定路径另见上节；OS资源耗尽和穷举全部调度交错未认证。运行时检查使用明确失败计数，Release不依赖assert。

基准固定24任务×2048原码，w32/h16=>各127窗口，队列2。1/2/3worker各1次暖机+7次样本。计时包括任务复制、线程启动、解析、扫描、格式化、拥有结果复制、完整文本一致性校验与join；不包括固定输入生成和输出。原始样本、环境和观察摘要见同目录[evidence/README.md](evidence/README.md)、[benchmark.csv](evidence/benchmark.csv)、[benchmark-runtime.json](evidence/benchmark-runtime.json)。这些是本机观察，不能承诺其他机器/负载、尾延迟或内存硬上限；不包含汇编/向量化/NUMA实验。完整应用峰值还取决于保留结果、窗口存储、线程栈与分配器元数据，队列槽位不能替代总内存证明。

原有界任务段Debug/Release完整CTest各8/8；本段增加普通分配故障后各9/9。默认安装独立consumer仍为3项。自定义public-api目录另行验证结果见证据页。结果PMR故障的10个分配点沿用第13讲真实测试，其计数域没有扩展到本段所有普通分配。高级模块/ABI/协程的接续接口和预期证据列于第14讲；尚未跑这些实验，#244保持未全完成。

## 单线程协程帧的高级消费者

[[计算机知识/10-编程语言/02-C++/10-系统课程/16-协程帧拥有暂停与取消|第16讲]]和[advanced/coroutine/README.md](advanced/coroutine/README.md)继续兑现前述协程分支的单线程范围。该独立CMake工程只find_package已安装组件：输入/设置进入拥有帧，ReportSession跨实际co_await挂起，最终只交付拥有string；正常、取消、失败、移动和帧释放在Debug/Release各两项CTest验证。它有独立构建入口，不增加上文旧工程的8项测试，也不把旧consumer的3项改称本批重跑。没有外部事件调度、并发恢复、异步I/O、模块或跨编译器ABI认证；帧计数不扩展PMR或普通allocator故障覆盖。
