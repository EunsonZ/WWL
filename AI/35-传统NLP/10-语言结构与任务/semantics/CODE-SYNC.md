---
type: reference
stage: 3
aliases: []
prerequisites:
  - "[[AI/35-传统NLP/10-语言结构与任务/82-语义篇章与翻译任务复算]]"
sources: []
---
# 语义与翻译实践的规范源码镜像

运行、条件与实际输出见[[AI/35-传统NLP/10-语言结构与任务/82-语义篇章与翻译任务复算|实践82]]；本页是精确镜像，不作独立实现/核查证据。修改以.py为真源并同步。

## semantics_lab.py

<!-- code-sync: AI/35-传统NLP/10-语言结构与任务/semantics/code-sync/semantics_lab.py -->
```python
#!/usr/bin/env python3
"""Controlled raw-text extraction, explicit coreference, typed scope and MT diagnostics.

No learned NLP/MT model and no inference of real-world truth. Standard library only.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import itertools
import json
import math
from pathlib import Path
import re
from xml.sax.saxutils import escape

EPS = 1e-12
TOKEN_RE = re.compile(r'[A-Za-z]+|\.')


def tokenize(text):
    if not isinstance(text, str) or not text or len(text) > 20000:
        raise ValueError('nonempty controlled English text <= 20000 codepoints required')
    result=[]; end=0
    for match in TOKEN_RE.finditer(text):
        if text[end:match.start()].strip():
            raise ValueError('unsupported characters, not silently discarded')
        result.append({'form':match.group(),'start':match.start(),'end':match.end()})
        end=match.end()
    if text[end:].strip() or not result:
        raise ValueError('unsupported or empty tokenization')
    return result


def parse(text, people):
    tokens=tokenize(text); words=[t['form'] for t in tokens]
    ends=[i for i,w in enumerate(words) if w=='.']
    if not ends or ends[-1]!=len(words)-1 or len(ends)>8:
        raise ValueError('complete period-terminated controlled clauses required')
    mentions=[]; events=[]; start=0
    def mention(a,b,typ,sent):
        name='m'+str(len(mentions)); form=' '.join(words[a:b])
        entity=people.get(form) if typ=='PERSON' else 'b'
        mentions.append({'id':name,'form':form,'type':typ,'token_span':[a,b],
            'char_span':[tokens[a]['start'],tokens[b-1]['end']],'sentence':sent,'entity':entity})
        return name
    for sent,end in enumerate(ends):
        clause=words[start:end]; typ=None; polarity='positive'; manner=None; slots={}; trigger=None
        # Full-string matching over declared token units; no dependency/POS oracle.
        if len(clause) in (6,7) and clause[1]=='gave' and clause[-2]=='to' and clause[0] in people and clause[-1] in people:
            np=clause[2:-2]
            if np not in (['a','book'],['a','red','book']): raise ValueError('unsupported theme')
            typ='GIVE'; slots={'giver':(0,1,'PERSON'),'theme':(2,len(clause)-2,'THING'),'recipient':(len(clause)-1,len(clause),'PERSON')}; trigger=1
        elif len(clause) in (7,8) and clause[1:3]==['was','given'] and clause[-2]=='by' and clause[0] in people and clause[-1] in people:
            np=clause[3:-2]
            if np not in (['a','book'],['a','red','book']): raise ValueError('unsupported theme')
            typ='GIVE'; slots={'recipient':(0,1,'PERSON'),'theme':(3,len(clause)-2,'THING'),'giver':(len(clause)-1,len(clause),'PERSON')}; trigger=2
        else:
            person=lambda w: w in people or w in ('She','she','her')
            if len(clause)==3 and person(clause[0]) and person(clause[2]) and clause[1] in ('thanked','praised'):
                typ='THANK' if clause[1]=='thanked' else 'PRAISE'; slots={'agent':(0,1,'PERSON'),'target':(2,3,'PERSON')}; trigger=1
            elif len(clause)==5 and person(clause[0]) and person(clause[4]) and clause[1:4]==['did','not','thank']:
                typ='THANK'; polarity='negative'; slots={'agent':(0,1,'PERSON'),'target':(4,5,'PERSON')}; trigger=3
            elif len(clause)==4 and person(clause[0]) and person(clause[3]) and clause[1:3]==['reluctantly','thanked']:
                typ='THANK'; manner='reluctant'; slots={'agent':(0,1,'PERSON'),'target':(3,4,'PERSON')}; trigger=2
        if typ is None: raise ValueError('unsupported construction; no asserted event invented')
        if typ=='GIVE' and events: raise ValueError('one introductory GIVE only; new book identity not silently collapsed')
        roles={}
        for role,(a,b,t) in sorted(slots.items(),key=lambda kv:kv[1][0]):
            roles[role]=mention(start+a,start+b,t,sent)
        events.append({'id':'e'+str(sent),'type':typ,'trigger':start+trigger,'polarity':polarity,
            'roles':roles,'manner':manner,'red_theme':typ=='GIVE' and 'red' in clause})
        start=end+1
    return {'text':text,'tokens':tokens,'mentions':mentions,'events':events}


def assignments(doc, context=None):
    # Pronouns in this fragment refer to a PERSON introduced in sentence 0.
    fixed={m['id']:m['entity'] for m in doc['mentions'] if m['entity'] is not None}
    pronouns=[m['id'] for m in doc['mentions'] if m['entity'] is None]
    candidates=sorted({m['entity'] for m in doc['mentions'] if m['sentence']==0 and m['type']=='PERSON' and m['entity'] is not None})
    out=[]
    for values in itertools.product(candidates,repeat=len(pronouns)):
        g=dict(fixed,**dict(zip(pronouns,values)))
        if any(e['type'] in ('THANK','PRAISE') and g[e['roles']['agent']]==g[e['roles']['target']] for e in doc['events']):continue
        if context is not None:
            give=next((e for e in doc['events'] if e['type']=='GIVE'),None)
            thank=next((e for e in doc['events'] if e['type']=='THANK'),None)
            if give is None or thank is None: raise ValueError('context needs GIVE and THANK')
            if any(g[thank['roles'][r]]!=g[give['roles'][gr]] for r,gr in context.items()):continue
        out.append(g)
    return out


def nearest(doc):
    names=[m for m in doc['mentions'] if m['sentence']==0 and m['type']=='PERSON' and m['entity'] is not None]
    if not names:raise ValueError('no declared antecedent')
    closest=max(names,key=lambda m:m['token_span'][1])['entity']
    return {m['id']:m['entity'] if m['entity'] is not None else closest for m in doc['mentions']}


def frames(doc,g):
    return [{'type':e['type'],'polarity':e['polarity'],'roles':{k:g[m] for k,m in e['roles'].items()},'manner':e['manner'],'theme_properties':['red'] if e['red_theme'] else []} for e in doc['events']]


def pair_set(g):
    return {tuple(sorted((a,b))) for a,b in itertools.combinations(g,2) if g[a]==g[b]}


def f1(pred,gold):
    pred=set(pred);gold=set(gold);tp=len(pred&gold);p=len(pred);g=len(gold)
    return {'tp':tp,'predicted':p,'reference':g,'precision':tp/p if p else None,
            'recall':tp/g if g else None,'f1':2*tp/(p+g) if p+g else None}


def role_pairs(fs):
    return {(i,role,entity) for i,e in enumerate(fs) for role,entity in e['roles'].items()}


def typed_scope(students,books,pairs):
    if len(set(students))!=len(students) or len(set(books))!=len(books):raise ValueError('duplicate domain IDs')
    rel={tuple(p) for p in pairs}
    if any(s not in students or b not in books for s,b in rel):raise ValueError('Read outside typed domain')
    a=all(any((s,b) in rel for b in books) for s in students)
    c=any(all((s,b) in rel for s in students) for b in books)
    return {'A':a,'C':c,'not_A':not a,'each_has_unread':all(any((s,b) not in rel for b in books) for s in students),
            'row_witnesses':{s:[b for b in books if (s,b) in rel] for s in students},
            'common_books':[b for b in books if all((s,b) in rel for s in students)]}


def ngrams(tokens,n):
    return Counter(tuple(tokens[i:i+n]) for i in range(max(0,len(tokens)-n+1)))


def bleu(candidate,reference,order):
    if order not in (1,4):raise ValueError('declared BLEU1 or BLEU4 only')
    rt=[t['form'].lower() for t in tokenize(reference)]
    if not candidate.strip():
        return {'order':order,'candidate_length':0,'reference_length':len(rt),'bp':0.,
            'ngrams':[{'n':n,'matched':0,'total':0,'precision':None} for n in range(1,order+1)],'score':0.}
    ct=[t['form'].lower() for t in tokenize(candidate)]
    rows=[]
    for n in range(1,order+1):
        cc=ngrams(ct,n);rr=ngrams(rt,n)
        num=sum(min(k,rr[g]) for g,k in cc.items());den=sum(cc.values())
        rows.append({'n':n,'matched':num,'total':den,'precision':num/den if den else None})
    bp=math.exp(min(0,1-len(rt)/len(ct)))
    if any(row['total']==0 for row in rows):score=None
    elif any(row['matched']==0 for row in rows):score=0.
    else:score=bp*math.exp(sum(math.log(row['precision']) for row in rows)/order)
    return {'order':order,'candidate_length':len(ct),'reference_length':len(rt),'bp':bp,'ngrams':rows,'score':score}


def build_prefix(candidates):
    if not candidates or any(type(c['weight']) is not int or c['weight']<=0 for c in candidates):raise ValueError('positive integer candidate masses required')
    total=sum(c['weight'] for c in candidates);mass=defaultdict(Fraction);leaves={}
    for c in candidates:
        seq=tuple(c['tokens'])+('<EOS>',)
        if seq in leaves or '<EOS>' in c['tokens']:raise ValueError('duplicate candidate or interior EOS')
        p=Fraction(c['weight'],total);leaves[seq]=p
        for n in range(len(seq)+1):mass[seq[:n]]+=p
    children=defaultdict(dict)
    for prefix,value in mass.items():
        if prefix:children[prefix[:-1]][prefix[-1]]=value/mass[prefix[:-1]]
    if any(sum(row.values())!=1 for row in children.values()):raise AssertionError('prefix normalization')
    return mass,children,leaves


def beam(candidates,width):
    if type(width) is not int or width<1:raise ValueError('beam width positive integer')
    mass,children,leaves=build_prefix(candidates)
    frontier=[((),Fraction(1))];trace=[]
    for _ in range(max(map(len,leaves))+1):
        expanded=[]
        for prefix,prob in frontier:
            if prefix and prefix[-1]=='<EOS>':expanded.append((prefix,prob));continue
            expanded.extend((prefix+(token,),prob*q) for token,q in children[prefix].items())
        frontier=sorted(expanded,key=lambda item:(-item[1],item[0]))[:width]
        trace.append([{'tokens':list(s),'probability':str(p)} for s,p in frontier])
        if all(s[-1]=='<EOS>' for s,p in frontier):break
    if not frontier or any(s[-1]!='<EOS>' for s,p in frontier):raise AssertionError('nontermination')
    return {'tokens':list(frontier[0][0][:-1]),'probability':str(frontier[0][1]),'trace':trace}


def close(a,b):
    if abs(a-b)>EPS:raise AssertionError(f'{a} != {b}')


def svg(path,title,body):
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="650" viewBox="0 0 1200 650">\n'
        f'<title>{escape(title)}</title><desc>同一inputs与results中的区间、角色、共指或译文计分；非真人语义认证。</desc>\n'
        '<rect width="1200" height="650" fill="#fbfcfe"/><g font-family="Arial, sans-serif" fill="#20334b">\n'+body+'\n</g></svg>\n')


def text(x,y,value,size=20,color='#20334b'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(str(value))}</text>\n'


def render(out,result):
    doc=result['document'];g=result['coreference']['recipient_thanks_giver'][0]
    body=text(35,40,'Same mentions, different entity assignments',28)
    body+=text(35,80,doc['text'],22)
    for i,m in enumerate(doc['mentions']):
        x=45+i*225;body+=f'<rect x="{x}" y="125" width="205" height="120" rx="8" fill="#e0ebf4"/>'
        body+=text(x+12,157,m['id']+': '+m['form'],19)+text(x+12,190,f"[{m['token_span'][0]},{m['token_span'][1]}) "+m['type'],16)+text(x+12,222,'entity: '+g[m['id']],18)
    body+=text(45,295,'GIVE: giver M / theme b / recipient L',24)
    body+=text(45,342,'Context R: THANK L -> M',24,'#176799')
    body+=text(45,387,'Context G: THANK M -> L',24,'#b56425')
    body+=text(45,438,'Unknown context: both assignments remain admissible.',22)
    s=result['scores']['nearest_pair']
    body+=text(45,495,f"Nearest baseline: mentions correct, positive-pair F1 = {s['tp']}/{s['predicted']} P, {s['tp']}/{s['reference']} R -> {s['f1']:.2f}",19)
    body+=text(45,548,'Coreference is identity; discourse Result is a separate claim.',21)
    body+=text(45,600,'Offsets are half-open; codepoint and token spans are saved in JSON.',18)
    svg(out/'figures'/'roles-coreference.svg','Mentions, roles and identity',body)
    body=text(35,40,'Lexical overlap is not a meaning certificate',28)
    body+=text(35,80,'Same Chinese source, same visible recipient-thanks-giver context',20)
    for j,label in enumerate(['Candidate','BLEU1','BLEU4','Core facts','Manner same']):body+=text([35,450,600,760,940][j],138,label,20)
    for i,row in enumerate(result['translation']):
        y=190+i*67
        vals=[row['id'],f"{row['bleu1']['score']:.3f}",f"{row['bleu4']['score']:.3f}",'same' if row['core_equal'] else 'CHANGED',str(row['manner_equal'])]
        for x,v in zip([35,450,600,760,940],vals):body+=text(x,y,v,22,'#b34e2b' if v=='CHANGED' else '#20334b')
    body+=text(35,560,'Scores: one aligned paragraph, lowercase word + punctuation tokens.',18)
    body+=text(35,600,'Manual semantic protocol is explicit; no learned general MT or human rating.',18)
    svg(out/'figures'/'translation-layers.svg','Translation scores and preserved meaning',body)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    base=Path(__file__).resolve().parents[1]
    parser.add_argument('--input',type=Path,default=base/'inputs.json')
    parser.add_argument('--output-dir',type=Path,default=base)
    args=parser.parse_args();data=json.loads(args.input.read_text())
    out=args.output_dir
    for sub in ('results','figures'):(out/sub).mkdir(parents=True,exist_ok=True)
    doc=parse(data['document'],data['people'])
    gold_spans={tuple(m) for m in data['gold_mentions']}
    observed={(m['token_span'][0],m['token_span'][1],m['type']) for m in doc['mentions']}
    if observed!=gold_spans:raise AssertionError('manual mention reference mismatch')
    for m in doc['mentions']:
        a,b=m['char_span']
        if data['document'][a:b]!=m['form']:raise AssertionError('raw codepoint offset mismatch')
    contexts={key:assignments(doc,con) for key,con in data['contexts'].items()}
    assert len(contexts['unknown'])==2 and len(contexts['recipient_thanks_giver'])==len(contexts['giver_thanks_recipient'])==1
    gold=data['gold_assignment'];assert contexts['recipient_thanks_giver'][0]==gold
    assert frames(doc,gold)==data['gold_frames']
    bad=nearest(doc);pair_score=f1(pair_set(bad),pair_set(gold));close(pair_score['f1'],.4)
    boundary=set(observed);boundary.remove((2,5,'THING'));boundary.add((4,5,'THING'))
    boundary_score=f1(boundary,gold_spans);close(boundary_score['f1'],.8)
    swapped=frames(doc,gold);swapped[0]['roles']['giver'],swapped[0]['roles']['recipient']=swapped[0]['roles']['recipient'],swapped[0]['roles']['giver']
    swapped_score=f1(role_pairs(swapped),role_pairs(data['gold_frames']));close(swapped_score['f1'],.6)
    nearest_role=f1(role_pairs(frames(doc,bad)),role_pairs(data['gold_frames']));close(nearest_role['f1'],.8)
    type_doc=parse('Mira gave a red book to Lena. Lena praised Mira.',data['people'])
    type_frames=frames(type_doc,assignments(type_doc)[0])
    type_correct=sum(p['type']==g['type'] for p,g in zip(type_frames,data['gold_frames']))
    assert type_correct==1
    scope_rows=[];counts=Counter()
    for bits in itertools.product([False,True],repeat=4):
        pairs=[[data['students'][i],data['books'][j]] for i in range(2) for j in range(2) if bits[i*2+j]]
        row=typed_scope(data['students'],data['books'],pairs);counts[str((row['A'],row['C']))]+=1
        scope_rows.append({'matrix':[list(bits[:2]),list(bits[2:])],**row})
    assert counts=={'(False, False)':7,'(True, False)':2,'(True, True)':7}
    reference=parse(data['reference'],data['people']);rg=assignments(reference)[0];rf=frames(reference,rg)
    translation=[];candidates=[]
    for c in data['candidates']:
        parsed=parse(c['text'],data['people']);g=assignments(parsed)[0];fs=frames(parsed,g)
        core=lambda fs:[{k:v for k,v in f.items() if k!='manner'} for f in fs]
        row={'id':c['id'],'text':c['text'],'parsed':parsed,'frames':fs,'bleu1':bleu(c['text'],data['reference'],1),
            'bleu4':bleu(c['text'],data['reference'],4),'core_equal':core(fs)==core(rf),'manner_equal':[f['manner'] for f in fs]==[f['manner'] for f in rf]}
        translation.append(row);candidates.append({'tokens':[t['form'] for t in parsed['tokens']],'weight':c['weight']})
    lookup={r['id']:r for r in translation}
    close(lookup['roles_swapped']['bleu1']['score'],1)
    assert lookup['passive']['core_equal'] and not lookup['roles_swapped']['core_equal'] and not lookup['negative']['core_equal']
    assert lookup['attitude']['core_equal'] and not lookup['attitude']['manner_equal']
    assert lookup['roles_swapped']['bleu4']['score']>lookup['passive']['bleu4']['score']
    for c in candidates:
        mass,ch,leaves=build_prefix(candidates);prefix=();p=Fraction(1)
        for token in c['tokens']+['<EOS>']:p*=ch[prefix][token];prefix+=(token,)
        assert p==leaves[prefix]
    fullmap=max(build_prefix(candidates)[2].items(),key=lambda item:item[1])
    assert list(fullmap[0][:-1])==candidates[2]['tokens']
    fixture=data['decoder_fixture'];greedy=beam(fixture,1);beam2=beam(fixture,2)
    assert greedy['tokens']==fixture[0]['tokens'] and beam2['tokens']==fixture[2]['tokens']
    padding=[]
    for count in data['padding_counts']:
        suffix=' The door stayed open.'*count
        score=bleu(lookup['roles_swapped']['text']+suffix,data['reference']+suffix,4)
        padding.append({'added_sentences':count,'bleu4':score})
    assert padding[0]['bleu4']['score']<padding[1]['bleu4']['score']<padding[2]['bleu4']['score']
    rejected=[]
    for raw in data['refusals']:
        try:parse(raw,data['people'])
        except ValueError:rejected.append(raw)
        else:raise AssertionError('unsupported raw accepted')
    try:typed_scope(['Ada'],['red'],[['Ada','blue']])
    except ValueError:rejected.append('Read outside book domain')
    else:raise AssertionError('untyped Read accepted')
    first=[t['form'] for t in reference['tokens'][:8]]
    for i,j in data['first_alignment']:
        assert 0<=i<len(data['source_first_tokens']) and 0<=j<len(first)
    result={'status':'PASS','input_scope':data['provenance'],'document':doc,'coreference':contexts,'nearest_assignment':bad,
        'layered_errors':{'boundary':{'predicted_spans':sorted(boundary),'reference_spans':sorted(gold_spans),'score':boundary_score},
            'role_swap':{'predicted_frames':swapped,'score':swapped_score},
            'predicate':{'raw_text':type_doc['text'],'predicted_frames':type_frames,'type_correct':type_correct,'type_total':2},
            'nearest':{'predicted_assignment':bad,'predicted_frames':frames(doc,bad),'admissible':bad in contexts['unknown']}},
        'scores':{'nearest_pair':pair_score,'boundary':boundary_score,'swapped_roles':swapped_score,'nearest_entity_roles':nearest_role},
        'scope':{'diagonal':typed_scope(data['students'],data['books'],data['read_pairs']),'all_models':scope_rows,'counts':dict(counts),
            'empty_students':typed_scope([],data['books'],[]),'empty_books':typed_scope(data['students'],[],[]),'both_empty':typed_scope([],[],[])},
        'translation':translation,'alignment':{'source':data['source_first_tokens'],'target':first,'links':data['first_alignment']},
        'decoder':{'greedy':greedy,'beam2':beam2,'exact_probability':'2/5','paragraph_map_tokens':list(fullmap[0][:-1]),'paragraph_map_probability':str(fullmap[1])},
        'padding':padding,'short_bleu4':bleu('Mira thanked Lena', 'Mira thanked Lena .',4),'rejected':rejected}
    (out/'results'/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    # Raw candidates and all admissible assignments stay inspectable, not only aggregate scores.
    with (out/'results'/'predictions.jsonl').open('w') as f:
        for row in translation:f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    render(out,result)
    print('PASS: raw controlled extraction, two admissible coreference partitions, explicit-context filtering')
    print(f"pair F1={pair_score['f1']:.1f}; boundary F1={boundary_score['f1']:.1f}; swapped-role F1={swapped_score['f1']:.1f}")
    print('typed 2x2 scope counts: FF=7, TF=2, TT=7, FT=0')
    for row in translation:print(f"{row['id']}: BLEU1={row['bleu1']['score']:.9f} BLEU4={row['bleu4']['score']:.9f} core={row['core_equal']} manner={row['manner_equal']}")
    print(f"greedy={greedy['probability']}; beam2={beam2['probability']}; exact MAP={result['decoder']['paragraph_map_probability']} selects wrong paragraph roles")
    print('rejected='+str(len(rejected)))


if __name__=='__main__':main()
```

## test_semantics_lab.py

<!-- code-sync: AI/35-传统NLP/10-语言结构与任务/semantics/code-sync/test_semantics_lab.py -->
```python
"""Contract variants that distinguish semantic errors from lexical matching."""
import itertools
import unittest
import semantics_lab as lab

PEOPLE={'Mira':'M','Lena':'L','Noor':'N','Omar':'O'}


class ContractTests(unittest.TestCase):
    def test_voice_and_theme_variants(self):
        for giver,recipient in itertools.permutations(PEOPLE,2):
            for np in ('a book','a red book'):
                with self.subTest(giver=giver,recipient=recipient,np=np):
                    active=lab.parse(f'{giver} gave {np} to {recipient}.',PEOPLE)
                    passive=lab.parse(f'{recipient} was given {np} by {giver}.',PEOPLE)
                    fa=lab.frames(active,lab.assignments(active)[0])[0]
                    fp=lab.frames(passive,lab.assignments(passive)[0])[0]
                    self.assertEqual(fa,fp)
                    self.assertEqual(fa['roles'],{'giver':PEOPLE[giver],'theme':'b','recipient':PEOPLE[recipient]})
                    self.assertEqual(fa['theme_properties'],['red'] if np=='a red book' else [])

    def test_negation_and_additional_attitude(self):
        a=lab.parse('Lena thanked Mira.',PEOPLE)
        n=lab.parse('Lena did not thank Mira.',PEOPLE)
        h=lab.parse('Lena reluctantly thanked Mira.',PEOPLE)
        af=lab.frames(a,lab.assignments(a)[0])[0]
        nf=lab.frames(n,lab.assignments(n)[0])[0]
        hf=lab.frames(h,lab.assignments(h)[0])[0]
        self.assertEqual(af['roles'],nf['roles']);self.assertNotEqual(af['polarity'],nf['polarity'])
        self.assertEqual(af['roles'],hf['roles']);self.assertNotEqual(af['manner'],hf['manner'])

    def test_no_antecedent_or_reflexive_guess(self):
        self.assertEqual(lab.assignments(lab.parse('She thanked her.',PEOPLE)),[])
        self.assertEqual(lab.assignments(lab.parse('Mira thanked Mira.',PEOPLE)),[])
        d=lab.parse('Mira gave a book to Lena. She thanked her.',PEOPLE)
        self.assertEqual(len(lab.assignments(d)),2)
        self.assertEqual(len(lab.assignments(d,{'agent':'recipient','target':'recipient'})),0)

    def test_permutation_invariant_bag_does_not_preserve_roles(self):
        r='Mira thanked Lena.'; c='Lena thanked Mira.'
        self.assertEqual(lab.bleu(c,r,1)['score'],1)
        a=lab.parse(r,PEOPLE);b=lab.parse(c,PEOPLE)
        self.assertNotEqual(lab.frames(a,lab.assignments(a)[0]),lab.frames(b,lab.assignments(b)[0]))
        repeated=lab.bleu('Mira Mira Mira Mira.','Mira thanked Lena.',1)
        self.assertEqual(repeated['ngrams'][0]['matched'],2)  # Mira once + period once.
        self.assertIsNone(lab.bleu('Mira thanked Lena','Mira thanked Lena.',4)['score'])
        self.assertEqual(lab.bleu('', 'Mira thanked Lena.',4)['score'],0)

    def test_empty_typed_domains(self):
        self.assertEqual((lab.typed_scope([],['b'],[])['A'],lab.typed_scope([],['b'],[])['C']),(True,True))
        self.assertEqual((lab.typed_scope(['s'],[],[])['A'],lab.typed_scope(['s'],[],[])['C']),(False,False))
        self.assertEqual((lab.typed_scope([],[],[])['A'],lab.typed_scope([],[],[])['C']),(True,False))
        with self.assertRaises(ValueError):lab.typed_scope(['s'],['b'],[['b','s']])

    def test_prefix_mass_and_invalid_candidates(self):
        cs=[{'tokens':['a'],'weight':2},{'tokens':['a','b'],'weight':1},{'tokens':['c'],'weight':3}]
        mass,children,leaves=lab.build_prefix(cs)
        for leaf,p in leaves.items():
            prefix=();product=lab.Fraction(1)
            for token in leaf:product*=children[prefix][token];prefix+=(token,)
            self.assertEqual(product,p)
        with self.assertRaises(ValueError):lab.build_prefix([{'tokens':['a'],'weight':0}])
        with self.assertRaises(ValueError):lab.beam(cs,True)
        for text in ('Mira promised to give a book to Lena.','Mira did not give a book to Lena.','Mira thanked Lena?','米拉感谢莉娜。','Mira gave a book to Lena. Noor gave a book to Omar.'):
            with self.assertRaises(ValueError):lab.parse(text,PEOPLE)


if __name__=='__main__':unittest.main(verbosity=2)
```
