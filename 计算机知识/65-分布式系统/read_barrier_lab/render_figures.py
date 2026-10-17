"""Optional SVG rasterization; numerical experiment uses only stdlib."""
import argparse
from pathlib import Path
import resvg_py
p=argparse.ArgumentParser();p.add_argument('--dir',type=Path,required=True);a=p.parse_args()
for name in ['barriers','histories']:
    svg=(a.dir/(name+'.svg')).read_text()
    (a.dir/(name+'.png')).write_bytes(resvg_py.svg_to_bytes(svg_string=svg,width=1600,font_files=['/System/Library/Fonts/PingFang.ttc']))
print('two PNGs rasterized')
