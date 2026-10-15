"""Read-only independent finite arithmetic supplement; no candidate imports."""
import json,ast
from pathlib import Path
from fractions import Fraction as F
from itertools import product
from oracle_core import s3_expected,matmul
r=Path(__file__).resolve().parent;s3=s3_expected();c=s3['characters'];perm=[1+x for x in c['standard']];tensor=[x*x for x in c['standard']]
def inner(a,b):return sum(F(x*y,6) for x,y in zip(a,b))
multiplicities={name:[int(inner(chi,c[k])) for k in ['trivial','sign','standard']] for name,chi in [('permutation',perm),('standard_tensor_square',tensor)]}
raw=json.loads((r/'logs/fixed-cli.stdout').read_text())['representation'];assert raw['permutation_multiplicities']==multiplicities['permutation'];assert raw['tensor_multiplicities']==multiplicities['standard_tensor_square']
tree=ast.parse((r/'snapshot/数学/25-高等代数/50-模与有限群表示/code/examples.py').read_text());j=None
for node in ast.walk(tree):
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='j' for t in node.targets):j=ast.literal_eval(node.value.args[0])
assert j==[[1,1],[0,1]]
power=matmul(matmul(j,j,2,2,2),j,2,2,2);assert [[x%3 for x in row] for row in power]==[[1,0],[0,1]]
lines=[(1,0),(0,1),(1,1),(1,2)];witness=[]
for v in lines:
 w=[sum(j[i][k]*v[k] for k in range(2))%3 for i in range(2)];lambdas=[a for a in range(3) if w==[(a*x)%3 for x in v]];witness.append({'line_generator':v,'Jv':w,'invariant_scalars':lambdas})
assert [w['line_generator'] for w in witness if w['invariant_scalars']]==[(1,0)]
print(json.dumps({'status':'PASS','independent_characters_over_six_elements':c,'permutation_character':perm,'tensor_character':tensor,'multiplicities':multiplicities,'regular_character':s3['regular_character'],'regular_multiplicities':s3['regular_multiplicities'],'regular_dimension':s3['regular_decomposition_dimension'],'regular_scope':'supplemental independent finite arithmetic; source CLI has no separate regular-representation matrix API','F3_actual_source_J':j,'F3_J_cubed':[[x%3 for x in row] for row in power],'F3_all_projective_lines':witness,'F3_no_invariant_complement_to_span_e1':True,'scope':'No general-theorem certification.'},indent=2))
