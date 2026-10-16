"""Render real-panel diagnostics from the frozen source/input/results; no training."""
import argparse
import html
import json
import math
from pathlib import Path
import numpy as np


def load(path):return json.loads(path.read_text())
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def text(x,y,value,size=15,color='#172b4d',anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(value))}</text>'
def svg(body,title,desc,width,height):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc><rect width="100%" height="100%" fill="white"/>'+body+'</svg>\n'


def render(root,out):
    out.mkdir(parents=True,exist_ok=False);data=load(root/'inputs.json');summary=load(root/'results/summary.json');heads=load(root/'results/head_metrics.json');selection=load(root/'results/selection.json');audit=load(root/'results/graph-audit.json');features=np.array(load(root/'results/features.json'));public=data['public'];n=len(public['country_qids']);k=len(public['continent_qids'])
    selected={(x['seed'],x['model']):x for x in selection};table=['| seed | model | selected epoch | test BCE | entity raw MRR | entity filtered MRR | entity Hits@1 | micro filtered MRR |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in summary:
        if row['split']=='test':
            choice=selected[row['seed'],row['model']];table.append(f"| {row['seed'] if row['seed'] is not None else 'fixed'} | {row['model']} | {choice['epoch'] if choice['epoch'] is not None else 'none'} | "+' | '.join(f'{row[key]:.6f}'for key in ('cross_entropy','macro_raw_mrr','macro_filtered_mrr','macro_filtered_hits1','micro_filtered_mrr'))+' |')
    (out/'results-table.md').write_text('\n'.join(table)+'\n')
    chosen=[r for r in heads if r['split']=='test'and(r['seed']==17 or r['model']=='neighbor_prior')];diagnostics=[]
    for head in data['test']['query_heads']:
        diagnostics.append({'entity':public['entities'][head],'graph':audit[head],'metrics':[r for r in chosen if r['head']==head]})
    collisions=[]
    for i,head in enumerate(data['train']['query_heads']):
        for other in data['train']['query_heads'][i+1:]:
            if np.array_equal(features[head],features[other]):collisions.append([public['country_qids'][head],public['country_qids'][other]])
    dump(out/'diagnostics.json',{'test_entities':diagnostics,'train_feature_column_max':features[data['train']['query_heads'],:-1].max(axis=0).tolist(),'train_feature_rank':int(np.linalg.matrix_rank(features[data['train']['query_heads']])),'train_equal_feature_pairs':collisions})
    body=text(30,30,'One graph, five held-out entities: seed 17 + fixed mechanism',21);models=['no_graph','relational','neighbor_prior'];colors=['#73849a','#0072B2','#D55E00'];x0=310;width=650;ybase=100
    for i,head in enumerate(data['test']['query_heads']):
        entity=public['entities'][head];label=entity['label'];label='China'if entity['qid']=='Q148'else label
        body+=text(25,ybase+i*67+16,f"{label} ({entity['qid']})",16)
        for j,model in enumerate(models):
            row=next(r for r in chosen if r['head']==head and r['model']==model);value=row['filtered_mrr'];y=ybase+i*67+j*15
            body+=f'<rect x="{x0}" y="{y}" width="{value*width}" height="10" fill="{colors[j]}"/>'+text(x0+value*width+8,y+10,f'{value:.3f}',12,colors[j])
    bottom=ybase+4*67+55
    for tick in range(6):
        x=x0+width*tick/5;body+=f'<path d="M{x},{bottom}v7" stroke="#172b4d"/>'+text(x,bottom+25,f'{tick/5:.1f}',13,anchor='middle')
    body+=text(x0,bottom+54,'Per-entity filtered mean reciprocal rank (fraction)',15)
    for j,model in enumerate(models):body+=text(30+j*290,bottom+88,model,16,colors[j])
    body+=text(30,bottom+124,'Average facts within each entity, then average entities. Not five independent graph samples.',15)
    body+=text(30,bottom+152,'No confidence interval: same static purposive panel; three optimizer seeds are all reported in the table.',14)
    (out/'entity-results.svg').write_text(svg(body,'Per-entity real KG results','Five test entities, actual seed17 head scores and the predeclared fixed neighbor-prior mechanism; no graph-independent uncertainty claimed.',1100,int(bottom+180)))
    # Draw only public support; train seed labels are available, held-out labels are hidden.
    positions=[]
    for i in range(n):
        group=0 if i<8 else 1 if i<16 else 2;start=0 if group==0 else 8 if group==1 else 16;count=8 if group<2 else n-16;theta=-math.pi/2+2*math.pi*(i-start)/count;center=[200,575,930][group];radius=135 if group<2 else 105
        positions.append((center+radius*math.cos(theta),225+radius*math.sin(theta)))
    edges=sorted({tuple(sorted(edge))for edge in public['border_edges']});body=text(25,30,'Public P47 support + training seeds; held-out P30 is hidden',21)
    for a,b in edges:
        x1,y1=positions[a];x2,y2=positions[b];body+=f'<path d="M{x1},{y1}L{x2},{y2}" stroke="#a8b6c5" stroke-width="1.5"/>'
    parts={head:split for split in ('train','val','test')for head in data[split]['query_heads']};seed_labels={head:[]for head in data['train']['query_heads']}
    short={'Q15':'AF','Q51':'AN','Q48':'AS','Q46':'EU','Q49':'NA','Q538':'OC','Q18':'SA'}
    for head,_,tail in data['train']['positives']:seed_labels[head].append(short[public['entities'][tail]['qid']])
    nodes=[]
    for i,(x,y)in enumerate(positions):
        split=parts[i];color={'train':'#0072B2','val':'#7a459c','test':'#D55E00'}[split];fill='#d9edf8'if split=='train'else'white';body+=f'<circle cx="{x}" cy="{y}" r="23" fill="{fill}" stroke="{color}" stroke-width="3"/>'+text(x,y+5,public['country_qids'][i],11,anchor='middle')
        label=','.join(seed_labels.get(i,[]))if split=='train'else'?';body+=text(x,y+40,label,12,color,anchor='middle');nodes.append({'entity':public['entities'][i],'split':split,'position':[x,y],'visible_seed_labels':seed_labels.get(i,[])})
    body+=text(25,421,'Blue filled: train seed shown. Purple rim: validation. Orange rim: test. ? means P30 is hidden.',15)
    body+=text(25,455,'27 undirected pairs are the explicit closure of 52 recorded directed P47 facts.',15)
    body+=text(25,489,'P47 includes water/point borders. Layout is schematic; distances and positions are not geography.',15)
    body+=text(25,523,'Turkey is isolated inside this truncated panel; this does not mean it has no real-world neighbors.',15)
    dump(out/'support-layout.json',{'nodes':nodes,'undirected_edges':edges,'layout_warning':'schematic panel grouping, not geographic coordinates'})
    (out/'supervised-support.svg').write_text(svg(body,'Supervised relation feature support','Actual fixed border support, with only training continent labels displayed; no validation/test P30 enters features.',1100,555))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();render(args.root,args.output)
