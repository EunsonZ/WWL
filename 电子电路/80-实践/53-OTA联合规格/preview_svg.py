"""Optional local SVG display adapter, not part of circuit computation."""
import argparse
from pathlib import Path
import resvg_py
p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);a=p.parse_args()
for n in ('network','tradeoff','noise-corners'):
    (a.results/(n+'.png')).write_bytes(resvg_py.svg_to_bytes(svg_path=str(a.results/(n+'.svg')),width=1600,font_family='PingFang SC',font_files=['/System/Library/Fonts/PingFang.ttc']))
