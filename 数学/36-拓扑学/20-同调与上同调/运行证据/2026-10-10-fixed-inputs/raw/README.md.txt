# #154 独立有限链 / 杯积 / #152 联调执行包

实际固定 CLI、7 项 unittest、独立 oracle 均通过；两幅冻结 SVG 最终经 macOS Quick Look 离线渲染并逐图查看，中文与数学 glyph 完整。有限证据不认证一般奇异/胞腔比较、分类、同伦不变、UCT 或杯积定理；独立理论 reviewer 为 /root/review177178（review154/）。

`source-snapshot.json` 绑定作者 freeze-r1 的 14 文件，复制及执行后 SHA 全一致。只读并运行本人 snapshot，写入仅本包；未改 author/main/Git/GH/Logs，未安装、改系统字体或服务。源码没有要求库外输出 guard，固定 CLI 的不存在绝对输出目录位于本包。

- homology_lab.py：`5ec65f5d876f713ef7fb4823096f748040176c3e04c35a897304b26805c52879`。
- test_homology_lab.py：`4c59d3ea9364f5d8e03f84c21fbe4b425f8df587f51aff31a2d3a403dd3d97b2`。
- dependency152/integer_smith.py：`71d9ef1efafcf162d46599462e4740ab3ff8ec48ce64058d93df8ec4fe8ee397`；来自 #152 已执行 snapshot，与作者 r1/r3 完全同字节。没有重造第二份 Smith 算法。

## 真实结果和证据

| Job / raw 入口 | exit | wall 秒 | 观察 |
|---|---:|---:|---|
| logs/unit-tests.stderr | 0 | 0.0897 | 7 tests OK；unittest 的正常详细输出在 stderr |
| fixed-output/report.json / logs/fixed-cli.json | 0 | 0.0485 | 固定七模型报告 |
| logs/independent-oracle.stdout | 0 | 0.1451 | 完整实际变换、子式、链与杯积 trace |
| logs/svg-render.stdout | 0 | 0.1944 | CairoSVG 默认字体缺中文字形，未判显示通过 |
| logs/svg-render-fontconfig.stdout | 0 | 0.2008 | 自有 Fontconfig 尝试仍缺字，未声称修复 |
| logs/native-svg-render.stderr | 255 | 0.0216 | sandbox extension/initialization denied，原错误保留 |
| logs/native-svg-render-approved.stdout | 0 | 0.1922 | 显式 require_escalated 经自动审批，Quick Look PNG 完成 |

各 `.json` 保存实际命令、cwd、限时、环境请求、退出码、stdout/stderr SHA、wall 与直接 child ru_maxrss；wrapper 自身传播 child 非零和 timeout。全部在 60 秒预跑限时内完成，无需把相同输入再跑 5 分钟。系统 Python 3.14.7/macOS 27.0.1 arm64；CairoSVG 2.9.1 使用已安装 .venv，不安装依赖。env 各请求≤4线程，不是 OS 硬限制。数值 oracle child ru_maxrss 26,099,712 bytes；最大直接 child 观测为 Quick Look 92,848,128 bytes，未覆盖 XPC renderer helper、A槽或全系统 aggregate RSS/线程计数，不能据此宣称 8GiB 硬限制已测。

独立预期由 `prepare_expectations.py` 在导入被测 API 前生成 `expected-before-output.json`：三角形 ∂1 由各有向边“终点−起点”独立构造，∂2 由三个有序面符号生成；其余指定最小胞腔数据与群期望明确列出。独立 rank 由所有阶子式的 gcd 非零判定；候选自己的 fixed_report/expected 没有作为独立 oracle。

独立检查给出以下结果，42 组整数同调/上同调的 U/D/V、K/C、原链代表和子式数据均在 raw：

| 模型 | 整数 H0,H1,H2 | 整数 H⁰,H¹,H² | χ |
|---|---|---|---:|
| 三角形仅边 | Z,Z,0 | Z,Z,0 | 0 |
| 三角形填面 | Z,0,0 | Z,0,0 | 1 |
| S1 | Z,Z,0 | Z,Z,0 | 0 |
| T2 最小 / 两三角形 | Z,Z²,Z | Z,Z²,Z | 0 |
| RP2 | Z,Z/2,0 | Z,0,Z/2 | 1 |
| W=S1∨S1∨S2 | Z,Z²,Z | Z,Z²,Z | 0 |

每模型显式核 ∂1∂2=0，转置余链核 δ1δ0=0，并复算 Q-Betti 与 Euler。RP2 的 F2 边界是0、Betti=[1,1,1]；整数 H1 与整数 H² 的 Z/2，以及 F2 系数群，是不同 degree/coefficient 对象，未相互替换。

#152 联调 A=(2,1), B=(3,−6)ᵀ：实际 K=(1,−2)ᵀ、C=[3]，H=Z/3；原代表 (1,−2)ᵀ 的1、2倍不属于原 im B，3倍属于。用自有伴随逆解原 B 的整数格成员，独立核代表最小阶，不借用候选 Smith helper 作 oracle。

杯积 oracle 独立按 t1=[00,10,11] 和 t2=[00,01,11] 的前/后边分别乘积，再评价 t1−t2。625 对 cocycles 保存两个面各自值及实际结果；基上 xy=1,yx=−1,xx=yy=0，反定向翻号，指定 (2x−y)(x+3y)=7 由作者 test 实跑。W 没有源码 cup API；补充的625个零张量配对明确使用课程提供的 H¹ 限制到 S² 为零、H² 限制为恒等的特定数据，不能由相同加法链矩阵推出杯积。关于所有类与自然性的一般证明仍由理论 reviewer 独核。

7 个额外实际拒绝包括 ∂²非零、错误空 shape、Smith AB非零/链尺寸、非cocycle/float/错误orientation。全空有限链[0,0,0]是合法输入、Betti全0，未错误要求拒绝合法空 shape。重复 output-dir 的 CLI 真实 exit1，完整 traceback 在 logs/reused-output.stderr；既有 report.json 原字节与 SHA不变。两个具体覆盖终点也独立核 circle=3、torus=[0,1]，均不闭合。

## 图像实际查看

`rendered/*.svg.png` 为未改源 SVG 的 Quick Look 最终图。三角形 v0→v1、v1→v2、v0→v2 的箭头与 e01+e12−e02 相符；左空/右填面及 H1/χ 标签完整。环面 a→、b↑、c↗，00/10/01/11、t1/t2、前后边及 xy/yx 符号完整，未见中文方框或裁切。两指向 v2/11 的箭头头部相邻重叠，但方向仍可读。Quick Look 缩略图留白属于输出画布，不把它当 Obsidian 页面布局证据。

Cairo 原 PNG 与 Fontconfig 尝试 PNG 均保留，中文和部分 ℤ/箭头缺字确实存在；Fontconfig 匹配到 Arial Unicode 不等于 Cairo 实际渲染已修复。首次 Quick Look sandbox错误保留，后次显式审批成功而非绕开保护。未改源码解决图像；未做 Obsidian/真人核验。

## 在本人新空目录复现

本包证据只读，所有重跑必须在本人**新空目录**。复制 snapshot/、dependency152/、oracle_core.py、verify_protocol.py、prepare_expectations.py、execute_oracle.py、run_job.py；建立 home/ tmp/ state/ logs/ rendered/。在新目录执行：

```sh
python3 -B prepare_expectations.py > logs/prepare-expectations.stdout
python3 -B run_job.py unit-tests 60 snapshot/数学/36-拓扑学/20-同调与上同调 python3 -B -m unittest -v test_homology_lab.py
python3 -B run_job.py fixed-cli 60 snapshot/数学/36-拓扑学/20-同调与上同调 python3 -B homology_lab.py --output-dir "$PWD/fixed-output"
python3 -B run_job.py independent-oracle 60 . python3 -B execute_oracle.py
```

每 job 后核新 logs/name.json 的 status=completed、exit_code=0；CLI/oracle stderr 应空，unittest stderr 应显示 OK而非把详细输出当异常。固定 CLI 输出目录必须不存在。wrapper 拒绝覆写同名日志。若需离线图，在新目录复制 render_svg*.py，并提供已安装 CairoSVG；本机最终 Quick Look 可用 qlmanage -t -s 1800 -o 新目录/rendered 两个复制SVG，sandbox需显式正常审批。复现 Fontconfig尝试时复制fontconfig.xml并将cachedir改成新目录/tmp；不要重用本原路径缓存。任何新图和日志均不回写冻结包。
