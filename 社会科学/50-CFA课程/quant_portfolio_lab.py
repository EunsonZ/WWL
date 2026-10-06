"""Synthetic cash-flow, regression and two-asset lab. No market estimates."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def finite(values):
    result = tuple(float(x) for x in values)
    if not result or not all(math.isfinite(x) for x in result):
        raise ValueError('nonempty finite numeric values required')
    return result


def twr(starts, ends):
    starts, ends = finite(starts), finite(ends)
    if len(starts) != len(ends) or any(x <= 0 for x in starts) or any(x < 0 for x in ends):
        raise ValueError('matching positive starts and nonnegative ends required')
    result=math.prod(b/a for a,b in zip(starts,ends))-1
    if not math.isfinite(result): raise ValueError('nonfinite wealth factor')
    return result


def npv(rate, times, flows):
    times, flows = finite(times), finite(flows)
    if len(times)!=len(flows) or times[0]!=0 or any(t<0 for t in times) or any(a>=b for a,b in zip(times,times[1:])):
        raise ValueError('strictly increasing times in years beginning at zero required')
    if not math.isfinite(rate) or rate<=-1:
        raise ValueError('effective annual rate must exceed -1')
    try:
        value=math.fsum(c*math.exp(-t*math.log1p(rate)) for t,c in zip(times,flows))
    except OverflowError as exc:
        raise ValueError('discount overflow; choose safer bracket') from exc
    if not math.isfinite(value): raise ValueError('nonfinite discounted sum')
    return value


def irr_bracket(times, flows, lo, hi, *, tol=1e-12, iterations=200):
    """One root in a supplied sign-changing bracket; no all-root claim."""
    if not math.isfinite(lo) or not math.isfinite(hi) or lo>=hi or not math.isfinite(tol) or tol<=0 or not isinstance(iterations,int) or isinstance(iterations,bool) or iterations<1:
        raise ValueError('ordered finite bracket, positive tolerance and iterations required')
    a,b=npv(lo,times,flows),npv(hi,times,flows)
    if a==0: return lo
    if b==0: return hi
    if (a>0)==(b>0): raise ValueError('no endpoint sign change; roots may still exist')
    for _ in range(iterations):
        mid=lo+(hi-lo)/2; c=npv(mid,times,flows)
        if c==0 or hi-lo<=tol*max(1,abs(mid)): return mid
        if (a>0)==(c>0): lo,a=mid,c
        else: hi=mid
    raise RuntimeError('bisection did not converge')


def regression(x,y):
    x,y=finite(x),finite(y)
    if len(x)!=len(y) or len(x)<3: raise ValueError('three or more paired observations required')
    n=len(x); xb=math.fsum(x)/n; yb=math.fsum(y)/n
    sxx=math.fsum((v-xb)**2 for v in x)
    if sxx<=0: raise ValueError('constant predictor; slope not identified')
    slope=math.fsum((a-xb)*(b-yb) for a,b in zip(x,y))/sxx
    intercept=yb-slope*xb
    residuals=[b-intercept-slope*a for a,b in zip(x,y)]
    sse=math.fsum(e*e for e in residuals); sst=math.fsum((b-yb)**2 for b in y)
    if sst<=0 or sse<=1e-28*max(1,sst): raise ValueError('constant response or effectively perfect fit; inference degenerates')
    mse=sse/(n-2); se=math.sqrt(mse/sxx)
    return dict(intercept=intercept,slope=slope,residuals=residuals,sse=sse,ssr=sst-sse,sst=sst,mse=mse,se_slope=se,t=slope/se,f=(sst-sse)/mse,r2=1-sse/sst)


MU=(.10,.06)
COV=((.04,.004),(.004,.01))
RF=.02


def portfolio(w,mu=MU,cov=COV):
    w=float(w); mu=finite(mu)
    if len(mu)!=2 or len(cov)!=2 or any(len(row)!=2 for row in cov) or not math.isfinite(w): raise ValueError('two-asset inputs required')
    a,c=finite(cov[0]); d,b=finite(cov[1])
    if a<0 or b<0 or c!=d: raise ValueError('symmetric positive semidefinite covariance required')
    if (a==0 or b==0) and c!=0: raise ValueError('zero variance requires zero covariance')
    if a>0 and b>0 and abs(c/math.sqrt(a)/math.sqrt(b))>1+1e-14: raise ValueError('invalid covariance correlation')
    variance=w*w*a+(1-w)**2*b+2*w*(1-w)*c
    if not math.isfinite(variance) or variance < -1e-14: raise ValueError('nonfinite or negative variance')
    return w*mu[0]+(1-w)*mu[1],math.sqrt(max(0,variance))


def constrained_minimum(target,upper=.6):
    """Fixed MU/COV, no shorts, return lower bound and A upper bound."""
    if not math.isfinite(target) or not math.isfinite(upper) or not 0<=upper<=1: raise ValueError('finite target and upper in [0,1] required')
    lower=max(0,(target-MU[1])/(MU[0]-MU[1]))
    if lower>upper+1e-14: raise ValueError('infeasible target')
    gmv=(COV[1][1]-COV[0][1])/(COV[0][0]+COV[1][1]-2*COV[0][1])
    w=min(upper,max(lower,gmv)); m,s=portfolio(w)
    return dict(w_a=w,mean=m,sigma=s)


def example():
    net=twr((100,209,157),(109,187,179))
    return dict(net_twr=net,net_twr_annual=(1+net)**.5-1,gross_twr=twr((100,209,157),(110,188.1,180.55)),mwr=irr_bracket((0,.5,1,2),(-100,-100,30,179),-.5,.5),regression=regression((-2,-1,0,1,2,3),(-1,0,0,2,3,3)),gmv=constrained_minimum(.06,1),target8=constrained_minimum(.08))


def figures(directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='wwl-quant-20260917'
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    ws=[i/1000 for i in range(1001)]; points=[portfolio(w) for w in ws]
    gmv=constrained_minimum(.06,1); tangent=1/3
    mt,st=portfolio(tangent)
    fig,ax=plt.subplots(figsize=(7.2,4.5))
    ax.plot([s*100 for m,s in points],[m*100 for m,s in points],label='Two risky assets; 0 <= w_A <= 1')
    efficient=[portfolio(w) for w in ws if w>=gmv['w_a']]
    ax.plot([s*100 for m,s in efficient],[m*100 for m,s in efficient],lw=3,label='Efficient branch')
    ys=[i/100 for i in range(101)]
    ax.plot([y*st*100 for y in ys],[(RF+y*(mt-RF))*100 for y in ys],'--',label='Tangency CAL; no borrowing')
    for name,w in [('GMV',gmv['w_a']),('Target 8%',.5),('Tangency',tangent)]:
        m,s=portfolio(w); ax.scatter([s*100],[m*100]); ax.annotate(name,(s*100,m*100),xytext=(5,5),textcoords='offset points')
    ax.set(xlabel='Annual standard deviation (%)',ylabel='Model expected annual return (%)',title='Synthetic inputs; no costs, no future guarantee')
    ax.legend(fontsize=8); ax.grid(alpha=.25); fig.tight_layout()
    path=directory/'quant-frontier.svg'; fig.savefig(path,metadata={'Date':None}); plt.close(fig)
    path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines()).rstrip('\n') + '\n', encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--figures',type=Path); args=parser.parse_args()
    print(json.dumps(example(),ensure_ascii=False,indent=2))
    if args.figures: figures(args.figures)
