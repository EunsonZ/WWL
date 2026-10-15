#!/usr/bin/env python3
"""Producer self-check: original N7, Schur11 and (x,e) coordinates, never reviewer sign-off."""
import argparse,json
import sympy as sp
from run_experiment import load_card,verify,exact_pd,serial,VERTICES
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--certificate',type=Path,required=True);a=p.parse_args()
i,m=load_card(a.inputs);c=json.loads(a.certificate.read_text());K,G,C,F,N,P,eta,checks=verify(i,m,c)
T=sp.eye(2).row_join(sp.zeros(2,2)).col_join(sp.eye(2).row_join(-sp.eye(2)))
if T*T!=sp.eye(4):raise ValueError('coordinate transform not involutory')
Pe=T.T*P*T;Ge=T*G;Ce=C*T;reports=[]
for th in VERTICES:
 f=F(th);br=(f.T*P+P*f).row_join(P*G).row_join(C.T).col_join((G.T*P).row_join(-eta*sp.eye(3)).row_join(sp.zeros(3,4))).col_join(C.row_join(sp.zeros(4,3)).row_join(-sp.eye(4)))
 A=m['A0']+th[0]*m['A1']+th[1]*m['A2'];fe=(A+m['B2']*K).row_join(-m['B2']*K).col_join((A-m['A0']).row_join(m['A0']-m['L']*m['H']))
 if T*f*T!=fe:raise ValueError('(x,e) transformed F mismatch')
 ne=(fe.T*Pe+Pe*fe+Ce.T*Ce).row_join(Pe*Ge).col_join((Ge.T*Pe).row_join(-eta*sp.eye(3)))
 congr=sp.diag(T,sp.eye(3))
 if ne!=congr.T*N(th,P,eta)*congr:raise ValueError('N coordinate congruence failed')
 r={'theta':list(th),'N7':exact_pd(-N(th,P,eta)),'Schur11':exact_pd(-br),'error_coordinate_N7':exact_pd(-ne),'F':serial(f),'G':serial(G),'C':serial(C),'F_error_coordinates':serial(fe)}
 if not all(r[k]['positive_definite'] for k in ['N7','Schur11','error_coordinate_N7']):raise ValueError('Exact original/Schur/coordinate test failed')
 reports.append(r)
print(json.dumps({'accepted':True,'route':'producer original N7/Schur11/error-coordinate exact self-check','review_scope':'Producer self-check only; independent review must be performed by a non-author.','eta':str(eta),'gamma_numeric':c['gamma_numeric'],'nominal_observer_eigenvalues':[str(v) for v in (m['A0']-m['L']*m['H']).eigenvals()],'coordinate_T':serial(T),'vertices':reports},indent=2))
