#!/usr/bin/env python3
"""Synthetic pulse-train + stable two-pole cascades. Not recorded human speech.
NumPy arrays follow the existing mathematics STFT convention: frames x frequency.
"""
import argparse
import base64
import io
import json
import math
from pathlib import Path
import wave
import numpy as np
from PIL import Image


def section(fs, frequency, bandwidth):
    if not math.isfinite(fs) or fs<=0 or not 0<frequency<fs/2 or not math.isfinite(bandwidth) or bandwidth<=0:
        raise ValueError('positive fs/B and pole frequency strictly inside Nyquist required')
    theta=2*math.pi*frequency/fs;r=math.exp(-math.pi*bandwidth/fs)
    if not 0<r<1: raise ValueError('floating pole radius must lie strictly in (0,1)')
    a1=-2*r*math.cos(theta);a2=r*r;g=1+a1+a2 # Unit DC gain, not unit peak gain.
    return dict(radius=r,theta_rad=theta,a1=a1,a2=a2,g=g,pole_frequency_hz=frequency,decay_bandwidth_hz=bandwidth)


def filter_section(x,s):
    y=np.empty(len(x),dtype=np.float64); prev=prev2=0.
    for n,v in enumerate(x):
        z=s['g']*v-s['a1']*prev-s['a2']*prev2
        y[n]=z;prev2,prev=prev,z
    return y


def response(sections,freq,fs):
    z=np.exp(-2j*np.pi*np.asarray(freq)/fs);h=np.ones_like(z,dtype=complex)
    for s in sections:h*=s['g']/(1+s['a1']*z+s['a2']*z*z)
    return h


def impulse_closed(s,n):
    k=np.arange(n);return s['g']*s['radius']**k*np.sin((k+1)*s['theta_rad'])/math.sin(s['theta_rad'])


def validate(c):
    fs=c['fs_hz']
    if type(fs) is not int or fs<1:raise ValueError('fs must be positive integer Hz')
    for key in ('duration_s','warmup_s'):
        if not math.isfinite(c[key]) or c[key]<=0 or not math.isclose(fs*c[key],round(fs*c[key]),abs_tol=1e-8):
            raise ValueError('duration and warmup require positive integral sample counts')
    n=round(fs*c['duration_s']);w=round(fs*c['warmup_s'])
    if n+w>200000:raise ValueError('finite lab memory bound: at most 200000 generated samples per case')
    l,h,k=c['frame_length'],c['hop'],c['nfft']
    if any(type(v) is not int or v<1 for v in (l,h,k)) or l<2 or l>n or k<l or k>4096:
        raise ValueError('integer frame/hop/NFFT, 2<=L<=N and L<=NFFT<=4096 required')
    if (n-l)//h+1>5000:raise ValueError('finite frame memory bound exceeded')
    if not math.isfinite(c['pcm_peak']) or not 0<c['pcm_peak']<=32767/32768:raise ValueError('PCM peak must lie in (0,32767/32768] to avoid int16 overflow')
    if not c['cases'] or len(c['cases'])>3 or len(set(v['name'] for v in c['cases']))!=len(c['cases']):
        raise ValueError('one to three distinct case names required')
    for v in c['cases']:
        if v['name'] not in ('base','pitch','filter'):raise ValueError('use base/pitch/filter case names')
        f0=v['f0_hz'];p=fs/f0 if math.isfinite(f0) and f0>0 else float('nan')
        if not math.isfinite(p) or p<2 or not math.isclose(p,round(p),abs_tol=1e-10):
            raise ValueError('this impulse-source implementation requires integer period >=2')
        if n%round(p):raise ValueError('retained record must contain an integer number of source periods')
        if len(v['formants_hz'])!=2 or len(v['decay_bandwidths_hz'])!=2:raise ValueError('exactly two resonators required')
        for f,b in zip(v['formants_hz'],v['decay_bandwidths_hz']):section(fs,f,b)


def analyze(c):
    validate(c);fs=c['fs_hz'];n=round(fs*c['duration_s']);warm=round(fs*c['warmup_s'])
    arrays={};rows=[]
    for v in c['cases']:
        p=round(fs/v['f0_hz']);u=np.zeros(n+warm);u[::p]=1
        sections=[section(fs,f,b) for f,b in zip(v['formants_hz'],v['decay_bandwidths_hz'])]
        y=u.copy()
        for s in sections:y=filter_section(y,s)
        rows.append(dict(**v,period_samples=p,sections=sections))
        arrays[v['name']+'_source']=u[warm:];arrays[v['name']+'_raw']=y[warm:]
    scale=c['pcm_peak']/max(np.max(np.abs(arrays[v['name']+'_raw'])) for v in c['cases'])
    starts=np.arange(0,n-c['frame_length']+1,c['hop']);window=np.hanning(c['frame_length'])
    centers=(starts+(c['frame_length']-1)/2)/fs
    freqs=np.fft.rfftfreq(n,1/fs);stftfreq=np.fft.rfftfreq(c['nfft'],1/fs)
    arrays.update(frame_starts=starts,frame_centers_s=centers,spectrum_freq_hz=freqs,stft_freq_hz=stftfreq)
    for row in rows:
        name=row['name'];y=scale*arrays[name+'_raw'];arrays[name+'_samples']=y
        frames=np.stack([y[s:s+c['frame_length']]*window for s in starts]);z=np.fft.rfft(frames,n=c['nfft'],axis=1)
        arrays[name+'_stft']=z
        transform=np.fft.rfft(y);amp=np.abs(transform)/n;amp[1:-1 if n%2==0 else None]*=2
        arrays[name+'_spectrum_amplitude']=amp
        # Exact finite periodic input DFT and infinite steady-state filter response.
        predicted=scale*response(row['sections'],freqs,fs)*np.fft.rfft(arrays[name+'_source'])
        row.update(peak=float(np.max(np.abs(y))),rms=float(np.sqrt(np.mean(y*y))),
                   steady_fft_max_complex_error=float(np.max(np.abs(transform-predicted))),
                   period_repeat_max_error=float(np.max(np.abs(y[row['period_samples']:]-y[:-row['period_samples']]))),
                   strongest_harmonic_hz=float(freqs[1+np.argmax(amp[1:])]))
        grid=np.linspace(1,fs/2,65537);envelope=np.abs(response(row['sections'],grid,fs))
        row['envelope_peaks_hz']=[float(grid[np.flatnonzero((grid>max(1,f-250))&(grid<min(fs/2,f+250)))[np.argmax(envelope[(grid>max(1,f-250))&(grid<min(fs/2,f+250))])]]) for f in row['formants_hz']]
    return dict(config=c,common_output_gain=scale,samples=n,warmup_samples=warm,frames=len(starts),
                stft_shape=[len(starts),len(stftfreq)],frame_first_center_s=float(centers[0]),frame_last_center_s=float(centers[-1]),
                hop_s=c['hop']/fs,window_s=c['frame_length']/fs,stft_grid_hz=fs/c['nfft'],cases=rows,
                listening=dict(status='not_performed',materials=[v['name']+'.wav' for v in c['cases']],
                               claims_not_measured=['human pitch','vowel identity','intelligibility','naturalness'])),arrays


def figures(out,arr,target):
    c=out['config'];fs=c['fs_hz'];rows=out['cases'];w=1160;rh=240;height=70+rh*len(rows)
    def head(title,desc,height):return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{height}" viewBox="0 0 {w} {height}">',f'<title>{title}</title><desc>{desc}</desc>','<rect width="100%" height="100%" fill="white"/>','<style>text{font:14px Arial,sans-serif;fill:#18212c}.head{font-size:19px;font-weight:bold}.grid{stroke:#dce2e8;stroke-width:1}</style>']
    s=head('Synthetic source-filter waveforms and harmonic envelopes','Three actual retained signals. Left first 32 milliseconds share one gain. Right single-sided DFT amplitude in dB relative to full scale one, plus scaled transfer envelope 2 gain H / period. DC omitted from right. Pole-angle frequencies need not equal envelope peaks.',height)
    s.append('<text x="25" y="28" class="head">Synthetic pulse source + two resonators: one knob changed at a time</text>')
    for i,row in enumerate(rows):
        top=70+i*rh;bottom=top+160;name=row['name'];y=arr[name+'_samples'];left=70;right=480
        s.append(f'<text x="{left}" y="{top-15}">{name}: f0={row["f0_hz"]} Hz; pole frequencies {row["formants_hz"]} Hz</text>')
        for value in (-c['pcm_peak'],0,c['pcm_peak']):
            yy=top+80-80*value/c['pcm_peak'];s+=[f'<line x1="{left}" y1="{yy}" x2="{right}" y2="{yy}" class="grid"/>',f'<text x="20" y="{yy+5}">{value:g}</text>']
        count=min(len(y),round(fs*.032));pts=' '.join(f'{left+410*k/(fs*.032):.4f},{top+80-80*y[k]/c["pcm_peak"]:.4f}' for k in range(count))
        s.append(f'<polyline points="{pts}" fill="none" stroke="#2563a6" stroke-width="1.1"/>')
        s.append(f'<text x="70" y="{bottom+23}">0</text><text x="410" y="{bottom+23}">32 ms</text>')
        xl,xr=640,1100;fmax=min(4000,fs/2);fx=lambda f:xl+(xr-xl)*f/fmax;dy=lambda db:bottom-160*(max(-80,min(0,db))+80)/80
        for db in (-80,-40,0):s +=[f'<line x1="{xl}" y1="{dy(db)}" x2="{xr}" y2="{dy(db)}" class="grid"/>',f'<text x="595" y="{dy(db)+5}">{db}</text>']
        grid=np.linspace(max(1,row['f0_hz']/2),fmax,600);en=2*out['common_output_gain']/row['period_samples']*np.abs(response(row['sections'],grid,fs))
        pts=' '.join(f'{fx(f):.4f},{dy(20*math.log10(max(a,1e-8))):.4f}' for f,a in zip(grid,en))
        s.append(f'<polyline points="{pts}" fill="none" stroke="#b34438" stroke-width="2"/>')
        for h in range(1,math.floor(fmax/row['f0_hz'])+1):
            f=h*row['f0_hz'];k=round(f*out['samples']/fs);db=20*math.log10(max(arr[name+'_spectrum_amplitude'][k],1e-8))
            s.append(f'<line x1="{fx(f):.4f}" y1="{bottom}" x2="{fx(f):.4f}" y2="{dy(db):.4f}" stroke="#2563a6" stroke-width="1.4"/>')
        s +=[f'<text x="640" y="{top-15}">DFT lines / theoretical envelope (amplitude dB, not PSD)</text>',f'<text x="640" y="{bottom+23}">0</text><text x="1030" y="{bottom+23}">{fmax:g} Hz</text>']
    s.append('</svg>');(target/'wave-spectrum.svg').write_text('\n'.join(s)+'\n')
    height=75+250*len(rows);s=head('STFT of the same three synthetic signals','Hann is symmetric length L. No frame padding or centering. Time cells surround actual frame centers, frequency cells surround bin centers. Same global amplitude reference across cases; colors clip -80 to zero dB. Full complex matrices saved in samples.npz.',height)
    s +=[f'<text x="25" y="28" class="head">Same samples: Hann L={c["frame_length"]}, H={c["hop"]}, FFT={c["nfft"]}; {out["frames"]} complete frames</text>']
    maxmag=max(np.max(np.abs(arr[v['name']+'_stft'])) for v in rows);fmax=min(4000,fs/2);shown=arr['stft_freq_hz']<=fmax
    for i,row in enumerate(rows):
        top=75+250*i;left=80;width=950;hh=165;z=np.abs(arr[row['name']+'_stft'][:,shown]).T[::-1]
        db=np.maximum(-80,20*np.log10(np.maximum(z/maxmag,1e-8)));q=(db+80)/80
        rgb=np.stack([255*q,80*q+70*q*q,210*q*q*q],axis=-1).astype(np.uint8)
        buf=io.BytesIO();Image.fromarray(rgb).save(buf,format='PNG');url=base64.b64encode(buf.getvalue()).decode()
        t0=out['frame_first_center_s']-out['hop_s']/2;dt=out['frames']*out['hop_s'];df=out['stft_grid_hz']
        upper=float(arr['stft_freq_hz'][shown][-1])+df/2
        s +=[f'<defs><clipPath id="p{i}"><rect x="{left}" y="{top}" width="{width}" height="{hh}"/></clipPath></defs>',f'<text x="80" y="{top-15}">{row["name"]}: f0={row["f0_hz"]} Hz; pole frequencies {row["formants_hz"]} Hz</text>',f'<image href="data:image/png;base64,{url}" x="{left+width*t0/c["duration_s"]:.6f}" y="{top+hh-hh*upper/fmax:.6f}" width="{width*dt/c["duration_s"]:.6f}" height="{hh*(upper+df/2)/fmax:.6f}" preserveAspectRatio="none" image-rendering="pixelated" clip-path="url(#p{i})"/>',f'<text x="25" y="{top+7}">{fmax:g}</text><text x="35" y="{top+hh}">0 Hz</text>',f'<text x="80" y="{top+hh+25}">0</text><text x="970" y="{top+hh+25}">{c["duration_s"]:g} s</text>',f'<text x="80" y="{top+hh+48}">White margins: no frame-center cells. Black=-80 dB; bright pink=0 dB (global |STFT| reference).</text>']
    s.append('</svg>');(target/'same-samples-stft.svg').write_text('\n'.join(s)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'));parser.add_argument('--output',type=Path,default=Path(__file__).with_name('results'));args=parser.parse_args()
    c=json.loads(args.input.read_text());out,arr=analyze(c);args.output.mkdir(parents=True,exist_ok=True)
    for row in out['cases']:
        name=row['name'];q=np.rint(arr[name+'_samples']*32768).astype('<i2');arr[name+'_pcm16']=q
        with wave.open(str(args.output/(name+'.wav')),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(c['fs_hz']);f.writeframes(q.tobytes())
        row['pcm_max_quantization_error']=float(np.max(np.abs(q.astype(float)/32768-arr[name+'_samples'])))
    np.savez(args.output/'samples.npz',**arr)
    (args.output/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');figures(out,arr,args.output)
    print(json.dumps(dict(samples=out['samples'],frames=out['frames'],shape=out['stft_shape'],gain=out['common_output_gain'],steady_errors=[r['steady_fft_max_complex_error'] for r in out['cases']])))


if __name__=='__main__':main()
