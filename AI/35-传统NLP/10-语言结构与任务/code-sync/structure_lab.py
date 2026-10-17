"""Tiny constituency-to-dependency contract and explicit aligned-word evaluation."""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
from itertools import product
import json
import math
from pathlib import Path

# Rule -> head child, non-head relation. This is a declared toy conversion,
# not a general converter to every UD construction or annotation tradition.
HEAD_RULES={('S','NP','VP'):(1,'nsubj'),('VP','V','NP'):(0,'obj'),
            ('VP','VP','PP'):(0,'obl'),('NP','NP','PP'):(0,'nmod'),
            ('PP','P','NP'):(1,'case')}


def load_parent(path=None):
    path=Path(path) if path else Path(__file__).resolve().parents[2]/'nlp_lab.py'
    spec=importlib.util.spec_from_file_location('published_nlp_lab',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,path


def validate(rows):
    """Basic rooted tree; empty record sequence accepted only as empty input."""
    n=len(rows)
    for i,row in enumerate(rows,1):
        if type(row.get('id')) is not int or row['id']!=i:raise ValueError('ordered IDs must be exactly1..n')
        if not all(isinstance(row.get(k),str) and row[k] for k in ['form','upos','relation']):raise ValueError('nonempty token fields required')
        h=row.get('head')
        if type(h) is not int or not 0<=h<=n or h==i:raise ValueError('head domain or self-loop')
        if (h==0)!=(row['relation']=='root'):raise ValueError('root label iff head0')
    if n and sum(r['head']==0 for r in rows)!=1:raise ValueError('exactly one root word required')
    for i in range(1,n+1):
        seen=set();j=i
        while j:
            if j in seen:raise ValueError('cycle or disconnected rootless component')
            seen.add(j);j=rows[j-1]['head']
    return rows


def to_dependency(tree,words,upos):
    """Head propagation in a supported binary tree; repeated words keep positions."""
    if len(words)!=len(upos) or not words:raise ValueError('nonempty aligned word/UPOS sequence required')
    rows=[];trace=[]
    def visit(node):
        if not isinstance(node,(tuple,list)) or len(node) not in (2,3):raise ValueError('unsupported node shape')
        if len(node)==2:
            category,word=node;i=len(rows)+1
            if category not in {'NP','V','P'} or i>len(words) or word!=words[i-1]:raise ValueError('leaf yield/category mismatch')
            rows.append(dict(id=i,form=word,upos=upos[i-1],head=None,relation=None));return i,(i,i+1)
        category,left,right=node
        if not isinstance(left,(tuple,list)) or not isinstance(right,(tuple,list)) or not left or not right:raise ValueError('malformed child')
        rule=(category,left[0],right[0])
        if rule not in HEAD_RULES:raise ValueError('head rule not supplied for this production')
        lh,ls=visit(left);rh,rs=visit(right);which,label=HEAD_RULES[rule]
        head,dependent=(lh,rh) if which==0 else (rh,lh)
        rows[dependent-1].update(head=head,relation=label)
        trace.append(dict(rule=list(rule),span=[ls[0],rs[1]],head=head,dependent=dependent,relation=label))
        return head,(ls[0],rs[1])
    root,_=visit(tree)
    if len(rows)!=len(words):raise ValueError('leaf yield length mismatch')
    rows[root-1].update(head=0,relation='root');validate(rows)
    return dict(tree=tree,rows=rows,trace=trace,root_word=root)


def aligned_scores(reference,prediction,include_punct=True,include_root_word=True):
    """UAS/LAS accuracy on a fixed reference-defined word set, not raw-text F1."""
    validate(reference);validate(prediction)
    if [(r['id'],r['form']) for r in reference]!=[(r['id'],r['form']) for r in prediction]:raise ValueError('word alignment differs: no zip-and-score')
    detail=[]
    for gold,pred in zip(reference,prediction):
        scored=(include_punct or gold['upos']!='PUNCT') and (include_root_word or gold['head']!=0)
        head_ok=gold['head']==pred['head'];label_ok=gold['relation']==pred['relation']
        detail.append(dict(id=gold['id'],form=gold['form'],gold=gold,prediction=pred,scored=scored,head_correct=head_ok,label_correct=label_ok,both_correct=head_ok and label_ok))
    n=sum(r['scored'] for r in detail);u=sum(r['scored'] and r['head_correct'] for r in detail);l=sum(r['scored'] and r['both_correct'] for r in detail)
    return dict(denominator=n,uas_correct=u,las_correct=l,UAS=u/n if n else None,LAS=l/n if n else None,
                exact_scored_tree=all(r['both_correct'] for r in detail if r['scored']) if n else None,detail=detail)


def supplied_score_example(config):
    n=config['nodes']
    if type(n) is not int or not 1<=n<=5:raise ValueError('finite enumerator supports1..5 nodes')
    table={}
    if not isinstance(config['other_score'],(int,float)) or not math.isfinite(config['other_score']):raise ValueError('finite scores required')
    for h,d,s in config['nonzero']:
        if type(h) is not int or type(d) is not int or not 0<=h<=n or not 1<=d<=n or h==d:raise ValueError('score arc outside allowed domain')
        if (h,d) in table or not isinstance(s,(int,float)) or not math.isfinite(s):raise ValueError('distinct arcs with finite scores required')
        table[h,d]=s
    def total(heads):return sum(table.get((h,d),config['other_score']) for d,h in enumerate(heads,1))
    choices=[[h for h in range(n+1) if h!=d] for d in range(1,n+1)]
    local=[max(pool,key=lambda h:table.get((h,d),config['other_score'])) for d,pool in enumerate(choices,1)]
    valid=[];invalid=[]
    for hs in product(*choices):
        rows=[dict(id=d,form=f'w{d}',upos='X',head=h,relation='root' if h==0 else 'dep') for d,h in enumerate(hs,1)]
        try:validate(rows)
        except ValueError as e:invalid.append(dict(heads=list(hs),reason=str(e)))
        else:valid.append(dict(heads=list(hs),score=total(hs)))
    best=max(r['score'] for r in valid)
    return dict(nodes=n,local_heads=local,local_score=total(local),all_combinations=len(valid)+len(invalid),
                valid_candidates=valid,invalid_candidates=invalid,best_legal_score=best,best_legal=[r for r in valid if r['score']==best])


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def run(inputs,output,parent_path=None):
    inputs,output=Path(inputs),Path(output);output.mkdir(parents=True,exist_ok=True)
    config=json.loads(inputs.read_text());parent,parent_file=load_parent(parent_path)
    conversions=[];transfer=[]
    for words,upos,lexical,dest in [(config['words'],config['upos'],parent.LEXICAL,conversions),
                                  (config['transfer']['words'],config['transfer']['upos'],parent.LEXICAL+[tuple(r) for r in config['transfer']['lexical_additions']],transfer)]:
        trees,_=parent.cky(words,lexical,parent.BINARY)
        for tree in trees:
            result=to_dependency(tree,words,upos)
            result['attachment']='NP' if any(t['relation']=='nmod' for t in result['trace']) else 'VP';dest.append(result)
    by_attachment={r['attachment']:r for r in conversions}
    if len(conversions)!=2 or set(by_attachment)!={'NP','VP'}:raise ValueError('expected both original CKY analyses')
    gold=by_attachment[config['reference_attachment']]['rows'];vp=by_attachment['VP']['rows']
    label_only=deepcopy(gold);label_only[-1]['relation']='obl'
    head_only=deepcopy(vp);head_only[-1]['relation']='nmod'
    gold_punct=deepcopy(gold);vp_punct=deepcopy(vp)
    punctuation=dict(id=len(gold)+1,**config['punctuation_extension'])
    for rows in [gold_punct,vp_punct]:rows.append(deepcopy(punctuation))
    metrics=[]
    for name,g,p in [('reference',gold,gold),('other_attachment',gold,vp),('label_only_error',gold,label_only),('head_only_error',gold,head_only),('with_correct_punctuation',gold_punct,vp_punct)]:
        for policy in config['policies']:
            metrics.append(dict(case=name,policy=policy['name'],**aligned_scores(g,p,policy['include_punct'],policy['include_root_word'])))
    alignment_failure=''
    split=deepcopy(vp);split[-1]['form']='scope';split.append(dict(id=6,form='s',upos='X',head=5,relation='dep'))
    try:aligned_scores(gold,split)
    except ValueError as e:alignment_failure=str(e)
    result=dict(provenance=config['provenance'],words=config['words'],conversions=conversions,transfer=transfer,
                metrics=metrics,alignment_failure=alignment_failure,supplied_scores=supplied_score_example(config['supplied_edge_scores']),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parent_source_sha256=hashlib.sha256(parent_file.read_bytes()).hexdigest(),input_sha256=hashlib.sha256(inputs.read_bytes()).hexdigest())
    save(output/'structure-results.json',result)
    with (output/'arc-comparisons.jsonl').open('w') as stream:
        for item in metrics:
            for row in item['detail']:stream.write(json.dumps(dict(case=item['case'],policy=item['policy'],**row),ensure_ascii=False,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--parent',type=Path)
    parser.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parents[1]/'inputs/structure.json');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();r=run(args.inputs,args.output,args.parent)
    print(json.dumps(dict(trees=len(r['conversions']),comparisons=len(r['metrics']),local_heads=r['supplied_scores']['local_heads'],best_legal=r['supplied_scores']['best_legal_score']),ensure_ascii=False))
