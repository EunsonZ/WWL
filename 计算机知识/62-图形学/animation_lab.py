"""Column-vector scene hierarchy, shortest-arc quaternions, LBS and finite spring integration."""
import math
import numpy as np


def translation(x,y,z):
    m=np.eye(4);m[:3,3]=[x,y,z];return m


def unit_quaternion(value):
    q=np.asarray(value,dtype=float)
    if q.shape!=(4,) or not np.isfinite(q).all() or np.linalg.norm(q)<=1e-12:raise ValueError('quaternion')
    return q/np.linalg.norm(q)


def axis_angle(axis,angle):
    a=np.asarray(axis,dtype=float)
    if a.shape!=(3,) or not np.isfinite(a).all() or np.linalg.norm(a)<=1e-12 or not np.isfinite(angle):raise ValueError('axis_angle')
    return np.r_[math.cos(angle/2),a/np.linalg.norm(a)*math.sin(angle/2)]


def rotation(value):
    w,x,y,z=unit_quaternion(value);m=np.eye(4)
    m[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],[2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],[2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]]
    return m


def slerp(a,b,t):
    a=unit_quaternion(a);b=unit_quaternion(b)
    if not np.isfinite(t) or not 0<=t<=1:raise ValueError('key_parameter')
    dot=float(a@b)
    if dot<0:b=-b;dot=-dot
    dot=min(1.,max(-1.,dot))
    if dot>.9995:return unit_quaternion((1-t)*a+t*b)
    theta=math.acos(dot)
    return unit_quaternion((math.sin((1-t)*theta)*a+math.sin(t*theta)*b)/math.sin(theta))


def hierarchy(parents,local):
    a=np.asarray(local,dtype=float)
    if not 1<=len(parents)<=16 or a.shape!=(len(parents),4,4) or not np.isfinite(a).all() or not np.allclose(a[:,3,:],[0,0,0,1],atol=1e-12,rtol=0):raise ValueError('local_affine')
    world=[]
    for i,parent in enumerate(parents):
        if type(parent)!=int or parent < -1 or parent>=i:raise ValueError('parent_topological_order')
        world.append(a[i] if parent==-1 else world[parent]@a[i])
    return np.array(world)


def skin(positions,weights,pose,bind):
    p=np.asarray(positions,dtype=float);w=np.asarray(weights,dtype=float);g=np.asarray(pose,dtype=float);b=np.asarray(bind,dtype=float)
    if p.ndim!=2 or p.shape[1]!=3 or w.ndim!=2 or w.shape[0]!=len(p) or not 1<=w.shape[1]<=16 or g.shape!=(w.shape[1],4,4) or b.shape!=g.shape:raise ValueError('skin_shape')
    if not all(np.isfinite(x).all() for x in (p,w,g,b)) or np.any(w<0) or not np.allclose(w.sum(axis=1),1,atol=1e-12,rtol=0):raise ValueError('skin_weights')
    if not np.allclose(g[:,3,:],[0,0,0,1],atol=1e-12,rtol=0) or not np.allclose(b[:,3,:],[0,0,0,1],atol=1e-12,rtol=0) or any(np.linalg.cond(x)>1e12 for x in b):raise ValueError('skin_bind')
    k=g@np.linalg.inv(b);hp=np.c_[p,np.ones(len(p))];blend=np.einsum('ij,jab->iab',w,k);out=np.einsum('iab,ib->ia',blend,hp)
    return {'positions':out[:,:3].tolist(),'joint_matrices':k.tolist(),'blend_linear_determinants':np.linalg.det(blend[:,:3,:3]).tolist()}


def fk2(lengths,angles):
    l=np.asarray(lengths,dtype=float);q=np.asarray(angles,dtype=float)
    if l.shape!=(2,) or q.shape!=(2,) or not np.isfinite(l).all() or not np.isfinite(q).all() or np.any(l<=0):raise ValueError('two_link')
    elbow=l[0]*np.array([math.cos(q[0]),math.sin(q[0])]);end=elbow+l[1]*np.array([math.cos(q.sum()),math.sin(q.sum())]);return {'elbow':elbow.tolist(),'end':end.tolist()}


def ik2(lengths,target):
    l=np.asarray(lengths,dtype=float);p=np.asarray(target,dtype=float)
    if l.shape!=(2,) or p.shape!=(2,) or not np.isfinite(l).all() or not np.isfinite(p).all() or np.any(l<=0):raise ValueError('two_link')
    r=float(np.linalg.norm(p))
    if r<abs(l[0]-l[1])-1e-12 or r>l.sum()+1e-12:raise ValueError('unreachable')
    if r<=1e-12:raise ValueError('underdetermined_target')
    c=float(np.clip((r*r-l@l)/(2*l[0]*l[1]),-1,1));q2=math.acos(c);out=[]
    for bend in ([q2] if abs(math.sin(q2))<=1e-12 else [q2,-q2]):
        q1=math.atan2(p[1],p[0])-math.atan2(l[1]*math.sin(bend),l[0]+l[1]*math.cos(bend));out.append([q1,bend])
    return out


def spring(omega,h,steps,method):
    if not np.isfinite([omega,h]).all() or not 0<omega<=10 or not 0<h<=2 or omega*h>4 or type(steps)!=int or not 1<=steps<=64 or method not in ('explicit','symplectic'):raise ValueError('spring_input')
    q=1.;v=0.;trace=[]
    for i in range(steps+1):
        t=i*h;exact=np.array([math.cos(omega*t),-omega*math.sin(omega*t)]);state=np.array([q,v]);error=state-exact
        trace.append({'step':i,'time':t,'q':q,'v':v,'energy':.5*(v*v+omega*omega*q*q),'exact':exact.tolist(),'q_error':abs(float(error[0])),'phase_state_error':float(np.linalg.norm([error[0],error[1]/omega]))})
        if i==steps:break
        if method=='explicit':q,v=q+h*v,v-h*omega*omega*q
        else:v=v-h*omega*omega*q;q=q+h*v
    return trace
