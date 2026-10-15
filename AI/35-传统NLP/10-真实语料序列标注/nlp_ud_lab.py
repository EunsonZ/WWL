#!/usr/bin/env python3
"""A small, dependency-free supervised HMM POS experiment on UD EWT r2.16."""
import argparse, collections, hashlib, json, math, pathlib

SPLITS = {"train": "en_ewt-ud-train.conllu", "dev": "en_ewt-ud-dev.conllu", "test": "en_ewt-ud-test.conllu"}
K = 4

def checked_data_dir(value):
    data_dir = pathlib.Path(value)
    missing = [name for name in SPLITS.values() if not (data_dir / name).is_file()]
    if missing:
        raise ValueError("--data-dir must contain fixed r2.16 CoNLL-U files: " + ", ".join(missing))
    return data_dir

def selected(doc):
    return int(hashlib.sha256(doc.encode()).hexdigest(), 16) % K == 0

def read_conllu(path):
    docs, doc, sent, cur = [], None, [], []
    for raw in pathlib.Path(path).read_text(encoding="utf-8").splitlines() + [""]:
        if raw.startswith("# newdoc id = "):
            if cur: sent.append(cur); cur=[]
            if doc is not None: docs.append((doc, sent)); sent=[]
            doc = raw.split(" = ", 1)[1]
        elif raw.startswith("# sent_id = "):
            sent_id = raw.split(" = ", 1)[1]
        elif not raw:
            if cur:
                sent.append((sent_id, cur)); cur=[]
        elif not raw.startswith("#"):
            f = raw.split("\t")
            # Exclude syntactic range rows 1-2 and decimal empty nodes 3.1.
            if f[0].isdigit(): cur.append((f[1], f[3]))
    if doc is not None: docs.append((doc, sent))
    return [(d, s) for d, s in docs if selected(d)]

def flatten(docs):
    return [(d, sid, xs) for d, ss in docs for sid, xs in ss if xs]

def sentence_key(xs):
    """A duplicate-text key: the complete ordered sequence of surface FORM values."""
    return tuple(w for w, _ in xs)

class HMM:
    def __init__(self, rare=1, alpha=0.1): self.rare, self.alpha = rare, alpha
    def fit(self, sentences):
        wc = collections.Counter(w for _,_,xs in sentences for w,_ in xs)
        self.tags = sorted({t for _,_,xs in sentences for _,t in xs})
        self.vocab = {w for w,n in wc.items() if n > self.rare}
        self.vocab.add("<UNK>")
        self.seen_words = set(wc); self.rare_words = {w for w,n in wc.items() if n <= self.rare}
        self.start, self.trans, self.emit = collections.Counter(), collections.Counter(), collections.Counter()
        self.trans_n = collections.Counter()
        self.tag_n = collections.Counter()
        for _,_,xs in sentences:
            prev = None
            for w,t in xs:
                w = w if w in self.vocab else "<UNK>"; self.tag_n[t] += 1; self.emit[t,w] += 1
                if prev is None: self.start[t] += 1
                else: self.trans[prev,t] += 1; self.trans_n[prev] += 1
                prev = t
        self.nsent = len(sentences)
        return self
    def decode(self, words):
        log = lambda x: math.log(x)
        V = len(self.vocab); T = len(self.tags); a = self.alpha
        e = lambda tag,w: log((self.emit[tag, w if w in self.vocab else "<UNK>"] + a)/(self.tag_n[tag]+a*V))
        dp, back = [], []
        dp.append({t: log((self.start[t]+a)/(self.nsent+a*T))+e(t,words[0]) for t in self.tags}); back.append({})
        for w in words[1:]:
            row, bp = {}, {}
            for t in self.tags:
                p = max(self.tags, key=lambda q: dp[-1][q]+log((self.trans[q,t]+a)/(self.trans_n[q]+a*T)))
                row[t] = dp[-1][p]+log((self.trans[p,t]+a)/(self.trans_n[p]+a*T))+e(t,w); bp[t]=p
            dp.append(row); back.append(bp)
        tag=max(self.tags,key=dp[-1].get); out=[tag]
        for i in range(len(words)-1,0,-1): tag=back[i][tag]; out.append(tag)
        return list(reversed(out))

def unigram(train):
    c=collections.Counter(t for _,_,xs in train for _,t in xs); return max(c,key=c.get)
def word_baseline(train):
    c=collections.defaultdict(collections.Counter); overall=collections.Counter()
    for _,_,xs in train:
        for w,t in xs: c[w][t]+=1; overall[t]+=1
    default=max(overall,key=overall.get)
    return {w:max(v,key=v.get) for w,v in c.items()}, default

def evaluate(name, sentences, predictor, seen, rare, include_predictions=False):
    pairs=[]; sentence_correct=[]
    for doc,sid,xs in sentences:
        words=[w for w,_ in xs]; gold=[t for _,t in xs]; pred=predictor(words)
        pairs.extend((doc,sid,w,g,p) for w,g,p in zip(words,gold,pred))
        sentence_correct.append(all(g == p for g, p in zip(gold, pred)))
    n=len(pairs); ok=sum(g==p for _,_,_,g,p in pairs)
    def acc(sub): return None if not sub else sum(g==p for *_,g,p in sub)/len(sub)
    oov=[x for x in pairs if x[2] not in seen]; rarex=[x for x in pairs if x[2] in rare]
    bytag={t:acc([x for x in pairs if x[3]==t]) for t in sorted({x[3] for x in pairs})}
    bylen={}
    for label, lo, hi in (("1-5",1,5),("6-15",6,15),("16+",16,10**9)):
        ss=[]
        for doc,sid,xs in sentences:
            if lo<=len(xs)<=hi:
                ps=predictor([w for w,_ in xs]); ss += [(w,g,p) for (w,g),p in zip(xs,ps)]
        bylen[label]={"n":len(ss),"accuracy":None if not ss else sum(g==p for _,g,p in ss)/len(ss)}
    conf=collections.Counter((g,p) for *_,g,p in pairs if g!=p)
    out={"name":name,"token_accuracy":ok/n,"n_tokens":n,"n_sentences":len(sentences),"sentence_accuracy":sum(sentence_correct)/len(sentence_correct),"true_oov":{"n":len(oov),"accuracy":acc(oov)},"seen_rare":{"n":len(rarex),"accuracy":acc(rarex)},"gold_tag_accuracy":bytag,"length":bylen,"top_confusions":[{"gold":g,"pred":p,"n":v} for (g,p),v in conf.most_common(12)]}
    if include_predictions:
        out["predictions"]=[{"doc_id":d,"sent_id":s,"form":w,"gold":g,"pred":p} for d,s,w,g,p in pairs]
    return out

def run(data_dir, include_predictions=False):
    data_dir = checked_data_dir(data_dir)
    raw={k:read_conllu(data_dir/v) for k,v in SPLITS.items()}
    data={k:flatten(v) for k,v in raw.items()}
    hchoices=[]
    for a in (0.01,0.1,1.0):
        h=HMM(rare=1,alpha=a).fit(data["train"])
        r=evaluate("hmm alpha="+str(a),data["dev"],h.decode,h.seen_words,h.rare_words); hchoices.append((r["token_accuracy"],a))
    _, alpha=max(hchoices); h=HMM(rare=1,alpha=alpha).fit(data["train"])
    uni=unigram(data["train"]); wm,default=word_baseline(data["train"])
    out={"protocol":{"ud_release":"2.16","subset":"sha256(newdoc_id) mod 4 == 0","token_rows":"integer ID only; ranges and decimal empty nodes excluded","form":"raw FORM","label":"UPOS","rare":"training count <= 1 becomes <UNK>","dev_selection":{"alpha_candidates":[0.01,0.1,1.0],"chosen":alpha,"criterion":"maximum dev token accuracy"},"result_release":"aggregate-only; no FORM, sentence ID, document ID, or per-token prediction is written unless --include-predictions is explicitly used for private evidence"},"inputs":{k:{"docs":len(raw[k]),"sentences":len(data[k]),"tokens":sum(len(x) for _,_,x in data[k])} for k in data},"results":{"unigram":evaluate("unigram",data["test"],lambda ws:[uni]*len(ws),h.seen_words,h.rare_words,include_predictions),"word_frequency":evaluate("word-frequency tag",data["test"],lambda ws:[wm.get(w,default) for w in ws],h.seen_words,h.rare_words,include_predictions),"hmm":evaluate("HMM",data["test"],h.decode,h.seen_words,h.rare_words,include_predictions)}}
    # Cross-document duplicate sentence texts are measured, not removed.
    text_sets={k:{sentence_key(xs) for _, _, xs in ss} for k, ss in data.items()}
    pairs=(("train","dev"),("train","test"),("dev","test"))
    out["cross_split_duplicate_sentence_forms"]={a+"_"+b:len(text_sets[a] & text_sets[b]) for a,b in pairs}
    test_seen_in_train=[row for row in data["test"] if sentence_key(row[2]) in text_sets["train"]]
    clean_test=[row for row in data["test"] if sentence_key(row[2]) not in text_sets["train"]]
    out["sensitivity_excluding_test_sentence_forms_seen_in_train"]={
        "rule":"exclude every fixed-test sentence whose complete FORM tuple appears in the selected train subset; not used for model selection",
        "excluded_test_sentences":len(test_seen_in_train),
        "remaining_test_sentences":len(clean_test),
        "remaining_test_tokens":sum(len(xs) for _,_,xs in clean_test),
        "hmm":evaluate("HMM sensitivity",clean_test,h.decode,h.seen_words,h.rare_words,include_predictions)
    }
    return out

if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--data-dir",required=True,help="directory containing fixed r2.16 en_ewt-ud-{train,dev,test}.conllu"); ap.add_argument("--output",default="results.json"); ap.add_argument("--include-predictions",action="store_true"); args=ap.parse_args()
    pathlib.Path(args.output).write_text(json.dumps(run(args.data_dir,args.include_predictions),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
