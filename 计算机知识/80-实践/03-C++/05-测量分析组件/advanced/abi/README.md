---
type: lab
stage: 4
aliases: []
sources:
  - https://cmake.org/cmake/help/latest/prop_tgt/POSITION_INDEPENDENT_CODE.html
  - https://cmake.org/cmake/help/latest/prop_tgt/SOVERSION.html
prerequisites:
  - "[[计算机知识/10-编程语言/02-C++/10-系统课程/17-动态C接口版本与释放边界]]"
---
# 安装一个版本化 C ABI，再由纯 C 程序消费

本目录是现有 ReportSession 的高级包装，统计/窗口/异常提交仍编译消费已安装的原库。解释入口见 [[计算机知识/10-编程语言/02-C++/10-系统课程/17-动态C接口版本与释放边界|第17讲]]。公开真源为 [measurement_abi.h](include/wwl/measurement_abi.h)，实现为 [measurement_abi.cpp](measurement_abi.cpp)，C 调用过程在 [consumer.c](consumer/consumer.c)，失败实验在 [tests.cpp](tests.cpp)，真实SHARED实现的宿主默认PMR寿命回归在 [tests_default_resource.cpp](tests_default_resource.cpp)。

## 从干净目录构建并安装

先把 shell 当前目录设为本目录，再执行。需要已有 CMake、C/C++ 编译器；这里不安装工具。`mktemp` 产生库外目录，四类构建/安装目录互相独立。macOS 可明确传入 `/usr/bin/clang++` 和 `/usr/bin/clang`；也可将 C++ 编译器替换为已有 Homebrew clang，C 消费者仍保持 AppleClang。

```bash
ABI_SOURCE="$PWD"
BASE_SOURCE="$(cd ../.. && pwd)"
ABI_RUN="$(mktemp -d /private/tmp/wwl-abi.XXXXXX)"
cmake -S "$BASE_SOURCE" -B "$ABI_RUN/base-build" \
  -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_COMPILER=/usr/bin/clang++ \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_INSTALL_PREFIX="$ABI_RUN/base-install"
cmake --build "$ABI_RUN/base-build" --parallel 2
ctest --test-dir "$ABI_RUN/base-build" --output-on-failure
cmake --install "$ABI_RUN/base-build"
cmake -S "$ABI_SOURCE" -B "$ABI_RUN/abi-build" \
  -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_COMPILER=/usr/bin/clang++ \
  -DCMAKE_PREFIX_PATH="$ABI_RUN/base-install" -DCMAKE_INSTALL_PREFIX="$ABI_RUN/abi-install"
cmake --build "$ABI_RUN/abi-build" --parallel 2
ctest --test-dir "$ABI_RUN/abi-build" -V
cmake --install "$ABI_RUN/abi-build"
cmake -S "$ABI_SOURCE/consumer" -B "$ABI_RUN/c-build" \
  -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=/usr/bin/clang \
  -DCMAKE_PREFIX_PATH="$ABI_RUN/abi-install"
cmake --build "$ABI_RUN/c-build" --verbose --parallel 2
ctest --test-dir "$ABI_RUN/c-build" -V
otool -L "$ABI_RUN/c-build/abi_consumer"
otool -l "$ABI_RUN/c-build/abi_consumer"
nm -gU "$ABI_RUN/abi-install/lib/libmeasurement_abi.1.0.0.dylib"
env DYLD_PRINT_LIBRARIES=1 "$ABI_RUN/c-build/abi_consumer"
```

另用新 `ABI_RUN`，把三处 Debug 都改为 Release，再执行全套。测试用显式失败计数，不依赖 `assert`，因此 `NDEBUG` 不会使它们空过。这里的 `DYLD_PRINT_LIBRARIES` 仅在一个子进程里输出实际加载路径，没有设置全局库搜索变量。`otool`/`nm` 命令为 macOS 工具，其他系统需另核其加载器与符号验证方法。

ABI安装包只导出 `WWL::measurement_abi`，C消费目标没有 C++ 编译特性、C++公开头或 `WWL::measurement` 静态依赖。基库编译成 PIC 后被封装进 SHARED；它在实现内部仍要求匹配该实现的 C++ 工具链。`Config.cmake.in` 没有让 C 消费者再寻找基库，构建目录也没有通过 `add_subdirectory` 偷带源文件。

## 接口与资源约束

版本1要求配置尺寸精确一致；未知版本和短/长结构在字段读取前拒绝。配置的整数范围、空指针合同、NUL所需字节和输入生命周期都写在公开头中。输入最多8192字节；合法输入至少每个码一个字符、相邻码一个空白，因此最多4096个码。width/hop为1..4096，标签1..40个限定ASCII字符；其余标定和间隔范围继续由原库校验。

每次替换拥有一个暂时输入副本、解析对象及候选 Snapshot；提交过程中旧报告与新报告会短暂共存。参考窗口算法仍是 O(Kw)，不承诺恒定延迟。接口没有全局句柄数上限，也没有整个进程内存硬限额；8192字节只是单次输入限制。所有调用是同步的，同一handle必须外部串行化，库在handle存活时保持加载。输出由调用方分配和释放，库内对象只能经destroy释放。生产Session显式绑定静态存储期的 `std::pmr::new_delete_resource()`，不捕获宿主可变的默认PMR指针；C接口没有要求宿主保留一个临时默认pool。

## 实际观察与未覆盖范围

2026-10-11，macOS27.0.1（26A434）/arm64，CMake4.4.3；Apple clang21.0.0（clang-2100.3.34.2）与 Homebrew clang23.1.0。两种 C++ 实现组合各完成干净 Debug、Release 基库构建/安装与8/8基库测试，独立 SHARED 构建/安装与2/2 ABI测试（故障变体及真实SHARED默认PMR寿命），再由 AppleClang21 的 `LANGUAGES C` 工程完成1/1安装消费者测试。C++模式202002；Apple编译头 `_LIBCPP_VERSION=220106`，Homebrew编译头为230100，实际 dylib 都依赖 `/usr/lib/libc++.1.dylib`（otool current version2200.27.0）。这说明当前两套编译器/头加同一系统运行库组合可运行，不是任意运行库互换。

四组布局均为size64、align4、offsets0/4/8/12/16/20/24；正常四码的三窗均值3/5/7。安装消费者的链接命令直接引用安装 dylib；`otool -L` 指向 `@rpath/libmeasurement_abi.1.dylib`，`LC_RPATH`指向对应安装lib目录，单次 dyld 跟踪确认加载那里的1.0.0文件。`nm -gU`仅列五个公开C符号，测试钩子不在安装库。

未安装测试变体中，四码报告实际7个PMR分配点逐点失败后旧文本和live块/字节保持；destroy后live_handles/live_blocks/live_bytes均0。每个导出的五类异常映射均检验；合法空输入、8192字节/4096码上限、超限、坏码、配置范围、版本尺寸、短缓冲不写及迁移算例均有测试。真实SHARED回归另在create期间临时设定一个堆上pool为默认资源，恢复旧默认并销毁pool后继续replace/copy/destroy，验证句柄不借用该pool；独立C调用方另外验证实际动态库的布局、失败保留、哨兵、结果复制和释放。测试变体的故障证据不能替代已发布二进制自身的故障注入；各条验证责任明确分开。额外AppleClang21 Debug构建将基库、wrapper和消费者全部以 `-fsanitize=address -fno-omit-frame-pointer` 编译，2/2 ABI测试与1/1安装C消费者通过，无ASan诊断。该结果只覆盖实际执行的路径，不证明所有内存错误不存在。

构建每次最多2个并行作业，四组顺序执行；wrapper不启动线程。修正版四组非ASan程序另由独立子进程getrusage观察：故障测试RSS高水位4276224..4653056字节，真实SHARED寿命回归1867776..1949696字节，纯C消费者1900544..1966080字节（macOS单位）。这不含构建进程或ASan进程，也不是所有输入/句柄数量的上界。普通allocator/OS全部故障点、任意野指针/重复销毁检测、库热卸载、Linux/Windows/其他架构、长期压力与整个进程内存上界未验。没有把动态库加载成功称作跨平台通用ABI；Obsidian显示、同步和真人学习仍需另行确认。
