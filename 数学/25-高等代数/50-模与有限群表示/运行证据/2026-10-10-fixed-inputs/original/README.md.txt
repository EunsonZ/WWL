# #152 独立精确计算实跑包 · r1 源码

执行侧有限检查通过。固定课程 CLI、修正后的独立整数 oracle、表示补充 arithmetic 均 exit 0，stderr 空。首次 oracle 的 AST 适配失败原样保留；它不是候选 Smith 的业务失败。作者一般证明仍由独立领域 reviewer 核对，本包不以有限矩阵数量认证一般 PID 分类、Maschke、Schur 或字符正交定理。

## 字节身份与安全范围

`source-snapshot.json` 绑定作者 `freeze-r1.json` 的 14 个文件，复制时逐 SHA 一致；必要指令 `snapshot/AGENTS.md` 同时保存。候选源码与固定输入仅运行 own snapshot，未 import 活候选、未改 author/main/Git/GH/Logs，未安装依赖、改服务或启动其他数值任务。源码只用标准库，无外部写路径 guard，因此无需 /private/tmp 例外目录。

- integer_smith.py：`71d9ef1efafcf162d46599462e4740ab3ff8ec48ce64058d93df8ec4fe8ee397`。
- 固定输入及 CLI examples.py：`2ccb0251b65c88abae9414d1f2e30eebbdf125963ebb80458f4660f379977b7f`。
- 执行前独立预期 `independent-fixed-input-expectations.json`：`2f7b05dab2a7434acb685776f9b14e722636429623ce2cfdbff154df06780769`。由自有 `oracle_core.py` 产生，不调用候选 expected/run。

`post-run-source-check.json` 记录 14 文件的后核：两源码及其余 11 文件未变；06 正文从 r1 的 `3b92e9…` 变为 `8bea73…`。作者随后提供 r2 的 `freeze-r2-reference.json`；`r2-docdelta-reference.json` 验证两个源码同字节并明确行为 `REUSED_EXACT_SOURCE`。06 仅澄清每次 smith 的输入守卫：homology 核 A/C，没有原 B 元素上限或整体坐标 bit cap；该新文 NOTRUN_DOC_ONLY，理论/doc review 单独处理。该正文新字节未替换本包冻结 snapshot，也未宣称本执行者已审。纯正文 delta 是否接受由作者/独立 reviewer 处理；源码行为只绑定上述两实际 SHA。

## 实际运行与失败保留

| 日志入口 | 限时 | wall 秒 | exit | child ru_maxrss（Darwin bytes） |
|---|---:|---:|---:|---:|
| logs/fixed-cli.stdout | 60 | 0.0480 | 0 | 19,660,800 |
| logs/independent-oracle.stderr（首次） | 60 | 0.2102 | 1 | 28,606,464 |
| logs/independent-oracle-r1.stdout | 60 | 0.2036 | 0 | 37,093,376 |
| logs/representation-supplement.stdout | 60 | 0.0483 | 0 | 18,694,144 |

每个 job 的 `.json` 保存真实命令、相对 cwd、stdout/stderr 字节和 SHA、退出码、限时、Python/platform、线程请求环境、wall/RSS。Python 3.14.7，macOS 27.0.1 arm64。请求 OMP/OpenBLAS/MKL/VecLib/NumExpr 各最多 4 线程；这不是 OS 强制上限。单个 stdlib 子进程顺序运行，无系统线程计数或所有任务 aggregate RSS 观测，不能把 ru_maxrss 当 8GiB 全系统硬限制。各 job 已在 60 秒预跑界限内完成，因此无需相同输入再跑 5 分钟版本。

首次 `execute_oracle.py` 在读取冻结 examples 的 `R,S = ...` AST tuple 赋值时 `ValueError: R`；原执行 driver 在 `execute_oracle-first-executed.py`，原 stderr/exit1 完整保留。只修自有 AST adapter；`harness-ast-fix.diff/.json` 记录前后 SHA；第二次运行使用当前 `execute_oracle.py`，没有更改任何候选源码或隐藏首次失败。

## 独立整数证据

`oracle_core.py` 用排列求行列式（不同于被测 Gaussian/Euclidean reduction），枚举所有 k 阶子式并取 gcd，独立 rank/Smith 不变量由 Δk/Δk−1 得到；`verify_protocol.py` 检查 U、V 行列式 ±1、UBV=D、正整除链、全部子式不变量、候选 kernel/image 基、原输入 x→V⁻¹x 与 Bx→UBx 的整数坐标 trace。空矩阵尺寸显式保存，det(0×0)=1。

实际包括 CLI 的 7 个 Smith 和 3 个同调，额外 7 个指定矩阵、625 个 entries∈{-2,…,2} 的完整 2×2 输入、30 个 seed=152 的 3×3 输入。所有实际 U/D/V、子式 determinants/gcd、坐标 trace 都在 `logs/independent-oracle-r1.stdout`，并非仅 Boolean。

额外代表输入得 diag(6,10)→(2,30)、signed rectangular→(3,3)、rank1→(2)、非平凡坐标例→(2,6)，0×3/3×0/allzero 均无非零不变量。

同调用自有独立 K/C 建立预期，再验证候选 K=V_A 后列、V_A⁻¹B 前行零、B=KC、C 的子式不变量、原链代表 KU_C⁻¹。原始 B 整数格成员用非奇异行子式的伴随逆求系数，检查整数性和全原矩阵回代；不依赖候选 Smith helper。

- A=[2,3,0], B=[−6,4,0]ᵀ：Z/2⊕Z；实际原代表列 (−3,2,0) 与 (0,0,1)，第一列 1 倍不在 im B、2 倍在，第二列前 4 个正倍数不在。自由秩由独立 rank 与坐标变换检查，而非由这 4 点宣称无限证明。
- A=[1,1,0], B=[[4,6],[−4,−6],[2,6]]：Z/2⊕Z/6；实际代表列 (2,−2,1) 与 (1,−1,1)，逐正倍数 1…2、1…6 检查最小阶。
- fullcolumn A：K shape 2×0，C shape 0×2，代表 shape 2×0，H=0。
- 0×3 A 与 B=[2,0,0]ᵀ：Z/2⊕Z²；B 的空列例：Z²。

19 个真实异常记录涵盖 AB≠0、链 shape、ncols False/float/empty string/negative、bool/float entries、ragged rows、9列、entry>10^6、max_ops/max_bits 非法类型/值和各自资源限制。超资源抛 RuntimeError 并不返回 partial form；这不表示算法理论失败。

## 表示与范围

固定 CLI 实际执行 S3 36 对乘法、共同分块、字符 Gram、分解重数与 3 个 Q(ω) Fourier 向量。独立 oracle 读取冻结 AST 的生成矩阵/换基/Fourier literals，使用自有运算复核；另保存所有 6 元素标准表示矩阵和 36 个乘积 witness。

`representation_supplement.py` 无候选 import，以固定点数−1 得标准字符、全六元素内积独立算置换重数(1,0,1)、标准 tensor square 重数(1,1,1)，与实际 CLI 比对。正则表示重数(1,1,2)与维数6是独立补充有限 arithmetic；候选无单独 regular-matrix API。它还读取实际 source 的 F3 Jordan J，独立枚举全部4条射影直线：唯一不变线是 span(e1)，没有不变补空间；这是该有限反例的实算。

## 在新空目录复现

本证据包只读；不要在此直接重跑覆盖 logs。先选 own **新空目录**，复制 `snapshot/`、`oracle_core.py`、`verify_protocol.py`、`execute_oracle.py`、`representation_supplement.py`、`run_job.py`，建立 `home/ tmp/ state/ logs/`。复制后在新目录执行以下命令，所有输入来自复制的 snapshot；不访问隐藏 author runtime。

```sh
python3 -B run_job.py fixed-cli 60 snapshot/数学/25-高等代数/50-模与有限群表示/code python3 -B examples.py
python3 -B run_job.py independent-oracle-r1 60 . python3 -B execute_oracle.py
python3 -B run_job.py representation-supplement 60 . python3 -B representation_supplement.py
```

若要复现历史 harness 失败，应复制 `execute_oracle-first-executed.py` 到同一个新的布局并使用新的 job 名运行；原失败日志也保持只读。driver 会拒绝覆写同名 evidence。

本包尚不证明 Obsidian 渲染、真人理解、一般定理，也不授权整合或关闭 issue。领域 reviewer 的签收在 review152/；本包是其可复核输入。
