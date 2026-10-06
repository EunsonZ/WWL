#!/usr/bin/env python3
"""六科综合实验：精确算例、有限采样数值检查、网格误差三类证据分开记录。
运行：python 六科综合实验.py [--output REPORT.json]
依赖：numpy scipy sympy。不会下载数据；所有输入在代码中公开。
"""
from __future__ import annotations
import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Callable, Any
import numpy as np
import scipy
import sympy as sp
from scipy.integrate import quad
from scipy.linalg import expm
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
RESULTS: list[dict[str, Any]] = []
x,y,t,z = sp.symbols('x y t z', real=True)

def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

def exact_zero(expr: sp.Expr | sp.MatrixBase) -> None:
    if isinstance(expr, sp.MatrixBase):
        require(all(sp.simplify(v)==0 for v in expr), f'矩阵并非精确零：{expr}')
    else:
        require(sp.simplify(expr)==0, f'表达式并非精确零：{expr}')

def run(name: str, kind: str, fn: Callable[[],dict[str,Any]]) -> None:
    try:
        data=fn();RESULTS.append({'name':name,'kind':kind,'passed':True,'details':data})
    except Exception as exc:
        RESULTS.append({'name':name,'kind':kind,'passed':False,'error':f'{type(exc).__name__}: {exc}'})

def taylor_integral() -> dict:
    lim=sp.limit((sp.sin(x)-x+x**3/6)/x**5,x,0)
    val=sp.integrate(x*sp.log(1+x*x),(x,0,1))
    exact_zero(lim-sp.Rational(1,120));exact_zero(val-sp.log(2)+sp.Rational(1,2))
    return {'Taylor极限':str(lim),'积分':str(val)}

def quadrature() -> dict:
    ns=np.array([8,16,32,64]);trap=[];simpson=[]
    for n in ns:
        q=np.linspace(0,1,n+1);v=np.exp(q);h=1/n
        trap.append(abs(h*(v[0]/2+v[1:-1].sum()+v[-1]/2)-np.expm1(1)))
        simpson.append(abs(h/3*(v[0]+v[-1]+4*v[1:-1:2].sum()+2*v[2:-1:2].sum())-np.expm1(1)))
    require(np.allclose(np.array(trap[:-1])/trap[1:],4,rtol=.01),'梯形误差阶异常')
    require(np.allclose(np.array(simpson[:-1])/simpson[1:],16,rtol=.01),'Simpson误差阶异常')
    return {'n':ns.tolist(),'梯形绝对误差':trap,'Simpson绝对误差':simpson,'说明':'仅验证给定光滑函数及网格；不是通用误差定理证明'}

def jacobian_flux() -> dict:
    J=sp.Matrix([[sp.Rational(3,2),sp.Rational(7,10)],[sp.Rational(1,5),sp.Rational(6,5)]])
    exact_zero(J.det()-sp.Rational(83,50))
    v1=sp.Matrix([1,0,-1]);v2=sp.Matrix([0,1,-1]);exact_zero(v1.cross(v2)-sp.ones(3,1))
    div=3;vol=4*sp.pi/3;exact_zero(div*vol-4*sp.pi)
    return {'Jacobian':str(J.det()),'法向叉积':str(v1.cross(v2)),'单位球通量':str(div*vol)}

def projection() -> dict:
    G=sp.Matrix([[1,sp.Rational(1,2)],[sp.Rational(1,2),sp.Rational(1,3)]])
    c=G.inv()*sp.Matrix([sp.Rational(1,3),sp.Rational(1,4)])
    exact_zero(c-sp.Matrix([-sp.Rational(1,6),1]))
    err=sp.integrate((x*x-c[0]-c[1]*x)**2,(x,0,1));exact_zero(err-sp.Rational(1,180))
    H=G+sp.diag(0,1);d=H.inv()*sp.Matrix([sp.Rational(1,4),sp.Rational(6,5)])
    exact_zero(d-sp.Matrix([-sp.Rational(16,65),sp.Rational(129,130)]))
    return {'L2投影x²系数':list(map(str,c)),'误差平方':str(err),'H1投影x³系数':list(map(str,d))}

def convergence_integral() -> dict:
    vals=[]
    for n in [2,10,100,1000]:
        value=np.log1p(n*n)/(2*n)
        require(value>=0,'积分应非负');vals.append(value)
    n=sp.symbols('n',positive=True)
    exact_zero(sp.integrate(n*x/(1+n*n*x*x),(x,0,1))-sp.log(n*n+1)/(2*n))
    return {'n':[2,10,100,1000],'积分':vals,'尖峰n乘区间长度':1,'说明':'极限交换的证明在正文；有限样本只作交叉检查'}

def fubini_counterexample() -> dict:
    f=(x*x-y*y)/(x*x+y*y)**2
    # 对每个正参数，用原函数端点计算避免在原点未定义处直接代入。
    exact_zero(sp.diff(y/(x*x+y*y),y)-f)
    exact_zero(sp.diff(-x/(x*x+y*y),x)-f)
    a=sp.integrate(1/(1+x*x),(x,0,1));b=-sp.integrate(1/(1+y*y),(y,0,1))
    exact_zero(a-sp.pi/4);exact_zero(b+sp.pi/4)
    return {'先y后x':str(a),'先x后y':str(b),'解释':'非绝对可积；不能据有限累次积分推断Fubini条件'}

def parameter_integral() -> dict:
    tt=sp.symbols('a',positive=True)
    exact_zero(sp.diff(1/(1+tt*tt),tt)+2*tt/(1+tt*tt)**2)
    errors=[]
    for a in [.5,1,2]:
        v=quad(lambda q:q*np.exp(-a*q)*np.sin(q),0,np.inf,epsabs=1e-11)[0]
        errors.append(abs(v-2*a/(1+a*a)**2))
    require(max(errors)<1e-9,'含参积分核验失败')
    return {'参数':[.5,1,2],'绝对误差':errors}

def least_squares_qr() -> dict:
    A=np.array([[1.,0],[1,1],[1,2]]);b=np.array([1.,0,1])
    Q,R=np.linalg.qr(A);c=np.linalg.solve(R,Q.T@b);r=b-A@c
    require(np.allclose(c,[2/3,0]),'最小二乘系数异常')
    require(np.linalg.norm(A.T@r)<1e-12,'残差不正交')
    require(np.allclose(Q.T@Q,np.eye(2)),'Q列不正交')
    return {'系数':c.tolist(),'残差平方':float(r@r),'正交残差':float(np.linalg.norm(A.T@r))}

def svd() -> dict:
    A=np.diag([4.,2,1]);B=np.diag([4.,0,0])
    require(np.isclose(np.linalg.norm(A-B,'fro'),np.sqrt(5)),'Frobenius尾值失败')
    require(np.isclose(np.linalg.norm(A-B,2),2),'谱范数尾值失败')
    vals=[float(np.linalg.norm(A-np.diag([q,0,0]),2)) for q in [2,3,4,5,6]]
    require(np.allclose(vals,2),'谱范数最优不唯一示例失败')
    return {'Frobenius误差':float(np.sqrt(5)),'谱误差不同最优解':vals}

def conditioning() -> dict:
    A=np.diag([1.,1e-6]);b=np.array([1.,0]);db=np.array([0.,1e-6])
    exact=np.linalg.solve(A,b);pert=np.linalg.solve(A,b+db)
    amplification=np.linalg.norm(pert-exact)/np.linalg.norm(db)
    require(np.isclose(amplification,1e6),'条件数放大异常')
    return {'条件数':float(np.linalg.cond(A)),'实际误差放大':float(amplification)}

def schur() -> dict:
    A=sp.Matrix([[2,0],[0,3]]);B=sp.Matrix([[1],[2]]);D=sp.Matrix([[4]])
    M=A.row_join(B).col_join(B.T.row_join(D));S=D-B.T*A.inv()*B
    exact_zero(M.det()-A.det()*S.det())
    xx=sp.Matrix([x,y]);yy=sp.Matrix([t]);zz=xx.col_join(yy);v=xx+A.inv()*B*yy
    exact_zero((zz.T*M*zz-v.T*A*v-yy.T*S*yy)[0])
    return {'Schur补':str(S[0]),'块行列式':str(M.det())}

def jordan() -> dict:
    A=sp.Matrix([[1,1,0],[0,1,0],[0,0,2]]);P2=(A-sp.eye(3))**2;P1=sp.eye(3)-P2
    exact_zero(P2*P2-P2);exact_zero(P1*P2);exact_zero((A-sp.eye(3))**2*(A-2*sp.eye(3)))
    v=sp.Matrix([0,1,1]);C=v.row_join(A*v).row_join(A*A*v)
    exact_zero(C.det()+1)
    I=sp.eye(3);expected=sp.exp(t)*(I-P2+t*(A-I)*P1)+sp.exp(2*t)*P2
    exact_zero(sp.diff(expected,t)-A*expected);exact_zero(expected.subs(t,0)-I)
    return {'循环基行列式':str(C.det()),'谱投影P2':str(P2),'矩阵指数':'初值和ODE均精确满足'}

def smith_resultant() -> dict:
    from sympy.matrices.normalforms import smith_normal_form
    from sympy.polys.domains import QQ
    M=sp.Matrix([[t,1],[0,t]]);S=smith_normal_form(M,domain=QQ.poly_ring(t))
    require(sp.expand(S[0,0]) in (1,-1),'首因子应为单位')
    require(sp.expand(S[1,1]) in (t*t,-t*t),'末因子应相伴于t²')
    a,b=sp.symbols('a b');r=sp.resultant(x*x-a,x-b,x);exact_zero(r-(b*b-a))
    return {'Smith矩阵含单位符号':str(S),'结果式':str(r)}

def jordan_nullities() -> dict:
    N=sp.zeros(5);N[0,1]=N[1,2]=N[3,4]=1
    nullities=[5-(N**j).rank() for j in [1,2,3]]
    require(nullities==[2,4,5],'核维数应为2,4,5')
    return {'核维数':nullities,'块大小':[3,2]}

def polynomial_field() -> dict:
    rem=sp.rem((x+1)*(1-x)/2,x*x+1,x);exact_zero(rem-1)
    A=sp.Matrix([[1,2],[0,3]]);B=sp.Matrix([[4,1],[0,5]])
    L=sp.kronecker_product(sp.eye(2),A)-sp.kronecker_product(B.T,sp.eye(2))
    require(L.det()!=0,'谱不相交应使Sylvester算子可逆')
    return {'多项式模逆验证':str(rem),'Sylvester行列式':str(L.det())}

def residue() -> dict:
    zz=sp.symbols('z');r=sp.residue(1/(zz*zz+1)**2,zz,sp.I)
    exact_zero(2*sp.pi*sp.I*r-sp.pi/2)
    r2=sp.residue(sp.exp(zz)/(zz-1)**3,zz,1);exact_zero(r2-sp.E/2)
    return {'二阶极点留数':str(r),'实积分':str(sp.pi/2),'Cauchy积分':str(sp.pi*sp.I*sp.E)}

def contour() -> dict:
    n=8192;theta=np.arange(n)*2*np.pi/n;zz=np.exp(1j*theta)
    # f(z)=z^5+3z+1 在单位圆无零点。周期梯形求辐角原理积分。
    f=zz**5+3*zz+1;fp=5*zz**4+3
    count=np.mean(fp*zz/f)
    require(abs(count-1)<1e-10,'围道计数数值核验失败')
    return {'采样点数':n,'零点计数近似':{'real':float(count.real),'imag':float(count.imag)},'说明':'Rouché提供严格计数；离散积分作独立核验'}

def poisson_kernel() -> dict:
    errors=[]
    for r in [.2,.6,.85]:
        v=quad(lambda q:(1-r*r)/(1-2*r*np.cos(q)+r*r)/(2*np.pi),-np.pi,np.pi,epsabs=1e-11)[0]
        errors.append(abs(v-1))
    require(max(errors)<1e-10,'Poisson核质量失败')
    exact_zero(sp.diff(x*x-y*y,x,2)+sp.diff(x*x-y*y,y,2))
    return {'半径':[.2,.6,.85],'质量误差':errors,'调和模式':'x²−y²'}

def fourier() -> dict:
    vals={}
    for m,n in [(1,1),(1,2),(2,3)]:
        val=sp.integrate(sp.sin(m*x)*sp.sin(n*x),(x,0,sp.pi))
        exact_zero(val-(sp.pi/2 if m==n else 0));vals[f'{m},{n}']=str(val)
    return {'正交积分':vals}

def heat_wave() -> dict:
    u=sp.exp(-t)*sp.sin(x)+sp.exp(-9*t)*sp.sin(3*x)/3
    exact_zero(sp.diff(u,t)-sp.diff(u,x,2));exact_zero(u.subs(x,0));exact_zero(u.subs(x,sp.pi))
    forced=t*sp.exp(-t)*sp.sin(x)
    exact_zero(sp.diff(forced,t)-sp.diff(forced,x,2)-sp.exp(-t)*sp.sin(x))
    wave=sp.cos(2*t)*sp.sin(2*x)
    exact_zero(sp.diff(wave,t,2)-sp.diff(wave,x,2))
    energy=sp.integrate((sp.diff(wave,t)**2+sp.diff(wave,x)**2)/2,(x,0,sp.pi))
    exact_zero(energy-sp.pi)
    return {'热方程残差':0,'受迫热方程残差':0,'波能量':str(sp.simplify(energy))}

def heat_kernel() -> dict:
    masses=[];moments=[]
    for a in [.1,.5,1.]:
        K=lambda q:np.exp(-q*q/(4*a))/np.sqrt(4*np.pi*a)
        masses.append(quad(K,-np.inf,np.inf)[0]);moments.append(quad(lambda q:q*q*K(q),-np.inf,np.inf)[0])
    require(np.allclose(masses,1,atol=1e-10),'热核质量错误')
    require(np.allclose(moments,[.2,1,2],atol=1e-10),'热核方差错误')
    return {'t':[.1,.5,1.],'质量':masses,'二阶矩':moments}

def green() -> dict:
    xi=sp.symbols('xi',positive=True);left=x*(1-xi);right=xi*(1-x)
    exact_zero(left.subs(x,xi)-right.subs(x,xi));jump=sp.diff(right,x)-sp.diff(left,x);exact_zero(jump+1)
    u=sp.integrate(y*(1-x),(y,0,x))+sp.integrate(x*(1-y),(y,x,1))
    exact_zero(u-x*(1-x)/2)
    return {'导数跳跃':str(jump),'单位载荷解':str(sp.factor(u))}

def robin() -> dict:
    alpha=brentq(lambda a:a/np.tanh(a)-2,1e-5,4)
    residual=alpha*np.cosh(alpha)-2*np.sinh(alpha)
    require(abs(residual)<1e-10,'Robin负特征值边界残差异常')
    return {'L':1,'h':-2,'alpha':float(alpha),'特征值':float(-alpha*alpha),'边界残差':float(residual)}

def geometry() -> dict:
    rr=sp.Matrix([sp.cos(t),sp.sin(t),t/3]);v=sp.diff(rr,t);a=sp.diff(v,t);j=sp.diff(a,t)
    cross=v.cross(a);curv=sp.sqrt(sp.simplify(cross.dot(cross)))/sp.sqrt(sp.simplify(v.dot(v)))**3
    torsion=sp.simplify(cross.dot(j)/cross.dot(cross));exact_zero(curv-sp.Rational(9,10));exact_zero(torsion-sp.Rational(3,10))
    return {'螺线曲率':str(sp.simplify(curv)),'螺线挠率':str(torsion)}

def variation() -> dict:
    u=sp.sinh(x)/sp.sinh(1);exact_zero(sp.diff(u,x,2)-u);exact_zero(u.subs(x,0));exact_zero(u.subs(x,1)-1)
    return {'极小函数':str(u),'Euler–Lagrange残差':0,'解释':'正定二次泛函的差值证明提供全局最小性'}

def fem() -> dict:
    ns=[4,8,16,32];energy=[];l2=[];nodeerrors=[]
    q,w=np.polynomial.legendre.leggauss(4)
    for n in ns:
        h=1/n;K=(np.diag(np.full(n-1,2.))+np.diag(np.full(n-2,-1.),1)+np.diag(np.full(n-2,-1.),-1))/h
        c=np.r_[0,np.linalg.solve(K,np.full(n-1,h)),0];nodes=np.linspace(0,1,n+1)
        nodeerrors.append(float(np.max(np.abs(c-nodes*(1-nodes)/2))))
        e1=e0=0.
        for i in range(n):
            xx=nodes[i]+(q+1)*h/2;uh=c[i]+(xx-nodes[i])*(c[i+1]-c[i])/h
            e0+=float(np.sum(w*(xx*(1-xx)/2-uh)**2)*h/2)
            e1+=float(np.sum(w*((1-2*xx)/2-(c[i+1]-c[i])/h)**2)*h/2)
        energy.append(np.sqrt(e1));l2.append(np.sqrt(e0))
        require(np.isclose(np.sqrt(e1),h/np.sqrt(12),rtol=1e-10),'有限元能量误差错误')
        require(np.isclose(np.sqrt(e0),h*h/np.sqrt(120),rtol=1e-9),'有限元L2误差错误')
    return {'单元数':ns,'能量误差':energy,'L2误差':l2,'节点误差':nodeerrors,'说明':'四点Gauss精确覆盖本例误差多项式积分；浮点仍有舍入'}

def stability() -> dict:
    theta=np.linspace(0,np.pi,2049);out={}
    for mu in [.25,.5,.65]:out[str(mu)]=float(np.max(np.abs(1-4*mu*np.sin(theta/2)**2)))
    require(out['0.25']<=1+1e-14 and out['0.5']<=1+1e-14,'稳定区检查失败')
    require(out['0.65']>1,'应存在放大模态')
    return {'最大放大因子':out,'说明':'理论条件见正文；有限频率采样不替代一般证明'}

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'90-资源/维护/综合实验验收.json');args=parser.parse_args()
    groups=[('Taylor极限与积分','精确算例',taylor_integral),('复合积分误差阶','数值检查',quadrature),('Jacobian与法向通量','精确算例',jacobian_flux),('不同内积的投影','精确算例',projection),('收敛与尖峰','混合检查',convergence_integral),('Fubini反例','精确算例',fubini_counterexample),('含参积分','混合检查',parameter_integral),('QR与最小二乘','数值检查',least_squares_qr),('SVD范数与唯一性','数值检查',svd),('条件数放大','数值检查',conditioning),('Schur配方','精确算例',schur),('Jordan与谱投影','精确算例',jordan),('Smith与结果式','精确算例',smith_resultant),('核维数与Jordan块','精确算例',jordan_nullities),('模逆与Sylvester算子','精确算例',polynomial_field),('留数与Cauchy积分','精确算例',residue),('围道零点计数','数值检查',contour),('Poisson核与调和模式','混合检查',poisson_kernel),('Fourier正交','精确算例',fourier),('热波精确解与能量','精确算例',heat_wave),('热核质量与二阶矩','数值检查',heat_kernel),('Green跳跃与响应','精确算例',green),('Robin负谱','数值检查',robin),('曲率与挠率','精确算例',geometry),('变分方程','精确算例',variation),('有限元网格误差','数值检查',fem),('显式热格式稳定性','数值检查',stability)]
    for name,kind,fn in groups:run(name,kind,fn)
    report={'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'sympy':sp.__version__},'total':len(RESULTS),'passed':sum(r['passed'] for r in RESULTS),'results':RESULTS,'limits':'精确算例只验证这些表达式；有限数值试验不是定理证明。'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"综合实验：{report['passed']}/{report['total']} 通过。报告：{args.output}")
    for r in RESULTS:
        if not r['passed']:print(r['name'],r['error'],file=sys.stderr)
    return 0 if report['passed']==report['total'] else 1

if __name__=='__main__':
    raise SystemExit(main())
