# PDE 与复几何代表分支：2026-10-10 运行回执

本回执对应三篇高级 PDE 课、两篇多复变量/复流形课及两份标准库源码。独立执行者已在 Python 3.14.7、macOS 27.0.1 arm64 上运行两份冻结源码与独立有限 oracle：两源码、oracle 均退出 0，三份 stderr 均为空。这里归档原记录，装配阶段没有重跑。它只支持指定样例的公式与实现核对，不代表一般 PDE 或复几何全覆盖；#209 仍保持开放。Obsidian 显示/跳转/同步及真人理解未验证。

返回 [PDE 代表主线](../../../46-数理方程/30-正则性与非线性演化/00-高级PDE代表主线.md) 或 [多复变量与复流形入口](../../../45-复变函数/30-多复变量与复流形/00-多复变量与复流形入口.md)。完整有限结果说明见[执行报告原字节归档](archive/README.md.txt)，数学/来源审阅见[独立审阅报告原字节归档](review/REPORT.md.txt)。

## 原始结果与适用边界

- [PDE 原 stdout](logs/pde.stdout)：固定 Burgers 熵方向与行波、材料通量、角点径向积分、热模态、8 节点差分及常数反应样例。[原 stderr](logs/pde.stderr)为空。
- [复分析原 stdout](logs/complex.stdout)：三角映射与逆、CP¹ 两图切余切配对、Hartogs 数值积分。[原 stderr](logs/complex.stderr)为空。
- [独立 oracle 原 stdout](logs/executor-oracle.stdout)与[原 stderr](logs/executor-oracle.stderr)：从独立闭式、Fraction/单位根关系、坐标算术核对原输出；另有 Hessian、Neumann 初始量、向量场与环面有限算术。这些补充算术不是原源码没有提供的数值演化接口，也不证明拓扑或全称定理。

**上述 oracle 输出、[原期待](expected-before-output.json)与[原 oracle driver](executor_oracle.py)必须共同读取[H² 平方勘误](ERRATUM-H2-squared.md)。** 原 `full_H2_seminorm_on_sector_annulus` 字段实际为 $\int|D^2w|_F^2\,dx$，即 Hessian Frobenius 约定下的二阶半范数平方；混合导数计两次。半范数本身须取平方根。原标签及数值原字节保留，没有冒称修正字段已经运行。勘误身份见[执行者勘误回执](ERRATUM-receipt.json)和[独立勘误审阅回执](review/ERRATUM-REVIEW-RECEIPT.json)。

运行命令、真实 cwd、解释器、环境、时长、退出码分别在[两源码运行记录](fixed-runs.json)与[oracle 运行记录](executor-run.json)。四线程环境变量是请求值；两份 RSS 是各自命令的有限观察，不能相加宣称进程树峰值或硬限额。没有安装依赖、网络服务、外部数值库或 PDE 时间演化。Hartogs N=32 已到浮点舍入区，不能要求观测误差按理论比例严格缩小。

## 原字节与来源

`snapshot/candidate/`保存运行时冻结的 11 文件；两 `.py` 原名保留，其余九份 Markdown 以 `.md.txt` 保存原字节。这些历史 Markdown 的 vault 根 wiki / 相对链接依赖原库上下文，归档不是独立读者页面，不能把其中链接失效解读为正文迁移完成。`snapshot/FREEZE.sha256`、[原 source manifest](source-manifest.json)、[原收尾复查](source-recheck.json)绑定原 11 文件（读取归档 Markdown 时须在原路径后加 `.txt`）。两源码 SHA-256：

- PDE：`50edb7835a4248552372f6663880e3c625c38542e0d1979e98965ea57307c56f`
- complex：`b50ebbd2256ea3ed3a487d984b03ddb6ec7542cc1c649d2f958234d9491da2aa`

[原 artifact manifest](artifact-manifest.json)仍绑定勘误前包：其中 `README.md` 对应这里的[勘误前报告归档](archive/README-before-H2-erratum.md.txt)，当前执行者报告对应 `archive/README.md.txt`；其新增字节由勘误回执绑定。报告、回执中的原恢复目录/绝对 cwd 是历史出处，不要求该目录仍在线。所有原路径到归档目标映射与 SHA 在本目录的 [COPY-MAP.json](COPY-MAP.json)。[源审回执](review/SOURCE-RECEIPT.json)与[执行审阅回执](review/EXECUTION-RECEIPT.json)保留历史签收身份。

已有独立源审直接核过以下来源；本装配只复用已签收阅读结果，没有下载或重读 PDF：

| 来源与署名 | 已核阅读定位与边界 |
| --- | --- |
| [John K. Hunter，PDE 第4章](https://www.math.ucdavis.edu/~hunter/pdes/ch4.pdf) | §4.11 / Theorem 4.27，印刷 pp.112–113 差分商；§4.12 / Theorem 4.30，p.115 边界条件。原文 C¹ 结论与正文自行推导的局部 W¹∞ 条件分开。 |
| [John K. Hunter，PDE 第5章](https://www.math.ucdavis.edu/~hunter/pdes/ch5.pdf) | §5.4–5.5，Definition 5.48 / Theorem 5.49；全空间框架与正文周期 C 模型分开。 |
| [Jiří Lebl，Tasty Bits of Several Complex Variables](https://www.jirka.org/scv/scv.pdf) | v4.4，2026-05-31；§4.3 Theorem 4.3.1，印刷 p.135，核维数/相对紧/连通条件。一般紧洞定理是外部输入。 |
| [MIT 18.117 lec07](https://ocw.mit.edu/courses/18-117-topics-in-several-complex-variables-spring-2005/989bea2ba42545febc2830a2b5f59cf2_18117_lec07.pdf) | pp.1–2 全纯逆函数与流形公理。Victor Guillemin 讲授，Jonathan Campbell 整理，按 PDF 主题定位。 |
| [S. N. Kružkov 1970 官方目录](https://www.mathnet.ru/php/archive.phtml?jrnid=sm&option_lang=eng&paperid=3372&wshow=paper)；[大学保存的 IOP 原论文副本](https://www.ucg.ac.me/skladiste/blog_2503/objava_7962/fajlovi/kruzhkov_first_order_quasilinear_equations_in_several_independent_variables.pdf) | 原论文 *First order quasilinear equations in several independent variables*。副本 3,286,862 bytes，SHA `b9179100ca857401fa081816b108f9e734fa4fd49c59b01977f42f4be515a316`；含一页下载封面，PDF 第5/8/14/15/22/24页对应印刷220/223/229/230/237/239。§4 p230 与§5第4条 p239明确自治 flux C¹ 条件，详见[原文补签归档](review/SOURCE-ADDENDUM.md.txt)。 |

未带入整套 PDF、缓存、临时目录或虚拟环境；其余来源没有已保存且本装配可核的 PDF SHA，因此不补造哈希。

## 在新的空目录复建

原 driver 的 `BASE` 相对于自身位置，源码只从 `snapshot/candidate` 读取。以下命令从本回执所在目录启动，先复制到 `mktemp` 创建的唯一新空目录；若复制、固定任一 job、schema/日志检查或 oracle 失败，立即停止。原证据包保持只读。`run_fixed.py` 自己退出 0 不保证两个 job 都成功，因此必须先读实际 `fixed-runs.json` 的 `runs` 数组、核全两个预期 job 和退出码，再继续 oracle。

```sh
set -eu
task209_dir="$(mktemp -d "${TMPDIR:-/tmp}/wwl209-rebuild.XXXXXXXX")"
cp -R snapshot "$task209_dir/snapshot"
cp run_fixed.py executor_oracle.py "$task209_dir/"
mkdir "$task209_dir/home" "$task209_dir/tmp" "$task209_dir/logs"
cd "$task209_dir"
python3 -B run_fixed.py
python3 -B - <<'PY'
from pathlib import Path
import json
r = json.loads(Path('fixed-runs.json').read_text())
jobs = r.get('runs')
if not isinstance(jobs, list) or len(jobs) != 2:
    raise SystemExit('STOP: expected exactly two fixed jobs')
if {j.get('name') for j in jobs} != {'pde', 'complex'}:
    raise SystemExit('STOP: missing or unexpected fixed job')
for j in jobs:
    if type(j.get('exit')) is not int or j['exit'] != 0 or 'error' in j:
        raise SystemExit('STOP: fixed job failure')
    p = Path('logs') / (j['name'] + '.stdout')
    e = Path('logs') / (j['name'] + '.stderr')
    if not p.is_file() or not e.is_file() or e.stat().st_size != 0:
        raise SystemExit('STOP: missing output or nonempty stderr')
    json.loads(p.read_text())
PY
python3 -B executor_oracle.py > logs/executor-oracle.stdout 2> logs/executor-oracle.stderr
python3 -B - <<'PY'
from pathlib import Path
if Path('logs/executor-oracle.stderr').stat().st_size:
    raise SystemExit('STOP: oracle stderr is nonempty')
PY
```

这些是经静态核对的新复建说明，装配阶段未执行。复建会产生新记录与新环境，不能冒充本次归档；oracle 仍保留旧 H² 字段，必须与勘误共同解释。有限运行以外的一般定理、真实 PDE 演化、客户端与真人层仍需独立证据。
