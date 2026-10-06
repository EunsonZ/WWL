"""Editable error responsibility diagram. Inert import; explicit new output only."""
import argparse
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape
from joint_lab import run, HERE


def generate(output, vault):
    out=Path(output).resolve();root=Path(vault).resolve()
    if out==root or root in out.parents or out==HERE or HERE in out.parents:raise ValueError('output outside source/vault only')
    if out.exists():raise FileExistsError('choose new output')
    budget=run(root,('L07',))['cards']['L07']['good']
    # Load optional raster renderer only after explicit call and all numerical guards.
    import cairosvg
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="360" height="880" viewBox="0 0 360 880"><title>L07 five distinct error accounts at defined ports</title><rect width="360" height="880" fill="white"/><g font-family="DejaVu Sans" fill="#182d45">']
    def text(x,y,s,size=13):parts.append(f'<text x="{x}" y="{y}" font-size="{size}">{escape(s)}</text>')
    text(14,26,'L07: one synthetic chain, five accounts',15)
    text(14,49,'1mVpk -> G20 -> G10 -> LP4 -> ADC16')
    text(14,70,'bias1.65V; 1kHz; fs100kHz; VFS3.3V')
    groups=[('DC bound',f"{budget['offset_input_bound']*1e6:.6f} uV input",['Vos, reference mismatch, Ib+ / Ib-','signed KCL first; absolute bounds after','NOT a random RSS guarantee']),('Random before quantization',f"{math.sqrt(budget['output_noise_rms']**2-budget['quantization_rms']**2)/budget['gain_nominal']*1e6:.6f} uVrms input",['ports -> |H(f)|^2 -> integral df [Hz]','single-sided PSD [V^2/Hz]','independence assumed; correlation adds terms']),('Quantization',f"{budget['quantization_rms']*1e6:.6f} uVrms ADC",['Delta / sqrt(12) conditional model','fixed DC may lock one code','NOT universal white noise']),('Aliased tone',f"{budget['alias_peak_adc_V']*1e6:.6f} uVpk ADC",['99kHz -> analog LP -> fold to 1kHz','peak and RMS have different contracts','digital filtering cannot unmix same samples']),('Acquisition',f"halfLSB {budget['half_lsb_V']*1e6:.6f} uV",['3.3V step; R200ohm, C20pF; 5us','RC and driver transient separately','NOT a real ADC BUSY/valid measurement'])]
    for i,(title,value,lines) in enumerate(groups):
        y=92+i*148
        parts.append(f'<rect x="12" y="{y}" width="336" height="134" rx="4" fill="#f0f4f7" stroke="#263e55"/>')
        text(24,y+24,title,16);text(24,y+47,value,14)
        for j,line in enumerate(lines):text(24,y+72+20*j,line,12)
    text(14,854,'allocated ADC20uVrms already includes kT/C',12)
    text(14,873,'CPU content != measured hardware budget',12)
    parts.append('</g></svg>');svg=''.join(parts).encode()
    # Finish raster work in memory; failures cannot leave a half-written output.
    pngs={w:cairosvg.svg2png(bytestring=svg,output_width=w,output_height=round(880*w/360)) for w in (360,425)}
    out.mkdir(parents=True,exist_ok=False);(out/'L07-error-sources.svg').write_bytes(svg)
    for w,b in pngs.items():(out/f'L07-error-sources-{w}.png').write_bytes(b)
    (out/'figure-data.json').write_text(json.dumps({'identity':'synthetic budget responsibility graph, not circuit/hardware','good':budget},indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    return out


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--vault',type=Path,required=True);a=p.parse_args(argv);generate(a.output,a.vault)

if __name__=='__main__':main()
