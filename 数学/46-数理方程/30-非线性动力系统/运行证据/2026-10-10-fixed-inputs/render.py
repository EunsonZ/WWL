from pathlib import Path
import hashlib,json,importlib.metadata
import cairosvg
from PIL import Image
p=Path(__file__).resolve().parent
svg=p/'cli-output/pendulum-phase.svg';out=p/'assets';out.mkdir(exist_ok=False)
(out/'pendulum-phase.svg').write_bytes(svg.read_bytes())
assert hashlib.sha256(svg.read_bytes()).digest()==hashlib.sha256((out/'pendulum-phase.svg').read_bytes()).digest()
cairosvg.svg2png(url=str(svg),write_to=str(out/'pendulum-phase.png'))
with Image.open(out/'pendulum-phase.png') as image:dim=list(image.size)
r={'renderer':'CairoSVG offline native viewport','cairosvg_version':importlib.metadata.version('CairoSVG'),'svg_sha256':hashlib.sha256(svg.read_bytes()).hexdigest(),'png_sha256':hashlib.sha256((out/'pendulum-phase.png').read_bytes()).hexdigest(),'png_dimensions':dim,'scope':'actual offline SVG raster; no source edits or GUI screen access'}
(p/'render-results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
