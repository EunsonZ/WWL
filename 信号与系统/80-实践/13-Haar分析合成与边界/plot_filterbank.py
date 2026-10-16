#!/usr/bin/env python3
"""Two bounded SVGs read only the saved Haar experiment JSON."""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

FONT='Arial Unicode MS,PingFang SC,Noto Sans CJK SC,system-ui,sans-serif'
BLUE='#3266a5';ORANGE='#b46314';GREEN='#27765d';PURPLE='#923a81'


class SVG:
    def __init__(self,title,desc,height):
        self.a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="940" height="{height}" viewBox="0 0 940 {height}" role="img" aria-labelledby="title desc">',
                f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>',
                f'<rect width="940" height="{height}" fill="white"/>',
                f'<g font-family="{FONT}" font-size="14" fill="#203142">']
        self.text(30,32,title,22)
    def text(self,x,y,s,size=14,color='#203142'):
        self.a.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}">{escape(str(s))}</text>')
    def line(self,x1,y1,x2,y2,color='#ced6df',dash=''):
        self.a.append(f'<path d="M{x1:.2f} {y1:.2f} L{x2:.2f} {y2:.2f}" fill="none" stroke="{color}" stroke-dasharray="{dash}"/>')
    def dot(self,x,y,color,square=False):
        if square:self.a.append(f'<rect x="{x-4:.2f}" y="{y-4:.2f}" width="8" height="8" fill="white" stroke="{color}" stroke-width="2"/>')
        else:self.a.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="white" stroke="{color}" stroke-width="2"/>')
    def curve(self,points,color,dash=''):
        pts=' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
        self.a.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>')
    def panel(self,top,N,low,high,title):
        self.text(30,top-48,title,18)
        bottom=top+160;left,right=90,865
        x=lambda n:left+25+(right-left-50)*n/max(1,N-1)
        y=lambda v:bottom-(v-low)/(high-low)*160
        for n in range(N):self.line(x(n),top,x(n),bottom);self.text(x(n)-4,bottom+21,n)
        for j in range(5):
            value=low+(high-low)*j/4;self.line(left,y(value),right,y(value));self.text(42,y(value)+4,f'{value:g}')
        self.line(left,top,left,bottom,'#35485b');self.line(left,bottom,right,bottom,'#35485b')
        self.text(870,bottom+22,'n');self.text(30,top-12,'V')
        return x,y
    def save(self,p):
        if p.exists():raise ValueError('output exists: '+str(p))
        p.write_text('\n'.join(self.a+['</g></svg>'])+'\n')


def draw(result,out):
    r=next(x for x in result['records'] if x['original_length']==4)
    vals=r['samples_V']+r['low_only_crop_V']+r['wrong_detail_sign_crop_V']
    lo=min(0,min(vals));hi=max(vals)*1.1 if max(vals)>0 else 1
    f=SVG('四点Haar：两支合起来恢复，删一支才改变信号',
          'The full pair transform is invertible and orthogonal. Correct synthesis, low-only reconstruction and a deliberately wrong detail sign are shown from the same saved samples. Units are V; energies are discrete squared norms in V squared.',790)
    f.text(35,60,'分析保留奇相位；合成插零在偶位置。无下标延迟，仍须等每对第二个样点。')
    x,y=f.panel(145,4,lo,hi,'A  同一输入与三种合成结果')
    series=[(r['samples_V'],'原输入 / 全系数恢复',BLUE,''),
            (r['low_only_crop_V'],'只留低支',ORANGE,'7 4'),
            (r['wrong_detail_sign_crop_V'],'合成细节符号反号',PURPLE,'3 4')]
    for j,(values,label,color,dash) in enumerate(series):
        f.text(105+j*260,119,label,14,color)
        f.curve([(x(k),y(v)) for k,v in enumerate(values)],color,dash)
        for k,v in enumerate(values):f.dot(x(k),y(v),color,j==2)
    f.text(30,357,'B  两个低支系数 + 两个细节系数 = 四个自由度',18)
    for j in range(2):
        yy=404+j*66
        f.text(55,yy,f'输入对 {j}: ({r["samples_V"][2*j]:g}, {r["samples_V"][2*j+1]:g})')
        f.text(300,yy,f'a[{j}]={r["a_V"][j]:.6g} V',16,BLUE)
        f.text(550,yy,f'd[{j}]={r["d_V"][j]:.6g} V',16,ORANGE)
        f.line(235,yy-5,280,yy-5,'#35485b');f.text(250,yy-12,'→')
        f.text(775,yy,'合成 → 原输入',14,GREEN)
    low_energy=r['coefficient_squared_norm_V2']-r['detail_squared_norm_V2']
    f.text(35,550,f'离散平方和：{r["input_squared_norm_V2"]:g} = 低支 {low_energy:g} + 细节 {r["detail_squared_norm_V2"]:g} V²',18)
    f.text(35,591,f'删细节误差 {r["low_only_crop_error_V2"]:g} V²；仅改合成细节符号，误差 {r["wrong_detail_sign_error_V2"]:g} V²。',16)
    c=result['two_level_coefficients']
    f.text(35,648,'C  再拆低支：同一四点的两级Haar',18)
    f.text(55,685,f'a₂={c["a2_V"][0]:g} V，d₂={c["d2_V"][0]:g} V；平方和 {sum(v*v for v in c["a2_V"]):g} + {sum(v*v for v in c["d2_V"]):g} + {sum(v*v for v in c["d1_V"]):g} V²',15)
    f.text(35,748,'全输入PR来自任意一对的代数恒等；固定N的全部basis另核实现，不从一次素材重建推全输入。',13)
    f.save(out/'haar.svg')

    odd=len(result['inputs']['odd_samples_V'])
    rows=[z for z in result['records'] if z['original_length']==odd]
    zero=next((z for z in rows if z['boundary']=='zero'),rows[0])
    repeat=next((z for z in rows if z['boundary']=='repeat'),rows[-1])
    allvalues=zero['samples_V']+zero['low_only_crop_V']+repeat['low_only_crop_V']
    lo=min(0,min(allvalues));hi=max(allvalues)*1.1 if max(allvalues)>0 else 1
    f=SVG('奇长度边界与非正交：可逆不等于每种能量账都相同',
          'All coefficients reconstruct the original after explicit extension and cropping. Zero and repeat-right extension give different low-only endpoints and coefficient squared norms. A finite nonorthogonal shear is invertible but is not Parseval.',815)
    f.text(35,60,f'原长度 N={odd}，先保存原N/边界；补到偶数，完整合成后再裁回原域。')
    x,y=f.panel(140,odd,lo,hi,'A  全系数在所列边界可恢复；删细节后的端点另核')
    for j,(rr,label,color,dash) in enumerate([(zero,'原输入',BLUE,'')]+[(rr,rr['boundary']+'低保留',[ORANGE,GREEN][j],'7 4' if j==0 else '3 4') for j,rr in enumerate(rows)]):
        values=rr['samples_V'] if j==0 else rr['low_only_crop_V']
        f.text(100+j*260,114,label,14,color);f.curve([(x(k),y(v)) for k,v in enumerate(values)],color,dash)
        for k,v in enumerate(values):f.dot(x(k),y(v),color,j==2)
    f.text(30,353,'B  原输入、延拓/系数能量与原域误差分别记账',18)
    for j,(col,label) in enumerate([(35,'边界'),(190,'原域平方和'),(390,'系数平方和'),(610,'删d后原域误差')]):f.text(col,394,label,15)
    f.line(35,405,890,405)
    for i,rr in enumerate(rows):
        yy=445+i*47
        f.text(35,yy,rr['boundary']);f.text(190,yy,f'{rr["input_squared_norm_V2"]:g} V²')
        f.text(390,yy,f'{rr["coefficient_squared_norm_V2"]:g} V²');f.text(610,yy,f'{rr["low_only_crop_error_V2"]:g} V²')
    lam=result['inputs']['shear_lambda']
    f.text(35,575,f'C  四点可逆shear：a′=a+({lam:g})d，d′=d（有限双基，非连续小波构造）',17)
    relation='=' if abs(r['shear_coefficient_squared_norm_V2']-r['input_squared_norm_V2'])<1e-10 else '≠'
    f.text(55,617,f'全留仍恢复；系数平方和 {r["shear_coefficient_squared_norm_V2"]:g} V² {relation} 原 {r["input_squared_norm_V2"]:g} V²。',16)
    f.text(55,657,f'删d′后恢复 {tuple(round(v,6) for v in r["shear_low_only_crop_V"])}，误差 {r["shear_low_only_error_V2"]:g} V²。',15)
    kind='斜投影' if lam!=0 else '正交投影'
    f.text(55,700,f'原四维低保留为{kind}；奇长zero裁剪不幂等，不能统称为原域正交投影。',14)
    f.text(35,768,'图只读取results.json。无真实采集、量化码率或去噪真值验证；原生Obsidian显示单独验收。',13)
    f.save(out/'boundary.svg')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    draw(json.loads(args.results.read_text()),args.output)
    print(args.output/'haar.svg');print(args.output/'boundary.svg')


if __name__=='__main__':main()
