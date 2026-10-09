# #209 PDE / 复分析代表包独立执行

本轮两份冻结原源码与额外独立有限复算已完成：三命令退出0，三份stderr为空，没有运行缺陷或缺依赖。数学正文/一般论证由review209pdecomplex独核；这里不认定整个#209完成，issue继续active。

## 固定输入与隔离

`snapshot/candidate/`保存FREEZE.sha256列出的11个候选文件，两stdlib源码保持原始字节未改；HANDOFF、AGENTS、CANDIDATE.diff、FREEZE.sha256一同复制。实际候选材料名为CANDIDATE.diff/FREEZE.sha256；首次尝试读取不存在的CANDIDATE.md/FREEZE.json只发生文件发现错误，随后按真实材料核对，没有执行或改写历史recipe。`source-manifest.json`逐文件绑定，11文件规范manifest aggregate SHA256为 `ec1e11cb6d3d4be7bdf7d2d0fc38cf592950ffef4acedf79c9cc339aaa7e7712`。`source-recheck.json`收尾确认全部11文件与作者候选仍相同，没有用新SHA冒签旧正文。

- pde_regularities.py：`50edb7835a4248552372f6663880e3c625c38542e0d1979e98965ea57307c56f`
- complex_chart_checks.py：`b50ebbd2256ea3ed3a487d984b03ddb6ec7542cc1c649d2f958234d9491da2aa`

静态读取确认两个源码只用math/cmath/json标准库、有限固定循环、JSON stdout，没有import时执行或网络/服务/文件写操作，也没有CLI输出目录guard。因此直接在自己的新完整snapshot布局执行，不需要transient/tmp绕guard或改算法。作者、主库、174冻结包与Git/GH状态均未改；未派生代理。

## 真实运行

`fixed-runs.json`记录Python3.14.7、平台、真实argv/cwd、开始时刻、时长、退出码、隔离HOME/TMPDIR和4线程环境请求。单进程串行两个job，subprocess timeout60秒；实际PDE约0.019秒、complex约0.017秒。无编译、安装、外部数据、随机性或依赖准备。原输出在 `logs/pde.stdout`、`logs/complex.stdout`，对应stderr为空。

`executor_oracle.py`不import候选或调用被测main/expected/run；先从题设独立构造Fractions/闭式/单位根期待并写 `expected-before-output.json`，然后才读取原stdout比较。其命令/环境/退出码见 `executor-run.json`；实际约0.000612秒，原输出为 `logs/executor-oracle.stdout`，stderr为空。

固定children的resource.ru_maxrss观察15,695,872 bytes，oracle自进程17,743,872 bytes，macOS单位。两者为不同执行命令的有限RSS观察，不是合计进程树峰值、硬内存限制或实际OS线程数。固定job设置4线程环境，oracle继承环境中相应变量可为null；均只有stdlib，没有线程池或numeric library，不混写这两个环境。

## PDE 有限结果

- 独立从通量跳跃求RH速度、从 `[q]-s[eta]` 求平方熵产生。2/-2的speed0、RH残差0、熵产生-16/3；反向-2/2仍满足RH但熵产生+16/3。另有3/1与1/3的-2/3和+2/3。这些有限反例不证明全部凸熵或唯一性。
- 用指数商形式而非候选tanh调用独立重算xi=-.1/0/.1的U与U'；中心U0、U'=-20、epsilon U'=-2、乘积项-2，且反对称/偶对称样值一致。
- 材料a=1,2的斜率1,.5、通量1匹配。角点alpha=2/3的Laplace系数零在浮点容差内；独立积分幂次2alpha-1与2alpha-3给H1径向因子、三截断H2径向积分严格增大。源码输出不含角积分与导数系数，未标作完整范数。
- 额外保留Hessian Frobenius系数 `2alpha²(alpha-1)²=8/81`，三个(radius,theta)点通过xx/xy/yy平方和核对；按 Hessian Frobenius 约定，完整扇形环带二阶半范数的平方需将径向积分另乘角度3pi/2和8/81；半范数本身是该值的平方根。有限采样不认证H0¹迹/弱式或一般不可积证明。
- Fourier n4/kappa1振幅与归一平方能量匹配；8节点最高频用独立标量放大因子1-4r重算r=.4/.6的-.6/-1.4，二步振幅.36/1.96、均方.1296/3.8416。
- c2反应显式采样2、2.5、4、10与T*=.5匹配。源码/主文实际采用周期模型，没有Neumann数值接口。oracle另用兼容零Neumann的初始函数2+cos(pi*x)在[0,1]做64点初始均值2、平方均值4.5、方差.5及端点导数有限复算，记录1/m0=.5的算术上界；没有运行Neumann演化或认证非均匀爆破时间。该补例与实际源码执行分开。

## 复分析有限结果

三角映射(1+i,2-i)到(1+i,2+i)，逆恢复原输入。CP1固定z1+i的w=.5-.5i、Jacobian=.5i、切系数i、余切系数-2i，两图配对均2，全部原JSON匹配。

Hartogs参数r=.5、epsilon=.25、rho=.7：(.4,.2)在单位双圆盘内，却不在原Hartogs图形H；积分圆周半径.7全部落原环带。独立单位根均值推导保留k为N倍数的项，得到N>2时理想离散值 `(5/8+1/25)/(1-(2/7)^N)`，真实填入值133/200=.665，理想误差 `(133/200)*(2/7)^N/(1-(2/7)^N)`。

| N | 原脚本computed | 独立理论误差 | 原值到理想离散值距离 |
| --- | --- | --- | --- |
|16|0.6650000013113933 - 7.309138110651834e-18 i|1.3113932277103635e-9|7.309138110651834e-18|
|32|0.665 + 1.5496013726045042e-18 i|2.5860935201531345e-18|1.5496013726045042e-18|

使用1e-14浮点容差，32点理论误差低于双精度舍入量级，不要求观测误差按理论比率严格缩小。期待中的完整精确Fraction保留在expected文件，原输出误差字段也独立核对。

CP1向量场分类与环面拓扑没有候选可运行接口：oracle补做4组(a,b,c)、3个非零z的 `-w²h(1/w)=-(aw²+bw+c)`有限系数一致及w0值-c；环面tau=i的5个格点平移核对代表点、平移导数1及dz不变。明确这是独立有限坐标算术，不能冒充执行不存在的源码接口，更不代替全局分类、Hausdorff/第二可数或一般Hartogs证明。

## 补充证据标签勘误

独立审阅发现 `expected-before-output.json` 及原执行 `executor_oracle.py` 的字段 `full_H2_seminorm_on_sector_annulus` 标签漏写平方。原数值实际为 `∫|D²w|_F² dx`，对应 Hessian Frobenius 约定下的二阶半范数平方，其中混合导数按 `w_xx²+2w_xy²+w_yy²` 计；它们不是半范数本身。半范数须再取平方根。字段的正确语义名应为 `squared_H2_seminorm_on_sector_annulus`，本勘误只澄清原标签，不改原执行脚本或原 JSON 字节，不冒称已运行新版字段。

独立勘误文件为 `ERRATUM-H2-squared.md`，前后 README 与差异身份保存在 `ERRATUM-receipt.json`、`README-before-H2-erratum.md`、`README-H2-erratum.diff`。原两份候选 stdout、独立 oracle 原输出、expectation、driver 与 source inputs 全部保留；原 `artifact-manifest.json` 继续绑定勘误前包，当前说明增量另由ERRATUM回执绑定。没有重跑或修改候选，一般不可积与H0¹证明仍归数学独审。

## 复建与证据边界

原证据包冻结只读。每次重跑先在自己拥有的新空目录复制 `snapshot/`、`run_fixed.py`、`executor_oracle.py`，创建 `home/`、`tmp/`、`logs/` 子目录，然后只在新目录执行：

```sh
python3 -B run_fixed.py
python3 -B executor_oracle.py > logs/executor-oracle.stdout 2> logs/executor-oracle.stderr
```

驱动和oracle以自身位置解析snapshot与日志，无hidden候选runtime依赖；不从冻结原包运行上述写日志命令。完整脚本/报告/原输出字节SHA在artifact-manifest。独立oracle固定有限循环，可在相同60秒外层限制下复建，运行不会回写snapshot。

本包未跑图生成、Obsidian显示/跳转/同步、外部数值库、真实PDE时间演化、设备或真人学习。有限计算仅复核公式/示例和数值实现；generalproof由数学独审负责。本代表包通过不代表整个#209课程或高级分支完成。
