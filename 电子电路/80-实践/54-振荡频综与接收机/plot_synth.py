"""Draw only stored evidence. Fixed-card layout, no numerical model imports."""
import argparse,gzip,json,math
from pathlib import Path
from html import escape
COL=['#176b97','#c25b23','#19866c','#9b497d']
def txt(x,y,s,size=19,fill='#17293a'):
 return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}">{escape(str(s))}</text>'
def path(points,color,width=2):
 return '<polyline fill="none" stroke="'+color+'" stroke-width="'+str(width)+'" points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in points)+'"/>'
def box(x,y,w,h,label):
 return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#e9f1f6" stroke="#55778c"/>'+txt(x+12,y+h/2+7,label)
def chart(x,y,w,h,lines,xr,yr,logx=False,logy=False):
 def sc(v,r,log):
  a,b=r
  return (math.log10(v)-math.log10(a))/(math.log10(b)-math.log10(a)) if log else (v-a)/(b-a)
 s=path([(x,y),(x,y+h),(x+w,y+h)],'#7b8791',1)
 for a,b in lines:
  pts=[(x+w*sc(v[0],xr,logx),y+h-h*sc(max(v[1],yr[0]) if logy else v[1],yr,logy)) for v in a if xr[0]<=v[0]<=xr[1] and (not logy or v[1]>0)]
  s+=path(pts,b,2)
 return s

def write(out,name,title,desc,body,h=960):
 s=f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{h}" viewBox="0 0 1200 {h}"><title>{escape(title)}</title><desc>{escape(desc)}</desc><rect width="1200" height="{h}" fill="#fafcfe"/><g font-family="PingFang SC,Noto Sans CJK SC,sans-serif">'+txt(35,42,title,28)+body+'</g></svg>\n'
 (out/(name+'.svg')).write_text(s)

def main(root,out):
 d=json.loads((root/'results/results.json').read_text());osc=json.loads((root/'oscillator/summary.json').read_text());out.mkdir(parents=True,exist_ok=True)
 s=txt(35,78,'同一 LEVEL1 两管：实际启动与稳幅；确定性波形不提供相噪',19)
 s+=path([(110,125),(1000,125)],'#435869',2)+txt(40,131,'1.8V')
 for x,name,gate in [(330,'M1','gate ← dn'),(800,'M2','gate ← dp')]:
  s+=path([(x,125),(x,165),(x+12,175),(x-12,190),(x+12,205),(x,215),(x,250)],'#435869',2)+txt(x+24,185,'10Ω + 100nH')
  s+=box(x-65,270,130,55,name)+txt(x-60,350,gate,17)
  s+=path([(x,325),(x,390),(565,390)],'#435869',2)
  s+=path([(x,250),(x+140,250),(x+140,290)],'#435869',2)+txt(x+115,322,'25pF → 0',16)
  s+=txt(x-35,245,'dp' if name=='M1' else 'dn')
 s+=path([(565,390),(565,420)],'#435869',2)+txt(590,414,'共同源 s → 理想尾流 2mA → 0')
 s+=txt(35,460,'启动窗 0..200ns：v(dp)−v(dn)，V；每条为真实非均匀样点（显示抽点）')
 lines=[]
 for name,col in zip(['nominal','zero_seed','low_tail'],COL):
  # Raw compact columns are t, differential voltage, common mode.
  import io
  import numpy as np
  a=np.loadtxt(io.BytesIO(gzip.decompress((root/'oscillator'/name/'startup.csv.gz').read_bytes())),delimiter=',',skiprows=1)
  stride=max(1,len(a)//2500);lines.append(([(t*1e9,v) for t,v,cm in a[::stride]],col))
 s+=chart(80,495,1000,180,lines,[0,200],[-1.05,1.05])+txt(25,500,'+1')+txt(25,590,'0')+txt(25,680,'−1')+txt(80,705,'0 ns')+txt(990,705,'200 ns')
 s+=txt(300,487,'蓝：名义；橙：零显式种子；绿：尾流1µA',16)
 s+=txt(35,750,'late 1..2µs：有种子/零显式种子均稳幅；低尾流衰减。中间窗未画，未补直线。')
 s+=txt(35,792,'方案',18)+txt(300,792,'实际频率 MHz',18)+txt(570,792,'差分峰值 V',18)+txt(850,792,'供电平均 mW',18)
 for j,(name,label) in enumerate([('nominal','名义'),('zero_seed','零显式种子'),('low_tail','尾流 1µA'),('cap30p','每侧 C=30pF'),('nominal_5ps','名义 5ps步长')]):
  q=osc[name];f=q['frequency_Hz'];yy=825+j*30
  s+=txt(35,yy,label,18)+txt(300,yy,'无稳态周期' if f is None else f'{f/1e6:.6f}',18)+txt(570,yy,f'{q["peak_diff_V"]:.6g}',18)+txt(850,yy,f'{q["supply_mean_W"]*1e3:.6f}',18)
 write(out,'oscillator','负电导负责启动，MOS换向负责稳幅','两侧电路与真实启动窗、晚期频率振幅功率。零种子浮点启动不是物理噪声。',s,1020)
 s=txt(35,82,'PFD ±100µA → 串联 R+C → u=clip(z+RI) → VCO → ÷10；同沿1fs数值容差')
 for x,w,label in [(40,180,'10MHz参考'),(265,150,'边沿PFD'),(460,180,'CP / R+C'),(685,210,'VCO 82..118MHz'),(940,170,'÷10反馈')]:s+=box(x,110,w,55,label)
 s+=txt(40,205,'三种 R：1k / 2k / 8kΩ；C=10nF。噪声传递只在锁定邻域，积分100Hz..1MHz。')
 sp=d['PLL']['balanced'];lines=[]
 for j,col in [(1,COL[0]),(2,COL[1])]:lines.append(([(x[0],x[j]) for x in sp['grid']],col))
 s+=chart(100,255,980,190,lines,[100,1e6],[1e-16,1e-10],True,True)
 s+=txt(40,245,'R=2kΩ 输出相位 PSD rad²/Hz（对数）')+txt(35,273,'1e−10',15)+txt(35,450,'1e−16',15)+txt(100,474,'100Hz')+txt(960,474,'1MHz')+txt(400,480,'蓝：N²|T|²Sr；橙：|S|²Sv')
 s+=txt(40,525,'R=2k：低端初态 z=.2V 与超出调谐目标120MHz；电容电压 z [V]')
 lines=[]
 for idx,col in [(1,COL[0]),(3,COL[1])]:
  item=d['dynamics']['balanced'][idx];a=json.loads(gzip.decompress((root/'results'/item['trace_file']).read_bytes()));stride=max(1,len(a)//2200);lines.append(([(x[0]*1e3,x[1]) for x in a[::stride]],col))
 s+=chart(100,560,980,180,lines,[0,1],[0,6.3])+txt(45,572,'6.3')+txt(65,743,'0')+txt(100,772,'0ms')+txt(1010,772,'1ms')+txt(430,772,'橙色 z继续积分，不是调谐端可超1.8V')
 s+=txt(40,820,'R [kΩ]',18)+txt(300,820,'交越 kHz',18)+txt(550,820,'相位裕度 °',18)+txt(820,820,'带内 RMS抖动 fs',18)
 for j,(name,v) in enumerate(d['PLL'].items()):
  R=next(x['R_ohm'] for x in d['input']['pll']['designs'] if x['name']==name);y=855+j*32
  s+=txt(40,y,f'{R/1000:g}',18)+txt(300,y,f'{v["unity_Hz"]/1000:.3f}',18)+txt(550,y,f'{v["PM_deg"]:.3f}',18)+txt(820,y,f'{v["jitter_s"]*1e15:.3f}',18)
 write(out,'pll','局部相位预算与大频差捕获分开核','同卡双噪声通路和真实边沿PFD积分；超调谐失败与三种R的局部指标。',s,995)
 r=d['RX'];s=txt(35,82,'下列为显式单向/匹配模块模型，不是两旧MOS电路的实际物理级联。')
 for x,w,label in [(30,180,'前置损耗 L'),(240,160,'CG 输出1kΩ'),(430,250,'缓冲1k→差分50Ω'),(710,210,'基波混频到10MHz'),(950,210,'IF增益100')]:s+=box(x,115,w,65,label)
 s+=txt(35,235,'相同110MHz希望 / 130与150MHz等功率阻塞：前衰减减少三阶失真，也损害NF和灵敏度。')
 heads=[(35,'L'),(150,'NF dB'),(330,'总增益 dB'),(540,'C/IM3 dB'),(750,'未选频峰值 √W'),(1000,'联合结果')]
 for x,label in heads:s+=txt(x,292,label,18)
 for j,row in enumerate(r['stress']):
  yy=340+j*55;passed=all(row['budget_checks'].values());vals=[row['preloss'],f'{row["NF_dB"]:.3f}',f'{10*math.log10(row["gain"]):.3f}',f'{row["C_to_IM3_dB"]:.3f}',f'{row["preselection_peak_sqrtW"]:.5f}','PASS' if passed else 'FAIL']
  for (x,_),val in zip(heads,vals):s+=txt(x,yy,val,21,COL[2] if passed else COL[1])
 s+=txt(35,530,'标称远偏移LO谱：20/40/40/60MHz四项，不外推低偏移PLL连续模型。')
 s+=txt(35,575,f'无衰减热噪声 {r["output_PSD_W_per_Hz"]*1e5:.4g} W / RM {r["reciprocal_mixing"][0]["total_W"]:.4g} W；B=100kHz。')
 s+=txt(35,620,'L=4时：名义带外谱 SNR=24.924dB；只将带外谱×10 →23.608dB，原带内抖动不变。')
 s+=txt(35,665,'预算：NF≤19dB，增益≥8dB，C/IM3≥35dB，峰值≤.01√W，SNR≥24.5dB。')
 s+=txt(35,720,f'功耗合计 {d["joint_budget"]["power_W"]*1e3:.6f}mW：LC/CG来自实际Q，其余缓冲/IF/驱动/控制为声明卡。')
 s+=txt(35,775,'R=2k的477.345fs与L=4名义谱同时通过；强带外谱使SNR失败，不能只挑最低抖动。')
 s+=txt(35,840,'立方IM3是同频相干干扰，单独报C/IM3；未把它伪装成随机热噪声加进NF。')
 write(out,'receiver','同一接收机：少一点阻塞，付出多少噪声代价','显式参考面、前置损耗的联合预算、带外相噪变式与真实/声明功耗边界。',s,920)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=Path(__file__).parent);a.add_argument('--out',type=Path,required=True);z=a.parse_args();main(z.root,z.out)
