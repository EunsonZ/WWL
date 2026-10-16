"""SVG figures from the same frozen spec/results; no simulator or circuit re-execution."""
import argparse,html,json,math
from pathlib import Path


def text(x,y,v,size=16,color='#24364b',anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(v))}</text>'

def line(x,y,a,b,color='#64788e',dash=''):
    return f'<path d="M{x} {y} L{a} {b}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>'

def box(x,y,w,h,label):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#edf3f9" stroke="#64788e"/>'+text(x+w/2,y+h/2+6,label,17,anchor='middle')

def doc(w,h,title,parts):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><title>{html.escape(title)}</title><desc>同一11MOS及显式输入RC/跨节点补偿的有限教学模型；数据从固定spec/results读取，不是工艺或硅测量。</desc><rect width="100%" height="100%" fill="#f8fafc"/><g font-family="PingFang SC,sans-serif">'+''.join(parts)+'</g></svg>\n'


def make(lab,out):
    s=json.loads((lab/'spec.json').read_text());a=json.loads((lab/'results/results.json').read_text());c=a['cases']['balanced']['configuration'];out.mkdir(parents=True,exist_ok=True)
    p=[text(35,40,'原11管电路如何变为10个电压状态？',26),text(35,75,f'原09全部MOS/体端/偏置保留；图中框是该完整电路的层级接口，Rdet改为{c["rdet"]/1e6:g} MΩ',17),box(480,150,280,260,'原09：11 MOS + CMFB')]
    for y,n,drive in [(205,'gp','dp'),(335,'gm','dm')]:
        p += [text(35,y-25,drive+'：理想求和器输出',16),line(40,y,145,y),box(145,y-20,110,40,f'Rg {c["rgate"]/1e3:g} kΩ'),line(255,y,480,y),text(335,y-15,n,18),line(335,y,335,y+55),line(320,y+55,350,y+55),line(320,y+63,350,y+63),line(335,y+63,335,y+82),text(360,y+63,f'Cg {c["cgate"]*1e12:g} pF →0',15)]
    p += [text(35,455,f'dp/dm = Vic + uc ± [ud + {c["feedback"]:g}(op−om)]/2',19),text(35,488,'MOS输入在gp/gm；Rg也是实际热噪声源',17)]
    p += [line(760,195,900,195),text(785,180,'op',18),line(825,195,825,130),box(750,90,150,40,f'Co {c["cout"]*1e12:g}pF →0'),line(760,345,1030,345),text(785,330,'om',18),line(825,345,825,440),box(750,440,150,40,f'Co {c["cout"]*1e12:g}pF →0'),line(900,195,900,220),box(845,220,110,40,f'Cb {c["cbridge"]*1e12:g}pF'),line(900,260,900,270),line(1030,345,1030,315),box(975,275,110,40,f'Cb {c["cbridge"]*1e12:g}pF'),line(1030,275,1030,270),line(760,270,1170,270),text(775,253,'vc',18),box(1170,250,160,40,f'Cc {c["ccontrol"]*1e9:g}nF →0'),text(760,520,'两条桥电容接同一vc；所有→0明确表示接地',16),text(35,600,'对地Co/Cc与跨节点Cb分别盖章，不用两个对地Miller电容替掉前馈路径。',18),text(35,640,'C = diag(各节点对地C) + Cb(eop−evc)(eop−evc)ᵀ + Cb(eom−evc)(eom−evc)ᵀ',18),text(35,675,f'四个offdiag均−{c["cbridge"]*1e12:g} pF；gp/gm的差与均也要变换，差模块是2状态，不是原来的1状态',17)]
    (out/'network.svg').write_text(doc(1380,710,'新增RC与跨节点电荷连接',p))
    p=[text(35,40,'同Q点的一次补偿，改善了哪条环路？',26),text(35,73,'噪声积分1 Hz…100 kHz；单边PSD；输出RMS和逐频输入等效RMS分列',17)]
    xs=[35,200,305,430,555,690,825,990];labels=['设计','Co pF','Cc nF','DM PM°','CM PM°','DM µV','CM µV','输入等效 µV']
    for x,l in zip(xs,labels):p.append(text(x,118,l,16))
    for j,n in enumerate(['starting','dm_only','balanced','heavy_output']):
        r=a['cases'][n];v=r['linear'];vals=[n,f'{r["configuration"]["cout"]*1e12:g}',f'{r["configuration"]["ccontrol"]*1e9:g}',f'{v["cuts"]["dm"]["crossings"][0]["phase_margin_deg"]:.2f}',f'{v["cuts"]["cm"]["crossings"][0]["phase_margin_deg"]:.2f}',f'{v["noise_dm_rms_V"]*1e6:.2f}',f'{v["noise_cm_rms_V"]*1e6:.2f}',f'{v["input_equivalent_rms_V"]*1e6:.2f}']
        for x,val in zip(xs,vals):p.append(text(x,165+j*48,val,17,'#217653' if r['budget']['all_met'] else '#913c33'))
    p += [text(35,380,'仅加Co：差模裕度↑，共模裕度↓；再加Cc才同时过55°/60°。输出噪声下降不等于输入等效下降。',17),text(35,425,'balanced：同一输入端口，改变幅度后的响应',21)]
    x0,y0=80,700;ww,hh=720,215;p += [line(x0,y0-hh,x0,y0),line(x0,y0,x0+ww,y0),text(30,490,'1.2',15),text(30,525,'1',15),text(30,700,'0',15),text(75,730,'0',15),text(745,730,'150 µs',15)]
    traces=[(a['balanced_other_amplitudes'][0],'#386cad','5 3'),(a['cases']['balanced']['step'],'#287c57',''),(a['balanced_other_amplitudes'][1],'#bf642d','2 3')]
    for k,(tr,color,dash) in enumerate(traces):
        d0=tr['initial'][0]-tr['initial'][1];d1=tr['target'][0]-tr['target'][1];points=' '.join(f'{x0+ww*t/.00015:.3f},{y0-hh/1.2*(v-d0)/(d1-d0):.3f}' for t,v in zip(tr['time_s'],tr['differential_V']) if t<=.00015);p.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>');p += [text(840,495+k*65,f'ud ±{tr["input_step"][1]:g} V',16,color),text(840,518+k*65,f'平均斜率 {tr["average_10_90_slew_V_s"]/1e6:.4f} V/µs',15,color)]
    p += [text(35,775,'纵轴：(Vod−初态)/(本次最终Vod−初态)。±.35 V的大步已越过线性摆幅，归一化快不等于保真。',17),text(35,810,'节点电荷决定最大导数；10–90%平均斜率与1%建立时间分别从固定采样窗计算。',17)]
    (out/'tradeoff.svg').write_text(doc(1200,845,'两环补偿与非线性步进的代价',p))
    p=[text(35,40,'同一噪声源只数一次；确定角点也不等于良率',25),text(35,75,'balanced：1 Hz处逐源输出PSD；DM与CM分别列，单位V²/Hz，左→右不是信号增益',17)]
    row=a['cases']['balanced']['linear']['spectrum'][0];names=[r['name'] for r in a['cases']['balanced']['linear']['sources']]
    p += [text(35,120,'源',16),text(210,120,'DM PSD',16),text(450,120,'CM PSD',16),text(720,120,'15个实际注入端口',19)]
    for k,n in enumerate(names):
        y=153+k*25;p += [text(35,y,n,15),text(210,y,f'{row["dm_source_psd"][k]:.3e}',15),text(450,y,f'{row["cm_source_psd"][k]:.3e}',15)]
    p += [text(720,160,'M1…M11：漏→源的白电流源',16),text(720,195,'RDp/RDm：输出↔sense',16),text(720,230,'RGp/RGm：实际栅↔理想驱动',16),text(720,275,'单源经镜像/反馈分成多条响应，',16),text(720,302,'先在同一传递中合成，再合PSD。',16),text(720,350,'对称时控制器噪声可在DM消去，',16),text(720,377,'CM仍非零；失配后重新求Q与传递。',16),text(720,425,'对称DM理论为0；极小非零数是',16),text(720,452,'浮点消差残差，不是可测噪声底。',16),text(35,580,'四个教学角：相同预算逐项判定，不调掉失败条件',21)]
    for k in range(1,5):
        r=a['cases']['corner_'+str(k)];c=r['configuration'];v=r['linear'];fail=', '.join(r['budget']['failed']) or '全部已列预算通过';p += [text(35,625+(k-1)*40,f'{k}: VDD={c["vdd"]:g} V，T={c["temperature_K"]:g} K，KP×{c["kp_scale"]:.3f}，Δ|VT|={c["threshold_shift"]:+.3f} V',16),text(720,625+(k-1)*40,fail,16,'#913c33' if r['budget']['failed'] else '#217653')]
    p += [text(35,815,'角3在Vic=1.35 V的最小饱和余量约20.4 mV：仍在饱和，但未过50 mV预算。不是统计失效概率。',17)]
    (out/'noise-corners.svg').write_text(doc(1200,845,'噪声端口与有限参数角',p))


def main():
    p=argparse.ArgumentParser();p.add_argument('--lab',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();make(a.lab,a.out)
if __name__=='__main__':main()
