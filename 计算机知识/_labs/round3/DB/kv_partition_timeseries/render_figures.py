import argparse
import html
import json
from pathlib import Path


def render(actual):
    final=actual['prefixes'][-1];daily=final['layouts'][0]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="640" viewBox="0 0 1100 640" role="img" aria-labelledby="title desc">',
         '<title id="title">迟到进入旧桶，并列时间仍有独立身份</title>',
         '<desc id="desc">S1九个接受变更分三日桶。R14晚于R08到达但事件时点更早，因此排在旧桶R08前。R12 R13时点相同，使用事件id打破并列。下表显示同一查询三个布局的逻辑成本，不是引擎时延。</desc>',
         '<rect width="1100" height="640" fill="white"/><g font-family="PingFang SC,sans-serif" fill="#1c2d44">',
         '<text x="40" y="43" font-size="25">事件时点决定桶与顺序，处理位置决定何时可见</text>',
         '<text x="40" y="77" font-size="17">每行按(event_ms,event_id)排序；横向只表示顺序，不按时长比例绘制</text>']
    for i,p in enumerate(x for x in daily['partitions'] if x['key'][0]=='S1'):
        y=125+i*100
        svg.append(f'<text x="40" y="{y+25}" font-size="18">UTC日 {p["key"][1]}</text>')
        for j,point in enumerate(p['rows']):
            x=195+j*210; fill='#fff1d6' if point['event_id']=='R14' else '#e9f1fb'
            label=point['event_id']+(' 删除' if point['deleted'] else ' v'+str(point['version']))
            svg.append(f'<rect x="{x}" y="{y}" width="190" height="65" rx="8" fill="{fill}" stroke="#425b78"/><text x="{x+12}" y="{y+25}" font-size="18">{html.escape(label)}</text><text x="{x+12}" y="{y+49}" font-size="15">t={point["event_ms"]} ms</text>')
    svg.extend(['<text x="40" y="455" font-size="19">S1全范围首分页(size=2)：相同答案，不同布局成本</text>',
                '<text x="40" y="491" font-size="16">布局</text><text x="375" y="491" font-size="16">探测分区</text><text x="535" y="491" font-size="16">拷入候选行</text><text x="735" y="491" font-size="16">最大实际分区行数</text>'])
    for i,layout in enumerate(final['layouts']):
        q=next(q for q in layout['queries'] if q['query_id']=='all_S1')['pages'][0]
        svg.append(f'<text x="40" y="{527+34*i}" font-size="17">{layout["id"]}</text><text x="375" y="{527+34*i}" font-size="17">{q["cost"]["partition_probes"]}</text><text x="535" y="{527+34*i}" font-size="17">{q["cost"]["candidate_rows_read"]}</text><text x="735" y="{527+34*i}" font-size="17">{layout["max_partition_rows"]}</text>')
    svg.append('</g></svg>');return '\n'.join(svg)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--actual',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.write_text(render(json.loads(a.actual.read_text())))
if __name__=='__main__':main()
