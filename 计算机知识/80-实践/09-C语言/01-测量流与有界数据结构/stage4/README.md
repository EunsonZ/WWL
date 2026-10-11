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
