#!/usr/bin/env python3
"""Exact synthetic entry/commitment and repeated-game certificates; not empirical behavior."""
import argparse
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
from html import escape

def maxima(v):
    top=max(v.values());return [k for k,x in v.items() if x==top]
def entry_model(e):
    o,ef,ea,uf,ua,b,k=[F(e[n]) for n in ('out_inc','entrant_f','entrant_a','inc_f','inc_a','bond','fee')]
    if not ef<0<ea or not uf<ua or b<0 or k<0:raise ValueError('entry requires ef<0<ea, uf<ua, nonnegative bond/fee')
    payoff={('O','F'):[F(0),o],('O','A'):[F(0),o],('I','F'):[ef,uf],('I','A'):[ea,ua]}
    nash=[];checks=[]
    for a,c in product(('O','I'),('F','A')):
        own=payoff[a,c];br0=maxima({x:payoff[x,c][0] for x in ('O','I')});br1=maxima({x:payoff[a,x][1] for x in ('F','A')});ok=a in br0 and c in br1
        checks.append(dict(entrant=a,incumbent=c,payoff=own,entrant_BR=br0,incumbent_BR=br1,nash=ok))
        if ok:nash.append([a,c])
    def continuation(contract):
        fee=k if contract else F(0);bond=b if contract else F(0)
        response=maxima({'F':uf-fee,'A':ua-bond-fee});res=[]
        for c in response:
            er=ef if c=='F' else ea
            for a in maxima({'O':F(0),'I':er}):
                inc=o-fee if a=='O' else (uf-fee if c=='F' else ua-bond-fee)
                transfer=fee+(bond if a=='I' and c=='A' else 0)
                res.append(dict(entrant=a,incumbent=c,payoff=[F(0) if a=='O' else er,inc],external_payment=transfer))
        return res
    no=continuation(False);post=continuation(True);profiles=[]
    for cn,cp in product(no,post):
        for initial in maxima({'No':cn['payoff'][1],'Post':cp['payoff'][1]}):
            profiles.append(dict(initial=initial,No=cn,Post=cp,outcome=cn if initial=='No' else cp))
    return dict(payoff=[dict(entrant=a,incumbent=c,value=v) for (a,c),v in payoff.items()],pure_checks=checks,pure_NE=nash,full_mixed_NE=dict(entrant_p_zero_inc_q_interval=[ea/(ea-ef),F(1)],other_point=[F(1),F(0)]),no_contract_pure_SPNE=no,contract_continuations=post,pure_contract_SPNE=profiles,bond_weak_threshold=ua-uf)

def stage(p,a,b):
    return p['R'] if a==b=='C' else p['P'] if a==b=='D' else p['T'] if a=='D' else p['S']
def matrix_checks(p):
    out=[]
    for a,b in product(('C','D'),repeat=2):
        br0=maxima({c:stage(p,c,b) for c in ('C','D')});br1=maxima({c:stage(p,c,a) for c in ('C','D')})
        out.append(dict(actions=[a,b],payoff=[stage(p,a,b),stage(p,b,a)],BR=[br0,br1],nash=a in br0 and b in br1))
    return out

def dp(p,H,tail):
    d=p['delta'];rho=p['rho'];v=dict(tail);layers=[dict(h=0,values=dict(v))]
    for h in range(1,H+1):
        qc=(1-d)*p['R']+d*v['G'];qd=(1-d)*p['T']+d*((1-rho)*v['G']+rho*v['B'])
        bc=(1-d)*p['S']+d*v['B'];bd=(1-d)*p['P']+d*v['B']
        v={'G':max(qc,qd),'B':max(bc,bd)}
        layers.append(dict(h=h,values=dict(v),QG={'C':qc,'D':qd},QB={'C':bc,'D':bd},best={'G':maxima({'C':qc,'D':qd}),'B':maxima({'C':bc,'D':bd})}))
    return dict(H=H,terminal=tail,layers=layers,values=v)

def enumerate_policies(p,H,tail):
    """Every deterministic time-by-state policy, not just constant stationary actions."""
    output=[];d=p['delta'];rho=p['rho']
    for actions in product(('C','D'),repeat=2*H):
        def value(t,s):
            if t==H:return tail[s]
            a=actions[2*t+(s=='B')]
            if s=='B':return (1-d)*stage(p,a,'D')+d*value(t+1,'B')
            if a=='C':return (1-d)*p['R']+d*value(t+1,'G')
            return (1-d)*p['T']+d*((1-rho)*value(t+1,'G')+rho*value(t+1,'B'))
        output.append(dict(policy=list(actions),values={s:value(0,s) for s in ('G','B')}))
    return dict(H=H,count=len(output),maximum={s:max(x['values'][s] for x in output) for s in ('G','B')},policies=output)

def repeated_model(raw):
    p={k:F(raw[k]) for k in ('R','T','P','S','delta','rho')};R,T,P,S,d,rho=[p[k] for k in ('R','T','P','S','delta','rho')]
    if not T>R>P>S:raise ValueError('require strict PD order T>R>P>S')
    if not 0<d<1 or not 0<=rho<=1:raise ValueError('delta in (0,1), rho in [0,1] required')
    N=raw['finite_periods'];hs=raw['horizons'];grid=list(map(F,raw['rho_grid']))
    if type(N) is not int or not 1<=N<=6:raise ValueError('finite_periods is integer in [1,6]')
    if not hs or any(type(h) is not int or not 1<=h<=256 for h in hs):raise ValueError('horizons are integers in [1,256]')
    if not grid or any(not 0<=x<=1 for x in grid):raise ValueError('rho grid in [0,1] required')
    threshold=(T-R)/(T-R+rho*(R-P));qD=(1-d)*T+d*((1-rho)*R+rho*P)
    dstar=((1-d)*T+d*rho*P)/(1-d*(1-rho));best=max(R,dstar);M=max(map(abs,(R,T,P,S)))
    tail={'G':R,'B':P};zero={'G':F(0),'B':F(0)}
    continuation=[dict(rho=x,threshold=(T-R)/(T-R+x*(R-P)),sustainable=d>=(T-R)/(T-R+x*(R-P))) for x in grid]
    dps=[]
    for H in hs:
        x=dp(p,H,tail);z=dp(p,H,zero);assert abs(z['values']['G']-best)<=M*d**H
        if d>=threshold:assert x['values']==tail
        dps.append(dict(H=H,guarded=x,zero=z,zero_tail_error_bound=M*d**H))
    enum=enumerate_policies(p,3,tail);assert enum['maximum']==dp(p,3,tail)['values']
    finite=[]
    for t in range(N):
        for history in product(('CC','CD','DC','DD'),repeat=t):
            finite.append(dict(history=list(history),remaining=N-t,actions=['D','D'],continuation_value=P*(1-d**(N-t))))
    first_deviation=[dict(tau=t,value=R+d**t*((1-d)*T+d*P-R)) for t in range(9)]
    perfect_best=max(R,(1-d)*T+d*P)
    return dict(parameters=p,stage_checks=matrix_checks(p),threshold=threshold,grim_value=tail,one_deviation_value=qD,one_deviation_gain=qD-R,sustainable=d>=threshold,analytic_optimal_deviation_value={'G':best,'B':P},defect_until_alarm_value=dstar,monitoring_grid=continuation,finite_histories=finite,finite_periods=N,dp=dps,enumerated_policies=enum,perfect_monitoring_first_D=first_deviation,perfect_monitoring_best=perfect_best)

def convert(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,dict):return {k:convert(x) for k,x in v.items()}
    if isinstance(v,list):return [convert(x) for x in v]
    return v

def svg_start(title,desc,w=980,h=560):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><title>{escape(title)}</title><desc>{escape(desc)}</desc><rect width="100%" height="100%" fill="white"/><g font-family="Arial, sans-serif" fill="#17212b">',f'<text x="30" y="36" font-size="23">{escape(title)}</text>']
def entry_svg(e,model):
    s=svg_start('Entry: the response must remain optimal after entry','Synthetic perfect-information entry tree. The bold route uses the no-contract subgame-perfect continuation. The public contract is a separate preceding choice, summarized below.')
    def line(x,y,a,b,bold=False):return f'<line x1="{x}" y1="{y}" x2="{a}" y2="{b}" stroke="{ "#245dba" if bold else "#737b83"}" stroke-width="{4 if bold else 2}"/>'
    s += [line(130,220,460,115),line(130,220,460,325,True),line(460,325,790,250),line(460,325,790,410,True)]
    for x,y in [(130,220),(460,325)]:s.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#17212b"/>')
    labels=[(45,200,'Entrant'),(275,140,'O (out)'),(275,305,'I (enter)'),(365,280,'Incumbent observes I'),(615,265,'F (fight)'),(615,340,'A (accommodate)'),(480,120,f"(0, {e['out_inc']})"),(795,255,f"({e['entrant_f']}, {e['inc_f']})"),(795,415,f"({e['entrant_a']}, {e['inc_a']})")]
    for x,y,t in labels:s.append(f'<text x="{x}" y="{y}" font-size="17">{escape(t)}</text>')
    s += ['<text x="35" y="80" font-size="16">Payoffs: entrant first, incumbent second. Bold path = no-contract SPNE.</text>','<text x="35" y="465" font-size="17">Normal-form pure NE: (O,F), (I,A); only (I,A) is subgame perfect.</text>']
    choices=','.join(sorted(set(x['initial'] for x in model['pure_contract_SPNE'])))
    s.append(f'<text x="35" y="505" font-size="16">Prior enforceable contract: bond {escape(e["bond"])}, fee {escape(e["fee"])}; initial pure-SPNE choice(s): {choices}.</text>')
    s.append('<text x="35" y="540" font-size="14">Refunded bond is not a permanent cost. Enforcement and affordability are model assumptions.</text></g></svg>')
    return '\n'.join(s)+'\n'
def monitoring_svg(p,res):
    R,T,P,S,d,rho=[p[k] for k in ('R','T','P','S','delta','rho')];s=svg_start('Public monitoring: when does this grim plan resist deviation?','Synthetic PD with no false alarms under CC. Curve is the analytic required discount threshold. Horizontal dashed line and marked point show input discount and detection. Delta=1 is excluded, so zero detection never supports this plan.')
    xp=lambda x:100+780*float(x);yp=lambda y:425-300*float(y)
    s.append('<path d="M100 100V425H880" fill="none" stroke="#444"/>')
    for i in range(6):
        x=F(i,5);s.append(f'<text x="{xp(x)}" y="452" text-anchor="middle">{float(x):.1f}</text>');s.append(f'<text x="85" y="{yp(x)+5}" text-anchor="end">{float(x):.1f}</text>')
    pts=' '.join(f'{xp(F(j,100)):.2f},{yp((T-R)/(T-R+F(j,100)*(R-P))):.2f}' for j in range(101))
    s.append(f'<polyline points="{pts}" stroke="#245dba" fill="none" stroke-width="3"/>')
    s.append(f'<line x1="100" y1="{yp(d)}" x2="880" y2="{yp(d)}" stroke="#bd4c18" stroke-dasharray="9 5" stroke-width="2"/>')
    s.append(f'<circle cx="100" cy="{yp(F(1))}" r="6" fill="white" stroke="#245dba" stroke-width="2"/>')
    s.append(f'<rect x="{xp(rho)-5}" y="{yp(d)-5}" width="10" height="10" fill="#17212b"/>')
    s.append(f'<text x="105" y="75" font-size="16">Solid: threshold; dashed: delta={d}; square: rho={rho}; sustainable={res["sustainable"]}.</text>')
    s.append(f'<text x="105" y="100" font-size="15">Stage payoffs R={R}, T={T}, P={P}, S={S}. Equality is weak incentive compatibility.</text>')
    s += ['<text x="490" y="490" text-anchor="middle">Public detection rho (no false alarm under CC)</text>','<text x="105" y="525" font-size="15">Vertical: required delta. Open endpoint delta=1 is outside the infinite discounted model.</text>','<text x="105" y="550" font-size="14">A threshold for one public plan is not a prediction of behavior or a full set of equilibria.</text></g></svg>']
    return '\n'.join(s)+'\n'
def run(inp,out):
    raw=json.loads(inp.read_text());entry=entry_model(raw['entry']);repeat=repeated_model(raw['repeated']);w=raw['observation_worlds'];N=w['periods'];bt=F(w['world_b_T']);p=repeat['parameters']
    if type(N) is not int or not 1<=N<=1000 or not p['R']>bt:raise ValueError('observation periods integer1..1000, worldB T<R required')
    worlds=dict(identity='specified competing synthetic mechanisms, not inferred from observations',world_A_supported_perfect_grim=p['delta']>=(p['T']-p['R'])/(p['T']-p['P']),world_B_constant_C_is_stage_NE=True,world_B_T=bt,records=[dict(t=t,actions=['C','C'],alarm=0) for t in range(N)])
    result=dict(identity='entirely synthetic; proof and finite verification are distinct',entry=entry,repeated=repeat,observation_worlds=worlds)
    out.mkdir(parents=True,exist_ok=True);out.joinpath('results.json').write_text(json.dumps(convert(result),ensure_ascii=False,indent=2)+'\n');out.joinpath('entry-tree.svg').write_text(entry_svg(raw['entry'],entry));out.joinpath('monitoring-threshold.svg').write_text(monitoring_svg(p,repeat));print('PASS exact entry/commitment, finite histories, global deviation DP and all 64 time-state policies')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();run(a.input,a.out)
