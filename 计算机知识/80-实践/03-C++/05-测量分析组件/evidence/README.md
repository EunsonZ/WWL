# 报告任务：本机性能观察与验证边界

输入和算法真源是[report_benchmark.cpp](../src/report_benchmark.cpp)：24任务×2048原码；每份w32/h16，127完整窗口；队列容量2。1、2、3工作线程，加调用线程最多4个。每种线程数暖机1次，再观测7次；逐次检查完整报告文本一致、总字节一致和任务完成状态。原始数据[benchmark.csv](benchmark.csv)保留全部21条样本，单位µs。[环境/RSS记录](benchmark-runtime.json)和[程序观察摘要](benchmark-summary.txt)可对照。

| 工作线程 | 最小µs | 中位µs | 最大µs |
| --- | ---: | ---: | ---: |
| 1 | 1934 | 2038 | 2097 |
| 2 | 997 | 1016 | 1087 |
| 3 | 694 | 706 | 854 |

这是本次Release运行的观察分布。整批吞吐可按24×10^6/t计算（t为表中µs，单位报告/秒）；它包含启动和校验成本，不是每项任务排队/执行延迟。计时包含任务复制、启动线程、解析、扫描、格式化、结果复制、全文一致性校验与join，排除输入生成和控制台输出。没有固定CPU亲和性/频率、独占后台负载或可信尾延迟分位数；7样本不构成置信区间。多线程在这份输入下较快不保证任意工作量都较快。

环境实证为macOS27.0.1、arm64，实际CMake编译器/usr/bin/c++、AppleClang21.0.0.21000334、libc++220106、CMake4.4.3，C++20、Release、-fno-fast-math/-ffp-contract=off。PATH上的另一个clang++版本没有用于这次构建。具体芯片型号sysctl查询被沙盒拒绝；不将用户指定的M4当成工具认证型号。

在一个只启动本benchmark的全新Python父进程中，resource.getrusage(RUSAGE_CHILDREN).ru_maxrss观察到4,440,064字节（macOS单位字节，约4.23 MiB）。这是子进程高水位，远低于8 GiB；不是整个机器的总用量，也不是理论内存上界。进程实际输入只有约24×10 KiB，工作量不能拿来证明API最大输入的峰值。

Debug/Release分别完整构建并CTest8/8；默认安装consumer各3/3；Release另配CMAKE_INSTALL_INCLUDEDIR=public-api，重新构建/安装、独立消费3/3。独立工程只通过find_package取得公开头及导出目标。实际等待、close/cancel、FIFO、部分启动异常和任务寿命见[queue_tests.cpp](../tests/queue_tests.cpp)。没有使用assert作为运行时验收。

开发中发生两次可解释失败：第一次测试初始化把explicit ReportSettings默认构造写成隐式{}导致编译拒绝，修为显式ReportSettings{}；一次CLI测试的诊断正则写成cannot open input，而程序实际是cannot open batch input，修正测试后通过。最终干净Debug/Release均通过。测试缝隙模拟启动失败，没有真实耗尽OS线程，也没有逐点注入所有普通分配器。没有运行TSan、跨平台、动态库ABI、模块、协程或硬件型号认证。详尽构建日志保存在本隔离候选的过程evidence目录，不要求读者维护日志清单。
