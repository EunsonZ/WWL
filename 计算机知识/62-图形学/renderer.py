"""CPU teaching rasterizer: RH, column vectors, camera -Z, GL-style clip.
Run: python -B renderer.py; requires NumPy. No GPU/API conformance claim.
"""
from pathlib import Path
import json
import struct
import zlib
import numpy as np


def finite(value, shape=None):
    a = np.asarray(value, dtype=float)
    if (shape is not None and a.shape != shape) or not np.isfinite(a).all():
        raise ValueError('invalid shape or nonfinite input')
    return a


def unit(v):
    a = finite(v, (3,))
    length = np.linalg.norm(a)
    if not np.isfinite(length) or length < 1e-12:
        raise ValueError('zero or numerically invalid direction')
    return a / length


def affine(m):
    m = finite(m, (4, 4))
    if not np.array_equal(m[3], [0, 0, 0, 1]):
        raise ValueError('expected affine matrix')
    return m


def perspective(near=1., far=9., fovy=np.pi/2, aspect=1.):
    p = finite([near, far, fovy, aspect])
    if not (0 < near < far and 0 < fovy < np.pi and aspect > 0):
        raise ValueError('invalid frustum')
    s = 1 / np.tan(p[2]/2)
    return finite(np.array([[s/aspect,0,0,0],[0,s,0,0],
                     [0,0,-(far+near)/(far-near),-2*far*near/(far-near)],
                     [0,0,-1,0]], float))


def normal_matrix(m):
    linear = affine(m)[:3,:3]
    if np.linalg.cond(linear) > 1e12:
        raise ValueError('singular or ill-conditioned normal transform')
    return np.linalg.inv(linear).T


# Packed vertex = clip xyzw, linear-light RGB, unnormalized view normal.
PLANES = np.array([[1,0,0,1],[-1,0,0,1],[0,1,0,1],
                   [0,-1,0,1],[0,0,1,1],[0,0,-1,1]], float)


def clip_polygon(vertices):
    poly = finite(vertices)
    if poly.ndim != 2 or poly.shape[1] != 10:
        raise ValueError('packed vertices require shape (N,10)')
    for plane in PLANES:
        out = []
        if len(poly) == 0:
            break
        prev = poly[-1]
        dp = prev[:4] @ plane
        for curr in poly:
            dc = curr[:4] @ plane
            if (dp >= 0) != (dc >= 0):
                t = dp / (dp-dc)
                out.append(prev + t*(curr-prev))
            if dc >= 0:
                out.append(curr.copy())
            prev, dp = curr, dc
        poly = finite(np.array(out, float).reshape(-1, 10))
    return poly


def edge(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])


def top_left(a, b):
    dx, dy = b[:2]-a[:2]
    return dy < 0 or (dy == 0 and dx > 0)  # screen Y down, positive area


def samples(screen, width, height):
    """Yield (x,y,barycentric) at half-integer centers. No epsilon edge bias."""
    s = finite(screen, (3, 2))
    area = edge(s[0], s[1], s[2])
    if area <= 1e-12:
        return
    low = np.maximum(0, np.ceil(s.min(axis=0)-.5)).astype(int)
    high = np.minimum([width-1,height-1], np.floor(s.max(axis=0)-.5)).astype(int)
    pairs = [(s[1],s[2]),(s[2],s[0]),(s[0],s[1])]
    for y in range(low[1], high[1]+1):
        for x in range(low[0], high[0]+1):
            es = np.array([edge(a,b,[x+.5,y+.5]) for a,b in pairs])
            if all(e > 0 or (e == 0 and top_left(a,b)) for e,(a,b) in zip(es,pairs)):
                yield x,y,es/area


def interpolate(lam, w, attributes):
    lam, w, a = finite(lam,(3,)), finite(w,(3,)), finite(attributes)
    if a.ndim != 2 or a.shape[0] != 3 or np.any(w <= 0):
        raise ValueError('invalid attributes or nonpositive w')
    if np.any(lam < 0) or not np.isclose(lam.sum(),1):
        raise ValueError('invalid barycentric weights')
    q = lam / w
    if not np.isfinite(q).all() or not np.isfinite(q.sum()) or q.sum() <= 0:
        raise ValueError('invalid perspective denominator')
    return finite((q @ a) / q.sum())


def render(positions, triangles, colors, normals, model=None, view=None,
           projection=None, width=64, height=64, light=(0,0,1)):
    if not isinstance(width,int) or not isinstance(height,int) or not (1 <= width <= 2048 and 1 <= height <= 2048):
        raise ValueError('invalid image dimensions')
    pos = finite(positions)
    if pos.ndim != 2 or pos.shape[1] != 3:
        raise ValueError('positions require shape (N,3)')
    color, normal = finite(colors, pos.shape), finite(normals, pos.shape)
    if np.any(color < 0) or np.any(color > 1):
        raise ValueError('linear RGB outside [0,1]')
    for n in normal:
        unit(n)
    tri = np.asarray(triangles)
    if tri.ndim != 2 or tri.shape[1] != 3 or tri.dtype.kind not in 'iu' or np.any(tri < 0) or np.any(tri >= len(pos)):
        raise ValueError('invalid triangle indices')
    model = affine(np.eye(4) if model is None else model)
    view = affine(np.eye(4) if view is None else view)
    projection = finite(perspective() if projection is None else projection,(4,4))
    mv = view @ model
    nm = normal_matrix(mv)
    clip = (projection @ mv @ np.column_stack([pos,np.ones(len(pos))]).T).T
    packed = finite(np.column_stack([clip,color,(nm @ normal.T).T]))
    image = np.zeros((height,width,3))
    depth = np.full((height,width),np.inf)
    light = unit(light)
    for ids in tri:
        polygon = clip_polygon(packed[ids])
        for i in range(1,len(polygon)-1):
            v = polygon[[0,i,i+1]].copy()
            w = v[:,3]
            if np.any(w <= 1e-12):
                raise ValueError('projection produced invalid surviving w')
            ndc = v[:,:3]/w[:,None]
            screen = np.column_stack([(ndc[:,0]+1)*width/2,(1-ndc[:,1])*height/2])
            if edge(screen[0],screen[1],screen[2]) < 0:
                v = v[[0,2,1]]; w = w[[0,2,1]]; ndc = ndc[[0,2,1]]; screen = screen[[0,2,1]]
            for x,y,lam in samples(screen,width,height):
                z = (lam @ ndc[:,2]+1)/2  # NDC depth is affine in screen!
                if z < depth[y,x]:
                    a = interpolate(lam,w,v[:,4:])
                    n = unit(a[3:])
                    intensity = .1 + .9*max(0., n @ light)
                    image[y,x] = a[:3]*intensity
                    depth[y,x] = z
    return image,depth


def srgb(linear):
    a = finite(linear)
    if np.any(a < 0) or np.any(a > 1):
        raise ValueError('RGB outside display range')
    return np.where(a <= .0031308,12.92*a,1.055*a**(1/2.4)-.055)


def demo(output=None):
    root = Path(__file__).parent if output is None else Path(output)
    root.mkdir(parents=True,exist_ok=True)
    p = np.array([[-1,-1,0],[2,-2,-2],[0,1,0],[-2,-2,-3],[2,-2,-3],[0,2,-3]],float)
    m = np.eye(4); m[2,3] = -2
    n = unit(np.cross(p[1]-p[0],p[2]-p[0]))
    normals = np.array([n,n,n,[0,0,1],[0,0,1],[0,0,1]])
    c = np.array([[1,0,0],[0,1,0],[0,0,1],[.5,.5,.5],[.5,.5,.5],[.5,.5,.5]])
    image,depth = render(p,np.array([[3,4,5],[0,1,2]]),c,normals,model=m)
    pixels = np.rint(srgb(image)*255).astype(np.uint8)
    with (root/'assets'/'graphics-render.ppm').open('wb') as f:
        f.write(b'P6\n64 64\n255\n'); f.write(pixels.tobytes())
    def chunk(kind, data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    rows = b''.join(b'\x00'+row.tobytes() for row in pixels)
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',64,64,8,2,0,0,0))
    png += chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b'')
    (root/'assets'/'graphics-render.png').write_bytes(png)
    clip = (perspective() @ m @ np.column_stack([p[:3],np.ones(3)]).T).T
    ndc = clip[:,:3]/clip[:,3,None]
    result = {'object':p[:3].tolist(),'world_view':(p[:3]+[0,0,-2]).tolist(),
              'clip':clip.round(8).tolist(),'ndc':ndc.round(8).tolist(),
              'viewport':np.column_stack([(ndc[:,0]+1)*32,(1-ndc[:,1])*32]).round(8).tolist(),
              'covered_pixels':int(np.isfinite(depth).sum()),'pixel_32_32_linear':image[32,32].tolist(),
              'pixel_32_32_depth':float(depth[32,32])}
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    demo()
