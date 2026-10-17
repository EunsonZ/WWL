"""Exact basic-UD projection of a fixed licensed release; no model-based filtering."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from shutil import copyfile
from fetch_talbanken import EXPECTED_SHA256,COMMIT


def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def read_source(path):
    doc=None;sid=None;rows=[];sentences=[];excluded=Counter();start_line=None
    for number,line in enumerate(path.read_text().splitlines()+[''],1):
        if line.startswith('# newdoc id = '):doc=line.split(' = ',1)[1]
        elif line.startswith('# sent_id = '):sid=line.split(' = ',1)[1]
        elif not line:
            if rows:
                if not doc or not sid:raise ValueError('missing document/sentence identity')
                sample=doc+'::'+sid
                sentences.append(dict(sample_id=sample,doc_id=doc,sent_id=sid,source_line=start_line,rows=rows,
                                      form_sha256=digest(json.dumps([r['form'] for r in rows],ensure_ascii=False,separators=(',',':')).encode())))
                rows=[];start_line=None
        elif not line.startswith('#'):
            f=line.split('\t')
            if len(f)!=10:raise ValueError('CoNLL-U requires10 columns')
            if f[0].isdigit():
                if start_line is None:start_line=number
                rows.append(dict(id=int(f[0]),form=f[1],upos=f[3],head=int(f[6]),relation=f[7]))
            elif '-' in f[0]:excluded['multiword_range']+=1
            elif '.' in f[0]:excluded['empty_node']+=1
            else:raise ValueError('unknown ID kind')
    if len({s['sample_id'] for s in sentences})!=len(sentences):raise ValueError('duplicate sample identity')
    return sentences,dict(excluded)


def prepare(raw_dir,output):
    raw_dir,output=Path(raw_dir),Path(output);output.mkdir(parents=True,exist_ok=True)
    for name,expected in EXPECTED_SHA256.items():
        if digest((raw_dir/name).read_bytes())!=expected:raise ValueError('source identity mismatch: '+name)
    selections={};audit={};all_docs={}
    for split in ['train','dev','test']:
        sentences,excluded=read_source(raw_dir/('sv_talbanken-ud-'+split+'.conllu'))
        chosen=[s for s in sentences if int(hashlib.sha256(s['doc_id'].encode()).hexdigest(),16)%4==0 and 2<=len(s['rows'])<=12]
        all_docs[split]={s['doc_id'] for s in sentences};selections[split]=chosen
        features=[];targets=[]
        for s in chosen:
            features.append({k:v for k,v in s.items() if k!='rows'}|dict(rows=[{k:r[k] for k in ['id','form','upos']} for r in s['rows']]))
            targets.append(dict(sample_id=s['sample_id'],rows=[{k:r[k] for k in ['id','head','relation']} for r in s['rows']]))
        save(output/(split+'-features.json'),features);save(output/(split+'-targets.json'),targets)
        audit[split]=dict(official_sentences=len(sentences),official_documents=len(all_docs[split]),official_integer_words=sum(len(s['rows']) for s in sentences),excluded_row_kinds_full=excluded,
                          selected_sentences=len(chosen),selected_documents=sorted({s['doc_id'] for s in chosen}),selected_words=sum(len(s['rows']) for s in chosen))
    overlaps=[]
    for a,b in [('train','dev'),('train','test'),('dev','test')]:
        row=dict(splits=[a,b],official_doc_overlap=sorted(all_docs[a]&all_docs[b]),selected_form_sequence_overlap=sorted({s['form_sha256'] for s in selections[a]}&{s['form_sha256'] for s in selections[b]}));overlaps.append(row)
        if row['official_doc_overlap'] or row['selected_form_sequence_overlap']:raise ValueError('cross-split identity collision; report before model fitting')
    protocol=dict(dataset='UD Swedish-Talbanken',release='r2.16',commit=COMMIT,source_sha256=EXPECTED_SHA256,
                  license='Source treebank and selected projections/prediction adaptations: CC BY-SA4.0; attribution and full upstream license in dependency/data. Code/course license unchanged.',
                  projection='Integer basic syntactic words only; original FORM/UPOS/HEAD/DEPREL exact, no subtype collapse, no reference projectivization. MWT ranges and enhanced empty nodes/DEPS not basic targets.',
                  selection='Keep official train/dev/test; sha256(newdoc_id)mod4==0, then integer word count2..12. No reference-label or score filter.',
                  models=['geometry','upos_geometry'],alphas=[.1,1.0,10.0],distance_buckets=[1,2,3,'4+'],
                  selection_metric='max dev micro LAS on reference UPOS!=PUNCT, include real root word; earliest alpha-list tie, independently per model; no train+dev refit',
                  test_access='After both model alpha decisions; public fixed benchmark, not external blind test.',
                  input_visibility='Gold integer-word boundaries/FORM and gold UPOS are oracle inputs; model uses positions/UPOS, not FORM/lemma/FEATS/XPOS/DEPS/HEAD/DEPREL. Train HEAD/DEPREL fit counts; dev targets select alpha; test targets score and diagnose only.',
                  decoder='Single-root projective Eisner; iterate real-root candidate, fixed-root cubic/global quartic; ordered root/split/label ties. Original nonprojective gold retained.',
                  metrics='Reuse published structure_lab.aligned_scores/validate; primary exclude reference PUNCT/include real root, secondary all words; exact full labels, same-word accuracy not official raw-text F1.',
                  grouping='Token micro, sentence macro, exact sentence and per-document descriptive results; test3 docs/dev1 doc do not support iid-sentence confidence claims.',
                  audit=audit,identity_overlap=overlaps)
    save(output/'protocol.json',protocol);return protocol


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=prepare(a.raw_dir,a.output)
    print(json.dumps(r['audit'],ensure_ascii=False))
