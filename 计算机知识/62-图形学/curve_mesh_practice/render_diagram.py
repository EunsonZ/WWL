import argparse,json
from pathlib import Path


def draw(actual):
    c=actual['cases'][0];P=c['control'];points=c['curve_points'];pos=c['positions']
    def xy(p,offset=80):return offset+180*p[0],400-120*p[1]
    def seq(points,offset):return ' '.join(f'{xy(p,offset)[0]:.3f},{xy(p,offset)[1]:.3f}' for p in points)
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="660" viewBox="0 0 1050 660" role="img" aria-labelledby="title desc">',
       '<title id="title">控制点、曲线采样点与索引网格分别是什么</title>',
       '<desc id="desc">左侧灰虚线为控制多边形，黑实线二次曲线，蓝点是N4样本。右侧同一采样的Y总跨度0.25窄带，十顶点八三角形，索引按正Z绕序。下表误差来自同一actual.json。</desc>',
       '<rect width="1050" height="660" fill="white"/><g font-family="PingFang SC,sans-serif" fill="#172b44">',
       '<text x="35" y="40" font-size="25">控制点通常不在曲线上；样本与连接一起决定网格</text>',
       '<text x="35" y="78" font-size="18">对象空间XY，横纵显示缩放不同，勿据图量角/距离；+Z向读者，右图为数组下标</text>',
       f'<polyline points="{seq(P,80)}" fill="none" stroke="#8b8b8b" stroke-dasharray="7 5"/>']
    a,b,d=[xy(p) for p in P];s.append(f'<path d="M{a[0]} {a[1]} Q{b[0]} {b[1]} {d[0]} {d[1]}" fill="none" stroke="#171717" stroke-width="3"/>')
    for i,p in enumerate(P):
        x,y=xy(p);s.append(f'<rect x="{x-5}" y="{y-5}" width="10" height="10" fill="white" stroke="#666"/><text x="{x+9}" y="{y-12}" font-size="16">P{i} 控制点</text>')
    s.append(f'<polyline points="{seq(points,80)}" fill="none" stroke="#1c70b0" stroke-width="2"/>')
    for i,p in enumerate(points):
        x,y=xy(p);s.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#1c70b0"/><text x="{x-12}" y="{y+25}" font-size="14">t={c["parameters"][i]:g}</text>')
    for i,face in enumerate(c['triangles']):
        vertices=[pos[j] for j in face];s.append(f'<polygon points="{seq(vertices,590)}" fill="{"#dce9fb" if i%2 else "#eef3fc"}" stroke="#44627e"/>')
    for i,p in enumerate(pos):
        x,y=xy(p,590);dy=19 if i%2==0 else -8;s.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#244b71"/><text x="{x+5}" y="{y+dy}" font-size="14">{i}</text>')
    s.extend(['<text x="35" y="465" font-size="18">同参数点到折线点的最大距离（非最近点距离）</text>',
              '<text x="35" y="502" font-size="16">几何</text><text x="280" y="502" font-size="16">误差</text><text x="450" y="502" font-size="16">顶点/边/面</text><text x="690" y="502" font-size="16">64px覆盖数</text>'])
    for i,c in enumerate(actual['cases']):
        t=c['topology'];y=535+25*i;s.append(f'<text x="35" y="{y}" font-size="16">{c["id"]}</text><text x="280" y="{y}" font-size="16">{c["exact_matched_parameter_max"]:.8g}</text><text x="450" y="{y}" font-size="16">{t["V"]}/{t["E"]}/{t["F"]}</text><text x="690" y="{y}" font-size="16">{c["renders"][0]["covered_pixels"]}</text>')
    s.append('</g></svg>');return '\n'.join(s)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--actual',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.write_text(draw(json.loads(a.actual.read_text())))
if __name__=='__main__':main()
