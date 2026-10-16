"""Generate SVGs and result tables from the saved inputs, spectra and predictions.

No training, no model selection changes, no external plotting library.
"""
import argparse
from html import escape
import json
import math
from pathlib import Path
import statistics

COLORS = {'no_graph': '#52616b', 'fixed': '#bd5424', 'joint': '#166b99'}


def read(path):
    return json.loads(path.read_text())


def svg(title, desc, width, height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">',
            f'<title>{escape(title)}</title><desc>{escape(desc)}</desc>',
            f'<rect width="{width}" height="{height}" fill="white"/>',
            '<g font-family="sans-serif" fill="#1b2730">']


def text(x, y, label, size=15, extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" {extra}>{escape(str(label))}</text>'


def line(x1, y1, x2, y2, color='#536273', extra=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" {extra}/>'


def curve(points, color, extra=''):
    return '<polyline fill="none" stroke-width="2.5" stroke="' + color + '" points="' + ' '.join(f'{x:.3f},{y:.3f}' for x,y in points) + '" ' + extra + '/>'


def nodes(s, dest):
    parts = svg('Pulse diffusion on C6 and two triangles', 'Same 0 to 1 color scale for all eight panels. Numbers display node index and scalar feature. Layout is not a model input.', 1240, 620)
    parts += [text(25, 28, 'h0 = e1; P = (A + I)/3. Every panel uses the SAME scalar color scale [0,1].', 19)]
    for row, name in enumerate(('cycle6','two_triangles')):
        data = s[name]
        for col, k in enumerate((0,1,4,12)):
            ox, oy = col*305+20, row*265+55
            parts.append(text(ox,oy, f'{name}; k={k}', 17))
            if row == 0:
                pos=[(ox+145+82*math.cos(i*math.pi/3),oy+110+70*math.sin(i*math.pi/3))for i in range(6)]
            else:
                pos=[(ox+30,oy+60),(ox+110,oy+60),(ox+70,oy+145),(ox+185,oy+60),(ox+265,oy+60),(ox+225,oy+145)]
            for i in range(6):
                for j in range(i+1,6):
                    if data['A'][i][j]:parts.append(line(*pos[i],*pos[j],extra='stroke-width="2"'))
            for i,(xx,yy) in enumerate(pos):
                v=data['history'][k]['h'][i]
                # Fixed monotone blue scale, independent of each panel's extrema.
                r,g,b=(round(246-220*v), round(249-145*v), round(252-100*v))
                parts.append(f'<circle cx="{xx}" cy="{yy}" r="19" fill="rgb({r},{g},{b})" stroke="#223e50"/>')
                parts.append(text(xx,yy+5,i+1,14,'text-anchor="middle" '+('fill="white"'if v>.6 else '')))
                parts.append(text(xx,yy+38,f'{v:.4f}',13,'text-anchor="middle"'))
    for i in range(101):
        v=i/100;r,g,b=(round(246-220*v),round(249-145*v),round(252-100*v))
        parts.append(f'<rect x="{360+4*i}" y="580" width="4.1" height="15" fill="rgb({r},{g},{b})"/>')
    parts += [text(320,593,'0'),text(775,593,'1'),text(25,613,'Values: dimensionless. Circles contain node indices; below circles: h_k values.',13),'</g></svg>']
    (dest/'spectral_nodes.svg').write_text('\n'.join(parts))


def norm_plot(s,dest):
    p=svg('Centering norms distinguish component means', 'Global centering is different from distance to component-mean projection. C6 norm is bounded by sqrt(5/6)*(2/3)^k.',860,450)
    x=lambda k:75+55*k;y=lambda v:350-280*v
    for k in (0,2,4,6,8,10,12):p +=[line(x(k),70,x(k),350,'#e7ebee'),text(x(k),374,k,14,'text-anchor="middle"')]
    for v in (0,.2,.4,.6,.8,1):p +=[line(75,y(v),735,y(v),'#e7ebee'),text(63,y(v)+5,f'{v:.1f}',14,'text-anchor="end"')]
    p += [text(20,28,'Euclidean norm (dimensionless)',19),line(75,70,75,350),line(75,350,735,350),text(330,409,'Propagation steps k (integer)',17)]
    for name,key,color,dash in [('cycle6','distance_to_limit','#166b99',''),('two_triangles','global_centered_norm','#bd5424',''),('two_triangles','distance_to_limit','#30814b','stroke-dasharray="4 3"')]:
        p.append(curve([(x(r['k']),y(r[key]))for r in s[name]['history']],color,dash))
    p.append(curve([(x(k),y(math.sqrt(5/6)*(2/3)**k))for k in range(13)],'#714c92','stroke-dasharray="7 4"'))
    for i,(label,color)in enumerate([('C6: distance to global mean','#166b99'),('C6: spectral upper bound','#714c92'),('Two triangles: global centering','#bd5424'),('Two triangles: component projection','#30814b')]):
        p += [line(400,30+i*19,425,30+i*19,color,extra='stroke-width="3"'),text(433,35+i*19,label,13)]
    p.append('</g></svg>');(dest/'spectral_norm.svg').write_text('\n'.join(p))


def accuracy_plot(summary,dest):
    p=svg('Predeclared test curves by depth and edge regime', 'Each faint mark is a seed average over four independent test graphs. Thick lines are three-seed means. No test-based depth selection is used.',1120,450)
    p.append(text(25,27,'TEST accuracy by predeclared depth; 3 seeds x 4 graphs each (no confidence intervals)',19))
    for panel,regime in enumerate(('homophily','heterophily')):
        ox=panel*550+70;x=lambda k:ox+100*k;y=lambda v:350-270*v
        p += [text(ox,65,regime,20),line(ox,80,ox,350),line(ox,350,ox+400,350)]
        for v in (0,.25,.5,.75,1):p += [line(ox,y(v),ox+400,y(v),'#e7ebee'),text(ox-9,y(v)+4,f'{v:g}',13,'text-anchor="end"')]
        for k in (0,1,2,4):p.append(text(x(k),373,k,14,'text-anchor="middle"'))
        for family,color in COLORS.items():
            points=[]
            for k in (0,1,2,4):
                vals=[r['accuracy']for r in summary if r['regime']==regime and r['family']==family and r['depth']==k and r['split']=='test']
                points.append((x(k),y(statistics.mean(vals))))
                for j,v in enumerate(vals):p.append(f'<circle cx="{x(k)+(j-1)*5}" cy="{y(v)}" r="3" fill="{color}" opacity=".45"/>')
            p.append(curve(points,color, {'no_graph':'stroke-dasharray="2 4"','fixed':'stroke-dasharray="8 4"','joint':''}[family]))
        p.append(text(ox+115,407,'Depth K (integer)',16))
    for j,(family,color)in enumerate(COLORS.items()):p += [line(260+j*220,432,285+j*220,432,color,extra='stroke-width="3"'),text(294+j*220,437,family)]
    p.append('</g></svg>');(dest/'test_depth.svg').write_text('\n'.join(p))


def training_plot(checkpoints,selection,dest):
    p=svg('Seed 43 homophily training and validation curves', 'Each family uses the depth chosen by validation, not test. Solid lines are train cross entropy and dashed lines validation. Dots mark selected epoch.',900,450)
    chosen=[r for r in selection if r['seed']==43 and r['regime']=='homophily']
    traces=[]
    for row in chosen:
        item=next(c for c in checkpoints if all(c[k]==row[k]for k in ('seed','regime','family','depth')))
        traces.append((row,item['trace']))
    top=max(r[k]for _,trace in traces for r in trace for k in ('train_ce','val_ce'))*1.05
    x=lambda e:75+(e-1)*650/119;y=lambda v:350-270*v/top
    p += [text(20,28,'Seed 43, homophily: train (solid), validation (dashed)',19),line(75,80,75,350),line(75,350,725,350)]
    for e in (1,20,40,60,80,100,120):p.append(text(x(e),374,e,13,'text-anchor="middle"'))
    for i in range(5):
        v=top*i/4;p += [line(75,y(v),725,y(v),'#e7ebee'),text(64,y(v)+4,f'{v:.2f}',13,'text-anchor="end"')]
    for j,(row,trace)in enumerate(traces):
        color=COLORS[row['family']]
        for key,dash in [('train_ce',''),('val_ce','stroke-dasharray="6 4"')]:p.append(curve([(x(t['epoch']),y(t[key]))for t in trace],color,dash))
        t=trace[row['epoch']-1];p.append(f'<circle cx="{x(row["epoch"])}" cy="{y(t["val_ce"])}" r="4" fill="{color}"/>')
        p +=[line(300,45+19*j,325,45+19*j,color,extra='stroke-width="3"'),text(333,50+19*j,f'{row["family"]}: K={row["depth"]}, epoch={row["epoch"]}',13)]
    p += [text(330,413,'Training epoch (integer)',17),text(25,440,'Y: graph-mean cross entropy (natural-log units); plotted losses exclude L2 penalty.',13),'</g></svg>']
    (dest/'training_seed43.svg').write_text('\n'.join(p))


def derived(inputs,summary,selection,dest):
    audit={'label_feature_oracle':{'description':'ILLEGAL: append 2*y-1 as a feature and classify by its sign', 'accuracy':None, 'per_graph':[]}, 'test_selection_optimism':[], 'observed_edge_homophily':[]}
    for graph in inputs['graphs']:
        if graph['split'] == 'test':
            leaked_feature = [2*y-1 for y in graph['y']]
            prediction = [int(value > 0) for value in leaked_feature]
            correct = sum(p == y for p,y in zip(prediction, graph['y']))
            audit['label_feature_oracle']['per_graph'].append({'graph_id':graph['id'], 'correct':correct, 'nodes':len(prediction)})
    leak_rows = audit['label_feature_oracle']['per_graph']
    audit['label_feature_oracle']['accuracy'] = sum(r['correct'] for r in leak_rows)/sum(r['nodes'] for r in leak_rows)
    for row in selection:
        candidates=[s for s in summary if all(s[k]==row[k]for k in ('seed','regime','family'))and s['split']=='test']
        actual=next(s for s in candidates if s['depth']==row['depth'])
        winner=max(candidates,key=lambda s:s['accuracy'])
        audit['test_selection_optimism'].append({k:row[k]for k in ('seed','regime','family')}|{'validation_selected_depth':row['depth'],'honest_test_accuracy':actual['accuracy'],'ILLEGAL_test_selected_depth':winner['depth'],'ILLEGAL_max_test_accuracy':winner['accuracy']})
    for graph in inputs['graphs']:
        same=total=0
        for i in range(len(graph['A'])):
            for j in range(i+1,len(graph['A'])):
                if graph['A'][i][j]:total+=1;same+=int(graph['y'][i]==graph['y'][j])
        audit['observed_edge_homophily'].append({'graph_id':graph['id'],'regime':graph['regime'],'split':graph['split'],'same_edges':same,'total_edges':total,'fraction':same/total if total else None})
    (dest/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    lines=['| seed | 环境 | 模型 | val选K | val选epoch | test逐图均值 | test逐图最小–最大 |','| --- | --- | --- | --- | --- | --- | --- |']
    for row in selection:
        s=next(s for s in summary if all(s[k]==row[k]for k in ('seed','regime','family','depth')) and s['split']=='test')
        lines.append(f'| {row["seed"]} | {row["regime"]} | {row["family"]} | {row["depth"]} | {row["epoch"]} | {s["accuracy"]:.4f} | {s["graph_accuracy_min"]:.4f}–{s["graph_accuracy_max"]:.4f} |')
    (dest/'selected_table.md.txt').write_text('\n'.join(lines)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).parent)
    ap.add_argument('--output',type=Path,required=True,help='new directory')
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    root=args.root;s=read(root/'spectral.json');summary=read(root/'results/summary.json')
    selection=read(root/'results/selection.json');checkpoints=read(root/'results/checkpoints.json')
    nodes(s,args.output);norm_plot(s,args.output);accuracy_plot(summary,args.output)
    training_plot(checkpoints,selection,args.output)
    derived(read(root/'inputs.json'),summary,selection,args.output)


if __name__=='__main__':main()
