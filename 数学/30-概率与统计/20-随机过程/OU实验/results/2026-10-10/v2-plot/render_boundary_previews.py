from pathlib import Path
import cairosvg, json
base=Path(__file__).resolve().parent
for name in ['synthetic-T2-boundary','synthetic-zero-boundary']:
 raw=(base/'plots'/(name+'.svg')).read_text().strip().replace('<svg ', '<svg width="650" height="340" ', 1)
 # Retain the raw v2-generated SVG. Add visible provenance only to audit previews.
 wrapper='<svg xmlns="http://www.w3.org/2000/svg" width="1300" height="770" viewBox="0 0 650 385"><rect width="650" height="385" fill="white"/><text x="15" y="18" font-family="sans-serif" font-size="12" fill="#7a1b00">SYNTHETIC PLOT BOUNDARY: zero MC samples; orange values are mock estimates</text><g transform="translate(0,35)">'+raw+'</g></svg>'
 target=base/'plots'/(name+'-audit-preview.svg');target.write_text(wrapper+'\n')
 cairosvg.svg2png(url=str(target),write_to=str(target.with_suffix('.png')),output_width=1300,output_height=770)
print(json.dumps({'rendered_previews':2,'raw_source_generated_svg_unchanged':True}))
