#!/usr/bin/env python3
"""Render the saved finite outputs and ideal analytic shapes into two SVGs."""
import argparse
import csv
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape
from pulse_lab import rc, rrc

COLORS=['#3266a5','#b25d10','#278064','#933d85']
FONT='Arial Unicode MS,PingFang SC,Noto Sans CJK SC,system-ui,sans-serif'


class SVG:
    def __init__(self,title,description,height):
        self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="940" height="{height}" viewBox="0 0 940 {height}" role="img" aria-labelledby="title desc">',
                    f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
                    f'<rect width="940" height="{height}" fill="white"/>',
                    f'<g font-family="{FONT}" font-size="14" fill="#1d2a38">']
        self.text(30,30,title,21)
    def text(self,x,y,label,size=14,color='#1d2a38'):
        self.parts.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}">{escape(label)}</text>')
    def line(self,x1,y1,x2,y2,color='#ced6df',dash=''):
        self.parts.append(f'<path d="M{x1:.2f} {y1:.2f} L{x2:.2f} {y2:.2f}" fill="none" stroke="{color}" stroke-dasharray="{dash}"/>')
    def curve(self,points,color,dash=''):
        value=' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
        self.parts.append(f'<polyline points="{value}" fill="none" stroke="{color}" stroke-width="2.2" stroke-dasharray="{dash}"/>')
    def dot(self,x,y,color,shape='circle'):
        if shape=='square':
            self.parts.append(f'<rect x="{x-3:.2f}" y="{y-3:.2f}" width="6" height="6" fill="white" stroke="{color}" stroke-width="1.8"/>')
        else:
            self.parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.2" fill="white" stroke="{color}" stroke-width="1.8"/>')
    def panel(self,top,xlim,ylim,xticks,yticks,title,xlabel,ylabel):
        left,right,bottom=90,875,top+190
        x=lambda v:left+(v-xlim[0])/(xlim[1]-xlim[0])*(right-left)
        y=lambda v:bottom-(v-ylim[0])/(ylim[1]-ylim[0])*190
        self.text(30,top-46,title,17)
        for v in xticks:
            self.line(x(v),top,x(v),bottom)
            self.text(x(v)-10,bottom+21,f'{v:g}')
        for v in yticks:
            self.line(left,y(v),right,y(v))
            self.text(43,y(v)+4,f'{v:g}')
        self.line(left,top,left,bottom,'#35485b');self.line(left,bottom,right,bottom,'#35485b')
        self.text(790,bottom+42,xlabel);self.text(30,top-5,ylabel)
        return x,y
    def save(self,path):
        if path.exists(): raise ValueError('output exists: '+str(path))
        path.write_text('\n'.join(self.parts+['</g></svg>'])+'\n')


def draw(results_dir,output_dir):
    result=json.loads((results_dir/'results.json').read_text())
    c=result['inputs'];L=max(c['samples_per_symbol']);span=min(c['spans_symbols'])
    # The canonical fixed card supplies all three comparisons. Other cards get the
    # same figures with the first beta and available span comparisons.
    beta=.25 if .25 in c['betas'] else c['betas'][0]
    alternate=.5 if .5 in c['betas'] else c['betas'][-1]
    longer=max(c['spans_symbols'])
    find=lambda b,s:next(r for r in result['cases'] if (r['beta'],r['span_symbols'],r['sps'])==(b,s,L))
    base=find(beta,span)
    fig=SVG('RC/RRC：连续谱、两种脉冲与有限截断',
            'Frequency is nu=fT. Ideal raised-cosine spectrum is dimensionless G/T. Time shapes are g(Tx) and sqrt(T)p(Tx). Finite cascade symbol taps do not vanish exactly. The last plot has a minus 60 dB display floor.',1030)
    x,y=fig.panel(95,(-1.2,1.2),(0,1.12),[-1,-.5,0,.5,1],[0,.5,1],
                  'A  理想RC谱：rolloff改变截止频率，折叠和保持1','ν=fT','G/T')
    for j,b in enumerate(c['betas']):
        points=[]
        # Frequency shape read from saved spectrum table at nonnegative nu.
        with (results_dir/'spectrum.csv').open() as f:
            rows=[r for r in csv.DictReader(f) if float(r['beta'])==b and int(r['span'])==span and int(r['sps'])==L and float(r['nu_fT'])<=1.2]
        positive=[(float(r['nu_fT']),float(r['ideal_G_over_T'])) for r in rows]
        data=[(-v,w) for v,w in reversed(positive[1:])]+positive
        fig.curve([(x(v),y(w)) for v,w in data],COLORS[j],'' if j%2==0 else '6 3')
        fig.text(110+j*180,70,f'β={b:g}',14,COLORS[j])
    x,y=fig.panel(405,(-3.2,3.2),(-.28,1.2),[-3,-2,-1,0,1,2,3],[-.2,0,.5,1],
                  f'B  β={beta:g}：RRC自身不过所有符号零点；有限级联仍有旁瓣','x=t/T','无量纲')
    points=[-3.2+j*6.4/640 for j in range(641)]
    fig.curve([(x(v),y(rc(v,beta))) for v in points],COLORS[0])
    fig.curve([(x(v),y(rrc(v,beta))) for v in points],COLORS[1],'7 4')
    fig.text(100,380,'蓝实线 g(Tx)；橙虚线 √T·p(Tx)；方点 有限RRC级联符号tap',14)
    for key,value in base['symbol_lags'].items():
        m=int(key)
        if abs(m)<=3: fig.dot(x(m),y(value),COLORS[3],'square')
    x,y=fig.panel(715,(0,1.2),(-60,6),[0,.25,.5,.75,1],[0,-20,-40,-60],
                  f'C  β={beta:g}：截断后的带外尾；数字频谱此处只显示局部','ν=fT','10 log10(|P|²/T)')
    with (results_dir/'spectrum.csv').open() as f: rows=list(csv.DictReader(f))
    for j,s in enumerate(sorted(set([span,longer]))):
        chosen=[r for r in rows if float(r['beta'])==beta and int(r['span'])==s and int(r['sps'])==L and float(r['nu_fT'])<=1.2]
        fig.curve([(x(float(r['nu_fT'])),y(max(-60,10*math.log10(max(1e-30,float(r['finite_P_squared_over_T'])))))) for r in chosen],COLORS[j+1],'' if j==0 else '6 3')
        fig.text(110+j*265,690,f'有限 S={s}, L={L}',14,COLORS[j+1])
    chosen=[r for r in rows if float(r['beta'])==beta and int(r['span'])==span and int(r['sps'])==L and float(r['nu_fT'])<=1.2]
    fig.curve([(x(float(r['nu_fT'])),y(max(-60,10*math.log10(max(1e-30,float(r['ideal_G_over_T'])))))) for r in chosen],'#35485b','3 5')
    fig.text(655,690,'灰点线 理想；显示底限−60 dB',13)
    fig.text(35,980,'有限DTFT的 |P|²/T = |Σ u[n] exp(−j2πν(n−D)/L)|²/L；周期为L，不是严格连续带限证明。',13)
    fig.save(output_dir/'pulses.svg')

    count=len(c['bits']);symbols=[1 if b=='1' else -1 for b in c['bits']]
    fig=SVG('同一比特串经过有限RRC发射与匹配接收',
            'All symbols, including frame boundaries, are kept. Waveforms are aligned by each case known FIR pair delay. The second panel shows noiseless amplitude errors at correct and late sampling, not a measured BER.',800)
    fig.text(35,56,f'位串 {c["bits"]}；1→+，0→−；T={c["T_s"]*1000:g} ms；单脉冲 Eb={c["Eb_J"]*1e6:g} μJ',14)
    x,y=fig.panel(130,(-1,count+.2),(-1.9,1.9),list(range(count+1)),[-1,0,1],
                  'A  完整线性卷积的判决窗口，保留全部符号并扣除已知延时','(t−delay)/T','Y/√Eb')
    specs=list(dict.fromkeys([(beta,span),(alternate,span),(beta,longer)]))
    with (results_dir/'waveform.csv').open() as f: waves=list(csv.DictReader(f))
    for j,(b,s) in enumerate(specs):
        chosen=[r for r in waves if float(r['beta'])==b and int(r['span'])==s and int(r['sps'])==L and -1<=float(r['delay_removed_t_over_T'])<=count+.2]
        fig.curve([(x(float(r['delay_removed_t_over_T'])),y(float(r['matched_Y_over_A']))) for r in chosen],COLORS[j],'' if j==0 else '7 4')
        fig.text(100+j*260,104,f'β={b:g}, S={s}, L={L}',14,COLORS[j])
    for k,value in enumerate(base['noiseless_Y_over_A']):fig.dot(x(k),y(value),COLORS[0])
    x,y=fig.panel(475,(-.4,count-.6),(-.95,.95),list(range(count)),[-.8,-.4,0,.4,.8],
                  'B  同一符号的幅值偏差：时偏有干扰，不要求这7位已经翻转','符号 k','Y/√Eb − a[k]')
    series=[(base['noiseless_Y_over_A'],f'τ=0, S={span}',COLORS[0],-.08),
            (base['offset_Y_over_A'],f'τ={c["timing_offset_T"]:g}T, S={span}',COLORS[1],0),
            (find(beta,longer)['noiseless_Y_over_A'],f'τ=0, S={longer}',COLORS[2],.08)]
    for j,(values,label,color,dx) in enumerate(series):
        fig.text(100+j*260,447,label,14,color)
        for k,(value,a) in enumerate(zip(values,symbols)):
            fig.line(x(k+dx),y(0),x(k+dx),y(value-a),color)
            fig.dot(x(k+dx),y(value-a),color,'square' if j==1 else 'circle')
    fig.text(35,738,'曲线来自保存的完整线性卷积；判决点来自results.json。序列外符号为0，没有丢掉边缘位。',13)
    fig.text(35,765,'更细ADC网格提供选择，不自动估计正确相位；此处没有同步获取、真实RF或随机BER实验。',13)
    fig.save(output_dir/'chain.svg')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    draw(args.results,args.output)
    print(args.output/'pulses.svg');print(args.output/'chain.svg')


if __name__=='__main__':main()
