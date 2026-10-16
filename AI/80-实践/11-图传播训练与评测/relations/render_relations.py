"""Rebuild two SVGs and three numerical/table derivatives; no training."""
import argparse
import html
import json
import math
from pathlib import Path
import numpy as np
import relations as r


def load(path):return json.loads(path.read_text())
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def text(x,y,s,size=15,color='#172b4d',anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(s))}</text>'
def svg(body,title,desc,width,height):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc><rect width="100%" height="100%" fill="white"/>'+body+'</svg>\n'
def edge(x1,y1,x2,y2,color):
    return f'<path d="M{x1},{y1}L{x2},{y2}" stroke="{color}" stroke-width="3" fill="none" marker-end="url(#arrow)"/>'
def node(x,y,label,value):
    return f'<circle cx="{x}" cy="{y}" r="24" fill="#dfe8f2"/>'+text(x,y+5,label,16,anchor='middle')+text(x,y+47,f'x = {value}',14,anchor='middle')


def render(root,out):
    out.mkdir(parents=True,exist_ok=False);inputs=load(root/'inputs.json');protocol=load(root/'protocol.json');checkpoints=load(root/'results/checkpoints.json');summary=load(root/'results/summary.json')
    selected={(row['seed'],row['model']):row for row in checkpoints};table=['| seed | decoder | selected epoch | test CE | raw MRR | filtered MRR | filtered Hits@1 | filtered Hits@3 |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in summary:
        if row['split']=='test':
            sel=selected[row['seed'],row['model']];table.append(f"| {row['seed']} | {row['model']} | {sel['epoch']} | "+' | '.join(f'{row[key]:.6f}'for key in ('cross_entropy','raw_mrr','filtered_mrr','filtered_hits1','filtered_hits3'))+' |')
    (out/'results-table.md').write_text('\n'.join(table)+'\n')
    # Relation-label counterexample and a multiplicity fixture use the exact encoder.
    x=np.array([[0.],[1.],[3.]])
    friend=np.zeros((3,3));blocks=np.zeros((3,3));friend[0,1]=1;blocks[0,2]=1
    weights={'friend':np.array([[1.]]),'blocks':np.array([[-1.]])};root_weight=np.zeros((1,1))
    examples=[]
    for b in ({'friend':friend,'blocks':blocks},{'friend':blocks,'blocks':friend}):
        examples.append({'X':x.tolist(),'normalized':{k:v.tolist()for k,v in b.items()},'weights':{k:v.tolist()for k,v in weights.items()},'encoded':r.encode(x,b,weights,root_weight).tolist()})
    count=np.zeros((3,3));count[0,1]=2;count[0,2]=1;degree=count.sum(axis=1,keepdims=True);normal=np.divide(count,degree,out=np.zeros_like(count),where=degree>0)
    multiple={'counts':count.tolist(),'normalized':normal.tolist(),'X':x.tolist(),'encoded':r.encode(x,{'r':normal},{'r':np.ones((1,1))},root_weight).tolist()}
    dump(out/'message-fixtures.json',{'relation_swap':examples,'multiplicity':multiple})
    body='<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#52677f"/></marker></defs>'+text(30,32,'Relation identity changes the message; entity order does not',22)
    for panel,example in enumerate(examples):
        cx=245+panel*490;cy=200
        body+=edge(cx-120,110,cx-20,cy-24,'#0072B2'if panel==0 else'#D55E00')+edge(cx+120,110,cx+20,cy-24,'#D55E00'if panel==0 else'#0072B2')
        body+=node(cx-130,90,'u',1)+node(cx+130,90,'v',3)+node(cx,cy,'i',0)
        labels=['friend (+1)','blocks (-1)']if panel==0 else['blocks (-1)','friend (+1)']
        body+=text(cx-200,166,labels[0],14)+text(cx+65,166,labels[1],14)
        body+=text(cx,294,f'encoded i = {example["encoded"][0][0]:g}',19,anchor='middle')
    body+=text(30,354,'Both directed untyped adjacency matrices are identical; only relation labels are swapped.',16)
    body+=text(30,400,'Multiplicity fixture: i receives x=1 twice and x=3 once within one relation.',16)
    body+=text(30,438,f'Relation mean = (2*1+3)/3 = {multiple["encoded"][0][0]:.6f}; deduplicating gives 2.',16)
    body+=text(30,478,'Root weight is zero here; all values are computed by the same encode() used in the practice.',14)
    (out/'relation-messages.svg').write_text(svg(body,'Relation messages and multiplicity','Two relation labelings have equal untyped adjacency and opposite encoded values; multiplicity changes the normalized mean.',1000,510))
    matrices=[];model_seed=17;public=inputs['public'];pairs=[(i,j,0)for i in range(8)for j in range(8)]
    for model in protocol['models']:
        item=selected[model_seed,model];params={k:np.asarray(v)for k,v in item['params'].items()};h=r.fixed_embeddings(public,model);matrix=r.scores(params,h,pairs,model).reshape(8,8);matrices.append(matrix)
    bound=math.ceil(max(float(np.abs(matrix[~np.eye(8,dtype=bool)]).max())for matrix in matrices));truth={tuple(t)for split in ('train','val','test')for t in inputs[split]['positives']}
    dump(out/'score-matrices.json',{'seed':model_seed,'models':protocol['models'],'matrices':[m.tolist()for m in matrices],'common_color_abs_bound':bound,'display_self_cells':'masked, not legal candidates','positive_outline':sorted(list(truth))})
    def color(value):
        z=min(1,abs(value)/bound);end=(213,94,0)if value>=0 else(0,114,178);return '#'+''.join(f'{round(255+(component-255)*z):02x}'for component in end)
    body=text(30,30,'Fixed encoder, trained decoder: scores for seed 17',22)
    for panel,(model,matrix)in enumerate(zip(protocol['models'],matrices)):
        x0=70+panel*350;y0=135;cell=29
        body+=text(x0+116,74,model,19,anchor='middle')+text(x0+116,99,'tail Person (column)',13,anchor='middle')
        for j in range(8):body+=text(x0+j*cell+cell/2,y0-12,f'P{j}',12,anchor='middle')
        for i in range(8):
            body+=text(x0-10,y0+i*cell+19,f'P{i}'+('*'if i in protocol['query_heads']['test']else''),12,'#ad1f1f'if i in protocol['query_heads']['test']else'#172b4d',anchor='end')
            for j in range(8):
                x0c=x0+j*cell;y=y0+i*cell
                if i==j:fill='#d6d8dc';label='x'
                else:fill=color(matrix[i,j]);label=f'{matrix[i,j]:.1f}'
                outline='black'if(i,'next',j)in truth else'white';sw=2 if outline=='black'else .6
                body+=f'<rect x="{x0c}" y="{y}" width="{cell}" height="{cell}" fill="{fill}" stroke="{outline}" stroke-width="{sw}"/>'+text(x0c+cell/2,y+19,label,10,anchor='middle')
    body+=text(30,407,'Rows are query heads; * marks test heads. Black outlines: positive facts, used only for display.',15)
    body+=text(30,439,f'Common color scale: blue = -{bound}, white = 0, orange = +{bound}. Values are logits, not probabilities.',15)
    body+=text(30,472,'Gray self cells are excluded from all legal ranking candidates; no_graph scores are tied.',15)
    body+=text(30,504,'DistMult scores are symmetric; full bilinear scores can differ when head and tail exchange.',15)
    (out/'decoder-scores.svg').write_text(svg(body,'Decoder score matrices','Three actual checkpoint score matrices share the same logit color scale, with illegal self cells masked and true target facts outlined.',1100,535))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();render(args.root,args.output)
