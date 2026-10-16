"""Deterministic SVG and tables from saved graph-level inputs/results; no retraining."""
import argparse
import html
import json
from pathlib import Path
import numpy as np
import graphlevel as g


def load(path):return json.loads(path.read_text())
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def text(x,y,s,size=15,color='#172b4d',anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(s))}</text>'
def svg(body,width=940,height=530):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>'+body+'</svg>\n'

def render(root,out):
    out.mkdir(parents=True,exist_ok=False);protocol=load(root/'protocol.json');summary=load(root/'results/summary.json');selected=load(root/'results/selection.json')
    rows=[r for r in summary if r['split']=='test'];selections={(r['seed'],r['model']):r for r in selected}
    table=['| seed | model | selected epoch / convex steps | test graphs | accuracy | graph-mean CE |','| --- | --- | --- | --- | --- | --- |']
    for r in rows:
        sel=selections[r['seed'],r['model']];step=sel['epoch'] if sel['epoch'] is not None else 'convex '+str(sel['certificate']['steps'])
        table.append(f"| {r['seed']} | {r['model']} | {step} | {r['graphs']} | {r['accuracy']:.6f} | {r['cross_entropy']:.6f} |")
    (out/'results-table.md').write_text('\n'.join(table)+'\n');dump(out/'test-points.json',rows)
    colors=['#0072B2','#D55E00','#009E73'];models=protocol['models'];body=text(30,30,'Finite graph benchmark: every dot is one fixed seed',21)
    for panel,(title,key,maximum)in enumerate([('Graph accuracy (fraction)','accuracy',1.0),('Graph-mean cross entropy (natural log)','cross_entropy',.8)]):
        x0=70+panel*465;y0=365;w=360;h=250
        body+=text(x0,76,title,16)
        for k in range(5):
            val=maximum*k/4;y=y0-h*k/4;body+=f'<path d="M{x0},{y}h{w}" stroke="#dde3ea"/>'+text(x0-10,y+5,f'{val:.2f}',12,anchor='end')
        for j,model in enumerate(models):
            x=x0+25+j*76;body+=text(x,y0+28,model,14,anchor='middle')
            for k,seed in enumerate(protocol['seeds']):
                row=next(r for r in rows if r['seed']==seed and r['model']==model);y=y0-h*row[key]/maximum
                body+=f'<circle cx="{x+(k-1)*8}" cy="{y}" r="4" fill="{colors[k]}"/>'
        body+=f'<path d="M{x0},{y0-h}v{h}h{w}" stroke="#172b4d" fill="none"/>'
    for k,seed in enumerate(protocol['seeds']):body+=text(70+k*155,440,f'seed {seed}',15,colors[k])
    body+=text(30,480,'12 test graphs per seed; topology groups disjoint globally; no confidence interval.',15)
    body+=text(30,506,'fixed is a task-specific structural witness; these dots do not establish a general ranking.',14)
    (out/'test-readouts.svg').write_text(svg(body,height=530))
    # Same unlabeled path, changed mark allocation: a deliberate grouping example, not extra data.
    a=np.zeros((4,4),int)
    for i in range(3):a[i,i+1]=a[i+1,i]=1
    examples=[];body=text(30,32,'One topology, two mark allocations: one identity group',21)
    for k,marked in enumerate([(0,1),(0,2)]):
        x=np.zeros((4,1));x[list(marked)]=1;q=a@x;t=np.maximum(2*x+q-2.5,0);psi=g.fixed_features(a,x,'fixed',10)[0]
        record={'A':a.tolist(),'X':x.tolist(),'neighbor_mark_count':q[:,0].tolist(),'gate':t[:,0].tolist(),'psi':psi,'y':int(a[marked[0],marked[1]]),'group_id':g.canonical(a)};examples.append(record)
        x0=80+k*450;y=150
        for i in range(3):body+=f'<path d="M{x0+i*90},{y}h90" stroke="#73849a" stroke-width="3"/>'
        for i in range(4):
            fill='#D55E00' if x[i,0] else '#dfe8f2';body+=f'<circle cx="{x0+i*90}" cy="{y}" r="22" fill="{fill}"/>'+text(x0+i*90,y+6,i,16,'white' if x[i,0] else '#172b4d',anchor='middle')
        body+=text(x0-35,87,f'marks {marked}; y = {record["y"]}',17)
        for j,(label,values)in enumerate([('x',x[:,0]),('Ax',q[:,0]),('ReLU(2x+Ax-2.5)',t[:,0])]):
            body+=text(x0-35,220+j*38,label,14)
            for i,value in enumerate(values):body+=text(x0+i*90,239+j*38,f'{value:g}',14,anchor='middle')
        body+=text(x0-35,365,f'sum gate = {psi:g}; mean = {t.mean():g}; max = {t.max():g}',15)
    body+=text(30,420,'Both examples have identical unmarked A and therefore the SAME canonical group.',16)
    body+=text(30,453,'They may illustrate a task, but must never be split into train and test as new entities.',15)
    body+=text(30,486,'No self loops. Node numbers are display labels; all three readouts ignore their order.',14)
    dump(out/'readout-fixtures.json',examples);(out/'marked-path.svg').write_text(svg(body,height=515))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();render(args.root,args.output)
