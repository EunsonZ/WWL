"""Executor-owned exact small-matrix/S3 expectations; no candidate dependency.
Determinants enumerate permutations, and Smith invariants are minor gcd ratios.
Empty dimensions always remain explicit. Large-matrix performance not claimed.
"""
from fractions import Fraction as F
from itertools import permutations,combinations,product
from math import gcd
from functools import reduce

def sign(p):return -1 if sum(p[i]>p[j] for i in range(len(p)) for j in range(i+1,len(p)))%2 else 1

def determinant(a):
 n=len(a);assert all(len(r)==n for r in a)
 return sum(sign(p)*reduce(lambda x,y:x*y,(a[i][p[i]] for i in range(n)),1) for p in permutations(range(n)))

def minor_gcd(rows,m,n,k):
 assert len(rows)==m and all(len(r)==n for r in rows)
 vals=[determinant([[rows[i][j] for j in cc] for i in rr]) for rr in combinations(range(m),k) for cc in combinations(range(n),k)]
 return reduce(gcd,vals,0),vals

def determinantal_expected(rows,m,n):
 deltas=[1];minors=[]
 for k in range(1,min(m,n)+1):
  d,values=minor_gcd(rows,m,n,k);deltas.append(d);minors.append({'k':k,'determinants':values,'gcd':d})
 rank=max((i for i,d in enumerate(deltas) if d),default=0)
 invariants=[deltas[k]//deltas[k-1] for k in range(1,rank+1)]
 return {'shape':[m,n],'rank':rank,'invariants':invariants,'minor_data':minors,'free_coker_rank':m-rank}

def matmul(a,b,m,k,n):
 assert len(a)==m and all(len(r)==k for r in a) and len(b)==k and all(len(r)==n for r in b)
 return [[sum(a[i][t]*b[t][j] for t in range(k)) for j in range(n)] for i in range(m)]

def inverse_exact(a):
 n=len(a);d=determinant(a);assert d
 return [[F(((-1)**(i+j))*determinant([[a[r][c] for c in range(n) if c!=i] for r in range(n) if r!=j]),d) for j in range(n)] for i in range(n)]

def vector_product(a,v):return [sum(x*y for x,y in zip(row,v)) for row in a]

def fullcolumn_lattice_member(b,n,p,v):
 """Independent original-B membership via nonsingular p-row minor and adjugate.
 This helper intentionally only claims fullcolumnrank (or p=0) small fixtures.
 """
 if p==0:return all(x==0 for x in v),[]
 for rr in combinations(range(n),p):
  square=[[b[i][j] for j in range(p)] for i in rr]
  if determinant(square):
   coefficients=vector_product(inverse_exact(square),[v[i] for i in rr])
   exact=vector_product(b,coefficients)==v
   return exact and all(x.denominator==1 for x in coefficients),[str(x) for x in coefficients]
 raise ValueError('oracle full-column-rank fixture required')

def permutation_matrix(g):return [[int(g[j]==i) for j in range(len(g))] for i in range(len(g))]
def compose(g,h):return tuple(g[h[i]] for i in range(len(g)))
def s3_expected():
 group=list(permutations(range(3)));basis=[[1,0],[0,1],[-1,-1]];rho={}
 for g in group:
  columns=matmul(permutation_matrix(g),basis,3,3,2);assert all(sum(columns[i][j] for i in range(3))==0 for j in range(2));rho[g]=columns[:2]
 product_witnesses=[]
 for g,h in product(group,repeat=2):
  assert matmul(rho[g],rho[h],2,2,2)==rho[compose(g,h)];product_witnesses.append({'g':g,'h':h,'product':compose(g,h)})
 chars={'trivial':[1]*6,'sign':[sign(g) for g in group],'standard':[sum(g[i]==i for i in range(3))-1 for g in group]}
 gram={a:{b:str(sum(F(x*y,6) for x,y in zip(ca,cb))) for b,cb in chars.items()} for a,ca in chars.items()}
 assert all(gram[a][b]==str(int(a==b)) for a in chars for b in chars)
 regular=[6 if g==tuple(range(3)) else 0 for g in group];multiplicities={name:sum(F(x*y,6) for x,y in zip(regular,char)) for name,char in chars.items()};assert multiplicities=={'trivial':F(1),'sign':F(1),'standard':F(2)}
 return {'permutations':group,'standard_matrices':[{'g':g,'matrix':rho[g]} for g in group],'multiplication_cases':product_witnesses,'characters':chars,'gram_exact':gram,'regular_character':regular,'regular_multiplicities':{k:int(v) for k,v in multiplicities.items()},'dimensions':[1,1,2],'dimension_squared_sum':6,'regular_decomposition_dimension':1+1+2*2}

MATRIX_INPUTS=[
 {'name':'diag6_10','shape':[2,2],'rows':[[6,0],[0,10]]},
 {'name':'signed_rectangular','shape':[2,3],'rows':[[0,-6,9],[15,0,3]]},
 {'name':'rank1','shape':[2,3],'rows':[[2,4,6],[4,8,12]]},
 {'name':'coordinate_example','shape':[2,2],'rows':[[4,6],[2,6]]},
 {'name':'zero_0x3','shape':[0,3],'rows':[]},
 {'name':'zero_3x0','shape':[3,0],'rows':[[],[],[]]},
 {'name':'allzero_2x3','shape':[2,3],'rows':[[0,0,0],[0,0,0]]},
]
HOMOLOGY_INPUTS=[
 {'name':'Z2_plus_Z','A':{'shape':[1,3],'rows':[[2,3,0]]},'B':{'shape':[3,1],'rows':[[-6],[4],[0]]},'independent_K':[[-3,0],[2,0],[0,1]],'independent_C':[[2],[0]]},
 {'name':'Z2_plus_Z6','A':{'shape':[1,3],'rows':[[1,1,0]]},'B':{'shape':[3,2],'rows':[[4,6],[-4,-6],[2,6]]},'independent_K':[[1,0],[-1,0],[0,1]],'independent_C':[[4,6],[2,6]]},
 {'name':'fullcolumn_A_zero_kernel','A':{'shape':[2,2],'rows':[[2,0],[0,3]]},'B':{'shape':[2,2],'rows':[[0,0],[0,0]]},'independent_K':[[],[]],'independent_C':[]},
 {'name':'zero_A_0x3','A':{'shape':[0,3],'rows':[]},'B':{'shape':[3,1],'rows':[[2],[0],[0]]},'independent_K':[[1,0,0],[0,1,0],[0,0,1]],'independent_C':[[2],[0],[0]]},
 {'name':'B_empty','A':{'shape':[1,3],'rows':[[2,3,0]]},'B':{'shape':[3,0],'rows':[[],[],[]]},'independent_K':[[-3,0],[2,0],[0,1]],'independent_C':[[],[]]},
]

def fixed_expectations():
 matrices=[{'input':item,'expected':determinantal_expected(item['rows'],*item['shape'])} for item in MATRIX_INPUTS];homology=[]
 for item in HOMOLOGY_INPUTS:
  m,n=item['A']['shape'];bn,p=item['B']['shape'];assert bn==n;assert matmul(item['A']['rows'],item['B']['rows'],m,n,p)==[[0]*p for _ in range(m)]
  K,C=item['independent_K'],item['independent_C'];q=len(K[0]) if K else 0;assert matmul(K,C,n,q,p)==item['B']['rows'];expected=determinantal_expected(C,q,p)
  homology.append({'input':item,'expected_C_smith':expected,'torsion_orders':[d for d in expected['invariants'] if d>1],'free_rank':q-expected['rank']})
 return {'matrix_cases':matrices,'homology_cases':homology,'S3_finite_expected':s3_expected(),'invalid_chain':{'A':{'shape':[1,2],'rows':[[1,0]]},'B':{'shape':[2,1],'rows':[[1],[0]]},'AB':[[1]],'expected':'reject'}}
