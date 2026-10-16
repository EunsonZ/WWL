"""Original synthetic ratings fixture, fixed before any model result. No personal data."""
import argparse
import json
from pathlib import Path

RATINGS = [[5,4,1,1,3,2], [4,5,1,2,3,1], [5,4,2,1,2,3], [1,2,5,4,3,2],
           [2,1,4,5,2,3], [1,2,5,4,3,3], [3,3,2,2,5,4], [2,3,3,2,4,5]]
TRAIN_ITEMS = [[0,2,4],[1,2,4],[0,3,5],[0,2,4],[1,3,5],[0,3,5],[0,2,4],[1,3,5]]


def generate(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    train=[];val=[];test=[];unrated=[];time=0
    for u,items in enumerate(TRAIN_ITEMS):
        for i in items:
            time+=1
            train.append(dict(event=f'e{time:02}',user=u,item=i,time=time,exposed=True,rating_observed=True,rating=RATINGS[u][i]))
    remaining=[[i for i in range(6) if i not in TRAIN_ITEMS[u]] for u in range(8)]
    for u in [0,1]:
        time+=1;i=remaining[u][1]
        unrated.append(dict(event=f'e{time:02}',user=u,item=i,time=time,exposed=True,rating_observed=False,rating=None))
    for split,column in [(val,0),(test,2)]:
        for u in range(8):
            time+=1;i=remaining[u][column]
            split.append(dict(event=f'e{time:02}',user=u,item=i,time=time,exposed=True,rating_observed=True,rating=RATINGS[u][i]))
    protocol=dict(dataset='original-synthetic-ratings-v1',provenance='Hand specified pedagogical values; no downloaded or human records; no natural population claim.',
                  users=list(range(8)),items=list(range(6)),rating_scale=[1,5],time_unit='synthetic ordered event tick, not a date',
                  split_cutoffs=dict(train_through=26,val_through=34,test_through=42),
                  exposure_policy='Fixed teaching event schedule, no estimated or known population propensities. Absence is not proof of zero propensity.',
                  rank=2,regularization=.01,seed=17,initial_factor_std=.1,learning_rate=.1,epochs=800,
                  checkpoints=[0,50,200,800],selection='lowest validation MSE; earliest epoch breaks exact ties',
                  prediction='raw unbounded real score; no clipping or rounding for loss/metrics',
                  metrics=['MSE','RMSE','MAE'],iid_claim=False,
                  pre_run='20 training updates only; no validation selection or test read; not a performance result')
    for name,value in [('protocol.json',protocol),('train.json',train+unrated),('val.json',val),('test.json',test)]:
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    generate(parser.parse_args().output)
