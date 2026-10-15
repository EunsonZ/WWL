# 共同数组与单位尺度：2026-10-10 独立执行原件

本次独立执行者先按冻结 SHA 复制8件输入，再保存独立期望，运行两个业务程序、两个作者供件核对器和外部独立 oracle，共5个进程全部退出0。实际环境为 Python 3.14.7、macOS 27.0.1 arm64，仅标准库；两个业务固定小输入以60秒上限完整预跑，实际各约0.048/0.024秒，随后核对上限300秒。资源字段记录库线程请求与终止子进程峰值RSS观察，不宣称OS线程硬限制或硬内存上限。完整环境与命令在 [总回执](report.json) 和各 `*-receipt.json`，原始输出与stderr全部保留。

**#214 观察。** 原低/高频数组最大差约1.4142，相位0抽取却同为周期 `[1,0,-1,0]`；独立解析表对各输出的最大浮点差约 $4.22\times10^{-15}$，小于声明容差 $10^{-11}$。因果两点均值的低/高频增益为约0.9238795/0.3826834，且相位分别为−π/8、−3π/8；完整样本不能用增益代替。平方后直接抽取和先滤输入再平方都给 `[1,.25,.25]`，平方后低通再抽取给常量`.5`。独立扩展还核了相位1的相反输出、周期/零延拓的不同首样本，以及一像素位移不能映为整数输出位移而某个标量能量统计仍可相同。这些是有限数组观察，没有训练CNN、证明经验鲁棒性或实现完美重建滤波器组。

**#215 观察。** 精确分数核尺度100、10沿用字面惩罚时预测`10000/10001`、`100/101`；正确变换惩罚均保持`1/2`。独立非对角D/Λ和加权残差的三组对应点给相同预测与目标。二维原例核 $D^\top HD=I$ 与 $DD^\top=\operatorname{diag}(1,1/100)$，两种普通梯度的一步分别`(.99,0)`与映回`(.99,.99)`；迁移D=diag(1,1/5)给H_v=diag(1,4)与一步`(.99,.96)`。有限代数和轨迹不证明一般深网标准化改善，不降低实际仪器误差。

两个供件核对器虽然不导入业务实现，仍单列为作者自检；[外部oracle](oracle.py)不导入业务函数、供件verify或作者预期，通过三角恒等式、精确Fraction二次型与中心差分梯度独立计算。它的[运行前期望](expectations-before-run.json)、[实际结果](independent-results.json)、[执行回执](independent-receipt.json)和 [原stdout](independent.stdout)分别保存。业务原输出是 [aliasing.stdout](aliasing.stdout) 与 [scaling.stdout](scaling.stdout)。有限周期测试不能代替正文对全部整数的恒等式证明；非作者理论审阅另交付。

## 原件身份与路径

[artifact-sha256.json](artifact-sha256.json) 为执行者原清单，[copy-map.json](copy-map.json) 给原路径到本正式结果路径的逐字节映射；35件清单成员及原清单共36件内容保持原字节。原Markdown快照/说明统一追加`.txt`后缀以标明历史上下文，路径映射不改变内容。snapshot/README.md.txt和SCALING.md.txt是执行时r1说明；正式实验入口后来只增加本实际回执，4py和2输入JSON仍与实际运行快照相同。旧原绝对命令是运行身份记录；下面是新目录中的可移动复建接口，未把接口静态审查写成已再次运行。

## 在新空目录复建

从本结果目录运行以下命令；`mktemp`产生唯一新空目录，复制或任一步骤失败时停止，原结果不会被覆盖。snapshot保持源码/JSON相邻。execute.py依次执行完整五任务并在任何非零退出时停止，oracle依本新目录读取新业务stdout。

```bash
task_tmp="$(mktemp -d)" &&
cp -R snapshot "$task_tmp/snapshot" &&
cp execute.py oracle.py "$task_tmp/" &&
python3 -B "$task_tmp/oracle.py" prepare > "$task_tmp/expectation-preparation.stdout" &&
python3 -B "$task_tmp/execute.py" > "$task_tmp/supervisor.stdout" 2> "$task_tmp/supervisor.stderr" &&
python3 -B - "$task_tmp" <<'PY'
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
labels = {'aliasing', 'scaling', 'verify-aliasing', 'verify-scaling', 'independent'}
assert {f.name.removesuffix('-receipt.json') for f in p.glob('*-receipt.json')} == labels
for label in labels:
    r = json.loads((p / (label + '-receipt.json')).read_text())
    assert r['returncode'] == 0 and not r['timed_out'], label
assert json.loads((p / 'independent-results.json').read_text())['scope'].startswith('Finite')
print('five complete receipts exit 0; inspect original stdout and independent results')
PY
```

复建需要 Python 3.10+，所用程序无第三方库。原监督驱动的RSS字段按macOS单位记录；换平台时需另核资源单位，数值结果不由该资源字段决定。执行新增独立记录，不能把旧JSON改名为新结果。一般来源/语义核查、Obsidian显示、真实设备、同步与真人学习仍分层记录。

返回 [[AI/80-实践/抽取单位与正则尺度/README|抽取接口]] 或 [[AI/80-实践/抽取单位与正则尺度/SCALING|正则尺度接口]]，再沿各自主解释核对条件。
