"""SVGs from saved results/input only; no market calibration."""
import argparse
from fractions import Fraction as F
import html
import json
from pathlib import Path


def t(x,y,s,size=21,color='#17324d'):return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{html.escape(str(s))}</text>'
def start(title,desc,h=650):return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{h}" viewBox="0 0 1200 {h}"><title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc><rect width="1200" height="100%" fill="#f7fafc"/><g font-family="PingFang SC, sans-serif">',t(35,48,title,30),t(35,83,desc,18)]
def val(x,d=5):return f'{float(F(x)):.{d}f}'
def done(x):return '\n'.join([*x,'</g></svg>'])+'\n'


def plots(data):
    raw=data['input'];r=data['results'];v=r['valuation'];n=len(raw['valuation']['fcf'])
    if n!=2:raise ValueError('this diagram interface requires two periods; raw valuation supports 1..12')
    a=start('先选债务政策，再选择税盾与折现口径','每个V/D为当期现金分派及债务重配后；V包含未来税盾，单位为同一货币。',650)
    for i,(name,key) in enumerate([('固定摊还债务','fixed_debt'),('恒定市场债务比例','constant_ratio')]):
        x=40+i*590;p=v[key];a.extend([f'<rect x="{x}" y="115" width="555" height="390" rx="12" fill="#e6eef7"/>',t(x+15,151,name,25)])
        for xx,h in [(x+15,'位置/支付'),(x+300,'0→1'),(x+425,'1→2')]:a.append(t(xx,198,h,21))
        fields=[('期初 V','V_ex_distribution',False),('期初 D','D_ex_distribution',False),('当期税盾','shield',False),('当期WACC %','wacc',True),('债现金','debt_cash',False),('股现金','equity_cash',False)]
        for j,(label,field,percent) in enumerate(fields):
            y=240+j*41;a.append(t(x+15,y,label,20))
            for k in range(2):a.append(t(x+280+125*k,y,val(F(p[field][k])*(100 if percent else 1),4),18))
        a.append(t(x+15,490,'APV = 逐期WACC = '+val(p['APV']),20,'#147352'))
    a.extend([t(40,550,'固定D误用另一政策恒定w的估值差：'+val(v['wrong_minus_correct_fixed'],8),23),t(40,594,f"教学 r={val(raw['valuation']['r'],3)}；τ={val(raw['valuation']['tax'],3)}。全部确定支付，不含现实风险/税法校准。",20)])
    b=start('同样的企业，谁会支持改变投资？','上部是旧债既存后的市场现金；下部是另一创业项目的努力激励，不能混成同一福利总量。',730)
    rs=r['risk_shift'];cols=[40,400,650,900]
    for x,h in zip(cols,['方案','总值 V','旧债 D','股 E']):b.append(t(x,135,h,23))
    for i,(label,key) in enumerate([('安全方案','safe'),('风险替换','risky')]):
        y=184+i*50
        for x,s in zip(cols,[label,rs[key]['V'],rs[key]['D'],rs[key]['E']]):b.append(t(x,y,s,24))
    b.append(t(40,288,f"股权变化 {rs['equity_gain']}；旧债变化 {rs['old_debt_change']}；总值变化 {rs['total_change']}。",23,'#a93628'))
    c=raw['pledge'];R=F(c['success_cash']);ph=F(c['p_effort']);pl=F(c['p_shirk']);benefit=F(c['private_benefit'])
    if R<=0:raise ValueError('IC line plot requires positive success cash')
    yl=(ph-pl)*R-benefit;yr=-benefit;low=min(yr,F())-3;high=max(yl,F())+3
    def xy(d,y):return 110+float(d/R)*690,380+float((high-y)/(high-low))*205
    x0,y0=xy(0,0);x1,y1=xy(R,0);b.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="#788b9c"/>')
    x0,y0=xy(0,yl);x1,y1=xy(R,yr);b.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="#3975b7" stroke-width="4"/>')
    b.extend([t(40,342,'努力−偷懒效用差 ΔU = (pH−pL)(R−D)−b',23),t(108,620,'成功偿付 D：0',18),t(710,620,str(R),18),t(825,421,'ΔU ≥ 0才满足弱IC',20),t(825,461,'D上限：'+str(r['pledge']['D_max_weak_IC']),20),t(825,501,'外部融资上限：'+str(r['pledge']['maximum_outside_funding']),20),t(40,685,'若连 D=0 时 ΔU<0，努力集合为空；不能把负上限裁成0来制造可行点。',22,'#a93628')])
    c=start('有选择权值，不等于现在值得投入','同一面板无贴现、风险中性；观察后的动作按当时信息决定。金额为合成货币。',680)
    o=r['options'];labels=[('立即投入NPV','immediate_NPV'),('免费且不损收入的等待','free_wait_value'),('等待收入损失后的等待','delayed_cash_wait_value'),('已选择购买等待、再扣费用','delayed_cash_with_fee_value'),('强制续营NPV（另一个放弃项目）','forced_continue_NPV'),('可按状态放弃NPV','with_abandon_NPV'),('放弃权增值','option_increment'),('0期可不投时的最优值','date0_best_invest_or_skip')]
    for i,(label,key) in enumerate(labels):
        y=137+i*51;c.extend([f'<rect x="30" y="{y-28}" width="1140" height="44" fill="{"#e4f2eb" if i in [1,6] else "#e8eef5"}"/>',t(45,y,label,22),t(1000,y,o[key],25)])
    c.extend([t(40,590,'放弃策略：'+str(o['abandon_actions'])+'；分支最优支付 '+str(o['abandon_post_choice_by_state']),20),t(40,635,'扣费等待的负值不等于总体最优为负：可不买/不投；初始投入仍须另算。',21,'#a93628')])
    return {'policies.svg':done(a),'incentives.svg':done(b),'options.svg':done(c)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    for name,s in plots(json.loads(a.results.read_text())).items():(a.out/name).write_text(s)
    print('three SVGs from saved finite input/results')
if __name__=='__main__':main()
