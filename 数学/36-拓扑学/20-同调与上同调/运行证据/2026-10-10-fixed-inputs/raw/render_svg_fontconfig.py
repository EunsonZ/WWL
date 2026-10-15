from pathlib import Path
import cairosvg,json,hashlib
r=Path(__file__).resolve().parent;a=r/'snapshot/数学/36-拓扑学/20-同调与上同调/assets';records=[]
for p in sorted(a.glob('*.svg')):
 out=r/'rendered'/f'{p.stem}-fontconfig.png';assert not out.exists();cairosvg.svg2png(bytestring=p.read_bytes(),write_to=str(out),scale=2)
 records.append({'source':str(p.relative_to(r)),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'png':str(out.relative_to(r)),'png_sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
print(json.dumps({'renderer':'CairoSVG','version':cairosvg.__version__,'scale':2,'outputs':records,'scope':'Offline rendering, not Obsidian or human reading'},indent=2))
