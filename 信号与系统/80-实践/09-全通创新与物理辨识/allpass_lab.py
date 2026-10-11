#!/usr/bin/env python3
"""Exact all-pass probes, using only stdlib; no stationary-law Monte Carlo claim."""
import argparse
import csv
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys


def h(a, k):
    return -a if k == 0 else (1-a*a)*a**(k-1)


def gaussian_r(a, lag, cutoff):
    """Finite convolution sum plus exact geometric tail, not truncated covariance."""
    prefix = sum((h(a,j)*h(a,j+lag) for j in range(cutoff)), F(0))
    tail = (1-a*a)*a**(2*cutoff+lag-2)
    return prefix+tail, prefix, tail


def ratio_at_quarter(a):
    # (-a-i)/(1+ai): exact pair of real and imaginary parts.
    return -2*a/(1+a*a), -(1-a*a)/(1+a*a)


def div_pair(n, d):
    norm=d[0]*d[0]+d[1]*d[1]
    return ((n[0]*d[0]+n[1]*d[1])/norm,
            (n[1]*d[0]-n[0]*d[1])/norm)


def dump_csv(path, rows):
    with path.open('w', newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader()
        writer.writerows(rows)


def svg(data_path, dest, selected_a, V0, npts):
    # The plotted points are re-read from the delivered CSV, not recomputed.
    with data_path.open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    rows=[r for r in rows if r['a']==selected_a]
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 790" role="img" aria-labelledby="title desc">',
         '<title id="title">Same input probes and different observation objects</title>',
         '<desc id="desc">Top: fixed 4-periodic input on all integer times, identity and all-pass outputs. Middle: exact stationary Gaussian covariance, equal for both systems. Bottom: zero-state Gaussian startup variance, unequal to stationary variance. Every point is read from same-data.csv; no random simulated law.</desc>',
         '<rect width="920" height="790" fill="#fff"/>',
         '<g font-family="Arial,sans-serif" font-size="15" fill="#182333">',
         f'<text x="35" y="28" font-size="21">Same data, three questions (a = {selected_a}, V0 = {V0} V)</text>']
    configs=[('periodic-input',70,170,[('u_V','#204da8','2 4'),('identity_x_V','#204da8',''),('allpass_x_V','#b84023','7 4')],-float(V0),float(V0),'Fixed periodic input and synchronized outputs / V'),
             ('stationary-covariance',340,100,[('stationary_r_V2','#267447','')],0,float(V0*V0),'Stationary Gaussian covariance, both models / V^2'),
             ('startup-variance',540,100,[('zero_state_variance_V2','#b84023',''),('stationary_variance_V2','#267447','5 4')],0,float(V0*V0),'Zero-state startup variance versus stationary / V^2')]
    for kind,y0,height,fields,vmin,vmax,title in configs:
        pts=[r for r in rows if r['kind']==kind]; xmax=max(int(r['index']) for r in pts)
        px=lambda n:85+780*n/max(1,xmax)
        py=lambda v:y0+height-(v-vmin)/(vmax-vmin)*height
        out.extend([f'<text x="35" y="{y0-13}" font-size="17">{title}</text>',
                    f'<path d="M85 {y0} V{y0+height} H865" fill="none" stroke="#7d8998"/>'])
        if vmin<0: out.append(f'<path d="M85 {py(0)} H865" stroke="#ced3db"/>')
        for v in [vmin,vmax]:out.append(f'<text x="42" y="{py(v)+5}">{v:g}</text>')
        for field,color,dash in fields:
            coords=[(px(int(r['index'])),py(float(F(r[field])))) for r in pts]
            out.append(f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x,y in coords)}" fill="none" stroke="{color}" stroke-width="2.5" stroke-dasharray="{dash}"/>')
            for x,y in coords:out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.3" fill="{color}"/>')
        out.append(f'<text x="800" y="{y0-13}">n / lag</text>')
        for k in range(0,xmax+1,max(1,xmax//4)):
            out.append(f'<text x="{px(k)-5:.1f}" y="{y0+height+21}">{k}</text>')
    out.extend([f'<text x="100" y="290">Blue: input = identity x. Orange dashed: all-pass x. {npts} samples; periodic prehistory.</text>',
                f'<text x="100" y="490">Green: r[0] = {V0*V0} V^2; every nonzero lag = 0 (exact infinite-tail sum).</text>',
                '<text x="100" y="695">Orange: V0^2 [1 - (1-a^2) a^(2n)]. Dashed green: stationary variance = V0^2.</text>',
                '<text x="100" y="735">Deterministic probes and exact moments do not prove Gaussian equality by simulation.</text>',
                '</g></svg>'])
    dest.write_text('\n'.join(out)+'\n',encoding='utf-8')


def check(condition, message):
    if not condition:
        raise ArithmeticError(message)


def read_spec(inputs):
    spec=json.loads(inputs.read_text())
    if not isinstance(spec, dict):
        raise ValueError('input must be a JSON object')
    def fraction(key, value):
        if not isinstance(value, str):
            raise ValueError(f'{key} must be a rational string')
        try:
            result=F(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f'{key} must be a valid rational string') from exc
        if max(abs(result.numerator).bit_length(),result.denominator.bit_length())>16:
            raise ValueError(f'{key} numerator and denominator must fit 16 bits')
        return result
    def count(key, low, high):
        value=spec.get(key)
        if type(value) is not int or not low<=value<=high:
            raise ValueError(f'{key} must be an integer in {low}..{high}')
        return value
    av=spec.get('a_values')
    if not isinstance(av,list) or not 1<=len(av)<=8:
        raise ValueError('a_values must be a nonempty list of at most eight rational strings')
    params=[fraction('a_values',v) for v in av]
    if any(not 0<a<1 for a in params):
        raise ValueError('all a_values must lie strictly between zero and one')
    if len(set(params))!=len(params):
        raise ValueError('a_values must be distinct after rational normalization')
    pv=spec.get('periodic_u_over_V0')
    if not isinstance(pv,list) or len(pv)!=4:
        raise ValueError('periodic_u_over_V0 must contain four rational strings')
    period=[fraction('periodic_u_over_V0',v) for v in pv]
    if period!=[F(1),F(0),F(-1),F(0)]:
        raise ValueError('this probe requires periodic_u_over_V0 = ["1","0","-1","0"]')
    V0=fraction('unit_V',spec.get('unit_V')); fs=fraction('sampling_rate_Hz',spec.get('sampling_rate_Hz'))
    if V0<=0 or fs<=0:
        raise ValueError('unit_V and sampling_rate_Hz must be strictly positive')
    return spec,params,count('impulse_indices',1,64),count('covariance_lags',1,64),count('periodic_record_samples',4,256),period,V0,fs


def run(inputs, output):
    spec,params,count,lags,npts,period,V0,fs=read_spec(inputs)
    output.mkdir(parents=True,exist_ok=True)
    rows=[]; reports=[]
    for a in params:
        text=str(a)
        covs=[gaussian_r(a,m,count) for m in range(lags)]
        check([r[0] for r in covs]==[F(1)]+[F(0)]*(lags-1), 'covariance check failed')
        re,im=ratio_at_quarter(a)
        check((re,im)==div_pair((-a,F(-1)),(F(1),a)) and re*re+im*im==1, 'complex ratio check failed')
        # Independent exact four-periodic recurrence solve: -i transfer action
        # is x[n]=Re(G)*cos(n*pi/2)-Im(G)*sin(n*pi/2).
        periodic=[re,-im,-re,im]
        for n in range(npts):
            u=period[n%4]*V0; x=periodic[n%4]*V0
            check(x == a*periodic[(n-1)%4]*V0+period[(n-1)%4]*V0-a*u, 'periodic recurrence check failed')
            rows.append(dict(a=text,kind='periodic-input',index=n,u_V=str(u),identity_x_V=str(u),allpass_x_V=str(x),stationary_r_V2='',zero_state_variance_V2='',stationary_variance_V2=''))
        for m,(value,prefix,tail) in enumerate(covs):
            rows.append(dict(a=text,kind='stationary-covariance',index=m,u_V='',identity_x_V='',allpass_x_V='',stationary_r_V2=str(value*V0**2),zero_state_variance_V2='',stationary_variance_V2=''))
        for n in range(npts):
            v=sum((h(a,k)**2 for k in range(n+1)),F(0))
            check(v==1-(1-a*a)*a**(2*n), 'startup variance check failed')
            rows.append(dict(a=text,kind='startup-variance',index=n,u_V='',identity_x_V='',allpass_x_V='',stationary_r_V2='',zero_state_variance_V2=str(v*V0**2),stationary_variance_V2=str(V0**2)))
        fourth_sum=a**4+(1-a*a)**4/(1-a**4)
        fourth=3-2*fourth_sum
        # Direct sum first overlap + geometric tail, independently simplify.
        cross_sum=h(a,1)*h(a,0)**3+(1-a*a)**4*a/(1-a**4)
        check(cross_sum==a*(1-a*a)*(1-3*a*a)/(1+a*a), 'fourth moment check failed')
        reports.append(dict(a=text,impulse=[str(h(a,k)) for k in range(count)],pole_z=str(a),zero_z=str(1/a),inverse_causal_pole_z=str(1/a),
             stationary_variance_V2=str(V0**2),stationary_covariance_V2=[str(r[0]*V0**2) for r in covs],
             covariance_prefix=[str(r[1]) for r in covs],covariance_exact_tail=[str(r[2]) for r in covs],
             impulse_crop_missing_energy=str((1-a*a)*a**(2*count-2)),
             cross_ratio_pi_2=[str(re),str(im)],reverse_cross_ratio_pi_2=[str(re),str(-im)],
             magnitude_squared_coherence='1',normalized_outer_F='1',physical_u_given_x_past_conditional_variance_V2=str((1-a*a)*V0**2),
             rademacher_normalized_fourth_moment_identity='1',rademacher_normalized_fourth_moment_allpass=str(fourth),
             rademacher_cross_cubic_moment=str(-2*cross_sum),
             gaussian_Hz_PSD_V2_per_Hz=str(V0**2/fs)))
    dump_csv(output/'same-data.csv',rows)
    report={'python':sys.version,'fixed_input_sha256':hashlib.sha256(inputs.read_bytes()).hexdigest(),
            'arithmetic':'Fraction; exact tails. SVG coordinates only use floats.',
            'claim_boundary':'No finite random stationary-law simulation; Gaussian finite-dimensional law follows analytic proof in Wiener03.',
            'plot_model_a':str(params[0]),'unit_V':str(V0),'sampling_rate_Hz':str(fs),'periodic_record_samples':npts,'models':reports}
    (output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    svg(output/'same-data.csv',output/'same-data.svg',str(params[0]),V0,npts)
    print(json.dumps({'a_values':spec['a_values'],'checks':'exact covariance, impulse tail, complex quotient, periodic recurrence, startup variance, fourth moments passed','rows':len(rows)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,default=Path(__file__).with_name('fixed-inputs.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        run(args.inputs,args.output)
    except ValueError as exc:
        parser.error(str(exc))
