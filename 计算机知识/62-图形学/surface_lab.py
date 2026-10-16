"""Finite spline/patch/Loop teaching model; canonical rasterizer and topology stay separate."""
import math
from collections import defaultdict
import numpy as np
from curve_mesh_lab import topology


def spline(control,knots,degree,t):
    p=np.asarray(control,dtype=float);u=np.asarray(knots,dtype=float)
    if p.ndim!=2 or p.shape[1]!=3 or not 2<=len(p)<=12 or not np.isfinite(p).all() or np.max(np.abs(p))>100:raise ValueError('spline_control')
    if type(degree)!=int or not 1<=degree<=3 or len(p)<=degree:raise ValueError('spline_degree')
    if u.shape!=(len(p)+degree+1,) or not np.isfinite(u).all() or np.any(np.diff(u)<0) or u[degree]>=u[len(p)]:raise ValueError('knots')
    if not np.isfinite(t) or not u[degree]<=t<=u[len(p)]:raise ValueError('spline_parameter')
    # Left-limit at the final domain endpoint, not a global step-function convention.
    x=np.nextafter(t,-np.inf) if t==u[len(p)] else t
    values=((u[:-1]<=x)&(x<u[1:])).astype(float)
    for q in range(1,degree+1):
        values=np.array([((x-u[i])/(u[i+q]-u[i])*values[i] if u[i+q]!=u[i] else 0)+((u[i+q+1]-x)/(u[i+q+1]-u[i+1])*values[i+1] if u[i+q+1]!=u[i+1] else 0) for i in range(len(values)-1)])
    return {'basis':values.tolist(),'point':(values@p).tolist()}


def patch(control,u,v):
    p=np.asarray(control,dtype=float)
    if p.shape!=(3,3,3) or not np.isfinite(p).all() or np.max(np.abs(p))>100:raise ValueError('patch_control')
    if not np.isfinite([u,v]).all() or not 0<=u<=1 or not 0<=v<=1:raise ValueError('patch_parameter')
    def basis(t):return np.array([(1-t)**2,2*t*(1-t),t*t]),np.array([-2*(1-t),2-4*t,2*t])
    bu,du=basis(u);bv,dv=basis(v)
    point=np.einsum('i,j,ijk->k',bu,bv,p);su=np.einsum('i,j,ijk->k',du,bv,p);sv=np.einsum('i,j,ijk->k',bu,dv,p)
    n=np.cross(su,sv);length=np.linalg.norm(n)
    if length<=1e-12:raise ValueError('singular_patch_parameterization')
    return point,su,sv,n/length


def patch_mesh(control,n):
    if type(n)!=int or not 1<=n<=16:raise ValueError('patch_resolution')
    samples=[patch(control,i/n,j/n) for j in range(n+1) for i in range(n+1)]
    p=np.array([s[0] for s in samples]);normal=np.array([s[3] for s in samples]);faces=[]
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;b=a+1;c=a+n+1;d=c+1;faces.extend([[a,b,c],[b,d,c]])
    f=np.array(faces,dtype=int)
    return {'positions':p.tolist(),'triangles':f.tolist(),'normals':normal.tolist(),'topology':topology(p,f)}


def loop_step(positions,faces):
    p=np.asarray(positions,dtype=float);f=np.asarray(faces);top=topology(p,f)
    neighbors=defaultdict(set);boundary=defaultdict(list)
    for row in top['edges']:
        a,b=row['vertices'];neighbors[a].add(b);neighbors[b].add(a)
        if len(row['faces'])==1:boundary[a].append(b);boundary[b].append(a)
    new=[]
    for i,point in enumerate(p):
        ns=sorted(neighbors[i])
        if i in boundary:
            if len(boundary[i])!=2:raise ValueError('loop_boundary')
            q=.75*point+.125*p[boundary[i]].sum(axis=0)
        else:
            n=len(ns);beta=(5/8-(3/8+.25*math.cos(2*math.pi/n))**2)/n
            q=(1-n*beta)*point+beta*p[ns].sum(axis=0)
        new.append(q)
    edge_index={}
    for row in top['edges']:
        a,b=row['vertices'];ids=row['faces'];edge_index[(a,b)]=len(new)
        if len(ids)==1:q=(p[a]+p[b])/2
        else:
            opposite=[next(x for x in f[k] if x not in (a,b)) for k in ids]
            q=3/8*(p[a]+p[b])+1/8*p[opposite].sum(axis=0)
        new.append(q)
    refined=[]
    for a,b,c in f.tolist():
        ab=edge_index[tuple(sorted((a,b)))];bc=edge_index[tuple(sorted((b,c)))];ca=edge_index[tuple(sorted((c,a)))]
        refined.extend([[a,ab,ca],[b,bc,ab],[c,ca,bc],[ab,bc,ca]])
    new=np.asarray(new);refined=np.asarray(refined,dtype=int)
    return {'positions':new.tolist(),'triangles':refined.tolist(),'topology':topology(new,refined),'edge_indices':[{'edge':list(e),'vertex':i} for e,i in edge_index.items()]}


def flat_arrays(mesh):
    """Face normals from actual geometry; duplicated vertices are a render view, not welded topology."""
    p=np.asarray(mesh['positions']);f=np.asarray(mesh['triangles'],dtype=int);tri=p[f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);length=np.linalg.norm(cross,axis=1)
    if np.any(length<=1e-12):raise ValueError('deformed_degenerate_face')
    vertices=tri.reshape(-1,3);normals=np.repeat(cross/length[:,None],3,axis=0)
    return vertices,np.arange(len(vertices)).reshape(-1,3),normals
