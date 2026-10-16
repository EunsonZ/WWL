# 同一曲面对象的建模、层级与运动

本实践接 [06 的 B-spline/曲面/细分主解释](../06-曲线网格与几何建模.md) 与 [07 层级动画与变形](../07-层级动画与变形.md)，从固定原始规格生成完整状态与 13 张 CPU 图。旧 `renderer.py` 和 `curve_mesh_lab.py` 只读复用；没有复制或修改旧光栅化/拓扑实现，旧十张窄带图与其成熟测试本次没有重跑。

## 固定输入与证据层

[spec.json](spec.json) 版本 `surface-animation-v1` 是唯一固定输入，含两组 B-spline、3×3 曲面控制网、几何分段 N、Loop 级数、骨骼时点、四元数端点、IK目标、弹簧频率/步长/时长和图像分辨率。坐标单位 m、时间 s、角度源输入 degree 明示后转 rad；参数 u/v/α 无单位。

1. **表示与几何层**：[surface_lab.py](../surface_lab.py) 实际执行 Cox–de Boor 基函数递推、双二次 Bézier patch 与 Loop 有限细分。`control[i][j]` 分别对应 u/v，mesh index=j*(N+1)+i，每格面(a,b,c)/(b,d,c)沿b—c分割。一般控制网可求值，固定误差公式只用于当前解析 S=(2u,2v,u(1−u)+v(1−v))。B-spline 不是 NURBS/CAD 引擎；Loop 当前内点用含 cos 的原 β、平滑边界，不能混称 Warren 近似/硬角规则。
2. **姿态与运动层**：[animation_lab.py](../animation_lab.py) 实际执行列向量层级、wxyz Hamilton主动右手旋转、最短弧SLERP（近角转NLERP）、LBS、平面两杆FK/IK和两种弹簧积分。FK/IK消费机器人已发布2R相对角/单位/多解合同，没有另建机器人动力学平台。根弹簧 m=1kg、k=4N/m、q0=1m、v0=0，T1s；超界反例T10s另标，不能和T1误差比较混合。
3. **渲染层**：[run_lab.py](run_lab.py) 把实际 positions/triangles/colors/normals/model 交给唯一 renderer；结果记录全量渲染输入、覆盖数与PNG SHA。patch用解析法线，Loop/skin用实际变形三角面叉积的平面法线；后者复制顶点只为渲染，原焊接网格拓扑仍另存。没有将逐点混合矩阵逆转置当连续权重场的精确法线。
4. **独立批量答案层**：[batch_oracle.py](batch_oracle.py) 只用标准库，从原始规格以分段有理多项式、独立权矩阵、解析曲面/平面旋转和精确2×2矩阵幂重建答案；不import两个规范模型、旧topology、NumPy或renderer。它核几何/状态与PNG身份，**不是新场景的独立像素渲染证明**。旧renderer验收只作为被复用前提，不能冒称本次运行了其整套suite。非作者独核另用不同路线核承重定义/变式/正文，作者oracle不能代替独核。

## 逐断言的高重要性验收

| 断言 | 重要性理由 | 必须检查的观察与失败条件 |
| --- | --- | --- |
| B-spline权重/节点/右端/局部支撑正确 | 否则把控制点当插值点、改一点牵动错误区间 | 两规格14点的全权重与点；分段有理式逐值比对，右端按左极限浮点容差；修改P0不影响t1.5；坏节点总数/次序/域应拒绝 |
| patch位置、偏导与法线使用同一(u,v)索引 | 交换两轴可画出“像曲面”的错误数组 | 全网格与解析式逐值，4独立参数点的du/dv/normal，叉积零应拒绝；不是只核中心 |
| 几何误差是同参数三角近似的精确最大值 | 采样点恰好在曲面上不能证明面内精度 | 每格对角中点误差N4=.03125、N8=.0078125m，结合正文二次式证明；不冒称最近点精确距离 |
| Loop同步位置/边界/β和拓扑一致 | 遍历写回会偷偷换算法；原β与简式并非处处相同 | 三全级别positions/faces/拓扑，初始中心.5→.375→.34375；V/E/F和boundary，四价β31/256区别；不是把Loop当原patch重采样 |
| 层级方向、四元数约定与最短弧一致 | 小图可能掩盖旋转反向/父子倒置 | 全local/world/bind；TS/ST=5/8；170→−170中点将X转−X；双覆盖不改物理姿态；near-angle分支仅近似恒速 |
| LBS的逆绑定/权和/非刚体与法线边界正确 | 少一个inverse bind可让绑定姿态本身移动 | 三姿态全顶点/权重/矩阵；G=B应复原；坏权/奇异bind拒绝；I/R180等权塌缩和面退化失败；无体积守恒/全局自交保证 |
| IK分清多解/不可达/欠定 | 迭代出一个数不等于实际可达或唯一 | (1,1)两支、(2,0)边界一支、(3,0)unreachable、(0,0)underdetermined；FK回代和输入约束，不推碰撞/限位已验 |
| 积分次序、全轨迹、稳定边界与单位正确 | 仅比较末端位置会掩盖速度抵消和失稳 | 80状态逐步比精确矩阵幂，q/v/time/energy；位置与v/ω合成同单位误差；辛稳定严格0<hω<2，等号不是有界保证 |
| 同对象N×h可独立改变且真实送入renderer | 更多面不能证明时间稳定，截图不能代世界空间误差 | 四组合同时保存几何误差、q_error、phase_state_error与实际PNG；N只改几何，h只改状态；13图全输入/SHA绑定 |

数值比较容差为 `abs(a-b) <= 1e-10*max(1,abs(a),abs(b))`，计数/索引/裁决精确相等。较大超界状态采用相对容差，不能写成一律绝对10⁻¹⁰。PNG身份按SHA精确；本作者批量oracle没有规定新像素“近似通过”门槛。图的字体预览与几何结果分层。

## 正式结果与原始运行

[results/actual.json](results/actual.json) 保存：14条样条完整权重/点及局部修改；全部patch点/面/法线/拓扑/逐格误差；Loop0/1/2完整网格/边新点索引；每姿态parent/local/world/bind/weight/K与全部顶点；IK所有分支/拒因；显式与辛Euler的完整80状态；四N×h比较；13渲染数组/model/覆盖数/PNG SHA。它没有仅存一个“PASS”或最终sum。

[run-result.json](run-result.json) 记录实际命令、Python3.14.7、NumPy2.5.2（actual内）、单线程环境、exit0、生成耗时 .465764s 及原始stdout/stderr。[oracle-result.json](oracle-result.json) 为独立算法实际PASS；[tests.stdout](tests.stdout)/[tests.stderr](tests.stderr) 为9行为测试原始捕获，exit0、unittest内部 .020s。追加检查各列实际退出码，未把未测时长写成实测。渲染及几何所用旧源码SHA在actual的bindings，旧源本次只读。

| 核心结果 | 实际值 |
| --- | --- |
| patch N4 / N8几何最大同参数误差 | .03125 / .0078125m |
| Loop V/E/F | 9/16/8 → 25/56/32 → 81/208/128 |
| Loop旧中心z | .5 → .375 → .34375m，目标形状改变 |
| 辛Euler h=.25/.125/.0625，T1状态误差 | .2526460591 / .1191518448 / .0581072442m |
| 显式Euler同h、T1状态误差 | .5910883923 / .2781505042 / .1325095078m |
| 辛Euler h1.25、T10超界q | 87381.33332824707m，非物理增能 |
| 13实际帧 | patch两帧、Loop三帧、skin三帧、N×h四帧、解析根位置参考一帧 |

[geometry.svg](geometry.svg)/[geometry.png](geometry.png) 和 [motion.svg](motion.svg)/[motion.png](motion.png) 由 [diagrams.py](diagrams.py) 从同一actual/spec生成，已实际目视检查；几何图斜投影非等距量图，运动图解析线用cos(ωt)而不是混成模拟轨迹。13张CPU图已实际检查可读输出；不声称GPU、Obsidian客户端或真人理解被验收。

## 可复建命令与有限资源

从库根运行。只有 run_lab 的 --out 要求新目录并拒绝已存在目录；batch_oracle、diagrams 和预览助手会写入或覆盖指定文件。下例将后续结果也放入 run_lab 新建的复建目录，避免覆盖已保存的课程基线。几何/运动执行层需Python3.10+及NumPy；实际版本以上述记录为准，跨版本元数据可能不同。batch oracle是纯标准库。缺NumPy时可在 `/private/tmp` 新建venv安装匹配版本，不改系统或主库环境。没有安装/启动外部服务。

```bash
python3 -B 计算机知识/62-图形学/model_animation_practice/run_lab.py --spec 计算机知识/62-图形学/model_animation_practice/spec.json --shared-dir 计算机知识/62-图形学 --out /private/tmp/surface-animation-rebuild-168
python3 -B 计算机知识/62-图形学/model_animation_practice/batch_oracle.py --spec 计算机知识/62-图形学/model_animation_practice/spec.json --actual /private/tmp/surface-animation-rebuild-168/actual.json --out /private/tmp/surface-animation-rebuild-168/oracle.json
python3 -B 计算机知识/62-图形学/test_surface_animation.py
python3 -B 计算机知识/62-图形学/model_animation_practice/diagrams.py --spec 计算机知识/62-图形学/model_animation_practice/spec.json --actual /private/tmp/surface-animation-rebuild-168/actual.json --out-dir /private/tmp/surface-animation-rebuild-168
```

候选阶段测试另加 `--shared-dir /实际主库/计算机知识/62-图形学`，驱动也用此显式目录，以便导入只读renderer/topology，两个新模块优先从候选父目录加载；整合后相邻路径即为同一源。正式执行均经 `python3 /private/tmp/wwl-next-context/run_local.py --timeout 120 -- <实际解释器> -B <脚本/参数>`，自动占用两数值槽之一，OMP/BLAS/VECLIB/NUMEXPR强制1线程。当前固定输入远低于5分钟。输入保护限制patch每向≤12、最多3种N、Loop初始N≤4/级数≤2、图64/128、skin最多4时点/终角≤45°、IK最多8目标、样条每组≤32参数且control≤12/p≤3；T1时h≥1/32且整除1，积分最多64步、h≤2且hω≤4。后者只是有限运行上限，**不**意味着hω=4稳定。

程序先构建各组状态，再创建新结果目录，但导入模块可能先发生；渲染过程中失败可留下部分输出，未承诺全输出事务原子性。不要把部分目录当完成证据，应检查进程退出码与actual是否完整。源规格不是任意不可信JSON的服务级validator；固定合同之外修改可能清晰失败，不扩写为生产工具。

可选PNG讲解图预览复用旧 [preview_diagram.py](../curve_mesh_practice/preview_diagram.py)：隔离环境`resvg-py==0.5.0`，`--svg <geometry或motion.svg> --out <新png>`，本机PingFang SC/1600px。此次复用已存在 `/private/tmp/wwl-next-172-analytics/render-env/bin/python`，没有新装依赖；其他字体/平台不承诺预览PNG字节相同。

## 变条件、边界与下一层

在新spec/输出目录改输入，先预测再运行正文四道形状题与六道动画题；固定batch oracle刻意只接受当前两种节点配置及解析patch，换任意控制网需要对应独立答案，而不是更改断言来“过绿”。规范patch函数支持一般3×3控制网，独立审阅另用非可分离网格核过点/du/dv/法线，不据此宣布所有网格都合法。

B-spline实体曲线、规则patch与Loop细分目标不同；Loop限制于通过现有局部流形检查的三角网格，不能自动保证一般嵌入无自交或给任意非流形修复。关键帧不含力，FK/IK不含碰撞/力矩；LBS可能塌缩，重算法线不是修复形变。辛稳定推导只针对线性无阻尼弹簧，不是所有受力系统的步长证书。

若继续做真实GPU，输入保持相同数组/clip/color约定，具体观察应是边界样本、深度、法线与颜色差异；本包未执行GPU/驱动。若继续接触/柔体，要增加质量/约束/接触与积分器，观察约束残差及耗散/能量；当前仅根节点单自由度弹簧。NURBS/硬折痕/高阶四元数曲线/双四元数蒙皮分别有明确模型入口，但不是原本有限单元交付必须覆盖所有生产分支的新门槛。原#168机制、图形生成与运动、分段/步长独立比较的闭环由06+07及前包共同承担；整课结项须另由非作者按原scope审计。

## 新行为测试镜像

<!-- code-sync: ../test_surface_animation.py -->
```python
"""Behavior boundaries for the new geometry and animation layers only."""
import math,sys,unittest
from pathlib import Path
import numpy as np
if len(sys.argv)>1 and sys.argv[1]=='--shared-dir':sys.path.insert(0,sys.argv.pop(2));sys.argv.pop(1)
import surface_lab as s
import animation_lab as a


def control():return np.array([[[i,j,.5*((i==1)+(j==1))] for j in range(3)] for i in range(3)],float)


class NewLayers(unittest.TestCase):
    def test_spline_support_and_knots(self):
        p=np.array([[0,0,0],[1,2,0],[2,2,0],[3,0,0]],float);k=[0,0,0,1,2,2,2]
        np.testing.assert_allclose(s.spline(p,k,2,1)['point'],[1.5,2,0])
        for t in [0,.5,1,1.5,2]:self.assertAlmostEqual(sum(s.spline(p,k,2,t)['basis']),1)
        changed=p.copy();changed[0,1]+=1;self.assertEqual(s.spline(p,k,2,1.5),s.spline(changed,k,2,1.5))
        for knots,degree,t in [(k[:-1],2,1),([0,0,0,2,1,2,2],2,1),(k,2,3),(k,4,1)]:
            with self.assertRaises(ValueError):s.spline(p,knots,degree,t)

    def test_repeated_knot_kink(self):
        p=[[0,0,0],[1,2,0],[2,2,0],[2,3,0],[4,0,0]];k=[0,0,0,1,1,2,2,2];mid=np.array(s.spline(p,k,2,1)['point']);h=1e-6
        np.testing.assert_allclose(mid,[2,2,0]);np.testing.assert_allclose((mid-s.spline(p,k,2,1-h)['point'])/h,[2,0,0],atol=3e-6);np.testing.assert_allclose((s.spline(p,k,2,1+h)['point']-mid)/h,[0,2,0],atol=5e-6)

    def test_patch_point_derivatives_and_domain(self):
        p,du,dv,n=s.patch(control(),.5,.5);np.testing.assert_allclose(p,[1,1,.5]);np.testing.assert_allclose(du,[2,0,0]);np.testing.assert_allclose(dv,[0,2,0]);np.testing.assert_allclose(n,[0,0,1])
        with self.assertRaises(ValueError):s.patch(np.zeros((3,3,3)),.5,.5)
        with self.assertRaises(ValueError):s.patch(control(),1.1,.5)
        with self.assertRaises(ValueError):s.patch_mesh(control(),1000)

    def test_loop_sync_and_boundary(self):
        mesh=s.patch_mesh(control(),2);before=np.array(mesh['positions']);r=s.loop_step(mesh['positions'],mesh['triangles']);np.testing.assert_equal(mesh['positions'],before)
        np.testing.assert_allclose(r['positions'][0],[.125,.125,.0625]);np.testing.assert_allclose(r['positions'][4],[1,1,.375]);self.assertEqual([r['topology'][x] for x in ('V','E','F','chi','boundary_count')],[25,56,32,1,16])
        with self.assertRaises(ValueError):s.loop_step(mesh['positions'],mesh['triangles']+[mesh['triangles'][0]])

    def test_hierarchy_order_and_nonrigid(self):
        r=a.hierarchy([-1,0],[a.translation(3,0,0),np.diag([2,1,1,1])]);np.testing.assert_allclose(r[1]@[1,0,0,1],[5,0,0,1])
        with self.assertRaises(ValueError):a.hierarchy([1,-1],[np.eye(4),np.eye(4)])

    def test_quaternion_double_cover_and_short_arc(self):
        q=a.axis_angle([0,0,1],math.radians(170));r=a.axis_angle([0,0,1],math.radians(-170));mid=a.rotation(a.slerp(q,r,.5));np.testing.assert_allclose(mid@[1,0,0,1],[-1,0,0,1],atol=1e-12);np.testing.assert_allclose(a.rotation(a.slerp(q,-q,.4)),a.rotation(q))
        with self.assertRaises(ValueError):a.axis_angle([0,0,0],1)
        with self.assertRaises(ValueError):a.slerp(q,r,-.1)

    def test_bind_weights_and_collapse(self):
        p=[[1,1,0]];b=[np.eye(4),a.translation(1,0,0)];np.testing.assert_allclose(a.skin(p,[[.5,.5]],b,b)['positions'],p)
        with self.assertRaises(ValueError):a.skin(p,[[.5,.6]],b,b)
        with self.assertRaises(ValueError):a.skin(p,[[-.1,1.1]],b,b)
        r=a.skin(p,[[.5,.5]],[np.eye(4),a.rotation(a.axis_angle([0,0,1],math.pi))],[np.eye(4),np.eye(4)]);np.testing.assert_allclose(r['positions'],[[0,0,0]],atol=1e-12);self.assertLess(abs(r['blend_linear_determinants'][0]),1e-24)
        with self.assertRaises(ValueError):s.flat_arrays({'positions':[[0,0,0],[0,0,0],[1,0,0]],'triangles':[[0,1,2]]})

    def test_inverse_multiple_and_unreachable(self):
        solutions=a.ik2([1,1],[1,1]);self.assertEqual(len(solutions),2)
        for q in solutions:np.testing.assert_allclose(a.fk2([1,1],q)['end'],[1,1],atol=1e-12)
        self.assertEqual(len(a.ik2([1,1],[2,0])),1)
        for target in [[3,0],[0,0]]:
            with self.assertRaises(ValueError):a.ik2([1,1],target)

    def test_integrator_order_and_work_bound(self):
        e=a.spring(2,.25,1,'explicit');v=a.spring(2,.25,1,'symplectic');self.assertEqual([e[-1]['q'],e[-1]['v']],[1,-1]);self.assertEqual([v[-1]['q'],v[-1]['v']],[.75,-1]);self.assertGreater(e[-1]['energy'],e[0]['energy'])
        for h,steps in [(0,1),(1e100,1),(.1,100000)]:
            with self.assertRaises(ValueError):a.spring(2,h,steps,'explicit')


if __name__=='__main__':unittest.main(verbosity=2)
```
