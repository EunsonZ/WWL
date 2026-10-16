#!/usr/bin/env python3
"""Same finite voltage record: reuse canonical Haar/STFT; threshold truth and toy byte codec."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import struct
import sys
import time

HEADER = struct.Struct('<4sHHIdI')
PAIR = struct.Struct('<Hh')


def require(ok, message):
    if not ok: raise ValueError(message)


def finite(x):
    return type(x) in (int,float) and math.isfinite(x)


def power2(n):
    return type(n) is int and n > 0 and n & (n-1) == 0


def validate(c):
    require(type(c) is dict, 'input object required')
    n=c.get('length');fs=c.get('sample_rate_Hz');j=c.get('haar_levels')
    require(power2(n) and 64<=n<=256, 'power-of-two length in [64,256] required')
    require(type(fs) is int and 1<=fs<=1000000, 'integer sample_rate_Hz in [1,1000000] required')
    require(type(j) is int and 1<=j<=int(math.log2(n)), 'valid integer Haar levels required')
    for k in ('trend_start_V','trend_end_V','edge_height_V','pulse_height_V'):
        require(finite(c.get(k)) and abs(c[k])<=2, 'finite voltage components <=2V required')
    for k in ('edge_index','pulse_index'):
        require(type(c.get(k)) is int and 0<=c[k]<n, 'feature indices in original record required')
    require(finite(c.get('noise_sigma_V')) and 0<=c['noise_sigma_V']<=.2, 'noise sigma in [0,.2]V required')
    require(finite(c.get('threshold_sigma_multiple')) and 0<=c['threshold_sigma_multiple']<=10, 'threshold multiple in [0,10] required')
    require(finite(c.get('quantization_step_V')) and .01<=c['quantization_step_V']<=1, 'q in [.01,1]V required')
    cases=c.get('noise_cases')
    require(type(cases) is list and 1<=len(cases)<=2, 'one or two fixed noise cases required')
    labels=[]
    for q in cases:
        require(type(q) is dict and type(q.get('seed')) is int and 0<=q['seed']<2**32, 'uint32 noise label required')
        require(type(q.get('signs')) is str and len(q['signs'])==n and set(q['signs'])<=set('+-'), 'one fixed sign per sample required')
        labels.append(q['seed'])
    require(len(set(labels))==len(labels), 'distinct noise labels required')
    cfgs=c.get('stft')
    require(type(cfgs) is list and 1<=len(cfgs)<=2, 'one or two STFT configurations required')
    seen=[]
    for q in cfgs:
        require(type(q) is dict, 'STFT config object required')
        L,H,F=q.get('window_length'),q.get('hop'),q.get('nfft')
        require(power2(L) and 8<=L<=min(64,n), 'power-of-two window length in [8,min(64,N)] required')
        require(type(H) is int and H in (L//4,L//2), 'hop must be L/4 or L/2')
        require(power2(F) and L<=F<=64, 'power-of-two nfft in [L,64] required')
        seen.append((L,H,F))
    require(len(set(seen))==len(seen), 'distinct STFT configs required')
    require(type(c.get('mel_bands')) is int and 2<=c['mel_bands']<=6, '2..6 Mel bands required')
    require(finite(c.get('mel_floor_V2')) and 0<c['mel_floor_V2']<=1e-6, 'positive display Mel floor <=1e-6 V2 required')
    h=c.get('feature_halfwidth_samples')
    require(type(h) is int and 1<=h<=16, 'integer feature halfwidth in [1,16] required')


def load(path,name):
    path=Path(path).resolve();require(path.is_file(),'published source missing: '+str(path))
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def haar(x,levels,bank,resample):
    low=list(x);details=[]
    for _ in range(levels):
        p=bank.analysis(low,'zero',resample)
        low=list(map(float,p['a']));details.append(list(map(float,p['d'])))
    return low+[v for d in reversed(details) for v in d]


def inverse_haar(c,levels,bank,resample):
    N=len(c);size=N//2**levels;low=list(c[:size]);at=size
    for _ in range(levels):
        low=list(map(float,bank.synthesis(low,c[at:at+size],resample)))
        at+=size;size*=2
    require(at==N,'coefficient layout drift')
    return low


def threshold(c,low_count,lam,mode):
    require(mode in ('soft','hard','drop'),'threshold mode required')
    out=list(c[:low_count])
    for v in c[low_count:]:
        if mode=='drop':out.append(0.)
        elif mode=='hard':out.append(v if abs(v)>lam else 0.)
        else:out.append(math.copysign(max(abs(v)-lam,0.),v))
    return out


def measure(restored,truth,c):
    err=[(a-b)**2 for a,b in zip(restored,truth)];N=len(truth)
    h=c['feature_halfwidth_samples']
    pulse=c['pulse_index'];edge=c['edge_index']
    regions={'all':list(range(N)), 'pulse':list(range(max(0,pulse-h),min(N,pulse+h+1))),
             'edge':list(range(max(0,edge-h),min(N,edge+h+1))),
             'endpoints':list(range(h))+list(range(N-h,N))}
    return {'mse_V2':sum(err)/N, 'integrated_error_V2s':sum(err)/c['sample_rate_Hz'],
            'max_error_V':max(abs(a-b) for a,b in zip(restored,truth)),
            'region_mse_V2':{k:sum(err[i] for i in inds)/len(inds) for k,inds in regions.items()},
            'pulse_value_V':restored[pulse], 'edge_jump_V':restored[edge]-restored[edge-1] if edge else None}


def mel_bank(fs,F,bands):
    to_mel=lambda f:2595*math.log10(1+f/700)
    max_mel=to_mel(fs/2)
    nodes=[700*(10**((max_mel*r/(bands+1))/2595)-1) for r in range(bands+2)]
    freqs=[k*fs/F for k in range(F//2+1)]
    matrix=[]
    for r in range(bands):
        a,b,d=nodes[r:r+3]
        matrix.append([max(0.,min((f-a)/(b-a),(d-f)/(d-b))) for f in freqs])
    return nodes,freqs,matrix


def spectral(x,c,cfg,stft_source):
    N=len(x);fs=c['sample_rate_Hz'];L=cfg['window_length'];H=cfg['hop'];F=cfg['nfft']
    w=[.5-.5*math.cos(2*math.pi*r/L) for r in range(L)]
    starts=list(range(-L+H,N,H));U=sum(v*v for v in w);df=fs/F
    spectra=stft_source.stft(x,w,starts,F)
    restored,D=stft_source.reconstruct(spectra,w,starts,N)
    require(all(v is not None for v in restored),'finite original record not covered')
    maxerr=max(abs(a-b) for a,b in zip(restored,x))
    require(maxerr<2e-11*max(1,max(map(abs,x))),'full STFT reconstruction failed')
    nodes,freqs,B=mel_bank(fs,F,c['mel_bands'])
    psd=[];mel=[];identities=[]
    for start,X in zip(starts,spectra):
        P=[abs(X[k])**2/(fs*U)*(1 if k in (0,F//2) else 2) for k in range(F//2+1)]
        bands=[sum(b*p for b,p in zip(row,P))*df for row in B]
        time_power=sum((x[start+r] if 0<=start+r<N else 0)**2*w[r]**2 for r in range(L))/U
        spectral_power=sum(P)*df
        require(abs(spectral_power-time_power)<2e-11*max(1,time_power),'one-sided PSD integral mismatch')
        psd.append(P);mel.append(bands);identities.append([time_power,spectral_power])
    unstarts=list(range(0,N-L+1,H))
    unX=stft_source.stft(x,w,unstarts,F);unrest,unD=stft_source.reconstruct(unX,w,unstarts,N)
    # Global sign reversal is a concrete collision for all power/Mel features.
    minus=stft_source.stft([-v for v in x],w,starts,F)
    collision=max(abs(abs(a)**2-abs(b)**2) for X,Y in zip(spectra,minus) for a,b in zip(X,Y))
    return {'config':cfg,'window':w,'starts':starts,'frame_center_s':[(s+(L-1)/2)/fs for s in starts],
            'window_seconds':L/fs,'bin_Hz':df,'window_square_sum':U,'denominator':D,
            'restored_V':[float(v.real) for v in restored],'full_max_error_V':maxerr,
            'spectra_V':[[[v.real,v.imag] for v in X] for X in spectra],
            'frequencies_Hz':freqs,'one_sided_psd_V2_per_Hz':psd,'mel_nodes_Hz':nodes,
            'mel_weights':B,'mel_band_power_V2':mel,'frame_power_identity_V2':identities,
            'power_sign_collision_max':collision,'unextended_starts':unstarts,
            'unextended_denominator':unD,'unextended_unknown_indices':[i for i,v in enumerate(unrest) if v is None]}


def quantize(values,q):
    require(finite(q) and q>0 and all(finite(v) for v in values),'finite quantizer values and positive step required')
    codes=[round(v/q) for v in values]
    require(all(-32768<=v<=32767 for v in codes),'int16 overflow; no saturation permitted')
    return codes


def encode(values,N,levels,fs,q,sparse):
    require(power2(N) and 64<=N<=256 and len(values)==N,'encoder vector length must match N')
    require(type(fs) is int and 1<=fs<=1000000 and finite(q) and .01<=q<=1,'encoder fs/step invalid')
    require(type(sparse) is bool and type(levels) is int and
            (1<=levels<=int(math.log2(N)) if sparse else levels==0),'encoder layout/levels invalid')
    codes=quantize(values,q);items=[(i,v) for i,v in enumerate(codes) if v]
    if sparse:
        return HEADER.pack(b'WSP1',N,levels,fs,q,len(items))+b''.join(PAIR.pack(i,v) for i,v in items)
    require(levels==0,'PCM levels must be zero')
    return HEADER.pack(b'PCM1',N,0,fs,q,N)+struct.pack('<'+'h'*N,*codes)


def decode(blob,bank,resample):
    require(type(blob) is bytes and len(blob)>=HEADER.size,'truncated header')
    magic,N,levels,fs,q,K=HEADER.unpack_from(blob)
    require(power2(N) and 64<=N<=256 and 1<=fs<=1000000 and math.isfinite(q) and .01<=q<=1,'invalid decoded dimensions/scale')
    if magic==b'WSP1':
        require(1<=levels<=int(math.log2(N)) and K<=N and len(blob)==HEADER.size+PAIR.size*K,'invalid sparse extent/levels')
        vals=[0.]*N;last=-1
        for r in range(K):
            i,v=PAIR.unpack_from(blob,HEADER.size+r*PAIR.size)
            require(last<i<N and v!=0,'indices must be increasing, in range and nonzero')
            vals[i]=v*q;last=i
        x=inverse_haar(vals,levels,bank,resample)
    else:
        require(magic==b'PCM1' and levels==0 and K==N and len(blob)==HEADER.size+2*N,'invalid PCM extent/magic')
        vals=[v*q for v in struct.unpack_from('<'+'h'*N,blob,HEADER.size)];x=vals
    return {'samples_V':x,'dequantized_values':vals,'length':N,'levels':levels,'sample_rate_Hz':fs,
            'quantization_step_V':q,'nonzero_count':sum(v!=0 for v in vals),'total_bytes':len(blob),'header_bytes':HEADER.size}


def run(c,bank_path,resample_path,stft_path,output):
    validate(c);out=Path(output);require(not out.exists(),'output must not exist')
    bank=load(bank_path,'published_haar');resample=load(resample_path,'published_resample');stft_source=load(stft_path,'published_stft')
    begin=time.perf_counter();N=c['length'];fs=c['sample_rate_Hz'];J=c['haar_levels'];low=N//2**J
    trend=[c['trend_start_V']+(c['trend_end_V']-c['trend_start_V'])*n/(N-1) for n in range(N)]
    edge=[c['edge_height_V'] if n>=c['edge_index'] else 0. for n in range(N)]
    pulse=[c['pulse_height_V'] if n==c['pulse_index'] else 0. for n in range(N)]
    clean=[a+b+d for a,b,d in zip(trend,edge,pulse)]
    clean_c=haar(clean,J,bank,resample)
    full=inverse_haar(clean_c,J,bank,resample)
    require(max(abs(a-b) for a,b in zip(clean,full))<2e-12,'Haar identity failed')
    lam=c['noise_sigma_V']*c['threshold_sigma_multiple'];cases=[];files=[]
    def coded(name,values,target,levels,sparse):
        blob=encode(values,N,levels,fs,c['quantization_step_V'],sparse)
        # Decode from the actual serialized bytes, not retained coefficients.
        d=decode(blob,bank,resample)
        err=sum((a-b)**2 for a,b in zip(d['dequantized_values'],values))
        bound=N*c['quantization_step_V']**2/4
        require(err<=bound+2e-12*max(1,bound),'quantizer error bound failed')
        report={'name':name,**{k:v for k,v in d.items() if k not in ('samples_V','dequantized_values')},
                'payload_bytes':len(blob)-HEADER.size,'bits_per_original_sample':8*len(blob)/N,
                'total_bit_per_second':8*len(blob)/(N/fs),'quantization_error_squared_V2':err,
                'quantization_bound_squared_V2':bound,'metrics_to_clean':measure(d['samples_V'],clean,c),
                'metrics_to_encoded_target':measure(d['samples_V'],target,c),'decoded_samples_V':d['samples_V'],
                'sha256':hashlib.sha256(blob).hexdigest()}
        files.append((name,blob));return report
    codecs=[coded('clean-pcm.toy',clean,clean,0,False),coded('clean-haar.toy',clean_c,clean,J,True)]
    for q in c['noise_cases']:
        noise=[c['noise_sigma_V']*(1 if s=='+' else -1) for s in q['signs']]
        y=[a+b for a,b in zip(clean,noise)];cy=haar(y,J,bank,resample);methods=[]
        for mode in ('identity','drop','hard','soft'):
            cm=list(cy) if mode=='identity' else threshold(cy,low,lam,mode)
            z=inverse_haar(cm,J,bank,resample)
            coeff_error=sum((a-b)**2 for a,b in zip(cm,clean_c))
            sample_error=sum((a-b)**2 for a,b in zip(z,clean))
            require(abs(coeff_error-sample_error)<2e-11*max(1,sample_error),'orthogonal error identity failed')
            methods.append({'method':mode,'coefficients_V':cm,'samples_V':z,
                            'kept_detail_count':sum(v!=0 for v in cm[low:]),
                            'coefficient_error_squared_V2':coeff_error,'sample_error_squared_V2':sample_error,
                            'metrics':measure(z,clean,c)})
        soft=methods[-1]
        codecs.extend([coded(f'seed{q["seed"]}-pcm.toy',y,y,0,False),
                       coded(f'seed{q["seed"]}-haar.toy',cy,y,J,True),
                       coded(f'seed{q["seed"]}-soft-haar.toy',soft['coefficients_V'],soft['samples_V'],J,True)])
        cases.append({'seed':q['seed'],'noise_V':noise,'observed_V':y,'methods':methods})
    weak=[0.]*N;weak[c['pulse_index']]=lam/2
    wc=haar(weak,J,bank,resample);ws=threshold(wc,low,lam,'soft');wout=inverse_haar(ws,J,bank,resample)
    weak_error=sum((a-b)**2 for a,b in zip(wout,weak))
    if lam>0:require(weak_error>0,'noiseless weak pulse should be damaged by soft threshold')
    # Representations are all from this exact clean array; noisy denoising stays above.
    spectra=[spectral(clean,c,cfg,stft_source) for cfg in c['stft']]
    report={'inputs':c,'environment':{'python':platform.python_version(),'numpy':resample.np.__version__,
            'platform':platform.platform(),'threads':{k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},
            'published_sources':[{'path':str(Path(p).resolve()),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in (bank_path,resample_path,stft_path)]},
            'time_s':[n/fs for n in range(N)],'duration_s':N/fs,'components_V':{'trend':trend,'edge':edge,'pulse':pulse},
            'clean_V':clean,'clean_haar_V':clean_c,'haar_low_count':low,'threshold_V':lam,
            'haar_full_max_error_V':max(abs(a-b) for a,b in zip(clean,full)),
            'haar_input_energy_V2':sum(v*v for v in clean),'haar_coefficient_energy_V2':sum(v*v for v in clean_c),
            'noise_cases':cases,'spectral_representations':spectra,'codecs':codecs,
            'weak_pulse_counterexample':{'truth_V':weak,'soft_samples_V':wout,'amplitude_V':lam/2,
                'error_squared_V2':weak_error,'retained_energy_V2':sum(v*v for v in wout)},
            'elapsed_seconds':time.perf_counter()-begin}
    out.mkdir(parents=True)
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for name,blob in files:
        path=out/name;path.write_bytes(blob)
        # Re-read disk and actually decode the delivered bytes; require exact same byte content.
        disk=path.read_bytes();require(disk==blob,'file byte mismatch');decode(disk,bank,resample)
    with (out/'metrics.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['seed','method','mse_V2','integrated_error_V2s','pulse_region_mse_V2','edge_region_mse_V2','endpoint_mse_V2'])
        for q in cases:
            for m in q['methods']:
                v=m['metrics'];w.writerow([q['seed'],m['method'],v['mse_V2'],v['integrated_error_V2s'],v['region_mse_V2']['pulse'],v['region_mse_V2']['edge'],v['region_mse_V2']['endpoints']])
    return report


def main():
    here=Path(__file__).resolve().parent.parent
    root=here.parents[1]
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--haar-source',type=Path,default=here/'13-Haar分析合成与边界/filterbank_lab.py')
    p.add_argument('--resample-source',type=Path,default=here/'02-流式音频重采样/resample_lab.py')
    p.add_argument('--stft-source',type=Path,default=root/'数学/70-信号处理与多模态数学/81-STFT重建与边界实验.py')
    a=p.parse_args()
    try:r=run(json.loads(a.inputs.read_text()),a.haar_source,a.resample_source,a.stft_source,a.output)
    except (ValueError,KeyError,TypeError,OSError,struct.error) as e:
        print(str(e),file=sys.stderr);return 2
    print(json.dumps({'noise_cases':len(r['noise_cases']),'stft_configs':len(r['spectral_representations']),
                      'codec_files':len(r['codecs']),'elapsed_seconds':r['elapsed_seconds']}))
    return 0


if __name__=='__main__':sys.exit(main())
