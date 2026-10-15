"""Reproducible SVG and PNG figures for the three fixed F3 teaching cases."""
from pathlib import Path
from hashlib import sha256
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import sys
assets = Path(__file__).resolve().parent
sys.path.insert(0, str(assets.parent))
from level2_case_lab import ar1, bond_tree
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--font', type=Path, help='existing Chinese-capable font file')
parser.add_argument('--previews', type=Path, help='optional directory for PNG inspection')
args = parser.parse_args()
font = args.font
if font is None:
    for candidate in ('/System/Library/Fonts/STHeiti Light.ttc',
                      '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'):
        if Path(candidate).is_file():
            font = Path(candidate)
            break
if font is None or not font.is_file():
    parser.error('supply an existing Chinese-capable font via --font; no fonts are installed automatically')
font_manager.fontManager.addfont(str(font))
plt.rcParams.update({'font.family': font_manager.FontProperties(fname=str(font)).get_name(),
                     'axes.unicode_minus': False, 'svg.fonttype': 'path',
                     'svg.hashsalt': 'wwl-f3-fixed-figures-v2', 'font.size': 11})
preview = args.previews
if preview is not None:
    preview.mkdir(parents=True, exist_ok=True)

def save(fig,name):
    fig.savefig(assets/(name+'.svg'), bbox_inches='tight', metadata={'Date': None})
    svg_path = assets/(name+'.svg')
    svg_text = svg_path.read_text(encoding='utf-8')
    svg_path.write_text('\n'.join(line.rstrip(' \t') for line in svg_text.split('\n')), encoding='utf-8')
    if preview is not None:
        fig.savefig(preview/(name+'.png'), dpi=130, bbox_inches='tight')
    plt.close(fig)
    path = assets/(name+'.svg')
    print(f'{name}.svg {sha256(path.read_bytes()).hexdigest()}')

fig,ax=plt.subplots(figsize=(8,4.4))
a=ar1(.4,.8,3,.3,8)
h=list(range(9)); p=[3]+a['forecasts']; sd=[0]+[v**.5 for v in a['conditional_variances']]
ax.fill_between(h,[x-s for x,s in zip(p,sd)],[x+s for x,s in zip(p,sd)],color='#b4d5eb',label='±一个条件预测标准差（非95%区间）')
ax.plot(h,p,'o-',color='#125b84',label='条件均值预测')
ax.axhline(2,ls='--',color='#8c4635',label='长期均值2个百分点')
ax.set(xlabel='从T出发的预测视距h（季度）',ylabel='x：利润率偏差（百分点）',title='固定xT=3；c=0.4，phi=0.8，创新标准差0.3')
ax.annotate('h1：2.8；误差方差0.09',xy=(1,2.8),xytext=(2.3,3.18),arrowprops={'arrowstyle':'->'})
ax.annotate('h2：2.64；误差方差0.1476',xy=(2,2.64),xytext=(3.4,2.8),arrowprops={'arrowstyle':'->'})
ax.set_ylim(1.6,3.5)
ax.legend(loc='lower left'); ax.grid(alpha=.2)
save(fig,'f3-ar-forecast')

fig,ax=plt.subplots(figsize=(10,4.8)); ax.axis('off'); ax.set_xlim(0,10); ax.set_ylim(0,5)
def box(x,y,text,width=2.6,color='#eaf2f8'):
    ax.text(x,y,text,ha='center',va='center',bbox={'boxstyle':'round,pad=.65','fc':color,'ec':'#477188'},linespacing=1.6)
box(2,4.05,'稳定期NOPAT3\n112.167百万元')
box(2,2.5,'IC2 = 673.8\n净再投资3 = 3% × IC2\n20.214百万元')
box(5.25,3.5,'FCFF3 = 91.953\nTV2 = 91.953 / (9%−3%)\n1532.55百万元')
box(8.4,3.5,'贴现至t0\nEV经营 = 1407.558286\n（包含经营现金40）')
box(5.25,.7,'+剩余现金80 +联营90\n−金融债280 −租赁债40\n−少数股权25 −优先股15',color='#fff1df')
box(8.4,.7,'普通股权 = 1217.558286\n÷100百万股\n12.175583本币/股',color='#e4f1e4')
for start,end in [((3.2,4),(4,3.75)),((3.2,2.5),(4,3.2)),((6.5,3.5),(7,3.5)),((8.4,2.85),(8.4,1.5)),((6.65,.7),(7,.7))]:
    ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','lw':1.5})
ax.text(.2,.65,'金额：百万元本币\n时点：现金流为年末\n现金互斥：40经营+80剩余',va='center')
ax.text(5,4.85,'先保证资本与增长一致，再从经营EV桥接到普通股权',ha='center',fontsize=14)
save(fig,'f3-company-bridge')

fig,ax=plt.subplots(figsize=(11,6));ax.axis('off');ax.set_xlim(-.7,3.7);ax.set_ylim(-.4,3.6)
r=bond_tree([[.05],[.08,.04],[.11,.06,.02]],call={1:100,2:100})
coords={0:[(0,1.5)],1:[(1.2,2.3),(1.2,.7)],2:[(2.5,3),(2.5,1.5),(2.5,0)]}
for t in range(2):
    for j,(x,y) in enumerate(coords[t]):
        for k in (j,j+1):
            xx,yy=coords[t+1][k]
            ax.annotate('',xy=(xx-.28,yy),xytext=(x+.28,y),arrowprops={'arrowstyle':'->','color':'#7991a0','linestyle':'--' if t==1 and j==1 else '-'})
texts=[['t0；r0=5%\n价格99.077490'],['t1 U；r=8%\n余值96.062729\n不赎回','t1 D；r=4%\n继续值101.923077\n赎回后余值100'],['t2 UU；r=11%\n余值95.495495\n不赎回','t2 UD=DU；r=6%\n继续值100\n边界余值100','t2 DD；r=2%\n继续值103.921569\n赎回后余值100']]
for t in range(3):
    for j,(x,y) in enumerate(coords[t]):
        ax.text(x,y,texts[t][j],ha='center',va='center',fontsize=10,bbox={'boxstyle':'round,pad=.45','fc':'#fff0df' if (t==1 and j==1) or (t==2 and j>=1) else '#eaf2f8','ec':'#477188'})
ax.text(3.38,1.5,'t3到期\n每个存活节点\n支付106\n\n赎回路径\n后续支付0',ha='center',va='center',bbox={'boxstyle':'round,pad=.45','fc':'#e6f1e5','ec':'#477188'})
ax.text(1.5,3.55,'三期含权债：每期先付息6，再可赎回100；图中t1/t2为付息后余值',ha='center',fontsize=13)
ax.text(1.4,-.38,'q=1/2（风险中性）；年有效率；虚线仅为背景利率树，t1 D已赎回后路径终止',ha='center',fontsize=10)
save(fig,'f3-callable-tree')
