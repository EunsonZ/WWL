"""Independent arithmetic checks for normalized candidate observations.
No Smith reduction implementation and no imports from candidate.
"""
from oracle_core import *

def verify_smith(rows,m,n,s):
 U,V,D=s['U'],s['V'],s['D']
 assert abs(determinant(U))==abs(determinant(V))==1
 assert matmul(matmul(U,rows,m,m,n),V,m,n,n)==D
 expected=determinantal_expected(rows,m,n); ds=expected['invariants'];r=expected['rank']
 assert D==[[ds[i] if i==j and i<r else 0 for j in range(n)] for i in range(m)]
 assert all(d>0 for d in ds) and all(b%a==0 for a,b in zip(ds,ds[1:]))
 invU,invV=inverse_exact(U),inverse_exact(V)
 kernel=[[V[i][j] for j in range(r,n)] for i in range(n)]
 image=[[int(invU[i][j]*ds[j]) for j in range(r)] for i in range(m)]
 assert matmul(rows,kernel,m,n,n-r)==[[0]*(n-r) for _ in range(m)]
 assert all(v.denominator==1 for line in invU+invV for v in line)
 if 'kernel_basis' in s: assert s['kernel_basis']==kernel
 if 'image_basis' in s: assert s['image_basis']==image
 # Actual coordinates: every bounded original x converts integrally and Bx is in image.
 traces=[]
 for x in product(range(-1,2),repeat=n):
  y=vector_product(invV,x);b=vector_product(rows,x);z=vector_product(U,b)
  assert all(t.denominator==1 for t in y)
  assert z==[ds[i]*y[i] if i<r else 0 for i in range(m)]
  assert all(z[i]%ds[i]==0 for i in range(r)) and all(t==0 for t in z[r:])
  traces.append({'x':x,'smith_domain_coordinate':[int(t) for t in y],'Bx':b,'U_Bx':z})
 return {'shape':[m,n],'minor_oracle':expected,'detU':determinant(U),'detV':determinant(V),'kernel_basis':kernel,'image_basis':image,'coordinate_traces':traces}

def verify_homology(item,s):
 A,B=item['A']['rows'],item['B']['rows'];m,n=item['A']['shape'];_,p=item['B']['shape']
 ra=verify_smith(A,m,n,s['smith_A']);r=ra['minor_oracle']['rank'];q=n-r
 K,C=s['K'],s['C'];Va=s['smith_A']['V'];invVa=inverse_exact(Va)
 assert K==[[Va[i][j] for j in range(r,n)] for i in range(n)]
 assert matmul(A,K,m,n,q)==[[0]*q for _ in range(m)]
 vb=matmul(invVa,B,n,n,p);assert vb[:r]==[[0]*p for _ in range(r)] and C==vb[r:]
 assert matmul(K,C,n,q,p)==B
 rc=verify_smith(C,q,p,s['smith_C']);ds=rc['minor_oracle']['invariants'];rankc=len(ds)
 ownK,ownC=item['independent_K'],item['independent_C']; own=determinantal_expected(ownC,q,p)
 assert ds==own['invariants']
 Uc=s['smith_C']['U'];invUc=inverse_exact(Uc)
 reps=matmul(K,invUc,n,q,q)
 assert all(x.denominator==1 for line in reps for x in line)
 reps=[[int(x) for x in line] for line in reps]
 if 'representatives' in s: assert s['representatives']==reps
 witness=[]
 for i in range(q):
  rep=[reps[j][i] for j in range(n)]; assert vector_product(A,rep)==[0]*m
  order=ds[i] if i<rankc else None
  trials=[]
  if p and own['rank']==p:
   for k in range(1,(order+1) if order else 5):
    belongs,coefs=fullcolumn_lattice_member(B,n,p,[k*v for v in rep]);assert belongs==(order is not None and k%order==0)
    trials.append({'multiple':k,'in_original_image':belongs,'original_B_coefficients':coefs})
  elif p==0:
   belongs,_=fullcolumn_lattice_member(B,n,p,rep);assert not belongs
   trials.append({'multiple':1,'in_original_image':belongs})
  witness.append({'column':i,'original_chain_representative':rep,'order':order,'membership_trials':trials})
 return {'name':item['name'],'smith_A':ra,'smith_C':rc,'K':K,'C':C,'torsion_orders':[d for d in ds if d>1],'free_rank':q-rankc,'representative_witnesses':witness}
