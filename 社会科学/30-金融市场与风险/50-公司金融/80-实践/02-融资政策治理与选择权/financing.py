"""Finite synthetic claims/policies/incentives. Not tax law or an investment engine."""
import argparse
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path
import re


def q(x):
    if type(x) is int:
        if abs(x)>10**9:raise ValueError('bounded integer')
        return F(x)
    if not isinstance(x,str) or len(x)>40 or not re.fullmatch(r'-?\d+(?:/\d+|\.\d+)?',x):raise ValueError('bounded rational or decimal required')
    return F(x)


def vector(v,positive=False):
    if not isinstance(v,list) or not 1<=len(v)<=12:raise ValueError('1..12 finite entries')
    out=list(map(q,v))
    if any(x<0 or (positive and x==0) for x in out):raise ValueError('nonnegative/positive vector')
    return out


def prob(v):
    out=vector(v,True)
    if sum(out)!=1:raise ValueError('positive probabilities sum one')
    return out


def dot(a,b):
    if len(a)!=len(b):raise ValueError('matching states')
    return sum((x*y for x,y in zip(a,b)),F())


def pv(c,r):return sum((x/(1+r)**(i+1) for i,x in enumerate(c)),F())


def claim(x,face,prices,P=None):
    if face<0:raise ValueError('nonnegative face')
    d=[min(v,face) for v in x];e=[v-w for v,w in zip(x,d)];V=dot(prices,x);D=dot(prices,d);E=dot(prices,e)
    assert V==D+E and all(a==b+c for a,b,c in zip(x,d,e))
    out={'cash':x,'face':face,'debt_cash':d,'equity_cash':e,'V':V,'D':D,'E':E}
    if P is not None:
        out.update({'r_assets':dot(P,x)/V-1 if V else None,'r_debt':dot(P,d)/D-1 if D else None,'r_equity':dot(P,e)/E-1 if E else None,'promised_yield':face/D-1 if D else None})
        if E and D:assert out['r_assets']==D/V*out['r_debt']+E/V*out['r_equity']
    return out


def policy(fcf,r,tax,debt=None,lam=None):
    if r<0 or not 0<=tax<1 or (lam is not None and not 0<=lam<1):raise ValueError('nonnegative r; tax/target fraction in [0,1)')
    n=len(fcf);values=[F()]*(n+1)
    if debt is not None:
        if len(debt)!=n+1 or debt[-1]!=0 or any(x<0 for x in debt):raise ValueError('debt path ends zero')
        shield=[tax*r*d for d in debt[:-1]]
        for i in reversed(range(n)):values[i]=(fcf[i]+shield[i]+values[i+1])/(1+r)
    else:
        for i in reversed(range(n)):values[i]=(fcf[i]+values[i+1])/(1+r-tax*r*lam)
        debt=[lam*v for v in values];shield=[tax*r*d for d in debt[:-1]]
    equity=[v-d for v,d in zip(values,debt)]
    if any(v<=0 for v in values[:-1]) or any(e<0 for e in equity):raise ValueError('positive live V and nonnegative equity')
    interest=[r*d for d in debt[:-1]];debt_cash=[debt[i]-debt[i+1]+interest[i] for i in range(n)]
    equity_cash=[fcf[i]+shield[i]-debt_cash[i] for i in range(n)]
    if any(x<0 for x in equity_cash):raise ValueError('finite model excludes additional equity calls')
    wacc=[r-tax*r*debt[i]/values[i] for i in range(n)]
    wvalue=F()
    for i in reversed(range(n)):wvalue=(fcf[i]+wvalue)/(1+wacc[i])
    unlevered=pv(fcf,r);shield_pv=pv(shield,r);apv=unlevered+shield_pv
    assert apv==values[0]==wvalue
    assert pv(debt_cash,r)==debt[0] and pv(equity_cash,r)==equity[0]
    return {'V_ex_distribution':values,'D_ex_distribution':debt,'E_ex_distribution':equity,'interest':interest,'shield':shield,'debt_cash':debt_cash,'equity_cash':equity_cash,'wacc':wacc,'unlevered':unlevered,'shield_PV':shield_pv,'APV':apv,'WACC_value':wvalue,'debt_claim_PV':pv(debt_cash,r),'equity_claim_PV':pv(equity_cash,r)}


def run(data):
    if data['schema']!='financing-governance-v1' or data['data_kind']!='synthetic_not_market_or_tax_law':raise ValueError('fixed synthetic schema')
    out={}
    c=data['mm'];P=prob(c['P']);prices=vector(c['state_prices'],True);x=vector(c['cash']);faces=vector(c['faces']);shares=q(c['shares'])
    if shares<=0 or dot(prices,x)<=0:raise ValueError('positive shares/assets')
    rows=[claim(x,f,prices,P) for f in faces]
    for row in rows:row['equity_per_share']=row['E']/shares;row['oldholder_wealth_after_fair_recap']=row['D']+row['E']
    out['mm']={'rows':rows,'risk_free_rate':1/sum(prices)-1,'shares':shares,'scope':'fixed operating cash; common pricing and freely tradable claims'}
    c=data['valuation'];fcf=vector(c['fcf']);r=q(c['r']);tax=q(c['tax']);fixed=policy(fcf,r,tax,vector(c['debt_after_distribution']));target=policy(fcf,r,tax,lam=q(c['target_debt_fraction']))
    wrong=pv(fcf,target['wacc'][0]);out['valuation']={'fixed_debt':fixed,'constant_ratio':target,'fixed_debt_wrong_constant_target_WACC':wrong,'wrong_minus_correct_fixed':wrong-fixed['APV'],'initial_cost':q(c['initial_cost']),'fixed_NPV':fixed['APV']-q(c['initial_cost']),'target_NPV':target['APV']-q(c['initial_cost'])}
    c=data['distress'];prices=vector(c['state_prices'],True);x=vector(c['cash']);face=q(c['face']);loss=q(c['loss_if_default'])
    if loss<0 or any(loss>v for v in x if v<face):raise ValueError('distress loss cannot exceed default assets')
    after=[v-loss if v<face else v for v in x];clean=claim(x,face,prices);lost=claim(after,face,prices)
    out['distress']={'without_loss':clean,'with_loss':lost,'loss_cash':[a-b for a,b in zip(x,after)],'loss_PV':clean['V']-lost['V']}
    c=data['risk_shift'];P=prob(c['P']);safe=claim(vector(c['safe']),q(c['old_face']),P);risky=claim(vector(c['risky']),q(c['old_face']),P)
    out['risk_shift']={'safe':safe,'risky':risky,'equity_gain':risky['E']-safe['E'],'old_debt_change':risky['D']-safe['D'],'total_change':risky['V']-safe['V']}
    c={k:q(v) for k,v in data['overhang'].items()};v=c['old_assets'];f=c['old_face'];cost=c['new_cost'];new=v+c['new_cash'];ren=c['renegotiated_face']
    if min(c.values())<0 or ren>f:raise ValueError('nonnegative overhang values and reduced face')
    oldd=min(v,f);olde=max(v-f,0);newd=min(new,f);newe=max(new-f,0);rd=min(new,ren);re=max(new-ren,0)
    out['overhang']={'old_D':oldd,'old_E':olde,'new_assets':new,'new_D_original':newd,'new_E_original':newe,'total_increment_NPV':c['new_cash']-cost,'equity_increment_original':newe-olde-cost,'renegotiated_D':rd,'renegotiated_E':re,'old_creditor_increment':rd-oldd,'equity_increment_renegotiated':re-olde-cost}
    c={k:q(v) for k,v in data['pledge'].items()};I=c['cost'];R=c['success_cash'];ph=c['p_effort'];pl=c['p_shirk'];b=c['private_benefit'];inside=c['inside_cash']
    if not 0<=pl<ph<=1 or min(I,R,b,inside)<0 or inside>I:raise ValueError('effort and funds domain')
    bound=R-b/(ph-pl);implementable=bound>=0;Dmax=bound if implementable else None;capacity=ph*bound if implementable else None;Fneeded=I-inside;D=Fneeded/ph
    out['pledge']={'effort_implementable_weak_IC':implementable,'D_max_weak_IC':Dmax,'maximum_outside_funding':capacity,'fundable_without_inside_cash_weak_IC':implementable and I<=capacity,'minimum_inside_funding_weak_IC':max(I-capacity,F()) if implementable else None,'cash_project_NPV_effort':ph*R-I,'cash_project_NPV_shirk':pl*R-I,'cash_plus_private_benefit_shirk':pl*R+b-I,'chosen_inside':inside,'outside_needed':Fneeded,'success_repayment':D,'IC_effort_minus_shirk':(ph-pl)*(R-D)-b,'outside_break_even':ph*D-Fneeded,'fundable_weak_IC':implementable and D<=bound}
    c=data['information'];A=vector(c['old_assets']);P=prob(c['prior']);I=q(c['investment']);B=q(c['new_cash'])
    if len(A)!=2 or A[0]>=A[1] or c['old_shareholders']!='passive_no_rebalancing' or c['actions']!='issue_or_skip' or c['only_low_issues_candidate'] is not True or I<=0 or B<I:raise ValueError('two ordered types; passive issue/skip model')
    def issue_rows(a):return [{'type_old_asset':v,'old_retained_value':(1-a)*(v+B),'gain_vs_skip':(1-a)*(v+B)-v,'new_investor_receipt':a*(v+B)} for v in A]
    pooling_alpha=I/(dot(P,A)+B);separating_alpha=I/(A[0]+B)
    if max(pooling_alpha,separating_alpha)>1:raise ValueError('financing share cannot exceed one')
    out['information']={'pooling_new_fraction':pooling_alpha,'pooling_deviations':issue_rows(pooling_alpha),'only_low_issues_posterior':[F(1),F(0)],'only_low_new_fraction':separating_alpha,'only_low_deviations':issue_rows(separating_alpha),'candidate_is_self_consistent':issue_rows(separating_alpha)[0]['gain_vs_skip']>=0 and issue_rows(separating_alpha)[1]['gain_vs_skip']<=0,'safe_debt_available':min(A)+B>=I,'debt_repayment':I,'old_value_with_safe_debt':[v+B-I for v in A],'scope':'equity-only separating candidate checked; adding safe debt changes the action set'}
    c={k:q(v) for k,v in data['payout'].items()};A=c['operating_assets'];cash=c['cash'];n=c['shares'];alpha=c['manager_share'];b=c['private_benefit']
    if min(c.values())<0 or A<=0 or n<=0 or not 0<=alpha<=1:raise ValueError('payout domain')
    V=A+cash;price=V/n;repurchased=cash/price;remaining=n-repurchased
    out['payout']={'before_value':V,'before_price':price,'dividend_per_share':cash/n,'after_dividend_price':A/n,'repurchased_shares_fair':repurchased,'remaining_shares':remaining,'after_fair_repurchase_price':A/remaining,'all_original_wealth_after':cash+A,'bad_project_market_NPV':c['bad_investment_cash']-cash,'manager_increment_bad':alpha*(c['bad_investment_cash']-cash)+b,'good_project_market_NPV':c['good_investment_cash']-cash,'scope':'fixed investment for payout irrelevance; investment variants explicitly change policy'}
    c=data['options'];P=prob(c['P']);I=q(c['cost']);now=vector(c['now_cash']);free=vector(c['wait_no_loss_cash']);loss=vector(c['wait_loss_cash']);fee=q(c['waiting_fee']);salvage=q(c['salvage1']);contcost=q(c['continue_cost1']);cont=vector(c['continue_cash2']);I0=q(c['abandon_cost0'])
    if len(P)!=2 or any(len(v)!=2 for v in [now,free,loss,cont]) or min(I,fee,salvage,contcost,I0)<0:raise ValueError('two states and nonnegative option inputs')
    def wait(X):return [{'invest_by_state':list(actions),'payoffs':[x-I if act else F() for x,act in zip(X,actions)],'value':dot(P,[x-I if act else F() for x,act in zip(X,actions)])} for actions in product([False,True],repeat=2)]
    freepol=wait(free);losspol=wait(loss);continuation=[v-contcost for v in cont];post=[max(v,salvage) for v in continuation]
    out['options']={'immediate_NPV':dot(P,now)-I,'free_wait_all_4_policies':freepol,'free_wait_value':max(v['value'] for v in freepol),'delayed_cash_all_4_policies':losspol,'delayed_cash_wait_value':max(v['value'] for v in losspol),'delayed_cash_with_fee_value':max(v['value'] for v in losspol)-fee,'continue_net_by_state':continuation,'abandon_post_choice_by_state':post,'abandon_actions':['continue' if v>=salvage else 'abandon' for v in continuation],'forced_continue_NPV':-I0+dot(P,continuation),'with_abandon_NPV':-I0+dot(P,post),'option_increment':dot(P,post)-dot(P,continuation),'date0_best_invest_or_skip':max(F(),-I0+dot(P,post))}
    c=data['existing_ai'];Q=q(c['Q']);closed=vector(c['closed']);u=q(c['utilization']);price=q(c['price']);unit=q(c['unit_cash_cost']);fixed=q(c['fixed_cash_cost']);I=q(c['initial_cost']);S=q(c['salvage2']);r=q(c['r']);debt=vector(c['debt_after_distribution']);founder=q(c['founder_cash']);outside=q(c['new_equity_cash']);n=q(c['founder_shares']);fee=q(c['financing_fee'])
    if len(closed)!=2 or any(v>1 for v in closed) or not 0<=u<=1 or min(Q,price,unit,fixed,I,S,r,founder,outside,fee)<0 or n<=0:raise ValueError('finite original AI panel domain')
    sold=[Q*a*u for a in closed];fcf=[v*(price-unit)-fixed for v in sold];fcf[-1]+=S
    finance=policy(fcf,r,F(),debt);V=finance['APV'];E=finance['E_ex_distribution'][0]
    if E<=outside or founder+outside+debt[0]!=I:raise ValueError('positive founder claim and fully funded initial cost')
    new_fraction=outside/E;founder_value=E-outside;new_shares=n*outside/founder_value
    out['existing_ai']={'sold_tasks':sold,'FCF_including_terminal_salvage':fcf,'asset_value':V,'project_NPV':V-I,'debt':finance,'new_equity_fraction_fair':new_fraction,'founder_shares':n,'new_shares_fair':new_shares,'founder_claim_value':founder_value,'founder_initial_cash':founder,'founder_NPV':founder_value-founder,'external_equity_PV':new_fraction*pv(finance['equity_cash'],r),'founder_CF':[(1-new_fraction)*x for x in finance['equity_cash']],'external_CF':[new_fraction*x for x in finance['equity_cash']],'all_equity_NPV_after_fee':E-(I-debt[0]+fee),'founder_NPV_after_fee_with_extra_cash':founder_value-founder-fee,'funding_gap_before_outside_equity':I-founder-debt[0]}
    return {'schema':'financing-governance-result-v1','input':data,'results':out,'scope':'separate synthetic panels; not empirical financing, tax law, real security advice or a full equilibrium calibration'}


def encode(x):
    if isinstance(x,F):return str(x)
    if isinstance(x,dict):return {k:encode(v) for k,v in x.items()}
    if isinstance(x,list):return [encode(v) for v in x]
    return x


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists() or a.out.is_symlink():p.exit(2,'fresh output file required\n')
    result=encode(run(json.loads(a.input.read_text())));a.out.write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n');print(json.dumps({'status':'PASS','panels':len(result['results']),'scope':result['scope']}))
if __name__=='__main__':main()
