---
课程: "C++"
层级: "进阶与边界"
类型: "实践与构建"
sources:
  - https://clang.llvm.org/docs/StandardCPlusPlusModules.html
  - https://cmake.org/cmake/help/latest/manual/cmake-cxxmodules.7.html
  - https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p1689r5.html
---
# 同一窗口报告的模块导入与头文件包含

先读[[计算机知识/10-编程语言/02-C++/10-系统课程/18-模块接口导入与构建边界|第18讲：接口、BMI与链接为何需要分别检查]]。本目录给已有ReportSession加一个C++20 named-module门面`wwl.measurement`。接口、实现单元、独立importer、普通包含consumer是不同翻译单元；统计/窗口/资源算法仍只存在于原[src/report.cpp](../../src/report.cpp)及[src/measurement.cpp](../../src/measurement.cpp)。

## 文件分别承担什么

| 文件 | 责任 |
| --- | --- |
| [wwl.measurement.cppm](wwl.measurement.cppm) | GMF包含已安装公开头；导出既有类型/函数别名及一个模块附属函数声明 |
| [wwl.measurement.cpp](wwl.measurement.cpp) | 模块实现单元，定义`interface_revision()`；不能只靠BMI链接 |
| [importer.cpp](importer.cpp) | 只导入named module，不包含wwl头；自己的流/文本/时间依赖显式include |
| [header_consumer.cpp](header_consumer.cpp) | 普通包含同版公开头；与importer共享[report_consumer.inc](report_consumer.inc)控制流程 |
| [type_identity.cpp](type_identity.cpp) | 同一TU中include再import，以static_assert核对别名仍是原类 |
| [run.py](run.py) | 全量新目录重建原静态库并安装；扫描P1689依赖；依图编译、链接、运行与预期失败 |
| [CMakeLists.txt](CMakeLists.txt)、[consumer/CMakeLists.txt](consumer/CMakeLists.txt) | 标准CMake模块目标与独立consumer目标；需要支持模块扫描的generator |
| [not_exported.cpp](failures/not_exported.cpp)等失败例 | 未导出名字、临时Session借用、重复非inline定义的真实源码 |

别名位于`wwl::modules`；`wwl::modules::ReportSession`与`wwl::ReportSession`为同一类型，名字改变没有产生第二份实现。尚未导出queue API、CLI配置或全部旧公共名字。该门面只承诺表中的测量/窗口子集。

## 本机已跑的无Ninja完整入口

在WWL根运行。脚本需要Python 3、CMake、Make和配对的Clang/clang-scan-deps；不会下载或安装工具。`--build`必须是新的库外目录，现有证据不被覆盖；原实践源码只读。

```bash
WWL_VAULT="$PWD"
MODULE_LAB="$WWL_VAULT/计算机知识/80-实践/03-C++/05-测量分析组件/advanced/modules"
python3 "$MODULE_LAB/run.py" --vault "$WWL_VAULT" \
  --build /private/tmp/wwl-modules-my-debug \
  --cxx /opt/homebrew/opt/llvm/bin/clang++ --config Debug
python3 "$MODULE_LAB/run.py" --vault "$WWL_VAULT" \
  --build /private/tmp/wwl-modules-my-release \
  --cxx /opt/homebrew/opt/llvm/bin/clang++ --config Release
```

非本机环境把`--cxx`改为自己的Clang++路径，并先核对同目录scanner是否存在。不能将`clang++`符号链接解析成`clang`后直接用新文件名调用：driver名字影响C++运行库的默认链接。脚本保留clang++调用名，仅解析scanner所在目录。

脚本先以`Unix Makefiles`构建原静态库、安装到本次build/prefix；随后所有模块接口与consumer的wwl include路径只有`prefix/include`，链接`prefix/lib/libmeasurement.a`。原TensorBuffer/布局头只用于旧库实现，不泄漏给importer。原项目不含named module，普通Make构建在这里合法；named-module部分由下述独立扫描调度，不能推论CMake Makefiles generator也能构建模块。

[clang-scan-deps](https://clang.llvm.org/docs/StandardCPlusPlusModules.html#discovering-dependencies)读取真实compilation database，每项含`output`。其[P1689](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p1689r5.html)输出给接口的`provides`和实现/导入者的`requires`；脚本核唯一provider、拒绝缺provider/循环，然后拓扑调度。本例只有一个named module，没有分区/header unit；实现与importer彼此无依赖，二者顺序可互换。

对应的关键命令如下；`$BUILD`为脚本创建的目录，`$MODULE_LAB`为本目录，具体完整命令保存在commands.log：

```bash
clang-scan-deps -format=p1689 -compilation-database="$BUILD/compile_commands.json" \
  -j 1 -o "$BUILD/dependencies.json"
clang++ -std=c++20 -I "$BUILD/prefix/include" \
  --precompile "$MODULE_LAB/wwl.measurement.cppm" -o "$BUILD/wwl.measurement.pcm"
clang++ -std=c++20 -I "$BUILD/prefix/include" \
  -c "$BUILD/wwl.measurement.pcm" -o "$BUILD/wwl.measurement.cppm.o"
clang++ -std=c++20 -I "$BUILD/prefix/include" \
  -fmodule-file=wwl.measurement="$BUILD/wwl.measurement.pcm" \
  -c "$MODULE_LAB/wwl.measurement.cpp" -o "$BUILD/wwl.measurement.cpp.o"
clang++ -std=c++20 -I "$BUILD/prefix/include" \
  -fmodule-file=wwl.measurement="$BUILD/wwl.measurement.pcm" \
  -c "$MODULE_LAB/importer.cpp" -o "$BUILD/importer.cpp.o"
clang++ "$BUILD/importer.cpp.o" "$BUILD/wwl.measurement.cppm.o" \
  "$BUILD/wwl.measurement.cpp.o" "$BUILD/prefix/lib/libmeasurement.a" \
  -pthread -o "$BUILD/module_consumer"
```

这是显示依赖的核心命令；实际脚本对每一编译步骤一致使用Debug `-O0 -g`或Release `-O3 -DNDEBUG`、`-fno-fast-math -ffp-contract=off`及警告参数。已有build目录拒绝重用，脚本每次扫描/重编译全部源与头，从而不复用旧BMI。它没有实现增量头依赖缓存或生产构建系统；工程中的增量重建交给下一节CMake。

## CMake自动扫描入口与已验边界

[CMake官方模块说明](https://cmake.org/cmake/help/latest/manual/cmake-cxxmodules.7.html)自3.28支持模块file set；本例将接口放入`PUBLIC FILE_SET ... TYPE CXX_MODULES`，实现单元是普通target source；consumer通过target_link_libraries取得BMI依赖和旧库链接要求。需要支持扫描的工具链和generator，Ninja要求1.11或更新。本项目不用`import std`或header unit，也不把二进制BMI做可移植安装包。

先完成上节原库安装，再在WWL根运行：

```bash
WWL_VAULT="$PWD"
MODULE_LAB="$WWL_VAULT/计算机知识/80-实践/03-C++/05-测量分析组件/advanced/modules"
COMPONENT="$WWL_VAULT/计算机知识/80-实践/03-C++/05-测量分析组件"
# 使用已有Ninja；本次审阅者在隔离venv中固定1.13.2，未改系统PATH。
WWL_NINJA=/private/tmp/wwl-cpp-modules-ninja-validation-20261011/venv/bin/ninja
cmake -S "$MODULE_LAB" -B /private/tmp/wwl-modules-my-cmake -G Ninja \
  -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm/bin/clang++ \
  -DCMAKE_MAKE_PROGRAM="$WWL_NINJA" \
  -DCMAKE_BUILD_TYPE=Debug -DCMAKE_PREFIX_PATH=/private/tmp/wwl-modules-my-debug/prefix \
  -DWWL_CODES_INPUT="$COMPONENT/data/codes.txt" \
  -DWWL_REPORT_REFERENCE="$COMPONENT/data/report-reference.txt"
cmake --build /private/tmp/wwl-modules-my-cmake --parallel 2
ctest --test-dir /private/tmp/wwl-modules-my-cmake --output-on-failure
```

2026-10-11独立审阅者经授权在库外隔离venv固定Python包ninja==1.13.2（可执行版本1.13.2.git.kitware.jobserver-pipe-1），用本候选原源码/CMake字节、CMake4.4.3、Clang23.1.0实际configure/build/CTest：Debug/Release各`module_header_same_report`1/1通过。该测试不使用assert，全文核模块版、包含版和旧参考；另有外部项目通过add_subdirectory连接measurement_module，Debug/Release各2/2通过，自动传播BMI依赖和旧库链接要求。安装旧WWLMeasurement包的普通consumer两配置各3/3通过。这些补验来自独立审阅，作者手动扫描链仍保持自己的原证据身份。

审阅者只在scratch副本修改接口/实现检查增量：接口变化重编接口、实现及两个importer并重链接，未重编包含consumer；仅实现变化重编实现并重链接，未重编接口/importer；前后no-op构建均为`ninja: no work to do`。这是两项指定改变的调度观察，不认证所有头依赖、选项变化或工具链组合。

**模块安装边界**：本目录CMake没有模块目标的install/export规则，实际cmake --install没有交付文件；find_package(WWLMeasurementModule)探针实际失败。外部add_subdirectory消费的是模块源码目标，已安装的是旧WWLMeasurement头/静态库；尚未交付安装后的named-module package、可跨工具链复用的BMI或动态ABI。原作者的缺Ninja的configure记录仍保留为历史，不能代表这次补验后的状态。

## 已运行输出与反例

2026-10-11本机：Homebrew Clang 23.1.0，配对clang-scan-deps 23.1.0，libc++ `_LIBCPP_VERSION=230100`，CMake 4.4.3，Darwin 27.0.0/arm64，C++20。Debug/Release均通过正常比较、类型身份与七个预期拒绝；Release使用显式返回码/全文比较，`NDEBUG`不移除验证。此记录是本机同编译器静态链接观察。

固定输入`2 4 6 8`及1mV/码、1s、w2/h1输出与旧[data/report-reference.txt](../../data/report-reference.txt)逐字一致：

```text
label=adc count=4 interval_ms=1000 gain_uV_per_code=1000 offset_uV=0 window=2 hop=1 windows=3
begin=0 end=2 first_ms=0 last_ms=1000 sum_mV=6 mean_mV=3 population_variance_mV2=1 rms_squared_mV2=10
begin=1 end=3 first_ms=1000 last_ms=2000 sum_mV=10 mean_mV=5 population_variance_mV2=1 rms_squared_mV2=26
begin=2 end=4 first_ms=2000 last_ms=3000 sum_mV=14 mean_mV=7 population_variance_mV2=1 rms_squared_mV2=50
```

新输入`1 3 5 7`：三窗均值2/4/6mV，描述性方差各1mV²，RMS²5/17/37mV²；空输入count0/windows0退出0；`2 bad 6`两版都退出2、stderr为`error: each token must be a complete decimal ADC code`。脚本同时比较stdout、stderr、退出码，并对固定输出核原参考；小例精确不推论全输入浮点位级相等。

| 改一个构建/代码条件 | 本机观察 | 说明的边界 |
| --- | --- | --- |
| 导入时不给BMI映射 | `module 'wwl.measurement' not found` | 编译前要有可用的接口依赖 |
| 使用未导出的`wwl::modules::CommandOptions` | 无该成员的编译诊断 | 包含旧头不等于将所有名字export |
| `ReportSession{}.text()` | 调用deleted的右值重载 | 模块门面保留原借用约束 |
| 链接不带接口/实现对象 | undefined `interface_revision@wwl.measurement`等 | BMI不包含供链接器使用的全部对象代码 |
| 带模块对象却不链接原静态库 | undefined `ReportSession`等 | export using并没有定义原函数实现 |
| C++23导入C++20的本次BMI | `C++23 was disabled in precompiled file`、configuration mismatch | BMI有编译配置边界；不能盲复用 |
| 两个实现TU各定义同一非inline函数 | duplicate symbol `interface_revision@wwl.measurement()` | 本例真实ODR冲突被链接器拒绝；不是所有ODR违例都能诊断 |

build目录保存commands.log、dependencies.json、compile_commands.json、build-order.json、summary.json、原源码SHA、每例stdout/stderr与七份diagnostic。`run.py`在收尾复核原源码未漂移。完整输出文件留在本次本机库外证据，不把PCM/对象/安装树提交为教材源码。课程更一般的ABI与ODR条件见第18讲。

## 自己迁移一次

将新输入改为`0 2 4 6 8`，先预测四窗均值1/3/5/7mV、末样本时间1000/2000/3000/4000ms，再分别运行两版并核对。不改标定、不把w2误读成两秒钟。

只删除实现单元的对象能否通过链接？不能：importer调用模块附属`interface_revision`。删除原库但保留模块对象同样不能：ReportSession仍属于原全局模块实体。若把库本身整体改为模块附属定义，需要一起迁移声明、定义、类型身份和符号，不能靠更换include所在位置完成。

未验层：上述指定增量变化之外的构建条件、GCC/MSVC、跨编译器/标准库/动态库ABI、模块package/BMI安装分发、性能收益、客户端显示和真人学习。模块化没有扩大PMR故障计数域，也没有执行原组件全部八项CTest。
