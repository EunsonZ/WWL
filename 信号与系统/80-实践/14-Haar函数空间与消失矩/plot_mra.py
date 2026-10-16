#!/usr/bin/env python3
"""Draw only saved results; standard library SVG, no new numerical experiments."""
import argparse
from html import escape
import json
from pathlib import Path

COLORS = ['#246cba','#d95725','#22805e','#9c4593']
FONT = 'Arial Unicode MS,PingFang SC,Noto Sans CJK SC,system-ui,sans-serif'


class SVG:
    def __init__(self, title, desc, height):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" viewBox="0 0 1100 {height}" role="img">',
                      f'<title>{escape(title)}</title><desc>{escape(desc)}</desc>',
                      f'<rect width="1100" height="{height}" fill="#fff"/>',
                      f'<g font-family="{FONT}" fill="#172433">']
    def text(self, x, y, s, size=16, color='#172433', anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(s))}</text>')
    def line(self, x1,y1,x2,y2,color='#b4c0cc',width=1,dash=''):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>')
    def path(self, pts, color, dash='', width=2.3):
        d=' '.join(('M' if i==0 else 'L')+f'{x:.4f},{y:.4f}' for i,(x,y) in enumerate(pts))
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>')
    def circle(self,x,y,color):
        self.parts.append(f'<circle cx="{x:.4f}" cy="{y:.4f}" r="4" fill="{color}"/>')
    def panel(self, top, title, xr, yr, x_label):
        left,right,height=80,1040,180
        self.text(left,top-48,title,20)
        def mapxy(x,y):return left+(x-xr[0])/(xr[1]-xr[0])*(right-left),top+height-(y-yr[0])/(yr[1]-yr[0])*height
        for n in range(5):
            y=yr[0]+n*(yr[1]-yr[0])/4
            px,py=mapxy(xr[0],y)
            self.line(left,py,right,py)
            self.text(left-12,py+5,f'{y:.3g}',14,anchor='end')
        for n in range(5):
            x=xr[0]+n*(xr[1]-xr[0])/4
            px,py=mapxy(x,yr[0])
            self.line(px,top,px,top+height,'#edf0f3')
            self.text(px,top+height+24,f'{x:.3g}',14,anchor='middle')
        self.line(left,top+height,right,top+height,'#53687c',1.4)
        self.text(right,top+height+49,x_label,15,anchor='end')
        return mapxy
    def save(self,path):Path(path).write_text('\n'.join(self.parts+['</g></svg>'])+'\n')


def actual_points(segs):
    pts=[]
    for a,b,p in segs:
        # Degree<=2 polynomial draw; endpoints are coordinates, not L2 point claims.
        pts.append((a,0))
        for n in range(81):
            x=a+(b-a)*n/80
            pts.append((x,sum(v*x**r for r,v in enumerate(p))))
        pts.append((b,0))
    return pts


def projections(r,output):
    signals=r['signals']
    shown=signals[:2]
    svg=SVG('同函数的Haar格平均与L2误差','原函数、三个尺度的积分投影与保存的误差平方。端点连线只是绘图，不承诺逐点收敛。',1000)
    svg.text(55,42,'尺度变细补回哪些方向？',27)
    svg.text(55,72,'τ 无量纲；基归一为 2^(j/2)。曲线与表均来自 results.json。',16)
    for i,s in enumerate(shown):
        top=160+i*300
        candidates={p['level']:p for p in s['projections']}
        levels=[j for j in [0,2,4] if j in candidates]
        if not levels:levels=sorted(candidates)[-3:]
        pts=actual_points(s['segments']);ys=[y for _,y in pts]
        lo=min(0,min(ys));hi=max(ys)
        if hi==lo:hi=lo+1
        pad=(hi-lo)*.12
        visible=[cell for j in levels for cell in candidates[j]['cells']]
        xr=[min(s['segments'][0][0], min(t['left'] for t in visible)),
            max(s['segments'][-1][1], max(t['right'] for t in visible))]
        pts=[(xr[0],0)]+pts+[(xr[1],0)]
        xy=svg.panel(top,f'{chr(65+i)}  {s["name"]}：原函数与积分格平均',xr,[lo-pad,hi+pad],'τ')
        svg.text(80,top-20,'实线黑：原函数',15)
        svg.path([xy(x,y) for x,y in pts],'#172433',width=2.8)
        for n,j in enumerate(levels):
            p=candidates[j];v=[]
            for cell in p['cells']:
                a,b=cell['left'],cell['right']
                if b<xr[0] or a>xr[1]:continue
                v.extend([(max(a,xr[0]),cell['value']),(min(b,xr[1]),cell['value'])])
            dash=['8,4','3,4','12,3,2,3'][n]
            svg.path([xy(x,y) for x,y in v],COLORS[n],dash)
            svg.text(320+n*235,top-20,f'虚线 j={j}',15,COLORS[n])
    svg.text(80,738,'C  保存的 L² 误差平方（0 无需取对数或人为加 floor）',20)
    svg.text(100,773,'j',16)
    for i,s in enumerate(shown):svg.text(300+350*i,773,s['name'],16)
    records=[{p['level']:p for p in s['projections']} for s in shown]
    common=sorted(set.intersection(*(set(d) for d in records)))
    selected=[j for j in common if 0<=j<=6]
    if not selected:selected=common[:7]
    for n,j in enumerate(selected):
        y=803+n*23
        svg.text(100,y,j,15)
        for i,d in enumerate(records):svg.text(300+350*i,y,f'{d[j]["error_squared"]:.9g}',15)
    svg.text(80,982,'范数极限由正文证明；有限曲线只检查声明模型与积分实现。',15)
    svg.save(output/'projections.svg')


def moments(r,output):
    f={q['name']:q for q in r['filters']}
    svg=SVG('消失矩、有限边缘与连续缩放反例','保存的离散矩与斜坡完整零延拓输出；sparse QMF 的连续box平移存在重叠，不能由离散QMF推连续正交。',1060)
    svg.text(55,42,'矩为零，零的是哪个对象？',27)
    svg.text(55,72,'有限内积 b[m]=Σ g[n]x[2m+n]；因果实现用反向 tap，再按保存 slice 取内区间。',16)
    svg.text(80,120,'A  保存的离散矩：连续消失矩仍须先有合法尺度函数',20)
    headers=[('mask',80),('Σ g',320),('Σ n g',540),('Σ n² g',760)]
    for text,x in headers:svg.text(x,156,text,16)
    for i,q in enumerate(r['filters']):
        y=191+i*30
        svg.text(80,y,q['name'],16)
        for n,v in enumerate(q['g_discrete_moments_0_1_2']):svg.text(320+220*n,y,f'{v:.8g}',16)
    svg.text(80,290,'db2 h = '+', '.join(f'{v:.6f}' for v in f['db2_mask']['h']),15)
    top=390
    allv=[v for q in r['filters'] for v in q['polynomials'][1]['full_zero_extended_output']]
    high=max(allv);low=min(allv);pad=max(1,(high-low)*.12)
    count=max(len(q['polynomials'][1]['full_zero_extended_output']) for q in r['filters'])
    xy=svg.panel(top,'B  同一有限斜坡：完整零延拓输出（包括两端）',[0,count-1],[low-pad,high+pad],'输出序号 r；卷积索引 n=2r+1')
    for i,q in enumerate(r['filters']):
        out=q['polynomials'][1]['full_zero_extended_output']
        svg.text(80+i*310,top-20,q['name'],15,COLORS[i])
        pts=[xy(n,v) for n,v in enumerate(out)]
        svg.path(pts,COLORS[i],['','8,4','3,4'][i])
        for x,y in pts:svg.circle(x,y,COLORS[i])
    svg.text(80,660,'C  sparse QMF 的单位积分 refinement 解，不是连续正交尺度基',20)
    q=r['sparse_refinement'];a,b=q['support'];h=q['height']
    x=lambda t:100+(t-a)/(b+1-a)*900
    y0=840;y1=735
    svg.line(x(a),y0,x(b+1),y0,'#53687c',1.4)
    svg.parts.append(f'<rect x="{x(a+1)}" y="{y1}" width="{x(b)-x(a+1)}" height="{y0-y1}" fill="#d9e8ed"/>')
    svg.path([(x(a),y0),(x(a),y1),(x(b),y1),(x(b),y0)],COLORS[0])
    svg.path([(x(a+1),y0),(x(a+1),y1),(x(b+1),y1),(x(b+1),y0)],COLORS[1],'8,4')
    for t in range(a,b+2):svg.text(x(t),y0+25,t,15,anchor='middle')
    svg.text(100,700,f'高度 {h:.6g}；实线 φ*，虚线 φ*(τ−1)。重叠区 [1,3) 长2。',15)
    svg.text(100,916,f'保存 norm² = {q["norm_squared"]:.9g}；lag1 内积 = {q["integer_shift_1_inner_product"]:.9g}',17)
    svg.text(100,950,'阴影为两函数的重叠区；两函数实际高度同为1/3。',15)
    svg.text(100,991,'此反例通过离散偶移正交与低mask归一化，仍需另证连续平移和cascade。',16)
    svg.text(100,1025,'边界非零不反驳内区间消多项式；输入零延拓后已不再是全局斜坡。',15)
    svg.save(output/'moments.svg')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=json.loads(a.results.read_text())
    a.output.mkdir(parents=True,exist_ok=True)
    projections(r,a.output);moments(r,a.output)


if __name__=='__main__':main()
