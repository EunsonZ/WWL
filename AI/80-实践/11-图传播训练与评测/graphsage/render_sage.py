"""SVGs and a table from saved SAGE results; never train or change selection."""
import argparse
import json
from pathlib import Path
from html import escape
import statistics


def text(x,y,value,size=15,extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" {extra}>{escape(str(value))}</text>'


def line(x1,y1,x2,y2,color='#54616c',extra=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" {extra}/>'


def base(title,description,w,h):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title><desc>{escape(description)}</desc>',f'<rect width="{w}" height="{h}" fill="white"/><g font-family="sans-serif" fill="#172d3c">']


def curve(points,color,extra=''):
    return f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="'+ ' '.join(f'{x},{y}'for x,y in points)+f'" {extra}/>'


def enum_plot(enumeration,output):
    parts=base('Exact sampling variance does not make a nonlinear network unbiased','All subsets of neighbors -1,0,1,2. Left: sample mean variance equals finite-population formula. Right: expectation of ReLU(sample mean minus .5) differs from ReLU(population mean minus .5).',1100,420)
    parts.append(text(20,27,'Uniform sampling WITHOUT replacement: all finite subsets, no Monte Carlo error',19))
    for panel in (0,1):
        ox=panel*535+70;x=lambda f:ox+(f-1)*125
        maximum=1.5 if panel==0 else .6;y=lambda v:330-230*v/maximum
        parts+=[line(ox,80,ox,330),line(ox,330,ox+375,330)]
        for j in range(4):
            v=maximum*j/3;parts+=[line(ox,y(v),ox+375,y(v),'#e6ebef'),text(ox-9,y(v)+4,f'{v:.2f}',13,'text-anchor="end"')]
        for f in (1,2,3,4):parts.append(text(x(f),354,f,14,'text-anchor="middle"'))
        if panel==0:
            parts.append(text(ox,65,'Variance of sample mean (feature units squared)',16))
            parts.append(curve([(x(r['fanout']),y(r['variance']))for r in enumeration['rows']],'#166b99'))
            for r in enumeration['rows']:parts.append(f'<circle cx="{x(r["fanout"])}" cy="{y(r["theory_variance"])}" r="4" fill="white" stroke="#166b99" stroke-width="2"/>')
        else:
            parts.append(text(ox,65,'After ReLU(t - .5): output feature units',16))
            parts.append(curve([(x(r['fanout']),y(r['mean_relu_of_centered_sample']))for r in enumeration['rows']],'#b45524'))
            parts.append(line(ox,y(0),ox+375,y(0),'#52616b','stroke-width="3" stroke-dasharray="5 4"'))
        parts.append(text(ox+105,393,'Fanout f (integer)',16))
    parts +=[text(85,100,'line: enumeration; circles: exact formula',13),text(620,100,'solid: E[ReLU]; dashed: ReLU(E)=0',13),'</g></svg>']
    (output/'sampling_enumeration.svg').write_text('\n'.join(parts))


def selected_data(root):
    summary=json.loads((root/'results/summary.json').read_text());selection=json.loads((root/'results/selection.json').read_text())
    baseline=json.loads((root/'results/baseline_reference.json').read_text());rows=[]
    for item in selection:
        stat=next(r for r in summary if all(r[k]==item[k]for k in ('seed','regime','fanout','depth'))and r['split']=='test')
        rows.append(item|stat|{'model':'full'if item['fanout']is None else f'f{item["fanout"]}'})
    for item in baseline['selection']:
        raw=[r for r in baseline['raw_predictions']if all(r[k]==item[k]for k in ('seed','regime','depth'))and r['split']=='test']
        rows.append(item|{'model':'no_graph(reused)','accuracy':statistics.mean(r['accuracy']for r in raw),'graph_accuracy_min':min(r['accuracy']for r in raw),'graph_accuracy_max':max(r['accuracy']for r in raw)})
    return rows


def task_plot(rows,output):
    parts=base('GraphSAGE full and sampled neighbors versus reused no-graph control','Each marker is one seed mean over four test graphs. Horizontal short lines are three-seed means. Fanout is not selected on test. Baseline is published and reused, with different parameter budget.',1100,460)
    parts.append(text(20,27,'Validation-selected depth/epoch; TEST graph-mean accuracy (3 seeds, 4 graphs/seed)',19))
    models=['no_graph(reused)','full','f2','f4'];colors=['#52616b','#166b99','#bd5424','#34814f']
    for panel,regime in enumerate(('homophily','heterophily')):
        ox=panel*540+70;x=lambda j:ox+40+j*115;y=lambda v:350-260*v
        parts+=[text(ox,65,regime,20),line(ox,90,ox,350),line(ox,350,ox+435,350)]
        for v in (0,.25,.5,.75,1):parts+=[line(ox,y(v),ox+435,y(v),'#e6ebef'),text(ox-10,y(v)+4,f'{v:g}',13,'text-anchor="end"')]
        for j,(model,color)in enumerate(zip(models,colors)):
            vals=[r['accuracy']for r in rows if r['regime']==regime and r['model']==model]
            mean=statistics.mean(vals)
            for seed_index,value in enumerate(vals):
                xx=x(j)+(seed_index-1)*9;yy=y(value)
                if seed_index==0:parts.append(f'<circle cx="{xx}" cy="{yy}" r="4" fill="{color}"/>')
                elif seed_index==1:parts.append(f'<rect x="{xx-4}" y="{yy-4}" width="8" height="8" fill="{color}"/>')
                else:parts.append(f'<path d="M{xx},{yy-5} l-5,9 h10 z" fill="{color}"/>')
            parts+=[line(x(j)-23,y(mean),x(j)+23,y(mean),color,'stroke-width="3"'),text(x(j),376,'no_graph*'if j==0 else model,14,'text-anchor="middle"'),text(x(j),402,f'mean={mean:.4f}',13,'text-anchor="middle"')]
    parts+=[text(40,441,'circle=seed17; square=seed29; triangle=seed43; *published baseline reused; no confidence intervals',14),'</g></svg>']
    (output/'sage_comparison.svg').write_text('\n'.join(parts))


def degree_audit(root, inputs_path, rows):
    graphs={g['id']:g for g in json.loads(inputs_path.read_text())['graphs']}
    raw=json.loads((root/'results/raw_predictions.json').read_text())
    baseline=json.loads((root/'results/baseline_reference.json').read_text())['raw_predictions']
    result=[]
    for item in rows:
        source=baseline if item['model']=='no_graph(reused)'else raw
        matches=[r for r in source if r['split']=='test' and r['seed']==item['seed']and r['regime']==item['regime']and r['depth']==item['depth']and (item['model']=='no_graph(reused)'or r['fanout']==item['fanout'])]
        bins={'D0':[],'D1-2':[],'D3-5':[],'D6+':[]}
        for record in matches:
            graph=graphs[record['graph_id']]
            for adjacency,y,logit in zip(graph['A'],record['y'],record['logits']):
                degree=sum(adjacency);label='D0'if degree==0 else 'D1-2'if degree<=2 else 'D3-5'if degree<=5 else 'D6+'
                bins[label].append(int((logit>=0)==bool(y)))
        result.append({k:item[k]for k in ('seed','regime','model')}|{'bins':{key:{'correct':sum(vals),'nodes':len(vals),'accuracy':sum(vals)/len(vals)if vals else None}for key,vals in bins.items()}})
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).parent);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--inputs',type=Path)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    enum_plot(json.loads((args.root/'results/enumeration.json').read_text()),args.output)
    rows=selected_data(args.root);task_plot(rows,args.output)
    inputs=args.inputs or args.root.parent/'inputs.json'
    (args.output/'degree_audit.json').write_text(json.dumps(degree_audit(args.root,inputs,rows),indent=2)+'\n')
    table=['| seed | 环境 | 模型 | val选深度 | val选epoch | test逐图均值 | 逐图最小–最大 |','| --- | --- | --- | --- | --- | --- | --- |']
    for row in sorted(rows,key=lambda r:(r['seed'],r['regime'],r['model'])):
        table.append(f'| {row["seed"]} | {row["regime"]} | {row["model"]} | {row["depth"]} | {row["epoch"]} | {row["accuracy"]:.4f} | {row["graph_accuracy_min"]:.4f}–{row["graph_accuracy_max"]:.4f} |')
    (args.output/'selected_table.md.txt').write_text('\n'.join(table)+'\n')
    (args.output/'selected_data.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':main()
