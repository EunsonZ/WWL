from pathlib import Path
import os,json
base=Path(__file__).resolve().parent
os.environ['FONTCONFIG_FILE']=str(base/'local-fontconfig.xml');os.environ['MPLCONFIGDIR']=str(base/'mpl-cache')
import cairosvg
cairosvg.svg2png(url=str(base/'snapshot/assets/noise-paths.svg'),write_to=str(base/'plots/noise-paths-local-fonts.png'),output_width=1620,output_height=1050)
print(json.dumps({'status':'RENDERED','FONTCONFIG_FILE':os.environ['FONTCONFIG_FILE'],'cachedir':str(base/'font-cache'),'font_dirs':'existing OS fonts read-only','source_svg_modified':False}))
