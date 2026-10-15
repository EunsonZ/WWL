"""Independent finite fixtures and expectations; no subject import."""
import json
from pathlib import Path
edges=[(0,1),(1,2),(0,2)]
d1=[[int(v==b)-int(v==a) for a,b in edges] for v in range(3)]
face={edges[0]:1,edges[1]:1,edges[2]:-1};d2=[[face[e]] for e in edges]
models=[('triangle_boundary',[3,3,0],d1,[[],[],[]],[([ ],1),([],1),([],0)],[([],1),([],1),([],0)]),('triangle_filled',[3,3,1],d1,d2,[([],1),([],0),([],0)],[([],1),([],0),([],0)]),('S1',[1,1,0],[[0]],[[]],[([],1),([],1),([],0)],[([],1),([],1),([],0)]),('T2_minimal',[1,2,1],[[0,0]],[[0],[0]],[([],1),([],2),([],1)],[([],1),([],2),([],1)]),('RP2',[1,1,1],[[0]],[[2]],[([],1),([2],0),([],0)],[([],1),([],0),([2],0)]),('wedge_S1_S1_S2',[1,2,1],[[0,0]],[[0],[0]],[([],1),([],2),([],1)],[([],1),([],2),([],1)]),('T2_two_triangles',[1,3,2],[[0,0,0]],[[1,1],[1,1],[-1,-1]],[([],1),([],2),([],1)],[([],1),([],2),([],1)])]
expected={'models':[{'name':n,'dimensions':dims,'d1':a,'d2':b,'H_Z':[{'torsion':t,'free':f} for t,f in h],'Hco_Z':[{'torsion':t,'free':f} for t,f in hc]} for n,dims,a,b,h,hc in models],'cup_basis':{'xy_on_z':1,'yx_on_z':-1,'xx_on_z':0,'yy_on_z':0,'reverse_orientation_xy':-1},'RP2_F2_betti':[1,1,1],'smith_joint':{'A':[[2,1]],'B':[[3],[-6]],'independent_K':[[1],[-2]],'independent_C':[[3]],'torsion':[3],'free':0},'W_degree1_product_tensor':[[0,0],[0,0]],'W_scope':'Supplementary fixed zero tensor uses lesson restriction H1->H1(S2)=0 and H2->H2(S2)=identity; cannot infer it from additive boundary matrices. No subject W cup API.'}
r=Path(__file__).resolve().parent
(r/'expected-before-output.json').write_text(json.dumps(expected,indent=2)+'\n')
print(json.dumps(expected,indent=2))
