#!/usr/bin/env python3
"""生成知识库中的精确数学 SVG；所有参数均在此公开，不使用远程图片或字体文件。
运行：python 生成教学图示.py [--preview-dir PATH] [--only-helix]
依赖：numpy、matplotlib；完整生成（非 `--only-helix`）另需 scipy。SVG 将字形转为路径，阅读不需要安装中文字体。
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'assets'/'figures'
META: dict[str,dict] = {}
PREVIEW: Path | None = None

def setup() -> None:
    candidates = ('Noto Sans CJK SC','Noto Sans CJK TC','Microsoft YaHei','SimHei','Arial Unicode MS')
    available={f.name for f in font_manager.fontManager.ttflist}
    fallback=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if fallback.exists():
        font_manager.fontManager.addfont(str(fallback))
        family=font_manager.FontProperties(fname=str(fallback)).get_name()
    else:
        family=next((f for f in candidates if f in available),None)
    if family is None:
        raise RuntimeError('重绘中文图示需要本机中文字体；现有 SVG 可直接阅读，不受影响。')
    plt.rcParams['font.family']=family
    plt.rcParams['axes.unicode_minus']=False
    plt.rcParams['svg.fonttype']='path'
    plt.rcParams['font.size']=11
    OUT.mkdir(parents=True,exist_ok=True)

def base(title: str, xlabel: str='x', ylabel: str='y', equal: bool=False, three: bool=False):
    f=plt.figure(figsize=(8.4,5.7),layout='constrained')
    a=f.add_subplot(111,projection='3d' if three else None)
    a.set_title(title,pad=14); a.set_xlabel(xlabel); a.set_ylabel(ylabel)
    if equal: a.set_aspect('equal',adjustable='box')
    if not three: a.grid(True,alpha=.22)
    return f,a

def save(name: str, f, description: str, *, tight_bbox: bool=False) -> None:
    save_options={'bbox_inches':'tight','pad_inches':.1} if tight_bbox else {}
    f.savefig(OUT/(name+'.svg'),metadata={'Title':name,'Description':description,'Creator':'数学知识库：本地精确绘图脚本','Date':None},**save_options)
    if PREVIEW is not None:
        PREVIEW.mkdir(parents=True,exist_ok=True)
        f.savefig(PREVIEW/(name+'.png'),dpi=125,**save_options)
    META[name]={'file':'assets/figures/'+name+'.svg','construction':description,'remote_dependencies':False}
    plt.close(f)

def arrow(a, p, q, label: str='') -> None:
    a.annotate('',xy=q,xytext=p,arrowprops={'arrowstyle':'->','lw':1.4})
    if label: a.text((p[0]+q[0])/2,(p[1]+q[1])/2+.14,label,fontsize=10)

def generate_helix() -> None:
    f,a=base('螺旋线：切向量沿曲线出发',three=True)
    t=np.linspace(0,4*np.pi,700);a.plot(np.cos(t),np.sin(t),t/3);t0=2.4;p=np.array([np.cos(t0),np.sin(t0),t0/3]);v=np.array([-np.sin(t0),np.cos(t0),1/3]);a.quiver(*p,*v,length=.8,normalize=True);a.set_zlabel('z');a.set_box_aspect((1,1,1.5))
    a.set_xticks([-1,-.5,0,.5,1]);a.set_yticks([-1,-.5,0,.5,1])
    save('helix',f,'r(t)=(cos t,sin t,t/3)，切箭头起点为t=2.4处，方向r′。',tight_bbox=True)

def generate() -> None:
    from scipy.special import jv, jn_zeros
    f,a=base('极限：输入容差控制输出误差')
    x=np.linspace(1.25,2.7,500); eps=.65; d=min(1,eps/5)
    a.plot(x,x*x,label=r'$f(x)=x^2$'); a.axhline(4+eps,ls='--',label=r'$4\pm\varepsilon$'); a.axhline(4-eps,ls='--')
    a.axvline(2-d,ls=':',label=r'$2\pm\delta$');a.axvline(2+d,ls=':');a.plot([2],[4],'o');a.legend()
    save('epsilon-delta',f,'f=x², a=2, ε=0.65, δ=min(1,ε/5)=0.13；使用严格不等式容差。')
    f,a=base('局部线性化：二阶余项比位移更小')
    x=np.linspace(.2,1.8,400);a.plot(x,x*x,label=r'$x^2$');a.plot(x,2*x-1,label=r'$1+2(x-1)$')
    for v in [.6,1.4]: a.plot([v,v],[2*v-1,v*v],ls='--');a.text(v,v*v+.06,r'$(x-1)^2$',ha='center')
    a.legend();save('tangent-error',f,'x² 在 a=1 的切线 2x−1，垂直距离为 (x−1)²。')
    f,a=base('中值定理：割线与一条平行切线')
    x=np.linspace(0,2,400);a.plot(x,x*x,label=r'$x^2$');a.plot(x,2*x,label='端点割线');a.plot(x,2*x-1,label='c=1 处切线');a.plot([0,2],[0,4],'o');a.legend()
    save('mean-value',f,'f=x² 于[0,2]，割线斜率2=f′(1)。')
    f,a=base('Taylor 近似的局部有效性')
    x=np.linspace(-4,4,600);a.plot(x,np.sin(x),label=r'$\sin x$');a.plot(x,x-x**3/6,label=r'$x-x^3/6$');a.plot(x,x-x**3/6+x**5/120,label='五次多项式');a.set_ylim(-4,4);a.legend()
    save('taylor-sine',f,'sin x 的三次、五次 Maclaurin 多项式。')
    f,a=base('中点 Riemann 和：高度 × 宽度的累积')
    x=np.linspace(0,1,400); mids=(np.arange(8)+.5)/8
    a.bar(mids,mids*mids,width=1/8,alpha=.45,label='8 段中点矩形');a.plot(x,x*x,label=r'$x^2$');a.legend()
    save('riemann-sums',f,'[0,1] 上 x² 的8段中点和；这里只展示一个分割，不作为可积性证明。')
    f,a=base('数值积分：截断误差随步长变化','h','绝对误差')
    n=2**np.arange(1,14); et=[];es=[]
    for m in n:
        x=np.linspace(0,1,m+1);y=np.exp(x);h=1/m
        et.append(abs(h*(.5*y[0]+y[1:-1].sum()+.5*y[-1])-np.expm1(1)))
        es.append(abs(h/3*(y[0]+y[-1]+4*y[1:-1:2].sum()+2*y[2:-1:2].sum())-np.expm1(1)))
    a.loglog(1/n,np.maximum(et,np.finfo(float).eps),'o-',label='复合梯形');a.loglog(1/n,np.maximum(es,np.finfo(float).eps),'s-',label='复合 Simpson');a.legend()
    save('quadrature-error',f,'积分 exp(x) 从0到1；n=2^1 至2^13。低于机器精度的显示下限设为 ε，不能据此推断继续四阶。')
    f,a=base('尾积分：慢增长仍可能发散','截断上限 R','积分值')
    R=np.linspace(1,100,600);a.plot(R,np.log(R),label=r'$\int_1^R x^{-1}dx=\log R$');a.plot(R,1-1/R,label=r'$\int_1^R x^{-2}dx=1-1/R$');a.legend()
    save('improper-tail',f,'比较1/x与1/x²从1到R的截断积分。')
    f,a=base('部分和：收敛不是“看起来增长不快”','N','部分和')
    n=np.arange(1,101);a.plot(n,np.cumsum(1/n),label='调和级数');a.plot(n,1-2.**(-n),label=r'$\sum_{k=1}^N2^{-k}$');a.legend()
    save('series-partial-sums',f,'部分和 H_N 与1−2^(−N)，N≤100。')
    generate_helix()
    f,a=base('曲面与切平面：同时控制全部方向',three=True)
    u=np.linspace(.1,1.4,35);X,Y=np.meshgrid(u,u);a.plot_surface(X,Y,X*X+Y*Y,alpha=.55);a.plot_wireframe(X,Y,2*.7*X+2*.7*Y-2*.7**2,rstride=4,cstride=4,alpha=.8);a.scatter([.7],[.7],[.98]);a.set_zlabel('z')
    save('tangent-plane',f,'z=x²+y² 于(.7,.7)的切平面 z=1.4x+1.4y−.98。')
    f,a=base('Lagrange 乘子：目标等值线与约束相切',equal=True)
    t=np.linspace(0,2*np.pi,500);a.plot(np.cos(t),np.sin(t),label=r'$x^2+y^2=1$');x=np.linspace(-1.4,1.4,200)
    for c in [-np.sqrt(2),0,np.sqrt(2)]:a.plot(x,c-x,ls='--')
    p=np.ones(2)/np.sqrt(2);arrow(a,p,p+.45*np.ones(2));a.text(.1,1.2,r'$\nabla f\parallel\nabla g$');a.set_xlim(-1.5,1.5);a.set_ylim(-1.5,1.5);a.legend()
    save('lagrange',f,'f=x+y 在单位圆上的极值±√2；等值线x+y=c，梯度方向(1,1)。')
    f,a=base('Jacobian：整体面积伸缩不等于各边同倍伸长',equal=True)
    A=np.array([[1.5,.7],[.2,1.2]]);v=np.linspace(0,1,6)
    for x in v:
        a.plot([x,x],[0,1],ls=':');a.plot([0,1],[x,x],ls=':')
        q=A@np.array([[x,x],[0,1]])+np.array([[2.0],[0]]);a.plot(*q)
        q=A@np.array([[0,1],[x,x]])+np.array([[2.0],[0]]);a.plot(*q)
    a.text(.2,1.2,'输入网格');a.text(2.1,1.6,'输出网格，面积比 1.66');a.set_xlim(-.2,4.5);a.set_ylim(-.2,2)
    save('jacobian-grid',f,'线性变换A=[[1.5,.7],[.2,1.2]]，det=1.66；输出平移仅用于并排展示。')
    f,a=base('局部无旋 ≠ 绕洞积分为零',equal=True)
    x=np.linspace(-1.5,1.5,19);X,Y=np.meshgrid(x,x);R=X*X+Y*Y;mask=R>.08;U=np.zeros_like(X);V=U.copy();U[mask]=-Y[mask]/np.sqrt(R[mask]);V[mask]=X[mask]/np.sqrt(R[mask]);a.quiver(X,Y,U,V);t=np.linspace(0,2*np.pi,300);a.plot(np.cos(t),np.sin(t));a.add_patch(Circle((0,0),.11,fill=False));arrow(a,(1,0),(1,.3));a.text(.5,.015,'方向归一化显示；原点不在定义域',transform=a.transAxes,ha='center',fontsize=10)
    save('vortex-field',f,'F=(−y,x)/(x²+y²)，图只归一化箭头方向；原点去除，单位圆环流2π。')
    f,a=base('向量面积元：两个切向量的叉乘',three=True)
    u=np.linspace(-.5,1,20);X,Y=np.meshgrid(u,u);a.plot_surface(X,Y,1-X-Y,alpha=.4);p=np.array([.2,.2,.6]);vecs=[(1,0,-1),(0,1,-1),(1,1,1)]
    for v,l in zip(vecs,['r_x','r_y','n']):
        v=np.array(v)*.45;a.quiver(*p,*v);a.text(*(p+v),l)
    a.view_init(24,-65);a.set_zlabel('z');a.set_box_aspect((1,1,1))
    save('surface-normal',f,'曲面z=1−x−y，r_x=(1,0,−1)，r_y=(0,1,−1)，叉积(1,1,1)朝上。')
    f,a=base('定向小面：内部公共边相互抵消',equal=True)
    for i in range(2):
      for j in range(2):
        a.add_patch(Rectangle((i,j),1,1,fill=False));off=.05
        arrow(a,(i+.15,j+off),(i+.85,j+off));arrow(a,(i+1-off,j+.15),(i+1-off,j+.85));arrow(a,(i+.85,j+1-off),(i+.15,j+1-off));arrow(a,(i+off,j+.85),(i+off,j+.15))
    a.set_xlim(-.2,2.2);a.set_ylim(-.2,2.2);a.set_axis_off();save('boundary-cancellation',f,'四个正向平面方格，共享边出现两次且方向相反；边箭头略向各自单元内平移以便辨认。')
    f,a=base('上下极限：去掉有限前项之后的振荡','n',r'$a_n$')
    n=np.arange(1,61);v=(-1.)**n+1/n;a.plot(n,v,'o',ms=4);a.axhline(1,ls='--',label=r'$\limsup=1$');a.axhline(-1,ls=':',label=r'$\liminf=-1$');a.legend();save('limsup-liminf',f,'a_n=(−1)^n+1/n；水平线是上下极限，不是每一项的上下界。')
    f,a=base('点态但非一致：边界层挤向 x=1')
    x=np.linspace(0,1,1000)
    for n in [1,5,20,100]:a.plot(x,x**n,label=f'n={n}')
    a.legend();save('uniform-convergence',f,'[0,1]上的x^n；极限在[0,1)为0，在1为1。')
    f,a=base('光滑但不解析：所有 Taylor 系数都是零')
    x=np.linspace(-1.5,1.5,1001);y=np.zeros_like(x);m=x!=0;y[m]=np.exp(-1/x[m]**2);a.plot(x,y,label=r'$e^{-1/x^2}\ (x\ne0)$');a.axhline(0,ls='--',label='Taylor 级数 = 0');a.legend();save('flat-function',f,'f(0)=0，x≠0时exp(−1/x²)，在0处所有阶导数0，但任意邻域不恒零。')
    f,a=base('Fourier 收敛与跳跃附近的 Gibbs 现象')
    x=np.linspace(-np.pi,np.pi,1800);a.plot(x,x,ls='--',label='锯齿波（一周期）')
    for N in [5,20,80]:
        y=sum(2*(-1)**(n+1)*np.sin(n*x)/n for n in range(1,N+1));a.plot(x,y,label=f'N={N}')
    a.legend();save('fourier-gibbs',f,'f(x)=x 于(−π,π)的周期延拓，b_n=2(−1)^(n+1)/n；端点级数收敛到0。')
    f,a=base('收缩的支集，增大的高度，不变的积分','x','函数值')
    for n in [3,6,12]: a.step([0,1e-6,1/n,1/n+1e-6,1],[0,n,n,0,0],where='post',label=f'n={n}，面积=1')
    a.set_xlim(-.03,1);a.legend();save('moving-spike',f,'n 1_(0,1/n)，端点取值不影响积分；阶梯仅表达几乎处处值。')
    f,a=base('压缩映射：cos x 迭代的不动点',equal=True)
    x=np.linspace(0,1,400);a.plot(x,x,label='y=x');a.plot(x,np.cos(x),label='y=cos x');v=.1
    for _ in range(10): w=np.cos(v);a.plot([v,v,w],[v,w,w],ls=':');v=w
    a.legend();save('fixed-point',f,'cos把[0,1]映入[0,1]，Lipschitz上界sin(1)<1；从0.1作10次蛛网迭代。')
    f,a=base('行列式：单位面积变为 2',equal=True)
    p=np.array([[0,0],[1,0],[1,1],[0,1],[0,0]]);A=np.array([[2,1],[0,1]]);a.plot(*p.T,label='单位正方形');a.plot(*(p@A.T).T,label='A 的像');a.set_xlim(-.3,3.4);a.set_ylim(-.3,1.6);a.legend();save('determinant-area',f,'A=[[2,1],[0,1]]；列向量张成平行四边形面积2。')
    f,a=base('四个基本子空间：维数与正交分解')
    a.set_axis_off();a.set_xlim(0,10);a.set_ylim(0,6)
    boxes=[(.3,3.4,3.4,1.5,r'$\operatorname{im}A^T$'+'\n行空间：维数 r'),(.3,.6,3.4,1.5,r'$\ker A$'+'\n核：维数 n-r'),(6.1,3.4,3.5,1.5,r'$\operatorname{im}A$'+'\n列空间：维数 r'),(6.1,.6,3.5,1.5,r'$\ker A^T$'+'\n左核：维数 m-r')]
    for x,y,w,h,label in boxes: a.add_patch(Rectangle((x,y),w,h,fill=False));a.text(x+w/2,y+h/2,label,ha='center',va='center')
    arrow(a,(3.8,4.15),(6,4.15),'A：双射');arrow(a,(3.8,1.4),(5,1.4),'A → 0');a.text(2,2.7,'正交直和',ha='center');a.text(7.8,2.7,'正交直和',ha='center');a.text(2,5.3,r'$\mathbb{R}^n$',ha='center');a.text(7.8,5.3,r'$\mathbb{R}^m$',ha='center');save('four-subspaces',f,'实m×n秩r矩阵；复空间用共轭转置。框图仅表达关系与维数。')
    f,a=base('鞍点：一个特征方向增长，另一个衰减',equal=True)
    x=np.linspace(-2,2,24);X,Y=np.meshgrid(x,x);a.streamplot(X,Y,X,-Y,density=1);a.set_xlim(-2,2);a.set_ylim(-2,2);save('linear-flow',f,'常微分系统x′=x,y′=−y，原点鞍点。')
    f,a=base('投影：残差与子空间正交',equal=True)
    v=np.array([1.,2.]);d=np.array([2.,1.]);p=d*np.dot(v,d)/np.dot(d,d);a.plot([-1,3],[-.5,1.5],label='span(2,1)');arrow(a,(0,0),v);arrow(a,(0,0),p);arrow(a,p,v);a.text(.85,2.15,'v');a.text(p[0]+.1,p[1]-.15,'Pv');a.text(1.55,1.5,'v-Pv');a.set_xlim(-.5,3);a.set_ylim(-.5,2.6);a.legend();save('orthogonal-projection',f,'v=(1,2)投影到span(2,1)，Pv=(1.6,.8)，残差(−.6,1.2)垂直。')
    f,a=base('谱定理：正交主轴下没有交叉项',equal=True)
    x=np.linspace(-2,2,300);X,Y=np.meshgrid(x,x);cs=a.contour(X,Y,3*X*X+2*X*Y+2*Y*Y,levels=[.5,1,2,4,8]);a.clabel(cs,inline=True);w,V=np.linalg.eigh([[3,1],[1,2]])
    for v in V.T: a.plot([-1.8*v[0],1.8*v[0]],[-1.8*v[1],1.8*v[1]],ls='--')
    save('quadratic-levels',f,'Q=3x²+2xy+2y²，实对称矩阵[[3,1],[1,2]]；主轴使用eigh计算。')
    f,a=base('SVD：单位圆的像与奇异轴',equal=True)
    t=np.linspace(0,2*np.pi,600);q=np.array([np.cos(t),np.sin(t)]);A=np.array([[2,1],[0,1]]);U,s,_=np.linalg.svd(A);a.plot(*q,ls='--',label='输入单位圆');a.plot(*(A@q),label='输出椭圆')
    for i in range(2): arrow(a,(0,0),U[:,i]*s[i]);a.text(*(U[:,i]*s[i]*1.07),f'σ{i+1}={s[i]:.3f}',ha='right' if i==0 else 'left')
    a.set_xlim(-2.7,2.7);a.set_ylim(-1.6,1.6);a.legend();save('svd-ellipse',f,'A=[[2,1],[0,1]]，长短轴由左奇异向量×奇异值给出。')
    f,a=base('条件数：逆映射放大小奇异方向',equal=True)
    t=np.linspace(0,2*np.pi,600);a.plot(np.cos(t),np.sin(t),ls='--',label='输入圆');a.plot(np.cos(t),.08*np.sin(t),label='diag(1,0.08) 的像');a.text(-.7,-1.35,r'$\kappa_2=1/0.08=12.5$');a.legend();save('conditioning',f,'diag(1,.08) 的二范数条件数12.5。')
    f,a=base('Jordan 链：算子 N 将每级推向前一级')
    a.set_axis_off();a.set_xlim(0,9);a.set_ylim(0,4)
    for yy,n in [(2.9,3),(1.2,2)]:
      a.text(.3,yy,'0',ha='center')
      for i in range(1,n+1):
        xx=2.3*i;a.text(xx,yy,('$v_'+str(i)+'$') if n==3 else ('$w_'+str(i)+'$'),ha='center');arrow(a,(xx-.35,yy),(xx-1.7,yy))
    a.text(4.1,.25,r'$Nv_1=Nw_1=0$',ha='center');save('jordan-chains',f,'两条幂零链长度3与2，箭头N的作用方向由高索引指向低索引，末端0。')
    f,a=base('双二次扩张：域包含与固定子群反向')
    a.set_axis_off();a.set_xlim(-.6,8.6);a.set_ylim(-.5,5.5)
    pts=[(4,4.7),(0.8,2.5),(4,2.5),(7.2,2.5),(4,.3)]
    for i in [1,2,3]:a.plot([4,pts[i][0]],[4.4,2.9]);a.plot([pts[i][0],4],[2.1,.7])
    labels=[r'$\mathbb{Q}(\sqrt{2},\sqrt{3})$'+'\n固定子群阶 1',r'$\mathbb{Q}(\sqrt{2})$'+'\n固定子群阶 2',r'$\mathbb{Q}(\sqrt{3})$'+'\n固定子群阶 2',r'$\mathbb{Q}(\sqrt{6})$'+'\n固定子群阶 2',r'$\mathbb{Q}$'+'\n固定子群阶 4']
    for p,l in zip(pts,labels):a.text(*p,l,ha='center',va='center')
    save('galois-lattice',f,'Q(√2,√3)/Q 的全部中间域；子群仅以阶数标注，三个不同阶2子群对应三个二次子域。')
    f,a=base('复平方映射：正交网格的曲线像','Re w','Im w',True)
    q=np.linspace(-1.6,1.6,500)
    for b in np.linspace(-1.5,1.5,11):
      for z in [q+1j*b,b+1j*q]:w=z*z;a.plot(w.real,w.imag,lw=.8)
    a.set_xlim(-4,4);a.set_ylim(-4,4);save('complex-square',f,'将−1.6≤Re z,Im z≤1.6的直角网格经w=z²映射，临界点z0不保角。')
    f,a=base('主值辐角：负实轴两岸是不同极限','Re z','Im z',True)
    t=np.linspace(-np.pi+.1,np.pi-.1,600);a.plot(np.cos(t),np.sin(t));a.plot([-1.5,0],[0,0],ls='--',label='分支切线（排除）');a.scatter([-1,-1],[.11,-.11]);a.text(-1.4,.35,r'$\arg z\to\pi$');a.text(-1.4,-.5,r'$\arg z\to-\pi$');arrow(a,(1,0),(.99,.25));a.set_xlim(-1.6,1.4);a.set_ylim(-1.5,1.5);a.legend(loc='lower right');save('log-branch',f,'主支arg∈(−π,π)，定义域排除非正实轴。单位圆在切线两岸保留小缺口。')
    f,a=base('上半圆围道：实轴向右，圆弧逆时针','Re z','Im z',True)
    R=2.2;t=np.linspace(0,np.pi,400);a.plot(R*np.cos(t),R*np.sin(t));a.plot([-R,R],[0,0]);arrow(a,(-.5,0),(.2,0));arrow(a,(R*np.cos(.65),R*np.sin(.65)),(R*np.cos(.85),R*np.sin(.85)));p=np.exp(1j*np.array([np.pi/4,3*np.pi/4]));a.plot(p.real,p.imag,'x',ms=9);a.text(.2,1.15,r'$1/(z^4+1)$');a.set_ylim(-.2,2.6);save('residue-contour',f,'f=1/(z⁴+1)，上半平面极点e^(iπ/4),e^(3iπ/4)，有限R2.2围道正向。')
    f,a=base('辐角原理：像曲线绕原点一圈','Re p(z)','Im p(z)',True)
    t=np.linspace(0,2*np.pi,2401);z=np.exp(1j*t);w=z**5+3*z+1;a.plot(w.real,w.imag);a.plot([0],[0],'+',ms=12)
    for j in [120,680,1300,1900]:arrow(a,(w[j].real,w[j].imag),(w[j+30].real,w[j+30].imag))
    save('argument-principle',f,'p(z)=z⁵+3z+1，z=e^(it)；Rouché：|z⁵+1|≤2<3，所以绕数1。')
    f,a=base('Cayley 变换：上半平面到单位圆盘','Re w','Im w',True)
    t=np.linspace(0,2*np.pi,600);a.plot(np.cos(t),np.sin(t),ls='--')
    for b in [.1,.25,.5,1,2,4]:
      z=np.linspace(-20,20,2500)+1j*b;w=(z-1j)/(z+1j);a.plot(w.real,w.imag,lw=.8)
    for b in [-4,-2,-1,-.5,0,.5,1,2,4]:
      z=b+1j*np.geomspace(.005,40,1200);w=(z-1j)/(z+1j);a.plot(w.real,w.imag,lw=.8)
    save('mobius-grid',f,'w=(z−i)/(z+i)，上半平面水平/竖直网格像；实轴边界对应单位圆但∞处用极限理解。')
    f,a=base('Poisson 核：总质量 1 的边界平均','角度 θ','归一化核')
    t=np.linspace(-np.pi,np.pi,1800)
    for r in [.2,.6,.85]:a.plot(t,(1-r*r)/(1-2*r*np.cos(t)+r*r)/(2*np.pi),label=f'r={r}')
    a.legend();save('poisson-kernel',f,'(1−r²)/(2π(1−2r cosθ+r²))，θ∈[−π,π]的积分1。')
    f,a=base('输运：沿 x=ξ exp(t) 的曲线保持函数值','x','t')
    t=np.linspace(0,1.8,400)
    for xi in [-.8,-.4,0,.4,.8]:a.plot(xi*np.exp(t),t,label=f'ξ={xi}')
    a.legend();save('characteristics',f,'u_t+xu_x=0的特征线x(t)=ξe^t，图中t竖直。')
    f,a=base('Sturm–Liouville 模式：空间频率与谱')
    x=np.linspace(0,1,500)
    for n in [1,2,3]:a.plot(x,np.sin(n*np.pi*x),label=f'n={n}，λ={n*n}π²')
    a.legend();save('sturm-modes',f,'−X″=λX，X0=X1=0，Xn=sin(nπx)。展示未归一化模式。')
    f,a=base('热方程：高频先衰减','x','u(x,t)')
    x=np.linspace(0,np.pi,600)
    for t in [0,.1,.4,1.0]:a.plot(x,np.exp(-t)*np.sin(x)+np.exp(-9*t)*np.sin(3*x)/3,label=f't={t}')
    a.legend();save('heat-modes',f,'κ1，区间(0,π)双端零值；u=e^(−t)sinx+(1/3)e^(−9t)sin3x。')
    f,a=base('热核：扩散、峰值下降与质量守恒','x','K(x,t)')
    x=np.linspace(-5,5,1000)
    for t in [.1,.5,1]:a.plot(x,np.exp(-x*x/(4*t))/np.sqrt(4*np.pi*t),label=f't={t}')
    a.legend();save('heat-kernel',f,'一维κ1热核，x∈[−5,5]；全实线质量1，图外尾部并未截断为零。')
    f,a=base('波动方程：过去影响锥','x','t',True)
    a.plot([-2,0,2],[0,2,0]);a.plot([-2,2],[0,0],lw=3);a.plot([0],[2],'o');a.text(.15,2,r'$(x_0,t_0)=(0,2)$');a.text(-1.2,-.35,'初始影响区间 [-2,2]');a.set_xlim(-3,3);a.set_ylim(-.6,2.7)
    save('wave-cone',f,'c1，观察点(0,2)，过去锥 |x|≤2−t,0≤t≤2。')
    f,a=base('圆环内的调和函数：对数项合法','x','y',True)
    x=np.linspace(-1.05,1.05,500);X,Y=np.meshgrid(x,x);R=np.sqrt(X*X+Y*Y);U=np.ma.masked_where((R<.3)|(R>1),np.log(np.maximum(R,1e-8))/np.log(.3));cs=a.contour(X,Y,U,levels=[.1,.3,.5,.7,.9]);a.clabel(cs,inline=True)
    for r in [.3,1]:a.add_patch(Circle((0,0),r,fill=False,ls='--'))
    save('annulus-harmonic',f,'.3<r<1，u=log r/log(.3)，内边界1外边界0；去掉中心奇点。')
    f,a=base('圆盘径向模态：Bessel 而非普通正弦','r','模式值')
    r=np.linspace(0,1,700)
    for n,j in enumerate(jn_zeros(0,3),1):a.plot(r,jv(0,j*r),label=f'n={n}, j_0n={j:.3f}')
    a.legend();save('bessel-modes',f,'J0(j0n r)，j0n为J0前三个正零点，单位圆盘径向Dirichlet模式。')
    f,a=base('Green 函数：点源处斜率跳跃','x',r'$G(x,\xi)$')
    x=np.linspace(0,1,1001)
    for xi in [.25,.5,.75]:a.plot(x,np.minimum(x,xi)*(1-np.maximum(x,xi)),label=f'ξ={xi}')
    a.legend();save('green-function',f,'−d²/dx²在(0,1)零边界Green函数min(x,ξ)(1−max(x,ξ))，斜率跳−1。')
    f,a=base('Burgers 稀疏波：特征速度填满 0 到 1','x','t')
    t=np.linspace(0,1.5,400)
    for v in np.linspace(0,1,9):a.plot(v*t,t,lw=.9)
    for x0 in [-.9,-.6,-.3]:a.plot(np.full_like(t,x0),t,ls='--')
    for x0 in [.3,.6,.9]:a.plot(x0+t,t,ls='--')
    a.text(-.8,1.65,'u=0');a.text(.4,1.65,'u=x/t');a.text(1.6,1.65,'u=1');a.set_ylim(0,1.9);save('burgers-fan',f,'uL0,uR1的熵解，扇内0≤x/t≤1；实线扇区特征线，虚线外侧平行特征线。')
    f,a=base('显式热格式：高频何时被放大','θ',r'$G(\theta)$')
    t=np.linspace(0,np.pi,700)
    for mu in [.25,.5,.65]:a.plot(t,1-4*mu*np.sin(t/2)**2,label=f'μ={mu}')
    a.axhline(1,ls='--');a.axhline(-1,ls='--');a.legend();save('heat-stability',f,'FTCS热方程放大因子1−4μsin²(θ/2)，稳定需0≤μ≤.5。')
    f,a=base('有限元帽函数：局部支集导致稀疏矩阵','x',r'$\phi_i(x)$')
    x=np.linspace(0,1,1001);N=5;h=1/N
    for i in range(1,N):a.plot(x,np.maximum(1-np.abs(x-i*h)/h,0),label=f'i={i}')
    a.legend();save('fem-hats',f,'区间均分5单元，4个内部节点的分段线性帽函数，端点均零。')
    # 三个跨科图示：课程依赖、常见收敛、Robin 边界谱。
    f,a=base('六科依赖图：实线为主要先修方向')
    a.set_axis_off();a.set_xlim(0,10);a.set_ylim(0,6)
    nodes={'微积分':(1.5,4.8),'数学分析':(5,4.8),'复变函数':(8.5,4.8),'线性代数':(1.5,1.4),'高等代数':(5,1.4),'数理方程':(8.5,1.4)}
    for p,q in [('微积分','数学分析'),('数学分析','复变函数'),('线性代数','高等代数'),('线性代数','数理方程'),('数学分析','数理方程'),('微积分','数理方程'),('复变函数','数理方程')]:
        x=np.array(nodes[p]);y=np.array(nodes[q]);d=(y-x)/np.linalg.norm(y-x)
        if (p,q)==('线性代数','数理方程'):
            a.annotate('',xy=(8.5,1.05),xytext=(1.5,1.05),arrowprops={'arrowstyle':'->','connectionstyle':'arc3,rad=.25','lw':1.4})
        else:
            arrow(a,x+.75*d,y-.75*d)
    for name,p in nodes.items():a.text(*p,name,ha='center',va='center',fontsize=14,bbox={'boxstyle':'round,pad=.5','facecolor':'none'})
    save('course-dependencies',f,'课程先修关系示意；可并行学习，箭头不代表全部依赖，高等代数对PDE部分谱理论也是补充。')
    f,a=base('有限测度空间：常见收敛关系')
    a.set_axis_off();a.set_xlim(0,10);a.set_ylim(0,6)
    nodes={'一致收敛':(1.4,4.7),'几乎处处收敛':(5,4.7),'依测度收敛':(8.5,2.5),'Lp 收敛':(2,1.3)}
    for p,q in [('一致收敛','几乎处处收敛'),('一致收敛','Lp 收敛'),('几乎处处收敛','依测度收敛'),('Lp 收敛','依测度收敛')]:
      x=np.array(nodes[p]);y=np.array(nodes[q]);d=(y-x)/np.linalg.norm(y-x);arrow(a,x+.8*d,y-.9*d)
    for label,p in nodes.items():a.text(*p,label,ha='center',va='center',bbox={'boxstyle':'round,pad=.4','facecolor':'none'})
    a.text(5,.05,'依测度收敛只保证存在几乎处处收敛子列，非整列。',ha='center');save('convergence-map',f,'假设底空间测度有限，1≤p<∞，比较差函数；无限测度时一致到Lp、几乎处处到依测度的箭头不能照搬；一致到依测度仍成立。')
    f,a=base('Robin 边界：最低特征值可以穿过零','α','边界参数 h')
    x=np.linspace(.02,3,600);a.plot(x,-x/np.tanh(x),label=r'$h=-\alpha\coth\alpha$（负谱）');a.axhline(-1,ls='--',label='零谱阈值 h=-1');a.set_ylim(-3.3,0);a.legend();save('robin-spectrum',f,'L1，X0=0,X′1+hX1=0；负特征值−α²对应h=−αcothα，范围h<−1。')
    (OUT/'图示参数清单.json').write_text(json.dumps(META,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-dir',type=Path)
    parser.add_argument('--only-helix',action='store_true',help='只生成 helix.svg，不改写图示参数清单')
    args=parser.parse_args();PREVIEW=args.preview_dir
    setup()
    if args.only_helix:
        generate_helix()
    else:
        generate()
    print(f'已生成 {len(META)} 幅本地 SVG：{OUT}')
