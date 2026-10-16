---
type: code
stage: 0
aliases: []
sources: []
prerequisites: []
---
# 连续与期限复算源码

源码为真源，返回 [[社会科学/30-金融市场与风险/40-金融理论/80-实践/03-连续定价与期限综合/README|实践说明]]。

<!-- code-sync: 社会科学/30-金融市场与风险/40-金融理论/80-实践/03-连续定价与期限综合/continuous_term.py -->

```python
#!/usr/bin/env python3
"""Closed-form GBM vs deterministic integrals/FD; exact separate finite bond worlds. No market data."""
import argparse
from fractions import Fraction as F
import json
import math
from pathlib import Path
from html import escape


def phi(x): return math.exp(-x*x/2)/math.sqrt(2*math.pi)
def Phi(x): return math.erfc(-x/math.sqrt(2))/2


def call(s, k, r, sigma, tau):
    if s <= 0 or k <= 0 or sigma <= 0 or tau <= 0:
        raise ValueError('call formula requires S,K,sigma,tau strictly positive')
    d1=(math.log(s/k)+(r+sigma*sigma/2)*tau)/(sigma*math.sqrt(tau))
    d2=d1-sigma*math.sqrt(tau)
    price=s*Phi(d1)-k*math.exp(-r*tau)*Phi(d2)
    cash=-k*math.exp(-r*tau)*Phi(d2)
    delta=Phi(d1)
    gamma=phi(d1)/(s*sigma*math.sqrt(tau))
    theta=-s*sigma*phi(d1)/(2*math.sqrt(tau))-r*k*math.exp(-r*tau)*Phi(d2)
    residual=theta+sigma*sigma*s*s*gamma/2+r*s*delta-r*price
    assert abs(price-(delta*s+cash)) < 1e-10*max(s,1)
    assert abs(residual) < 1e-10*max(s,1)
    return dict(price=price,d1=d1,d2=d2,delta=delta,current_bank_cash=cash,
                gamma=gamma,calendar_theta=theta,analytic_PDE_residual=residual)


def simpson(fn, lo, hi, n):
    if hi <= lo: return 0.0
    h=(hi-lo)/n
    return h/3*(fn(lo)+fn(hi)+math.fsum((4 if i%2 else 2)*fn(lo+i*h) for i in range(1,n)))


def continuous(data):
    s,k,r,sigma,tau=[float(data[key]) for key in ['spot','strike','rate','sigma','years']]
    mus=[float(v) for v in data['physical_drifts']]
    n=data['simpson_panels']
    if not isinstance(n,int) or n<256 or n>65536 or n%2:
        raise ValueError('Simpson panels must be an even integer in [256,65536]')
    if not all(math.isfinite(v) for v in [s,k,r,sigma,tau]+mus) or not mus:
        raise ValueError('finite model inputs and at least one drift required')
    if s<=0 or k<=0 or sigma<=0 or tau<=0: raise ValueError('S,K,sigma,tau must be positive')
    # Numeric audit bounds, not restrictions of the mathematical theorem.
    if abs(r*tau)>2 or sigma*math.sqrt(tau)>3 or max(abs((mu-r)/sigma)*math.sqrt(tau) for mu in mus)>6:
        raise ValueError('outside declared deterministic-quadrature audit range')
    hs=float(data['fd_relative_spot_step']);ht=float(data['fd_relative_time_step'])
    if not (1e-5<=hs<=1e-3 and 1e-5<=ht<=1e-3): raise ValueError('FD relative steps require [1e-5,1e-3]')
    c=call(s,k,r,sigma,tau)
    root=math.sqrt(tau)
    lower_Q=(math.log(k/s)-(r-sigma*sigma/2)*tau)/(sigma*root)
    limit_Q=10+sigma*root
    def q_integrand(z):
        payoff=max(s*math.exp((r-sigma*sigma/2)*tau+sigma*root*z)-k,0)
        return math.exp(-r*tau)*payoff*phi(z)
    q_integral=simpson(q_integrand,max(-limit_Q,lower_Q),limit_Q,n)
    representations=[]
    for mu in mus:
        lam=(mu-r)/sigma
        limit=10+abs(lam)*root+sigma*root
        lower_P=(math.log(k/s)-(mu-sigma*sigma/2)*tau)/(sigma*root)
        def density(z): return math.exp(-lam*root*z-lam*lam*tau/2)
        def gross(z): return math.exp((mu-sigma*sigma/2)*tau+sigma*root*z)
        def integrand(z): return math.exp(-r*tau)*density(z)*max(s*gross(z)-k,0)*phi(z)
        p_integral=simpson(integrand,max(-limit,lower_P),limit,n)
        z_mean=simpson(lambda z:density(z)*phi(z),-limit,limit,n)
        mR=simpson(lambda z:math.exp(-r*tau)*density(z)*gross(z)*phi(z),-limit,limit,n)
        expected_gross=math.exp(mu*tau)
        covariance=1-math.exp((mu-r)*tau)
        premium=expected_gross-math.exp(r*tau)
        assert abs(p_integral-c['price'])<1e-7*max(1,s/100)
        assert abs(z_mean-1)<1e-10 and abs(mR-1)<1e-10
        assert abs(premium+covariance/math.exp(-r*tau))<1e-12
        representations.append(dict(mu=mu,lambda_value=lam,call_via_P_m=p_integral,
            abs_price_error=abs(p_integral-c['price']),density_mean=z_mean,normalized_stock_price=mR,
            m_at_W_zero=math.exp(-r*tau-lam*lam*tau/2),expected_stock_gross=expected_gross,
            stock_excess_expected_gross=premium,covariance_m_stock_gross=covariance,
            wrong_positive_density_normalized_stock_price=math.exp(2*(mu-r)*tau),
            integration_range=[-limit,limit],payoff_threshold=lower_P))
    assert abs(q_integral-c['price'])<1e-7*max(1,s/100)
    fd=[]
    for spot in [s*0.8,s,s*1.2]:
        ds=hs*spot;dt=ht*tau
        center=call(spot,k,r,sigma,tau)
        plus=call(spot+ds,k,r,sigma,tau)['price'];minus=call(spot-ds,k,r,sigma,tau)['price']
        delta=(plus-minus)/(2*ds)
        gamma=(plus-2*center['price']+minus)/(ds*ds)
        theta=(call(spot,k,r,sigma,tau-dt)['price']-call(spot,k,r,sigma,tau+dt)['price'])/(2*dt)
        residual=theta+sigma*sigma*spot*spot*gamma/2+r*spot*delta-r*center['price']
        assert abs(delta-center['delta'])<2e-6
        assert abs(residual)<1e-4*max(1,s/100)
        fd.append(dict(spot=spot,spot_step=ds,time_step=dt,delta=delta,gamma=gamma,
                       theta=theta,PDE_residual=residual,delta_abs_error=abs(delta-center['delta'])))
    static=[]
    for st in data['static_terminal_spots']:
        st=float(st)
        if st<0 or not math.isfinite(st): raise ValueError('terminal stress spots must be finite and nonnegative')
        wealth=c['delta']*st+c['current_bank_cash']*math.exp(r*tau)
        payoff=max(st-k,0)
        static.append(dict(terminal_spot=st,wealth=wealth,call_payoff=payoff,wealth_minus_payoff=wealth-payoff))
    curves=[]
    for i in range(101):
        spot=k*(0.5+i/100)
        curves.append(dict(spot=spot,call=call(spot,k,r,sigma,tau)['price'],
                           terminal_payoff=max(spot-k,0),discounted_strike_lower=max(spot-k*math.exp(-r*tau),0)))
    return dict(parameters=dict(spot=s,strike=k,rate=r,sigma=sigma,years=tau,simpson_panels=n),closed_form=c,
                Q_quadrature=dict(value=q_integral,abs_error=abs(q_integral-c['price']),integration_range=[-limit_Q,limit_Q],payoff_threshold=lower_Q),
                P_representations=representations,finite_difference=fd,static_initial_delta_stress=static,price_curve=curves)


def dot(a,b):return sum((x*y for x,y in zip(a,b)),F(0))


def term(data):
    r0=F(data['bank_gross_01']);short=[F(x) for x in data['short_gross_12']]
    d01=F(data['discount_01']);d02=F(data['discount_02'])
    if len(short)!=2 or not 0<short[0]<short[1] or r0<=0 or d02<=0:
        raise ValueError('positive bank, two ordered positive short gross returns and positive D02 required')
    if d01!=1/r0: raise ValueError('D01 must match the included bank account')
    next_prices=[1/x for x in short]
    piH=(d01*next_prices[0]-d02)/(next_prices[0]-next_prices[1])
    pi=[d01-piH,piH]
    if any(x<=0 for x in pi):raise ValueError('observed bond prices require strictly positive state prices')
    q=[r0*x for x in pi]
    assert sum(q)==1 and dot(pi,[r0,r0])==1 and dot(pi,next_prices)==d02
    bank2=[r0*x for x in short];pi2=[qi/bi for qi,bi in zip(q,bank2)]
    assert sum(pi2)==d02 and dot(pi2,bank2)==1
    fgross=d01/d02
    q_short=dot(q,short)
    jensen=fgross-q_short
    assert jensen<=0 and fgross==1/dot(q,next_prices)
    returns=[x/d02 for x in next_prices]
    assert dot(q,returns)==r0
    hz=-1/(next_prices[0]-next_prices[1]);hb=-hz*next_prices[0]/r0
    x_pay=[hb*r0+hz*x for x in next_prices]
    assert x_pay==[0,1] and hb+hz*d02==pi[1]
    worlds=[]
    if not data['physical_high_probabilities']:raise ValueError('at least one physical world required')
    for ph in [F(x) for x in data['physical_high_probabilities']]:
        if not 0<ph<1:raise ValueError('physical high probabilities must be interior')
        p=[1-ph,ph];m=[x/prob for x,prob in zip(pi,p)]
        eshort=dot(p,short);er=dot(p,returns);em=dot(p,m)
        covariance=dot(p,[ms*rs for ms,rs in zip(m,returns)])-em*er
        premium=er-r0;measure=q_short-eshort;gap=fgross-eshort
        assert em==d01 and dot(p,[ms*rs for ms,rs in zip(m,returns)])==1
        assert premium==-covariance/em and gap==jensen+measure
        worlds.append(dict(P_high=ph,m=m,expected_short_gross=eshort,expected_short_net=eshort-1,
            expected_bond_holding_gross=er,bond_expected_excess_gross=premium,covariance_m_bond_return=covariance,
            forward_minus_expected_net_short=gap,measure_difference=measure,jensen_component=jensen))
    cf=[F(x) for x in data['finite_cashflows']];ys=[F(x) for x in data['flat_annual_yields']]
    if not cf or any(x<0 for x in cf) or not any(cf) or len(ys)!=2 or not -1<ys[0]<ys[1]:
        raise ValueError('finite nonnegative cashflows with one positive and ordered yields > -1 required')
    flat=[]
    for y in ys:
        denominators=[(1+y)**(i+1) for i in range(len(cf))]
        factors=[1/x for x in denominators]
        price=dot(cf,factors)
        derivative=-sum((F(i+1)*v/(1+y)**(i+2) for i,v in enumerate(cf)),F(0))
        assert derivative<0
        flat.append(dict(yield_rate=y,denominators=denominators,discount_factors=factors,price=price,derivative=derivative))
    assert flat[1]['price']<flat[0]['price']
    assert all(a<b for a,b in zip(flat[0]['denominators'],flat[1]['denominators']))
    return dict(R0=r0,short_gross=short,D01=d01,D02=d02,payoff_matrix=[[r0,next_prices[0]],[r0,next_prices[1]]],
        prices=[F(1),d02],state_prices_01=pi,Q=q,bank_terminal=bank2,state_prices_02=pi2,
        spot_annual=[float(1/d01-1),math.sqrt(float(1/d02))-1],
        spot_continuous=[-math.log(float(d01)),-math.log(float(d02))/2],
        forward_gross=fgross,forward_net=fgross-1,forward_positions=dict(short_ZCB1=-1,long_ZCB2=fgross),
        forward_cashflows=[F(0),F(-1),fgross],Q_expected_short_gross=q_short,bond_holding_gross=returns,
        x_replication=dict(bank_units=hb,ZCB2_units=hz,cost0=hb+hz*d02,payoff1=x_pay),
        worlds=worlds,flat_yield_regression=flat)


def encode(value):
    if isinstance(value,F):return str(value)
    if isinstance(value,dict):return {k:encode(v) for k,v in value.items()}
    if isinstance(value,list):return [encode(v) for v in value]
    return value


def svg_start(title,desc,height):
    return ['<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="'+str(height)+'" viewBox="0 0 1060 '+str(height)+'">',
        '<title>'+escape(title)+'</title><desc>'+escape(desc)+'</desc><rect width="1060" height="'+str(height)+'" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#17273a;font-size:17px}.small{font-size:14px}.title{font-size:25px;font-weight:bold}</style>']


def call_svg(result):
    c=result['continuous'];p=c['parameters'];curve=c['price_curve']
    height=max(800,730+31*len(c['P_representations']))
    out=svg_start('连续call复制价格与物理风险解释','同一给定r/波动/期限的call价格与支付/贴现下界；物理漂移改变风险价格和真实预期，不改变本模型复制成本。',height)
    out+=['<text class="title" x="35" y="35">Call replication price and physical risk are different objects</text>',
          f'<text class="small" x="35" y="63">Synthetic GBM: K={p["strike"]:g}, r={p["rate"]:g}, sigma={p["sigma"]:g}, years={p["years"]:g}; price units: current money</text>']
    xmin=curve[0]['spot'];xmax=curve[-1]['spot'];ymax=max(v[key] for v in curve for key in ['call','terminal_payoff','discounted_strike_lower'])*1.12
    xx=lambda x:95+870*(x-xmin)/(xmax-xmin)
    yy=lambda y:505-390*y/ymax
    out.append('<path d="M95 105 V505 H965" fill="none" stroke="#25374b" stroke-width="2"/>')
    for i in range(5):
        x=xmin+(xmax-xmin)*i/4;y=ymax*i/4
        out.append(f'<text class="small" x="{xx(x)-10:.2f}" y="530">{x:g}</text>')
        out.append(f'<text class="small" x="35" y="{yy(y)+4:.2f}">{y:.1f}</text>')
    for key,color,dash in [('terminal_payoff','#777','7 4'),('discounted_strike_lower','#a2670c','3 4'),('call','#205f9c','none')]:
        pts=' '.join(f'{xx(v["spot"]):.3f},{yy(v[key]):.3f}' for v in curve)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.7" stroke-dasharray="{dash}"/>')
    out+=['<text x="760" y="560">Current stock price S</text>',
        '<text class="small" x="95" y="590">Blue: call C | dashed gray: (S-K)+ | dotted brown: max(S-K exp(-r h),0)</text>',
        '<text x="35" y="635">Changing physical drift alone leaves C and delta unchanged:</text>']
    for i,w in enumerate(c['P_representations']):
        out.append(f'<text x="45" y="{675+i*31}">mu={w["mu"]:g}: lambda={w["lambda_value"]:.5f}; E_P(stock gross)={w["expected_stock_gross"]:.6f}; C={c["closed_form"]["price"]:.6f}</text>')
    out+=[f'<text class="small" x="35" y="{height-20}">Curves are analytic; quadrature/finite differences are checks, not evidence of actual continuous trading.</text>','</svg>']
    return '\n'.join(out)+'\n'


def term_svg(result):
    t=result['term'];height=max(740,220+160*len(t['worlds']))
    out=svg_start('同一零息曲线不同真实预期和补偿','相同D01/D02与Q，物理P不同；远期减预期含非线性项，持有期补偿为另一个已定义对象。',height)
    out+=['<text class="title" x="35" y="35">Same observed zero prices; different physical expectations</text>',
        f'<text x="35" y="78">D(0,1)={t["D01"]}; D(0,2)={t["D02"]}; Q(H)={t["Q"][1]}; forward net={t["forward_net"]}</text>',
        '<text x="35" y="120">All following rates are fractions of one period (not asset price levels).</text>']
    labels=['E_P future net short','Forward minus E_P short','Bond expected excess HPR']
    keys=['expected_short_net','forward_minus_expected_net_short','bond_expected_excess_gross']
    colors=['#24679f','#9b6509','#6c469c']
    values=[float(w[k]) for w in t['worlds'] for k in keys]
    scale=250/max(max(abs(x) for x in values),0.001)
    for i,w in enumerate(t['worlds']):
        top=180+i*160
        out.append(f'<text x="35" y="{top}">P(H)={w["P_high"]}</text>')
        out.append(f'<line x1="640" y1="{top-15}" x2="640" y2="{top+105}" stroke="#a5a5a5"/>')
        for j,(label,key,color) in enumerate(zip(labels,keys,colors)):
            y=top+j*34;val=w[key];width=abs(float(val))*scale;x=640 if val>=0 else 640-width
            out.append(f'<text class="small" x="175" y="{y+3}">{label}</text>')
            out.append(f'<rect x="{x:.3f}" y="{y-13}" width="{width:.3f}" height="20" fill="{color}"/>')
            out.append(f'<text class="small" x="{max(650,x+width+10):.3f}" y="{y+3}">{val} ({100*float(val):.3f}%)</text>')
    out+=[f'<text class="small" x="35" y="{height-40}">Zero HPR premium at P=Q can coexist with a nonzero forward-forecast gap (Jensen/nonlinearity).</text>','</svg>']
    return '\n'.join(out)+'\n'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inputs',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();data=json.loads(args.inputs.read_text(encoding='utf-8'))
    result=dict(identity=data['identity'],continuous=continuous(data['continuous']),term=term(data['term']))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'results.json').write_text(json.dumps(encode(result),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.out/'continuous-call.svg').write_text(call_svg(result),encoding='utf-8')
    (args.out/'term-worlds.svg').write_text(term_svg(result),encoding='utf-8')
    print('PASS closed-form/P and Q quadrature/FD; exact bond matrix, three physical worlds, forward and covariance identities')
    print('call='+format(result['continuous']['closed_form']['price'],'.10f')+' Q quadrature abs error='+format(result['continuous']['Q_quadrature']['abs_error'],'.3g'))
    print('D01='+str(result['term']['D01'])+' D02='+str(result['term']['D02'])+' forward='+str(result['term']['forward_net']))
    print('bond excess HPR='+','.join(str(w['bond_expected_excess_gross']) for w in result['term']['worlds']))


if __name__=='__main__':main()
```
