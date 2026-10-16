"""Scientific figures from saved ranking queries and the fixed randomization space."""
import argparse
from collections import Counter
import json
from pathlib import Path
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({'svg.hashsalt':'wwl-162-ranking','font.family':'DejaVu Sans','font.size':10,
                     'axes.spines.top':False,'axes.spines.right':False})
BLUE,ORANGE,GREEN,PURPLE='#1264a3','#cc651b','#24804d','#8b479c'


def save(fig,path,title,desc):
    fig.savefig(path,format='svg',metadata={'Date':None,'Title':title,'Description':desc});plt.close(fig)
    text=path.read_text();path.write_text(text.replace('</title>','</title>\n <desc>'+escape(desc)+'</desc>',1))


def render(root,output):
    root,output=Path(root),Path(output);output.mkdir(parents=True,exist_ok=True)
    r=json.loads((root/'results.json').read_text());rows=[json.loads(line) for line in (root/'query-predictions.jsonl').read_text().splitlines()]
    models=['popularity','neighbors','bpr_uniform','bpr_popularity_plus_one','content'];labels=['pop','neighbors','BPR-U','BPR-P','content*']
    def summary(model,group,mode):return next(x for x in r['summary'] if x['model']==model and x['split']=='test' and x['group']==group and x['candidate_mode']==mode)
    fig,axes=plt.subplots(2,2,figsize=(11,7.5),layout='constrained')
    for ax,group,title in [(axes[0,0],'warm','A. Warm queries: the same retriever can erase gains'),(axes[0,1],'cold_user','B. Cold users: collaborative fallback is popularity')]:
        for shift,mode,color in [(-.18,'full',BLUE),(.18,'retrieved',ORANGE)]:
            values=[summary(m,group,mode)['ndcg'] for m in models]
            bars=ax.bar(np.arange(5)+shift,values,.34,color=color,label=mode)
            ax.bar_label(bars,labels=[f'{v:.3f}' for v in values],fontsize=8,padding=2)
        ax.set(xticks=range(5),xticklabels=labels,ylabel='macro end-to-end NDCG@2',ylim=(0,1.23),title=title)
        ax.legend(fontsize=8);ax.grid(axis='y',alpha=.15)
    ax=axes[1,0];cold=[x for x in rows if x['model']=='bpr_uniform' and x['split']=='test' and x['group']=='cold_item' and x['candidate_mode']=='full']
    values=[x['ndcg'] for x in cold];bars=ax.bar(range(6),values,color=PURPLE)
    ax.bar_label(bars,labels=[f'{v:.3f}' for v in values],fontsize=8,padding=3)
    ax.set(xticks=range(6),xticklabels=[f'user {x["user"]}' for x in cold],ylabel='NDCG@2',ylim=(0,1.2),title='C. Two cold items, K = 2: recall is always 1')
    ax.text(.05,.12,'Same-group metadata cannot rank item 4 versus 5.\nAll five methods share these cold-item results.',transform=ax.transAxes,fontsize=9)
    ax=axes[1,1]
    for shift,mode,key,color,label in [(-.25,'full','ndcg',BLUE,'full pool'),(0.,'retrieved','ndcg',ORANGE,'retrieved: full denominator'),(.25,'retrieved','conditional_ndcg',GREEN,'retrieved: conditional denominator')]:
        values=[]
        for u in [2,5]:
            row=next(x for x in rows if x['model']=='bpr_uniform' and x['split']=='test' and x['group']=='warm' and x['candidate_mode']==mode and x['user']==u)
            values.append(row[key])
        valid=[i for i,v in enumerate(values) if v is not None]
        ax.bar(np.array(valid)+shift,[values[i] for i in valid],.23,color=color,label=label)
        for i,v in enumerate(values):
            if v is None:ax.text(i+shift,.05,'undefined',rotation=90,ha='center',va='bottom',fontsize=8,color=color)
    ax.set(xticks=[0,1],xticklabels=['user 2: relevant item omitted','user 5: relevant item recalled'],ylabel='NDCG@2',ylim=(0,1.2),title='D. Do not drop failed queries by changing the denominator')
    ax.legend(fontsize=8,loc='upper center');ax.grid(axis='y',alpha=.15)
    save(fig,output/'ranking-candidates.svg','Candidate recall, warm and cold tasks, and conditional denominator failure',
         'Five fixed models use the same train-only popularity retriever. Content has additional predeclared group information. A/B show full-denominator NDCG before and after retrieval, without confidence intervals. C exposes recall degeneracy when K equals the two-item cold catalogue. D marks conditional NDCG undefined when no relevant candidate was retrieved; it is not a zero or a successful query. Warm/cold task denominators differ.')

    e=r['examples'];random=json.loads((root/'randomization.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.3),layout='constrained')
    ax=axes[0];value=e['sampler_loss'];loss=np.logaddexp(0.,-np.array(value['margins']))
    values=[value['uniform'],value['skew'],float(np.sum(np.array([.9,.1])*value['importance_weights']*loss))]
    bars=ax.bar(range(3),values,color=[BLUE,ORANGE,GREEN]);ax.bar_label(bars,labels=[f'{v:.6f}' for v in values],padding=3)
    ax.set(xticks=range(3),xticklabels=['uniform q','q = (0.9, 0.1)','weighted back to uniform'],ylabel='expected pair loss (dimensionless)',ylim=(0,.78),title='E. Fixed margins (0, 2), different sampling target')
    ax.text(.03,.95,'Training q is not logging propensity.',transform=ax.transAxes,va='top',fontsize=9)
    ax=axes[1];counts=Counter(row['difference'] for row in random['allocations']);x=sorted(counts)
    bars=ax.bar(x,[counts[v]/70 for v in x],width=.16,color=PURPLE)
    ax.bar_label(bars,labels=[f'{counts[v]}/70' for v in x],padding=3,fontsize=9)
    ax.axvline(random['population_ATE'],ymax=.68,color='black',ls=':',label='finite ATE = E[difference] = 0.25')
    ax.set(xlabel='B minus A user-mean difference',ylabel='fraction of 70 balanced assignments',ylim=(0,.48),xticks=x,title='F. One fixed 8-user population, not 70 human trials')
    ax.legend(fontsize=8);ax.text(.02,.93,'Exact variance = 1/16; single estimates can be negative.',transform=ax.transAxes,fontsize=9,va='top')
    save(fig,output/'sampling-and-randomization.svg','Negative-sampling targets and exact fixed-population randomization',
         'E uses the same two finite margins and shows how target weights change expected loss; correction requires support and is unrelated to exposure IPS. F enumerates all choose(8,4) assignments of the same synthetic potential responses. The expectation is 1/4, variance 1/16, and single differences range from -1/4 to 3/4. This is not actual online recommendation or human welfare evidence.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();render(args.results,args.output)
