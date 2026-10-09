"""Own-snapshot adapter and independent minor/adjugate/ordered-AW oracle."""
from pathlib import Path
import sys,json,itertools,subprocess,hashlib
from oracle_core import matmul,determinantal_expected,inverse_exact,vector_product,fullcolumn_lattice_member
from verify_protocol import verify_smith,verify_homology
r=Path(__file__).resolve().parent
sys.path.insert(0,str(r/'snapshot/数学/36-拓扑学/20-同调与上同调'));sys.path.insert(0,str(r/'dependency152'))
import homology_lab as lab
import integer_smith as smith
expected=json.loads((r/'expected-before-output.json').read_text());raw=json.loads((r/'fixed-output/report.json').read_text())
def trans(a,m,n):return [[a[i][j] for i in range(m)] for j in range(n)]
def rows(x):return [list(v) for v in x.rows]
def norm(s):return {k:rows(getattr(s,k)) for k in ['U','D','V']}
def calculate_homology(A,m,n,B,p):
 h=smith.homology(smith.matrix(A,n),smith.matrix(B,p));sa=norm(h['smith_A']);sc=norm(h['smith_C']);va=verify_smith(A,m,n,sa);q=n-va['minor_oracle']['rank'];K,C=rows(h['K']),rows(h['C'])
 assert h['K'].shape==(n,q) and h['C'].shape==(q,p)
 assert K==[[sa['V'][i][j] for j in range(n-q,n)] for i in range(n)]
 vb=matmul(inverse_exact(sa['V']),B,n,n,p);assert vb[:n-q]==[[0]*p for _ in range(n-q)] and vb[n-q:]==C
 assert matmul(K,C,n,q,p)==B
 vc=verify_smith(C,q,p,sc);ds=vc['minor_oracle']['invariants'];group={'torsion':[d for d in ds if d>1],'free':q-len(ds)}
 assert list(h['torsion'])==group['torsion'] and h['free_rank']==group['free']
 reps=matmul(K,inverse_exact(sc['U']),n,q,q);assert reps==rows(h['representatives'])
 return {'group':group,'K':K,'C':C,'smith_A':sa,'smith_C':sc,'representatives':rows(h['representatives']),'independent_A_minors':va['minor_oracle'],'independent_C_minors':vc['minor_oracle']}
results=[]
for e,actual in zip(expected['models'],raw['models']):
 n0,n1,n2=e['dimensions'];a,b=e['d1'],e['d2'];assert actual['name']==e['name'] and actual['dimensions']==e['dimensions'] and actual['d1']==a and actual['d2']==b
 sq=matmul(a,b,n0,n1,n2);assert sq==[[0]*n2 for _ in range(n0)]==actual['d1_d2']
 da,db=trans(a,n0,n1),trans(b,n1,n2);dsq=matmul(db,da,n2,n1,n0);assert dsq==[[0]*n0 for _ in range(n2)]
 r1=determinantal_expected(a,n0,n1)['rank'];r2=determinantal_expected(b,n1,n2)['rank'];betti=[n0-r1,n1-r1-r2,n2-r2];assert actual['betti_Q']==betti
 chi=n0-n1+n2;assert actual['chi']==chi==betti[0]-betti[1]+betti[2]
 H=[calculate_homology([],0,n0,a,n1),calculate_homology(a,n0,n1,b,n2),calculate_homology(b,n1,n2,[[] for _ in range(n2)],0)]
 HC=[calculate_homology(da,n1,n0,[[] for _ in range(n0)],0),calculate_homology(db,n2,n1,da,n0),calculate_homology([],0,n2,db,n1)]
 assert [x['group'] for x in H]==e['H_Z'];assert [x['group'] for x in HC]==e['Hco_Z']
 results.append({'name':e['name'],'boundary_square':sq,'coboundary_square':dsq,'betti_Q':betti,'chi':chi,'H_Z':H,'Hco_Z':HC})
j=expected['smith_joint'];h=smith.homology(smith.matrix(j['A']),smith.matrix(j['B']));observed={'K':rows(h['K']),'C':rows(h['C']),'smith_A':norm(h['smith_A']),'smith_C':norm(h['smith_C']),'representatives':rows(h['representatives'])};joint=verify_homology({'name':'Z3_joint','A':{'shape':[1,2],'rows':j['A']},'B':{'shape':[2,1],'rows':j['B']},'independent_K':j['independent_K'],'independent_C':j['independent_C']},observed);assert joint['torsion_orders']==[3] and joint['free_rank']==0
cup=[]
# AW uses front and back ordered edges separately for t1 and t2, evaluated on t1-t2.
for a,b,c,d in itertools.product(range(-2,3),repeat=4):
 x=(a,b,a+b);y=(c,d,c+d);t1=a*d;t2=b*c;want=t1-t2;actual=lab.cup_on_fundamental(x,y);assert actual==want;assert lab.cup_on_fundamental(x,y,-1)==-want
 cup.append({'x':x,'y':y,'t1_front_back':t1,'t2_front_back':t2,'on_t1_minus_t2':want,'actual':actual})
assert raw['torus_cup']==expected['cup_basis']
W=[]
for a,b,c,d in itertools.product(range(-2,3),repeat=4):W.append({'left':[a,b],'right':[c,d],'fixed_zero_tensor_pairing':0})
assert raw['RP2_F2_betti']==expected['RP2_F2_betti'] and raw['RP2_F2_d2']==[[0]]
relations=[]
for v in raw['one_relation_integer']:
 m=v['degree'];assert v['U'][0][0]*m*v['V'][0][0]==abs(m)==v['D'][0][0];assert abs(v['U'][0][0])==abs(v['V'][0][0])==1
 assert v['H1_torsion_factors']==([abs(m)] if abs(m)>1 else []) and v['H1_free_rank']==int(m==0) and v['H2_free_rank']==int(m==0);relations.append(v)
rejections=[]
def reject(name,kind,fn):
 try:fn()
 except kind as e:rejections.append({'name':name,'type':type(e).__name__,'message':str(e)})
 else:raise AssertionError(name)
reject('chain_square_nonzero',ValueError,lambda:lab.finite_chain('bad',[2,1,1],[[-1],[1]],[[1]]))
reject('empty_declared_shape_bad',ValueError,lambda:lab.finite_chain('bad',[0,2,0],[],[[]]))
reject('smith_AB_nonzero',ValueError,lambda:smith.homology(smith.matrix([[1,0]]),smith.matrix([[1],[0]])))
reject('smith_chain_shape_bad',ValueError,lambda:smith.homology(smith.matrix([],3),smith.matrix([[],[]],0)))
reject('cup_not_cocycle',ValueError,lambda:lab.cup_on_fundamental((1,0,0),(0,1,1)))
reject('cup_float',TypeError,lambda:lab.cup_on_fundamental((1.,0,1),(0,1,1)))
reject('cup_orientation0',ValueError,lambda:lab.cup_on_fundamental((1,0,1),(0,1,1),0))
empty=lab.finite_chain('empty',[0,0,0],[],[]);assert empty['betti_Q']==[0,0,0]
# Check output no-overwrite behavior; capture complete expected failing CLI output separately.
source=r/'snapshot/数学/36-拓扑学/20-同调与上同调/homology_lab.py';before=(r/'fixed-output/report.json').read_bytes();proc=subprocess.run([sys.executable,'-B',str(source),'--output-dir',str(r/'fixed-output')],capture_output=True);(r/'logs/reused-output.stdout').write_bytes(proc.stdout);(r/'logs/reused-output.stderr').write_bytes(proc.stderr);assert proc.returncode!=0 and (r/'fixed-output/report.json').read_bytes()==before
circle=raw['circle_cover'];assert circle['endpoint']==3 and circle['closed'] is False
torus=raw['torus_cover'];assert torus['endpoint']==[0,1] and torus['closed'] is False
print(json.dumps({'status':'PASS','models':results,'smith152_joint_actual':observed,'smith152_joint_independent_check':joint,'AW_cases':cup,'AW_count':len(cup),'W_fixed_zero_tensor_cases':W,'W_scope':expected['W_scope'],'one_relation_actual':relations,'RP2_Z_vs_F2':'Integral H1=Z/2, integral H^2=Z/2; F2 Betti=[1,1,1]. These are different coefficient/degree objects.','rejections':rejections,'empty_finite_chain':empty,'no_overwrite':{'exit_code':proc.returncode,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256((r/'fixed-output/report.json').read_bytes()).hexdigest()},'cover_endpoints':{'circle':circle,'torus':torus},'scope':'Finite specified models only, no general theorem proof.'},indent=2))
