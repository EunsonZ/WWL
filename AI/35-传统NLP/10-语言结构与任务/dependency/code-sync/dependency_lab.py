"""Train-only count potentials and exact single-root projective dependency decoding."""
from collections import Counter,defaultdict
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time

NEG=-math.inf
UPOS=set('ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB X'.split())
_STRUCTURE=None
_STRUCTURE_PATH=None


def set_structure(path=None):
    global _STRUCTURE,_STRUCTURE_PATH
    path=Path(path) if path else Path(__file__).resolve().parents[2]/'code-sync/structure_lab.py'
    spec=importlib.util.spec_from_file_location('published_structure_lab',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    _STRUCTURE,_STRUCTURE_PATH=m,path
    return m


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def write_rows(path,rows):path.write_text(''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in rows))


class DataAccess:
    def __init__(self,root):self.root=Path(root);self.finished=False;self.events=[]
    def features(self,split):
        rows=json.loads((self.root/(split+'-features.json')).read_text())
        for sent in rows:
            for i,r in enumerate(sent['rows'],1):
                if set(r)!={'id','form','upos'} or type(r['id']) is not int or r['id']!=i:raise ValueError('feature rows must exclude targets and preserve ordered IDs')
                if not isinstance(r['form'],str) or not r['form'] or r['upos'] not in UPOS:raise ValueError('FORM/UPOS domain')
        if len({r['sample_id'] for r in rows})!=len(rows):raise ValueError('duplicate sample IDs')
        self.events.append(dict(action='features',split=split,selection_finished=self.finished));return rows
    def targets(self,split):
        if split=='test' and not self.finished:raise RuntimeError('test targets locked until both model choices')
        rows=json.loads((self.root/(split+'-targets.json')).read_text())
        if len({r['sample_id'] for r in rows})!=len(rows):raise ValueError('duplicate target sample IDs')
        self.events.append(dict(action='targets',split=split,selection_finished=self.finished));return rows
    def finish_selection(self,decisions):
        if {r['model'] for r in decisions}!={'geometry','upos_geometry'} or len(decisions)!=2:raise ValueError('both choices required')
        self.finished=True;self.events.append(dict(action='finish_selection',models=[r['model'] for r in decisions]))


def references(features,targets):
    keyed={r['sample_id']:r['rows'] for r in targets}
    if set(keyed)!={r['sample_id'] for r in features}:raise ValueError('feature/target identities differ')
    out={}
    for s in features:
        target=keyed[s['sample_id']]
        if len(target)!=len(s['rows']) or any(r['id']!=t['id'] for r,t in zip(s['rows'],target)):raise ValueError('target token alignment differs')
        rows=[dict(r,head=t['head'],relation=t['relation']) for r,t in zip(s['rows'],target)]
        _STRUCTURE.validate(rows);out[s['sample_id']]=rows
    return out


def geometry(h,d):
    if h==0:return 'ROOT','0'
    distance=abs(h-d);return ('L' if h<d else 'R'),str(distance) if distance<4 else '4+'


class CountModel:
    def __init__(self,mode):
        if mode not in {'geometry','upos_geometry'}:raise ValueError('unknown model')
        self.mode=mode;self.counts=Counter();self.conditions=Counter();self.labels=[]
    def key(self,rows,h,d,relation):
        direction,bucket=geometry(h,d)
        if self.mode=='geometry':return ('*',direction,bucket,relation)
        return (rows[d-1]['upos'],'<ROOT>' if h==0 else rows[h-1]['upos'],direction,bucket,relation)
    def fit(self,features,targets):
        gold=references(features,targets);self.counts.clear();self.conditions.clear();labels=set()
        for sent in features:
            for d,row in enumerate(gold[sent['sample_id']],1):
                key=self.key(sent['rows'],row['head'],d,row['relation']);self.counts[key]+=1;self.conditions[key[0]]+=1;labels.add(row['relation'])
        self.labels=sorted(labels)
        if 'root' not in labels or len(labels)<2:raise ValueError('need root and ordinary training relations')
        return self
    def matrices(self,rows,alpha):
        if not math.isfinite(alpha) or alpha<=0:raise ValueError('alpha must be finite positive')
        n=len(rows);scores=[[NEG]*(n+1) for _ in range(n+1)];labels=[[None]*(n+1) for _ in range(n+1)]
        ordinary=[r for r in self.labels if r!='root']
        for d in range(1,n+1):
            for h in range(n+1):
                if h==d:continue
                options=['root'] if h==0 else ordinary
                label=max(options,key=lambda r:self.counts[self.key(rows,h,d,r)])
                scores[h][d]=math.log(self.counts[self.key(rows,h,d,label)]+alpha);labels[h][d]=label
        return scores,labels
    def feature_domain_size(self):return 1+(8 if self.mode=='geometry' else 17*8)*(len(self.labels)-1)
    def feature_probability(self,rows,h,d,label,alpha):
        if label not in self.labels or (h==0)!=(label=='root') or not math.isfinite(alpha) or alpha<=0:raise ValueError('feature-label support or smoothing invalid')
        key=self.key(rows,h,d,label)
        return (self.counts[key]+alpha)/(self.conditions[key[0]]+alpha*self.feature_domain_size())
    def state(self):return dict(mode=self.mode,labels=self.labels,feature_domain_size=self.feature_domain_size(),conditions=dict(sorted(self.conditions.items())),counts=[dict(key=list(k),count=v) for k,v in sorted(self.counts.items())])


def projective(heads):
    arcs=[tuple(sorted((h,d))) for d,h in enumerate(heads,1)]
    return not any(a<c<b<d or c<a<d<b for i,(a,b) in enumerate(arcs) for c,d in arcs[i+1:])


def decode(scores):
    """Eisner max-sum per root. Shape (n+1)^2: row head, column dependent.

    L=0/R=1; C is complete, I is incomplete; ROOT0 has no incoming arc.
    Ordered root/split ties; total O(n^4), chart O(n^2); bounded1..20 words.
    """
    n=len(scores)-1
    if not 1<=n<=20 or any(len(row)!=n+1 for row in scores):raise ValueError('square ROOT-inclusive score matrix;1..20 real words')
    if any(math.isnan(v) or v==math.inf for row in scores for v in row):raise ValueError('finite scores or -inf only')
    if any(v!=NEG for v in [scores[h][0] for h in range(n+1)]+[scores[d][d] for d in range(n+1)]):raise ValueError('incoming ROOT and self arcs must be masked')
    best_score=NEG;best_heads=None
    for root in range(1,n+1):
        C=[[[NEG,NEG] for _ in range(n+1)] for _ in range(n+1)];I=[[[NEG,NEG] for _ in range(n+1)] for _ in range(n+1)]
        BC=[[[None,None] for _ in range(n+1)] for _ in range(n+1)];BI=[[[None,None] for _ in range(n+1)] for _ in range(n+1)]
        for i in range(n+1):C[i][i]=[0.,0.]
        for width in range(1,n+1):
            for i in range(n+1-width):
                j=i+width;value=NEG;split=None
                for k in range(i,j):
                    v=C[i][k][1]+C[k+1][j][0]
                    if v>value:value,split=v,k
                for direction,arc in [(0,scores[j][i]),(1,scores[i][j] if i or j==root else NEG)]:
                    I[i][j][direction]=value+arc;BI[i][j][direction]=split
                for k in range(i,j):
                    v=C[i][k][0]+I[k][j][0]
                    if v>C[i][j][0]:C[i][j][0],BC[i][j][0]=v,k
                for k in range(i+1,j+1):
                    v=I[i][k][1]+C[k][j][1]
                    if v>C[i][j][1]:C[i][j][1],BC[i][j][1]=v,k
        value=C[0][n][1]
        if value<=best_score:continue
        heads=[None]*(n+1)
        def recover(i,j,direction,complete):
            if i==j:return
            if complete:
                k=BC[i][j][direction]
                if direction==0:recover(i,k,0,True);recover(k,j,0,False)
                else:recover(i,k,1,False);recover(k,j,1,True)
            else:
                k=BI[i][j][direction];h,d=(j,i) if direction==0 else (i,j)
                if heads[d] is not None:raise AssertionError('duplicate decoded head')
                heads[d]=h;recover(i,k,1,True);recover(k+1,j,0,True)
        recover(0,n,1,True)
        best_score,best_heads=value,heads[1:]
    if best_heads is None:raise ValueError('no finite single-root projective tree')
    if sum(h==0 for h in best_heads)!=1 or not projective(best_heads):raise AssertionError('decoder invariant failed')
    return best_heads,best_score


def predict(model,alpha,sent):
    scores,labels=model.matrices(sent['rows'],alpha);heads,total=decode(scores)
    rows=[dict(r,head=h,relation=labels[h][d]) for d,(r,h) in enumerate(zip(sent['rows'],heads),1)]
    _STRUCTURE.validate(rows);return rows,total


def brief(score):return {k:v for k,v in score.items() if k!='detail'}


def evaluate(model,alpha,features,gold,split):
    out=[]
    for sent in features:
        predicted,total=predict(model,alpha,sent);reference=gold[sent['sample_id']]
        out.append(dict(model=model.mode,alpha=alpha,split=split,sample_id=sent['sample_id'],doc_id=sent['doc_id'],sent_id=sent['sent_id'],form_sha256=sent['form_sha256'],reference=reference,prediction=predicted,score=total,
                        primary=brief(_STRUCTURE.aligned_scores(reference,predicted,False,True)),all_words=brief(_STRUCTURE.aligned_scores(reference,predicted,True,True)),gold_projective=projective([r['head'] for r in reference])))
    return out


def aggregate(rows,metric='primary'):
    n=sum(r[metric]['denominator'] for r in rows);u=sum(r[metric]['uas_correct'] for r in rows);l=sum(r[metric]['las_correct'] for r in rows)
    valid=[r for r in rows if r[metric]['denominator']]
    return dict(sentences=len(rows),documents=len({r['doc_id'] for r in rows}),scored_words=n,uas_correct=u,las_correct=l,UAS=u/n if n else None,LAS=l/n if n else None,
                sentence_macro_UAS=sum(r[metric]['UAS'] for r in valid)/len(valid) if valid else None,sentence_macro_LAS=sum(r[metric]['LAS'] for r in valid)/len(valid) if valid else None,
                exact_sentences=sum(r[metric]['exact_scored_tree'] is True for r in valid),valid_sentences=len(valid))


def summarize(rows):
    out=[]
    for model in sorted({r['model'] for r in rows}):
        for split in sorted({r['split'] for r in rows}):
            group=[r for r in rows if r['model']==model and r['split']==split]
            docs=sorted({r['doc_id'] for r in group})
            for metric in ['primary','all_words']:
                a=aggregate(group,metric);a['document_macro_LAS']=sum(aggregate([r for r in group if r['doc_id']==d],metric)['LAS'] for d in docs)/len(docs) if docs else None
                out.append(dict(model=model,split=split,metric=metric,**a))
    return out


def error_slices(rows,labels):
    relations=defaultdict(Counter);documents=defaultdict(list);lengths=defaultdict(list);unseen=Counter()
    for row in rows:
        documents[row['doc_id']].append(row);n=len(row['reference']);lengths['2-5' if n<=5 else '6-8' if n<=8 else '9-12'].append(row)
        for g,p in zip(row['reference'],row['prediction']):
            if g['upos']=='PUNCT':continue
            r=relations[g['relation']];r['n']+=1;r['uas_correct']+=g['head']==p['head'];r['las_correct']+=g['head']==p['head'] and g['relation']==p['relation']
            if g['relation'] not in labels:unseen[g['relation']]+=1
    return dict(by_relation={k:dict(v) for k,v in sorted(relations.items())},by_document={d:aggregate(v) for d,v in sorted(documents.items())},by_length={d:aggregate(v) for d,v in sorted(lengths.items())},unseen_gold_relations=dict(unseen))


def oracle_bounds(features,gold,labels):
    out=[]
    for sent in features:
        reference=gold[sent['sample_id']];n=len(reference);denom=sum(r['upos']!='PUNCT' for r in reference);item=dict(sample_id=sent['sample_id'],doc_id=sent['doc_id'],denominator=denom,gold_projective=projective([r['head'] for r in reference]))
        for metric in ['UAS','LAS']:
            scores=[[NEG]*(n+1) for _ in range(n+1)]
            for d,g in enumerate(reference,1):
                for h in range(n+1):
                    if h!=d:scores[h][d]=float(g['upos']!='PUNCT' and h==g['head'] and (metric=='UAS' or g['relation'] in labels))
            heads,score=decode(scores);item[metric]=dict(max_correct=int(round(score)),ceiling=score/denom if denom else None,heads=heads)
        out.append(item)
    return out


def run(inputs,output,pre_run=False):
    started=time.perf_counter();inputs,output=Path(inputs),Path(output);output.mkdir(parents=True,exist_ok=True)
    config=json.loads((inputs/'protocol.json').read_text());reader=DataAccess(inputs);train=reader.features('train');train_targets=reader.targets('train')
    models={mode:CountModel(mode).fit(train,train_targets) for mode in config['models']}
    if pre_run:
        out=dict(mode='train-only pre-run',samples=[dict(model=mode,sample_id=train[0]['sample_id'],heads=[r['head'] for r in predict(m,config['alphas'][0],train[0])[0]]) for mode,m in models.items()],access_events=reader.events)
        save(output/'pre-run.json',out);return out
    dev=reader.features('dev');dev_gold=references(dev,reader.targets('dev'));decisions=[];validation=[];selected_rows=[]
    for mode,m in models.items():
        choices=[];runs=[]
        for alpha in config['alphas']:
            rows=evaluate(m,alpha,dev,dev_gold,'dev');validation.extend(rows);runs.append(rows);choices.append(dict(alpha=alpha,**aggregate(rows)))
        index=max(range(len(choices)),key=lambda i:choices[i]['las_correct']);chosen=choices[index]
        decisions.append(dict(model=mode,alpha=chosen['alpha'],choices=choices));selected_rows.extend(runs[index])
    reader.finish_selection(decisions);test=reader.features('test');test_gold=references(test,reader.targets('test'))
    for d in decisions:selected_rows.extend(evaluate(models[d['model']],d['alpha'],test,test_gold,'test'))
    bounds=oracle_bounds(test,test_gold,set(next(iter(models.values())).labels))
    slices={mode:error_slices([r for r in selected_rows if r['model']==mode and r['split']=='test'],set(m.labels)) for mode,m in models.items()}
    states={mode:m.state() for mode,m in models.items()};save(output/'models.json',states);write_rows(output/'validation-predictions.jsonl',validation);write_rows(output/'predictions.jsonl',selected_rows);save(output/'oracle-bounds.json',bounds)
    result=dict(decisions=decisions,summary=summarize(selected_rows),test_slices=slices,access_events=reader.events,
                test_gold_projective=sum(r['gold_projective'] for r in bounds),test_sentences=len(bounds),oracle_primary={metric:sum(r[metric]['max_correct'] for r in bounds)/sum(r['denominator'] for r in bounds) for metric in ['UAS','LAS']},
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),structure_source_sha256=hashlib.sha256(_STRUCTURE_PATH.read_bytes()).hexdigest(),input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs.glob('*.json'))},
                thread_limit_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']})
    save(output/'results.json',result);return dict(result,elapsed_seconds=time.perf_counter()-started)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--structure-source',type=Path);p.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parents[1]/'inputs');p.add_argument('--output',type=Path,required=True);p.add_argument('--pre-run',action='store_true');a=p.parse_args();set_structure(a.structure_source);r=run(a.inputs,a.output,a.pre_run)
    print(json.dumps(r if a.pre_run else dict(decisions=r['decisions'],summary=r['summary'],seconds=r['elapsed_seconds']),ensure_ascii=False))
