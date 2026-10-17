---
type: lab
stage: 2
aliases: []
sources:
  - "https://github.com/UniversalDependencies/UD_Swedish-Talbanken/tree/3fd9c4123f155560ebb68c324b346fa9fa33991c"
  - "https://aclanthology.org/C96-1058.pdf"
prerequisites:
  - '[[AI/35-传统NLP/10-语言结构与任务/02-真实依存基线计数势与投射解码]]'
---

# Talbanken依存训练与逐句评测复算

本实践兑现[[AI/35-传统NLP/10-语言结构与任务/02-真实依存基线计数势与投射解码|真实计数模型到结构预测]]。规范源在`dependency/code-sync/`，固定所选数据在`dependency/inputs/`，完整模型/逐句预测/诊断与同数据图在`dependency/assets/`。只读复用已发布`code-sync/structure_lab.py`的validate/aligned_scores，不复制评分定义、旧CKY或EWT词性框架。

## 固定数据、许可与投影

全部正式输入来自UD Swedish-Talbanken **r2.16 / commit3fd9c4123f155560ebb68c324b346fa9fa33991c**；五个固定官方文件的原字节SHA、URL/取回时点和许可见[[AI/35-传统NLP/10-语言结构与任务/dependency/data/README|数据归属]]。README/LICENSE原字节保留，treebank及所选投影/预测派生材料按CC BY-SA4.0归属；代码和其他课程许可不因此整体改动。它不是EWT，选择Talbanken是为合法公开完整样本身份与逐项输出，未拿另一语言或标注约定冒旧UD实验。

三个原CoNLL-U共约8.6MB，取回与CPU求值分开。保留原官方split，文档hash%4后限定2–12整数词，得到351/13/76句、2885/101/628词，11/1/3文档；未按关系、投射性或成绩筛选。DOC集合与所选完整FORM序列跨split重复0，不保证近重复/同编辑来源或句子iid。原enhanced empty节点28/2/9排除，官方无multiword；普通HEAD和完整DEPREL不改，DEPS不作本次目标。

每句features保留sample_id、doc/sent ID、源行、FORM序列hash和{id,form,upos}，targets另存同ID的{head,relation}。输入gold语法词和gold UPOS是明确的参考条件oracle任务；模型不消费FORM/lemma/XPOS/FEATS/DEPS，特征行若混进head列会拒绝。prepare数据投影阶段已读取含test在内的原始gold字节，以建立固定教材输入；这不是人类或外部盲测。正式训练/选择管线随后使用分离的test-target文件访问锁，必须两模型选择结束才解锁，并以改test标签变式核标签不回流。

## 可直接复算与原字节再生

发布后的库根运行，数值/测试/画SVG均只需Python标准库：

```sh
python3 -B 'AI/35-传统NLP/10-语言结构与任务/dependency/code-sync/dependency_lab.py' \
  --output 'AI/35-传统NLP/10-语言结构与任务/dependency/assets'
python3 -B 'AI/35-传统NLP/10-语言结构与任务/dependency/code-sync/test_dependency_lab.py'
python3 -B 'AI/35-传统NLP/10-语言结构与任务/dependency/code-sync/render_dependency.py' \
  --results 'AI/35-传统NLP/10-语言结构与任务/dependency/assets' \
  --output 'AI/35-传统NLP/10-语言结构与任务/dependency/assets'
```

固定所选输入随包可用，不要求每次联网。需要核原文件/重建投影时，先把实际库外目录代入`<raw-dir>`，按顺序运行：

```sh
python3 -B 'AI/35-传统NLP/10-语言结构与任务/dependency/code-sync/fetch_talbanken.py' \
  --output '<raw-dir>'
python3 -B 'AI/35-传统NLP/10-语言结构与任务/dependency/code-sync/prepare_talbanken.py' \
  --raw-dir '<raw-dir>' \
  --output 'AI/35-传统NLP/10-语言结构与任务/dependency/inputs'
```

fetch串行取固定commit而非master/tag浮动地址，逐个校验内置SHA；prepare再验原字节、精确投影、身份/重复，再写七输入JSON。它没有根据标签或模型给gold换树，也不自动修UD“已知问题”。新增语料应另核许可/ID/边界及基本/增强目标，不把此投影器称通用NLP服务。

隔离候选给`--structure-source <已发布structure_lab.py>`；测试用`WWL_STRUCTURE_SOURCE`指同源。训练器可`--inputs <七JSON目录>`。预跑用`--pre-run --output <库外目录>`，只读train特征/目标与第一句预测，不访问dev/test；相关测试实际在仅有protocol与train特征/目标三个文件的临时输入上执行。最终全部argv、版本、源/父接口/输入/输出身份在`dependency/assets/run-record.json`。

本次短预跑、正式、相关测试、SVG与Cairo都经全局两槽单线程`/private/tmp/wwl-next-context/run_local.py --timeout 300 -- <解释器> -B <argv>`；runner不是读者依赖。Python3.14.7，五线程变量实际为1；正式约.302s，包含计数、六次dev选择候选、两个冻结test预测及结构oracle，不含网络取回/队列。没有GPU、模型下载、新依赖安装或旧HMM/POS/CKY全套重跑。已有CairoSVG只负责实际显示；两SVG已转换PNG并目视，不能由此认证Obsidian或真人理解。

## 模型、选择与输出合同

两模型的输入可见性相同，geometry主动忽略UPOS；UPOS+geometry加head/dependent参考词性，两个特征空间不是等参数数目。训练关系库存36类含root，普通子型不折叠；K分别281/4761，实际非零计数键142/376。训练与解码保留标点，primary去标点只是评分mask；真实根词始终计分，人工0没有词行。

每个模型只数351训练句的2885真实弧，闭式拟合伪计数特征分布，不跑树级条件似然优化。α事先固定[.1,1,10]，由dev13句的主指标**词微LAS**选、并列最早；各自三α的开发主LAS恰好同分，均选.1。两选择全部完成后，才解锁test特征/目标；不做train+dev重拟合。root/split/label的同分次序已固定，合法同分树可能不止一个；独立最优性比较以score容差核，不把别的同分树冒成同一确定输出。

| 保存对象 | 数量/内容 | 重算方法 |
| --- | --- | --- |
| `models.json` | 两模型的完整关系库存、K、条件总数、所有非零计数 | 从train每个原弧按模式计数；q=(C+α)/(N+αK)，不是head-ID后验 |
| `validation-predictions.jsonl` | 2模型×3α×13句=78行，原参考/每词预测、全score、主/全词评分 | 重放矩阵/单根投射最大分，独立逐词计分与开发正确数选择 |
| `predictions.jsonl` | 2模型×(13dev+76test)=178行冻结预测 | 保留各句身份/词/UPOS、完整原HEAD/DEPREL与预测，不删失败或PUNCT行 |
| `results.json` | 两选择、8组model/split/mask summary、关系/长度/原文档切片、阶段事件与身份 | 主指标548词/全词628；分母、root和标签全名精确；微/宏/精确句不混 |
| `oracle-bounds.json` | 76 test句的结构UAS及库存LAS上界、达到上界的头 | 冻结模型后给正确参考head0/1奖励再解码；不是训练/调参输入，也不是本特征参数家族可达到性的证明 |
| 两SVG与`diagnostic-examples.json` | 同raw指标/三文档及按FORM hash选的两失败 | 只做解释性选择，不改模型；逐表核相对参考的差异，不造真人语义裁决 |

结果主指标：geometry test UAS92/548、LAS25/548；UPOS+geometry UAS439/548、LAS362/548，保留差基线。UPOS全词490/628、413/628，精确主句13/76、含标点精确句12/76；后者差一不矛盾，mask不同。主LAS的词/句/文档宏分别约.660584/.686368/.723623，P301占435/548主词，不是三个同权总体的同一个数。

测试76参考都投射，主UAS结构上界1。完整label库存未见acl:cleft/aux:pass各1，库存限制的主LAS上界546/548；实际head错109、head对label错77，不能用两未见类解释所有错误。投射能力的失败在原train两非投射句和主课三词2/3上界例中保留，未伪造本次test含非投射。全部测试目标公开复用，不称外部盲测。

## 重要断言、独立预期与失败接口

| 重要性/原因 | 独立预期与失败判据 | 实际证据和边界 |
| --- | --- | --- |
| 高：来源/实体/标注，混版本或改gold会换任务 | 原字节SHA全同；351/13/76固定身份与原整数词/HEAD/DEPREL逐行同；跨split doc/完整FORM重复0，增强节点另记 | fetch/prepare输入与data来源齐；不声称去除近重复或建立时间外推 |
| 高：训练对象/库存，给test子型扩词表即回流 | train计数/36标签/K281和4761可独立数；未见类保持不可预测；伪计数目标解正确、无树级MLE偷换 | 两完整states保留；FORM重命名不改变势，gold UPOS作为输入显著限定结果 |
| 高：结构解码，局部最优和投射/单根不能混 | 固定root三次方、逐root四次方；小n穷举独立后代判投射的最优score误差<1e−10；原非投射gold(2,0,1)最高2/3，不重写参照 | 作者4测试PASS；所有预测良构/单root/投射，实际real矩阵与最大分可独核 |
| 高：标签访问/选择，test反馈会伪造泛化 | pre-run无dev/test文件仍可跑；两决策前test targets拒读；把test目标换另一合法树不得改变计数、α、全部预测/score | 事件日志齐，非作者实际反转合法test树变式验证；gold UPOS/词输入不是未声明raw管线 |
| 高：指标/独立单位，删错词/截子型/多句当iid会误报 | 原句逐词重算主/全词、标签合取、548/628分母；两决策/8summary/关系文档长度切片全吻合 | 全256预测记录保留，dev1doc/test3doc无窄iid区间；不把依存分称语义保持 |
| 中：图与解释性样本，图不得另挑训练结论 | 同raw重建、方向/关系全名/排除PUNCT灰行清楚；失败选择仅冻结后按hash | 两实际显示SVG，不替独立来源与真人判断 |
| 高：后续真实全链/真人意义，oracle前端无法认证部署 | 原始文本语法词对齐、独立UPOS前端与训练源/污染审计、完整UD scorer口径、按文档外推与人工分歧/错误代价分别定义 | 本包未做预测词性或raw端到端、真人瑞典语标注裁决/意义或产品研究。小型前端/更多合法公开UD本机可继续，大训练才按实际资源另留接口，不一概外部化 |

非作者先独答A–F，再用不同的complete-subtree/ordered-children oracle核真实解码，并核来源/许可、词标签可见性和所有raw指标。独立报告经READY交接；不把作者单测当独立语义认证。原[#163](https://github.com/EunsonZ/WWL/issues/163)的真实结构最小基线在此建立，语义角色/实体关系事件、共指/篇章、量词作用域和翻译仍为后续原范围，不由一个真实语料实验自动关课。

## 规范源码镜像

<!-- code-sync: ./dependency/code-sync/fetch_talbanken.py -->
```python
"""Fetch immutable UD Talbanken files; network acquisition is separate from CPU runs."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request,urlopen

COMMIT='3fd9c4123f155560ebb68c324b346fa9fa33991c'
BASE='https://raw.githubusercontent.com/UniversalDependencies/UD_Swedish-Talbanken/'+COMMIT+'/'
EXPECTED_SHA256={'README.md': 'f46b14ceec36998c5e41e7a83cb98ca7d259e679ee07f2d7de28a15bc8d018bc', 'LICENSE.txt': '55d116ac4f9bc34715c7823a5f5ca2e4c0cac4917db9e58a470a3d48033d261c', 'sv_talbanken-ud-train.conllu': 'fcc4bed5885e3d95f34a0e1bf813783135d38ae76d5822c3530b371fe78fc35f', 'sv_talbanken-ud-dev.conllu': '2e30e94a73a6db89b09fe80767df0c8c1194a48525879126a793015e868f8265', 'sv_talbanken-ud-test.conllu': 'eb3950dfb820d13634bed35c1d0f69872851754e0b19af1a9705ce6978580434'}
FILES=['README.md','LICENSE.txt','sv_talbanken-ud-train.conllu','sv_talbanken-ud-dev.conllu','sv_talbanken-ud-test.conllu']


def fetch(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);records=[]
    for name in FILES:
        url=BASE+name
        with urlopen(Request(url,headers={'User-Agent':'WWL-163-fixed-UD-teaching-baseline'}),timeout=45) as response:
            raw=response.read(12_000_001)
            if len(raw)>12_000_000:raise ValueError('unexpected source size')
            row=dict(name=name,url=url,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),retrieved_at_utc=datetime.now(timezone.utc).isoformat(),http_date=response.headers.get('Date'),etag=response.headers.get('ETag'))
        if row['sha256']!=EXPECTED_SHA256[name]:raise ValueError('fixed source identity mismatch: '+name)
        (output/name).write_bytes(raw);records.append(row)
    record=dict(repository='UniversalDependencies/UD_Swedish-Talbanken',release='r2.16',commit=COMMIT,files=records)
    (output/'fetch-record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=fetch(a.output)
    print(json.dumps({x['name']:x['bytes'] for x in r['files']}))
```

<!-- code-sync: ./dependency/code-sync/prepare_talbanken.py -->
```python
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
```

<!-- code-sync: ./dependency/code-sync/dependency_lab.py -->
```python
"""Train-only count potentials and exact single-root projective dependency decoding."""
from collections import Counter,defaultdict
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time

NEG=-math.inf
UPOS=set('ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB X'.split())
_STRUCTURE=None
_STRUCTURE_PATH=None


def set_structure(path=None):
    global _STRUCTURE,_STRUCTURE_PATH
    path=Path(path) if path else Path(__file__).resolve().parents[2]/'code-sync/structure_lab.py'
    spec=importlib.util.spec_from_file_location('published_structure_lab',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    _STRUCTURE,_STRUCTURE_PATH=m,path
    return m


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def write_rows(path,rows):path.write_text(''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in rows))


class DataAccess:
    def __init__(self,root):self.root=Path(root);self.finished=False;self.events=[]
    def features(self,split):
        rows=json.loads((self.root/(split+'-features.json')).read_text())
        for sent in rows:
            for i,r in enumerate(sent['rows'],1):
                if set(r)!={'id','form','upos'} or type(r['id']) is not int or r['id']!=i:raise ValueError('feature rows must exclude targets and preserve ordered IDs')
                if not isinstance(r['form'],str) or not r['form'] or r['upos'] not in UPOS:raise ValueError('FORM/UPOS domain')
        if len({r['sample_id'] for r in rows})!=len(rows):raise ValueError('duplicate sample IDs')
        self.events.append(dict(action='features',split=split,selection_finished=self.finished));return rows
    def targets(self,split):
        if split=='test' and not self.finished:raise RuntimeError('test targets locked until both model choices')
        rows=json.loads((self.root/(split+'-targets.json')).read_text())
        if len({r['sample_id'] for r in rows})!=len(rows):raise ValueError('duplicate target sample IDs')
        self.events.append(dict(action='targets',split=split,selection_finished=self.finished));return rows
    def finish_selection(self,decisions):
        if {r['model'] for r in decisions}!={'geometry','upos_geometry'} or len(decisions)!=2:raise ValueError('both choices required')
        self.finished=True;self.events.append(dict(action='finish_selection',models=[r['model'] for r in decisions]))


def references(features,targets):
    keyed={r['sample_id']:r['rows'] for r in targets}
    if set(keyed)!={r['sample_id'] for r in features}:raise ValueError('feature/target identities differ')
    out={}
    for s in features:
        target=keyed[s['sample_id']]
        if len(target)!=len(s['rows']) or any(r['id']!=t['id'] for r,t in zip(s['rows'],target)):raise ValueError('target token alignment differs')
        rows=[dict(r,head=t['head'],relation=t['relation']) for r,t in zip(s['rows'],target)]
        _STRUCTURE.validate(rows);out[s['sample_id']]=rows
    return out


def geometry(h,d):
    if h==0:return 'ROOT','0'
    distance=abs(h-d);return ('L' if h<d else 'R'),str(distance) if distance<4 else '4+'


class CountModel:
    def __init__(self,mode):
        if mode not in {'geometry','upos_geometry'}:raise ValueError('unknown model')
        self.mode=mode;self.counts=Counter();self.conditions=Counter();self.labels=[]
    def key(self,rows,h,d,relation):
        direction,bucket=geometry(h,d)
        if self.mode=='geometry':return ('*',direction,bucket,relation)
        return (rows[d-1]['upos'],'<ROOT>' if h==0 else rows[h-1]['upos'],direction,bucket,relation)
    def fit(self,features,targets):
        gold=references(features,targets);self.counts.clear();self.conditions.clear();labels=set()
        for sent in features:
            for d,row in enumerate(gold[sent['sample_id']],1):
                key=self.key(sent['rows'],row['head'],d,row['relation']);self.counts[key]+=1;self.conditions[key[0]]+=1;labels.add(row['relation'])
        self.labels=sorted(labels)
        if 'root' not in labels or len(labels)<2:raise ValueError('need root and ordinary training relations')
        return self
    def matrices(self,rows,alpha):
        if not math.isfinite(alpha) or alpha<=0:raise ValueError('alpha must be finite positive')
        n=len(rows);scores=[[NEG]*(n+1) for _ in range(n+1)];labels=[[None]*(n+1) for _ in range(n+1)]
        ordinary=[r for r in self.labels if r!='root']
        for d in range(1,n+1):
            for h in range(n+1):
                if h==d:continue
                options=['root'] if h==0 else ordinary
                label=max(options,key=lambda r:self.counts[self.key(rows,h,d,r)])
                scores[h][d]=math.log(self.counts[self.key(rows,h,d,label)]+alpha);labels[h][d]=label
        return scores,labels
    def feature_domain_size(self):return 1+(8 if self.mode=='geometry' else 17*8)*(len(self.labels)-1)
    def feature_probability(self,rows,h,d,label,alpha):
        if label not in self.labels or (h==0)!=(label=='root') or not math.isfinite(alpha) or alpha<=0:raise ValueError('feature-label support or smoothing invalid')
        key=self.key(rows,h,d,label)
        return (self.counts[key]+alpha)/(self.conditions[key[0]]+alpha*self.feature_domain_size())
    def state(self):return dict(mode=self.mode,labels=self.labels,feature_domain_size=self.feature_domain_size(),conditions=dict(sorted(self.conditions.items())),counts=[dict(key=list(k),count=v) for k,v in sorted(self.counts.items())])


def projective(heads):
    arcs=[tuple(sorted((h,d))) for d,h in enumerate(heads,1)]
    return not any(a<c<b<d or c<a<d<b for i,(a,b) in enumerate(arcs) for c,d in arcs[i+1:])


def decode(scores):
    """Eisner max-sum per root. Shape (n+1)^2: row head, column dependent.

    L=0/R=1; C is complete, I is incomplete; ROOT0 has no incoming arc.
    Ordered root/split ties; total O(n^4), chart O(n^2); bounded1..20 words.
    """
    n=len(scores)-1
    if not 1<=n<=20 or any(len(row)!=n+1 for row in scores):raise ValueError('square ROOT-inclusive score matrix;1..20 real words')
    if any(math.isnan(v) or v==math.inf for row in scores for v in row):raise ValueError('finite scores or -inf only')
    if any(v!=NEG for v in [scores[h][0] for h in range(n+1)]+[scores[d][d] for d in range(n+1)]):raise ValueError('incoming ROOT and self arcs must be masked')
    best_score=NEG;best_heads=None
    for root in range(1,n+1):
        C=[[[NEG,NEG] for _ in range(n+1)] for _ in range(n+1)];I=[[[NEG,NEG] for _ in range(n+1)] for _ in range(n+1)]
        BC=[[[None,None] for _ in range(n+1)] for _ in range(n+1)];BI=[[[None,None] for _ in range(n+1)] for _ in range(n+1)]
        for i in range(n+1):C[i][i]=[0.,0.]
        for width in range(1,n+1):
            for i in range(n+1-width):
                j=i+width;value=NEG;split=None
                for k in range(i,j):
                    v=C[i][k][1]+C[k+1][j][0]
                    if v>value:value,split=v,k
                for direction,arc in [(0,scores[j][i]),(1,scores[i][j] if i or j==root else NEG)]:
                    I[i][j][direction]=value+arc;BI[i][j][direction]=split
                for k in range(i,j):
                    v=C[i][k][0]+I[k][j][0]
                    if v>C[i][j][0]:C[i][j][0],BC[i][j][0]=v,k
                for k in range(i+1,j+1):
                    v=I[i][k][1]+C[k][j][1]
                    if v>C[i][j][1]:C[i][j][1],BC[i][j][1]=v,k
        value=C[0][n][1]
        if value<=best_score:continue
        heads=[None]*(n+1)
        def recover(i,j,direction,complete):
            if i==j:return
            if complete:
                k=BC[i][j][direction]
                if direction==0:recover(i,k,0,True);recover(k,j,0,False)
                else:recover(i,k,1,False);recover(k,j,1,True)
            else:
                k=BI[i][j][direction];h,d=(j,i) if direction==0 else (i,j)
                if heads[d] is not None:raise AssertionError('duplicate decoded head')
                heads[d]=h;recover(i,k,1,True);recover(k+1,j,0,True)
        recover(0,n,1,True)
        best_score,best_heads=value,heads[1:]
    if best_heads is None:raise ValueError('no finite single-root projective tree')
    if sum(h==0 for h in best_heads)!=1 or not projective(best_heads):raise AssertionError('decoder invariant failed')
    return best_heads,best_score


def predict(model,alpha,sent):
    scores,labels=model.matrices(sent['rows'],alpha);heads,total=decode(scores)
    rows=[dict(r,head=h,relation=labels[h][d]) for d,(r,h) in enumerate(zip(sent['rows'],heads),1)]
    _STRUCTURE.validate(rows);return rows,total


def brief(score):return {k:v for k,v in score.items() if k!='detail'}


def evaluate(model,alpha,features,gold,split):
    out=[]
    for sent in features:
        predicted,total=predict(model,alpha,sent);reference=gold[sent['sample_id']]
        out.append(dict(model=model.mode,alpha=alpha,split=split,sample_id=sent['sample_id'],doc_id=sent['doc_id'],sent_id=sent['sent_id'],form_sha256=sent['form_sha256'],reference=reference,prediction=predicted,score=total,
                        primary=brief(_STRUCTURE.aligned_scores(reference,predicted,False,True)),all_words=brief(_STRUCTURE.aligned_scores(reference,predicted,True,True)),gold_projective=projective([r['head'] for r in reference])))
    return out


def aggregate(rows,metric='primary'):
    n=sum(r[metric]['denominator'] for r in rows);u=sum(r[metric]['uas_correct'] for r in rows);l=sum(r[metric]['las_correct'] for r in rows)
    valid=[r for r in rows if r[metric]['denominator']]
    return dict(sentences=len(rows),documents=len({r['doc_id'] for r in rows}),scored_words=n,uas_correct=u,las_correct=l,UAS=u/n if n else None,LAS=l/n if n else None,
                sentence_macro_UAS=sum(r[metric]['UAS'] for r in valid)/len(valid) if valid else None,sentence_macro_LAS=sum(r[metric]['LAS'] for r in valid)/len(valid) if valid else None,
                exact_sentences=sum(r[metric]['exact_scored_tree'] is True for r in valid),valid_sentences=len(valid))


def summarize(rows):
    out=[]
    for model in sorted({r['model'] for r in rows}):
        for split in sorted({r['split'] for r in rows}):
            group=[r for r in rows if r['model']==model and r['split']==split]
            docs=sorted({r['doc_id'] for r in group})
            for metric in ['primary','all_words']:
                a=aggregate(group,metric);a['document_macro_LAS']=sum(aggregate([r for r in group if r['doc_id']==d],metric)['LAS'] for d in docs)/len(docs) if docs else None
                out.append(dict(model=model,split=split,metric=metric,**a))
    return out


def error_slices(rows,labels):
    relations=defaultdict(Counter);documents=defaultdict(list);lengths=defaultdict(list);unseen=Counter()
    for row in rows:
        documents[row['doc_id']].append(row);n=len(row['reference']);lengths['2-5' if n<=5 else '6-8' if n<=8 else '9-12'].append(row)
        for g,p in zip(row['reference'],row['prediction']):
            if g['upos']=='PUNCT':continue
            r=relations[g['relation']];r['n']+=1;r['uas_correct']+=g['head']==p['head'];r['las_correct']+=g['head']==p['head'] and g['relation']==p['relation']
            if g['relation'] not in labels:unseen[g['relation']]+=1
    return dict(by_relation={k:dict(v) for k,v in sorted(relations.items())},by_document={d:aggregate(v) for d,v in sorted(documents.items())},by_length={d:aggregate(v) for d,v in sorted(lengths.items())},unseen_gold_relations=dict(unseen))


def oracle_bounds(features,gold,labels):
    out=[]
    for sent in features:
        reference=gold[sent['sample_id']];n=len(reference);denom=sum(r['upos']!='PUNCT' for r in reference);item=dict(sample_id=sent['sample_id'],doc_id=sent['doc_id'],denominator=denom,gold_projective=projective([r['head'] for r in reference]))
        for metric in ['UAS','LAS']:
            scores=[[NEG]*(n+1) for _ in range(n+1)]
            for d,g in enumerate(reference,1):
                for h in range(n+1):
                    if h!=d:scores[h][d]=float(g['upos']!='PUNCT' and h==g['head'] and (metric=='UAS' or g['relation'] in labels))
            heads,score=decode(scores);item[metric]=dict(max_correct=int(round(score)),ceiling=score/denom if denom else None,heads=heads)
        out.append(item)
    return out


def run(inputs,output,pre_run=False):
    started=time.perf_counter();inputs,output=Path(inputs),Path(output);output.mkdir(parents=True,exist_ok=True)
    config=json.loads((inputs/'protocol.json').read_text());reader=DataAccess(inputs);train=reader.features('train');train_targets=reader.targets('train')
    models={mode:CountModel(mode).fit(train,train_targets) for mode in config['models']}
    if pre_run:
        out=dict(mode='train-only pre-run',samples=[dict(model=mode,sample_id=train[0]['sample_id'],heads=[r['head'] for r in predict(m,config['alphas'][0],train[0])[0]]) for mode,m in models.items()],access_events=reader.events)
        save(output/'pre-run.json',out);return out
    dev=reader.features('dev');dev_gold=references(dev,reader.targets('dev'));decisions=[];validation=[];selected_rows=[]
    for mode,m in models.items():
        choices=[];runs=[]
        for alpha in config['alphas']:
            rows=evaluate(m,alpha,dev,dev_gold,'dev');validation.extend(rows);runs.append(rows);choices.append(dict(alpha=alpha,**aggregate(rows)))
        index=max(range(len(choices)),key=lambda i:choices[i]['las_correct']);chosen=choices[index]
        decisions.append(dict(model=mode,alpha=chosen['alpha'],choices=choices));selected_rows.extend(runs[index])
    reader.finish_selection(decisions);test=reader.features('test');test_gold=references(test,reader.targets('test'))
    for d in decisions:selected_rows.extend(evaluate(models[d['model']],d['alpha'],test,test_gold,'test'))
    bounds=oracle_bounds(test,test_gold,set(next(iter(models.values())).labels))
    slices={mode:error_slices([r for r in selected_rows if r['model']==mode and r['split']=='test'],set(m.labels)) for mode,m in models.items()}
    states={mode:m.state() for mode,m in models.items()};save(output/'models.json',states);write_rows(output/'validation-predictions.jsonl',validation);write_rows(output/'predictions.jsonl',selected_rows);save(output/'oracle-bounds.json',bounds)
    result=dict(decisions=decisions,summary=summarize(selected_rows),test_slices=slices,access_events=reader.events,
                test_gold_projective=sum(r['gold_projective'] for r in bounds),test_sentences=len(bounds),oracle_primary={metric:sum(r[metric]['max_correct'] for r in bounds)/sum(r['denominator'] for r in bounds) for metric in ['UAS','LAS']},
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),structure_source_sha256=hashlib.sha256(_STRUCTURE_PATH.read_bytes()).hexdigest(),input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs.glob('*.json'))},
                thread_limit_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']})
    save(output/'results.json',result);return dict(result,elapsed_seconds=time.perf_counter()-started)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--structure-source',type=Path);p.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parents[1]/'inputs');p.add_argument('--output',type=Path,required=True);p.add_argument('--pre-run',action='store_true');a=p.parse_args();set_structure(a.structure_source);r=run(a.inputs,a.output,a.pre_run)
    print(json.dumps(r if a.pre_run else dict(decisions=r['decisions'],summary=r['summary'],seconds=r['elapsed_seconds']),ensure_ascii=False))
```

<!-- code-sync: ./dependency/code-sync/test_dependency_lab.py -->
```python
"""Small exhaustive decoder oracle and train/target visibility contracts."""
from copy import deepcopy
from itertools import product
import math
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest
import dependency_lab as lab


def legal_projective(heads):
    if sum(h==0 for h in heads)!=1:return False
    def path(x):
        seen=[]
        while x:
            if x in seen:return None
            seen.append(x);x=heads[x-1]
        return seen+[0]
    paths=[None]+[path(d) for d in range(1,len(heads)+1)]
    if any(p is None for p in paths[1:]):return False
    return all(h in paths[k] for d,h in enumerate(heads,1) for k in range(min(h,d)+1,max(h,d)))


def exhaustive(scores):
    n=len(scores)-1;best=-math.inf
    for heads in product(*[[h for h in range(n+1) if h!=d] for d in range(1,n+1)]):
        if legal_projective(heads):best=max(best,sum(scores[h][d] for d,h in enumerate(heads,1)))
    return best


class DependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):lab.set_structure(os.environ.get('WWL_STRUCTURE_SOURCE'))

    def test_eisner_matches_exhaustive_descendant_oracle(self):
        rng=random.Random(271)
        for n in range(1,6):
            for repeat in range(2 if n<5 else 1):
                scores=[[lab.NEG]*(n+1) for _ in range(n+1)]
                for d in range(1,n+1):
                    for h in range(n+1):
                        if h!=d:scores[h][d]=rng.uniform(-2,2)
                heads,value=lab.decode(scores)
                self.assertTrue(legal_projective(heads));self.assertAlmostEqual(value,exhaustive(scores),places=11)
        with self.assertRaises(ValueError):lab.decode([[0.,1.],[0.,0.]])

    def test_nonprojective_reference_is_not_rewritten(self):
        gold=[2,0,1];self.assertFalse(legal_projective(gold));self.assertFalse(lab.projective(gold))
        scores=[[lab.NEG]*4 for _ in range(4)]
        for d,hg in enumerate(gold,1):
            for h in range(4):
                if h!=d:scores[h][d]=float(h==hg)
        heads,value=lab.decode(scores);self.assertEqual(value,2);self.assertEqual(gold,[2,0,1])

    def test_count_probabilities_support_and_form_invariance(self):
        rows=[dict(id=1,form='t ex',upos='ADV'),dict(id=2,form='fish',upos='NOUN'),dict(id=3,form='fish',upos='NOUN')]
        features=[dict(sample_id='s',rows=rows)];targets=[dict(sample_id='s',rows=[dict(id=1,head=2,relation='advmod'),dict(id=2,head=0,relation='root'),dict(id=3,head=2,relation='nmod:poss')])]
        for mode,K in [('geometry',17),('upos_geometry',273)]:
            model=lab.CountModel(mode).fit(features,targets);self.assertEqual(model.feature_domain_size(),K)
            key=model.key(rows,2,3,'nmod:poss');context=key[0];p=model.feature_probability(rows,2,3,'nmod:poss',1.)
            self.assertEqual(p,2/(model.conditions[context]+K))
            a,b=model.matrices(rows,1.);changed=deepcopy(rows)
            for i,row in enumerate(changed):row['form']='renamed'+str(i)
            self.assertEqual((a,b),model.matrices(changed,1.));self.assertIn('nmod:poss',model.labels)
            with self.assertRaises(ValueError):model.feature_probability(rows,2,3,'nmod',1.)

    def test_train_only_prerun_and_target_lock(self):
        original=Path(__file__).resolve().parents[1]/'inputs'
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);inputs=tmp/'inputs';inputs.mkdir()
            for name in ['protocol.json','train-features.json','train-targets.json']:shutil.copyfile(original/name,inputs/name)
            r=lab.run(inputs,tmp/'out',True);self.assertTrue(all(x.get('split')=='train' for x in r['access_events']))
            access=lab.DataAccess(inputs)
            with self.assertRaises(RuntimeError):access.targets('test')
            poison=[dict(sample_id='s',rows=[dict(id=1,form='x',upos='NOUN',head=0)])]
            lab.save(inputs/'train-features.json',poison)
            with self.assertRaises(ValueError):access.features('train')


if __name__=='__main__':unittest.main(verbosity=2)
```

<!-- code-sync: ./dependency/code-sync/render_dependency.py -->
```python
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
```
