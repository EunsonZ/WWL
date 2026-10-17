"""Draw only recorded states/client intervals; no protocol evaluation."""
import argparse
import html
import json
from pathlib import Path


def text(x,y,s,size=22,color='#17324d',weight='normal'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{html.escape(str(s))}</text>'


def canvas(title,subtitle,height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}">','<rect width="1200" height="100%" fill="#f7fafc"/>','<g font-family="PingFang SC, sans-serif">',text(40,48,title,30,weight='bold'),text(40,82,subtitle,18)]


def figures(data):
    cases={s['name']:s for s in data['scenarios']}
    a=canvas('多数确认后，为什么还不能返回？','ApplyLag：表中每行直接取正式结果的 B 状态；整数是日志位置，不是时间。',550)
    cols=[40,445,610,780,940]
    for x,h in zip(cols,['调度动作','term','commit','applied','value']):a.append(text(x,135,h,23,weight='bold'))
    rows=[(6,'B 当选，继承 put7'),(8,'提交当前 term 的 no-op'),(11,'本次多数已到，poll'),(14,'应用后再次 poll')]
    for row,(idx,label) in enumerate(rows):
        y=191+row*69;step=cases['ApplyLag']['steps'][idx-1];n=step['nodes']['B']
        a.append(f'<rect x="30" y="{y-35}" width="1140" height="56" rx="8" fill="{"#e3f4ed" if idx==14 else "#e8eff6"}"/>')
        for x,value in zip(cols,[label,n['term'],n['commit'],n['applied'],n['value']]):a.append(text(x,y,value))
        if idx in (11,14):a.append(text(45,y+22,step['result']['status'],16,'#b94726' if idx==11 else '#147352'))
    a.extend([text(40,474,'当前任期提交 → 捕获 readIndex → 本次同任期多数 → 应用到位 → 原子查询',23,weight='bold'),text(40,515,'commit=2 不等于 applied=2；等待状态不携带成功的寄存器读值。',20),'</g></svg>'])
    b=canvas('一条晚到回复，可以构成两种不同的历史','区间来自逻辑客户端调用/返回序号；不是跨机器墙钟或生产延迟测量。',830)
    panels=[('OldLeader','history_bad','① 写已完成再调用读：返回 0 不可线性化',False),('DelayedTermReply','history_good','② 读跨越新写：返回 0 可以排在 put7 之前',True),('ReadReadOrder','history_bad','③ 两次读有先后：在途写不能解释先 7 后 0',False)]
    for k,(name,group,title,good) in enumerate(panels):
        top=125+k*220;b.append(text(40,top,title,24,'#147352' if good else '#a93628',weight='bold'))
        history=sorted(cases[name][group],key=lambda h:(h['start'],h['id']))
        scale=68;origin=450
        for t in range(1,10):
            x=origin+(t-1)*scale;b.append(f'<line x1="{x}" y1="{top+14}" x2="{x}" y2="{top+154}" stroke="#d9e2eb"/>');b.append(text(x-5,top+178,t,16))
        for j,h in enumerate(history):
            y=top+42+j*45;label=f"{h['id']}: {'put '+str(h['value']) if h['kind']=='put' else 'get → '+str(h['value'])}"
            b.append(text(60,y+6,label,21));x1=origin+(h['start']-1)*scale;x2=origin+(h['end']-1)*scale;color='#386dc1' if h['kind']=='put' else '#d47b20'
            b.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="10" stroke-linecap="round"/>')
            for x in [x1,x2]:b.append(f'<circle cx="{x}" cy="{y}" r="6" fill="white" stroke="{color}" stroke-width="3"/>')
    b.extend([text(40,810,'蓝：put；橙：get。读的调用时点和整段实时顺序，比“返回时谁仍自称主”更关键。',20),'</g></svg>'])
    return {'barriers.svg':'\n'.join(a)+'\n','histories.svg':'\n'.join(b)+'\n'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,default=Path(__file__).parent/'evidence/memory-results.json');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    for name,svg in figures(json.loads(a.results.read_text())) .items():(a.out/name).write_text(svg)
    print('wrote two SVGs from recorded results')
if __name__=='__main__':main()
