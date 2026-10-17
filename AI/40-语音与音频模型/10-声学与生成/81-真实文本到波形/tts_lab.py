#!/usr/bin/env python3
"""Pinned eSpeak rule/formant TTS, real licensed corpus excerpts, observable interventions.
No microphone, playback, network request, model training or ASR is performed by this lab.
"""
import argparse
import csv
import ctypes as C
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import re
import subprocess
import sys
import time
import wave
import numpy as np

ROOT=Path(__file__).resolve().parent
MEMORY=8*1024**3

def memory_bound():
    # Darwin rejects lowering RLIMIT_AS on this host. Workload is finite (3 fixed
    # clips, <=1000 text chars); check measured peak RSS before/after each stage.
    raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak=raw if sys.platform=='darwin' else raw*1024
    if peak>MEMORY:raise MemoryError('observed process peak RSS exceeds 8 GiB budget')
    return peak


def sha(data):return hashlib.sha256(data).hexdigest()


def write_wav(path,pcm,rate):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(pcm)


def read_wav(path):
    with wave.open(str(path),'rb') as f:
        if f.getnchannels()!=1 or f.getsampwidth()!=2:raise ValueError('mono PCM16 required')
        rate=f.getframerate();pcm=f.readframes(f.getnframes())
    return np.frombuffer(pcm,dtype='<i2'),rate


def metrics(samples,rate):
    x=np.asarray(samples,dtype=float)/32768
    return dict(sample_rate_hz=rate,channels=1,bits_per_sample=16,samples=len(x),duration_s=len(x)/rate,
                peak=float(np.max(np.abs(x))),rms=float(np.sqrt(np.mean(x*x))),
                rail_fraction=float(np.mean((samples==32767)|(samples==-32768))),pcm_sha256=sha(np.asarray(samples,dtype='<i2').tobytes()))


class EventId(C.Union):
    _fields_=[('number',C.c_int),('name',C.c_void_p),('string',C.c_char*8)]
class Event(C.Structure):
    _fields_=[('type',C.c_int),('uid',C.c_uint),('text_position',C.c_int),('length',C.c_int),
              ('audio_position',C.c_int),('sample',C.c_int),('user_data',C.c_void_p),('id',EventId)]
CALLBACK=C.CFUNCTYPE(C.c_int,C.POINTER(C.c_short),C.c_int,C.POINTER(Event))


def synthesize(engine,output,name,text,voice,rate,pitch,volume,trace=True):
    memory_bound()
    if not text or len(text)>1000 or not text.isascii():raise ValueError('lab accepts nonempty ASCII text of at most 1000 characters')
    if not 80<=rate<=450 or not 0<=pitch<=100 or not 0<=volume<=200:raise ValueError('rate/pitch/volume outside declared API range')
    acoustic=output/(name+'.acoustic.csv')
    if trace:os.environ['WWL_TTS_ACOUSTIC_TRACE']=str(acoustic.resolve())
    else:os.environ.pop('WWL_TTS_ACOUSTIC_TRACE',None)
    lib=C.CDLL(str(engine/'lib/libespeak-ng.dylib'))
    lib.espeak_Initialize.argtypes=[C.c_int,C.c_int,C.c_char_p,C.c_int]
    lib.espeak_SetSynthCallback.argtypes=[CALLBACK];lib.espeak_SetVoiceByName.argtypes=[C.c_char_p]
    lib.espeak_Synth.argtypes=[C.c_void_p,C.c_size_t,C.c_uint,C.c_int,C.c_uint,C.c_uint,C.POINTER(C.c_uint),C.c_void_p]
    events=[];chunks=[]
    @CALLBACK
    def callback(pcm,n,ev):
        if pcm and n>0:chunks.append(C.string_at(pcm,n*2))
        k=0
        while ev and ev[k].type:
            e=ev[k]; phone=bytes(e.id.string).decode('ascii',errors='replace') if e.type==7 else ''
            events.append(dict(type=e.type,text_position_1based=e.text_position,text_length=e.length,
                               audio_ms=e.audio_position,phone=phone,
                               reported_text_slice=text[max(0,e.text_position-1):max(0,e.text_position-1)+e.length] if e.type==1 else ''))
            k+=1
        return 0
    sr=lib.espeak_Initialize(2,0,str(engine/'share').encode(),1) # synchronous retrieval, no playback; mnemonic events
    if sr<=0 or lib.espeak_SetVoiceByName(voice.encode())!=0:raise RuntimeError('initialization/voice failure')
    lib.espeak_SetSynthCallback(callback)
    for key,value in ((1,rate),(2,volume),(3,pitch)):
        if lib.espeak_SetParameter(key,value,0)!=0:raise RuntimeError('parameter failure')
    content=text.encode();uid=C.c_uint();start=time.perf_counter()
    code=lib.espeak_Synth(content,len(content)+1,0,1,0,1,C.byref(uid),None)
    elapsed=time.perf_counter()-start; peak_rss=memory_bound()
    if code!=0:raise RuntimeError('synthesis failed: '+str(code))
    pcm=b''.join(chunks);write_wav(output/(name+'.wav'),pcm,sr)
    (output/(name+'.events.json')).write_text(json.dumps(dict(text=text,events=events),ensure_ascii=False,indent=2)+'\n')
    cli=subprocess.run([str(engine/'bin/espeak-ng'),'-q','-X','-v',voice,'-s',str(rate),'-p',str(pitch),text],capture_output=True,text=True,check=True,
                       env={k:v for k,v in os.environ.items() if k!='WWL_TTS_ACOUSTIC_TRACE'})
    (output/(name+'.translation.txt')).write_text(cli.stdout)
    lib.espeak_Terminate()
    # Timing is a volatile observation, not part of byte-identical model output.
    (output/(name+'.timing.json')).write_text(json.dumps(dict(synth_call_wall_s=elapsed,audio_s=len(pcm)/2/sr,
                                      offline_initialized_call_rtf=elapsed/(len(pcm)/2/sr),peak_rss_bytes=peak_rss))+'\n')


def cardinal(n):
    if type(n) is not int or not 0<=n<100:raise ValueError('finite probe normalizer accepts only 0..99')
    small=['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen']
    tens=['','','twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety']
    return small[n] if n<20 else tens[n//10]+(' '+small[n%10] if n%10 else '')


def normalize_probe(text,contract,broken=False):
    match=re.fullmatch(r'I paid \$(\d+)\.(\d{2}) on (\d{2})/(\d{2})\.',text)
    if not match or contract['currency']!='USD' or contract['date_order'] not in ('DD/MM','MM/DD'):
        raise ValueError('finite USD/date probe grammar or application contract mismatch')
    dollars,cents,first,second=map(int,match.groups())
    if broken:
        token=match.group(1)+match.group(2); date=match.group(3)+match.group(4)
        return dict(text=f'I paid {token} on {date}.',amount_token=token,date_token=date,semantic_slots=None)
    day,month=(first,second) if contract['date_order']=='DD/MM' else (second,first)
    ordinals=['','first','second','third','fourth','fifth','sixth','seventh','eighth','ninth','tenth','eleventh','twelfth','thirteenth','fourteenth','fifteenth','sixteenth','seventeenth','eighteenth','nineteenth','twentieth','twenty first','twenty second','twenty third','twenty fourth','twenty fifth','twenty sixth','twenty seventh','twenty eighth','twenty ninth','thirtieth','thirty first']
    months=['','January','February','March','April','May','June','July','August','September','October','November','December']
    if not 1<=month<=12 or not 1<=day<=31:raise ValueError('month/day outside finite probe domain')
    # This is not a calendar validator; the fixed March/April day-three/four pair is valid.
    words=f'I paid {cardinal(dollars)} dollars and {cardinal(cents)} cents on {months[month]} {ordinals[day]}.'
    return dict(text=words,semantic_slots=dict(currency='USD',amount_cents=100*dollars+cents,month=month,day=day))


def validate(cfg):
    if cfg['engine_version']!='1.52.0' or cfg['voice']!='en-us':raise ValueError('this lesson pins one rule/model identity and voice')
    if cfg['application_contract']!={'currency':'USD','amount_cents':1250,'date_order':'DD/MM','day':3,'month':4}:
        raise ValueError('fixed probe application contract changed; provide a new reference before evaluation')
    if cfg['probe']!='I paid $12.50 on 03/04.' or cfg['expanded']!='I paid twelve dollars and fifty cents on April third.' or cfg['bad_normalized']!='I paid 1250 on 0304.':
        raise ValueError('fixed text/normalizer intervention is part of this finite evaluation')
    if not math.isfinite(cfg['clip_gain']) or cfg['clip_gain']<=1:raise ValueError('clip gain must exceed one')


def clipped(reference,rate,gain):
    x=np.asarray(reference,dtype=np.int64);z=x*gain
    out=np.clip(np.rint(z),-32768,32767).astype('<i2')
    error=(out.astype(float)-x)/32768
    snr=10*math.log10(np.mean((x/32768)**2)/np.mean(error**2)) if np.any(error) else None
    return out,dict(gain=gain,changed_fraction=float(np.mean(out!=x)),saturation_fraction=float(np.mean((z>32767)|(z<-32768))),
                    waveform_error_rms=float(np.sqrt(np.mean(error**2))),reference_to_error_db=snr)


def run(cfg,engine,output,ffmpeg):
    validate(cfg);output.mkdir(parents=True,exist_ok=True)
    version=subprocess.run([str(engine/'bin/espeak-ng'),'--version'],capture_output=True,text=True,check=True).stdout
    if '1.52.0' not in version:raise ValueError('wrong engine version')
    corpus=json.loads((ROOT/'data/utterances.json').read_text())
    if [r['id'] for r in corpus]!=cfg['corpus_ids']:raise ValueError('fixed corpus identity/order mismatch')
    cases=[dict(name=r['id'],text=r['text'],rate=cfg['rate_wpm'],pitch=cfg['pitch_parameter']) for r in corpus]
    normalized=normalize_probe(cfg['probe'],cfg['application_contract']);broken=normalize_probe(cfg['probe'],cfg['application_contract'],True)
    if normalized['text']!=cfg['expanded'] or broken['text']!=cfg['bad_normalized']:raise ValueError('normalizer output differs from the preregistered reference')
    cases += [dict(name=n,text=t,rate=rate,pitch=pitch) for n,t,rate,pitch in [
        ('probe_raw',cfg['probe'],cfg['rate_wpm'],cfg['pitch_parameter']),
        ('probe_explicit',normalized['text'],cfg['rate_wpm'],cfg['pitch_parameter']),
        ('probe_bad_frontend',broken['text'],cfg['rate_wpm'],cfg['pitch_parameter']),
        ('probe_slow',normalized['text'],cfg['slow_rate_wpm'],cfg['pitch_parameter']),
        ('probe_pitch',normalized['text'],cfg['rate_wpm'],cfg['raised_pitch_parameter'])]]
    for c in cases:
        subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--engine',str(engine),'--output',str(output),
                        '--case',c['name'],'--text',c['text'],'--voice',cfg['voice'],'--rate',str(c['rate']),'--pitch',str(c['pitch']),
                        '--volume',str(cfg['volume_parameter'])],check=True)
    rows=[]
    for c in cases:
        samples,sr=read_wav(output/(c['name']+'.wav'));ev=json.loads((output/(c['name']+'.events.json')).read_text())['events']
        phones=[e for e in ev if e['type']==7];words=[e for e in ev if e['type']==1]
        with (output/(c['name']+'.acoustic.csv')).open() as f:ac=list(csv.DictReader(f))
        rows.append(dict(**c,metrics=metrics(samples,sr),word_event_count=len(words),phone_event_count=len(phones),
                         last_event_ms=max(e['audio_ms'] for e in ev),phone_sequence=[e['phone'] for e in phones if e['phone']],
                         voiced_dispatches=len(ac),dispatch_pitch_median_hz=float(np.median([float(r['pitch_hz']) for r in ac]))))
    refs=[]
    for r in corpus:
        path=ROOT/'data'/r['audio']
        if sha(path.read_bytes())!=r['sha256']:raise ValueError('reference audio bytes changed')
        data=subprocess.run([ffmpeg,'-v','error','-threads','1','-i',str(path),'-threads','1','-f','s16le','-acodec','pcm_s16le','-'],capture_output=True,check=True).stdout
        # Source dataset declares mono16k. ffprobe verifies original stream, no -ar/-ac conversion.
        probe=subprocess.run([str(Path(ffmpeg).with_name('ffprobe')),'-v','error','-show_entries','stream=sample_rate,channels','-of','json',str(path)],capture_output=True,text=True,check=True)
        stream=json.loads(probe.stdout)['streams'][0]
        if stream['sample_rate']!='16000' or stream['channels']!=1:raise ValueError('reference stream must be mono16k')
        refs.append(dict(**r,metrics=metrics(np.frombuffer(data,dtype='<i2'),16000)))
    original,sr=read_wav(output/'probe_explicit.wav');damage,err=clipped(original,sr,cfg['clip_gain'])
    write_wav(output/'probe_clipped.wav',damage.tobytes(),sr)
    identity=dict(engine_version='1.52.0',source_commit=cfg['engine_commit'],voice='en-us',instrumentation='instrument_wavegen.py observational insertion',
                  platform=platform.platform(),python=platform.python_version(),numpy=np.__version__,
                  ffmpeg_version=subprocess.run([ffmpeg,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0])
    out=dict(config=cfg,identity=identity,corpus=refs,cases=rows,
             clipped=dict(source_case='probe_explicit',metrics=metrics(damage,sr),error=err),
             frontend=dict(raw=dict(status='underspecified_without_application_contract'),
                           explicit=dict(**normalized,application_slots_match=normalized['semantic_slots']==dict(currency='USD',amount_cents=1250,month=4,day=3)),
                           strip_punctuation=dict(**broken,application_slots_match=False)),
             listening=dict(status='not_performed',automatic_intelligibility='not_measured',naturalness='not_measured',speaker_similarity='not_measured'))
    (output/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');figures(out,output)
    print(json.dumps(dict(cases=len(cases),reference_clips=len(refs),clipped=err,
                         durations={r['name']:r['metrics']['duration_s'] for r in rows})))


def figures(out,target):
    def svg(title,desc,w,h):return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<title>{title}</title><desc>{desc}</desc>','<rect width="100%" height="100%" fill="white"/>','<style>text{font:14px Arial,sans-serif;fill:#17212d}.head{font-size:19px;font-weight:bold}.grid{stroke:#dce2e8;stroke-width:1}</style>']
    s=svg('Actual corpus reference and generic synthesis durations','Same reference transcripts, different speaker and generic rule synthesizer. Duration is a measurable discrepancy, not a quality or alignment score. All three real references are the same speaker and chapter.',1000,430)
    s += ['<text x="25" y="30" class="head">Real speech references / generic rule TTS: duration, not naturalness</text>']
    duration=max(max(r['metrics']['duration_s'] for r in out['corpus']),max(r['metrics']['duration_s'] for r in out['cases'][:3]))*1.1
    for i,(ref,gen) in enumerate(zip(out['corpus'],out['cases'][:3])):
        top=90+i*95;s.append(f'<text x="25" y="{top+19}">{ref["id"]}</text>')
        for k,(row,color) in enumerate(((ref,'#2563a6'),(gen,'#b34438'))):
            d=row['metrics']['duration_s'];s += [f'<rect x="250" y="{top+25*k}" width="{620*d/duration:.4f}" height="19" fill="{color}"/>',f'<text x="{260+620*d/duration:.4f}" y="{top+15+25*k}">{d:.3f} s</text>']
    s += ['<text x="250" y="390" style="fill:#2563a6">Blue: recorded reference 16 kHz</text>','<text x="550" y="390" style="fill:#b34438">Red: generic synthesis 22.05 kHz</text>','<text x="250" y="415">No ASR back-transcription, perceptual judgement or identity imitation.</text>','</svg>']
    (target/'corpus-duration.svg').write_text('\n'.join(s)+'\n')
    with (target/'probe_explicit.acoustic.csv').open() as f:frames=list(csv.DictReader(f))
    s=svg('Actual observed acoustic dispatch and PCM clipping','Upper: three formant parameter frequencies and pitch from periodic wavegen dispatches, indexed by dispatch not utterance time. Lower: first 60ms of generated explicit-probe waveform and gain-four saturated transformation. Trace only periodic branch, unvoiced sampled sounds are not these rows.',1100,680)
    s += ['<text x="25" y="30" class="head">A. Actual periodic-branch parameters (dispatch index, not milliseconds)</text>']
    width=900;left=80;top=80;hh=240;fmax=max(4000,max(float(r['F3_hz']) for r in frames)*1.1)
    for value in (0,1000,2000,3000,4000):
        yy=top+hh-hh*value/fmax;s +=[f'<line x1="80" y1="{yy:.4f}" x2="980" y2="{yy:.4f}" class="grid"/>',f'<text x="25" y="{yy+4:.4f}">{value}</text>']
    for i,key in enumerate(('F1_hz','F2_hz','F3_hz','pitch_hz')):
        colors=['#2563a6','#b34438','#328451','#9459a4'];pts=' '.join(f'{left+width*j/max(1,len(frames)-1):.4f},{top+hh-hh*float(row[key])/fmax:.4f}' for j,row in enumerate(frames))
        s +=[f'<polyline points="{pts}" fill="none" stroke="{colors[i]}" stroke-width="1.3"/>',f'<text x="{100+210*i}" y="355" style="fill:{colors[i]}">{key}</text>']
    s += [f'<text x="80" y="340">0</text><text x="850" y="340">index {len(frames)-1}</text>','<text x="25" y="400" class="head">B. Post-decoder intervention: same PCM, gain 4 then saturation</text>']
    original,sr=read_wav(target/'probe_explicit.wav');bad,_=read_wav(target/'probe_clipped.wav');n=min(round(.06*sr),len(original));top=430;hh=160
    for samples,color in ((bad,'#b34438'),(original,'#2563a6')):
        pts=' '.join(f'{80+900*j/(.06*sr):.4f},{top+hh/2-hh/2*float(v)/32768:.4f}' for j,v in enumerate(samples[:n]))
        s.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.1"/>')
    s +=['<text x="25" y="435">+1</text><text x="25" y="595">-1</text>','<text x="80" y="620">0</text><text x="900" y="620">60 ms</text>','<text x="80" y="650">Blue: original; red: transformed. Distortion measured digitally; human impact not tested.</text>','</svg>']
    (target/'acoustic-and-clipping.svg').write_text('\n'.join(s)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=ROOT/'inputs.json');p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'results');p.add_argument('--ffmpeg',default='/opt/homebrew/bin/ffmpeg')
    p.add_argument('--worker',action='store_true');p.add_argument('--case');p.add_argument('--text');p.add_argument('--voice',default='en-us');p.add_argument('--rate',type=int,default=175);p.add_argument('--pitch',type=int,default=50);p.add_argument('--volume',type=int,default=100);a=p.parse_args()
    if a.worker:synthesize(a.engine,a.output,a.case,a.text,a.voice,a.rate,a.pitch,a.volume)
    else:memory_bound();run(json.loads(a.input.read_text()),a.engine,a.output,a.ffmpeg)

if __name__=='__main__':main()
