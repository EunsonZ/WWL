#!/usr/bin/env python3
"""Draw saved JSON only. No cascade/reconstruction is recomputed here."""
import argparse
from html import escape
import json
from pathlib import Path

FONT='Arial Unicode MS,PingFang SC,Noto Sans CJK SC,system-ui,sans-serif'
COLORS=['#286bad','#c2572b','#218363','#9256a8']


class SVG:
    def __init__(self,title,desc,height):
        self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" viewBox="0 0 1100 {height}" role="img">',
                    f'<title>{escape(title)}</title><desc>{escape(desc)}</desc>',f'<rect width="1100" height="{height}" fill="#fff"/>',
                    f'<g font-family="{FONT}" fill="#172433">']
    def text(self,x,y,s,size=16,color='#172433',anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(s))}</text>')
    def line(self,x1,y1,x2,y2,color='#cad3dd',dash=''):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-dasharray="{dash}"/>')
    def path(self,pts,color,dash='',width=2):
        d=' '.join(('M' if i==0 else 'L')+f'{x:.3f},{y:.3f}' for i,(x,y) in enumerate(pts))
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>')
    def dot(self,x,y,color,r=3.5):
        self.parts.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r}" fill="{color}"/>')
    def panel(self,top,title,xr,ys,unit):
        left,right,height=82,1045,170
        lo=min(0,min(ys)); hi=max(0,max(ys))
        if hi==lo:hi=lo+1
        pad=(hi-lo)*.1;lo-=pad;hi+=pad
        def pos(x,y):return left+(x-xr[0])/(xr[1]-xr[0])*(right-left),top+height-(y-lo)/(hi-lo)*height
        self.text(left,top-46,title,20)
        self.text(30,top-12,unit,14)
        for i in range(5):
            y=lo+i*(hi-lo)/4;xx,yy=pos(xr[0],y)
            self.line(left,yy,right,yy);self.text(left-12,yy+5,f'{y:.3g}',14,anchor='end')
            x=xr[0]+i*(xr[1]-xr[0])/4;xx,yy=pos(x,lo)
            self.line(xx,top,xx,top+height,'#eef1f4');self.text(xx,top+height+24,f'{x:.3g}',14,anchor='middle')
        _,zero=pos(xr[0],0);self.line(left,zero,right,zero,'#8d9aa9')
        return pos
    def legend(self,top,items):
        x=85
        for label,color,dash in items:
            self.line(x,top-23,x+28,top-23,color,dash);self.text(x+36,top-18,label,15);x+=280
    def save(self,path):Path(path).write_text('\n'.join(self.parts+['</g></svg>'])+'\n')


def functions(r,out):
    cas=r['cascade'];curves=sorted(cas['curves'],key=lambda t:t['level']);a=r['inputs']['mix_a'];last=curves[-1]
    svg=SVG('db2有限迭代与连续双基构造','有限分格常值cascade曲线示意；存在性与连续正则性由正文证明，非曲线认证。双基面板截取显示范围，dual部分和有单列L2尾界。',1040)
    svg.text(50,40,'连续对象先证明，有限cascade再展示形状',27)
    svg.text(50,70,'τ 与纵轴均无量纲；φ⁽⁰⁾=1_[0,1)。图只读保存JSON，不把有限迭代当连续真值。',16)
    for i,(key,title) in enumerate([('phi_cascade','A  尺度函数有限迭代 φ^(J)'),('psi_cascade','B  小波有限迭代 ψ^(J)')]):
        top=155+285*i
        ys=[v for c in curves for t,v in zip(c['tau'],c[key]) if 0<=t<=3]
        pos=svg.panel(top,title,[0,3],ys,'幅值')
        shown=curves[-3:]
        svg.legend(top,[(f'J={c["level"]}',COLORS[k],'6,3' if k< len(shown)-1 else '') for k,c in enumerate(shown)])
        for k,c in enumerate(shown):svg.path([pos(t,v) for t,v in zip(c['tau'],c[key]) if 0<=t<=3],COLORS[k],'6,3' if k<len(shown)-1 else '',1.7)
        svg.text(1045,top+215,'τ',15,anchor='end')
    top=725;xr=[-min(cas['last_dual_shift'],4),4]
    ys=[v for key in ('b_cascade','dual_partial_cascade') for t,v in zip(last['tau'],last[key]) if xr[0]<=t<=xr[1]]
    pos=svg.panel(top,f'C  同一 J={last["level"]} 迭代：b 与 dual 的有限部分和，a={a:g}',xr,ys,'幅值')
    svg.legend(top,[('b=ψ+a·右移ψ',COLORS[0],''),(f'dual 保留 r=0…{cas["last_dual_shift"]}',COLORS[1],'5,3')])
    for key,color,dash in [('b_cascade',COLORS[0],''),('dual_partial_cascade',COLORS[1],'5,3')]:
        svg.path([pos(t,v) for t,v in zip(last['tau'],last[key]) if xr[0]<=t<=xr[1]],color,dash)
    svg.text(1045,top+215,'τ（显示窗口，非宣称完整dual支撑）',15,anchor='end')
    svg.text(50,995,f'精确 ψ 的 dual 尾 L² 范数界：{cas["dual_tail_L2_bound_for_exact_psi"]:.6g}；该界不包含有限cascade逼近误差。',16)
    svg.text(50,1022,'a=0 退化为正交 ψ；0<|a|<1 时精确dual非紧支撑。图中采样连线仅作示意。',15)
    svg.save(out/'functions.svg')


def boundaries(r,out):
    x=r['inputs']['samples_V'];rec=r['record'];n=len(x);a=r['inputs']['mix_a']
    svg=SVG('长db2边界与改基的有限记录','显示原输入全部N个样点及三种边界重建；漏左边界系数的解析rankone误差与双基系数平方和比较。',1000)
    svg.text(50,40,'同一记录：长滤波边界和改基分别改了什么？',27)
    svg.text(50,70,f'N={n}，fs={r["inputs"]["sample_rate_Hz"]:g} Hz；横轴原样点n，电压V；完整原区间均显示。',16)
    top=155;ys=x+rec['zero_dropped']['restored']
    pos=svg.panel(top,'A  原样点与zero dropped重建：丢失方向在边缘可见',[0,n-1],ys,'V')
    svg.legend(top,[('原输入',COLORS[0],''),('zero dropped',COLORS[1],'5,3')])
    for vals,col,dash in [(x,COLORS[0],''),(rec['zero_dropped']['restored'],COLORS[1],'5,3')]:
        pts=[pos(i,v) for i,v in enumerate(vals)];svg.path(pts,col,dash)
        for xx,yy in pts:svg.dot(xx,yy,col)
    svg.text(1045,top+215,'样点 n',15,anchor='end')
    top=445
    errors={key:[v-u for v,u in zip(rec[key]['restored'],x)] for key in ('periodic','zero_full','biorth_periodic')}
    yr=[v for vals in errors.values() for v in vals]
    pos=svg.panel(top,'B  三种正确合同的重建残差（直接写浮点值，不设零floor）',[0,n-1],yr,'V')
    svg.legend(top,[(key,COLORS[k],'') for k,key in enumerate(errors)])
    for k,(key,vals) in enumerate(errors.items()):svg.path([pos(i,v) for i,v in enumerate(vals)],COLORS[k])
    svg.text(1045,top+215,'样点 n',15,anchor='end')
    svg.text(75,740,'C  平方和账本：PR与等距是两份合同',21)
    svg.text(80,775,'对象',17);svg.text(550,775,'平方和 / V²',17);svg.text(825,775,'重建SSE / V²',17)
    rows=[('输入',rec['periodic']['input_squared_sum_V2'],None),('periodic',rec['periodic']['coefficient_squared_sum_V2'],rec['periodic']['error_squared_sum_V2']),
          ('zero full',rec['zero_full']['coefficient_squared_sum_V2'],rec['zero_full']['error_squared_sum_V2']),
          (f'periodic双基 a={a:g}',rec['biorth_periodic']['coefficient_squared_sum_V2'],rec['biorth_periodic']['error_squared_sum_V2'])]
    for j,(label,en,err) in enumerate(rows):
        y=809+28*j;svg.text(80,y,label,16);svg.text(550,y,f'{en:.12g}',16);svg.text(825,y,'—' if err is None else f'{err:.4g}',16)
    svg.text(65,936,f'漏m=−1：实测SSE {rec["zero_dropped"]["error_squared_sum_V2"]:.12g}；解析 |v^T x|²={r["boundary_prediction"]["predicted_dropped_SSE_V2"]:.12g}。',16)
    svg.text(65,966,'有限PR经指定N全基向量检查；连续db2与Riesz双基由正文独立证明，不由这张图推出。',15)
    svg.save(out/'boundaries.svg')


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    r=json.loads(args.results.read_text());args.out.mkdir(parents=True,exist_ok=True);functions(r,args.out);boundaries(r,args.out)

if __name__=='__main__':main()
