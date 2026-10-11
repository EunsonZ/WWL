---
type: lab
stage: 3
aliases: []
sources:
  - "https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf"
  - "https://www.open-std.org/jtc1/sc22/wg14/www/docs/n2396.htm"
prerequisites:
  - "[[计算机知识/10-编程语言/03-C语言/01-程序执行类型与表达式]]"
---
# C 实践：测量流与有界数据结构

本目录用同一批合成码值 [2,4,6,8] 把首次输入、对象所有权、标准库组合和多文件库接起来。主阅读路线见 [[计算机知识/10-编程语言/03-C语言/10-系统课程/00-C语言系统课程索引|C 唯一索引]]；容器与词频见 [[计算机知识/10-编程语言/03-C语言/10-系统课程/11-数据结构与标准库组合实作]]，数学、协议与工程解释见 [[计算机知识/10-编程语言/03-C语言/10-系统课程/12-测量流工具的完整工程]]。完整 `.c`/`.h` 文件是源码真源，本目录没有另存会漂移的代码镜像。

要求已有 C17 hosted 编译器、ar 和 make。核心库/工具只依赖标准 C 库；Python 3 用于独立数学对照和子进程测试，不是库的运行依赖。主线要求 8 位字节、uint16_t/uint32_t/uint64_t 与 ASCII 兼容执行字符集；编译期检查宽度与关键字符值，完整字符集兼容性仍是支持前提。缺这些条件应报不支持，不能强行认为 C17 都能解析同一格式。没有安装步骤，也不需要 Obsidian 插件。

## 第一次保存、构建与输入

先读基础首课的 [[计算机知识/10-编程语言/03-C语言/01-程序执行类型与表达式#先建立运行链，而不是背关键字|首个程序与运行链]]，把其中完整例子用纯文本编辑器保存为 `first.c`，保留 `.c` 后缀。终端切到保存目录，执行 `clang -std=c17 -Wall -Wextra -Wpedantic first.c -o first`，再执行 `./first`，参考输出是 10。编辑器负责保存文本，clang 负责构建，`./first` 才运行程序；构建未成功就不能把旧可执行文件的输出当作新源码结果。

接着打开本目录完整 `src/first_input.c`，读完并保存。这个版本只处理最多四行输入，每行一个 0..4095 的十进制整数、最多四位，不允许符号、空行或周围空白；最后一行可由 EOF 结束。它从标准输入读，和最终 count 格式有意不同：先把每次读一行、范围检查、累计和与循环结束解释清楚，再引入完整记录协议。在本工程目录执行：

```sh
clang -std=c17 -Wall -Wextra -Wpedantic src/first_input.c -o /private/tmp/wwl-first-input
/private/tmp/wwl-first-input < fixtures/first-input.txt
printf '2\nbad\n' | /private/tmp/wwl-first-input
```

正常输出 `n=4`、`mean_mv=5`，失败输入输出诊断 `error=invalid_or_empty` 到 stderr，返回非零且 stdout 为空。重定向 `<` 让样本文件成为标准输入；也可直接运行工具，逐行输入数字后给终端 EOF。这里四项和的上界为 4×4095=16380，`unsigned long` 足够；没有依赖 32 位 int。

按源码顺序解释：`code_line` 的局部 value 保存当前行，fgetc 的 int 同时表示字节或 EOF；每次乘十前已经限制位数、每次更新后检查 4095，四位以内的临时值不超过 9999，unsigned long 足够。函数返回 1 表示读到合法码，0 表示没有下一行，−1 表示坏行或读取故障。main 的 sum、n 是此前合法行的和与数量；第五行拒绝，不把有界数组/记录变成无界输入。最后先排除 n=0，才除以 n；`(double)sum` 使除法成为浮点除法。printf、刷新和关闭也要成功，才返回 0。

自己把第三行改成 4096，预测哪一步拒绝，再运行。把 `first.c` 的某个分号删除会产生编译诊断；把调用函数的名字与定义错开会出现编译或链接问题；把输入改坏只影响运行。发现问题先确认保存的源码、构建命令和运行的可执行文件是同一组。该初学操作是可执行学习任务，本文没有代填真人已学会；本次自动运行证据包括 first_input，不包括操作者自己创建的 first.c。

> [!question]- 首次输入练习的参考答案
> 行 `4096` 在 value 更新后越过业务上限，code_line 返回 −1，main 跳过均值输出并失败退出；前两行的临时和不被伪装为全记录结果。四行合法样本的循环不变量是 n 等于已接受行数、sum 等于这些行码值之和。数据还是码，默认每码 1 mV、零偏置才让 mean_mv 的数值等于码均值。

## 完整工程的文件与合同

| 文件 | 读者应找到的职责 |
| --- | --- |
| include/measure.h | 错误枚举、分配协议、样本所有者、标定、统计、借用环形窗口、写出回调 |
| src/measure.c | 严格文本/二进制适配、整数统计、物理零初态 FIR、报告 |
| src/main.c | CLI 参数、输入 FILE 的拥有与关闭、stdout 刷新/关闭和退出状态 |
| include/wordfreq.h、src/wordfreq.c | 有界哈希槽拥有键，临时词、排序借用与失败清理 |
| src/wordfreq_main.c | 词频工具的 FILE 生命周期和输出错误 |
| tests/test_measure.c | C API 合同、分配失败注入、存活分配计数、窗口与写回调失败 |
| tests/test_cli.py | 独立 Fraction 数学式、坏输入/超限、固定协议输出、真实 stdout 故障 |
| fixtures | 文本、真实 12 字节二进制、可读 hex、词频样本与精确预期 |
| Makefile | 多翻译单元 → 静态库 → 工具与测试；BUILD 可改为新输出目录 |

最终调用形式为 `measure text|binary FILE [SCALE_MV OFFSET_MV INTERVAL_S]` 和 `wordfreq FILE`。标定默认 1 mV/码、0 mV、1 s，三个可选参数要一起提供；参数由初始 C locale 下的 strtod 解析，要求完整转换、无 ERANGE、有限，随后检查业务范围。它接受 strtod 的数值语法，固定示范使用十进制。

文本是 count 后恰好 count 个 unsigned 十进制码，ASCII 空白分隔；每个 token 最多十位，总输入最多 16 MiB，FILE 按 rb 保留实际字节。二进制是四字节大端 count 后跟每项两字节大端码，支持 N≤10⁶ 和 0..4095；总长度最多 2000004 字节，额外数据非法。空文件 truncated；count0 合法解析，但统计 empty。ms_decode 接收“当前累计前缀”，eof=false 时完整前缀仍为 need_more，不交付对象；它不自动拼接相继分片。ms_read_text/ms_read_binary 则从 FILE 等待并读到最终 EOF。调用者真实拥有的可读范围是前提，size 不能凭数字制造存储。

ms_samples 必须初始化且为空才交解析器，失败不变，成功拥有数组并保存匹配 allocator/release/context；context 与分配出的真实存储都要满足寿命、大小和对齐合同。ms_samples 的浅拷贝不能生成两个可独立销毁的拥有者。ms_ring 借用调用者 slots[capacity]，不能靠假 capacity 证明存储存在；ms_fir 借用自己的内部数组，禁止按值复制后继续使用旧内部指针。同一记录标定保持不变，EOF 不排空 FIR。

词频协议只统计 ASCII 字母词，转为小写，非 ASCII 拒绝，其他 ASCII 字节（包括 NUL）分隔。最多 1 MiB、63 字母/词、256 键、521 个线性探测槽；频次递减、次键字典序递增。空词频文件成功输出空列表；读取失败不输出部分词表。输入字节计数用 uint32_t，键 count 用 size_t，增计数前检查 SIZE_MAX。固定表地址不变不等于更新后旧排序仍正确。

## 从新输出目录构建和复现

从仓库进入本实践目录；以下命令中的 build-local 是本目录下自选的输出目录，首次使用应不存在或为空。make 会创建它，源码/fixture 仍在原目录。需要强制新构建时换一个新名字，不先删除现有目录。

```sh
make BUILD=build-local test
build-local/first_input < fixtures/first-input.txt
build-local/measure text fixtures/samples.txt
build-local/measure binary fixtures/samples.bin
build-local/wordfreq fixtures/words.txt
build-local/measure text fixtures/samples.txt 0.25 -1 0.5
```

Makefile 显式 `-std=c17 -O2 -g -Wall -Wextra -Wpedantic -Wconversion -Werror`，编译 measure.c 与 wordfreq.c 为对象，再由 ar 建 libmeasure.a，CLI/test 分别链接这个库。`make CC=gcc BUILD=另一个新目录 test` 可选择已有 GCC，但本轮只实跑下述 clang，不把这条可复现接口记成 GCC 已验证。构建测试不加 NDEBUG：测试 assert 包含检查调用，移除断言不是同一个测试合同；库对外部输入的必要检查没有依赖 assert。

默认两种 measure 调用的精确输出都等于 fixtures/expected.txt：

```text
n=4
interval_s=1
sum_mv=20
mean_mv=5
descriptive_variance_mv2=5
rms2_mv2=30
fir_mv[0]=1
fir_mv[1]=3
fir_mv[2]=5
fir_mv[3]=7
```

词频 fixture 输出 red3、blue2、green1（三行键与次数以空格分隔）。最后的迁移调用应产生 sum1、mean0.25、variance0.3125、RMS²0.375 与 FIR −0.25,−0.25,0.25,0.75。输入和预期不靠执行未定义行为构造。

消毒器使用另一新目录：

```sh
make BUILD=build-sanitize-local CFLAGS='-std=c17 -O1 -g -Wall -Wextra -Wpedantic -Wconversion -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' test
```

这是 clang 的编译/运行能力，不是 C17 标准接口；目标上没有支持时主线仍可构建，并记录消毒器层未跑。不把未报错当作所有路径、语言规则、设备或真人理解的证明。

## 正常、失败与资源状态的可检查答案

| 输入或故障 | 精确结果与资源状态 | 当前检查 |
| --- | --- | --- |
| 默认四点与随机合法短记录 | 描述性 N 分母、RMS²含均值平方、FIR每真实输入一项 | fixtures 逐字节对照；Fraction 独立公式计算 |
| 每种 binary 前缀截断、文本缺码 | truncated；decode 的 eof=false 为 need_more；空 out 不被提交 | C与CLI |
| 坏码4096、符号、NUL、尾随 token/byte | invalid，非零退出；解析失败 stdout 为空 | C与CLI |
| N1000001、十位之外 token、1MiB/16MiB超限、64字母词、第257键 | limit；已取得临时键/数组释放 | C部分及CLI边界 |
| count0或空词频 | 测量 empty；词频成功空输出 | C与CLI |
| 分配器第1次/词频各新键分配失败 | nomem；out空、live分配计数归零 | C注入 |
| 写回调第k次失败 | io，可留下输出前缀；样本/词表所有权仍由调用者清理 | C注入 |
| stdout给只读文件描述符 | 两个最终CLI返回1，stderr含error=io，原文件字节保持 | Python真实主机故障夹具 |
| 相邻码1及非零偏置 | 首项保留半码；前物理输入0而非码0对应偏置 | C及Fraction对照 |
| 哈希碰撞与槽回绕 | tu/anr/bmd初桶520，tv初桶0；输出tu2、anr1、bmd1、tv1 | CLI固定预期 |
| 1000000个4095 | sum4095000000、variance0、RMS²16769025 | C真实分配与运行 |

Python独立对照用 Fraction 构造物理 x，再直接算 Σx/N、Σ(x−mean)²/N、Σx²/N 和相邻物理平均，避免调用生产库计算“预期”。随机种子242、N=1/2/4/17/100、scale/offset为(1,0)、(0.5,−3)、(2,7)。浮点容差 `isclose(rel_tol=1e-12,abs_tol=1e-10)`，绝对项分别按mV或mV²，错误状态/长度/协议字节精确比较。小scale下溢、大偏置抵消等极端值仍没有普遍精度保证；第12讲给出有限范围与舍入边界。

C测试在同一个 FIR 对象上遍历四点的全部8种分批边界组合；API只有逐点next，边界处保持对象，输出恒为1,3,5,7。测试不做越界读取来“验证”拒绝。小size_t容量拒绝有源码前置检查与整数证明，本机64位size_t没有执行到小平台这一分支，不把证明写成16位目标实跑。

## 本次实际运行与未验证层

2026-10-11 本机运行，编译器 Apple clang 21.0.0 (clang-2100.3.34.2)，Target arm64-apple-darwin27.0.0；`command -v clang` 为 `/usr/bin/clang`，clang 的 InstalledDir 指向 XcodeDefault.xctoolchain。Python 3.14.7。新普通/消毒器对象文件的调试 producer 字符串也均为该 Apple clang 版本，区别于2026-10-10首次尝试的Homebrew clang23.1.0；本段只记录2026-10-11新构建。采用上面已有源码与 fixture，无额外第三方库安装。实际工程命令为：

```sh
make BUILD=build-20261011 test
make BUILD=build-sanitize-20261011 CFLAGS='-std=c17 -O1 -g -Wall -Wextra -Wpedantic -Wconversion -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' test
build-20261011/measure text fixtures/samples.txt
build-20261011/measure binary fixtures/samples.bin
build-20261011/wordfreq fixtures/words.txt
build-20261011/first_input < fixtures/first-input.txt
```

两次 make 都从新的对应目录生成静态库与工具，返回码0；C合同测试均输出 `C contract tests: PASS`，7组Python测试全部成功；ASan/UBSan运行未报错。两种fixture适配器实际输出同一份上列结果，词频与首输入也实际执行正确。消毒器运行没有单独启用/认证 LeakSanitizer；分配失败清理证据来自C测试自定义allocator的live计数，不扩大为所有路径的泄漏证明。构建输出和dSYM属于本机可再生文件，不作为跨机发行产物。

这是一段阶段0–3的课程与工程候选，重要行为的独立审阅由未参与实现的审阅者另行核对；作者与测试自查不等同于独立验收。没有单独注入输入 fclose 故障、只在 fclose 时发生的故障或底层读取故障；真实 stdout 故障已跑，但不能据此认证所有关闭错误分支。没有实跑调试器会话、GCC/Windows/16位目标、Obsidian显示或真人学习验证。

阶段4仍缺完整有界线程生产消费、C11线程/原子支持实测、freestanding固定缓冲分支、窄C ABI跨语言消费例和目标ABI验证。没有真实ADC、DMA、控制闭环、硬件精度/时序或实时期限证据。原有系统08提供这些机制的入口，不能由这里的模拟文件与标准库运行宣称这些分支已完成，也不能宣称 #242 全部验收。

## 返回主解释并完成迁移

字节解析→[[计算机知识/10-编程语言/03-C语言/10-系统课程/10-对象表示别名与二进制解析#先构造值，再考虑优化|对象模型]]→解释为什么奇地址可以逐字节解析而虚构size仍不合法；环形状态→[[信号与系统/20-数字信号处理/01-FIR滤波设计与频率规格#手算核与迁移验收|FIR零延拓与尾部]]→保留跨批次状态；统计字段→[[电子电路/38-随机噪声与测量/01-RMS方差相关与谱密度#同一记录的中心与平方|有限记录的RMS²恒等式]]→用30=25+5确认单位和分母。三个往返题的答案要能回到本工具实际数据与对象，不能只说“有链接”。

不给操作提示的题与可折叠答案已放在第11/12讲；读者可改变键数、窗口核、scale/offset/dt后提交自己的预测与结果。源码和固定测试支撑模型走读，不代替真实读者的解释与反馈。
