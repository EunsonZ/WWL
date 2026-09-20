#!/usr/bin/env python3
"""Dependency-free SVG figures regenerated from results.json."""
import json, pathlib

root = pathlib.Path(__file__).parent
rdir = root / "figures"
rdir.mkdir(exist_ok=True)
r = json.loads((root / "results.json").read_text()) ["results"]

def svg_bars(path, title, labels, values, maxv=1):
    width, height, left, base = 760, 390, 170, 330
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<style>text{font-family:Arial,sans-serif;fill:#18212b}.t{font-size:18px;font-weight:bold}.l{font-size:14px}.v{font-size:13px;font-weight:bold}</style>', '<rect width="100%" height="100%" fill="#fbfcfe"/>',f'<text x="24" y="32" class="t">{title}</text>',f'<line x1="{left}" y1="60" x2="{left}" y2="{base}" stroke="#607080"/><line x1="{left}" y1="{base}" x2="730" y2="{base}" stroke="#607080"/>']
    for i in range(6):
        y=base-(base-60)*i/5; lines += [f'<line x1="{left}" y1="{y:.1f}" x2="730" y2="{y:.1f}" stroke="#dfe5eb"/>',f'<text x="{left-55}" y="{y+5:.1f}" class="l">{maxv*i/5:.1f}</text>']
    gap=560/len(labels)
    for i,(label,v) in enumerate(zip(labels,values)):
        x=left+30+i*gap; h=(base-60)*v/maxv
        lines += [f'<rect x="{x:.1f}" y="{base-h:.1f}" width="{gap-38:.1f}" height="{h:.1f}" fill="#2878b5"/>',f'<text x="{x:.1f}" y="{base-h-8:.1f}" class="v">{v:.3f}</text>',f'<text x="{x:.1f}" y="{base+24}" class="l">{label}</text>']
    lines.append('</svg>'); path.write_text('\n'.join(lines))

svg_bars(rdir/'ud-ewt-test-baselines.svg', 'UD English EWT r2.16 fixed test: token accuracy', ['unigram','word-tag','HMM'], [r['unigram']['token_accuracy'],r['word_frequency']['token_accuracy'],r['hmm']['token_accuracy']])
svg_bars(rdir/'ud-ewt-hmm-slices.svg', 'HMM fixed test: accuracy by exposure slice', ['all','true OOV','seen rare'], [r['hmm']['token_accuracy'],r['hmm']['true_oov']['accuracy'],r['hmm']['seen_rare']['accuracy']])
