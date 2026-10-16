---
type: reference
domain: electronics
stage: 4
aliases: []
sources: []
prerequisites: []
---
# ngspice 47 实际运行证据与复算

本目录是作者 READY 电路的外部执行结果，2026-10-16 在 macOS arm64 取得。
作者原始网表、模型参数不曾为改善结果而调整；Y 测量仅加独立 AC 注流探针。
原始 `command.json`、日志中的 `/private/tmp` 是实际执行来源记录，不是交付依赖。
`verify_runs.py` 与 `check_transient.py` 交付副本仅将 ngspice 路径改成环境变量
`NGSPICE`（缺省 `ngspice`）；路径化后未重跑实验。原始数据/结果/日志均保留。
`ota_model.py`、`author-results.json` 和 `author-transient.csv` 是本轮实跑冻结快照；当时输入接口尚未补后续有限ud/uc与严格8初值检查，数值方程/网表未改变。该快照仅用于复现历史证据，不是第二份现行真源；现行真源为上两级的实践根 `ota_model.py`，测试它应从实践根进入。

## 实际环境和复建

官方稳定版本依据：https://ngspice.sourceforge.io/download.html （47 stable）；
发布日期依据：https://ngspice.sourceforge.io/news.html （2026-08-11）。
实际源码 URL：https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47.tar.gz
源码 SHA256：`894e649651f1838a14095e5a5439e7d3aa63e87ede14d283173fda4fcdef675f`。
实际 binary SHA256：`aad64d99db6966f3a7e3304e3980f8ea295c41bd6b9ebd5ed07d35f927070d6e`。
Mach-O 64-bit arm64，Sparse Direct Linear Solver，仅链接 macOS libSystem/libc++；
详见 actual-version.txt 与 actual-binary-info.txt。GUI/readline/FFTW/KLU/CIDER/OpenMP/OSDI均未启用。
XSPICE保留官方默认：关闭会触发上游 `cktsopt.c:254 OPT_ENH_RSHUNT` 未定义。
其 `seegenerator` 缺 `stdlib.h` 声明，使用编译旗标补标准头，不改源码、不放宽诊断。

下面是可从干净源码复建的命令；实际先用相同 configure 但 CFLAGS 无 `-include stdlib.h`，
失败后增量 `make -j4 CFLAGS='-O2 -arch arm64 -include stdlib.h'` 成功。前一次
`--disable-xspice` 失败及两次诊断在环境原记录，未把编译树纳入本目录。

```sh
curl -fL 'https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47.tar.gz' -o ngspice-47.tar.gz
shasum -a 256 ngspice-47.tar.gz
tar -xzf ngspice-47.tar.gz
mkdir build
cd build
# 以绝对路径替换 /absolute/local-prefix；prefix 必须是局部目录。
CC=/opt/homebrew/opt/llvm/bin/clang CFLAGS='-O2 -arch arm64 -include stdlib.h' LDFLAGS='-arch arm64' ../ngspice-47/configure --prefix=/absolute/local-prefix --without-x --with-readline=no --with-editline=no --with-fftw3=no --disable-cider --disable-klu --disable-openmp --disable-osdi
make -j4
make install
```

实际 Python 3.12.11，numpy 2.5.4，scipy 1.18.1；在独立 uv venv 安装，arm64 import 通过。
可在新局部目录建立 `python3 -m venv .venv`，再用
`.venv/bin/python -m pip install numpy==2.5.4 scipy==1.18.1` 重建 Python 环境。
无需将 binary、Python runtime、源码归档或编译树提交到实践目录。

## 重跑

正式证据目录保持只读。先将本目录完整复制到**全新库外目录**，以下命令只在副本执行；脚本会覆盖自己的比较输出，因此不得直接在正式data中重跑。

在该库外副本设置 `NGSPICE=/absolute/local-prefix/bin/ngspice` 并放入 PATH；每个分析从相应
子目录执行，避免 wrdata 互相覆盖。实际执行使用项目现有 `run_local.py --timeout 300 --`
取得两个 flock 槽之一并将数值线程限定1；每次只运行一条命令。跨项目移植时也需将
OMP_NUM_THREADS、OPENBLAS_NUM_THREADS、MKL_NUM_THREADS、VECLIB_MAXIMUM_THREADS、
NUMEXPR_NUM_THREADS 设为1，并由调用方限制并发。

```sh
# 已处于刚复制的库外证据副本，绝非正式实践data目录。
export NGSPICE=/absolute/local-prefix/bin/ngspice
# 工作点：按需替换 nominal 为其余5个case；每份原始command.json留有真实命令。
(cd nominal-op && "$NGSPICE" -b nominal-op.cir > ngspice.log 2>&1)
(cd nominal-ac && "$NGSPICE" -b nominal-ac.cir > ngspice.log 2>&1)
(cd nominal-tran && "$NGSPICE" -b nominal-tran.cir > ngspice.log 2>&1)
# 以下脚本会重写相应测量/比较输出，外层按项目规则取得数值槽。
python verify_runs.py > verification.log 2>&1
python check_transient.py > transient-comparison.log 2>&1
python direct_kcl.py > direct-kcl.log 2>&1
```

`verify_runs.py` 对全部 OP、AC 作数值比较，并执行 nominal/small_control_cap 各8个节点
AC 注流测量。各 `ymatrix-*` 目录有网表、日志和 response.txt；8列电压组成阻抗矩阵 Z，
Y=inv(Z)，在1kHz抽取 J=Re(Y)、C=Im(Y)/(2πf)，完整状态 A=-inv(C)J 的8根保存在
verification.json。原始刺激源 AC 归零，模型和其余参数保持相同。该测量包含仅靠某一
端口 .pz 可能看不见的模态；它是本电路数值核对，不冒充一般论证独立审阅。
`check_transient.py` 比较名义 ngspice 与作者 Radau 轨迹，并从作者小电容配置生成/运行同初扰网表。

## 观察值和验收容差

全部8份 READY 原网表 exit=0。预设 OP 电压<1uV、支流<1e-10A；实际最大误差
7.32e-11V / 3.82e-15A。按SPICE支流与电阻支流直接重构KCL，最大残差7.59e-18A。
AC预设相对1e-5（零点需绝对容差）；|期望|>1e-8时实际最大相对误差DM8.86e-14/
CM4.11e-11，最大绝对误差分别3.00e-13/9.77e-13。器件区来自作者模型在SPICE Q重算。
Y抽取J误差<8.3e-18S；根最大绝对偏差1.08e-4 s^-1（最快根约6.5e7 s^-1）。
名义最慢根 -19587.402712±j8275.631071 s^-1，全部8根实部负；Cvc20pF有正根
+109720.704434±j332095.514032 s^-1。名义初扰2ms回Q误差<5.79e-12V；
400个作者时间点线性插值比对最大3.39e-7V（不含SPICE第一行以前t=0）。小电容同初扰
52206行，op范围0.101374–3.022186V；只证明此初扰进入大幅非线性运动，未认证渐近吸引子。
完整数值、状态顺序与原始数据见 verification.json 和各目录。真实PDK/工艺/硅/硬件/真人学习结果未验。
