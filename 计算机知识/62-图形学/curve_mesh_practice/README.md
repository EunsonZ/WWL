# 二次曲线 → 索引条带 → 既有 CPU 渲染器

[主解释与五题完整答案](../06-曲线网格与几何建模.md)回答控制点、切向、连接、拓扑与采样误差。此实验实际生成 5 组几何、调用同目录既有 `renderer.py` 生成 10 张 PNG，并保留全部数组与邻接。没有第二份光栅器，没有 GPU 或外部服务。

## 输入、对象与实现层

固定输入 [spec.json](spec.json) 的版本为 `quadratic-band-v1`。基准控制点 (0,0,0)/(1,2,0)/(2,0,0)，改控制点组为 P₁.y=3；均匀区间数 4/8/16，非均匀参数为 [0,.1,.2,.8,1]。参数无单位，所有对象坐标、平移与宽度共用一种任意场景长度单位。宽度 .25 为 Y 总跨度，非曲线法向等距宽度。

- [curve_mesh_lab.py](../curve_mesh_lab.py) 是规范生成器：de Casteljau 两层线性插值、解析切向、平面窄带网格、边与顶点 link 检查；PNG 写出只做文件序列化。正文有逐字镜像。
- [test_curve_mesh.py](../test_curve_mesh.py) 是行为测试真源，下面有逐字镜像。包括连续性、不同 N 的计数与误差、错误索引、退化、三面共边、蝴蝶结、错误绕序、构带域与输出目录归属。
- [curve_mesh_oracle.py](curve_mesh_oracle.py) 不导入生成器或 renderer：从原始输入以 Fraction 展开二次多项式，重算样本/切向/位置/误差；独立边计数检查拓扑；以相机射线与 z=−3 平面相交反求像素对应对象点，直接检验分段直线条带与线性色彩。它是当前固定构造的真值，不是任意场景通用渲染 oracle。
- [render_diagram.py](render_diagram.py) 从同一 actual.json 生成 [construction.svg](construction.svg)。[preview_diagram.py](preview_diagram.py) 只将 SVG 栅格预览成 [construction.png](construction.png)，不生成几何或替代实验输出。

原 renderer 数组接口为 positions[V,3]、整数 triangles[F,3]、colors[V,3] 线性 RGB、normals[V,3] 对象空间单位法线。模型 T(−1,−.5,−3)，view=I，默认透视 n/f=1/9、fovy90°、aspect1；clip w=3。原始结果内 `renderer_sha256` 固定实际被调用源码；renderer.py/test_renderer.py 本次只读，未运行旧渲染器整套测试，不能把旧验收称为本次重跑。

## 高重要性断言及为何值得运行

| 断言 | 重要性理由 | 输入/观察与失败判据 |
| --- | --- | --- |
| 递归插值与多项式是同一曲线，端点切向及 C¹/G¹ 条件正确 | 这是读者从编辑控制点过渡到可计算几何的承重定义 | 原始五组控制点/参数逐值对 Fraction 真值；坐标/导数/误差差值>10⁻¹² 失败 |
| 索引真正共享边，面方向与局部流形条件成立 | 可见接缝可能来自连接错误；只查 Euler 数会漏蝴蝶结 | 全量顶点/面/边/邻接、边界及 link；坏索引/退化/重复面/三面共边/断 link 应拒绝；不是只看 V−E+F |
| 固定 +Z 法线仅用于限定平面条带 | 不能让“轮廓弯曲”偷换成一般曲面法线 | 非 XY 控制点或非递增 x 的构带输入拒绝；一般 3D 点求值本身不被误禁 |
| 几何误差按最大参数跨度平方变化 | 点数相同不保证精度；防止非均匀采样被假验收 | N4/8/16 为 .0625/.015625/.00390625；改控制点 .09375；非均匀 .36。只检查中点截图不能证明最大值，本文另给精确二次推导 |
| 同一数组真实进入已有渲染器并形成预期像素 | 数表正确不能代替代码接线；错误空间/法线/颜色编码会破坏图 | 10 张 PNG 的尺寸、RGB、覆盖数和 SHA；作者固定 oracle 对非外边界像素字节容差 1，其余几何容差 10⁻¹²；独核另查完整边界归属 |
| 图与文字来自同一输入，几何和像素采样不混同 | 避免示意图与实验偷偷使用不同曲线 | construction.svg 读取 actual，正文覆盖表逐项一致；N4→N8→N16 覆盖数无需单调，不能以数多/图顺眼作为正确性证据 |

## 实际结果与原始记录

[results/actual.json](results/actual.json) 保留全部控制点、参数、曲线点、端点切向、positions、triangles、colors、normals、每段误差、全边列表、面邻居、link 与边界环，不仅保存终局统计。十张 PNG 位于同一目录，文件名由 case/resolution 对应，SHA 在各 `renders` 中。覆盖数为深度有限的像素数。

| case | 精确最大同参数误差 | V/E/F | 64² / 128² 覆盖数 |
| --- | --- | --- | --- |
| base_n4 | .0625 | 10/17/8 | 54 / 230 |
| base_n8 | .015625 | 18/33/16 | 58 / 218 |
| base_n16 | .00390625 | 34/65/32 | 56 / 220 |
| raised_n4 | .09375 | 10/17/8 | 60 / 220 |
| nonuniform | .36 | 10/17/8 | 62 / 241 |

[run-result.json](run-result.json) 是正式生成命令、实际解释器、单线程环境、exit0、0.151823 秒与原始 stdout/stderr。附加检查字段区分后续 oracle、测试和图预览命令，不把别人的运行合并为作者计时。作者实际 Python3.14.7/NumPy2.5.2；独立核查者使用 NumPy2.5.3，几何和 PNG 相同，环境元数据并不相同。[oracle-result.json](oracle-result.json) 是作者自建独立算法输出；[tests.stdout](tests.stdout) 与 [tests.stderr](tests.stderr) 保存 6 测试 exit0、unittest 内部计时 .021 秒。自测不代替未参与行为修改者的独核。

作者 oracle 对 nonuniform128 的一个精确外边界样本主动排除，其他样本均逐像素核；这是显式容差边界，不能声称作者 oracle 独立检查了全部 top-left 边界。独立审阅以原屏幕 top-left 规则另核该一个样本，十张完整 RGB/覆盖数 exact；独核入口由审阅者交整合者，未复制其证明为本脚本能力。实际 PNG 和 construction 图已经目视检查；Obsidian 客户端内嵌显示、真人理解与 GPU 输出均未验。

## 复建命令与资源范围

以下从库根运行。Python3.10+ 与 NumPy 可执行几何层；本次实际版本如上。使用新输出目录，程序拒绝已存在的输出目录，不覆盖已保存输入/结果。候选阶段用显式 `--renderer /实际主库/计算机知识/62-图形学/renderer.py`；整合后默认使用相邻唯一 renderer。

```bash
python3 -B 计算机知识/62-图形学/curve_mesh_lab.py --spec 计算机知识/62-图形学/curve_mesh_practice/spec.json --out /private/tmp/curve-mesh-rebuild-168
python3 -B 计算机知识/62-图形学/curve_mesh_practice/curve_mesh_oracle.py --spec 计算机知识/62-图形学/curve_mesh_practice/spec.json --actual /private/tmp/curve-mesh-rebuild-168/actual.json --out /private/tmp/curve-mesh-rebuild-168-oracle.json
python3 -B 计算机知识/62-图形学/test_curve_mesh.py
python3 -B 计算机知识/62-图形学/curve_mesh_practice/render_diagram.py --actual /private/tmp/curve-mesh-rebuild-168/actual.json --out /private/tmp/curve-mesh-rebuild-168-construction.svg
```

正式数值执行经现有本机 runner：`python3 /private/tmp/wwl-next-context/run_local.py --timeout 120 -- <实际解释器> -B <上述脚本与参数>`；它自动占用两数值槽之一并将 OMP/BLAS/VECLIB/NUMEXPR 线程设为 1。固定输入实际 5 case、10 张最大128² 图，常规远低于5分钟，不启动外部服务。CLI 限制最多8 case、每组2..65个参数、最多2种8..128分辨率，控制点有限且绝对值≤100；参数须包含0/1且严格间隔>10⁻⁸，构带控制 x 间隔>10⁻¹⁰。三角形叉积范数≤10⁻¹² 视为数值退化。此合同是有限教学输入的运行保护，不是鲁棒计算几何内核。

只复建 SVG 不需预览依赖。可选 PNG 预览用隔离环境安装 `resvg-py==0.5.0`，再执行 `python -B .../preview_diagram.py --svg /private/tmp/curve-mesh-rebuild-168-construction.svg --out /private/tmp/curve-mesh-rebuild-168-construction.png`。本次复用已存在隔离解释器 `/private/tmp/wwl-next-172-analytics/render-env/bin/python`，未改系统依赖；PingFang SC 的本机字形/缩放只是显示条件，不是跨平台 PNG 字节承诺。

## 变条件与真实未验接口

先在正文预测，再复制 spec 改控制点/参数/分辨率，写新输出目录；不要覆盖固定基线。小于阈值的极窄网格可能因面积阈值拒绝，不能把拒绝算成几何已被精确证伪。拓扑检查限连接和给定绕序，不能检测一般网格的空间自交、保证单个分量或自动修复非流形；C¹/G¹ 条件也未承诺匀速运动。

后续若做真正曲面，需要额外输入二维参数域、两方向切向及一致的法线/拼接条件，观察面片裂缝、自交与误差；若做层级/蒙皮，需要局部变换树、绑定姿势、权重与时间参数，观察关节连接及法线变化。那些实现尚未在本包运行，保留 #168 后续责任。GPU 接口可复用同一 positions/triangles/colors/normals 与相同 clip 约定，另比较边界样本、深度与颜色；没有执行 GPU/驱动，不能从本 CPU 结果推出硬件一致性。没有真人/硬件要求阻塞本有限几何单元，但也没有把这些层写成已验证。

## 行为测试镜像

<!-- code-sync: ../test_curve_mesh.py -->
```python
import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
import curve_mesh_lab as m
HERE=Path(__file__).parent
class Geometry(unittest.TestCase):
    def setUp(self):self.p=[[0,0,0],[1,2,0],[2,0,0]]
    def test_construct_point_and_join(self):
        np.testing.assert_allclose(m.casteljau(self.p,.5),[1,1,0]);np.testing.assert_allclose(m.tangent(self.p,1),[2,-4,0])
        q=[[2,0,0],[3,-2,0],[4,0,0]];np.testing.assert_allclose(m.tangent(q,0),m.tangent(self.p,1))
        q[1]=[2.5,-1,0];np.testing.assert_allclose(2*m.tangent(q,0),m.tangent(self.p,1))
    def test_strip_topology_and_error(self):
        for N in [1,4,8,16]:
            x=m.band(self.p,np.linspace(0,1,N+1),.25);t=x['topology']
            self.assertEqual([t[k] for k in ['V','E','F','chi','boundary_count']],[2*N+2,4*N+1,2*N,1,2*N+2])
            self.assertAlmostEqual(x['exact_matched_parameter_max'],1/N**2)
    def test_bad_indices_and_degenerate(self):
        x=m.band(self.p,[0,.5,1],.25);f=np.array(x['triangles']);f[0,0]=99
        with self.assertRaisesRegex(ValueError,'face_index'):m.topology(x['positions'],f)
        with self.assertRaisesRegex(ValueError,'numerically_degenerate'):m.topology([[0,0,0],[1,0,0],[2,0,0]],[[0,1,2]])
        with self.assertRaisesRegex(ValueError,'duplicate_face'):m.topology([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2],[2,1,0]])
    def test_nonmanifold_edge_and_vertex(self):
        p=[[0,0,0],[1,0,0],[0,1,0],[0,-1,0],[0,0,1]]
        with self.assertRaisesRegex(ValueError,'nonmanifold_edge'):m.topology(p,[[0,1,2],[1,0,3],[0,1,4]])
        p=[[0,0,0],[1,0,0],[0,1,0],[-1,0,0],[0,-1,0]]
        with self.assertRaisesRegex(ValueError,'disconnected_vertex_link'):m.topology(p,[[0,1,2],[0,3,4]])
    def test_wrong_orientation_and_band_domain(self):
        with self.assertRaisesRegex(ValueError,'shared_edge_orientation'):m.topology([[0,0,0],[1,0,0],[0,1,0],[0,-1,0]],[[0,1,2],[0,1,3]])
        for p,ts,w in [([[0,0,0],[0,1,0],[0,2,0]],[0,1],.25),(self.p,[0,.5,.5,1],.25),(self.p,[0,1],0),([[0,0,0],[1,2,1],[2,0,0]],[0,1],.25)]:
            with self.assertRaises(ValueError):m.band(p,ts,w)
    def test_parameters_and_output_ownership(self):
        with self.assertRaises(ValueError):m.casteljau(self.p,1.1)
        with self.assertRaises(ValueError):m.casteljau(self.p,float('nan'))
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):m.run({},Path('not-used'),Path(d))
if __name__=='__main__':unittest.main(verbosity=2)
```
