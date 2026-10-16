"""Two finite figures from saved analytical/SPICE JSON, no simulator imports."""
import argparse
import html
import json
import math
from pathlib import Path


class SVG:
    def __init__(self, title, h):
        self.s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{h}"><title>{html.escape(title)}</title><desc>同一固定卡的节点、噪声与实际有限窗口数据；非真实工艺或硬件。</desc><style>text{{font-family:Arial Unicode MS,PingFang SC,Noto Sans CJK SC,system-ui,sans-serif;font-size:16px;fill:#172033}}.title{{font-size:24px;font-weight:bold}}.small{{font-size:13px}}</style><rect width="1100" height="{h}" fill="#f8fafc"/>']
        self.text(40,40,title,"title")
    def text(self,x,y,t,cls=""):
        self.s.append(f'<text x="{x}" y="{y}" class="{cls}">{html.escape(str(t))}</text>')
    def line(self,x1,y1,x2,y2,c="#64748b",w=1.5):
        self.s.append(f'<path d="M{x1},{y1}L{x2},{y2}" stroke="{c}" stroke-width="{w}" fill="none"/>')
    def rect(self,x,y,w,h,c="#fff",stroke="#cbd5e1"):
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{c}" stroke="{stroke}"/>')
    def poly(self,pts,c):
        self.s.append('<polyline fill="none" stroke="'+c+'" stroke-width="2" points="'+" ".join(f"{x:.4f},{y:.4f}" for x,y in pts)+'"/>')
    def dot(self,x,y,c):
        self.s.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{c}"/>')
    def finish(self,p):
        p.write_text("\n".join(self.s+["</svg>"])+"\n")


COL=["#0369a1","#c2410c","#059669","#7c3aed"]


def panel(s,x,y,w,h,xr,yr,title,xlabel,ylabel,xtick=True):
    s.text(x,y-45,title)
    s.rect(x,y,w,h)
    def xx(v):return x+(v-xr[0])/(xr[1]-xr[0])*w
    def yy(v):return y+h-(v-yr[0])/(yr[1]-yr[0])*h
    for i in range(5):
        a=xr[0]+(xr[1]-xr[0])*i/4;b=yr[0]+(yr[1]-yr[0])*i/4
        s.line(x,yy(b),x+w,yy(b),"#e2e8f0")
        s.text(x-51,yy(b)+4,f"{b:.3g}","small")
        if xtick:s.text(xx(a)-15,y+h+22,f"{a:.3g}","small")
    s.text(x+w-110,y+h+46,xlabel,"small")
    s.text(x-25,y-14,ylabel,"small")
    return xx,yy


def draw(a,sp,out):
    cfg=a["input"];l=cfg["lna"];m=cfg["mixer"]
    rslist=l["Rs_cases_ohm"]
    if len(rslist)>4:raise ValueError("figure layout supports at most four Rs cases")
    s=SVG("共栅MOS：同一个Q点决定匹配、增益和主要噪声",1020)
    s.text(50,85,"A 实际拓扑：gate交流地，B随S；Cout隔直，RL为吸收读出")
    # Schematic is topology from the fixed card, not a transistor icon hiding its ports.
    s.rect(120,185,110,38);s.text(131,210,f'Rs={l["nominal_Rs_ohm"]:g}Ω')
    s.line(60,204,120,204);s.text(52,175,"vb＋e")
    s.line(230,204,395,204);s.text(335,190,"S, B")
    s.rect(395,146,115,90,"#e0f2fe","#0369a1");s.text(419,193,"M1 CG")
    s.line(565,164,565,115);s.rect(520,80,100,35);s.text(530,104,f'RD={l["Rd_ohm"]:g}Ω')
    s.line(565,80,565,66);s.text(600,76,f'VDD={l["vdd_V"]:g}V',"small")
    s.line(452,236,452,276);s.text(470,265,"G=VG，交流地","small")
    s.line(510,164,660,164);s.text(550,148,"D")
    s.line(660,149,660,180);s.line(670,149,670,180);s.line(670,164,850,164)
    s.text(635,130,f'Cout={l["Cout_F"]*1e9:g}nF',"small")
    s.text(808,145,"o")
    s.line(850,164,850,215);s.rect(807,215,85,38);s.text(818,239,f'RL={l["Rl_ohm"]:g}')
    s.line(850,253,850,280);s.line(831,280,869,280)
    s.text(50,318,"外支路：Cgs在G–S，Cgd在G–D，Cds在D–S；Meyer Cgs另加到总Cgs。","small")
    s.text(50,346,"表中三案主动重偏置VG保持ID，不能与固定VG换Rs的实验混同。","small")

    fs=sorted(set(r["frequency_Hz"] for r in a["lna"]))
    xr=(math.log10(min(fs)),math.log10(max(fs))) if len(fs)>1 else (math.log10(fs[0])-.1,math.log10(fs[0])+.1)
    gains=[abs(complex(*r["output_over_e"])) for r in a["lna"]]
    xx,yy=panel(s,85,440,430,255,xr,(min(gains)*.95,max(gains)*1.05),"B 有限频点：|vo/e|，标记为实际SPICE","log10 f/Hz","V/V")
    for i,rs in enumerate(rslist):
        rows=[r for r in a["lna"] if r["Rs_ohm"]==rs]
        s.poly([(xx(math.log10(r["frequency_Hz"])),yy(abs(complex(*r["output_over_e"])))) for r in rows],COL[i])
        for r in sp["lna"][str(rs)]["frequencies"]:
            s.dot(xx(math.log10(r["frequency_Hz"])),yy(r["gain_magnitude"]),COL[i])
        s.text(85+i*110,414,f"Rs={rs:g}Ω", "small")
    selected=[r for r in a["lna"] if r["frequency_Hz"]==max(fs)]
    s.text(610,395,f'C 同一频点 {max(fs)/1e6:g}MHz：功率与噪声')
    for i,r in enumerate(selected):
        y=435+i*65
        s.text(615,y,f'Rs={r["Rs_ohm"]:g}Ω  GT={r["G_T"]:.6f}')
        s.text(615,y+25,f'F={r["F"]:.6f} / NF={r["NF_dB"]:.6f}dB',"small")
    nom=min(selected,key=lambda r:abs(r["Rs_ohm"]-l["nominal_Rs_ohm"]))
    s.text(610,660,f'噪声条：Rs={nom["Rs_ohm"]:g}Ω / {nom["frequency_Hz"]/1e6:g}MHz，V²/Hz',"small")
    psd=nom["output_PSD_V2_per_Hz"];maximum=max(psd.values())
    for i,(label,value) in enumerate(psd.items()):
        y=697+i*40
        s.text(610,y,label,"small");s.rect(690,y-16,240*value/maximum,18,COL[i],"none")
        s.text(690,y+18,f"{value:.6g}","small")
    s.text(50,910,"D 固定理想gate/B随S/正R与C的三态多项式满足Routh；不认证任意终端或真实封装。","small")
    s.text(50,941,"信号源AC 1为线性基激励；实际RF幅度/区域与压缩另查，单位电压比不是功率增益。","small")
    s.finish(out/"lna.svg")

    s=SVG("四MOS换向桥：频移、镜像、阻塞和动态共模分开看",1120)
    s.text(50,86,"A 四管真实连接：蓝LO+直通，橙LO−交叉，所有B接0V")
    for label,x,y in (("RFp",150,150),("RFn",150,270),("op",770,150),("on",770,270)):
        s.text(x-25,y-20,label);s.dot(x,y,"#172033")
    for y in (150,270):
        s.line(150,y,770,y,COL[0],2)
        s.rect(405,y-15,80,30);s.text(417,y+6,"MOS+","small")
    s.line(150,150,770,270,COL[1],2);s.line(150,270,770,150,COL[1],2)
    s.rect(310,175,85,27);s.text(317,194,"Mnp LO−","small")
    s.rect(540,175,85,27);s.text(547,194,"Mpn LO−","small")
    s.line(770,150,940,150);s.line(770,270,940,270)
    s.line(940,150,940,193);s.rect(905,193,70,35);s.text(913,216,"RL","small");s.line(940,228,940,270)
    s.text(55,325,f'差分Rs={m["source_diff_ohm"]:g}Ω（每侧一半），RL={m["load_diff_ohm"]:g}Ω；op/on各RB={m["output_bias_each_ohm"]/1e6:g}MΩ回VCM。',"small")
    s.text(55,351,"交叉处无节点连接；输出偏置返回不等于瞬时共模钳位。LO有限边沿/Meyer均保留。","small")
    cases=sp["mixer"]
    items=[("wanted10",cases["mixer-wanted"]["projections"]["10000000"]["amplitude_V"]),
           ("image10",cases["mixer-image"]["projections"]["10000000"]["amplitude_V"]),
           ("weak10",cases["mixer-weak_LO"]["projections"]["10000000"]["amplitude_V"]),
           ("joint10",cases["mixer-wanted_with_blocker"]["projections"]["10000000"]["amplitude_V"]),
           ("joint30",cases["mixer-wanted_with_blocker"]["projections"]["30000000"]["amplitude_V"])]
    ds=[20*math.log10(max(v,1e-15)/.001) for _,v in items]
    xx,yy=panel(s,95,445,435,300,(0,5),(min(-90,min(ds)-5),max(55,max(ds)+5)),"B 同一500ns–1us有限窗口","","dB re 1mV",False)
    zero=yy(min(-90,min(ds)-5))
    for i,((label,val),db) in enumerate(zip(items,ds)):
        x=xx(i+.5);s.rect(x-22,yy(db),44,zero-yy(db),COL[i%4],"none")
        s.text(x-32,yy(db)-9,f"{val*1e3:.4g}mV","small")
        s.text(x-32,770,label,"small")
    xx,yy=panel(s,670,445,350,300,(0,3),(.3,.82),"C 实际共模范围/均值","","V",False)
    for i,key in enumerate(("mixer-baseline","mixer-weak_LO","mixer-wanted_with_blocker")):
        row=cases[key];lo,hi=row["common_mode_range_V"];x=xx(i+.5)
        s.line(x,yy(lo),x,yy(hi),COL[i],6);s.dot(x,yy(row["common_mode_mean_V"]),"#172033")
        s.text(x-32,770,("baseline","weak LO","joint")[i],"small")
    s.text(50,846,"D 理想常Ron噪声模型：不同RF谱口径，不是实际MOS周期noise仿真")
    r=a["mixer_ideal_limit"]
    s.text(60,884,f'两RF带 SSB F={r["two_RF_bands_SSB_F"]:.6f}；全白RF所有奇次带 F={r["all_white_RF_SSB_F"]:.6f}')
    s.text(60,917,"包括2Ron和RB热源；实际预选器还改变谐波阻抗/损耗热源，不能只删谱。","small")
    s.text(50,978,"弱LO小残余、强音10MHz残余均为有限窗口；步长细化不充PSS/物理IM3或硬件签核。","small")
    s.text(50,1010,"本图未给LNA到桥的真实balun/加载连接，两个器件实例不能直接乘GT/Friis。","small")
    s.finish(out/"mixer.svg")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analysis",type=Path,required=True)
    p.add_argument("--spice",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    draw(json.loads(a.analysis.read_text()),json.loads(a.spice.read_text()),a.out)


if __name__=="__main__":
    main()
