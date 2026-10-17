"""Same-data static SVGs: conditional parsing metrics and literal reference errors."""
import argparse
import json
from pathlib import Path
import textwrap
from xml.sax.saxutils import escape

BLUE='#185d9a';ORANGE='#b55b14';GRAY='#58636e';GREEN='#23734c';RED='#a83c3c'


def text(x,y,value,size=15,color=GRAY,anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(value))}</text>'


def start(width,height,title,desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            '<title id="title">'+escape(title)+'</title><desc id="desc">'+escape(desc)+'</desc>',
            '<rect width="100%" height="100%" fill="white"/><g font-family="DejaVu Sans, sans-serif">']


def render(root,output):
    root,output=Path(root),Path(output);output.mkdir(parents=True,exist_ok=True);r=json.loads((root/'results.json').read_text())
    models=[('geometry',BLUE,'geometry'),('upos_geometry',ORANGE,'UPOS + geometry')]
    desc='Fixed Swedish-Talbanken r2.16 short-word sentences, gold words and gold UPOS as declared inputs. Exact complete relation labels, real root included, reference punctuation excluded. Bars are descriptive proportions, not confidence intervals or human meaning. P301 contributes435 of548 scored test words. Data-derived adaptations CC BY-SA4.0; upstream attribution in dependency/data.'
    svg=start(1200,630,'Conditional reference-word dependency baseline and document slices',desc)
    svg.extend([text(35,35,'Gold words + gold UPOS: conditional structure, not raw-text parsing',22,BLUE),text(35,66,'Train351 / dev13 / test76 sentences;11 /1 /3 documents. Test denominator548 non-PUNCT words.',16)])
    y=112
    for mode,color,name in models:
        row=next(x for x in r['summary'] if x['model']==mode and x['split']=='test' and x['metric']=='primary')
        svg.append(text(35,y,name,18,color));y+=16
        for key in ['UAS','LAS']:
            value=row[key];count=row['uas_correct' if key=='UAS' else 'las_correct']
            svg.extend([text(35,y+16,key,15,color),f'<rect x="115" y="{y}" width="700" height="21" fill="#edf0f2"/>',f'<rect x="115" y="{y}" width="{700*value}" height="21" fill="{color}"/>',text(840,y+17,f'{count}/548 = {value:.6f}',16,color)]);y+=32
        y+=16
    svg.append(text(35,340,'Same selected models, grouped by original test document (LAS)',20,BLUE))
    for j,doc in enumerate(['P213','P218','P301']):
        x=35+j*390;items={mode:r['test_slices'][mode]['by_document'][doc] for mode,_,_ in models};n=items['geometry']['scored_words']
        svg.append(text(x,379,f'{doc}: {n} scored words',17))
        for k,(mode,color,name) in enumerate(models):
            item=items[mode];yy=402+k*56;svg.extend([text(x,yy,name,14,color),f'<rect x="{x}" y="{yy+8}" width="330" height="19" fill="#edf0f2"/>',f'<rect x="{x}" y="{yy+8}" width="{330*item["LAS"]}" height="19" fill="{color}"/>',text(x,yy+43,f'{item["las_correct"]}/{n} = {item["LAS"]:.6f}',14,color)])
    svg.extend([text(35,562,'No nonprojective test references in this subset; projective UAS ceiling =1.',16),text(35,590,'Two unseen full relation labels limit LAS to546/548, even with ideal heads.',16),text(35,615,'Not76 independent documents, not an end-to-end parser benchmark, not semantic correctness.',15),'</g></svg>'])
    (output/'dependency-baselines.svg').write_text('\n'.join(svg)+'\n')
    rows=[json.loads(line) for line in (root/'predictions.jsonl').read_text().splitlines()]
    examples=sorted([x for x in rows if x['model']=='upos_geometry' and x['split']=='test' and not x['primary']['exact_scored_tree']],key=lambda x:x['form_sha256'])[:2]
    svg=start(1240,1000,'Literal reference and predicted arcs on two fixed diagnostic examples',
              'First two failing UPOS-model test sentences sorted by pre-existing FORM hash, selected only after the frozen evaluation for explanation. All positions and full labels are unchanged. Gray PUNCT rows are displayed but excluded from primary counts. Gold UPOS is supplied, not predicted. Text/annotations and derived display under CC BY-SA4.0 from UD Swedish-Talbanken fixed commit; see dependency/data for attribution. These are annotation comparisons, not human adjudications of meaning.')
    svg.extend([text(30,34,'Actual failures: reference HEAD:relation versus frozen model prediction',22,BLUE),text(30,65,'Selection for explanation: first two failing test FORM hashes; no model or alpha changed.',15)])
    top=110
    for index,item in enumerate(examples):
        p=item['primary'];svg.append(text(30,top,f'{index+1}. {item["sample_id"]}   UAS {p["uas_correct"]}/{p["denominator"]}; LAS {p["las_correct"]}/{p["denominator"]}',18,BLUE))
        for x,label in [(30,'ID'),(80,'FORM'),(295,'gold UPOS'),(420,'reference head'),(570,'reference relation'),(765,'pred head'),(880,'pred relation'),(1090,'LAS arc?')]:svg.append(text(x,top+29,label,13))
        y=top+42
        for g,pred in zip(item['reference'],item['prediction']):
            lines=textwrap.wrap(g['form'],width=24,break_long_words=True,break_on_hyphens=False) or [''];height=max(27,len(lines)*17+7)
            excluded=g['upos']=='PUNCT';correct=g['head']==pred['head'] and g['relation']==pred['relation'];color=GRAY if excluded else GREEN if correct else RED
            if excluded:svg.append(f'<rect x="25" y="{y-17}" width="1190" height="{height}" fill="#f1f2f3"/>')
            for x,value in [(30,g['id']),(295,g['upos']),(420,g['head']),(570,g['relation']),(765,pred['head']),(880,pred['relation']),(1090,'excluded' if excluded else 'ok' if correct else 'wrong')]:svg.append(text(x,y,value,13,color))
            for k,word in enumerate(lines):svg.append(text(80,y+k*17,word,13,color))
            y+=height
        top=y+53
    svg.extend([text(30,955,'Gray rows are not deleted from trees. Full FORM, IDs and labels remain in raw predictions.',15),text(30,983,'Reference labels are benchmark annotations; no new human Swedish meaning/adjudication study is claimed.',15),'</g></svg>'])
    (output/'dependency-errors.svg').write_text('\n'.join(svg)+'\n')
    (output/'diagnostic-examples.json').write_text(json.dumps([dict(sample_id=x['sample_id'],form_sha256=x['form_sha256'],primary=x['primary']) for x in examples],ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();render(a.results,a.output)
