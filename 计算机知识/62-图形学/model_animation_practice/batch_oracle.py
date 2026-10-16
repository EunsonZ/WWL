"""Fixed-input independent batch answers: piecewise polynomials, weight matrices and exact powers.
Does not import either new model, shared topology, NumPy, or renderer.
"""
import argparse,json,math,hashlib
from fractions import Fraction as Q
from collections import defaultdict
from pathlib import Path


def close(x,y,tol=1e-10):
    if isinstance(x,(list,tuple)):
        assert len(x)==len(y)
        for a,b in zip(x,y):close(a,b,tol)
    else:assert abs(float(x)-float(y))<=tol*max(1,abs(float(x)),abs(float(y))),(x,y)


def dot(a,b):return sum(x*y for x,y in zip(a,b))
def apply(m,p):return [dot(row,p) for row in m]
def mul(a,b):return [[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]
def power(m,n):
    out=[[Q(1),Q(0)],[Q(0),Q(1)]]
    for _ in range(n):out=mul(out,m)
    return out


def grid(n):
    p=[[2*i/n,2*j/n,(i/n)*(1-i/n)+(j/n)*(1-j/n)] for j in range(n+1) for i in range(n+1)];f=[]
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;f.extend([[a,a+1,a+n+1],[a+1,a+n+2,a+n+1]])
    return p,f


def refine(p,f):
    edges=defaultdict(list);near=defaultdict(set)
    for face in f:
        for i in range(3):
            a,b,c=face[i],face[(i+1)%3],face[(i+2)%3];edges[tuple(sorted((a,b)))].append(c);near[a].add(b);near[b].add(a)
    rows=[]
    for v in range(len(p)):
        boundary=[b if a==v else a for (a,b),faces in edges.items() if len(faces)==1 and v in (a,b)];r=[0.]*len(p)
        if boundary:
            assert len(boundary)==2;r[v]=.75
            for k in boundary:r[k]=.125
        else:
            n=len(near[v]);beta=(.625-(.375+.25*math.cos(2*math.pi/n))**2)/n;r[v]=1-n*beta
            for k in near[v]:r[k]=beta
        rows.append(r)
    ordered=sorted(edges);lookup={e:i+len(p) for i,e in enumerate(ordered)}
    for edge in ordered:
        opposite=edges[edge];r=[0.]*len(p)
        for k in edge:r[k]=.5 if len(opposite)==1 else .375
        if len(opposite)==2:
            for k in opposite:r[k]+=.125
        rows.append(r)
    q=mul(rows,p);g=[]
    for a,b,c in f:
        ab=lookup[tuple(sorted((a,b)))];bc=lookup[tuple(sorted((b,c)))];ca=lookup[tuple(sorted((c,a)))];g.extend([[a,ab,ca],[b,bc,ab],[c,ca,bc],[ab,bc,ca]])
    return q,g


def check(spec,actual,folder):
    # Deliberately finite polynomial tables for the two declared knot configurations.
    assert spec['spline']['knots']==[0,0,0,1,2,2,2] and spec['spline']['degree']==2
    assert spec['repeated_spline']['knots']==[0,0,0,1,1,2,2,2]
    for name,obs in zip(('spline','repeated_spline'),actual['splines']):
        inp=spec[name]
        for t,row in zip(inp['parameters'],obs['samples']):
            t=Q(str(t))
            if name=='spline':
                if t<=1:weights=[(1-t)**2,2*t-Q(3,2)*t*t,t*t/2,0]
                else:
                    z=t-1;weights=[0,(1-z)**2/2,Q(1,2)+z-Q(3,2)*z*z,z*z]
            else:
                z=t if t<=1 else t-1;weights=[(1-z)**2,2*z*(1-z),z*z,0,0] if t<=1 else [0,0,(1-z)**2,2*z*(1-z),z*z]
            close(weights,row['basis']);close([sum(w*p[k] for w,p in zip(weights,inp['control'])) for k in range(3)],row['point'])
        if name=='spline':
            for before,after in zip(obs['samples'],obs['edited_samples']):
                weights=before['basis'];close([before['point'][k]+weights[inp['edit_index']]*inp['edit_delta'][k] for k in range(3)],after['point'])
    expected_control=[[[i,j,.5*((i==1)+(j==1))] for j in range(3)] for i in range(3)];assert spec['patch_control']==expected_control
    for row in actual['patch_samples']:
        u,v=row['uv'];close(row['point'],[2*u,2*v,u*(1-u)+v*(1-v)]);close(row['du'],[2,0,1-2*u]);close(row['dv'],[0,2,1-2*v])
    for n,mesh in zip(spec['patch_n'],actual['patches']):
        p,f=grid(n);close(p,mesh['positions']);assert f==mesh['triangles'];close([1/(2*n*n)]*(n*n),mesh['cell_diagonal_midpoint_errors']);assert [mesh['topology'][x] for x in ('V','E','F','chi','boundary_count')]==[(n+1)**2,3*n*n+2*n,2*n*n,1,4*n]
        for j in range(n+1):
            for i in range(n+1):
                normal=[-(1-2*i/n)/2,-(1-2*j/n)/2,1];length=math.sqrt(dot(normal,normal));close(mesh['normals'][j*(n+1)+i],[x/length for x in normal])
    p,f=grid(spec['loop_start_n'])
    for row in actual['loop']:
        close(p,row['positions']);assert f==row['triangles'];assert row['topology']['chi']==1;p,f=refine(p,f)
    close(actual['quaternion']['mid_matrix'],[[-1,0,0,0],[0,-1,0,0],[0,0,1,0],[0,0,0,1]])
    for row in actual['poses']:
        t=row['t'];theta=math.radians(spec['skin_max_degrees'])*t;c=math.cos(theta);s=math.sin(theta);points=actual['patches'][0]['positions'];weights=[[1-x/2,x/2] for x,y,z in points];close(weights,row['weights'])
        g0=[[1,0,0,.2*t],[0,1,0,0],[0,0,1,0],[0,0,0,1]];g1=[[c,-s,0,1+.2*t],[s,c,0,0],[0,0,1,0],[0,0,0,1]];close(row['world'],[g0,g1])
        expected=[]
        for (x,y,z),(w0,w1) in zip(points,weights):expected.append([w0*x+w1*(1+c*(x-1)-s*y)+.2*t,w0*y+w1*(s*(x-1)+c*y),z])
        close(expected,row['positions'])
    close(actual['nonrigid']['TS'],[5,0,0,1]);close(actual['nonrigid']['ST'],[8,0,0,1]);close(actual['nonrigid']['inverse_transpose_normal'],[.5,-1,0]);close(actual['collapse']['positions'],[[0,0,0]])
    for row in actual['ik']:
        if row['status']=='solved':
            for sol in row['solutions']:close(sol['end'],row['target'])
        else:assert row['status'] in ('unreachable','underdetermined_target')
    states=0
    for row in actual['spring']:
        h=Q(str(row['h']));w=Q(str(spec['spring']['omega']));m=[[1,h],[-w*w*h,1]] if row['method']=='explicit' else [[1-w*w*h*h,h],[-w*w*h,1]]
        for k,observed in enumerate(row['trace']):
            q,v=apply(power(m,k),[Q(1),Q(0)]);t=k*h;close([q,v,t], [observed['q'],observed['v'],observed['time']]);close((v*v+w*w*q*q)/2,observed['energy']);states+=1
    for row in actual['comparison']:
        close(1/(2*row['n']**2),row['geometry_error']);end=next(x for x in actual['spring'] if x['method']=='symplectic' and x['h']==row['h'])['trace'][-1];close(row['q_error'],abs(end['q']-math.cos(spec['spring']['omega'])));close(row['phase_state_error'],math.hypot(end['q']-math.cos(spec['spring']['omega']),end['v']/spec['spring']['omega']+math.sin(spec['spring']['omega'])))
    for row in actual['renders']:assert hashlib.sha256((folder/row['png']).read_bytes()).hexdigest()==row['png_sha256']
    return {'status':'PASS','spline_samples':sum(len(x['samples']) for x in actual['splines']),'patch_meshes':len(actual['patches']),'loop_levels':len(actual['loop']),'skin_poses':len(actual['poses']),'spring_states':states,'png_sha_count':len(actual['renders']),'absolute_relative_tolerance':1e-10,'scope':'fixed specification, geometry/kinematics/state/PNG identity; not a pixel rendering oracle'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--actual',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=check(json.loads(a.spec.read_text()),json.loads(a.actual.read_text()),a.actual.parent);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
