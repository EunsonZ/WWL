"""SVG diagrams from the exact saved trees, dependencies and evaluation rows."""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

BLUE='#185d9a';PURPLE='#793f91';GRAY='#56616c';ORANGE='#b75a14';GREEN='#24734d'


def text(x,y,value,size=16,color=GRAY,anchor='middle'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(value))}</text>'


def line(x1,y1,x2,y2,color=GRAY,arrow=False):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.8"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>'


def start(width,height,title,desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            '<title id="title">'+escape(title)+'</title><desc id="desc">'+escape(desc)+'</desc>',
            '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="'+GRAY+'"/></marker></defs>',
            '<rect width="100%" height="100%" fill="white"/><g font-family="DejaVu Sans, sans-serif">']


def constituency(tree,top):
    out=[];cursor=0;leaf_y=top+335
    def visit(node,depth):
        nonlocal cursor
        if len(node)==2:
            x=85+cursor*106;cursor+=1;y=top+depth*55
            out.extend([text(x,y,node[0],16,BLUE),line(x,y+7,x,leaf_y-24),text(x,leaf_y,f'{cursor}: {node[1]}',15)])
            return x,y
        before=len(out);children=[visit(node[1],depth+1),visit(node[2],depth+1)]
        x=sum(p[0] for p in children)/2;y=top+depth*55
        connectors=[line(x,y+7,xx,yy-18) for xx,yy in children]
        out[before:before]=connectors+[text(x,y,node[0],16,PURPLE if node[0]=='PP' else BLUE)]
        return x,y
    visit(tree,0);return out


def dependencies(rows,attachment,top):
    coords={0:(855,top),2:(855,top+80),1:(700,top+170),3:(930,top+170)}
    coords.update({5:(1035,top+250),4:(1120,top+325)} if attachment=='NP' else {5:(1100,top+170),4:(1100,top+265)})
    out=[]
    for row in rows:
        h,d=row['head'],row['id'];x1,y1=coords[h];x2,y2=coords[d];color=PURPLE if d==5 else GRAY
        out.append(line(x1,y1+13,x2,y2-22,color,True))
        out.append(text((x1+x2)/2+(-24 if d in (1,3) else 24),(y1+y2)/2+4,row['relation'],14,color))
    for i,(x,y) in coords.items():
        value='0: ROOT (artificial)' if i==0 else f'{i}: {rows[i-1]["form"]}'
        out.extend([f'<rect x="{x-72}" y="{y-20}" width="144" height="32" rx="7" fill="'+('#f0e7f6' if i==5 else '#edf4f9')+'"/>',text(x,y+2,value,14,PURPLE if i==5 else BLUE)])
    return out


def render(root,output):
    root,output=Path(root),Path(output);output.mkdir(parents=True,exist_ok=True);r=json.loads((root/'structure-results.json').read_text())
    svg=start(1260,1050,'Two constituent trees and their declared dependency conversions',
              'The same five words keep IDs1..5. On the left are the two published CKY trees. On the right arrows point from head to dependent, with artificial ROOT0. Only the incoming head and relation of scopes differ: birds to scopes nmod versus saw to scopes obl. with is case dependent of scopes in both. Grammar and head rules allow analyses; neither diagram proves which situation occurred.')
    svg.extend([text(35,32,'Same words, different PP attachment',24,BLUE,'start'),text(35,59,'Constituency: phrase nodes remain',16,GRAY,'start'),text(655,59,'Dependencies: word heads; head -> dependent',16,GRAY,'start')])
    by={x['attachment']:x for x in r['conversions']}
    for attachment,offset,title in [('NP',100,'A. NP attachment: birds have scopes'),('VP',580,'B. VP attachment: scopes used in seeing')]:
        svg.append(text(35,offset-12,title,19,PURPLE,'start'));svg+=constituency(by[attachment]['tree'],offset+22);svg+=dependencies(by[attachment]['rows'],attachment,offset+22)
        svg.append(line(35,offset+395,1225,offset+395,'#d4dce3'))
    svg.extend([text(35,1010,'Both: saw -> I (nsubj), saw -> birds (obj), scopes -> with (case), ROOT -> saw (root).',16,GRAY,'start'),text(35,1036,'Changed: birds -> scopes (nmod)  versus  saw -> scopes (obl). IDs denote positions, not word meanings.',16,PURPLE,'start'),'</g></svg>'])
    (output/'constituency-dependencies.svg').write_text('\n'.join(svg)+'\n')
    svg=start(1120,500,'Attachment scores depend on which reference words are evaluated',
              'All bars use the NP reference and VP prediction. Correct punctuation raises both from4/5 to5/6 without repairing scopes. Excluding punctuation restores4/5, also excluding the real root word yields3/4. Artificial ROOT0 never adds a denominator unit. A label-only error has UAS5/5 and LAS4/5. All units are proportions, not semantic accuracy.')
    svg.extend([text(35,32,'One attachment error; denominator policy changes the number',23,BLUE,'start'),text(35,62,'UAS = correct heads / scored words; LAS = correct head AND label / scored words',16,GRAY,'start')])
    selections=[('other_attachment','all_words','5 words'),('with_correct_punctuation','all_words','add correct punctuation'),('with_correct_punctuation','without_punct','exclude punctuation'),('with_correct_punctuation','without_punct_or_root_word','also exclude real root'),('label_only_error','all_words','label-only error')]
    for j,(case,policy,label) in enumerate(selections):
        row=next(x for x in r['metrics'] if x['case']==case and x['policy']==policy);y=110+j*65
        svg.append(text(35,y+20,label,15,GRAY,'start'))
        for k,(key,color) in enumerate([('UAS',BLUE),('LAS',ORANGE)]):
            yy=y+k*22;value=row[key];count=row['uas_correct' if key=='UAS' else 'las_correct']
            svg.extend([f'<rect x="300" y="{yy}" width="600" height="17" fill="#edf0f2"/>',f'<rect x="300" y="{yy}" width="{600*value}" height="17" fill="{color}"/>',text(925,yy+14,f'{key} {count}/{row["denominator"]} = {value:.3f}',14,color,'start')])
    svg.extend([text(35,469,'None of these policies resolves meaning. ROOT0 is not a scored word; saw (the root word) can be.',15,GRAY,'start'),'</g></svg>'])
    (output/'attachment-denominators.svg').write_text('\n'.join(svg)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();render(args.results,args.output)
