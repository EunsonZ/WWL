"""Reuse the published synthetic user/item table, not human click evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def generate(output,ratings_source=None):
    source=Path(ratings_source) if ratings_source else Path(__file__).resolve().parents[2]/'code-sync/make_ratings_inputs.py'
    spec=importlib.util.spec_from_file_location('published_rating_fixture',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    table=module.RATINGS;positive=[[0,1],[0],[0],[2,3],[3],[2]];nonclick=[2,3,3,0,1,0]
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    events=[];time=0
    for u,items in enumerate(positive):
        for i in items:
            time+=1;events.append(dict(user=u,item=i,time=time,exposed=True,click=1))
    for u,i in enumerate(nonclick):
        time+=1;assert table[u][i]<3
        events.append(dict(user=u,item=i,time=time,exposed=True,click=0))
    def query(user,group,time,items):
        candidates=[i for i in items if user>=6 or i not in positive[user]]
        return dict(query=f'{group}-u{user}',user=user,group=group,time=time,candidates=candidates,
                    relevant=[i for i in candidates if table[user][i]>=3])
    val=[query(1,'warm',20,range(4)),query(4,'warm',21,range(4))]
    test=[query(2,'warm',30,range(4)),query(5,'warm',31,range(4)),
          query(6,'cold_user',32,range(6)),query(7,'cold_user',33,range(6))]
    test.extend(query(u,'cold_item',40+u,[4,5]) for u in range(6))
    config=dict(dataset='synthetic-ranking-v1',provenance='Public synthetic rating fixture reused by explicit threshold >=3 as controlled binary relevance; these are not measured clicks or human preferences.',
                parent_fixture_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),users=list(range(8)),items=list(range(6)),
                train_users=list(range(6)),train_items=list(range(4)),train_through=14,
                user_group=[0,0,0,1,1,1,2,2],item_group=[0,0,1,1,2,2],side_information='Fixed teaching metadata, known at serving; an extra input used only by content baseline, not learned from test labels.',
                rank=2,regularization=.01,seed=17,initial_factor_std=.1,learning_rate=.2,epochs=300,
                checkpoints=[0,50,150,300],selection='max full-candidate validation macro NDCG@2; earliest exact tie',
                samplers=['uniform','popularity_plus_one'],neighbor_k=2,K=2,retriever_size=2,
                negative_pool='train eligible items minus each user training positives; known nonclick and unexposed mixed; no validation/test-positive filtering',
                positive_weighting='uniform train user, then uniform positive within that user',tie_break='descending score, then ascending item ID',
                cold_rule='no feedback for user 6/7 or item 4/5; unknown collaborative score explicitly falls back to training popularity',
                audit_truth='Complete synthetic relevance labels for every candidate; real unobserved items are not assumed negative.',iid_claim=False)
    truth=dict(binary_relevance=[[int(x>=3) for x in row] for row in table])
    for name,value in [('protocol.json',config),('train.json',events),('val.json',val),('test.json',test),('diagnostic-truth.json',truth)]:
        (root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--ratings-source',type=Path)
    args=parser.parse_args();generate(args.output,args.ratings_source)
