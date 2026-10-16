"""Optional SVG preview only; requires isolated resvg-py, no geometry generation."""
import argparse
from pathlib import Path
import resvg_py

def main():
    p=argparse.ArgumentParser();p.add_argument('--svg',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.write_bytes(resvg_py.svg_to_bytes(svg_path=str(a.svg),sans_serif_family='PingFang SC',width=1600))

if __name__=='__main__':main()
