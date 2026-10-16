"""Render fixed saved numerical objects; no model training or new data source."""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({'svg.hashsalt':'wwl-162-ratings','font.family':'DejaVu Sans','font.size':10,
                     'axes.spines.top':False,'axes.spines.right':False})


def save(fig,path,title,description):
    fig.savefig(path,format='svg',metadata={'Date':None,'Title':title,'Description':description})
    plt.close(fig)
    text=path.read_text();path.write_text(text.replace('</title>','</title>\n <desc>'+escape(description)+'</desc>',1))


def render(results,output):
    results,output=Path(results),Path(output);output.mkdir(parents=True,exist_ok=True)
    r=json.loads((results/'results.json').read_text());e=r['examples']
    fig,axes=plt.subplots(2,3,figsize=(10,6),layout='constrained')
    matrices=[(e['observed'],'A. Observed; ? is not zero'),(e['worlds'][0]['matrix'],'B. World A: item 1 preferred'),
              (e['worlds'][1]['matrix'],'C. World B: item 2 preferred'),
              (e['exact_rank1_completion'],'D. Hard rank 1 + exact observed fit'),
              (e['zero_filled_rank1_svd'],'E. Rank-1 SVD after zero filling')]
    cmap=plt.get_cmap('YlGnBu').copy();cmap.set_bad('#dddddd')
    for k,(value,title) in enumerate(matrices):
        ax=axes.flat[k];a=np.array(value,float)
        if k==0:a=np.ma.array(a,mask=~np.array(e['observed_mask'],bool))
        im=ax.imshow(a,cmap=cmap,vmin=0,vmax=5)
        for u in range(2):
            for i in range(2):
                unknown=k==0 and not e['observed_mask'][u][i]
                label='?' if unknown else f'{float(a[u,i]):.3f}'.rstrip('0').rstrip('.')
                ax.text(i,u,label,ha='center',va='center',fontsize=14,color='white' if not unknown and a[u,i]>3 else 'black')
        ax.set(xticks=[0,1],xticklabels=['item 1','item 2'],yticks=[0,1],yticklabels=['user 1','user 2'],title=title)
    fig.colorbar(im,ax=list(axes.flat)[:5],shrink=.7,label='rating / predicted score (same 0..5 scale)')
    ax=axes.flat[5];values=[e['exact_rank1_observed_sse'],e['zero_svd_observed_sse']]
    bars=ax.bar([0,1],values,color=['#1264a3','#cc651b']);ax.bar_label(bars,labels=[f'{x:.6f}' for x in values],padding=3)
    ax.set(xticks=[0,1],xticklabels=['masked rank-1 fit','zero-filled SVD'],ylabel='SSE on 3 observed entries (score squared)',ylim=(0,.6),title='F. Same rank, different objective')
    save(fig,output/'missing-worlds.svg','Missing explicit ratings, compatible worlds, and distinct rank-one objectives',
         'A masks the unobserved entry, not a measured zero. B/C match all three observed entries but reverse user-1 preference over the fixed diagnostic candidates including the already rated item. D imposes exact rank one as an additional assumption. E solves the different zero-filled complete-matrix problem. F compares only observed-entry SSE; it is not an unknown-truth accuracy claim.')

    curve=json.loads((results/'train-curve.json').read_text());validation=json.loads((results/'validation.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.1),layout='constrained')
    ax=axes[0];ax.plot([x['epoch'] for x in curve],[x['rmse'] for x in curve],color='#1264a3',label='MF training RMSE, each update')
    ax.plot([x['epoch'] for x in validation],[x['validation']['rmse'] for x in validation],color='#cc651b',marker='o',label='validation at 4 predeclared epochs')
    ax.axvline(r['selected_epoch'],color='black',ls=':',label=f'selected epoch {r["selected_epoch"]}')
    ax.set(xlabel='full-batch updates',ylabel='RMSE (score units)',title='G. Training fit and validation choice differ');ax.legend(fontsize=8);ax.grid(alpha=.15)
    ax=axes[1];models=['global_mean','item_bias','mf'];splits=['train','val','test'];colors=['#1264a3','#cc651b','#24804d']
    for j,(split,color) in enumerate(zip(splits,colors)):
        values=[next(x['rmse'] for x in r['summary'] if x['model']==model and x['split']==split) for model in models]
        bars=ax.bar(np.arange(3)+(j-1)*.24,values,.24,color=color,label=split)
        ax.bar_label(bars,labels=[f'{x:.3f}' for x in values],fontsize=8,padding=2)
    ax.set(xticks=range(3),xticklabels=['global mean','item bias','MF (epoch 200)'],ylabel='RMSE (score units)',ylim=(0,1.8),title='H. Better validation did not beat mean on test')
    ax.legend(fontsize=8)
    save(fig,output/'ratings-learning.svg','Fixed explicit-rating fit, validation selection, and retained test failure',
         'G has no test curve: four validation checkpoints choose epoch 200 before the test file is opened. H compares the same 24/8/8 observed rating events for each model. Eight users are shared across splits; bars are finite deterministic metrics without iid confidence intervals. MF uses more parameters, and its test RMSE remains worse than the global mean. No online or human outcome is measured.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();render(args.results,args.output)
