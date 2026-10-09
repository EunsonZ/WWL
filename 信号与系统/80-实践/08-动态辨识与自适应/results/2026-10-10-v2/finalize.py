from pathlib import Path
import json,hashlib
base=Path(__file__).resolve().parent;vault=base.parents[3];target=json.loads((base/'TARGETS_V2.json').read_text());prefix='信号与系统/80-实践/08-动态辨识与自适应/';orig=vault/'.wwl-recovery/2026-10-10-crash/author179180/candidate-v2'
freeze=[]
for x in target:
 if x['path'].startswith(prefix):
  name=x['path'].removeprefix(prefix);expected=x['candidate_sha256'];a=hashlib.sha256((orig/x['path']).read_bytes()).hexdigest();b=hashlib.sha256((base/'snapshot'/name).read_bytes()).hexdigest();assert a==b==expected;freeze.append({'path':x['path'],'snapshot':name,'sha256':expected})
(base/'SOURCE_FREEZE.json').write_text(json.dumps({'TARGETS_V2_sha256':'97858c52b24366c85666f5fb0c0ba96a93742392247128a5c33fe753d4cf0845','files':freeze,'original_and_snapshot_before_after_and_final_match':True},indent=2)+'\n')
r=json.loads((base/'output/results.json').read_text());o=json.loads((base/'independent-oracle.json').read_text());p=json.loads((base/'process-observations.json').read_text())
inputs={'generation':'Parameters and RNG schedules are frozen in source; no external config exists. Standard CLI has only --output.','fixed_seeds':r['fixed_seeds'],'sample_lengths':o['seed_record_lengths'],'CLI_standard_argv':next(x['argv'] for x in p if x['name']=='standard'),'source_sha256':'3365f8a19bf7f46c1881e7d1da77e3abc7850cc838339a2456a4f66d3a4a098d','test_sha256':'da4e3f63592e79e7c6fceee163d9c3b2e952feb2802502b222d03592d20106c6','FIR_splits':r['fir_order_validation']['splits'],'AR_splits':r['AR_splits'],'drift_range':[1,2048],'later_validation_range':[1,1024]}
(base/'INPUTS.json').write_text(json.dumps(inputs,indent=2)+'\n')
rebuild='''# Exact rebuild interface

No installation or network/device input is required. Use the existing locked `.venv-issues-111plus/bin/python`. Copy this run's `snapshot/` and helper Python files into a NEW sibling under `experiments180/`, with copied TARGETS_V2.json. Existing logs open exclusively and output directory creation rejects existing paths. Preserve existing evidence.

In that new sibling, run independent `analytic_expected.py` first, then use its monitor.py with names/timeouts below. The monitor uses the new sibling's base path and original V2 source is checked against TARGETS_V2. Set the output argument to that NEW sibling's absolute `output` path.

```
python -B analytic_expected.py
python -B monitor.py suite-preflight 60 -m unittest -v test_identification_lab.py
python -B monitor.py standard 300 identification_lab.py --output /ABSOLUTE/NEW-SIBLING/output
python -B monitor.py deterministic-probes 60 /ABSOLUTE/NEW-SIBLING/source_probes.py
python -B monitor.py independent-oracle 300 /ABSOLUTE/NEW-SIBLING/independent_oracle.py
python -B monitor.py additional-analytic 60 /ABSOLUTE/NEW-SIBLING/additional_analytic.py
```

The word python above denotes the verified locked interpreter, not an instruction to install or change Python. The actual absolute argv for this run are in process-observations.json. Set MPLCONFIGDIR to the NEW sibling's own writable cache before using render_evidence.py. Actual trajectory and physical-lag charts are rendered by installed Matplotlib. Frozen schematic SVG uses existing system Quick Look, whose exact argv/wait4 evidence are in qlmanage-approved-observation.json; ordinary sandbox thumbnail generation fails and a normal scoped approval is necessary. Do not reuse old output as proof of a new execution or rerun numerics just to repair a font renderer. Source_probes supplies business observations, while independent_oracle imports no business code.
'''
(base/'REBUILD.md').write_text(rebuild)
resource=['| process | exit | elapsed s | peak RSS bytes |','|---|---:|---:|---:|']
for x in p:resource.append(f"| {x['name']} | {x['exit_code']} | {x['wall_seconds']:.6f} | {x['child_max_rss_bytes_Darwin']} |")
report='''# #180 V2 固定实例与独立数值验收

状态：数值 PASS；中文图经正常批准的本机 Quick Look 静态渲染后可读。V2 源码 SHA `3365f8a19bf7f46c1881e7d1da77e3abc7850cc838339a2456a4f66d3a4a098d`，test SHA `da4e3f63592e79e7c6fceee163d9c3b2e952feb2802502b222d03592d20106c6`；TARGETS_V2 SHA `97858c52b24366c85666f5fb0c0ba96a93742392247128a5c33fe753d4cf0845`。五个08实践原目标与快照在运行前、后和最终核对时全部匹配。原候选、主库、Git/GitHub状态没有修改。

先独立记录解析预期和物理索引（analytic-expected.json），再用现有锁定 Python 3.14.7 执行九项测试作为60秒预跑，全部通过；随后标准CLI退出0。CLI固定输入来自冻结源码，无独立JSON配置；INPUTS.json记录全部seed、长度与划分，所有四份CSV及results.json保留原字节。全部过程的真实argv/cwd、独立子进程退出值、stdout/stderr、超时设置、时间和wait4 RSS见process-observations.json及各日志。

独立CSV oracle未导入业务源或源测试。从全部物理记录构造正规目标，用独立Cramer行列式求2/3维解；检查R、b、theta、验证选择、冻结测试MSE、AR一步与自由预测、全测试窗均值/N分母和每个lag0…8。35,783是比较字段/数值项数量，包含完整seed记录，不是35,783个独立测试；最大已记录比较误差2.0463630789890885e-12。物理lag全部定义u[k−ell]与e[k]，AR lag0为u[k]，lag1才是预测器输入；窗口k∈[2304,6400)，每个lag分母4096，截取起点2304+ell。FIR窗口[2048,4096)按同样定义分母2048。

FIR用[3,1024)训练，三种阶数只用[1024,2048)验证选阶；实际选中2阶，最终冻结测试MSE0.002522960847335672。未从最终测试回挑参数。

同一个6400拍物理x/u只改变输出测量噪声，burn[0,256)、train[256,2304)、test[2304,6400)。理想观察拟合(a,b)=(0.5123870597683181,0.24556788393565596)，一步/自由MSE=(0.7635286221197994,1.0048894728839999)；输出测量噪声拟合(a,b)=(0.4070498029226504,0.2640250843545303)，一步/自由MSE=(1.0265260566186252,1.21575872691774)。自由初值各取真实训练末观测y[2303]，之后只用自身模拟历史。

用固定真参数(.5,.25)计算的旧输出×有效误差样本矩是理想−0.0074165885355641226、测量−0.12535609970263223；解析预期分别0和−1/8，有限样本不强迫等于期望。含输入模型的Var(x)=13/12，测量噪声总体aOLS=13/32=0.40625，b=.25；不能错套无输入的2/5。完整两组九lag自相关/输入互相关都保存并独立逐项核对，这些有限诊断不签白噪声或一致性证书。

漂移记录的两种RLS各2047个参数前缀，用λ加权信息目标独立求解；不是复用业务batch或gain公式。全部前缀最大差λ1为2.6645352591003757e-15、λ.98为3.774758283725532e-15，另用直接指数权目标重算最后解及信息逆。LMS2047前缀用平方损失梯度独核，最大差0。最后独立seed180300在最终真实(.8,−.25)系统验证冻结参数，实际结果如下。

| 算法 | 最终h0 | 最终h1 | 后续独立验证MSE |
|---|---:|---:|---:|
| RLS λ=1 | 0.574684875404 | −0.246443555754 | 0.0532143224062 |
| RLS λ=.98 | 0.777749917593 | −0.248852132056 | 0.00290984690526 |
| LMS μ=.02 | 0.777977331599 | −0.249991906033 | 0.00290139361479 |

这里LMS与λ=.98差约8.45e-6，只有一个固定实例，不推广普遍优劣。较差RLS λ1的完整参数轨迹和指标同样保留。

额外独立Fraction核确认：短三行目标λ1解(9/32,−3/32)，λ.5解(31/79,−13/79)，零中心与非零中心每个前缀都与额外实际source observation比较；源observations与独立oracle明确分开。闭环四格κ1 OLS−.25、参考IV.5；κ0 OLS.5。四轴iid LMS μ1.5均值因子−.5但均方因子2.5，逐轴实际函数输出与独立解析比较；不误用时间共享模型。独立核坐标惩罚DᵀR₀D、有限冲激与常值rank、一步/自由运行不同初史反例及三行lag/中心/N夹具，详见两个analytic JSON。

图证据：actual-drift-trajectories.png与actual-AR-nine-lags.png由实际冻结结果和CSV生成，已实际view，横纵单位、物理时间/lag、全部算法/两观察路径/图例可读。原assets/noise-paths.svg第一次Cairo静态渲染出现中文tofu，局部只读现有字体的fontconfig重试仍tofu，两个PNG及原日志保留，不能视为可读图PASS。普通sandbox Quick Look失败exit255，保留Operation not permitted原日志；之后正常require_escalated auto-review批准单一QL读取冻结本机SVG，未安装/改系统配置/持久权限，QL exit0并生成native-preview-approved/noise-paths.svg.png，已实际view：三层噪声路径、中文、公式、IV条件和反馈箭头全部可读。QL方形thumbnail上下留白属本机预览，不是源SVG尺寸改动。Matplotlib默认缓存目录不可写，首次调用自动使用系统允许临时缓存，警告原样保留；REBUILD接口要求显式设owned MPLCONFIGDIR，未改变全局字体或数值环境。

资源观察（Darwin ru_maxrss bytes，线程环境OMP/MKL/OPENBLAS/VECLIB/NUMEXPR各1）：

'''+ '\n'.join(resource)+'''

数值库线程请求不是OS总线程硬cap；RSS为进程观测，不是A+B聚合峰值或4GiB硬限制。无数值超时或模型失败；仪器/字体失败与数值结果分开保留。所有重算与渲染已结束，B槽释放。版本绑定、原结果SHA及可复建接口见SOURCE_FREEZE.json、artifact-hashes.json、REBUILD.md。

本验收限定此有限合成模型和静态渲染，不签现实设备、闭环控制、全LMS步长、一般理论、原生Obsidian或真人理解。作者应按原字节复制正式实验候选并补读者解释，再由独立核查者接受整包；本runner没有启动新课。
'''
(base/'REPORT.md').write_text(report)
(base/'artifact-hashes.json').write_text(json.dumps({str(x.relative_to(base)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(base.rglob('*')) if x.is_file() and x.name!='artifact-hashes.json'},indent=2)+'\n')
print(json.dumps({'status':'PASS','frozen_sources':len(freeze),'report':str(base/'REPORT.md'),'comparisons_not_independent_tests':o['checks_count']}))
