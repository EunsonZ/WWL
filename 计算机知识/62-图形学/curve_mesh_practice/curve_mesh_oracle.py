"""Independent polynomial/Fraction geometry and direct planar pixel oracle; no generator import."""
import argparse
from collections import Counter
from fractions import Fraction as Q
import json,math,struct,zlib
from pathlib import Path


def close(a,b,tol=1e-12):
    if isinstance(a,list):assert len(a)==len(b);[close(x,y,tol) for x,y in zip(a,b)]
    else:assert abs(float(a)-float(b))<=tol,(a,b)


def read_png(path):
    data=path.read_bytes();offset=8;compressed=b'';size=None
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    while offset<len(data):
        n=struct.unpack('!I',data[offset:offset+4])[0];kind=data[offset+4:offset+8];payload=data[offset+8:offset+8+n]
        if kind==b'IHDR':w,h,depth,color,*_=struct.unpack('!IIBBBBB',payload);assert depth==8 and color==2;size=(w,h)
        if kind==b'IDAT':compressed+=payload
        offset+=n+12
    raw=zlib.decompress(compressed);w,h=size;rows=[]
    for j in range(h):
        row=raw[j*(1+3*w):(j+1)*(1+3*w)];assert row[0]==0;rows.append([list(row[1+3*i:4+3*i]) for i in range(w)])
    return rows


def verify(spec,actual,folder):
    report=[]
    for case,observed in zip(spec['cases'],actual['cases'],strict=True):
        p=[[Q(str(x)) for x in row] for row in case['control']];ts=[Q(str(t)) for t in case['parameters']];width=Q(str(case['total_y_width']));N=len(ts)-1
        coeff=[[p[0][k],2*(p[1][k]-p[0][k]),p[0][k]-2*p[1][k]+p[2][k]] for k in range(3)]
        def evaluate(t):return [c[0]+c[1]*t+c[2]*t*t for c in coeff]
        expected=[evaluate(t) for t in ts];close(expected,observed['curve_points'])
        close([[2*(p[1][k]-p[0][k]) for k in range(3)],[2*(p[2][k]-p[1][k]) for k in range(3)]],observed['endpoint_tangents'])
        vertices=[[point[0],point[1]+sign*width/2,point[2]] for point in expected for sign in (-1,1)];close(vertices,observed['positions'])
        assert observed['normals']==[[0.,0.,1.]]*len(vertices)
        edge=Counter();faces=observed['triangles']
        for a,b,c in faces:
            assert len({a,b,c})==3 and min(a,b,c)>=0 and max(a,b,c)<len(vertices)
            ax,ay,_=vertices[a];bx,by,_=vertices[b];cx,cy,_=vertices[c]
            assert (bx-ax)*(cy-ay)-(by-ay)*(cx-ax)>0
            edge.update(tuple(sorted(e)) for e in [(a,b),(b,c),(c,a)])
        top=observed['topology'];assert [top[k] for k in ['V','E','F','chi','boundary_count']]==[2*N+2,4*N+1,2*N,1,2*N+2]
        assert sorted(tuple(x) for x in top['boundary_edges'])==sorted(e for e,n in edge.items() if n==1)
        assert set(edge.values())<={1,2}
        for i,row in enumerate(top['face_neighbors']):assert row==[j for j,f in enumerate(faces) if j!=i and len(set(f)&set(faces[i]))==2]
        error_max=0.
        for (lo,hi),e in zip(zip(ts[:-1],ts[1:]),observed['interval_errors'],strict=True):
            exact=math.sqrt(sum(float(c[2])**2 for c in coeff))*float((hi-lo)**2)/4
            close(exact,e['exact_matched_parameter_max']);close(exact,e['midpoint_error']);error_max=max(error_max,exact)
        close(error_max,observed['exact_matched_parameter_max'])
        pixels=[]
        for render in observed['renders']:
            R=render['resolution'];image=read_png(folder/render['png']);checked=edges=0;covered=sum(any(v for v in pix) for row in image for pix in row)
            assert covered==render['covered_pixels']
            for j,row in enumerate(image):
                for i,pixel in enumerate(row):
                    # Invert the fixed view/projection at z=-3; no rasterizer call.
                    x=3*(2*(i+.5)/R-1)+1;y=3*(1-2*(j+.5)/R)+.5;t=x/2
                    if not 0<t<1:
                        assert pixel==[0,0,0];checked+=1;continue
                    interval=next(k for k in range(N) if float(ts[k])<=t<=float(ts[k+1]))
                    lo,hi=map(float,ts[interval:interval+2]);u=(t-lo)/(hi-lo);height=float(expected[interval][1])*(1-u)+float(expected[interval+1][1])*u
                    distance=abs(y-height)-float(width)/2
                    if abs(distance)<1e-10:edges+=1;continue  # original top-left rule is tested elsewhere
                    if distance>0:assert pixel==[0,0,0]
                    else:
                        color=[.2+.6*t,.4,1-.6*t];encoded=[round(255*(12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055)) for v in color]
                        assert max(abs(a-b) for a,b in zip(pixel,encoded))<=1,(case['id'],i,j,pixel,encoded)
                    checked+=1
            pixels.append({'resolution':R,'checked_nonboundary_pixels':checked,'excluded_exact_boundary_pixels':edges,'covered_pixels':covered})
        report.append({'id':case['id'],'exact_error':error_max,'pixels':pixels})
    return {'status':'PASS','geometry_absolute_tolerance':1e-12,'display_byte_tolerance':1,'cases':report,'scope':'fixed XY strip + fixed model; no generator/renderer import, no generic image oracle'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--actual',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=verify(json.loads(a.spec.read_text()),json.loads(a.actual.read_text()),a.actual.parent);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'cases':len(r['cases'])}))
if __name__=='__main__':main()
