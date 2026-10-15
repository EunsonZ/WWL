# 第四轮实验：推演、反例与独立参照

返回 [[计算机知识/00-开始/全局导航/11-难点导读与研究证据|难点导读]]；历史交付结论见 [[计算机知识/90-资源/维护/导入-com/_meta/07-第四轮深度研究修订报告|第四轮报告]]。本目录仅运行列出的审查过的本地实验，不遍历执行知识库里的其他代码。使用 Python 3.11 以上，不启用 `-O`。组成原理、网络、WAL 与 MVCC 中的模型有明确简化，不能当真实硬件或数据库的实现证明。

## 运行与记录

在 Vault 根目录运行：

```bash
python 计算机知识/_labs/round4/run_all.py
```

每次运行的默认结果写入 `Logs/运行/round4-labs/<运行时间戳>/计算机知识/lab_results.json`，不会覆盖历史输入包报告或先前运行。也可改用独立输出路径：

```bash
python 计算机知识/_labs/round4/run_all.py --output /tmp/round4-local-result.json
python 计算机知识/_labs/round3/run_all.py --output /tmp/round3-local-regression.json
```

编译文件位于临时目录；不安装包、不联网、不调用管理员命令，不访问生产服务。Linux 专有的 FD/epoll 与 Bash 测试需要 Linux/Bash；其他系统不能将运行失败误认为原理不成立。可在本目录分别执行 `python -m unittest -v test_compiler` 等组，以隔离环境依赖。

## Python 的 63 个测试方法在检查什么

| 文件 | 方法数 | 参照与反例 |
|---|---:|---|
| [test_structures_algorithms.py](test_structures_algorithms.py) | 15 | 懒标记与列表差分；可持久化分支版本；回滚；短串枚举；背包/区间调度暴力子集；最大流对全部割；匹配与近似保证。 |
| [test_compiler.py](test_compiler.py) | 8 | 从文法真正构造 SLR 状态与表，遍历短串并与独立识别条件对照；活跃性两种迭代；区间近似；有限类型统一和 occurs-check。 |
| [test_systems.py](test_systems.py) | 18 | 浮点与高精度参照；页表位划分；TLB/ROB 简模；条件变量；文件替换；IPv4 分片、RTO 与分帧；真实本地 FD、管道、epoll 与重定向。 |
| [test_database_crosslayer.py](test_database_crosslayer.py) | 14 | 属性闭包、键、分解；SQLite NULL/外连接；写偏斜与恢复简模；事务发件箱故障点与消费者去重；性能公式及分位数反例。 |
| [test_python.py](test_python.py) | 8 | 描述符优先级（含只有 setter 的反例）、C3、循环导入部分状态、TaskGroup 取消/异常、队列背压和哨兵计数。 |

方法内还包含固定种子的多组输入和小规模枚举。这些内部循环不另行夸大为独立实验数量。关键随机种子写在测试文件中；有限枚举找不到反例，不等于证明任意规模正确。

## C、C++、TypeScript 与 Rust

[C 契约源码](c_contracts.c) 以 C17 编译，开启 `-Wall -Wextra -Werror -pedantic` 和 UndefinedBehaviorSanitizer。它核对二维形状、大小溢出、失败时输出保持和字节序解析。[故意不兼容的二维参数](c_shape_reject.c) 应被编译器拒绝；运行器同时要求非零退出及相关诊断，避免把别的构建错误当成功。不会执行具有未定义行为的反例。

[C++ 源码](cpp_contracts.cpp) 以 C++20 编译，测试模板推导与转发、有效期内的视图、12 个复制失败注入点，以及 50 轮单次 release/acquire 发布。UBSan 不是线程竞争检测器；这 50 次成功不能证明任何自写无锁算法都正确。测试使用默认分配器和明确声明的复制/交换合同，不推广到任意 allocator。

[TypeScript 源码](typescript_contracts.ts) 启用严格模式、可选属性精确语义和索引可能为空检查，包含类型相等断言及 4 个 `@ts-expect-error` 预期拒绝点；随后由 Node 检查普通网络数据校验、状态转换、过时响应屏蔽和 Promise 失败不自动取消其他独立工作。类型拒绝和运行时校验是不同阶段。

[Rust 所有权示例](rust_ownership.rs) 含 3 个标准库测试：[冲突可变借用](rust_borrow_reject.rs) 是预期编译失败样例。**本次机器没有 rustc，二者均未编译或执行**，更没有执行 Tokio 运行时实验。装有编译器的环境可由运行器执行；没有编译器时明确输出 SKIP，不输出伪造成功结果。

## 明确未运行的 PostgreSQL 双会话实验

[postgresql_write_skew.sql](postgresql_write_skew.sql) 给出 PostgreSQL 17 文档对应的手工步骤，使用独立教学 schema。它不是一条可一次性自动跑完的脚本：两会话的 BEGIN、读、写、提交顺序必须按注释交错。只在独立测试数据库使用；本轮没有连接 PostgreSQL，也未将 SQLite 或进程内模型当作该数据库的并发实测。

## 模型与实现的分界

[structures.py](structures.py)、[algorithms.py](algorithms.py)、[compiler_models.py](compiler_models.py)、[system_models.py](system_models.py) 和 [database_models.py](database_models.py) 给出课堂推演的可执行支撑。文件系统 CrashFS 只将显式同步状态复制到稳定映射；它没有模拟真实文件系统可能提前持久的所有写入。WAL 的 redo/undo 示例也不是 PostgreSQL 内部算法或完整 ARIES 实现。

SQLite 发件箱只验证该本地事务内的业务效果与去重记录；外部付款等跨系统效果必须依赖对方的协议。分帧、路由、RTO 以独立模型核对；真实 Linux 实验只涉及临时文件和管道，不等于网络抓包。所有源码都应结合对应正文的前提阅读。
