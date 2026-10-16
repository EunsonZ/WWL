"""Deterministic SVG from the same immutable fixture and observed JSON."""
import argparse
import html
import json
from pathlib import Path


def render(spec, actual):
    xy={'a':(150,170),'b':(430,170),'c':(710,170),'d':(430,365),'z':(710,365),'t7':(150,365)}
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="560" viewBox="0 0 1000 560" role="img" aria-labelledby="title desc">',
           '<title id="title">同一属性图，三种路径规则</title>',
           '<desc id="desc">e1和e4是a到b的两条独立边；e2从b返回a。e3到c，e5 e6经d到c。TEACHES不属于REQUIRES查询。下表来自同一输入的实际完整输出。</desc>',
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10Z" fill="#40516d"/></marker></defs>',
           '<rect width="1000" height="560" fill="white"/>',
           '<g font-family="PingFang SC, sans-serif" fill="#16263d"><text x="45" y="42" font-size="24">边的身份、方向和类型都参与答案</text><text x="45" y="73" font-size="16">实线：REQUIRES　虚线：TEACHES（查询排除）　z：存在但孤立</text>']
    routes={'e1':('M180 150 Q290 82 400 150',285,108),'e4':('M185 175 L395 175',285,166),
            'e2':('M402 198 Q290 265 178 198',285,244),'e3':('M465 170 L675 170',555,155),
            'e5':('M176 192 L402 342',255,295),'e6':('M455 342 L685 192',595,292),
            'e7':('M170 139 Q430 75 690 139',465,99),'e8':('M150 330 L150 205',75,278)}
    for e in spec['edges']:
        path,x,y=routes[e['id']]; dash=' stroke-dasharray="7 5"' if e['type']=='TEACHES' else ''
        label=e['id']+(' (TEACHES)' if e['type']=='TEACHES' else '')
        parts.append(f'<path d="{path}" fill="none" stroke="#40516d" stroke-width="2" marker-end="url(#arrow)"{dash}/><text x="{x}" y="{y}" font-size="16" text-anchor="middle">{html.escape(label)}</text>')
    for n in spec['nodes']:
        x,y=xy[n['id']]
        parts.append(f'<circle cx="{x}" cy="{y}" r="34" fill="#eef3fc" stroke="#40516d" stroke-width="2"/><text x="{x}" y="{y+6}" text-anchor="middle" font-size="22">{n["id"]}</text>')
    parts.append('<text x="45" y="440" font-size="18">a → c，1..5 条边：完整输出中的路径数量</text>')
    for i,v in enumerate(actual['variants'][:3]):
        counts=[next(q['bounded']['path_count'] for q in v['queries'] if q['query_id']==f'a_c_1_5_{rule}') for rule in ['walk','trail','simple']]
        parts.append(f'<text x="45" y="{474+i*30}" font-size="17">{v["variant"]}:　walk {counts[0]}　trail {counts[1]}　simple {counts[2]}</text>')
    parts.append('</g></svg>')
    return '\n'.join(parts)+'\n'


def main():
    p=argparse.ArgumentParser(); p.add_argument('--spec',type=Path,required=True); p.add_argument('--actual',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); a.out.write_text(render(json.loads(a.spec.read_text()),json.loads(a.actual.read_text())))
if __name__=='__main__': main()
