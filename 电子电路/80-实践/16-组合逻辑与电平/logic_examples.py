"""Small explicit digital models. Import uses only standard library, never writes."""
import argparse
import itertools
import json
import math
import numbers
from pathlib import Path


def real(x, name, positive=False):
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        raise ValueError(f'{name} must be a finite real scalar')
    try: x = float(x)
    except (OverflowError, ValueError) as exc: raise ValueError(f'{name} invalid') from exc
    if not math.isfinite(x) or (positive and x <= 0):
        raise ValueError(f'{name} invalid')
    return x


def uint(x, width, name='word'):
    if type(width) is not int or not 1 <= width <= 8:
        raise ValueError('width must be integer 1..8')
    if type(x) is not int or not 0 <= x < 1 << width:
        raise ValueError(f'{name} outside unsigned word')
    return x


def bit(x):
    return uint(x, 1, 'bit')


def signed(x, width):
    uint(x, width)
    return x if x < 1 << (width-1) else x-(1 << width)


def add(a, b, width=4, carry_in=0):
    uint(a,width); uint(b,width); bit(carry_in)
    # Actual ripple structure; no host unbounded sum is used to implement carry.
    result=0; c=carry_in
    for k in range(width):
        if k == width-1: sign_carry=c
        x=(a>>k)&1; y=(b>>k)&1
        result |= (x ^ y ^ c) << k
        c=(x & y) | (c & (x ^ y))
    return {'word': result, 'carry':c,
            'overflow': sign_carry ^ c}


def sub(a,b,width=4):
    uint(a,width);uint(b,width)
    r=add(a,b ^ ((1<<width)-1),width,1)
    r['borrow']=1-r['carry']
    return r


def compare(a,b,width=4):
    r=sub(a,b,width)
    return {'unsigned_lt':r['borrow'],
            'signed_lt': ((r['word']>>(width-1))&1) ^ r['overflow']}


def mux(select,low,high):
    bit(select);bit(low);bit(high)
    return ((1-select)&low)|(select&high)


def priority4(word):
    uint(word,4)
    return {'valid':int(word != 0),'index':word.bit_length()-1 if word else 0}


def decode2(address,enable=1):
    uint(address,2);bit(enable)
    return tuple(int(enable and k==address) for k in range(4))


def hazard_logic(a,b,c,consensus=False):
    bit(a);bit(b);bit(c)
    if type(consensus) is not bool: raise ValueError('consensus must be bool')
    return (a&b)|((1-a)&c)|((b&c) if consensus else 0)


def bcd_ge5(word):
    uint(word,4)
    return ((word>>3)&1)|(((word>>2)&1)&(((word>>1)&1)|(word&1)))


def margins(vdd=3.3,vt=0.6):
    vdd=real(vdd,'vdd',True);vt=real(vt,'vt',True)
    if vdd <= 2*vt: raise ValueError('square-law model needs vdd > 2 vt')
    s=vdd-2*vt
    vil=0.375*vdd+vt/4;vih=vdd-vil
    vol=s/8;voh=vdd-vol
    return dict(vdd=vdd,vt=vt,vil=vil,vih=vih,vol=vol,voh=voh,nml=vil-vol,nmh=voh-vih)


def vtc(vin,vdd=3.3,vt=0.6):
    m=margins(vdd,vt);vdd=m['vdd'];vt=m['vt'];vin=real(vin,'vin')
    if not 0 <= vin <= vdd: raise ValueError('vin outside rails')
    if vin == vdd/2: raise ArithmeticError('lambda=0 model has nonunique DC output at midpoint')
    if vin <= vt: return vdd
    if vin >= vdd-vt: return 0.0
    if vin > vdd/2: return vdd-vtc(vdd-vin,vdd,vt)
    a=vin-vt;b=vdd-vin-vt
    return vdd-b+math.sqrt(b-a)*math.sqrt(b+a)


def charge(t,r=1000.0,c=20e-12,vdd=3.3):
    t=real(t,'t');r=real(r,'r',True);c=real(c,'c',True);vdd=real(vdd,'vdd',True)
    if t<0:raise ValueError('negative t')
    tau=r*c
    if not math.isfinite(tau) or tau<=0:raise ArithmeticError('RC product out of finite positive range')
    return vdd*(-math.expm1(-t/tau))


def power(c=20e-12,vdd=3.3,frequency=10e6,alpha=0.25):
    c=real(c,'c',True);vdd=real(vdd,'vdd',True);frequency=real(frequency,'frequency',True);alpha=real(alpha,'alpha')
    if not 0<=alpha<=1:raise ValueError('alpha assumes at most one 0->1 event per cycle')
    p=alpha*c*vdd*vdd*frequency
    if not math.isfinite(p):raise ArithmeticError('power overflow')
    return p


def pullup_time(vih=2.0,vdd=3.3,r=4700.0,c=100e-12):
    vih=real(vih,'vih');vdd=real(vdd,'vdd',True);r=real(r,'r',True);c=real(c,'c',True)
    if not 0<vih<vdd:raise ValueError('vih must be between rails')
    tau=r*c
    if not math.isfinite(tau) or tau<=0:raise ArithmeticError('RC product out of finite positive range')
    t=-tau*math.log1p(-vih/vdd)
    if not math.isfinite(t):raise ArithmeticError('time overflow')
    return t


def resolve(drivers):
    if not isinstance(drivers,(list,tuple)) or not 1<=len(drivers)<=16:
        raise ValueError('1..16 explicit drivers required')
    if any(type(x) is not str or x not in ('0','1','Z') for x in drivers):
        raise ValueError('driver must be 0, 1 or Z')
    active=set(drivers)-{'Z'}
    return 'X' if len(active)>1 else next(iter(active)) if active else 'Z'


def validate_all(width=4,budget=10000):
    uint(0,width)
    if type(budget) is not int or not 1<=budget<=1000000:raise ValueError('invalid budget')
    required=4*(1<<(2*width))+16+8+8+8+16
    if required>budget:raise ValueError(f'enumeration needs {required} cases, budget {budget}')
    counts={'arithmetic':0,'comparison':0,'boolean':0,'mux':0,'decoder':0,'priority':0,'bcd':0}
    mask=(1<<width)-1;bound=1<<(width-1)
    for a,b in itertools.product(range(1<<width),repeat=2):
        for cin in (0,1):
            r=add(a,b,width,cin);u=a+b+cin;s=signed(a,width)+signed(b,width)+cin
            assert r['word']==u&mask and r['carry']==u>>width
            assert r['overflow']==int(not -bound<=s<bound)
            counts['arithmetic']+=1
        r=sub(a,b,width);s=signed(a,width)-signed(b,width)
        assert r['word']==(a-b)&mask and r['borrow']==int(a<b)
        assert r['overflow']==int(not -bound<=s<bound)
        counts['arithmetic']+=1
        q=compare(a,b,width)
        assert q['unsigned_lt']==int(a<b) and q['signed_lt']==int(signed(a,width)<signed(b,width))
        counts['comparison']+=1
    for a,b,c in itertools.product((0,1),repeat=3):
        assert hazard_logic(a,b,c)==hazard_logic(a,b,c,True)
        counts['boolean']+=1
        assert mux(a,b,c)==(c if a else b);counts['mux']+=1
    for en,a in itertools.product((0,1),range(4)):
        d=decode2(a,en);assert sum(d)==en and (not en or d[a]);counts['decoder']+=1
    for w in range(16):
        e=priority4(w);assert e['valid']==int(w!=0)
        assert not w or ((w>>e['index'])&1 and w < 1<<(e['index']+1))
        counts['priority']+=1
        if w<10:assert bcd_ge5(w)==int(w>=5)
        counts['bcd']+=1
    return counts


def results():
    return {'model':'square law symmetric lambda=0; RC ideal; Boolean transport example',
            'margins_V':margins(),'charge_half_s':1000*20e-12*math.log(2),
            'dynamic_power_W':power(),'open_drain_high_s':pullup_time(),
            'hazard_static_events_ns':[[0,1],[3,0],[6,1]],
            'hazard_dynamic_events_ns':[[0,1],[2,0],[5,1]],
            'arithmetic_cases':{'7+3':add(7,3),'15+1':add(15,1),'3-5':sub(3,5),'15_vs_1':compare(15,1)},
            'enumeration':validate_all()}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();payload=results() # validate before any writing
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':main()
