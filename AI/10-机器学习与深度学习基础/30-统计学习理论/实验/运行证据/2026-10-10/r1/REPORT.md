# #158 有限分布独立执行回执

执行者只拥有本目录，未改作者源码、主库、Git/GitHub、Logs/CHANGES，未安装组件或派生代理。使用锁定既有 `.venv-issues-111plus`：macOS 27.0.1 arm64、Python 3.14.7。依赖只读清单见 environment.json；计算及 oracle 均只用标准库。

源码SHA256：`3d9b9e02590f6833a8804db213aff5c0ad271183a5c3455ee8aec4363802def8`。
输入SHA256：`263d889a428142306075532f104118cb75f6760f129f9b55d1f86e8310aa3f1e`。
精确快照在 snapshot/，原路径、复制前/后与执行后哈希见 identity.json、execution-direct.json、oracle-execution.json，均未漂移。

## 真实执行及失败层

1. 第一次以 `/usr/bin/time -l` 包裹指定 `python -B learning_theory.py --input inputs.json`。完整 stdout.json 成功产生；观测器因 `sysctl kern.clockrate: Operation not permitted` 返回1（stderr-time.txt）。不能据此声称业务子程序exit1，也不能把观测器当成功。外层耗时0.048814秒；无超时。
2. 直接exec指定业务命令，由父进程 `wait4` 取得真实子程序退出码0、空stderr、墙钟0.045730秒，macOS子进程 ru_maxrss=21,708,800 bytes（20.703125 MiB）。stdout-direct.json 与首次 stdout.json 字节完全一致，SHA256=`c16cf63b78250aadab941ef5e58b66d9d35be9460e0d824f85856c28c3ebca99`。
3. 首次开发完成后的独立oracle在终端实际执行exit0，工具观察0.524367秒，完整表已输出到终端；该次未单独保存stdout/stderr文件和进程rusage，不冒称具备这一层原始证据。随后为解决资源记录缺层作了下一次测量执行。
4. 测量版独立oracle实际exit0、空stderr、墙钟0.637854秒，子进程 ru_maxrss=22,904,832 bytes（21.84375 MiB），user=0.623518秒、system=0.008525秒。命令/输出/资源在 oracle-execution.json、oracle-stdout.json、oracle-stderr.txt。

业务及测量oracle均设60秒child停止机制，远低于5分钟常规上限。OMP、OPENBLAS、MKL、VECLIB、NUMEXPR环境各请求4线程；这不是OS硬线程限制。只取得每个被测子进程的峰值RSS，没有测得A/B聚合峰值，不能据单进程观测认证8GiB聚合硬限制。此目录只有串行短计算实例。

## 独立核对结果

independent_oracle.py 不调用/导入 learning_theory.py。n=4 枚举原四点分布的全部256有序训练集，分别计算经验损失的线性系数，把二次目标驻点与边界作为候选并比较完整目标值求最优；四点测试分布直接加权计算真实风险。n=16、64 另用一阶/二阶矩核lambda=1/2、2，并用精确binomial和直接目标求优覆盖lambda=1/8与全部计数状态。所有2820个字段/性质比较匹配，failed_checks=[]；详细逐项结果在 oracle-results.json。这一计数包括重复表的各样本检查，不代表2820个独立理论证明。

| n | lambda | E bare train loss | E true score risk | E gap |
|---:|---:|---:|---:|---:|
|4|1/8|57/256|21/64|27/256|
|4|1/2|9/32|3/8|3/32|
|4|2|57/128|15/32|3/128|
|16|1/2|45/128|3/8|3/128|
|16|2|237/512|15/32|3/512|
|64|1/2|189/512|3/8|3/512|
|64|2|957/2048|15/32|3/2048|

n4 对应平均正则目标分别557/2048、25/64、121/256，和表中bare empirical risk不同；这些损失也不是0-1分类错误率。n16/64 lambda1/8的较长精确分数保存在完整解析表。

替换敏感度由相邻数据计数与四个测试点直接损失差核对：n4依次1/2、1/4、1/16，均不超过beta；全部n的权重、状态、总质量、gap、超额风险、偏移风险也匹配。增长函数通过枚举全部二进制串，以单调串定义阈值、至多一个1块定义区间，检查完整模式集合及m=1至8的m+1与1+m(m+1)/2。Rademacher n4直接枚举符号，n16/64以even-n中心二项式恒等式核精确值；有限类epsilon、7/100迁移界均匹配。

复制行负向对照对原256样本逐个复制16次并重新直接最小化目标，输出不变；4个独立对象仍给lambda1/2 gap=3/32，严格大于错误按64独立行使用的1/64。部署偏移的n4风险依次43/64、5/8、17/32。模拟检验这些固定接口与失效例，不证明一般VC/PAC、可测性、稳定性或真实数据训练结论。

## 交付边界

本目录是实验恢复区。author158 应逐字复制必要源码、输入、oracle、输出、环境、命令、失败与资源回执到正式lab候选，并在80页给出真实结果入口。该复制、独审与主库/远端交付尚待其角色完成；本报告不以hidden-only目录替代正式交付。Obsidian、同步、真人理解与一般定理证明没有由本实验认证。
