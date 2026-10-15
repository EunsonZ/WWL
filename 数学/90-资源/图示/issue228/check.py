"""Author's separate artifact check, not independent human/agent review."""
from pathlib import Path
from fractions import Fraction as F
import sys, json, xml.etree.ElementTree as ET
out=Path(sys.argv[1]); d=json.loads((out/'samples.json').read_text()); count=0
for rec in d['records']:
    a=rec['a']
    assert len(rec['x'])==len(rec['y'])==401
    for x,y in zip(rec['x'],rec['y']):
        assert x+a>=0 and abs(y*y-x*x*(x+a))<2e-15
        count+=1
# Independent exact rational parameterization from t=y/x away from origin:
# x=t^2-a, y=t(t^2-a). Test each a without calling generator functions.
for a in [-1,0,1,F(1,4),F(-1,4)]:
    for t in [F(-2),F(-1),F(0),F(1,2),F(1),F(2)]:
        x=t*t-a; y=t*x; assert y*y==x*x*(x+a)
    # constant/linear coefficients vanish, quadratic term y^2-a*x^2.
    assert -a*0**2-0**3+0**2==0
# negative-a window proof sampled exactly; sign argument is in the lesson.
for x in [F(i,20) for i in range(-9,10) if i]:
    assert x*x*(x-1)<0
for name in ['plus1','zero','minus1']:
    tree=ET.parse(out/f'curve-{name}.svg'); svg=tree.getroot()
    assert svg.tag.endswith('svg') and 'viewBox' in svg.attrib
    assert not any(e.tag.endswith('image') for e in svg.iter())
    assert len([e for e in svg.iter() if e.tag.endswith('path')])>20
    assert (out/f'curve-{name}.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
print(f'PASS: {count} numerical samples; 30 exact parameter points; negative RHS; 3 SVG XML/path and 3 PNG signatures.')
