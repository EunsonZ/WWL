"""Independent finite checks: 3-node solve, polynomial convolution, charge/phase.
Does not import synth_rx or its reused device modules. This is an author check,
not a substitute for the independent reviewer and separately run SPICE.
"""
import argparse
import gzip
import json
import math
from pathlib import Path
import numpy as np

K=1.380649e-23
T=300.15

def close(a,b,rtol=1e-8,atol=1e-12):
    if not np.allclose(a,b,rtol=rtol,atol=atol):raise AssertionError((a,b))

def mul(a,b):
    out={}
    for i,v in a.items():
        for j,w in b.items():out[i+j]=out.get(i+j,0)+v*w
    return out

def verify(path):
    d=json.loads(path.read_text());c=d['input'];p=c['pll'];r=c['rx'];count=0
    # Three explicit physical node equations, without Kron elimination/waves.
    Id=.001;Rs=50.;RD=800.;RL=1000.;beta=.02*10.;lam=.02
    vd=1.8-Id*RD;vs=.1+Id*Rs;vds=vd-vs;ov=math.sqrt(2*Id/(beta*(1+lam*vds)))
    gm=beta*ov*(1+lam*vds);go=beta*ov*ov*lam/2
    noise=[];gains=[]
    for f in [90e6,110e6]:
        s=2j*math.pi*f;cgs=.5e-12+2/3*(3.9*8.854214871e-12)/20e-9*10e-6*1e-6;cgd=.05e-12;cds=.1e-12;co=1e-9
        Y=np.array([[1/Rs+gm+go+s*(cgs+cds),-go-s*cds,0],[-gm-go-s*cds,1/RD+go+s*(cgd+cds+co),-s*co],[0,-s*co,1/RL+s*co]],complex)
        h=np.linalg.solve(Y,[1/Rs,0,0])[2];hc=np.linalg.solve(Y,[1,-1,0])[2];hr=np.linalg.solve(Y,[0,1,0])[2]
        n=(abs(h)**2*4*K*T*Rs+abs(hc)**2*4*K*T*2/3*gm+abs(hr)**2*4*K*T/RD)/RL
        noise.append(n);gains.append(4*Rs/RL*abs(h)**2);count+=1
    q1=2/math.pi;ron=1/(.002*100*(1.8-.6-.5));re=1/(1/1000+1/2e6);eta=re/(re+50+2*ron)
    gmixer=4*50/1000*(eta*q1)**2;hb=1/(1/re+1/(50+2*ron))
    nintern=(eta**2*4*K*T*2*ron+hb**2*4*K*T/2e6)/1000
    nout=100*(gmixer*sum(v+K*T for v in noise)+nintern)+4*100*K*T
    G=gains[1]*gmixer*100;F=nout/(G*K*T)
    rx=d['RX'];close(noise,rx['LNA_band_output_W_per_Hz'],atol=1e-30);close([G,F,nout],[rx['total_gain'],rx['total_F'],rx['output_PSD_W_per_Hz']],atol=1e-30)
    # Exact trig-polynomial coefficients, no waveform projection.
    for row in rx['stress']:
        L=row['preloss'];a1=math.sqrt(gains[1]);a3=-2*a1/(3*r['LNA_IIP3_W']);factor=math.sqrt(gmixer*100)
        def peak(wanted,blocker):
            x={}
            if wanted:
                for k in [11,-11]:x[k]=math.sqrt(2*r['wanted_W']/L)/2
            if blocker:
                for k in [13,-13,15,-15]:x[k]=math.sqrt(2*r['blocker_each_W']/L)/2
            cube=mul(mul(x,x),x);z={k:a1*x.get(k,0)+a3*cube.get(k,0) for k in set(x)|set(cube)}
            return 2*factor*(z.get(1-10,0)+z.get(1+10,0))
        for key,a,b in [('wanted_only_complex_sqrtW',True,False),('blocker_IM3_complex_sqrtW',False,True),('joint_complex_sqrtW',True,True)]:
            close(row[key],[peak(a,b),0],atol=3e-16,rtol=1e-8);count+=1
    maxcharge=0.;maxphase=0.;segments=0
    for name,items in d['dynamics'].items():
        R=next(x['R_ohm'] for x in p['designs'] if x['name']==name)
        for item in items:
            rows=json.loads(gzip.decompress((path.parent/item['trace_file']).read_bytes()))
            assert len(rows)==item['trace_rows']
            for a,b in zip(rows,rows[1:]):
                dt=b[0]-a[0];rate=a[3]*p['Icp_A']/p['C_F'];u=a[1]+a[3]*p['Icp_A']*R
                maxcharge=max(maxcharge,abs((b[1]-a[1])-rate*dt))
                # Integral of clip(u+rate*t), independent antiderivative.
                lo,hi=p['tune_limits_V']
                def primitive(v):
                    if v<lo:return lo*v
                    if v<=hi:return .5*(v*v+lo*lo)
                    return hi*v-.5*(hi*hi-lo*lo)
                iu=(primitive(u+rate*dt)-primitive(u))/rate if rate else min(hi,max(lo,u))*dt
                phase=(p['center_Hz']*dt+p['Kv_Hz_per_V']*(iu-p['center_voltage_V']*dt))/p['N']
                maxphase=max(maxphase,abs((b[2]-a[2])-phase));segments+=1
                if b[4] in ['feedback','both']:close(b[2],round(b[2]),atol=1e-10)
                if b[4] in ['ref','both']:close(b[0]*item['initial']['reference_Hz'],round(b[0]*item['initial']['reference_Hz']),atol=2e-8)
                if b[4]=='both':assert b[3]==0
    assert maxcharge<3e-12 and maxphase<3e-8,(maxcharge,maxphase)
    # Spectrum via explicit two-state response matrix, dense independent trap.
    for design in p['designs']:
        R=design['R_ohm'];I=p['Icp_A'];kv=2*math.pi*p['Kv_Hz_per_V'];kd=I/(2*math.pi)
        # x=(phi_out,z); xdot=A x + Br phi_ref; output additive VCO phase
        # transfer follows s/(s²+a*s+b) times disturbance derivative.
        A=np.array([[-kv*kd*R/p['N'],kv],[-kd/(p['N']*p['C_F']),0.]])
        Br=np.array([kv*kd*R,kd/p['C_F']]);spec=d['PLL'][design['name']]
        close(np.sort_complex(np.linalg.eigvals(A)),np.sort_complex([complex(*z) for z in spec['roots_per_s']]),atol=1e-7)
        ff=np.geomspace(*c['noise']['integration_Hz'],50001);parts=[]
        for f in ff:
            s=2j*math.pi*f;hr=np.linalg.solve(s*np.eye(2)-A,Br)[0];hv=np.linalg.solve(s*np.eye(2)-A,[s,0])[0]
            n=c['noise'];sr=n['reference_white']+n['reference_flicker']/f;sv=n['vco_white']+n['vco_inverse_square']/f**2+n['vco_inverse_cube']/f**3;parts.append([abs(hr)**2*sr,abs(hv)**2*sv])
        var=np.trapezoid(parts,ff,axis=0);close(var,spec['phase_variance_parts_rad2'],rtol=2e-8,atol=1e-18);count+=1
    return {'PASS':True,'independent_3node_and_polynomial_spectrum_cases':count,'charge_phase_segments':segments,'maximum_charge_identity_error_V':maxcharge,'maximum_integrated_phase_error_cycles':maxphase,'methods':'3x3 KCL; exact polynomial convolution; clipped-ramp antiderivative; 2-state resolvent + 50001 log-grid trapezoid; no core import'}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--results',type=Path,required=True);a.add_argument('--out',type=Path,required=True);z=a.parse_args()
    if z.out.exists() or z.out.is_symlink():a.exit(2,'fresh output required\n')
    report=verify(z.results);z.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
