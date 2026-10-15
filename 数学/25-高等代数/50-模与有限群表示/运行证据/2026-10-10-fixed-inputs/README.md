# 整数 Smith 与表示：固定输入运行证据

2026-10-10，独立执行者在自己的 r1 冻结副本运行固定课程 CLI、修正后的整数 oracle 和表示补充计算，三项退出码均为0、stderr均为空。环境为 Python 3.14.7、macOS 27.0.1 arm64。运行输出及首次失败完整保留，详见 [原始执行报告](original/README.md.txt)。

固定 CLI 实算 S3 的36组乘法、共同分块、特征标及3个精确 Fourier 向量；独立整数核查覆盖7个固定输入、625个二阶矩阵、30个固定seed=152的三阶矩阵、5个同调案例及CLI的3个同调、19个拒绝路径。有限实算没有替代一般 PID／Maschke／Schur／特征标的证明。

- [固定 CLI 命令、环境与退出码](original/logs/fixed-cli.json)，[完整输出](original/logs/fixed-cli.stdout)。
- [首次 oracle 退出1的记录](original/logs/independent-oracle.json)，[原错误输出](original/logs/independent-oracle.stderr)。失败来自独立执行者读取 `R,S` 元组赋值的 AST 适配；候选源码未改。
- [修正版 oracle 退出0的记录](original/logs/independent-oracle-r1.json)，[完整子式／坐标／代表阶输出](original/logs/independent-oracle-r1.stdout)，[适配修正差异](original/harness-ast-fix.diff)。
- [独立表示补充记录](original/logs/representation-supplement.json)，[完整输出](original/logs/representation-supplement.stdout)。

`original/` 中44份文件与原执行包逐字一致，共3,810,235 bytes；只排除缓存和空临时环境目录。历史 Markdown 改用 `.md.txt` 存放，正文没有改字。[copy-map.json](copy-map.json) 给出源路径、复制路径、长度和 SHA256；原 r1 snapshot、初次失败 driver、修正版 driver、固定输入、命令环境和 raw 输出都在其中。

## r1 的执行输入与 r3 的正文

实际运行身份见 [原冻结清单](original/freeze-r1.json) 和 [副本身份](original/source-snapshot.json)。课程两个源码直到 r3 均为同字节：integer_smith.py SHA256 `71d9ef1efafcf162d46599462e4740ab3ff8ec48ce64058d93df8ec4fe8ee397`，examples.py SHA256 `2ccb0251b65c88abae9414d1f2e30eebbdf125963ebb80458f4660f379977b7f`；计算证据属于相同源码的复用。

r2/r3 的新增正文分别收紧 homology 守卫范围、补消费页的 Fourier 归一化与图级不变论证归属。这些变化接受正文独立核查，没有重新执行整个 r3；它们没有替换本包的 r1 snapshot。Obsidian显示和真人迁移理解仍未验证。

## 在新目录复现

本目录保存历史证据。`python3 -B restore_copy.py /绝对路径/新的历史副本` 只按映射恢复原文件名和旧布局，**也会带回历史 logs**，不执行实验。若要重跑，再创建一个完全不同的新空工作目录，按下例只复制 snapshot 和6个driver，完全不复制 logs。两个参数分别换成刚恢复的历史副本和新的工作目录：

```sh
python3 -B - /绝对路径/历史副本 /绝对路径/新工作目录 <<'PY'
from pathlib import Path
import shutil, sys
src, dst = (Path(x).resolve() for x in sys.argv[1:])
if dst.exists():
    raise SystemExit("工作目录必须尚不存在")
dst.mkdir(parents=True)
shutil.copytree(src / "snapshot", dst / "snapshot")
for name in ("oracle_core.py", "verify_protocol.py", "execute_oracle.py",
             "representation_supplement.py", "run_job.py", "execute_oracle-first-executed.py"):
    shutil.copy2(src / name, dst / name)
for name in ("home", "tmp", "state", "logs"):
    (dst / name).mkdir()
PY
```

进入新工作目录，依次运行以下三个命令；每条完成后先按下一段核其 JSON 和 stderr，成功才运行下一条。`fixed-cli` 的 job 名必须保留，因为后两项硬编码读取 `logs/fixed-cli.stdout`；仅改 job 名会读错或误用历史输出。

```sh
python3 -B run_job.py fixed-cli 60 snapshot/数学/25-高等代数/50-模与有限群表示/code python3 -B examples.py
python3 -B run_job.py independent-oracle-r1 60 . python3 -B execute_oracle.py
python3 -B run_job.py representation-supplement 60 . python3 -B representation_supplement.py
```

`run_job.py` 自身的退出码不代表 child 成功。每条运行后以它的 job 名执行下面检查；示例是第一条，第二、三条分别改成 `independent-oracle-r1`、`representation-supplement`。出现断言失败即停止，保留新输出，不继续引用旧结果。

```sh
python3 -B - fixed-cli <<'PY'
from pathlib import Path
import json, sys
job = sys.argv[1]
rec = json.loads((Path("logs") / (job + ".json")).read_text())
assert rec["status"] == "completed" and rec["exit_code"] == 0
assert (Path("logs") / (job + ".stderr")).read_bytes() == b""
print(job + " child completed with exit 0 and empty stderr")
PY
```

原失败复现如有需要，用保留的 `execute_oracle-first-executed.py` 及不同的失败 job 名，其结果应单独保存；正常成功链仍先生成新的 `fixed-cli.stdout`。本次交付只作字节复制及静态核对，没有运行恢复helper或重跑实验。
