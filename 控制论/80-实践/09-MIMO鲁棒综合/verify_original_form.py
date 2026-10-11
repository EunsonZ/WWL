#!/usr/bin/env python3
"""Second algebraic route: substitute exact K,P into the original dissipation form.
This author-side program self-check is not an independent reviewer sign-off.
"""
import json
from pathlib import Path
import sympy as s
R=Path(__file__).resolve().parent
i=json.loads((R/'inputs.json').read_text());c=json.loads((R/'certificate.json').read_text())
def mat(rows):return s.Matrix([[s.Rational(v) for v in row] for row in rows])
if i.get('theta_box')!=[[-1,1],[-1,1]] or i.get('dimensions')!={'x':2,'w':2,'u':2,'z':4}: raise ValueError('Unsupported box or dimensions')
shapes={'A0':(2,2),'A1':(2,2),'A2':(2,2),'B1':(2,2),'B2':(2,2),'Cz':(4,2),'Dzu':(4,2),'Dzw':(4,2)}
for key,shape in shapes.items():
    m=mat(i[key])
    if m.shape!=shape or any(v.is_finite is not True for v in m): raise ValueError(f'{key}: invalid shape or nonfinite entry')
if mat(i['Dzw'])!=s.zeros(4,2): raise ValueError('Nonzero Dzw is unsupported')
if c.get('schema')!='wwl-mimo-hinf-rational-v1': raise ValueError('Unknown certificate schema')
A0,A1,A2,B1,B2,C,D=[mat(i[k]) for k in ['A0','A1','A2','B1','B2','Cz','Dzu']]
X,Y,P,K=[mat(c[k]) for k in ['X','Y','P','K']];eta=s.Rational(c['eta'])
if any(m.shape!=(2,2) for m in [X,Y,P,K]) or any(v.is_finite is not True for m in [X,Y,P,K] for v in m) or eta.is_finite is not True or eta<=0: raise ValueError('Invalid certificate shape/entries/eta')
if P!=P.T or P[0,0]<=0 or P.det()<=0: raise ValueError('P must be symmetric positive definite')
if P*X!=s.eye(2) or K*X!=Y: raise ValueError('Stored P/K does not match X/Y')

def Q(theta,k,bound):
    acl=A0+theta[0]*A1+theta[1]*A2+B2*k;h=C+D*k
    tl=acl.T*P+P*acl+h.T*h
    return tl.row_join(P*B1).col_join((B1.T*P).row_join(-bound*s.eye(2)))
def check(q):
    if q!=q.T: raise ValueError('Dissipation matrix must be symmetric')
    d=[(-q)[:j,:j].det(method='domain-ge') for j in range(1,q.rows+1)]
    return {'negative_definite':all(v>0 for v in d),'negative_Q_leading_minors':[str(v) for v in d]}
vs=[(-1,-1),(-1,1),(1,-1),(1,1)]
results=[{'theta':list(t),**check(Q(t,K,eta))} for t in vs]
if not all(r['negative_definite'] for r in results): raise ValueError('Original-form certificate failed')
# Trial tighter bound using the SAME gain and P; diagnostic only.
# It fails on the default card but may be feasible after legitimate plant changes.
broken=[{'theta':list(t),**check(Q(t,K,s.Rational(1,100)))} for t in vs]
report={'route':'Original 4x4 dissipation matrix; exact rational Schur-complement route separate from 8x8 synthesis matrix','P_X_identity':True,'K_X_equals_Y':True,'vertices':results,'trial_eta':'1/100','trial_bound_checks':broken,'trial_bound_scope':'Diagnostic only: eta=1/100 fails on the default card, but its outcome never determines original certificate acceptance','review_scope':'program self-check, not independent reviewer sign-off'}
(R/'original_form_check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'all_original_form_vertices_negative_definite':True,'trial_eta_rejected_at_all_vertices':not any(r['negative_definite'] for r in broken)},indent=2))
