"""Deterministic SVGs and selected tables from saved GAT results. No training."""
import argparse
from html import escape
import json
from pathlib import Path
import statistics


def read(path):return json.loads(path.read_text())


def text(x,y,label,size=15,extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" {extra}>{escape(str(label))}</text>'


def line(x1,y1,x2,y2,color='#536273',extra=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" {extra}/>'


def begin(title,desc,w,h):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title><desc>{escape(desc)}</desc>',f'<rect width="{w}" height="{h}" fill="white"/><g font-family="sans-serif" fill="#192f3f">']


def path_plot(fixture,destination):
    parts=begin('GAT masked attention on the three-node path','Rows are receivers, columns senders. Self is included. Nonedges are zero. Same head_forward as training source, W=1, left=right=1, bias=0, no post-activation.',1050,470)
    parts.append(text(25,30,'One head: W=1, aL=aR=1; self included; no post-activation',20))
    for i,x in enumerate((90,240,390)):
        if i<2:parts.append(line(x,180,x+150,180,extra='stroke-width="3"'))
    for i,x in enumerate((90,240,390)):
        parts +=[f'<circle cx="{x}" cy="180" r="28" fill="#e8f2fa" stroke="#23648b" stroke-width="2"/>',text(x,186,i+1,19,'text-anchor="middle"'),text(x,235,f'X={fixture["X"][i][0]:g}',17,'text-anchor="middle"')]
    parts +=[text(70,95,'Input graph: path 1-2-3',20),text(550,95,'alpha: row receiver i, column sender j',19)]
    for j in range(3):parts.append(text(655+j*105,127,f'j={j+1}',16,'text-anchor="middle"'))
    for i in range(3):
        parts.append(text(570,171+i*65,f'i={i+1}',16))
        for j in range(3):
            value=fixture['alpha'][i][j];xx=605+j*105;yy=140+i*65
            r,g,b=round(248-180*value),round(250-95*value),round(252-40*value)
            parts +=[f'<rect x="{xx}" y="{yy}" width="100" height="55" fill="rgb({r},{g},{b})" stroke="white"/>',text(xx+50,yy+33,f'{value:.4f}'if value else '0 (masked)',15,'text-anchor="middle"')]
    parts +=[text(30,320,'Nonedge 1 <- 3 stays zero, despite raw score r13=3.',17),text(30,360,'o = alpha Z = ('+', '.join(f'{v[0]:.6f}'for v in fixture['head_output'])+')',19),text(30,405,'Each receiver row sums to 1; columns need not sum to 1.',17),text(30,445,'Features and outputs are synthetic dimensionless scalars; attention coefficients are dimensionless.',14),'</g></svg>']
    (destination/'path_attention.svg').write_text('\n'.join(parts))


def rank_plot(ranking,destination):
    parts=begin('Static ordering is different from constant attention values','Two shared keys -1,+1 and query offsets -2,+2. Conditional softmax over these TWO keys only. Full GAT rows also contain self; adding candidates does not reverse pair ordering.',850,410)
    parts +=[text(25,30,'One additive GAT head: shared-key ranking stays fixed',20),text(25,65,'Conditional weights over the common two keys ONLY (self omitted here)',16)]
    for i,(query,values)in enumerate(zip(ranking['queries'],ranking['alpha_conditioned_on_common_two_keys'])):
        oy=140+i*120;parts.append(text(30,oy,f'query={query:g}',18))
        for j,(value,color)in enumerate(zip(values,('#52616b','#166b99'))):
            y=oy-25+j*40;parts+=[f'<rect x="210" y="{y}" width="{450*value}" height="25" fill="{color}"/>',text(225+450*value,y+19,f'key={ranking["common_keys"][j]:g}: {value:.4f}',16)]
    parts +=[text(25,360,'Both prefer key +1; preference strength changes across the LeakyReLU branches.',16),text(25,394,'Bar length: conditional attention probability, dimensionless; this is not a whole-network impossibility claim.',13),'</g></svg>']
    (destination/'static_ranking.svg').write_text('\n'.join(parts))


def selected_rows(root):
    summary=read(root/'results/summary.json');selection=read(root/'results/selection.json');rows=[]
    for row in selection:
        stat=next(s for s in summary if all(s[k]==row[k]for k in ('seed','regime','variant'))and s['split']=='test')
        rows.append(row|stat|{'model':'GAT'if row['variant']=='attention'else 'uniform'})
    baselines=read(root/'results/baseline_reference.json')
    for name,label in [('no_graph','no_graph*'),('sage_full','SAGE_full*')]:
        data=baselines[name]
        for row in data['selection']:
            records=[r for r in data['raw_predictions']if all(r[k]==row[k]for k in ('seed','regime','depth'))and r['split']=='test']
            rows.append(row|{'model':label,'accuracy':statistics.mean(r['accuracy']for r in records),
                'graph_accuracy_min':min(r['accuracy']for r in records),'graph_accuracy_max':max(r['accuracy']for r in records)})
    return rows


def comparison(rows,destination):
    parts=begin('GAT and uniform control versus published no-graph and GraphSAGE controls','Each marker is a seed average over four independent test graphs. Short horizontal bars are three-seed means. Published controls reused, not retrained. Parameter and compute budgets differ.',1110,460)
    parts.append(text(20,28,'TEST graph-mean accuracy; fixed architecture, validation-selected epoch',20))
    models=['no_graph*','SAGE_full*','uniform','GAT'];colors=['#52616b','#34814f','#b65626','#166b99']
    for panel,regime in enumerate(('homophily','heterophily')):
        ox=panel*550+70;x=lambda j:ox+40+j*120;y=lambda v:350-260*v
        parts+=[text(ox,65,regime,20),line(ox,90,ox,350),line(ox,350,ox+440,350)]
        for value in (0,.25,.5,.75,1):parts+=[line(ox,y(value),ox+440,y(value),'#e6ebef'),text(ox-10,y(value)+5,f'{value:g}',13,'text-anchor="end"')]
        for j,(model,color)in enumerate(zip(models,colors)):
            values=[r['accuracy']for r in rows if r['regime']==regime and r['model']==model]
            mean=statistics.mean(values)
            for k,value in enumerate(values):
                xx=x(j)+(k-1)*9;yy=y(value)
                if k==0:parts.append(f'<circle cx="{xx}" cy="{yy}" r="4" fill="{color}"/>')
                elif k==1:parts.append(f'<rect x="{xx-4}" y="{yy-4}" width="8" height="8" fill="{color}"/>')
                else:parts.append(f'<path d="M{xx},{yy-5} l-5,9 h10 z" fill="{color}"/>')
            parts+=[line(x(j)-24,y(mean),x(j)+24,y(mean),color,'stroke-width="3"'),text(x(j),377,model,14,'text-anchor="middle"'),text(x(j),404,f'mean={mean:.4f}',13,'text-anchor="middle"')]
    parts+=[text(25,443,'circle=seed17; square=seed29; triangle=seed43; *published/reused; no confidence intervals; public test benchmark',14),'</g></svg>']
    (destination/'gat_comparison.svg').write_text('\n'.join(parts))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).parent);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);fixtures=read(args.root/'results/fixtures.json')
    path_plot(fixtures['path'],args.output);rank_plot(fixtures['ranking'],args.output)
    rows=selected_rows(args.root);comparison(rows,args.output)
    table=['| seed | 环境 | 模型 | val选epoch | test逐图均值 | 逐图最小–最大 |','| --- | --- | --- | --- | --- | --- |']
    for row in sorted(rows,key=lambda r:(r['seed'],r['regime'],r['model'])):
        table.append(f'| {row["seed"]} | {row["regime"]} | {row["model"]} | {row["epoch"]} | {row["accuracy"]:.4f} | {row["graph_accuracy_min"]:.4f}–{row["graph_accuracy_max"]:.4f} |')
    (args.output/'selected_table.md.txt').write_text('\n'.join(table)+'\n')
    (args.output/'selected_data.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':main()
