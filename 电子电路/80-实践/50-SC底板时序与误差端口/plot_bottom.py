#!/usr/bin/env python3
"""SVG from saved ledger only; schematic states implement the declared port table."""
import argparse
from html import escape
from fractions import Fraction as F
import json
from pathlib import Path
FONT='Arial Unicode MS,PingFang SC,Noto Sans CJK SC,system-ui,sans-serif'
C=['#246bb0','#b9502c','#218261']
class SVG:
    def __init__(self,title,desc,height):
        self.p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" viewBox="0 0 1100 {height}" role="img"><title>{escape(title)}</title><desc>{escape(desc)}</desc><rect width="1100" height="{height}" fill="white"/><g font-family="{FONT}" fill="#172433">']
    def text(self,x,y,s,z=16,col='#172433',anchor='start'):self.p.append(f'<text x="{x}" y="{y}" font-size="{z}" fill="{col}" text-anchor="{anchor}">{escape(str(s))}</text>')
    def line(self,x1,y1,x2,y2,col='#72869a',width=1.5,dash=''):self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{width}" stroke-dasharray="{dash}"/>')
    def poly(self,pts,col,width=2,dash=''):
        d=' '.join(('M' if k==0 else 'L')+f'{x:.3f},{y:.3f}' for k,(x,y) in enumerate(pts));self.p.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{width}" stroke-dasharray="{dash}"/>')
    def dot(self,x,y,col='#172433',radius=3):self.p.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{col}"/>')
    def cap(self,x,y,label):
        self.line(x-26,y,x-5,y);self.line(x-5,y-13,x-5,y+13);self.line(x+5,y-13,x+5,y+13);self.line(x+5,y,x+26,y);self.text(x,y-21,label,16,anchor='middle')
    def switch(self,x,y,label):
        self.line(x-28,y,x-16,y);self.line(x+16,y,x+28,y);self.line(x-16,y,x+12,y-14);self.text(x,y+26,label,15,anchor='middle')
    def panel(self,top,title,ys,n):
        left,right,h=85,1040,170;lo=min([0]+ys);hi=max([0]+ys)
        if lo==hi:hi=lo+1
        pad=.1*(hi-lo);lo-=pad;hi+=pad
        self.text(left,top-45,title,20);self.text(30,top-12,'V',14)
        def pos(x,y):return left+x/max(1,n-1)*(right-left),top+h-(y-lo)/(hi-lo)*h
        for k in range(5):
            v=lo+k*(hi-lo)/4;_,yy=pos(0,v);self.line(left,yy,right,yy,'#dce3ea',1);self.text(left-12,yy+5,f'{v:.3g}',14,anchor='end')
        for i in range(n):
            xx,_=pos(i,lo);self.text(xx,top+h+23,i,14,anchor='middle')
        self.text(right,top+h+47,'原样点 n（全部保留）',15,anchor='end');return pos
    def curve(self,values,pos,color,dash=''):
        pts=[pos(i,v) for i,v in enumerate(values)];self.poly(pts,color,2,dash)
        for xx,yy in pts:self.dot(xx,yy,color,3.5)
    def save(self,path):Path(path).write_text('\n'.join(self.p+['</g></svg>'])+'\n')


def topology(r,out):
    c=r['inputs'];vcm=c['Vcm_absolute_V'];s=SVG('四开关SC的板端口和先断B协议','四个开关端点、永久反馈、局部参考与六步相位表；所有时钟耦合另列端点，图不代表真实PDK尺寸。',1120)
    s.text(48,40,'先断哪只开关：端点与浮动集合决定电荷',27)
    s.text(48,72,f'局部 0 = Vcm = {float(F(vcm)):g} V；clock绝对 {float(F(c["clock_high_absolute_V"])):g}→{float(F(c["clock_low_absolute_V"])):g} V。开关图画端点，状态在下表。',16)
    s.text(65,220,'Vcm+x',18);s.line(135,220,162,220);s.switch(190,220,'S_AX');s.line(218,220,300,220)
    s.dot(300,220);s.text(300,248,'A',18,anchor='middle');s.line(300,220,374,220);s.cap(400,220,'Cs');s.line(426,220,510,220);s.dot(510,220);s.text(530,249,'B',18,anchor='middle')
    s.line(510,220,582,220);s.switch(610,220,'S_Bs');s.line(638,220,740,220);s.dot(740,220);s.text(735,205,'s',18)
    s.line(300,220,300,165);s.line(300,165,300,110);s.text(310,142,'S_A0：A ↔ Vcm',15);s.text(300,94,'0',18,anchor='middle')
    s.line(510,220,510,335);s.text(522,298,'S_B0：B ↔ Vcm',15);s.text(510,360,'0',18,anchor='middle')
    # Branch labels explicitly define controlled switches, not a permanent wire.
    s.p.append('<rect x="292" y="139" width="16" height="22" fill="white"/>');s.line(300,160,310,142)
    s.p.append('<rect x="502" y="280" width="16" height="24" fill="white"/>');s.line(510,303,520,284)
    s.line(740,220,740,280);s.line(740,280,800,280);s.poly([(800,260),(800,340),(900,300),(800,260)],'#172433')
    s.text(809,286,'−',18);s.text(809,325,'+',18);s.text(837,305,'OTA',17);s.line(800,320,775,320);s.line(775,320,775,350);s.text(775,372,'0',18,anchor='middle')
    s.line(900,300,1020,300);s.text(1020,325,'Vcm+y',17,anchor='end');s.line(1000,300,1000,140);s.line(1000,140,880,140);s.cap(854,140,'Cf');s.line(828,140,740,140);s.line(740,140,740,220)
    s.text(58,425,'给定线性支路（下列端点也是图的一部分）',20)
    rows=[('CpA：A ↔ Vcm','CpB：B ↔ Vcm'),('CgA：A ↔ gA','CgB：B ↔ gB'),('Ccross：B ↔ gA','Cf：s ↔ 输出；s并非永久接地')]
    for j,(a,b) in enumerate(rows):s.text(80,460+31*j,a,17);s.text(555,460+31*j,b,17)
    s.text(58,585,'B先断的完整次序（闭/断按实际端点，不按波形颜色猜）',20)
    headers=['阶段','S_AX','S_B0','S_A0','S_Bs','约束/浮置'];xs=[65,310,425,540,655,765]
    for x,h in zip(xs,headers):s.text(x,625,h,16)
    states=[['track','闭','闭','断','断','A=x，B=0'],['B先释放','闭','断','断','断','A=x，B浮动'],['A后释放','断','断','断','断','A/B均浮动'],['A回参考','断','断','闭','断','A=0，B浮动'],['转移/读w','断','断','闭','闭','B=s，逐窗建立'],['s侧释放','断','断','闭','断','Cf孤立，随后恢复']]
    for j,row in enumerate(states):
        yy=665+43*j;s.line(58,yy+13,1040,yy+13,'#e1e6ec',1)
        for x,val in zip(xs,row):s.text(x,yy,val,16,C[2] if val=='闭' else '#172433')
    s.text(58,985,'下拍先将B接回参考；A从参考切回输入时仍需break-before-make，不能把互斥开关重叠。',16)
    s.text(58,1020,'B净自由电荷守恒 ≠ 只看Cs单板；clock与参考源可经电容提供位移电流。',17)
    s.text(58,1055,'本图是给定q/C线性端口模型；5V clock不表示任意工艺耐压已经验证。',16)
    s.save(out/'topology.svg')


def budget(r,out):
    n=len(r['inputs']['x_V']);ideal=r['nominal_ideal_after_V'];seq=r['sequences'];s=SVG('同一输入的断开顺序与端口误差','全部四样点的精确电荷模型与有限OTA轨迹，末状态顺序差量；差量是确定望远镜分解，不是独立随机RMS。',1200)
    s.text(48,40,'保护一条信号路径，不保证总偏差自动变小',27)
    s.text(48,72,'同一相对输入、Cs/Cf、clock与given q；图只读results.json，不补造PDK数据。',16)
    vals=[ideal,[float(F(x['y_after_off_V'])) for x in seq['bottom_first']],[float(F(x['y_after_off_V'])) for x in seq['input_first']]]
    pos=s.panel(160,'A  充分建立：BF先断B、AF反序；读off后的恢复值',sum(vals,[]),n)
    for i,(label,value) in enumerate(zip(['理想无packet','BF含注入/馈通/off','AF同参数'],vals)):
        s.text(88+310*i,139,label,15,C[i]);s.curve(value,pos,C[i],'' if i==0 else '5,3' if i==2 else '')
    finite=r['finite_cases'];keys=['finite_actual_caps','plus_off','plus_clock'];vals=[[x['y_next_V'] for x in finite[k]] for k in keys]
    pos=s.panel(465,'B  有限OTA：明确读下一y，不把w当相同状态',sum(vals,[]),n)
    for i,(label,value) in enumerate(zip(['实际电容/无packet','再加channel/feed/off','再加确定clock偏移'],vals)):
        s.text(88+310*i,444,label,15,C[i]);s.curve(value,pos,C[i],'' if i<2 else '5,3')
    s.text(65,750,'C  最后状态的顺序差量（mV）：按表顺序相加，不能RSS',21)
    labels=['有限OTA名义','实际电容','通道包','馈通','反馈off包','确定clock变化']
    bar_scale=330/max(1,max(abs(d['delta_y_V'][-1]*1000) for d in r['controlled_telescope']))
    for j,(label,d) in enumerate(zip(labels,r['controlled_telescope'])):
        yy=790+38*j;v=d['delta_y_V'][-1]*1000;s.text(85,yy,label,17);s.text(365,yy,f'{v:+.9f}',17,anchor='end')
        center=650;end=center+v*bar_scale;s.line(center,yy-7,end,yy-7,C[0] if v>=0 else C[1],13);s.line(center,yy-22,center,yy+10,'#a5b0bc',1)
    s.text(65,1060,f'同一实际窗口的所选噪声方差小计：{r["selected_noise"]["selected_total_V2"]:.9g} V²；不是全硬件RMS。',17)
    s.text(65,1095,'未知参考/转移热源/有色OTA与其交叉项在正文保留端口、状态和协方差接口。',16)
    s.text(65,1130,'确定轨迹摆幅须检查相起点y、转移末w、恢复末y；过载后的线性值仅作失败证据。',16)
    s.text(65,1165,'颜色外仍以标签/虚线区分；横轴显示全部原样点，纵轴与差量单位分开。',15)
    s.save(out/'budget.svg')


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args();r=json.loads(args.results.read_text());args.out.mkdir(parents=True,exist_ok=True);topology(r,args.out);budget(r,args.out)
if __name__=='__main__':main()
