---
type: lab
stage: 1
aliases: []
sources:
  - "https://pbr-book.org/4ed/Textures_and_Materials/Texture_Sampling_and_Antialiasing"
  - "https://pbr-book.org/4ed/Textures_and_Materials/Image_Texture"
  - "https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf"
prerequisites:
  - "[[计算机知识/62-图形学/08-纹理足迹与抗锯齿]]"
---

# 固定三角形的纹理足迹实践

读 [[计算机知识/62-图形学/08-纹理足迹与抗锯齿|主解释]]，带着“同一像素平均哪一片纹理”的问题运行。本实践不更改旧renderer，直接调用其 perspective/samples/interpolate/srgb；没有复制另一套裁剪、深度或光照管线。源为 [texture_lab.py](texture_lab.py) 与 [test_texture_lab.py](test_texture_lab.py)，[[计算机知识/_labs/texture_footprint/源码与验证|code-sync镜像]]只供阅读。

## 为什么必须实际运行这组数据

本实验重要性高：主文的0.375对0.5反例依赖 texel 中心、屏幕相位、足迹尺度和线性域的共同合同；若其中一处偏半格，一张看似平滑的图可以掩盖错误。三组缩小尺度、独立面积参考、负UV和几何边界测试分别约束这些承重断言。它们验证有限CPU数组与实现，不证明所有纹理都无混叠，也不等于物理测光、GPU规范一致性或真人理解。

固定 [scene.json](scene.json) 声明位置(3,3)、三角形索引(1,3)、UV(3,2)、64²视口、32²棋盘、s=1/0.5/0.25、两轴相位0/0.25 texel。旧模型的照明系数在此不使用；纹理为未照明归一化线性灰度，黑背景。代码只接受本例等w且完整在裁剪域内的三角形，仿射UV导数须轴对齐；矩形面积参考只在满覆盖内部像素上代表完整像素颜色。生成图仍用中心覆盖mask，边缘另核。

## 固定输出与读法

- [results.json](data/results.json)：6行投影/UV/J/足迹/频率/探针、几何边、各向异性反例和实际环境；同时记输入scene与规范renderer的SHA256。
- [probes.csv](data/probes.csv)：同6行表，顺序为两个phase分别配三尺度；浮点残差约10⁻¹⁴，主文按精确几何写整数。
- [linear-images.npy](data/linear-images.npy)：float64，shape=(2,3,4,64,64)，索引依次phase、scale、method、y、x；method固定nearest/bilinear/box/mip。是线性域标量，尚未编码；RGB可复制同一通道。
- [coverage-masks.npy](data/coverage-masks.npy)：bool，shape=(2,3,64,64)，旧renderer中心覆盖，四method共用。未覆盖处线性0。
- ![[计算机知识/_labs/texture_footprint/data/texture-comparison.png|900]]
- ![[计算机知识/_labs/texture_footprint/data/edge-coverage.png|800]]

两PNG由上述数组和results绘制；主图取phase=0.25，每个尺寸单独裁切再最近邻放大，标题给真实crop范围。第二图解析面积0.32与规则子中心计数同源，Y向下。PNG是解释图，不是加入了面积覆盖的全新渲染结果。

## 预测、容差与失败判据

在s=1/0.5/0.25时，J分别近似I/2I/4I，单位texel/pixel；面积是1/4/16 texel²。phase0.25内部探针四列应分别为(1,.625,.625,.625)、(0,.375,.5,.5)、(0,.375,.5,.5)，误差≤10⁻¹²。精确box通过与独立可分离方波原函数比较，覆盖整数/非整数足迹、repeat与负UV；不能拿同一个overlap函数自证。

mip层尺寸32/16/8/4/2/1，棋盘一级后全0.5。本教学实现每次查询重建层级，未缓存跨查询复用；金字塔预计算的效率收益是机制说明，本轮未做速度比较。竖条纹中心(0.5,0.5)texel、足迹(1,8)时box0而本isotropic mip为.5，拒绝“mip总等精确面积平均”。白三角形Y平移.2时pixel(24,40)解析面积.32，n=1/4/8/32规则覆盖为0/.375/.328125/.3173828125；它只是有限求积，绝不承诺一般误差单调。线性0.5编码为.7353569830524495；编码0.5解码为.21404114048223255，绝差≤10⁻¹²。

无效shape、非有限/过大输入、bool数组/标量、越界颜色、零或过大footprint、非方形/非2幂mip、未知method都应在采样前ValueError；不存在状态ledger或外部写入。有限输入上限为绝对值10⁶，纹理每轴1..64、值[0,1]，box每轴宽1/64..64 texel，projected尺度.25..1，phase−1..1 texel。Python异质列表若由NumPy先转为数值dtype，元素原类型不再保留；本合同检查最终数组dtype/值，不声称追踪所有元素的原Python类型。

任一数表不符、输入接受非有限值、镜像不同字节，或把mip/box当成几何边界真值，都应停下纠正相应合同。普通相位0恰在texel边界时会受到浮点tie影响；它保留为实际输出，主图不靠该tie展示结论。

## 在全新库外目录复算

从库根执行，已有兼容环境可直接运行；新环境时依赖版本在 [requirements.txt](requirements.txt)。命令只把新输出写入 `mktemp` 目录，**不覆盖本页正式data**：

```bash
LAB="$PWD/计算机知识/_labs/texture_footprint"
RUN=$(mktemp -d /private/tmp/wwl-texture-XXXXXX)
# 可选：没有兼容环境时在库外建立，不安装到系统Python。
python3 -m venv "$RUN/venv"
"$RUN/venv/bin/python" -m pip install -r "$LAB/requirements.txt"
PY="$RUN/venv/bin/python"
MPLCONFIGDIR="$RUN/mpl" XDG_CACHE_HOME="$RUN/cache" "$PY" -B -m unittest discover -s "$LAB" -p test_texture_lab.py -v
MPLCONFIGDIR="$RUN/mpl" XDG_CACHE_HOME="$RUN/cache" "$PY" -B "$LAB/texture_lab.py" --output "$RUN/output"
```

库内默认从同级计算机知识目录定位规范renderer；隔离候选未带旧文件时，才设置 `WWL_RENDERER_SOURCE=/绝对路径/renderer.py`。输出目录必须原先不存在；拒绝覆盖已留证据目录。读取NPY请用 `np.load(path, allow_pickle=False)`。若只重绘，把本目录加到Python路径后调用 `texture_lab.plot('/新输出目录')`；它读取retained数组/results，不重算采样。

正式结果使用的 renderer SHA256 为 `a69a5c55330dfc19141187ef446a06cd53296608ac6e46f2f3d7a85697ddf203`，可从固定提交 `bd7266e0e1d113bb145c5cd765eb8cbbc291b4a6` 的 `计算机知识/62-图形学/renderer.py` 恢复并指向其库外副本。这是复现输入身份，不要求把主库回退该提交。新版本若变更接口/数值，应对照身份重新核，不能把历史结果冒充新执行。

## 本次真实执行与证据层

作者实际解释器为主库 `.venv/bin/python`，Python3.14.7、NumPy2.5.3、matplotlib3.11.2，macOS arm64；未安装依赖、未用远端/GPU。实际调用两槽runner，限制线程1、timeout120秒：

```bash
WWL_RENDERER_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/计算机知识/62-图形学/renderer.py' MPLCONFIGDIR=/private/tmp/wwl-next-169/mpl /private/tmp/wwl-next-context/run_local.py --timeout 120 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B -m unittest discover -s /private/tmp/wwl-next-169/vault/计算机知识/_labs/texture_footprint -p test_texture_lab.py -v
WWL_RENDERER_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/计算机知识/62-图形学/renderer.py' MPLCONFIGDIR=/private/tmp/wwl-next-169/mpl /private/tmp/wwl-next-context/run_local.py --timeout 120 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B /private/tmp/wwl-next-169/vault/计算机知识/_labs/texture_footprint/texture_lab.py --output /private/tmp/wwl-next-169/author-run-20261017
```

7tests实际0.224s、exit0，CLI exit0。[author-check.txt](data/author-check.txt)记录必要结果。首次matplotlib字体缓存提示无HOME写权限，实际仍成功绘图；后续重绘额外把XDG_CACHE_HOME指向候选区。作者看图后将边缘图Y轴反向匹配screenY向下，只有plot改动，沿同一retained数组/结果重新绘图，无采样重跑；正式PNG已同步。除图像字节可能受字体/绘图库影响外，数组和探针是数值复现的主要对象；环境字符串因机器可不同。

非作者已完成独立内容核查：128组有限Fraction周期分片积分/nearest/tent重建、mip块均值与LOD、三尺度投影与覆盖，24幅数组/两实际图、7tests、完整文稿/题解/两镜像及共享页局部返程均通过；6生成附件与其独立CLI输出逐字相同。未做Obsidian实际视觉预览、GPU API一致性、性能基准、物理测光或真人学习验收。#169后续辐射量/光传输/直接与间接路径仍未由本首单元交付；本实验不关闭整项。
