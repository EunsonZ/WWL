"""Optional local display adapter; not needed for SVG generation or numerical reconstruction."""
import argparse
from pathlib import Path
import resvg_py
p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);a=p.parse_args()
for name in ('forward','reconstruction','selection'):
    (a.results/(name+'.png')).write_bytes(resvg_py.svg_to_bytes(svg_path=str(a.results/(name+'.svg')),width=1600,font_family='PingFang SC',font_files=['/System/Library/Fonts/PingFang.ttc']))
