"""Scientific SVGs from the published raw arrays; display clipping never changes metrics."""
import argparse,html,json,math
from pathlib import Path


def text(x,y,value,size=16,color='#203047',anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(value))}</text>'

def rect(x,y,w,h,fill,stroke='none'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}"/>'

def document(width,height,parts,title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><title>{html.escape(title)}</title><desc>同一固定PSF与原始数值生成；图中保留单位、边界、未观测与指标范围。完整数组见actual.json，显示不改变数值。</desc><rect width="100%" height="100%" fill="#f7f9fc"/><g font-family="PingFang SC, sans-serif">'+''.join(parts)+'</g></svg>\n'

def shade(v):
    t=max(0,min(1,v));return '#%02x%02x%02x'%(round(235-205*t),round(245-135*t),round(252-75*t))

def grid(parts,values,x,y,cell,cols,rows,maximum=1):
    for r in range(rows):
        for c in range(cols):
            v=values[r*cols+c];parts.append(rect(x+c*cell,y+r*cell,cell,cell,shade(v/maximum),'#dce3ec'))
            if v<0 or v>maximum:parts.append(rect(x+c*cell+2,y+r*cell+2,cell-4,cell-4,'none','#d24636'))

def make(spec,development,evaluation,actual,selection,out):
    out.mkdir(parents=True,exist_ok=True)
    p=[text(30,36,'一次观测先经过哪三步？',25),text(30,65,'x: 8×8 / .1 mm → H: 同尺寸模糊 → B: 2×2平均 → C: 留3×4读数',17),text(30,92,'h原点(1,1)；像素按row-major排列；主体零延拓；数值均由同一spec/actual生成',15)]
    psf=spec['psf'];grid(p,sum(psf,[]),40,126,60,3,3,1)
    for r in range(3):
        for c in range(3):p.append(text(70+60*c,162+60*r,str(round(psf[r][c]*16))+'/16',18,anchor='middle'))
    p += [text(40,331,'非对称PSF，∑h=1；不是把核翻转后仍算同一次采集',15),text(300,146,'A = C B H : 12×64',22),text(300,182,'A* = H* B* C* : 64×12',22),text(300,219,'C*: 未读位置补0；B*: 每个读数分回4格，各乘1/4',16),text(300,250,'H*: 同一索引逐项scatter；不能仅换一张翻核图',16)]
    a=actual['operator'];mx=max(max(row) for row in a);grid(p,sum(a,[]),40,382,12,64,12,mx)
    p += [text(40,367,'A系数热图：横轴源像素j=8r+c，纵轴观测k=4r+c；深色=大系数',16),text(40,552,'0',14),text(136,552,'8',14),text(232,552,'16',14),text(328,552,'24',14),text(424,552,'32',14),text(520,552,'40',14),text(616,552,'48',14),text(712,552,'56 … 63',14),rect(712,382,96,144,'none','#d24636'),text(40,592,'精确rank=12，nullity=52；末行8个源像素对应零列，未观测≠真值为0',18),text(40,625,'角脉冲：零边界y00=13/64；周期另有y03=2/64；(AᵀAe00)00=169/4096≠1',17),text(40,656,'∑h=1不保证有限边界响应或裁剪后总和保持；A*是返传，不是逆',17)]
    (out/'forward.svg').write_text(document(1000,690,p,"有限采集链与12乘64矩阵"))
    p=[text(30,36,'同一12个带噪读数，四种重建',25),text(30,66,'所有面板同一物理视野.8×.8 mm；显示灰度限0…1 U，红框=数值超界；指标使用未裁剪值',16)]
    panels=[('指定test真图',sum(evaluation['truth'],[]),None),('观测3×4（下方一行未读）',actual['evaluation']['fit'],None)]+[(r['id'],r['fit']['x'],r['metrics']) for r in actual['reconstructions']]
    for k,(title,values,metrics) in enumerate(panels):
        x=40+(k%3)*310;y=130+(k//3)*320;p.append(text(x,y-18,title,18))
        if k==1:
            grid(p,values,x,y,48,4,3)
            for c in range(4):
                p.append(rect(x+c*48,y+144,48,48,'#e3e5e9','#a1a8b3'));p.append(text(x+c*48+24,y+174,'×',24,anchor='middle'))
        else:grid(p,values,x,y,24,8,8)
        if metrics:
            p += [text(x,y+222,f"MSE {metrics['mse']:.5f} U²",16),text(x,y+246,f"PSNR {metrics['psnr_db']:.3f} dB",16),text(x,y+270,f"repeat预测MSE {metrics['repeat_prediction_mse']:.6f}",14)]
        elif k==0:p.append(text(x,y+222,'末行未知模式也明确保留在评估',15))
        else:p.append(text(x,y+222,'电子噪声在平均/裁剪之后加入',15))
    p += [text(40,790,'TV把test[0,6]的1 U尖峰估成约.353 U；末行的平整填补来自先验，不是恢复了缺失读数',17),text(40,822,'本例TV的latent MSE较小，但repeat预测MSE比pinv大；“更像真图”和“预测新观测”不是同一目标',16)]
    (out/'reconstruction.svg').write_text(document(1000,850,p,"同一真图和观测的四种重建"))
    p=[text(30,36,'先锁参数，再看另一对象：选择目标与停机目标分开',24),text(30,66,'左：dev-val独立噪声预测MSE；右：selected test TV的浮点primal-dual gap（U²）',16)]
    colors={'tsvd':'#386bb1','ridge':'#d26c2b','tv':'#2b855e'}
    for mi,method in enumerate(('tsvd','ridge','tv')):
        rr=[r for r in selection['rows'] if r['candidate']['method']==method];yy=116+mi*112;p.append(text(35,yy,method,18,colors[method]))
        for k,row in enumerate(rr):
            xx=112+k*88;score=row['validation_mse'];chosen=row['candidate']==selection['by_family'][method];p += [rect(xx,yy+14,64,12,colors[method] if chosen else '#cbd5e3'),text(xx,yy+48,f"{row['candidate']['parameter']:g}",15),text(xx,yy+73,f'{score:.5f}',14)]
    history=next(r for r in actual['reconstructions'] if r['id']=='tv_selected')['fit']['history'];x0,y0=610,420;ww,hh=340,285;logs=[math.log10(max(1e-14,h['gap'])) for h in history];low=-12;high=max(0,max(logs));last=history[-1]['iteration'];p += [f'<path d="M{x0} {y0-hh} V{y0} H{x0+ww}" fill="none" stroke="#506078"/>']
    pts=' '.join(f'{x0+ww*h["iteration"]/last:.4f},{y0-hh*(v-low)/(high-low):.4f}' for h,v in zip(history,logs));p.append(f'<polyline points="{pts}" fill="none" stroke="#2b855e" stroke-width="2"/>')
    for v in (-12,-9,-6,-3,0):p.append(text(x0-8,y0-hh*(v-low)/(high-low)+5,f'10^{v}',13,anchor='end'))
    p += [text(x0,y0+25,'0',14),text(x0+ww,y0+25,str(last)+' iter',14,anchor='end'),text(600,490,f'最终gap={history[-1]["gap"]:.3g} U²',16),text(600,520,'gap约束距本目标最优解，不认证真图',16),text(35,508,'色条=各族被选参数；总赢家 TV λ=.001 U',17),text(35,540,'13个候选预先给定；不按test真图MSE重挑',17),text(35,580,'右图仅画实际记录点；ADMM目标/残差不要求每步单调',16)]
    (out/'selection.svg').write_text(document(1000,620,p,"参数选择与优化停机的不同目标"))


def main():
    p=argparse.ArgumentParser();p.add_argument('--lab',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();load=lambda n:json.loads((a.lab/n).read_text());make(load('spec.json'),load('development.json'),load('evaluation.json'),load('results/actual.json'),load('results/selection.json'),a.out)
if __name__=='__main__':main()
