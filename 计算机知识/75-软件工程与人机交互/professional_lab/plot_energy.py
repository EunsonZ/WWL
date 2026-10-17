"""Draw saved allocation results and labels from the same input card."""
import argparse
import html
import json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();data=json.loads(a.results.read_text());rows=data['results'];cards={c['id']:c for c in data['input']['cases']};common=data['input']['common']
valid=[r for r in rows if r['status']=='calculated_synthetic'];bad=[r for r in rows if r['status']!='calculated_synthetic']
if not 1<=len(valid)<=32:raise ValueError('plot requires 1..32 calculated cases')
height=320+len(valid)*75;scale=380/(max(r['metrics']['total_allocated_g']['decimal'] for r in valid) or 1)
def t(x,y,s,size=20,color='#17324d'):return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{html.escape(str(s))}</text>'
x=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" viewBox="0 0 1100 {height}"><title>同质量教学请求的单位强度与窗口总摊分</title><desc>操作能耗与制造摊分均为模型；每行参数来自对应输入卡，不能把单位下降直接说成总量下降。</desc><rect width="1100" height="100%" fill="#f7fafc"/><g font-family="PingFang SC, sans-serif">',t(35,46,'单位数值变好，总量也一定下降吗？',30),t(35,80,'每行采用输入卡的窗口/寿命/碳强度；全为教学模型，非测量或认证。',20)]
for xx,s in [(35,'方案与输入'),(290,'总分摊 C（gCO₂e）'),(800,'mgCO₂e / 成功请求')]:x.append(t(xx,127,s,22))
for i,r in enumerate(valid):
    c=cards[r['id']];settings={**common,**c['override']};m=r['metrics'];y=184+i*75;o=m['operational_g']['decimal'];e=m['embodied_allocated_g']['decimal'];label=r['id'][:18]
    detail=f"N={c['successful_requests']}; e={c['success_J']}J"
    detail2=f"T={settings['window_h']}h; EL={settings['hardware_life_h']}h; I={settings['grid_g_per_kWh']}"
    x.extend([f'<g><title>{html.escape(r["id"]+"; "+detail+"; "+detail2)}</title>',t(35,y-5,label,21),t(35,y+17,detail,15),t(35,y+35,detail2,12),f'<rect x="290" y="{y-21}" width="{o*scale}" height="30" fill="#3975b7"/>',f'<rect x="{290+o*scale}" y="{y-21}" width="{e*scale}" height="30" fill="#d88a38"/>',t(300+(o+e)*scale,y+3,f'{o+e:.3f}',18),t(845,y+4,f"{1000*m['g_per_functional_unit']['decimal']:.6f}",22),'</g>'])
footer=190+len(valid)*75
x.extend([t(35,footer,'蓝：运行 O；橙：制造分摊 M。条长比较窗口总 C，右列另有成功请求分母。',20),t(35,footer+36,f'质量不达声明门槛的卡共 {len(bad)} 项：不输出同功能单位强度；完整拒因留在JSON。',20),t(35,footer+72,'设施系数只乘 IT；外部网络另计。寿命与碳强度改变是敏感性，不是已发生事实。',18),'</g></svg>'])
a.out.write_text('\n'.join(x)+'\n')
