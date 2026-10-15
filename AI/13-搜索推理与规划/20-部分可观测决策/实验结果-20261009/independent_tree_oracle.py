"""Flat terminal-path mass enumeration; imports neither candidate function."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json

def trees(h):
    leaves=['skip','protect']
    if h==1:return leaves
    lower=trees(h-1)
    return leaves+[['sense',a,b] for a,b in product(lower,repeat=2)]

def terminal_paths(tree, signals=()):
    if isinstance(tree,str):return [(signals,tree)]
    return terminal_paths(tree[1],signals+('+',))+terminal_paths(tree[2],signals+('-',))

checks=[]
for case in ('h3c1','h2c3','h2c6','h2c0K60','perfect','uninformative'):
    output=json.loads(Path(case+'.json').read_text());m=output['model']
    p=F(m['prior']['exact']);k=F(m['prevention']['exact']);c=F(m['sense_cost']['exact'])
    likelihood=[F(m['false_positive']['exact']),F(m['sensitivity']['exact'])]
    scores=[]
    for tree in trees(m['horizon']):
        total=F(0)
        for history,action in terminal_paths(tree):
            for y in (0,1):
                mass=p if y else 1-p
                for signal in history:mass*=likelihood[y] if signal=='+' else 1-likelihood[y]
                total+=mass*(len(history)*c+(100*y if action=='skip' else k))
        scores.append((total,tree))
    minimum=min(risk for risk,_ in scores)
    winners=[tree for risk,tree in scores if risk==minimum]
    assert F(output['oracle_risk']['exact'])==minimum
    assert output['optimal_trees']==winners
    assert output['policy_count']==len(scores)
    same=output['same_mean']
    assert F(same['delta0']['mean']['exact'])==F(same['symmetric']['mean']['exact'])==0
    assert F(same['delta0']['risky_reward']['exact'])==-F(1,2)
    assert F(same['symmetric']['risky_reward']['exact'])==F(1,2)
    assert same['delta0']['best_action']=='safe' and same['symmetric']['best_action']=='risky'
    checks.append({'case':case,'risk':str(minimum),'policy_count':len(scores),'winners':winners})
Path('independent_tree_expected.json').write_text(json.dumps(checks,indent=2)+'\n')
print('PASS: independent flat terminal-path joint-mass enumeration of six complete policy sets; original mean-zero counterexample')
