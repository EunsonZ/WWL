"""Finite SI teaching models; all frequencies in rad/s; import has no effects."""
import math
import numpy as np


def real(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int,float)):
        raise ValueError('finite real required')
    try: value=float(value)
    except OverflowError as exc: raise ValueError('outside float range') from exc
    if not math.isfinite(value) or (positive and value<=0):
        raise ValueError('finite positive required' if positive else 'finite real required')
    return value


def finite(value):
    if not np.all(np.isfinite(value)): raise ValueError('derived value outside range')
    return value


def rc_h(omega_rad_s, r_ohm=1000., c_F=1e-6):
    w=real(omega_rad_s);r=real(r_ohm,True);c=real(c_F,True)
    tau=r*c
    if not 0<tau<math.inf: raise ValueError('time constant outside range')
    scaled=w*tau
    if not math.isfinite(scaled): raise ValueError('scaled frequency outside range')
    return 1/complex(1,scaled)


def rc_started_cosine(time_s, omega_rad_s=1000., initial_V=.4):
    """Unit peak volt input cos(wt), switched on at t=0; fixed 1 ms RC."""
    t=real(time_s);w=real(omega_rad_s);v0=real(initial_V)
    if t<0: raise ValueError('time must be nonnegative')
    phase=t*w
    if not math.isfinite(phase): raise ValueError('phase outside range')
    h=rc_h(w);decay=math.exp(-1000*t);rise=-math.expm1(-1000*t)
    change=-2*h.real*math.sin(phase/2)**2-h.imag*math.sin(phase)
    return finite(v0*decay+h.real*rise+change)


def db_phase(value):
    finite(value)
    magnitude=math.hypot(value.real,value.imag)
    if magnitude==0 or not math.isfinite(magnitude):
        raise ValueError('magnitude has no finite dB or unique phase')
    return 20*math.log10(magnitude),math.degrees(math.atan2(value.imag,value.real))


def rc_asymptotic_db(omega_rad_s):
    w=real(omega_rad_s,True)
    return -20*max(0.,math.log10(w/1000.))


def second_order_h(omega_rad_s, natural_rad_s=10000., damping=.25):
    w=real(omega_rad_s);wn=real(natural_rad_s,True);zeta=real(damping,True)
    ratio=w/wn
    denominator=complex(1-ratio*ratio,2*zeta*ratio)
    finite(denominator)
    if denominator==0:raise ValueError('singular frequency')
    return 1/denominator


def zero_pair_h(omega_rad_s, right_half_plane=False):
    """Stable proper example (1 +/- s/1000)/(1+s/10000)."""
    w=real(omega_rad_s)
    return finite(complex(1,(-1 if right_half_plane else 1)*w/1000)/complex(1,w/10000))


def rlc_physical(r_ohm=50., l_H=.01, c_F=1e-6):
    r=real(r_ohm,True);l=real(l_H,True);c=real(c_F,True)
    A=np.array([[0.,1/c],[-1/l,-r/l]])
    B=np.array([[0.],[1/l]]);C=np.array([[1.,0.]]);D=np.zeros((1,1))
    for matrix in (A,B,C,D):finite(matrix)
    return A,B,C,D


def rlc_normalized():
    # x=[v/1V, i/.01A], u/1V, y/1V; every A/B entry is per second.
    return (np.array([[0.,10000.],[-10000.,-5000.]]),
            np.array([[0.],[10000.]]),np.array([[1.,0.]]),np.zeros((1,1)))


def hidden_model(kind='unobservable'):
    if kind not in ('unobservable','uncontrollable'):raise ValueError('unknown kind')
    A=np.diag([-1000.,1000.]);D=np.zeros((1,1))
    if kind=='unobservable': B=np.array([[1000.],[1000.]]);C=np.array([[1.,0.]])
    else: B=np.array([[1000.],[0.]]);C=np.array([[1.,1.]])
    return A,B,C,D


def validated_model(model):
    raw=[np.asarray(m) for m in model]
    # Reject complex dtype before any cast; even zero imaginary parts are a
    # different supplied contract. Object arrays need an explicit scalar check.
    if any(np.iscomplexobj(m) or (m.dtype==object and any(isinstance(v,(complex,np.complexfloating)) for v in m.flat)) for m in raw):
        raise ValueError('A/B/C/D must be real matrices')
    try: A,B,C,D=(np.asarray(m,dtype=float) for m in raw)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('real numeric A/B/C/D required') from exc
    if A.ndim!=2 or A.shape[0]!=A.shape[1] or not A.shape[0]:raise ValueError('A must be nonempty square')
    n=A.shape[0]
    if B.ndim!=2 or C.ndim!=2 or D.ndim!=2 or B.shape[0]!=n or C.shape[1]!=n or D.shape!=(C.shape[0],B.shape[1]):
        raise ValueError('incompatible A/B/C/D shapes')
    for m in (A,B,C,D):finite(m)
    return A,B,C,D


def port_h(omega_rad_s, model):
    w=real(omega_rad_s);A,B,C,D=validated_model(model)
    try: result=C@np.linalg.solve(1j*w*np.eye(A.shape[0])-A,B)+D
    except np.linalg.LinAlgError as exc:raise ValueError('singular resolvent') from exc
    return finite(result)


def rank_matrices(model):
    A,B,C,D=validated_model(model);n=A.shape[0]
    powers=[np.linalg.matrix_power(A,k) for k in range(n)]
    reach=np.hstack([p@B for p in powers]);observe=np.vstack([C@p for p in powers])
    finite(reach);finite(observe)
    return reach,observe
