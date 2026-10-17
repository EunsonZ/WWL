#!/usr/bin/env python3
"""Fixed small GSP contract; NumPy only, no random data or inferred graph.

All voltages are V; weights, L, H, mu and alpha are dimensionless.
Finite checks verify these inputs, not the lesson's general theorems.
"""
import argparse
import itertools
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

MATRIX_TOL = 5e-12
VALUE_TOL = 2e-10
BOUND_TOL = 2e-9
RANK_TOL = 1e-10
RCOND = 1e-12
GD_TOL = 1e-10
C6_EDGES = [(j, (j + 1) % 6, 1.0) for j in range(6)]
OMEGA_E = [0, 2, 4]
OMEGA_C = [0, 1, 2]
NOISE = np.array([.01, -.02, .015, 0., .005, -.01])
X = np.array([3., 3., 2., 1., 1., 2.])
MU = .1
MU_GRID = [1e-4, 1e-3, .01, .1, 1., 10.]
ALPHA_GRID = [0., .01, .1, 1.]


def integer(value):
    return isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_))


def laplacian(n, edges):
    if not integer(n) or n < 1:
        raise ValueError('n must be a positive integer')
    out = np.zeros((n, n))
    seen = set()
    for i, j, w in edges:
        if not integer(i) or not integer(j) or not 0 <= i < n or not 0 <= j < n or i == j:
            raise ValueError('edge endpoints must be distinct valid integers')
        key = tuple(sorted((i, j)))
        if key in seen or not np.isfinite(w) or w < 0:
            raise ValueError('duplicate edge or invalid nonnegative weight')
        seen.add(key)
        out[i, i] += w
        out[j, j] += w
        out[i, j] -= w
        out[j, i] -= w
    return out


def sampling(n, omega):
    if not omega or any(not integer(i) or not 0 <= i < n for i in omega) or len(set(omega)) != len(omega):
        raise ValueError('samples must be nonempty, distinct valid integers')
    return np.eye(n)[omega]


def local_l(x, edges):
    out = np.zeros_like(x, dtype=float)
    for i, j, w in edges:
        flow = w * (x[i] - x[j])
        out[i] += flow
        out[j] -= flow
    return out


def local_h(x, edges):
    return x - local_l(x, edges) / 4


def local_forward(x, edges, omega):
    return local_h(x, edges)[omega]


def local_adjoint(y, n, edges, omega):
    z = np.zeros(n)
    z[omega] = y
    return local_h(z, edges)


def min_gain(b):
    if b.shape[0] < b.shape[1]:
        return 0.0
    return float(np.linalg.svd(b, compute_uv=False)[-1])


def band_solve(b, y):
    if min_gain(b) <= RANK_TOL:
        raise ValueError('band model not identifiable at the declared tolerance')
    return np.linalg.lstsq(b, y, rcond=RCOND)[0]


def smooth(a, l, y, mu):
    if not np.isfinite(mu) or mu <= 0 or y.shape != (a.shape[0],) or not np.all(np.isfinite(y)):
        raise ValueError('mu positive and finite; y finite with the declared shape')
    q = a.T @ a + mu * l
    ev = np.linalg.eigvalsh(q)
    if ev[0] <= RANK_TOL:
        raise ValueError('smooth optimum not unique at the declared tolerance')
    return np.linalg.solve(q, a.T @ y), q, ev


def close(actual, expected, tol=VALUE_TOL):
    error = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
    if error > tol:
        raise AssertionError(f'value error {error} > {tol}')
    return error


def bound(actual, upper):
    if actual > upper + BOUND_TOL:
        raise AssertionError(f'bound failed: {actual} > {upper}')


def svg_start(title, description, width=1200, height=600):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<title>{escape(title)}</title><desc>{escape(description)}</desc>',
            '<rect width="100%" height="100%" fill="#fbfcfe"/>',
            '<g font-family="Arial, sans-serif" fill="#18293d">']


def label(out, x, y, text, size=18, color='#18293d'):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(text)}</text>')


def poly(out, pts, color, dash=False, width=3):
    dash_attr = ' stroke-dasharray="7 5"' if dash else ''
    out.append(f'<polyline points="{" ".join(f"{x:.3f},{y:.3f}" for x,y in pts)}" fill="none" stroke="{color}" stroke-width="{width}"{dash_attr}/>')


def figures(outdir, data):
    d = data['band']
    out = svg_start('Same graph, different sampling stability', '同一六环、两个采样集与同输入电压恢复；所有曲线来自results.json。')
    label(out, 35, 38, 'Known graph + known prefilter + declared low band', 25)
    label(out, 35, 66, 'C6 | H = I - L/4 | lambda <= 1 | voltage in V', 17)
    for panel, omega, title in [(0, OMEGA_E, 'Even nodes: {0,2,4}'), (1, OMEGA_C, 'Cluster: {0,1,2}')]:
        cx = 170 + 565 * panel
        cy = 230
        pts = [(cx + 105 * math.cos(-math.pi/2 + j*math.pi/3), cy + 105 * math.sin(-math.pi/2 + j*math.pi/3)) for j in range(6)]
        for j in range(6):
            poly(out, [pts[j], pts[(j+1)%6]], '#a6b5c7', width=2)
        for j, (px, py) in enumerate(pts):
            fill = '#e98724' if j in omega else '#dce6ef'
            out.append(f'<circle cx="{px}" cy="{py}" r="18" fill="{fill}" stroke="#334c64"/>')
            label(out, px-5, py+6, str(j), 17)
        rec = d['even' if panel == 0 else 'cluster']
        label(out, cx+140, 150, title, 19)
        label(out, cx+140, 184, f"min gain = {rec['s_min']:.6f}", 17)
        label(out, cx+140, 216, f"noise norm = {rec['noise_norm']:.6f} V", 16)
        label(out, cx+140, 248, f"LS error = {rec['error']:.6f} V", 16)
        label(out, cx+140, 280, f"noise bound = {rec['noise_bound']:.6f} V", 16)
    x0, y0, scale_x, scale_y = 65, 525, 95, 45
    poly(out, [(x0, 345), (x0, y0), (x0+5*scale_x, y0)], '#8798aa', width=1)
    for j in range(6):
        label(out, x0+j*scale_x-4, y0+22, str(j), 14)
    label(out, 35, 364, 'V', 15)
    for v in [1,2,3]:
        label(out, 42, y0-scale_y*v+5, str(v), 14)
    for values, color, dashed in [(data['x'], '#124e78', False), (data['hx'], '#8b9eaf', True), (d['even']['x_hat'], '#e98724', False)]:
        poly(out, [(x0+j*scale_x, y0-scale_y*v) for j,v in enumerate(values)], color, dashed)
    label(out, 665, 387, 'Bottom: same x_B and same global noise vector', 17)
    label(out, 665, 419, 'Blue: truth | Gray: Hx_B | Orange: even-node LS', 16)
    label(out, 665, 458, 'One fixed noise vector is not a population MSE.', 17)
    label(out, 665, 490, 'Min gain certifies worst-case amplification.', 17)
    label(out, 65, 579, 'Node index (not time); orange graph nodes are measured.', 16)
    out.append('</g></svg>')
    (outdir/'figures'/'graph_recovery.svg').write_text('\n'.join(out)+'\n')
    out = svg_start('Optimization certificate versus signal error', 'GD残差证书核同一二次目标；唯一最小点并非真信号可辨。')
    label(out, 35, 38, 'Separate optimization error from signal error', 25)
    label(out, 35, 70, 'Same even-node observations | mu = 0.1 | step = 1 / q_max', 17)
    hist = data['smooth']['gd']['history']
    xmax = hist[-1]['iteration']
    def pos(k, value):
        return (70+600*k/max(1,xmax), 475-27*(math.log10(max(value,1e-12))+12))
    poly(out, [(70, 108), (70, 475), (670, 475)], '#8798aa', width=1)
    for exponent in [-12, -9, -6, -3, 0]:
        yy = 475-27*(exponent+12)
        label(out, 18, yy+5, f'1e{exponent}', 13)
    poly(out, [pos(r['iteration'], r['certificate']) for r in hist], '#e98724')
    poly(out, [pos(r['iteration'], r['optimum_error']) for r in hist], '#124e78', True)
    label(out, 70, 510, f'Iteration 0 to {xmax} | vertical: norm in V (log10)', 16)
    label(out, 70, 548, 'Orange: ||Qx-b||/q_min | Blue: error to direct optimum', 16)
    z = data['failures']['zero_data']
    label(out, 735, 140, 'A different fixed zero-data case:', 20)
    label(out, 735, 181, 'C6, samples {0,3}, truth = u_s', 18)
    label(out, 735, 221, f"sample residual = {z['residual']:.1f} V", 18)
    label(out, 735, 261, f"unique smooth output error = {z['error']:.1f} V", 18)
    label(out, 735, 316, 'Optimizer unique: YES', 20, '#124e78')
    label(out, 735, 354, 'Truth identifiable: NO', 20, '#b94e30')
    label(out, 735, 415, 'A stopped optimizer does not measure', 18)
    label(out, 735, 445, 'the missing direction.', 18)
    out.append('</g></svg>')
    (outdir/'figures'/'error_budget.svg').write_text('\n'.join(out)+'\n')


def run():
    l = laplacian(6, C6_EDGES)
    h = np.eye(6)-l/4
    u = np.column_stack((np.ones(6)/math.sqrt(6),
        np.array([1,.5,-.5,-1,-.5,.5])/math.sqrt(3),
        np.array([0,.5,.5,0,-.5,-.5]),
        np.array([1,-.5,-.5,1,-.5,-.5])/math.sqrt(3),
        np.array([0,.5,-.5,0,.5,-.5]), np.array([1,-1,1,-1,1,-1])/math.sqrt(6)))
    eig = np.array([0,1,1,3,3,4])
    uk = u[:,:3]
    a_true = uk.T @ X
    close(u.T@u, np.eye(6), MATRIX_TOL)
    close(l@u, u*eig, MATRIX_TOL)
    close(h@X, [2.75,2.75,2,1.25,1.25,2], MATRIX_TOL)
    close(np.column_stack([local_l(e,C6_EDGES) for e in np.eye(6)]), l, MATRIX_TOL)
    close(np.column_stack([local_h(e,C6_EDGES) for e in np.eye(6)]), h, MATRIX_TOL)
    data = {'schema': 1, 'units': 'V; dimensionless L/H/weights/mu/alpha', 'l':l, 'h':h, 'u':u,
            'lambda':eig, 'x':X, 'hx':h@X, 'a_true':a_true, 'band':{}}
    for name, omega in [('even', OMEGA_E), ('cluster', OMEGA_C)]:
        s = sampling(6,omega)
        a = s@h
        b = a@uk
        eta = NOISE[omega]
        y = a@X+eta
        ahat = band_solve(b,y)
        xhat = uk@ahat
        error = np.linalg.norm(xhat-X)
        upper = np.linalg.norm(eta)/min_gain(b)
        bound(error,upper)
        close(local_forward(X,C6_EDGES,omega),a@X,MATRIX_TOL)
        close(local_adjoint(eta,6,C6_EDGES,omega),a.T@eta,MATRIX_TOL)
        close(np.dot(a@X,eta),np.dot(X,local_adjoint(eta,6,C6_EDGES,omega)),MATRIX_TOL)
        expected = [9/32, (25-math.sqrt(561))/64, (25+math.sqrt(561))/64] if name=='cluster' else [.5,9/32,9/32]
        close(np.linalg.eigvalsh(b.T@b),sorted(expected))
        data['band'][name]={'omega':omega,'a':a,'b':b,'gram':b.T@b,'s_min':min_gain(b),
            'y':y,'noise_norm':np.linalg.norm(eta),'x_hat':xhat,'error':error,'noise_bound':upper,
            'residual':np.linalg.norm(a@xhat-y)}
    se=min_gain(data['band']['even']['b'])
    design=[{'omega':list(o),'s_min':min_gain(sampling(6,list(o))@h@uk)} for o in itertools.combinations(range(6),3)]
    best=max(v['s_min'] for v in design)
    winners=[v['omega'] for v in design if abs(v['s_min']-best)<VALUE_TOL]
    assert winners==[[0,2,4],[1,3,5]]
    close(best,3/(4*math.sqrt(2)))
    data['design']={'all':design,'best_sets':winners,'upper':3/(4*math.sqrt(2))}
    s=sampling(6,OMEGA_E); a=s@h; b=a@uk
    direction=s@u[:,2]; eta_adv=.02*direction/np.linalg.norm(direction)
    adversarial=uk@band_solve(b,a@X+eta_adv)
    close(np.linalg.norm(adversarial-X),.02/se)
    tail=.3*np.array([1,-.5,-.5,1,-.5,-.5])
    tailhat=uk@band_solve(b,a@(X+tail))
    close(tailhat-X,.1*np.array([1,.5,-.5,-1,-.5,.5]))
    tail_error=np.linalg.norm(tailhat-X-tail)
    close(tail_error,math.sqrt(.3))
    delta=np.linalg.norm(tail)
    tail_bound=math.sqrt(delta**2+(np.linalg.norm(a@tail)/se)**2)
    bound(tail_error,tail_bound)
    close(h@u[:,5],np.zeros(6),MATRIX_TOL)
    s03=sampling(6,[0,3])
    ranks=[int(np.linalg.matrix_rank(s03@h@u[:,idx],tol=RANK_TOL)) for idx in [[0,1],[0,2],[0,1,2]]]
    assert ranks==[2,1,2]
    # Repeated-eigenspace rotation and node reindexing preserve the same problem.
    angle=math.pi/5; rot=np.eye(3)
    rot[1:,1:]=[[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]]
    close(uk@rot@band_solve(b@rot,data['band']['even']['y']),data['band']['even']['x_hat'])
    pi=np.eye(6)[[3,0,5,2,1,4]]
    ap=(s@pi.T)@(pi@h@pi.T); up=pi@uk
    close(up@band_solve(ap@up,data['band']['even']['y']),pi@data['band']['even']['x_hat'])
    # Connected m=K is not sufficient for band identifiability.
    l4=laplacian(4,[(0,1,1),(0,2,1),(1,2,1),(2,3,1)])
    h4=np.eye(4)-l4/4; u4=np.column_stack([np.ones(4)/2,np.array([1,1,0,-2])/math.sqrt(6)])
    invisible=np.array([1.,1.,-3.,-11.])
    close(np.linalg.eigvalsh(l4),[0,1,3,4]); close(h4@invisible,[0,0,-3,-9])
    assert min_gain(sampling(4,[0,1])@h4@u4)<RANK_TOL
    assert min_gain(sampling(4,[0,3])@h4@u4)>RANK_TOL
    # The smooth optimizer can be unique although the truth is invisible.
    az=s03@h; zero,_,_=smooth(az,l,np.zeros(2),MU)
    close(az@u[:,2],np.zeros(2)); close(zero,np.zeros(6))
    edges2=[(0,1,1),(1,2,1),(2,0,1),(3,4,1),(4,5,1),(5,3,1)]
    ld=laplacian(6,edges2); hd=np.eye(6)-ld/4; ad=sampling(6,[0,1])@hd
    qd=ad.T@ad+MU*ld; evd=np.linalg.eigvalsh(qd)
    assert np.count_nonzero(evd>RANK_TOL)==5
    xd=np.array([1.,1.,1.,3.,3.,3.]); yd=ad@xd
    ridge_d=np.linalg.solve(qd+.01*np.eye(6),ad.T@yd)
    close(ridge_d[3:],np.zeros(3))
    data['failures']={'tail':{'r':tail,'x_hat':tailhat,'error':tail_error,'bound':tail_bound,
        'residual':np.linalg.norm(a@tailhat-a@(X+tail))},'highest_mode_gain':np.linalg.norm(h@u[:,5]),
        'cut_repeated_ranks':ranks,'connected':{'l':l4,'invisible':invisible,'h_invisible':h4@invisible},
        'zero_data':{'truth':u[:,2],'x_hat':zero,'error':np.linalg.norm(zero-u[:,2]),'residual':np.linalg.norm(az@zero)},
        'disconnected':{'eigenvalues_q':evd,'ridge_x':ridge_d,'unseen_error':np.linalg.norm(ridge_d[3:]-xd[3:])}}
    data['adversarial']={'epsilon':.02,'eta':eta_adv,'error':np.linalg.norm(adversarial-X),'upper':.02/se}
    y=data['band']['even']['y']; eta=NOISE[OMEGA_E]
    xhat,q,ev=smooth(a,l,y,MU)
    truth_error=np.linalg.norm(xhat-X)
    bias_bound=MU*np.linalg.norm(l@X)/ev[0]
    noise_bound=np.linalg.norm(a,2)*np.linalg.norm(eta)/ev[0]
    bound(truth_error,bias_bound+noise_bound)
    close(xhat-X,-MU*np.linalg.solve(q,l@X)+np.linalg.solve(q,a.T@eta))
    step=1/ev[-1]; xi=np.zeros(6); history=[]
    for k in range(5001):
        residual=local_adjoint(local_forward(xi,C6_EDGES,OMEGA_E)-y,6,C6_EDGES,OMEGA_E)+MU*local_l(xi,C6_EDGES)
        cert=np.linalg.norm(residual)/ev[0]
        opt_error=np.linalg.norm(xi-xhat)
        bound(opt_error,cert)
        history.append({'iteration':k,'certificate':cert,'optimum_error':opt_error})
        if cert<=GD_TOL:
            break
        xi=xi-step*residual
    else:
        raise AssertionError('GD did not meet its predeclared certificate tolerance')
    close(xi,xhat)
    mu_sweep=[]
    for mu in MU_GRID:
        xm,qm,em=smooth(a,l,y,mu)
        mu_sweep.append({'mu':mu,'x_hat':xm,'truth_error':np.linalg.norm(xm-X),
            'fit_norm':np.linalg.norm(a@xm-y),'energy':xm@l@xm,'q_min':em[0]})
    assert all(mu_sweep[i]['energy']>=mu_sweep[i+1]['energy']-VALUE_TOL for i in range(len(mu_sweep)-1))
    assert all(mu_sweep[i]['fit_norm']<=mu_sweep[i+1]['fit_norm']+VALUE_TOL for i in range(len(mu_sweep)-1))
    changed=[(i,j,1.01 if (i,j)==(0,1) else w) for i,j,w in C6_EDGES]
    lp=laplacian(6,changed); hp=np.eye(6)-lp/4; ap=s@hp
    xp,qp,ep=smooth(ap,lp,y,MU); da=np.linalg.norm(ap-a,2); dq=np.linalg.norm(qp-q,2)
    assert dq<ev[0]
    model_bound=(da*np.linalg.norm(y)+dq*np.linalg.norm(xhat))/(ev[0]-dq)
    model_error=np.linalg.norm(xp-xhat); bound(model_error,model_bound)
    dq_upper=2*np.linalg.norm(a,2)*da+da**2+MU*np.linalg.norm(lp-l,2); bound(dq,dq_upper)
    close(smooth(a,7*l,y,MU/7)[0],xhat)
    ridge=[]; bc=data['band']['cluster']['b']; yc=data['band']['cluster']['y']; ec=NOISE[OMEGA_C]
    for alpha in ALPHA_GRID:
        ar=band_solve(bc,yc) if alpha==0 else np.linalg.solve(bc.T@bc+alpha*np.eye(3),bc.T@yc)
        upper=np.linalg.norm(ec)/min_gain(bc) if alpha==0 else alpha/(min_gain(bc)**2+alpha)*np.linalg.norm(a_true)+np.linalg.norm(ec)/(2*math.sqrt(alpha))
        er=np.linalg.norm(ar-a_true); bound(er,upper)
        ridge.append({'alpha':alpha,'coefficient':ar,'error':er,'upper':upper})
    data['smooth']={'mu':MU,'x_hat':xhat,'q':q,'q_eigenvalues':ev,'truth_error':truth_error,
        'bias_bound':bias_bound,'noise_bound':noise_bound,'mu_sweep':mu_sweep,
        'gd':{'step':step,'iterations':k,'x':xi,'certificate':cert,'history':history},
        'model':{'changed_edge':[0,1,1.01],'delta_a':da,'delta_l':np.linalg.norm(lp-l,2),
            'delta_q':dq,'delta_q_upper':dq_upper,'q_min':ev[0],'error':model_error,'upper':model_bound,'x_hat_prime':xp}}
    data['ridge']=ridge
    invalid=[('boolean n',lambda:laplacian(True,[])),('negative weight',lambda:laplacian(2,[(0,1,-1)])),
        ('duplicate edge',lambda:laplacian(2,[(0,1,1),(1,0,1)])),('self-loop',lambda:laplacian(2,[(0,0,1)])),
        ('endpoint',lambda:laplacian(2,[(0,2,1)])),('nan weight',lambda:laplacian(2,[(0,1,float('nan'))])),
        ('duplicate sample',lambda:sampling(6,[0,0])),('sample range',lambda:sampling(6,[6])),
        ('boolean sample',lambda:sampling(6,[False])),('zero mu',lambda:smooth(a,l,y,0)),
        ('wrong y shape',lambda:smooth(a,l,np.zeros(2),.1)),('rank-deficient LS',lambda:band_solve(s03@h@uk,np.zeros(2))),
        ('uncovered component',lambda:smooth(ad,ld,yd,.1))]
    rejected=[]
    for name,fn in invalid:
        try:
            fn()
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError('missing refusal: '+name)
    data['rejected']=rejected
    data['tolerances']={'matrix':MATRIX_TOL,'values':VALUE_TOL,'bounds':BOUND_TOL,'rank':RANK_TOL,'lstsq_rcond':RCOND,'gd_certificate':GD_TOL}
    return data


def serial(value):
    if isinstance(value,np.ndarray): return value.tolist()
    if isinstance(value,np.generic): return value.item()
    if isinstance(value,dict): return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [serial(v) for v in value]
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    out=args.output_dir
    for sub in ['results','figures']: (out/sub).mkdir(parents=True,exist_ok=True)
    inputs={'nodes':6,'edges':C6_EDGES,'x_B_V':X,'noise_global_V':NOISE,'omega_even':OMEGA_E,'omega_cluster':OMEGA_C,
        'prefilter':'I - L/4','band':'all eigenvalues <= 1; K=3','mu':MU,'mu_grid':MU_GRID,'alpha_grid':ALPHA_GRID,
        'tail_V':[.3,-.15,-.15,.3,-.15,-.15],'adversarial_noise_norm_V':.02,'changed_edge':[0,1,1.01]}
    data=run()
    (out/'inputs.json').write_text(json.dumps(serial(inputs),indent=2,allow_nan=False)+'\n')
    clean=serial(data)
    (out/'results'/'results.json').write_text(json.dumps(clean,indent=2,allow_nan=False)+'\n')
    figures(out,clean)
    print('PASS: fixed C6 forward/adjoint, full repeated band, 20 sample sets, noise/tail and invisible modes')
    print(f"min gains even={clean['band']['even']['s_min']:.12g}, cluster={clean['band']['cluster']['s_min']:.12g}")
    print(f"tail error={clean['failures']['tail']['error']:.12g} V; residual={clean['failures']['tail']['residual']:.3g} V")
    print(f"smooth q_min={clean['smooth']['q_eigenvalues'][0]:.12g}; GD iterations={clean['smooth']['gd']['iterations']}; certificate={clean['smooth']['gd']['certificate']:.3g} V")
    print(f"model error={clean['smooth']['model']['error']:.12g} <= {clean['smooth']['model']['upper']:.12g} V; rejected={len(clean['rejected'])}")


if __name__=='__main__':
    main()
