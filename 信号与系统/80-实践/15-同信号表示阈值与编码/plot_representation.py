#!/usr/bin/env python3
"""Render saved voltage/PSD/coefficient/Mel and truth metrics; no new numerical runs."""
import argparse
from html import escape
import json
import math
from pathlib import Path

FONT='Arial Unicode MS,PingFang SC,Noto Sans CJK SC,system-ui,sans-serif'
COLORS=['#172433','#9b9b9b','#23864b','#c7552f','#8953a5','#2877bc']


class SVG:
    def __init__(self,title,desc,height):
        self.p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1150" height="{height}" viewBox="0 0 1150 {height}" role="img">',
                f'<title>{escape(title)}</title><desc>{escape(desc)}</desc>',f'<rect width="1150" height="{height}" fill="white"/>',
                f'<g font-family="{FONT}" fill="#172433">']
    def text(self,x,y,s,size=16,color='#172433',anchor='start'):
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(s))}</text>')
    def line(self,x,y,X,Y,color='#bbc6ce',width=1,dash=''):
        self.p.append(f'<line x1="{x}" y1="{y}" x2="{X}" y2="{Y}" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>')
    def rect(self,x,y,w,h,color):
        self.p.append(f'<rect x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" fill="{color}"/>')
    def path(self,pts,color,width=2,dash=''):
        d=' '.join(('M' if i==0 else 'L')+f'{x:.4f},{y:.4f}' for i,(x,y) in enumerate(pts))
        self.p.append(f'<path d="{d}" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}" fill="none"/>')
    def panel(self,top,title,xr,yr,h=155,yunit='',xlabel='时间 ms',ylabels=True):
        left,right=95,1080
        self.text(left,top-43,title,20)
        self.text(24,top-12,yunit,14)
        def xy(x,y):return left+(x-xr[0])/(xr[1]-xr[0])*(right-left),top+h-(y-yr[0])/(yr[1]-yr[0])*h
        for n in range(5):
            y=yr[0]+n*(yr[1]-yr[0])/4;px,py=xy(xr[0],y)
            self.line(left,py,right,py)
            if ylabels:self.text(left-12,py+5,f'{y:.3g}',13,anchor='end')
        for n in range(6):
            x=xr[0]+n*(xr[1]-xr[0])/5;px,py=xy(x,yr[0])
            self.line(px,top,px,top+h,'#edf1f4');self.text(px,top+h+22,f'{x:.4g}',13,anchor='middle')
        self.text(right,top+h+45,xlabel,14,anchor='end')
        return xy
    def save(self,path):Path(path).write_text('\n'.join(self.p+['</g></svg>'])+'\n')


def heatcolor(power):
    db=10*math.log10(power) if power>0 else -100
    t=max(0,min(1,(db+100)/100))
    return '#%02x%02x%02x'%(int(242-220*t),int(247-132*t),int(250-113*t))


def representations(r,out):
    c=r['inputs'];fs=c['sample_rate_Hz'];N=c['length'];J=c['haar_levels'];spec=r['spectral_representations']
    fig=SVG('同一clean电压记录的不同表示','同一clean记录、两STFT单边PSD的共同绝对色标、Haar有符号细节与长窗Mel带功率。谱图不代表处理后的去噪结果。',1530)
    fig.text(55,43,'同一 clean 数组：表示保留了什么？',27)
    fig.text(55,75,'全部来自保存 JSON；频率轴 Hz，波形/系数 V，PSD 与 Mel 的功率口径分开。',16)
    lo=min((s['frame_center_s'][0]-s['config']['hop']/(2*fs))*1000 for s in spec)
    hi=max((s['frame_center_s'][-1]+s['config']['hop']/(2*fs))*1000 for s in spec)
    xr=[lo,hi];vals=r['clean_V'];yr=[min(0,min(vals))-.05,max(vals)+.1]
    xy=fig.panel(145,'A  真值：缓变 + 脉冲 + 台阶',xr,yr,h=140,yunit='V')
    fig.path([xy(t*1000,v) for t,v in zip(r['time_s'],vals)],COLORS[0],2.3)
    fig.text(95,123,'原记录 0..N−1；谱的负起点和尾帧采用明确零延拓。',14)
    for i,s in enumerate(spec):
        top=385+i*255
        cfg=s['config'];xy=fig.panel(top,f'{chr(66+i)}  单边 PSD：L={cfg["window_length"]}, H={cfg["hop"]}, F={cfg["nfft"]}',xr,[0,fs/2],h=155,yunit='Hz')
        centers=s['frame_center_s'];hop=cfg['hop']/fs;freqs=s['frequencies_Hz'];df=s['bin_Hz']
        for t,row in zip(centers,s['one_sided_psd_V2_per_Hz']):
            for k,p in enumerate(row):
                a,b=max(0,freqs[k]-df/2),min(fs/2,freqs[k]+df/2)
                x1,y1=xy((t-hop/2)*1000,b);x2,y2=xy((t+hop/2)*1000,a)
                fig.rect(x1,y1,x2-x1+.2,y2-y1+.2,heatcolor(p))
        fig.text(95,top-20,'同一绝对色标：10 log10(P / 1 V²/Hz)，≤−100 dB 同色；保存值未截。',14)
    top=915
    # Four levels are rows, horizontal extents are actual supports, not rectangular Hz bands.
    xy=fig.panel(top,'D  Haar 有符号细节：时间—尺度支持（不是固定 Hz 箱）',xr,[0,J],h=155,yunit='级',ylabels=False)
    coeff=r['clean_haar_V'];at=r['haar_low_count'];details={}
    for ell in range(J,0,-1):
        count=N//2**ell;details[ell]=coeff[at:at+count];at+=count
    peak=max(abs(v) for d in details.values() for v in d) or 1
    for ell,d in details.items():
        fig.text(82,xy(xr[0],ell-.5)[1]+5,f'd{ell}',13,anchor='end')
        for k,v in enumerate(d):
            t1=k*2**ell/fs*1000;t2=(k+1)*2**ell/fs*1000
            x1,y1=xy(t1,ell);x2,y2=xy(t2,ell-1)
            strength=abs(v)/peak
            base=(32,114,178) if v>=0 else (192,74,45)
            color='#%02x%02x%02x'%tuple(round(255*(1-strength)+a*strength) for a in base)
            fig.rect(x1,y1,x2-x1+.1,y2-y1+.1,color)
    fig.text(95,top-20,f'蓝正／红负；共同饱和幅度 ±{peak:.4g} V；低支全留但此处只画细节。',14)
    chosen=max(spec,key=lambda s:s['config']['window_length']);top=1200
    curves=[]
    for b in range(c['mel_bands']):
        curves.append([10*math.log10(max(row[b],c['mel_floor_V2'])) for row in chosen['mel_band_power_V2']])
    xy=fig.panel(top,'E  同一长窗谱的 Mel 带功率（高度1三角、乘 Δf）',xr,[min(-120,min(v for row in curves for v in row)),max(0,max(v for row in curves for v in row))],h=155,yunit='dB')
    for b,curve in enumerate(curves):
        color=['#2774ae','#bc4b2a','#277f51','#8b4ca0','#a08016','#207f85'][b]
        fig.path([xy(t*1000,v) for t,v in zip(chosen['frame_center_s'],curve)],color,1.8,['','6,3','2,3','9,3,2,3','4,2','1,3'][b])
        fig.text(95+b*160,top-20,f'带{b+1}',13,color)
    fig.text(95,1433,f'参考 1 V²；显示 floor={c["mel_floor_V2"]:g} V²。PSD/Mel 不能唯一反推原波形极性。',15)
    fig.text(95,1470,'B/C 共同 PSD 色标 dB：',14)
    for n in range(5):
        db=-100+25*n;fig.rect(400+n*110,1455,85,12,heatcolor(10**(db/10)))
        fig.text(442+n*110,1490,db,13,anchor='middle')
    fig.save(out/'representations.svg')


def denoising(r,out):
    c=r['inputs'];fs=c['sample_rate_Hz'];N=c['length'];h=c['feature_halfwidth_samples'];case=r['noise_cases'][0];methods={m['method']:m for m in case['methods']}
    fig=SVG('总体与局部阈值误差','同一固定噪声实现的真值、观测、hard、soft与全丢细节，保留全原域指标；另显示无噪对照输入与soft输出。',1490)
    fig.text(55,43,f'固定 λ={r["threshold_V"]:.4g} V：总体与局部误差分别看',26)
    fig.text(55,74,f'曲线示范 seed{case["seed"]} 的固定符号实现；表给全部 case，不把两次实现当总体风险定理。',16)
    rows=[('真值',r['clean_V'],COLORS[0],''),('观测',case['observed_V'],COLORS[1],'2,3'),
          ('hard',methods['hard']['samples_V'],COLORS[2],'7,3'),('soft',methods['soft']['samples_V'],COLORS[3],''),
          ('丢细节',methods['drop']['samples_V'],COLORS[4],'11,3,2,3')]
    for panel,(top,title,inds) in enumerate([(145,'A  全部原样点',list(range(N))),
                   (420,'B  脉冲附近：soft 的偏差不能被全局均值藏掉',list(range(max(0,c['pulse_index']-h),min(N,c['pulse_index']+h+1)))),
                   (695,('C  台阶附近：粗格边界对齐' if c['edge_index']%2**c['haar_levels']==0 else 'C  台阶附近：未与粗格边界对齐'),list(range(max(0,c['edge_index']-h),min(N,c['edge_index']+h+1))))]):
        vals=[data[n] for _,data,_,_ in rows for n in inds];a,b=min(vals),max(vals);pad=max(.04,(b-a)*.1)
        xy=fig.panel(top,title,[inds[0]/fs*1000,inds[-1]/fs*1000],[a-pad,b+pad],h=155,yunit='V')
        for i,(name,data,color,dash) in enumerate(rows):
            fig.text(95+i*180,top-20,name,14,color)
            fig.path([xy(n/fs*1000,data[n]) for n in inds],color,2,dash)
    fig.text(95,957,f'D  保存的 MSE，单位 V²；pulse 为中心±{h}样点，包含真脉冲',20)
    fig.text(95,990,'case / 方法',15);fig.text(420,990,'总体',15);fig.text(730,990,'pulse 区',15)
    y=1018
    for q in r['noise_cases']:
        for m in q['methods']:
            fig.text(95,y,f'{q["seed"]} / {m["method"]}',14)
            fig.text(420,y,f'{m["metrics"]["mse_V2"]:.8g}',14)
            fig.text(730,y,f'{m["metrics"]["region_mse_V2"]["pulse"]:.8g}',14);y+=21
    weak=r['weak_pulse_counterexample'];block=2**c['haar_levels'];start=c['pulse_index']//block*block
    inds=list(range(max(0,start-2),min(N,start+block+2)))
    top=1285;peak=max(weak['truth_V']) or .01
    xy=fig.panel(top,('E  无噪弱脉冲：先处理就已经引入失真' if weak['error_squared_V2']>0 else 'E  阈值为0：此弱脉冲反例退化为零'),[inds[0]/fs*1000,inds[-1]/fs*1000],[-.08*peak,1.1*peak],h=120,yunit='V')
    fig.text(95,top-20,'实线真值；虚线soft只剩粗块均值',14)
    fig.path([xy(n/fs*1000,weak['truth_V'][n]) for n in inds],COLORS[0],2.2)
    fig.path([xy(n/fs*1000,weak['soft_samples_V'][n]) for n in inds],COLORS[3],2.2,'7,3')
    fig.text(95,1474,f'无噪平方误差 {weak["error_squared_V2"]:.8g} V²；原本误差为0。事件检测还需任务真值指标。',15)
    fig.save(out/'denoising.svg')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=json.loads(a.results.read_text());a.output.mkdir(parents=True,exist_ok=True)
    representations(r,a.output);denoising(r,a.output)


if __name__=='__main__':main()
