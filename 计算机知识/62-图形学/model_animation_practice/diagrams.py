"""Figures derived from the same recorded meshes/traces; no AI illustration or external scene."""
import argparse,json,math
from pathlib import Path


def header(w,h,title):return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"><title>{title}</title><rect width="100%" height="100%" fill="white"/><g font-family="PingFang SC,sans-serif" fill="#16304c">']
def text(x,y,s,size=18):return f'<text x="{x}" y="{y}" font-size="{size}">{s}</text>'


def geometry(actual):
    svg=header(1100,430,'解析曲面重采样与Loop平滑改变不同对象');svg+=[text(25,35,'解析曲面重采样与 Loop 平滑：更多面不自动等于原形状更准',25),text(25,68,'线框取自 actual.json，使用同一对象空间斜投影；这不是相机渲染或等比例测量图',17)]
    meshes=[actual['patches'][-1],actual['loop'][0],actual['loop'][-1]];labels=['解析曲面 N8','Loop 控制网格 level0','Loop level2（边界也移动）']
    for k,(mesh,label) in enumerate(zip(meshes,labels)):
        center=180+365*k
        def xy(p):x,y,z=p;return center+70*(x-y),300-35*(x+y)-130*z
        edges={tuple(sorted((a,b))) for f in mesh['triangles'] for a,b in zip(f,f[1:]+f[:1])}
        for a,b in sorted(edges):
            x,y=xy(mesh['positions'][a]);u,v=xy(mesh['positions'][b]);svg.append(f'<line x1="{x:.4f}" y1="{y:.4f}" x2="{u:.4f}" y2="{v:.4f}" stroke="#3f7797" stroke-width="1.2"/>')
        top=mesh['topology'];svg += [text(center-150,110,label,18),text(center-150,350,f'V/E/F = {top["V"]}/{top["E"]}/{top["F"]}'),text(center-150,379,f'边界边 {top["boundary_count"]}；Euler = {top["chi"]}',17)]
    svg += [text(25,415,'Loop 的中心高度 .5 → .375 → .34375；原解析曲面中心仍为 .5m。',17),'</g></svg>'];return '\n'.join(svg)+'\n'


def motion(actual,spec):
    svg=header(1100,680,'同一对象独立改变几何分段N和积分步长h');svg += [text(25,35,'同一对象：几何 N 与时间 h 是两个独立旋钮',25),text(25,70,'固定弹簧 ω=2/s，T=1s；上图是根节点位置 q(t)，下表取同一网格与完整状态误差',17)]
    def xy(t,q):return 95+900*t,335-210*q
    for value in [-.5,0,.5,1]:
        x,y=xy(0,value);svg += [f'<line x1="95" y1="{y}" x2="995" y2="{y}" stroke="#ddd"/>',text(40,y+5,f'{value:g}',15)]
    for value in [0,.25,.5,.75,1]:x,y=xy(value,-.5);svg.append(text(x-10,465,f'{value:g}',15))
    series=[('解析解','#222',[(i/100,math.cos(spec['spring']['omega']*i/100)) for i in range(101)])]
    for method,color in [('explicit','#be4d22'),('symplectic','#176ab0')]:
        row=next(x for x in actual['spring'] if x['method']==method and x['h']==.25);series.append((method+' h=.25',color,[(x['time'],x['q']) for x in row['trace']]))
    for k,(name,color,points) in enumerate(series):
        seq=' '.join(f'{xy(t,q)[0]:.4f},{xy(t,q)[1]:.4f}' for t,q in points);svg.append(f'<polyline points="{seq}" fill="none" stroke="{color}" stroke-width="2.5"/>');svg.append(f'<text x="{160+280*k}" y="105" font-size="17" fill="{color}">{name}</text>')
    svg += [text(1005,466,'t/s',15),text(25,129,'q/m',15)]
    for x,label in [(40,'N'),(180,'h/s'),(350,'几何误差/m'),(580,'位置误差/m'),(825,'状态误差/m')]:svg.append(text(x,515,label,17))
    for i,row in enumerate(actual['comparison']):
        y=550+27*i
        for x,value in [(40,row['n']),(180,row['h']),(350,row['geometry_error']),(580,row['q_error']),(825,row['phase_state_error'])]:svg.append(text(x,y,f'{value:.7g}',17))
    svg += [text(25,671,'状态误差 = √[(q−q*)² + ((v−v*)/ω)²]；没有把 m 与 m/s 直接相加。',16),'</g></svg>'];return '\n'.join(svg)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--actual',type=Path,required=True);p.add_argument('--spec',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True);a=p.parse_args();d=json.loads(a.actual.read_text());s=json.loads(a.spec.read_text());(a.out_dir/'geometry.svg').write_text(geometry(d));(a.out_dir/'motion.svg').write_text(motion(d,s))
if __name__=='__main__':main()
