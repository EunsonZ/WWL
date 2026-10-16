"""Generate accessible SVG figures directly from the fixed spec/actual/layout results."""
import argparse
from html import escape
import json
from pathlib import Path


def text(x, y, value, size=16, fill="#17212b"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}">{escape(str(value))}</text>'


def svg(width, height, title, desc, nodes):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="'+str(width)+'" height="'+str(height)+'" viewBox="0 0 '+str(width)+' '+str(height)+'" role="img" aria-labelledby="title desc">\n'
            '<title id="title">'+escape(title)+'</title><desc id="desc">'+escape(desc)+'</desc>'
            '<rect width="100%" height="100%" fill="white"/>'
            '<g font-family="sans-serif">'+''.join(nodes)+'</g></svg>\n')


def cost_figure(result):
    n=result["N"]
    rows=result["row_scan"]["metrics"]
    cols=result["column_scan"]["metrics"]
    nodes=[text(32,35,'同一查询：少读列与少进批入口分别省什么？',23),
           text(32,65,f'N={n}；9列×int64；筛选发生日≥10且渠道web；每条事实仍只算一次',15),
           text(32,105,'A · 序列化payload返回字节（不是SSD物理I/O）',18)]
    maximum=max(rows["returned_payload_bytes"],cols["returned_payload_bytes"],1)
    for i,(label,metrics,color) in enumerate([('按行全记录',rows,'#326b9b'),('按列投影4列',cols,'#55916a')]):
        y=132+i*62
        value=metrics["returned_payload_bytes"]
        nodes.append(text(35,y+22,label))
        nodes.append(f'<rect x="205" y="{y}" width="{560*value/maximum:.1f}" height="32" fill="{color}"/>')
        nodes.append(text(210+560*value/maximum,y+23,f'{value:,} bytes',14))
    nodes += [text(32,290,'B · 显式处理入口调用；行内判断/聚合工作仍在',18),
              text(32,318,f'所有路径predicate_rows={n}；selected/aggregate_updates={rows["selected_rows"]}',15)]
    calls=[('逐行入口',rows['operator_calls'])]+[(f'批入口 B={b}',r['metrics']['operator_calls']) for b,r in result['blocked'].items()]
    for i,(label,value) in enumerate(calls):
        y=345+i*40
        nodes.append(text(35,y+21,label,15))
        nodes.append(f'<rect x="205" y="{y}" width="{560*value/max(n,1):.1f}" height="27" fill="#8768a5"/>')
        nodes.append(text(213+560*value/max(n,1),y+20,str(value),14))
    nodes.append(text(32,585,'Python批循环 ≠ SIMD；不据这些计数声称真实引擎加速。',15))
    return svg(980,610,'同一有限工作负载的投影字节与批入口调用','上半图比较行文件完整记录与四列投影返回的序列化字节；下半图比较显式入口调用。单位分开，不给运行时间或物理I/O加速结论。',nodes)


def temporal_figure(spec, actual):
    prefix=actual['trace'][4]['state']
    entities=dict(prefix['entities'])
    dims=[d for d in spec['dimension_snapshots'][0]['rows'] if d['customer_id']=='c1']
    x=lambda day:100+27*day
    nodes=[text(30,35,'晚到的事实：按发生日，还是按收件时的新标签？',23),
           text(30,64,'取投递前缀p=5；r1维度；当前事实版本（不是历史全库快照）',15)]
    for j,d in enumerate(dims):
        y=115+j*85
        hi=d['valid_to'] if d['valid_to'] is not None else 22
        nodes.append(f'<rect x="{x(d["valid_from"])}" y="{y}" width="{27*(hi-d["valid_from"])}" height="40" fill="{["#d6e7f6","#daf0df"][j]}" stroke="#415568"/>')
        nodes.append(text(x(d['valid_from']),y-12,d['sk']+' · '+d['region']+' ['+str(d['valid_from'])+','+(str(d['valid_to']) if d['valid_to'] is not None else '∞')+')',16))
    nodes.append(f'<line x1="{x(10)}" y1="82" x2="{x(10)}" y2="320" stroke="#9a493f" stroke-dasharray="6 4"/>')
    for key,label,y in [('flate','p5: flate/v1',142),('f1','p1: f1/v1',142),('f2','p2: f2/v1',227)]:
        day=entities[key]['after']['occurred_day']
        nodes.append(f'<circle cx="{x(day)}" cy="{y}" r="6" fill="#17212b"/>')
        label_y=290 if key=='flate' else 325 if key=='f1' else 360
        label_x=x(day)+130 if key=='f2' else x(day)
        if key=='f2':
            nodes.append(f'<polyline points="{x(day)},{y+7} {label_x},{y+30} {label_x},{label_y-18}" fill="none" stroke="#415568"/>')
        else:
            nodes.append(f'<line x1="{x(day)}" y1="{y+7}" x2="{label_x}" y2="{label_y-18}" stroke="#415568"/>')
        nodes.append(text(label_x-35,label_y,label+' / day='+str(day),14))
    nodes += [text(30,405,'p5比p2晚收，day3仍属于North；day10恰好归South。',17),
              text(30,435,'后续flate/v2将发生日改成10，需重归属；修订不是把旧标签也再加一次。',15)]
    return svg(850,460,'SCD半开接缝与迟到事实归属','r1客户c1的North区间为零到十不含十，South从十开始。前缀五中迟到的flate业务日三仍属North，f2业务日十属South。',nodes)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--actual',type=Path,required=True)
    p.add_argument('--layout',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    spec=json.loads(a.input.read_text())
    actual=json.loads(a.actual.read_text())
    layout=json.loads(a.layout.read_text())
    a.out.mkdir()
    (a.out/'projection-batches.svg').write_text(cost_figure(layout['result']))
    (a.out/'scd-boundary.svg').write_text(temporal_figure(spec,actual))


if __name__=='__main__':
    main()
