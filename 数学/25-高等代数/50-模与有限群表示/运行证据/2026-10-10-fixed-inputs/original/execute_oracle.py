"""Frozen API adapter plus independent exact verifier. Candidate expected/run unused."""
import sys,json,itertools,random
from pathlib import Path
from oracle_core import *
from verify_protocol import verify_smith,verify_homology
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'snapshot/数学/25-高等代数/50-模与有限群表示/code'))
import integer_smith as subject

def rows(m):return [list(r) for r in m.rows]
def normalized(s):return {'U':rows(s.U),'D':rows(s.D),'V':rows(s.V)}
def observe_matrix(item):
 m,n=item['shape'];b=subject.matrix(item['rows'],n);s=subject.smith(b);k,im=subject.kernel_image(b,s);observed=normalized(s);observed.update(kernel_basis=rows(k),image_basis=rows(im));check=verify_smith(item['rows'],m,n,observed)
 assert s.rank==check['minor_oracle']['rank'] and list(s.invariants)==check['minor_oracle']['invariants']
 return {'input':item,'actual':observed,'independent_check':check}
def observe_homology(item):
 a=subject.matrix(item['A']['rows'],item['A']['shape'][1]);b=subject.matrix(item['B']['rows'],item['B']['shape'][1]);h=subject.homology(a,b)
 obs={'K':rows(h['K']),'C':rows(h['C']),'smith_A':normalized(h['smith_A']),'smith_C':normalized(h['smith_C']),'representatives':rows(h['representatives'])}
 check=verify_homology(item,obs);assert list(h['torsion'])==check['torsion_orders'] and h['free_rank']==check['free_rank']
 return {'input':item,'actual':obs,'independent_check':check}

fixed=json.loads((root/'logs/fixed-cli.stdout').read_text());fixed_checks=[]
for record in fixed['integer_smith']:
 obs={k:record[k] for k in ['U','D','V','image_basis']};obs['kernel_basis']=record['K'];fixed_checks.append(verify_smith(record['B'],*record['shape'],obs))
fixed_h=[]
# Independently chosen K/C for author CLI's three chain fixtures.
for record,K,C in zip(fixed['homology'],[[[-1],[1]],[[-1,0],[1,0],[0,1]],[[],[]]],[[[-2]],[[-2],[0]],[]]):
 item={'name':record['name'],'A':record['A'],'B':record['B'],'independent_K':K,'independent_C':C}
 obs={k:record[k]['rows'] for k in ['K','C','representatives']};obs.update({k:{t:record[k][t]['rows'] for t in ['U','D','V']} for k in ['smith_A','smith_C']});fixed_h.append(verify_homology(item,obs))
checks=[observe_matrix(i) for i in MATRIX_INPUTS];homology=[observe_homology(i) for i in HOMOLOGY_INPUTS]
exhaustive=[]
for values in itertools.product(range(-2,3),repeat=4):
 item={'name':'exhaustive2x2','shape':[2,2],'rows':[list(values[:2]),list(values[2:])]};exhaustive.append(observe_matrix(item))
rng=random.Random(152);three=[]
for i in range(30):three.append(observe_matrix({'name':f'seed152_3x3_{i}','shape':[3,3],'rows':[[rng.randrange(-9,10) for _ in range(3)] for _ in range(3)]}))
rejections=[]
def reject(name,kind,fn):
 try:fn()
 except kind as e:rejections.append({'name':name,'error_type':type(e).__name__,'message':str(e)})
 else:raise AssertionError('required rejection absent: '+name)
reject('AB_nonzero',ValueError,lambda:subject.homology(subject.matrix([[1,0]]),subject.matrix([[1],[0]])))
reject('chain_shape',ValueError,lambda:subject.homology(subject.matrix([[1,0]]),subject.matrix([[0]])))
for cols in [False,0.0,'',-1]:reject('invalid_ncols_'+repr(cols),ValueError,lambda cols=cols:subject.matrix([],cols))
for entry in [False,1.0]:reject('invalid_entry_'+repr(entry),TypeError,lambda entry=entry:subject.matrix([[entry]]))
reject('ragged',ValueError,lambda:subject.matrix([[1],[1,2]]))
reject('dimension9',ValueError,lambda:subject.smith(subject.matrix([[1]*9])))
reject('entry_over_1million',ValueError,lambda:subject.smith(subject.matrix([[1000001]])))
for arg in [False,0,1.0]:
 reject('invalid_maxops_'+repr(arg),ValueError,lambda arg=arg:subject.smith(subject.matrix([[1]]),max_ops=arg))
 reject('invalid_maxbits_'+repr(arg),ValueError,lambda arg=arg:subject.smith(subject.matrix([[1]]),max_bits=arg))
reject('operation_limit',RuntimeError,lambda:subject.smith(subject.matrix([[4,6],[2,6]]),max_ops=1))
reject('bit_limit',RuntimeError,lambda:subject.smith(subject.matrix([[4,6],[2,6]]),max_bits=1))

# Independently inspect actual definitions in frozen examples via AST literals;
# do not import/call examples helpers or expected/run as oracle.
import ast
source=(root/'snapshot/数学/25-高等代数/50-模与有限群表示/code/examples.py').read_text();tree=ast.parse(source)
def assigned(name):
 for node in ast.walk(tree):
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
   val=node.value
   if isinstance(val,ast.Call) and isinstance(val.func,ast.Name) and val.func.id=='matrix':val=val.args[0]
   return ast.literal_eval(val)
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Tuple) and isinstance(node.value,ast.Tuple):
   for target,val in zip(node.targets[0].elts,node.value.elts):
    if isinstance(target,ast.Name) and target.id==name:
     if isinstance(val,ast.Call) and isinstance(val.func,ast.Name) and val.func.id=='matrix':val=val.args[0]
     return ast.literal_eval(val)
 raise ValueError(name)
R,S,t,block_r,block_s=[assigned(k) for k in ['R','S','t','block_r','block_s']]
assert R==[[-1,-1],[1,0]] and S==[[0,1],[1,0]]
assert matmul(permutation_matrix((1,2,0)),t,3,3,3)==matmul(t,block_r,3,3,3)
assert matmul(permutation_matrix((1,0,2)),t,3,3,3)==matmul(t,block_s,3,3,3)
assert determinant(t)==3
s3=s3_expected();assert fixed['representation']['S3_character_gram']==[[1,0,0],[0,1,0],[0,0,1]]
assert fixed['representation']['permutation_multiplicities']==[1,0,1]
assert fixed['representation']['tensor_multiplicities']==[1,1,1]
# Q(omega) multiplication comes from independent polynomial convolution/reduction.
def polyomega(z,w):
 terms=[z[0]*w[0],z[0]*w[1]+z[1]*w[0],z[1]*w[1]]
 return (terms[0]-terms[2],terms[1]-terms[2])
roots,vectors=assigned('roots'),assigned('vectors');fourier=[]
for lam,vec in zip(roots,vectors):
 assert [tuple(v) for v in [vec[-1],vec[0],vec[1]]]==[polyomega(lam,x) for x in vec]
 fourier.append({'lambda':lam,'vector':vec,'shifted':[vec[-1],vec[0],vec[1]]})
print(json.dumps({'status':'PASS','fixed_cli_smith_checks':fixed_checks,'fixed_cli_homology_checks':fixed_h,'executor_matrix_cases':checks,'executor_homology_cases':homology,'exhaustive_2x2_count':len(exhaustive),'exhaustive_2x2':exhaustive,'seed152_3x3_count':len(three),'seed152_3x3':three,'actual_rejections':rejections,'S3_independent':s3,'source_generator_block_checks':{'R':R,'S':S,'t':t,'det_t':3},'fourier_exact':fourier,'scope':'Finite integer/representation execution checks do not certify general PID, Maschke, Schur or character theorems.'},indent=2))
