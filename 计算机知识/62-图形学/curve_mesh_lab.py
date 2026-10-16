"""Quadratic de Casteljau -> indexed XY ribbon -> the existing renderer arrays."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import struct
import zlib
import numpy as np


def controls(value):
    p=np.asarray(value,dtype=float)
    if p.shape!=(3,3) or not np.isfinite(p).all() or np.max(np.abs(p))>100:raise ValueError('control_shape_or_scale')
    return p


def casteljau(p,t):
    p=controls(p)
    if not np.isfinite(t) or not 0<=t<=1:raise ValueError('parameter_domain')
    first=(1-t)*p[:-1]+t*p[1:]
    return (1-t)*first[0]+t*first[1]


def tangent(p,t):
    p=controls(p)
    if not np.isfinite(t) or not 0<=t<=1:raise ValueError('parameter_domain')
    return 2*((1-t)*(p[1]-p[0])+t*(p[2]-p[1]))


def topology(positions,faces):
    p=np.asarray(positions,dtype=float);f=np.asarray(faces)
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all():raise ValueError('vertex_shape')
    if f.ndim!=2 or f.shape[1]!=3 or f.dtype.kind not in 'iu' or len(f)==0 or np.any(f<0) or np.any(f>=len(p)):raise ValueError('face_index')
    edge_faces=defaultdict(list);vertex_faces=defaultdict(list);seen=set()
    for i,face in enumerate(f.tolist()):
        if len(set(face))!=3:raise ValueError('repeated_face_vertex')
        if tuple(sorted(face)) in seen:raise ValueError('duplicate_face')
        seen.add(tuple(sorted(face)))
        a,b,c=p[face]
        if np.linalg.norm(np.cross(b-a,c-a))<=1e-12:raise ValueError('numerically_degenerate_face')
        for v in face:vertex_faces[v].append(i)
        for a,b in zip(face,face[1:]+face[:1]):edge_faces[tuple(sorted((a,b)))].append((i,a,b))
    if set(vertex_faces)!=set(range(len(p))):raise ValueError('unused_vertex')
    boundary=[];face_neighbors=[set() for _ in f]
    for edge,uses in edge_faces.items():
        if len(uses)>2:raise ValueError('nonmanifold_edge')
        if len(uses)==1:boundary.append(edge)
        else:
            u,v=uses
            if (u[1],u[2])!=(v[2],v[1]):raise ValueError('shared_edge_orientation')
            face_neighbors[u[0]].add(v[0]);face_neighbors[v[0]].add(u[0])
    links=[]
    for v,ids in sorted(vertex_faces.items()):
        graph=defaultdict(set)
        for face_id in ids:
            a,b=[x for x in f[face_id].tolist() if x!=v];graph[a].add(b);graph[b].add(a)
        reached=set();todo=[next(iter(graph))]
        while todo:
            n=todo.pop()
            if n not in reached:reached.add(n);todo.extend(graph[n]-reached)
        if len(reached)!=len(graph):raise ValueError('disconnected_vertex_link')
        degrees=sorted(map(len,graph.values()));bd=sum(v in edge for edge in boundary)
        if (bd==0 and any(d!=2 for d in degrees)) or (bd==2 and (degrees.count(1)!=2 or any(d not in (1,2) for d in degrees))) or bd not in (0,2):raise ValueError('invalid_vertex_link')
        links.append({'vertex':v,'neighbor_degrees':degrees,'boundary_edges':bd})
    bdgraph=defaultdict(set)
    for a,b in boundary:bdgraph[a].add(b);bdgraph[b].add(a)
    loops=[];remaining=set(boundary)
    while remaining:
        a=min(min(e) for e in remaining);b=min(bdgraph[a]);loop=[a,b];remaining.remove(tuple(sorted((a,b))))
        while b!=a:
            c=next(x for x in bdgraph[b] if x!=loop[-2]);remaining.remove(tuple(sorted((b,c))));loop.append(c);b=c
        loops.append(loop)
    return {'V':len(p),'E':len(edge_faces),'F':len(f),'chi':len(p)-len(edge_faces)+len(f),
            'edges':[{'vertices':list(e),'faces':[u[0] for u in uses]} for e,uses in sorted(edge_faces.items())],
            'boundary_edges':[list(e) for e in sorted(boundary)],'boundary_loops':loops,
            'face_neighbors':[sorted(n) for n in face_neighbors],'vertex_links':links,
            'boundary_count':len(boundary),'scope':'connectivity and supplied orientation only; no global self-intersection test'}


def band(p,ts,width):
    p=controls(p);ts=np.asarray(ts,dtype=float)
    if np.any(p[:,2]!=0) or np.any(np.diff(p[:,0])<=1e-10):raise ValueError('band_requires_xy_increasing_control_x')
    if ts.ndim!=1 or not 2<=len(ts)<=65 or not np.isfinite(ts).all() or ts[0]!=0 or ts[-1]!=1 or np.any(np.diff(ts)<=1e-8):raise ValueError('sample_parameters')
    if not np.isfinite(width) or not 0<width<=1:raise ValueError('band_width')
    points=np.array([casteljau(p,float(t)) for t in ts])
    pos=np.array([point+[0,sign*width/2,0] for point in points for sign in (-1,1)])
    faces=np.array([[2*i,2*i+2,2*i+1] if k==0 else [2*i+2,2*i+3,2*i+1] for i in range(len(ts)-1) for k in range(2)],dtype=int)
    n=np.tile([0.,0.,1.],(len(pos),1));color=np.array([[.2+.6*t,.4,1-.6*t] for t in ts for _ in (-1,1)])
    error=[];a=p[0]-2*p[1]+p[2]
    for lo,hi in zip(ts[:-1],ts[1:]):
        mid=(lo+hi)/2; exact=np.linalg.norm(casteljau(p,mid)-(casteljau(p,lo)+casteljau(p,hi))/2)
        error.append({'interval':[float(lo),float(hi)],'midpoint_error':float(exact),'exact_matched_parameter_max':float(np.linalg.norm(a)*(hi-lo)**2/4)})
    return {'control':p.tolist(),'parameters':ts.tolist(),'total_y_width':float(width),'curve_points':points.tolist(),
            'endpoint_tangents':[tangent(p,0).tolist(),tangent(p,1).tolist()],
            'positions':pos.tolist(),'triangles':faces.tolist(),'colors':color.tolist(),'normals':n.tolist(),
            'interval_errors':error,'exact_matched_parameter_max':max(x['exact_matched_parameter_max'] for x in error),
            'topology':topology(pos,faces)}


def write_png(path,pixels):
    h,w,_=pixels.shape
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    rows=b''.join(b'\0'+row.tobytes() for row in pixels)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b''))


def run(spec,renderer_path,out):
    if out.exists():raise FileExistsError('use a new output directory')
    if not 1<=len(spec['cases'])<=8 or any(type(x)!=int or not 8<=x<=128 for x in spec['resolutions']) or len(spec['resolutions'])>2:raise ValueError('fixture_limit')
    names=[case['id'] for case in spec['cases']]
    if len(set(names))!=len(names) or any(not re.fullmatch(r'[a-z][a-z0-9_]{0,31}',name) for name in names):raise ValueError('case_id')
    loaded=importlib.util.spec_from_file_location('canonical_raster',renderer_path);r=importlib.util.module_from_spec(loaded);loaded.loader.exec_module(r)
    result={'input_version':spec['input_version'],'numpy':np.__version__,'renderer_sha256':hashlib.sha256(renderer_path.read_bytes()).hexdigest(),'cases':[]}
    meshes=[(case['id'],band(case['control'],case['parameters'],case['total_y_width'])) for case in spec['cases']]
    out.mkdir(parents=True)
    for name,mesh in meshes:
        mesh['id']=name;mesh['renders']=[]
        for resolution in spec['resolutions']:
            image,depth=r.render(np.array(mesh['positions']),np.array(mesh['triangles']),np.array(mesh['colors']),np.array(mesh['normals']),model=np.array(spec['model']),width=resolution,height=resolution)
            pixels=np.rint(r.srgb(image)*255).astype(np.uint8);filename=f'{name}_{resolution}.png';write_png(out/filename,pixels)
            mesh['renders'].append({'resolution':resolution,'covered_pixels':int(np.isfinite(depth).sum()),'png':filename,'png_sha256':hashlib.sha256((out/filename).read_bytes()).hexdigest()})
        result['cases'].append(mesh)
    (out/'actual.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--renderer',type=Path,default=Path(__file__).parent/'renderer.py');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();result=run(json.loads(a.spec.read_text()),a.renderer,a.out);print(json.dumps({'cases':len(result['cases']),'renders':sum(len(x['renders']) for x in result['cases'])}))
if __name__=='__main__':main()
