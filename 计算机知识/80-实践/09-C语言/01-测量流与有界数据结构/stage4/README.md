---
type: lab
stage: 4
aliases: []
sources:
  - "https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf"
  - "https://www.open-std.org/jtc1/sc22/wg14/www/docs/n2396.htm"
  - "https://doc.rust-lang.org/nomicon/ffi.html"
prerequisites:
  - "[[计算机知识/10-编程语言/03-C语言/10-系统课程/12-测量流工具的完整工程]]"
---
# 阶段4实验：队列、固定缓冲与窄C ABI

先读 [[计算机知识/10-编程语言/03-C语言/10-系统课程/13-线程固定缓冲与C接口边界|第13讲的对象与协议推导]]，阶段0–3源码和已记录运行继续见 [[计算机知识/80-实践/09-C语言/01-测量流与有界数据结构/README|实践主入口]]。本分支新增源码在stage4/，没有改动既有measure.c、其公开头文件、原测试或fixture。新ABI适配器调用原统计接口；旧审阅范围继续只覆盖原字节，新队列/固定缓冲/ABI须独立核对。

## 源码真源与支持矩阵

| 文件 | 对象、支持条件和实际结果 |
| --- | --- |
| probe.c | 条件检查C11 threads/atomics宏，分别尝试原子与线程创建/join；原子本机通过，线程返回77 |
| thread_queue.c | 完整标准C11队列分支与受条件保护的不支持入口；本机仅编译/运行不支持入口，主体未编译/未运行 |
| fixed.h、fixed.c | 调用者固定存储，最多1024码，块失败保持状态/输出，整数半码；freestanding模式编译通过 |
| test_fixed.c | 宿主验全部8种四点分块、坏码/输出容量/1024上限、状态/输出保持；普通和消毒器都通过 |
| cabi.h、cabi.c | 版本化C符号、uint32错误、调用者拥有输入/输出、无跨侧释放；静态库提供实际实现 |
| abi_consumer.cpp | C++17 extern C调用、布局/正常/错误/单位核对；普通、消毒器通过 |
| abi_consumer.rs | Rust2021 repr(C)/extern C和带理由unsafe调用；当前宿主正常构建通过 |
| Makefile、run_checks.py | 小规模构建与带15s超时的可执行检查，明确保留77不支持结果；不安装或改系统 |

不支持不是“通过线程测试”。run_checks只将已支持且真正执行的检查判为PASS；UNSUPPORTED显示并保留在最后一行，绝不转换成标准C11线程运行证明。线程源在支持的目标上需要重新编译、运行和审阅。本例不使用POSIX包装替代C11名字。

## 主机复现命令与实际工具链

在stage4目录执行：

```sh
make BUILD=build-stage4 test
make BUILD=build-homebrew CC=/opt/homebrew/opt/llvm/bin/clang CXX=/opt/homebrew/opt/llvm/bin/clang++ test
make BUILD=build-stage4 rust-test RUSTC=/Users/ysz/.cargo/bin/rustc
```

Makefile默认显式CC=/usr/bin/clang、CXX=/usr/bin/clang++、AR=/usr/bin/ar，避免随PATH改变运行身份；其他机器按已存在工具链设置CC/CXX/AR，不复制本机路径假装已安装。核心C使用-std=c17 -O2 -g -Wall -Wextra -Wpedantic -Wconversion -Werror；C++consumer是-std=c++17。Rust consumer是可选单独目标，缺rustc只记录未运行，不影响固定缓冲/C++分支。

2026-10-11实际执行的Apple工具链为Apple clang21.0.0 (clang-2100.3.34.2)，目标arm64-apple-darwin27.0.0；另一套已安装Homebrew clang23.1.0，目标同为arm64-apple-darwin27.0.0。Python3.14.7；现有rustc1.89.0 (29483883e 2025-08-04)，路径/Users/ysz/.cargo/bin/rustc。两个C工具链普通新目录构建均返回0；实际Rust调用先按以下命令完成，随后也用上面的rust-test目标（-C codegen-units=1）重新链接并通过，限制为一个代码生成单元。不使用Cargo、不下载crate：

```sh
/Users/ysz/.cargo/bin/rustc --edition=2021 abi_consumer.rs -L native=build-stage4 -l static=cabi -l m -o build-stage4/abi_consumer_rust
build-stage4/abi_consumer_rust
```

两套工具链探针都输出：

```text
threads_macro=0
atomics_macro=1
atomic_uint_lock_free=1
atomic_local_increment=PASS
create_join_increment=UNSUPPORTED
```

probe的退出77只表示线程子检查不支持；原子初始化/fetch_add/load已在单线程实跑，atomic_uint本机lock-free=1。它不代表任意原子类型lock-free，更不代表队列wait-free或已验证跨线程顺序。标准C11队列入口同样返回77并输出bounded_queue=UNSUPPORTED_C11_THREADS_OR_ATOMICS。两套现有工具链都声明不支持；没有卸载/安装或改宏把不支持伪作支持。

## 线程对象、结束与失败合同

完整支持分支在thread_queue.c的#else中：main拥有capacity2的queue、输入64码、producer_context、consumer_context；producer/consumer只借用这些对象，main在所有创建成功的线程join之后才销毁条件变量与锁、退出这些自动对象的寿命。最多main+producer+consumer=3个线程，不为了吞吐增加工作者。每条记录64码，20轮串行运行正常/坏码取消/生产者创建失败注入。系统线程栈尺寸由实现决定，源码内固定负载没有堆增长。

mutex保护head、length、closed、cancelled与槽内容，0≤length≤2、head∈{0,1}。producer在full且未结束/取消时while等待nonfull；consumer在empty且未结束/取消时while等待nonempty。cnd_wait要求当前线程持锁，等待期间释放并在返回前重新获得锁；被唤醒后条件可能再次改变，while重新检查谓词。正常close后consumer排空剩余数据再返回0；cancel优先于槽内容，丢弃尚未消费的队列，并向两类等待者broadcast。

atomic published/consumed仅为诊断计数，使用relaxed；队列数据发布依靠锁，不依靠这两个计数。没有从计数推断槽已写完。consumer自己的输出数组和FIR状态只由consumer访问，main在join完成后读取并检查每个值和次序，不在未结束时读非原子结果。

初始化逐项成功才建立后续资源；cnd_init失败只销毁已经初始化的对象。consumer创建失败时没有工作者借用；producer创建失败时设置cancel、唤醒consumer并join，再销毁。正常/取消路径都join每个创建成功的线程，绝不销毁仍有人等待的条件变量。创建失败注入跳过真实thrd_create并使用thrd_error，测试清理协议；不是本机操作系统真的耗尽线程资源的证据。未运行的同步函数硬故障走fail-stop：require_success输出fatal并_Exit(1)，不会在可能仍有借用时free/destroy；这不是库级可恢复错误模型，进程结束回收由host负责。

本机不支持，以上队列主体没有编译/执行。源码中完整正常、排空、取消、创建失败和join判据是后续支持目标的实验接口，不是当前测试成绩；无调度公平性、最坏等待、无饥饿或实时期限保证。探针/检查器15s超时是主机测试界限，不能据此推导实时期限。

## 固定缓冲与freestanding证据

fixed.c只依赖stddef.h/stdint.h/limits.h，无malloc、FILE、数学库、线程、设备或启动代码。wwl_fixed_state存n、sum、squares、previous；调用者拥有初始化状态、input[n]和output[n]，三者不重叠且存储实际有效。capacity不足、坏码或累计超过1024时，在任何写入前拒绝，状态与output保持。完整块先验证，再更新；并不尝试运行越界输入来证明拒绝。

输出是半码整数：output=previous+code=2*y，默认1mV/码、0偏置；初态previous0。输入2,4,6,8产生2,6,10,14，宿主除以2得到1,3,5,7mV，奇数码保留半码。它不是任意scale/offset的原hosted实现，也不代表ADC/Q15设备协议。N≤1024，sum≤4193280、squares≤17171481600；uint64_t先宽化平方，数据与控制范围分别核对。

Makefile将核心编译为-ffreestanding -fno-builtin对象。两套普通构建的 `/usr/bin/nm -u fixed.o` 均为空，说明这两个实际对象没有未定义外部运行库符号；它不是任意编译器/优化设置的普遍保证。test_fixed再以宿主main链接该对象，验证8种分块与全部失败保持、1024个4095和第1025次拒绝。裸机启动、链接脚本、栈/地址空间、设备访问、IRQ/DMA和缓存行为没有运行；不能把宿主运行称为freestanding设备启动成功。

## ABI所有权与可核对宿主布局

cabi.h的wwl_c_measure_v1使用uint16_t码指针、uint32_t条数/错误/输出大小、double标定、版本化结果结构；调用者拥有数组和结果，C只在调用期间借用，不保留指针、不分配、不释放调用者数据，没有回调。C内临时ms_samples借用输入，禁止destroy这个借用描述符；调用原统计函数后在成功时才提交结果。错误0成功、1invalid、2limit、3empty；失败不改结果。n、out_bytes不是实际存储证明；可接受n要求真实可读codes[n]，超限n在读取前拒绝，out仍需为真实结果对象。调用者满足对象有效、对齐、大小与不重叠。

这是native ABI而不是磁盘格式，不能将结构体字节复制成跨机协议。wwl_c_layout_v1与C++/Rust各自的sizeof/alignof/offsetof逐字段对照，固定宽度和布局只处理机器层的一部分，所有权规则还需调用者遵守。宿主实际结果为result大小40字节、对齐8、mean偏移16、rms2偏移32；只有本轮arm64-apple-darwin目标和列明工具链得到这份运行证据，其他目标需要重验。

两套C++consumer实际返回PASS：同一四点对象sum20/mean5/variance5/RMS²30；坏码、错误输出尺寸、空输入、超限和非法scale返回对应错误并保持原结果；0.25/−1标定得到sum1/mean0.25/variance0.3125/RMS²0.375。Rust consumer也实际核对repr(C)、布局、数值和坏码保持并返回PASS；unsafe注释逐个说明真实数组与结果的寿命、大小、对齐和不保留指针。该Rust最小例没有回调或Rust导出函数，assert panic在C返回之后发生；C++例不在C边界抛出异常。此合同禁止跨边界展开，不将extern C或repr(C)当异常/panic处理器。涉及回调/异常的接口另行设计和测试。

## 消毒器与未验层

实际对Apple新目录执行：

```sh
make BUILD=build-stage4-sanitize CFLAGS='-std=c17 -O1 -g -Wall -Wextra -Wpedantic -Wconversion -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' CXXFLAGS='-std=c++17 -O1 -g -Wall -Wextra -Wpedantic -Wconversion -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' CHECK_ARGS=--instrumented test
```

固定缓冲和C++ABI测试成功，未报ASan/UBSan；线程仍77不支持。instrumented fixed.o确有ASan/UBSan未定义符号，检查器明确打印zero_runtime_reference_claim=NOT_APPLICABLE_INSTRUMENTED_OBJECT，没有把消毒器对象伪称零运行库引用。Rust消费例未用消毒器，不把C++instrumented结果移植成Rust工具链证据；没有运行TSan，因为标准C11队列没有运行。

待独立复核的新增行为是：队列谓词/所有权/close与cancel/join协议、固定块的预验证与不重叠前提、整数精度/资源界、native ABI布局与错误保持、consumer unsafe理由，以及文档是否严格分开条件不支持、宿主实跑、freestanding编译和设备未验。阶段0–3的旧测试结果保留并注明复用，未为本增量重复重跑整门课测试或维护检查器。

## 迁移题与参考判据

不提供步骤：让两个消费者同时参与该记录，并允许C库返回一份动态分配的结果。现有顺序FIR与借用ABI能直接保留吗？你应交付哪些新合同和证据？

> [!question]- 参考答案与接受标准
> 多消费者弹出顺序可能仍有锁保证，但消费完成顺序和各自FIR历史不再是一条流；需要单一顺序状态拥有者或明确序号与重新排序/状态合并，不能只加线程。队列结束要唤醒所有等待者并join全部已创建者；容量、线程栈和错误停止也重新核对。动态ABI结果必须由分配侧提供显式释放函数/不透明句柄或约定兼容分配器，不能默认C malloc与Rust/C++自由交叉释放。测试布局/长度/失败/取消/重入和生命周期；本机线程不支持时只能交条件接口，不把非标准替代跑通称作C11线程证明。


## 跨语言错误保持的后续实验

2026-10-11后续增量保留cabi.c/cabi.h和旧生产库字节，在abi_consumer.cpp与abi_consumer.rs增加同一错误矩阵。每次失败后分别检查abi_version、n、sum_mv、mean_mv、descriptive_variance_mv2、rms2_mv2六个字段等于先前成功对象；不比较可能存在的结构体padding字节，也不把结构体按字节协议传输。

C++与Rust各覆盖12项：坏码4096、结果尺寸小1、NULL输入配n=0（EMPTY）、1000001超count（LIMIT）、NULL输入配n=1、scale0、scale NaN、offset无穷、interval NaN、scale1000001、offset1000000001、interval0。除了EMPTY/LIMIT，其余返回INVALID；每一项单独检查结果保持，不能等最后再检查。正常数组均为真实存活存储；超限count、错误尺寸和NULL路径由当前实现先拒绝，实验不通过虚构合法长度或悬空指针获得答案。

此外检查NULL out返回INVALID；layout给实际10槽但声明9返回INVALID且10槽原字段全部保持，NULL layout同样INVALID。C++额外保留原迁移标定结果，Rust保留原四点与布局对照。异常/panic只在消费例验证失败时、C函数返回之后产生，没有导出回调、跨边界unwind或分配转移；不据这些测试认证任意unsafe调用。

在stage4目录使用新的构建目录：

```sh
make BUILD=build-abi-failure build-abi-failure/abi_consumer
build-abi-failure/abi_consumer
make BUILD=build-abi-failure RUSTC=/Users/ysz/.cargo/bin/rustc rust-test
make BUILD=build-abi-failure-sanitize CFLAGS='-std=c17 -O1 -g -Wall -Wextra -Wpedantic -Wconversion -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' CXXFLAGS='-std=c++17 -O1 -g -Wall -Wextra -Wpedantic -Wconversion -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' build-abi-failure-sanitize/abi_consumer
build-abi-failure-sanitize/abi_consumer
```

实际Apple clang/clang++21.0.0（clang-2100.3.34.2）、arm64-apple-darwin27.0.0，stage4 Makefile显式/usr/bin/clang与/usr/bin/clang++。Rust为已安装的rustc1.89.0（29483883e 2025-08-04），edition2021，无Cargo依赖下载。两种普通消费均返回0，输出12_error_cases/all_fields_unchanged/null_output/layout_rejection；C++本目标仍报告result_bytes40、result_align8、mean_offset16、rms2_offset32。C++的ASan/UBSan消费返回0、无报错；Rust未消毒器，不继承C++的消毒器成绩。第一次从父工程目录误调用rust-test没有对应目标，未生成ABI结果；上述命令在stage4目录修正执行后才构成实跑证据。

本增量只重建必要ABI库/消费者，没有改probe、thread_queue或复跑不支持的队列入口；原C11线程77及完整主体未编译/未运行结论保持。本故障矩阵尚待独立复核，底层FILE读取/关闭注入另见 [[计算机知识/80-实践/09-C语言/01-测量流与有界数据结构/README#可控读取与关闭故障：2026-10-11 后续实验|FILE故障与清理]]。


## 直接检查头文件、链接与队列主体

此前probe.c依据条件宏避免包含不可用头文件，成功构建的是不支持入口。2026-10-11后续补充 `thread_smoke.c` 与 `check_threads.py`，直接无条件包含threads.h与stdatomic.h，分别保存可见编译诊断、链接结果和运行结果。probe.c、thread_queue.c及measure.c保持原字节，没有#undef特性宏、兼容包装或系统安装。

thread_smoke在支持目标建立一个mutex、一个condition与一个worker；main先持锁再创建worker，value仍为0，因此main必须至少一次cnd_wait释放锁，worker才可发布42。main以while复查，解锁后join，核worker返回7与atomic done=1，再销毁同步对象；最多两线程。锁/等待/信号/join硬错误使用进程fail-stop；创建失败在没有worker时解锁并逆序销毁。该源文件在本机缺头文件处停止，后续逻辑仅是可审阅实验接口，未宣称本机线程执行。

脚本先打印工具链身份、C17预定义条件宏，再单独编译thread_smoke.c；成功才链接并运行。若宏声明不支持且只有一条error诊断，其fatal missing filename精确为对应threads.h或stdatomic.h，返回77并显示missing_C11_header。只识别列明的Clang/GCC英文缺头诊断形式；包含栈路径不参加缺失文件名判断，混合其它error或无法识别的诊断保守返回1。其它语法/编译错误、链接失败、运行失败或超时返回1，不用77掩盖源码错误。如果直接API可运行但实现仍声明不支持，单独标记该矛盾并保留77，不强行启用条件队列。宏宣告可用且smoke运行成功才直接编译thread_queue.c与原measure.c，并执行完整20轮队列判据；只有queue输出正常、排空、取消、创建失败、join、顺序FIR的PASS且返回0才报告queue_body=COMPILED_AND_RUN。工作者最多main+producer+consumer=3，编译30s、运行15s超时仅用于实验进程边界。

在stage4目录执行（BUILD名称按需要选择新的目录）：

```sh
python3 check_threads.py --cc /usr/bin/clang --build build-direct-apple-final
python3 check_threads.py --cc /opt/homebrew/opt/llvm/bin/clang --build build-direct-homebrew-final
make BUILD=build-thread-stubs build-thread-stubs/probe build-thread-stubs/thread_queue
build-thread-stubs/probe
build-thread-stubs/thread_queue
```

前两条为本次实际执行命令，Python3.14.7；Apple clang21.0.0（clang-2100.3.34.2）与Homebrew clang23.1.0目标都为arm64-apple-darwin27.0.0。两套宏均advertised_no_threads=1、advertised_no_atomics=0，直接编译均退出1，具体诊断为 `fatal error: 'threads.h' file not found`；脚本均返回77、打印direct_thread_capability=UNSUPPORTED missing_C11_header与queue_body=NOT_COMPILED_OR_RUN。没有产生smoke对象/可执行文件，没有进入链接、运行或完整队列构建；不能把未进入的层记成链接失败或线程协议测试通过。

后三条实际以Apple clang重新构建既有受保护probe/queue：make返回0，probe原子初始化/增计数通过、lock-free=1但create/join不支持，probe与queue分别返回77。宏与真实头文件诊断一致，支持边界比单看宏更具体；这次没有重跑fixed/ABI、故障或整门课程测试，原结果仍按各自已有记录保存。

Makefile另提供 `make CC=/usr/bin/clang THREAD_BUILD=另一个新目录 thread-capability` 同一脚本入口；底层脚本77会使make非零，不能把它当线程PASS。其他已有支持工具链可传 `--cc`；目标链接约定需要时传 `--ldflag=-pthread`，这只是可复现接口，本机未使用或验证该参数。脚本不安装依赖、不抹宏；其他平台需以其自身头文件、运行库、目标和编译命令重新检查。不支持目标可继续完成 [[计算机知识/10-编程语言/03-C语言/10-系统课程/13-线程固定缓冲与C接口边界#宏、头文件与链接为什么要分别检查|分层支持与队列推演]]，保留真实线程、TSan、调度公平性/期限和设备层未验，而不阻塞hosted主线。


分类反例也已实际运行：存在的threads.h若内部include另一个缺失头，不能判作threads.h缺失。在stage4目录可独立复现这个失败（夹具只放在新构建目录）：

```sh
mkdir -p build-classifier-fixture
printf '#include <wwl_deliberate_missing_dependency.h>\n' > build-classifier-fixture/threads.h
python3 check_threads.py --cc '/usr/bin/clang -I build-classifier-fixture' --build build-dependency-local-fix
```

实际诊断点名wwl_deliberate_missing_dependency.h，脚本返回1/COMPILE_FAILED，尽管include-stack路径包含threads.h且实现声明no_threads=1。另实跑编译期强制include只含#error的夹具，再同时触发真实threads.h缺失；两条error合在一起时同样返回1/COMPILE_FAILED，不能吞掉独立编译错误。最后以新build-direct-apple-classifier-fix/build-direct-homebrew-classifier-fix目录重跑两套真实缺threads.h的检查，两者仍为77/missing_C11_header。这些分类回归不进入任何线程运行；夹具、对象目录属于可再生实验材料，不纳入交付源码组。
