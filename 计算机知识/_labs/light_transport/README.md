---
type: lab
stage: 1
aliases: []
sources:
  - "https://pbr-book.org/4ed/Light_Transport_I_Surface_Reflection/The_Light_Transport_Equation"
  - "https://pbr-book.org/4ed/Monte_Carlo_Integration/Improving_Efficiency"
  - "https://pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory"
prerequisites:
  - "[[计算机知识/62-图形学/09-辐射度量与光传输]]"
---

# 可解析光传输与路径采样实践

读 [[计算机知识/62-图形学/09-辐射度量与光传输|09主解释]]，然后预测这三件事：换PDF后均值应该变吗；固定最多5次反射能否仅靠增spp逼近全路；漏掉面积Jacobian能否用几何同比缩放检出？这里保存实际运行输入和原始数值，截图只是解释出口。

重要性高：本单元的能量、单位、PDF支撑、反弹数和方差结论互相约束，任何一项接错都可能生成“更亮、更平滑”却错误的图。因此使用解析有限目标、独立求积和真实轻量CPU路径共同验；不拿多跑随机数替代证明，不以显示图认证材料或硬件。

## 模型和固定输入

[scene.json](scene.json)是真实输入。规范 [transport_lab.py](transport_lab.py) 与 [test_transport_lab.py](test_transport_lab.py)；[[计算机知识/_labs/light_transport/源码与验证|两完整code-sync镜像]]供逐行阅读。依赖版本在 [requirements.txt](requirements.txt)。本单元没有修改旧renderer，也没有另建通用场景引擎。

- **面元基准**：ρ=.6、同一固定光谱带L₀=2 W·m⁻²·sr⁻¹，constant/cone/visibility三个目标；uniform/cosine/cap三PDF相对dω。visibility实际把方向射到高2m的黑平面，半径2√3m的孔决定V。该孔径是局部面元基准，不在两板场景另加不存在的遮挡。
- **圆盘基准**：R=1m、d=2m、ρ=.6、Lₑ=4，均匀面积取样。第二条路线逐点转换到pω，另留故意漏换元的错误数字；几何同比乘2检尺度不变性。
- **路径场景**：无限底板z−2m/ρF.6、顶板z+2m/ρC.5，内法线±Z。顶板自发光4仅限其内向μ≥.5，反射部分仍是全半球Lambert。外部驱动的方向发光不冒充热平衡黑体。复用08的(3,3)位置数组/整数索引 `[[0,1,2]]`，三角形只是底板观察窗口，路径在无限板上求交，绝不在该三角形边界截断。
- **投影/显示**：现renderer的perspective/samples/interpolate/srgb只读；64²、同相机、中心覆盖。不调用其“.1+.9点乘”光照。单带辐亮度按参考1 W·m⁻²·sr⁻¹和曝光1归一，再x/(1+x)后sRGB，仅为灰度展示。

固定反射路径使用5次余弦方向并保留1/3/5次累计前缀，另以q=.5在每次访问发光面后进行RR继续/终止。ρFρC<q是本教学实现比有限方差条件a²<q更窄的合同，使幸存项逐对不增长。guard超过10000周期就抛错，不返回伪称无偏的截断值。

## 正式实际输出

[results.json](data/results.json)含45组MC汇总、四固定方向/PDF/贡献、圆盘两路线、首条路径五次的几何/联合PDF/β、全部解析目标与环境/输入身份。生成文件全部来自同一最终运行：

| 文件 | shape或用途 |
| --- | --- |
| [benchmark-estimates.npy](data/benchmark-estimates.npy) | float64 (3,3,5,2048)：scenario、sampler、n、独立重复；顺序constant/cone/visibility，uniform/cosine/cap，n=1/4/16/64/256。不同n共享各次重复的样本前缀，不把曲线点之间误叫独立。 |
| [radiance-images.npy](data/radiance-images.npy) | float64 (4,2,64,64)：direct1/through3/through5/rr_full，4/64spp，y/x。**带单位原辐亮度**，不是[0,1]编码。 |
| [observation-mask.npy](data/observation-mask.npy) | bool (64,64)，实际496个中心样本。浮点投影的top-left实际归属保留，不把连续面积512当精确样本数。窗外0是图的掩码。 |
| [disk-samples.npy](data/disk-samples.npy) | float64 (65536,5)：U/V、正确area权重、正确solid-angle权重、故意错误数字。后者量纲不合法，不称辐亮度。 |
| [sampling-mse.png](data/sampling-mse.png) | 读取results里实测MSE/解析Var/n+bias²，不把一次随机波动当定理。 |
| [direct-indirect.png](data/direct-indirect.png) | 从原始radiance-images经过同一显示函数绘制，crop标出，最近邻放大不制造子像素。 |
| [directions-roughness-display.png](data/directions-roughness-display.png) | 固定方向投影、规范GGX公式曲线和显示映射；NDF不是完整GGX材质实现。 |

NPY均用 `np.load(path, allow_pickle=False)`。三幅图作者已实际打开核对标题、轴、裁切、显示顺序和可见内容。没有把三角形观察窗之外清黑解释成物理空间真的没有板。

## 先写预期与失败判据

常Li面元C=1.2：uniform/cosine/cap理论均值1.2/1.2/.9，单样本方差.48/0/.03。球冠在此漏支撑，MSE=.03/n+.09；cone或孔径目标本来只在μ≥.5有贡献，三法都无偏，方差.87/.27/.03。漏V算1.2而非.9；余弦采样除均匀PDF均值1.6而非1.2。这些差别不靠增N消除。

圆盘真值.48，方差.00384；area与转换后solid-angle逐点权重应在10⁻¹²内一致，整体尺度乘2后正确权重不变、错误数字乘4。方差用稳定式 $C^2t^4/[3(1+t)^3]$，避免极小t时二阶矩减均值平方的相消；测试还核R=.01m/d100m保持微小正方差，不用max(0,...)掩盖问题。

两板真值18/7，截断1/3/5次累计期望1.8/2.34/2.502，偏差−30%/−9%/−2.7%。余弦路径各次乘ρ，联合方向PDF必须等各次条件PDF乘积；固定全锥内路径累计(2.4,3.12,3.336)。RR单path方差4104/2009≈2.042807，N条IID均值方差除N；本次31744条RR路径实际最大访问顶板20次、共95486段求交。

随机验收使用解析期望/方差与有限容差：tests里的固定种子32768条RR均值在7个理论标准误内、方差相对误差<15%；这是一个可复核有限回归判据，不宣称随机算法永远不越界。圆盘、PDF、GGX归一等独立求积比较容差10⁻⁸至10⁻¹³按相应量级，代码列实际判据。RR或BRDF输入若违反合同必须拒绝，不能悄悄改PDF/ρ/终止深度凑图。

## 在全新库外目录复算

从库根运行。可用既有兼容环境；下面展示库外新建，不覆盖正式data：

```bash
LAB="$PWD/计算机知识/_labs/light_transport"
RUN=$(mktemp -d /private/tmp/wwl-transport-XXXXXX)
python3 -m venv "$RUN/venv"
"$RUN/venv/bin/python" -m pip install -r "$LAB/requirements.txt"
PY="$RUN/venv/bin/python"
MPLCONFIGDIR="$RUN/mpl" XDG_CACHE_HOME="$RUN/cache" "$PY" -B -m unittest discover -s "$LAB" -p test_transport_lab.py -v
MPLCONFIGDIR="$RUN/mpl" XDG_CACHE_HOME="$RUN/cache" "$PY" -B "$LAB/transport_lab.py" --output "$RUN/output"
```

CLI只有 `--output`，输出目录必须尚不存在，数值计算完成后才创建。场景是固定教学JSON，不是接受任意生产资产/未知schema的导入器；若要改几何、法线、发光域或sampler，须同时重写相应参考目标。标量参数严格拒bool/NaN/inf；数组检查最终实数dtype/shape/有限值及范围，不承诺追回异质Python列表经NumPy转型前的元素原类型。u坐标限(0,1]以避有限数值恰采地平线；PDF理论仍针对连续半球、零测度端点不改变积分。

默认导入主库规范renderer；隔离候选可设置 `WWL_RENDERER_SOURCE=/绝对路径/renderer.py`。正式结果记其SHA256 `a69a5c55330dfc19141187ef446a06cd53296608ac6e46f2f3d7a85697ddf203`，固定提交 `bd7266e0e1d113bb145c5cd765eb8cbbc291b4a6` 的该文件可导出到库外复算，不要求回退当前main。输入scene的SHA也在results中。比较不同机器时可忽略environment字符串，数组/公式合同应逐项比较；PNG字节还可能受字体/绘图库版本影响。

## 本次真实运行和有限结果

实际主库 `.venv/bin/python` 为Python3.14.7、NumPy2.5.3、matplotlib3.11.2，macOS27.0.1 arm64。复用既有依赖，无安装、GPU或远端。正式命令经两个自动槽位runner，线程1、timeout120s：

```bash
WWL_RENDERER_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/计算机知识/62-图形学/renderer.py' MPLCONFIGDIR=/private/tmp/wwl-next-169-transport/mpl XDG_CACHE_HOME=/private/tmp/wwl-next-169-transport/cache /private/tmp/wwl-next-context/run_local.py --timeout 120 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B -m unittest discover -s /private/tmp/wwl-next-169-transport/vault/计算机知识/_labs/light_transport -p test_transport_lab.py -v
WWL_RENDERER_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/计算机知识/62-图形学/renderer.py' MPLCONFIGDIR=/private/tmp/wwl-next-169-transport/mpl XDG_CACHE_HOME=/private/tmp/wwl-next-169-transport/cache /private/tmp/wwl-next-context/run_local.py --timeout 120 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B /private/tmp/wwl-next-169-transport/vault/计算机知识/_labs/light_transport/transport_lab.py --output /private/tmp/wwl-next-169-transport/author-run-final-20261017
```

最终8tests实际.053s PASS；CLI实际约1.01s、exit0，8生成附件已同步正式data。[author-check.txt](data/author-check.txt)留必要结果。先前首run在库外保留；独核建议极小t方差稳定式后，已补测试并完整重建final，不混用旧JSON与新源。首次图形字体缓存较慢，最终缓存已可用；不是物理计算性能测量。

实际n256常Li汇总：uniform均值1.19999827、MSE.00183220；cosine均值1.2、MSE仅浮点残差约3.3×10⁻²⁹；cap均值.90030044、MSE.08993202。64spp窗口均值：direct1=1.79546371、through3=2.33419355、through5=2.49653377、RR=2.57662087；每项分别与自己的解析目标比。圆盘均值.48012613，area/solid逐点最大差2.22×10⁻¹⁶，同比缩放正确差0，错误数字比4。GGX三α的投影归一误差≤1.1×10⁻¹³；仅核NDF，不把它冒充完整微表面材质。

非作者已完成独立内容核查：576方向/PDF/权重条件、九个理论格、92160个benchmark估计及45行汇总、65536个圆盘权重、31744条路径和全部图像数组重放均通过；真实五反射几何/PDF/β与RR递推、完整文稿/9题解/三实际图/两完整镜像/六旧页局部返程通过。独立CLI的8生成附件与正式数据逐字相同，8tests实际.045s PASS；107个wiki文件/精确锚点成立。依据08与09及既有正文，独核建议在发布身份核验后按#169原六目标结项。数学结论、有限实现、显示/硬件、真人学习是不同证据层。未做真实材料/光源测量、相机光谱与显示器校准、GPU一致性、Obsidian实际预览或真人验收。

原范围的纹理/几何边界由08承担，本页承担辐射量、MC与直接/间接链；是否在发布核验后关闭#169按原六项验收与独核结论判断。完整生产引擎、所有焦散、体积/波动光学并非在本轮被暗中追加为统一验收门槛。
