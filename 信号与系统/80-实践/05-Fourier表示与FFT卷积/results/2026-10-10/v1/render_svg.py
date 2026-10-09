import hashlib,json,pathlib,resource
import cairosvg
from PIL import Image,ImageDraw
OUT=pathlib.Path(__file__).resolve().parent;target=OUT/'svg-render';target.mkdir();results=[]
for svg in sorted((OUT/'source-layout').rglob('*.svg')):
    stem=svg.stem;native=target/(stem+'-native.png');narrow=target/(stem+'-360.png')
    cairosvg.svg2png(url=str(svg),write_to=str(native));cairosvg.svg2png(url=str(svg),write_to=str(narrow),output_width=360)
    results.append(dict(svg=str(svg.relative_to(OUT)),sha256=hashlib.sha256(svg.read_bytes()).hexdigest(),native_png=str(native.relative_to(OUT)),native_size=Image.open(native).size,narrow_png=str(narrow.relative_to(OUT)),narrow_size=Image.open(narrow).size))
sheet=Image.new('RGB',(1100,sum(Image.open(OUT/r['native_png']).height+30 for r in results)),(255,255,255));draw=ImageDraw.Draw(sheet);y=0
for r in results:
    im=Image.open(OUT/r['native_png']).convert('RGB');draw.text((10,y+5),pathlib.Path(r['svg']).name,fill='black');sheet.paste(im,(0,y+30));y+=im.height+30
sheet.save(target/'native-contact.png')
result=dict(status='rendered',renderer='CairoSVG '+cairosvg.__version__,images=results,self_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scope='PNG render evidence; visual judgment and actual Obsidian/client presentation remain distinct')
(OUT/'svg-render.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
