---
type: lab
domain: computer-science
status: expanded
revision_date: 2026-10-11
sources:
  - https://doc.rust-lang.org/cargo/reference/manifest.html
  - https://doc.rust-lang.org/cargo/commands/cargo-package.html
prerequisites:
  - "[[计算机知识/10-编程语言/04-Rust/10-系统课程/11-类型化数据管道与标准库实作]]"
---

# 类型化测量任务：串行组件与运行入口

课程主线见 [[计算机知识/10-编程语言/04-Rust/10-系统课程/11-类型化数据管道与标准库实作|第11讲]] 与 [[计算机知识/10-编程语言/04-Rust/10-系统课程/12-Cargo组件工程与测量任务流|第12讲]]；它们从零程序推进到公开组件，本 README 负责重跑与证据边界。无 C/C++ 前置、设备、在线服务或第三方依赖。

## 进入工程后执行

以下命令均以本 README 所在目录为当前目录：

```sh
cargo run --manifest-path stages/first/Cargo.toml --locked --offline
cargo test --manifest-path stages/first/Cargo.toml --locked --offline
cargo fmt --check
cargo test --locked --offline
cargo run --locked --offline
cargo run --locked --offline -- --file fixtures/fixed.txt
cargo run --locked --offline -- --codes 2 4096
cargo run --locked --offline -- --codes
cargo run --manifest-path caller/Cargo.toml --locked --offline
cargo doc --locked --offline --no-deps
cargo package --locked --offline --list
cargo package --locked --offline
cargo run --locked --offline -- --config fixtures/task.conf
cargo test --locked --offline --features threaded
cargo run --locked --offline --features threaded -- --config fixtures/task.conf --threaded
cargo run --manifest-path caller/Cargo.toml --locked --offline --features threaded
cargo package --locked --offline --features threaded
```

非法输入命令预期退出2，不应被 shell 脚本当作运行失败而隐藏。初次由空项目自己编写时，先允许 Cargo 生成锁，再用 --locked；保存的三个 package 均携带各自锁文件。

## 合同与预期

SampleIndex是批内零基序号，主CLI单批时对应相对秒数。各批分别parse会重启序号；新增threaded模块先验证全局序号并用split_batch/split_batch_at保留同一输入身份。设备实际时间戳仍未核验。

固定 `[2,4,6,8]`、`1 mV/码`、零偏置、每秒一项；最多1024码，范围0..=4095。文件每行一项、行含换行最多64字节，接受LF/CRLF；空行、空格、符号、非ASCII数字和无法表示为u16的文本为Syntax。u16解析成功但码>4095为Range。任一输入错误整批拒绝；合法空输入得到和0、均值未定义。

固定输出：

```text
count=4 sum=20 mV
mean=5.000 mV
Low=1
Normal=2
High=1
t=0 s filtered=1.0 mV
t=1 s filtered=3.0 mV
t=2 s filtered=5.0 mV
t=3 s filtered=7.0 mV
```

sum手算20，mean手算5。Fir2初始前值0，一项一输出、EOF无尾项；连续状态输出[1,3,5,7]，每批重置的反例是[1,3,3,7]。HalfMillivolt存两倍mV，保留0.5的精确结果。sum最多4,193,280，u64安全；浮点mean对一般分数可能舍入。

## 文件如何对应学习阶段

- `stages/first`：独立第一个 Cargo 程序，数组、元组、函数、分支、循环、枚举、Result与边界单元测试；它是教学检查点，阶段1的整批拒绝语义另在主组件实现。
- `src/lib.rs`：领域类型与验证、拥有Batch/借用view、纯统计、FIR状态、BTreeMap Entry、VecDeque、BufRead/Write。
- `src/config.rs`：有256字节总上限的严格配置，拥有TaskConfig、分类错误与私有字段。
- `src/threaded.rs`：threaded feature下的唯一接收者、全局序号/总资源检查、持续FIR状态与drop-sender/join关闭；私有单元测试控制真实Full和失败节点。
- `src/main.rs`：路径/参数、输入完成后再输出、stderr与退出2；stdout写失败可能留下部分字节，flush失败被报告但不自动撤销外部输出。
- `tests/contracts.rs`：范围与长度、空输入、跨批状态、成功借用/修改、强失败保证、I/O/flush故障、宏生成分类测试。
- `tests/config.rs`：默认值、范围、未知/重复键、UTF-8/读取上限及报告数量错配。
- `tests/threaded.rs`：各种容量与批大小、任意分块/空批、重启序号反例、总项与批对象数上限。
- `tests/cli.rs`：公开CLI固定结果、非法输入、配置错误与feature门控。
- lib文档：公开API正常示例，单位混用、冲突借用、move后再用三个compile-fail示例。
- `caller`：独立package，仅依赖公开API。
- `fixtures`：正常/非法文本输入。

## 版本、包与复建边界

edition2021；rust-version1.89为本轮实际验证的支持下限，非“最早可兼容版本”推断。rustc1.89.0(29483883e,2025-08-04)，Cargo1.89.0(c24e10642,2025-06-23)，target aarch64-apple-darwin；无外部依赖、default feature为空，threaded=[]，新增fixed=[]、ffi=[fixed]分支、publish=false。旧课“未安装rustc”仍保留原批次身份。

主包include覆盖Cargo.toml/Cargo.lock/README、src/**、tests/**、fixtures/**、ffi/**和examples/**，实际归档共22个成员（见下方清单）。Cargo产生的归档包含规范化manifest及Cargo.toml.orig；独立Rust消费工程caller/、首课检查点stages/first/、nostd/共源检查器与过程证据不随主包交付，ffi/caller.c则包含在主包中。解包者能测试和运行库/CLI，完整学习检查点和独立调用方从课程仓库取用。本包未设置发布许可、未上传registry、未安装到用户PATH。

## 配置与同步分支的运行合同

fixtures/task.conf为capacity=1、batch_size=2、max_samples=4。默认构建支持配置，但不生成线程模块；请求--threaded时退出2并提示--features threaded。启用feature后CLI先借用求summary，再消费同一Batch分批，发送给唯一worker；返回前关闭唯一sender并join。--codes消费所有余下参数，配置与模式flag须在它前。

配置允许缺省字段，空文件用默认2/2/1024；未知或重复键、非法数值均拒绝，不默默忽略。capacity范围0..16，0为交接式同步；batch_size范围1..1024；max_samples范围0..1024。线程API还限制总批对象1024个，空批也计数，且检查全部Record索引连续。独立parse多个批的重启索引会被拒绝；任意批界可用split_batch_at保留身份。

Full时取回同一未发批并阻塞send；发送端关闭或worker失败时仍关闭sender、join并返回错误。所有正常返回/Result失败路径均等待拥有的任务；spawn失败时没有成功生成任务。内部故障注入覆盖worker Err/panic、接收提前关闭、满队列时失败；没有通过耗尽OS资源强行触发spawn失败。程序不进行外部设备写入，错误丢弃内存中部分计算结果；报告flush错误仍可能留下外部字节。

write_report保留Record原索引；右批索引2、3会打印t=2、3，单批报告会新建FIR，输出3、7。write_summary_report用于完整已验证流，从0按位置枚举；持续FIR的右批输出5、7不能由单批重启报告代替。批对象超限用BatchCountLimit明确报告batch objects，样本超限仍用Limit报告total samples。相关suffix与诊断回归已纳入本轮测试。

## 接续批次的验证与边界

2026-10-11接续批次实际验证：默认构建1项单元+18项集成+5项文档测试，共24项通过；threaded构建6项单元+22项集成+8项文档测试，共36项通过。两种构建均在新空target目录执行cargo test --locked --offline，通过后独立caller分别运行。原首段检查点源码未改，本次未重复其运行，把原签收结果保留为基线。

配置串行与同步输出均20/5和[1,3,5,7]，threaded空输入成功；非法配置、配置总项超限、非法码、默认构建的--threaded请求均实际退出2且无成功报告。cargo fmt --check和caller格式检查通过，两种feature配置的cargo doc均成功。所有命令使用已有Rust/Cargo1.89.0及离线解析，没有安装依赖或联网拉包。

7种编译拒绝另核实际诊断：单位E0308、冲突借用E0502、move后使用E0382、配置私有字段E0451、Receiver clone E0599、线程借用逃逸E0597、默认feature缺模块E0432；不以任意编译失败冒充目标行为。

主包默认与threaded配置打包通过；最终实际归档解包后，两种feature配置的测试/运行均通过，包文件集合如下（不含caller、首课检查点与nostd共源检查器，仍从课程库取伴随材料）：

```text
Cargo.lock
Cargo.toml
Cargo.toml.orig
README.md
examples/fixed.rs
ffi/caller.c
ffi/wwl_measurement.h
fixtures/fixed.txt
fixtures/invalid.conf
fixtures/invalid.txt
fixtures/task.conf
src/config.rs
src/ffi.rs
src/fixed_core.rs
src/lib.rs
src/main.rs
src/threaded.rs
tests/cli.rs
tests/config.rs
tests/contracts.rs
tests/fixed.rs
tests/threaded.rs
```

本地包未发布；缺独立发布许可/站点元数据仍有Cargo warning。safe Rust、线程join与flush不等于业务回滚、设备实时或协议正确。

本次接续完成配置/features及有限单序列的同步任务流、资源上限与关闭；原首段源码与学习检查点保留。高级批次现已增加共源fixed核、native no_std编译检查及窄C ABI实际调用。异步适配、C++调用方与真实嵌入式运行尚缺，#243仍未全阶段完成。实际设备时间戳、实时deadline、采样误差、控制闭环、Obsidian显示及真人学习效果均未验证。

## 高级接续：固定核与 C 调用

fixed feature增加src/fixed_core.rs与examples/fixed.rs，用已有调用方固定数组，不使用std/alloc、无堆分配，保持同一前值；ffi feature包含fixed，增加src/ffi.rs、ffi/wwl_measurement.h与ffi/caller.c。主package仍使用std，静态库也包含std，不能把它称为裸机固件。

```sh
cargo fmt --check
cargo test --locked --offline --all-features
cargo run --locked --offline --example fixed --features fixed
cargo check --manifest-path nostd/Cargo.toml --locked --offline
cargo build --locked --offline --features ffi
cc -std=c11 -Wall -Wextra -Werror ffi/caller.c target/debug/libwwl_measurement.a -liconv -o target/c-caller
./target/c-caller
```

C/Rust须使用同一native target/兼容ABI。此链接命令验证于aarch64 macOS、Apple clang21；-liconv是本机系统库，其他平台需另查native-static-libs。WwlResult为三个u32，Rust/C实际核对大小12、字段偏移0/4/8。C调用者拥有初始化且有足够容量的state/input/output，调用期间必须有效、互不重叠、无竞争；核不留指针或释放资源。整数地址检查不能证明分配、寿命与provenance；非法地址不是可恢复测试。

前值与输入均为0..4095，每次最多1024项；所有范围/容量检查在写前完成，错误保持输出/state。C返回status、从1开始的非法样本position及written；成功输出是两倍mV整数。no_std检查器在nostd/src/lib.rs声明no_std，使用相同fixed_core.rs，不另复制算法；该伴随目录不进入主包，课程源码树中可以执行上述check。

本高级批次实际验证：默认24项、all-features40项测试分别从空target运行通过，新增3项固定核/FFI集成及1项FFI compile-fail。后者另外直接rustc核对确为E0133。Rust固定数组example与现有Fir2对照通过；实际C编译/链接/运行核对持续state与分类失败不写。native no_std共源check与格式检查、全部API文档通过。两个原独立caller在本候选重新运行通过。

工具链为Rust/Cargo1.89.0、Apple clang21，native aarch64-apple-darwin。最终本地归档解包后，all-features测试、fixed example及实际C caller再跑通过；nostd伴随目录不随主包，仍需课程源码树。没有将同版复制说成重新跑首课检查点。

本批未安装依赖、runtime或芯片target。no_std check只验证本机core环境编译；测试运行的是相同核的native std调用及C路径，未运行固件。无Future/JoinHandle，无异步取消完成观察；C函数是有限同步调用，不能以drop句柄取消。设备deadline、中断、DMA、内存映射硬件、采样误差、闭环和C++仍未验证。
