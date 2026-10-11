"""Generate real loci and real points of tangent cones; no complex plane projection.
Run: python -B generate.py NEW_OUTPUT_DIR (matplotlib required).
All x, y, a dimensionless. Each plot uses equal scale, [-.5,.5]^2.
"""
from pathlib import Path
import sys, math, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'svg.fonttype':'path','font.size':11})
out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=False)
records=[]
for a, name in [(1,'plus1'),(0,'zero'),(-1,'minus1')]:
    fig, axes=plt.subplots(2,1,figsize=(4.7,7.2))
    fig.suptitle(r'$C_a: y^2=x^2(x+a)$'+f'    a = {a}', fontsize=15)
    for ax in axes:
        ax.set_xlim(-.5,.5); ax.set_ylim(-.5,.5); ax.set_aspect('equal')
        ax.set_xticks([-.5,-.25,0,.25,.5]); ax.set_yticks([-.5,-.25,0,.25,.5])
        ax.grid(alpha=.2); ax.axhline(0,color='.7',lw=.6); ax.axvline(0,color='.7',lw=.6)
        ax.set_xlabel('x (dimensionless)'); ax.set_ylabel('y (dimensionless)')
    # Separate signs and x intervals: no segment connects distinct components.
    intervals=[(-.5,0),(0,.5)] if a==1 else [(0,.5)] if a==0 else []
    for lo,hi in intervals:
        xs=[lo+(hi-lo)*i/400 for i in range(401)]
        for sign in [-1,1]:
            ys=[sign*abs(x)*math.sqrt(x+a) for x in xs]
            axes[0].plot(xs,ys,color='#1267a6',lw=2)
            records.append({'a':a,'sign':sign,'x':xs,'y':ys})
    axes[0].plot(0,0,'o',color='#1267a6',ms=5,zorder=4)
    axes[0].set_title('Real points of C_a',fontsize=13)
    axes[0].text(.02,.04,'solid: curve; dot: origin',transform=axes[0].transAxes,fontsize=9,bbox=dict(facecolor="white",edgecolor="none",alpha=.9,pad=1))
    q={1:r'$y^2-x^2=0$',0:r'$y^2=0$',-1:r'$y^2+x^2=0$'}[a]
    axes[1].set_title('Real points of tangent cone\n'+q,fontsize=12)
    if a==1:
        axes[1].plot([-.5,.5],[-.5,.5],'--',color='#ad4a00',lw=2)
        axes[1].plot([-.5,.5],[.5,-.5],'--',color='#ad4a00',lw=2)
        axes[1].text(.02,.04,'dashed: two simple lines',transform=axes[1].transAxes,fontsize=9,bbox=dict(facecolor="white",edgecolor="none",alpha=.9,pad=1))
    elif a==0:
        axes[1].plot([-.5,.5],[0,0],'--',color='#ad4a00',lw=2)
        axes[1].text(.02,.04,'dashed: one line, multiplicity 2',transform=axes[1].transAxes,fontsize=9,bbox=dict(facecolor="white",edgecolor="none",alpha=.9,pad=1))
    else:
        axes[1].text(.02,.04,'real cone: origin only',transform=axes[1].transAxes,fontsize=9,bbox=dict(facecolor="white",edgecolor="none",alpha=.9,pad=1))
        axes[0].text(.02,.8,'No other real points\nin this window',transform=axes[0].transAxes,fontsize=9,bbox=dict(facecolor="white",edgecolor="none",alpha=.9,pad=1))
    axes[1].plot(0,0,'o',color='#ad4a00',ms=5,zorder=4)
    footer={1:'Over C: cone lines y = +x and -x',0:'Over C: double line y = 0',-1:'Over C: cone lines y = +ix and -ix'}[a]
    fig.text(.5,.02,footer,ha='center',fontsize=11)
    fig.subplots_adjust(left=.16,right=.97,top=.9,bottom=.13,hspace=.65)
    fig.savefig(out/f'curve-{name}.svg',metadata={'Date':None})
    fig.savefig(out/f'curve-{name}.png',dpi=140)
    plt.close(fig)
(out/'samples.json').write_text(json.dumps({'interval_points':401,'range':[-.5,.5],'records':records},separators=(',',':'))+'\n')
print('Generated 3 SVG, 3 PNG, samples.json; separate intervals/signs, equal axes.')
