#!/usr/bin/env python3
"""Two-stage binary signaling, actual sampled actors + a learned tabular central critic.
No actor takes the hidden state that is unavailable in its role. Critic is training only.
"""
import argparse
import csv
import gzip
import io
import json
import math
from pathlib import Path
import random

MODES=('fixed_sender','fixed_receiver','independent','ctde','snapshot','no_comm')
HEADER=['seed','mode','episode','active','partner_checkpoint','sender_version','receiver_version','critic_version',
        'x','m','flip','y','receiver_observation','a','r','p_m1','p_a1','b_sender_old','b_receiver_old',
        'sender_logit0_after','sender_logit1_after','receiver_logit0_after','receiver_logit1_after']


def sigmoid(z):
    return 1/(1+math.exp(-z))


def logit(p):
    if not 0 < p < 1:
        raise ValueError('finite logits require probabilities strictly in (0,1)')
    return math.log(p/(1-p))


def sender_probability(theta, observed_x):
    if type(observed_x) is not int or observed_x not in (0,1):
        raise ValueError('sender must receive its observed binary x')
    return sigmoid(theta[observed_x])


def receiver_probability(theta, received):
    """received is a legal message bit or None. No x/critic/version argument exists."""
    if received is not None and (type(received) is not int or received not in (0,1)):
        raise ValueError('receiver accepts a message bit or no-message None')
    return sigmoid(theta[0 if received is None else received])


def probabilities(theta, no_comm=False):
    return [sigmoid(t) for t in theta[:2]], [receiver_probability(theta[2:],None if no_comm else y) for y in (0,1)]


def events(p, d, eta):
    """Exactly 16 elementary events x,m,y,a, iid X uniform, BSC independent noise."""
    for x in (0,1):
        for m in (0,1):
            for y in (0,1):
                for a in (0,1):
                    weight=.5*(p[x] if m else 1-p[x])*((1-eta) if y==m else eta)*(d[y] if a else 1-d[y])
                    yield dict(x=x,m=m,y=y,a=a,weight=weight,r=int(a==x))


def evaluate_probabilities(p, d, eta, receiver_blind=False):
    if len(p)!=2 or len(d)!=2 or any(not math.isfinite(v) or not 0<=v<=1 for v in p+d):
        raise ValueError('encoder and decoder require two probabilities in [0,1]')
    if not math.isfinite(eta) or not 0<=eta<=.5:
        raise ValueError('BSC eta must lie in [0,.5]')
    if receiver_blind and d[0]!=d[1]:
        raise ValueError('a receiver without a message must use one constant distribution')
    rows=list(events(p,d,eta))
    success=sum(e['weight']*e['r'] for e in rows)
    # Best unilateral role deviation enumerates all four deterministic local maps.
    sender_values=[]; receiver_values=[]
    for b0 in (0,1):
        for b1 in (0,1):
            sender_values.append(sum(e['weight']*e['r'] for e in events([b0,b1],d,eta)))
            if not receiver_blind or b0==b1:
                receiver_values.append(sum(e['weight']*e['r'] for e in events(p,[b0,b1],eta)))
    return dict(sender_p1=p, receiver_a1=d, success=success, mismatch=1-success,
                individual=[success,success],team=2*success,
                unilateral_gain=[max(sender_values)-success,max(receiver_values)-success])


def evaluate(theta, eta, no_comm=False):
    return evaluate_probabilities(*probabilities(theta,no_comm),eta,receiver_blind=no_comm)


def baselines(critic, theta, x, y, eta, no_comm=False):
    """Old learned critic only; counterfactual message changes downstream y/decoder law."""
    p,d=probabilities(theta,no_comm)
    receiver=sum((d[y] if a else 1-d[y])*critic[4*x+2*y+a] for a in (0,1))
    qs=[]
    for m in (0,1):
        qs.append(sum(((1-eta) if yy==m else eta)*(d[yy] if a else 1-d[yy])*critic[4*x+2*yy+a]
                      for yy in (0,1) for a in (0,1)))
    sender=(1-p[x])*qs[0]+p[x]*qs[1]
    return sender,receiver


def validate(cfg):
    for key in ('role_updates','checkpoint_every','adapt_episodes'):
        if type(cfg[key]) is not int or cfg[key]<1: raise ValueError(key+' must be positive integer')
    if cfg['role_updates']%cfg['checkpoint_every']: raise ValueError('updates must divide into checkpoint blocks')
    if not isinstance(cfg['eta'],(int,float)) or not math.isfinite(cfg['eta']) or not 0<=cfg['eta']<=.5:
        raise ValueError('BSC eta must lie in [0,.5]')
    for key in ('actor_step','logit_bound','initial_range'):
        if not math.isfinite(cfg[key]) or cfg[key]<=0: raise ValueError('positive finite '+key+' required')
    if cfg['initial_range']>cfg['logit_bound'] or cfg['logit_bound']>30: raise ValueError('invalid finite logit box')
    if not cfg['seeds'] or len(set(cfg['seeds']))!=len(cfg['seeds']) or any(type(s) is not int or s<0 for s in cfg['seeds']):
        raise ValueError('distinct nonnegative integer seeds required')
    if not cfg['modes'] or len(set(cfg['modes']))!=len(cfg['modes']) or any(m not in MODES for m in cfg['modes']):
        raise ValueError('known distinct modes required')
    if len(cfg['fixed_truth_probabilities'])!=2 or any(not 0<p<1 for p in cfg['fixed_truth_probabilities']):
        raise ValueError('two fixed probabilities in (0,1) required')
    if max(abs(logit(p)) for p in list(cfg['fixed_truth_probabilities'])+[.05,.95])>cfg['logit_bound']:
        raise ValueError('fixed and adaptation initial logits must lie inside the declared box')
    if (not cfg['adapt_checkpoints'] or any(type(k) is not int or k<0 or k>cfg['adapt_episodes'] for k in cfg['adapt_checkpoints'])
            or cfg['adapt_checkpoints']!=sorted(set(cfg['adapt_checkpoints']))
            or cfg['adapt_checkpoints'][0]!=0 or cfg['adapt_checkpoints'][-1]!=cfg['adapt_episodes']):
        raise ValueError('adapt checkpoints must uniquely increase from 0 to episode budget')


class Trainer:
    def __init__(self,cfg,seed,mode,writer=None,theta=None):
        self.cfg,self.seed,self.mode,self.writer=cfg,seed,mode,writer
        self.rng=[random.Random(100*seed+i) for i in range(6)] # init,x,m,channel,a,archive
        self.theta=[self.rng[0].uniform(-cfg['initial_range'],cfg['initial_range']) for _ in range(4)] if theta is None else list(theta)
        fixed=list(map(logit,cfg['fixed_truth_probabilities']))
        if mode=='fixed_sender' or mode=='no_comm': self.theta[:2]=fixed
        if mode=='fixed_receiver': self.theta[2:]=fixed
        self.critic=[0.]*8; self.count=[0]*8
        self.versions=[0,0]; self.episode=0; self.archive=[list(self.theta)]
        self.checkpoints=[self.snapshot(0)]

    def snapshot(self,k):
        return dict(role_update=k,episodes=self.episode,theta=list(self.theta),versions=list(self.versions),
                    critic=list(self.critic),critic_count=list(self.count),
                    score=evaluate(self.theta,self.cfg['eta'],self.mode=='no_comm'))

    def step(self,active='both',partner=None,partner_checkpoint='current'):
        cfg=self.cfg; current=list(self.theta); effective=list(current)
        if partner is not None:
            if active=='sender': effective[2:]=partner[2:]
            elif active=='receiver': effective[:2]=partner[:2]
            else: raise ValueError('frozen archive role requires one active role')
        no_comm=self.mode=='no_comm'
        x=int(self.rng[1].random()<.5)
        ps=sender_probability(effective[:2],x); m=int(self.rng[2].random()<ps)
        flip=int(self.rng[3].random()<cfg['eta']); y=m^flip
        observed=None if no_comm else y
        pr=receiver_probability(effective[2:],observed); a=int(self.rng[4].random()<pr); r=int(a==x)
        # Condition on all pre-episode history. Do NOT update critic with r before this.
        bs,br=baselines(self.critic,effective,x,y,cfg['eta'],no_comm) if self.mode in ('ctde','snapshot') else (0.,0.)
        oldversions=list(self.versions); oldcritic=sum(self.count)
        grads=[0.]*4
        if active in ('sender','both'): grads[x]=(m-ps)*(r-bs)
        if active in ('receiver','both'): grads[2+(0 if observed is None else y)]=(a-pr)*(r-br)
        # Explicit score update: baseline is a stopped scalar; no derivative through it.
        self.theta=[max(-cfg['logit_bound'],min(cfg['logit_bound'],v+cfg['actor_step']*g)) for v,g in zip(current,grads)]
        if active in ('sender','both'): self.versions[0]+=1
        if active in ('receiver','both'): self.versions[1]+=1
        idx=4*x+2*y+a; self.count[idx]+=1; self.critic[idx]+=(r-self.critic[idx])/self.count[idx]
        self.episode+=1
        if self.writer:
            self.writer.writerow([self.seed,self.mode,self.episode,active,partner_checkpoint,*oldversions,oldcritic,
                                  x,m,flip,y,'blank' if observed is None else y,a,r,ps,pr,bs,br,*self.theta])
        return r

    def train(self):
        cfg=self.cfg
        for k in range(1,cfg['role_updates']+1):
            if self.mode=='snapshot':
                for role in ('sender','receiver'):
                    j=self.rng[5].randrange(len(self.archive)); self.step(role,self.archive[j],j*cfg['checkpoint_every'])
            else:
                active='receiver' if self.mode in ('fixed_sender','no_comm') else 'sender' if self.mode=='fixed_receiver' else 'both'
                self.step(active)
            if k%cfg['checkpoint_every']==0:
                self.checkpoints.append(self.snapshot(k))
                if self.mode=='snapshot': self.archive.append(list(self.theta))
        return dict(seed=self.seed,mode=self.mode,checkpoints=self.checkpoints,
                    archive_size=len(self.archive),total_environment_episodes=self.episode,role_updates=self.versions)


def adaptation(cfg,seed,receiver,writer):
    out=[]
    for name,p in [('truth',[.05,.95]),('flipped',[.95,.05])]:
        init=list(map(logit,p))+list(receiver)
        trainer=Trainer(cfg,seed,'adapt_'+name,writer,init)
        checkpoints=[dict(episode=0,score=evaluate(trainer.theta,cfg['eta']),theta=list(trainer.theta))]
        for k in range(1,cfg['adapt_episodes']+1):
            trainer.step('sender',partner_checkpoint='frozen_receiver')
            if k in cfg['adapt_checkpoints']:
                checkpoints.append(dict(episode=k,score=evaluate(trainer.theta,cfg['eta']),theta=list(trainer.theta)))
        out.append(dict(seed=seed,initial_encoder=name,frozen_receiver=list(receiver),checkpoints=checkpoints))
    return out


def gradient_moments(theta,eta,critic):
    """Independent validation should enumerate these 16 events by another route."""
    p,d=probabilities(theta)
    est=[[],[]]
    for e in events(p,d,eta):
        x,m,y,a,r,w=[e[k] for k in ('x','m','y','a','r','weight')]
        bs,br=baselines(critic,theta,x,y,eta)
        raw=[0.]*4; central=[0.]*4
        raw[x]=(m-p[x])*r; raw[2+y]=(a-d[y])*r
        central[x]=(m-p[x])*(r-bs); central[2+y]=(a-d[y])*(r-br)
        for bucket,g in zip(est,(raw,central)): bucket.append((w,g))
    result=[]
    for bucket in est:
        mean=[sum(w*g[j] for w,g in bucket) for j in range(4)]
        second=[sum(w*g[j]**2 for w,g in bucket) for j in range(4)]
        result.append(dict(mean=mean,variance=[v-m*m for v,m in zip(second,mean)]))
    return dict(theta=theta,eta=eta,critic=critic,raw=result[0],central=result[1])


def run(cfg,writer):
    validate(cfg)
    runs=[Trainer(cfg,seed,mode,writer).train() for mode in cfg['modes'] for seed in cfg['seeds']]
    cross={}
    for mode in cfg['modes']:
        family=[r for r in runs if r['mode']==mode]
        cross[mode]=[[evaluate(left['checkpoints'][-1]['theta'][:2]+right['checkpoints'][-1]['theta'][2:],cfg['eta'],mode=='no_comm')
                      for right in family] for left in family]
    adaptations=[]
    for row in runs:
        if row['mode']=='ctde': adaptations+=adaptation(cfg,row['seed'],row['checkpoints'][-1]['theta'][2:],writer)
    # These test partners are not archive opponents; no updates occur during frozen tests.
    heldout=[]
    partners={'truth':[.05,.95],'flipped':[.95,.05],'uninformative':[.5,.5],'weak_truth':[.25,.75]}
    for row in runs:
        theta=row['checkpoints'][-1]['theta']; p,d=probabilities(theta,row['mode']=='no_comm')
        for name,values in partners.items():
            heldout.append(dict(mode=row['mode'],seed=row['seed'],partner=name,active_role='sender',score=evaluate_probabilities(p,[values[0]]*2 if row['mode']=='no_comm' else values,cfg['eta'],receiver_blind=row['mode']=='no_comm')))
            heldout.append(dict(mode=row['mode'],seed=row['seed'],partner=name,active_role='receiver',score=evaluate_probabilities(values,d,cfg['eta'],receiver_blind=row['mode']=='no_comm')))
    fixed=[logit(.2),logit(.8),logit(.3),logit(.7)]
    return dict(config=cfg,runs=runs,crossplay=cross,heldout=heldout,adaptation=adaptations,
                moments=[gradient_moments(fixed,cfg['eta'],q) for q in ([0.]*8,[float(a==x) for x in (0,1) for y in (0,1) for a in (0,1)],[.1,.9,.8,.2,.4,.6,.3,.7])],
                legal_alias=dict(states=[{'x':0,'y':0},{'x':1,'y':0}],receiver_history=['wait',0],
                                 legal_p_a1=[receiver_probability(fixed[2:],0)]*2,illegal_x_table=[0,1]),
                conventions=dict(truth=evaluate_probabilities([0,1],[0,1],cfg['eta']),
                                 flipped=evaluate_probabilities([1,0],[1,0],cfg['eta']),
                                 incompatible=evaluate_probabilities([0,1],[1,0],cfg['eta']),
                                 no_communication_bound=.5,illegal_state_leak_success=1.))


def figures(out,target):
    cfg=out['config']; modes=cfg['modes']; colors=['#3267ad','#bc4b3d','#317c52','#965aa6','#a67714','#148896']
    def base(title,desc,w,h):
        return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                f'<title>{title}</title><desc>{desc}</desc>','<rect width="100%" height="100%" fill="white"/>',
                '<style>text{font:14px Arial,sans-serif;fill:#17212d}.head{font-size:19px;font-weight:bold}.grid{stroke:#dbe1e7;stroke-width:1}</style>']
    s=base('Frozen local actor success at checkpoints','Lines are exact 16-event expected success averaged over the fixed seed family. x is each trainable role update count, not equal environment cost. Snapshot uses twice as many environment episodes. Dashed limits are noisy channel optimum and no-message upper bound.',1050,510)
    s+=['<text x="30" y="30" class="head">A. Legal frozen actors: exact success, average over fixed seeds</text>']
    x=lambda k:75+850*k/cfg['role_updates'];y=lambda v:390-300*v
    for v in (0,.25,.5,.75,1):
        s += [f'<line x1="75" y1="{y(v):.4f}" x2="925" y2="{y(v):.4f}" class="grid"/>',f'<text x="30" y="{y(v)+5:.4f}">{v:g}</text>']
    for v,label in ((1-cfg['eta'],'channel optimum'),(.5,'no-message bound')):
        s += [f'<line x1="75" y1="{y(v):.4f}" x2="925" y2="{y(v):.4f}" stroke="#727b85" stroke-dasharray="6 4"/>',f'<text x="790" y="{y(v)-7:.4f}">{label}</text>']
    for i,mode in enumerate(modes):
        rows=[r for r in out['runs'] if r['mode']==mode]; vals=[]
        for j,c in enumerate(rows[0]['checkpoints']):
            value=sum(r['checkpoints'][j]['score']['success'] for r in rows)/len(rows)
            vals.append(f'{x(c["role_update"]):.4f},{y(value):.4f}')
        s += [f'<polyline points="{" ".join(vals)}" fill="none" stroke="{colors[i%6]}" stroke-width="2.2"/>',f'<text x="{70+300*(i%3)}" y="{452+23*(i//3)}" style="fill:{colors[i%6]}">{mode}</text>']
    s += [f'<text x="75" y="417">0</text><text x="760" y="417">{cfg["role_updates"]} role updates</text>','<text x="75" y="497">No learning in these evaluations; no error bars or general convergence claim.</text>','</svg>']
    (target/'checkpoint-success.svg').write_text('\n'.join(s)+'\n')
    available=[m for m in ('independent','ctde','snapshot') if m in out['crossplay']]
    n=len(cfg['seeds']); cell=min(42,250/n); panel=350
    s=base('Frozen cross-play and adaptive partner are different protocols','Each matrix row is one seed encoder and column another seed decoder. Cells show exact success. The lower adaptation lines freeze CTDE decoders and update only new encoders; they are not heldout frozen tests.',1100,760)
    s+=['<text x="25" y="28" class="head">B. Frozen cross-play: rows encoder seed, columns decoder seed</text>']
    for k,mode in enumerate(available):
        left=65+k*panel;top=100
        s.append(f'<text x="{left}" y="63">{mode}</text>')
        for i,seed in enumerate(cfg['seeds']):
            s += [f'<text x="{left-32}" y="{top+(i+.65)*cell:.3f}">{seed}</text>',f'<text x="{left+(i+.1)*cell:.3f}" y="{top-10}">{seed}</text>']
            for j,v in enumerate(out['crossplay'][mode][i]):
                z=v['success'];r=int(245-70*z);g=int(220+15*z);b=int(215+15*z)
                xx=left+j*cell;yy=top+i*cell
                s += [f'<rect x="{xx:.3f}" y="{yy:.3f}" width="{cell:.3f}" height="{cell:.3f}" fill="rgb({r},{g},{b})" stroke="white"/>',f'<text x="{xx+3:.3f}" y="{yy+cell*.65:.3f}">{z:.2f}</text>']
    s += ['<text x="25" y="398" class="head">C. Receiver frozen; new sender adapts from two initial codes</text>']
    xx=lambda k:75+850*k/cfg['adapt_episodes']; yy=lambda z:670-230*z
    for z in (0,.5,1):s += [f'<line x1="75" y1="{yy(z)}" x2="925" y2="{yy(z)}" class="grid"/>',f'<text x="35" y="{yy(z)+5}">{z}</text>']
    for i,name in enumerate(('truth','flipped')):
        rows=[r for r in out['adaptation'] if r['initial_encoder']==name]
        if rows:
            pts=' '.join(f'{xx(c["episode"]):.4f},{yy(sum(r["checkpoints"][j]["score"]["success"] for r in rows)/len(rows)):.4f}' for j,c in enumerate(rows[0]['checkpoints']))
            s.append(f'<polyline points="{pts}" fill="none" stroke="{colors[i]}" stroke-width="2.5"/>')
        s.append(f'<text x="{80+310*i}" y="724" style="fill:{colors[i]}">initial sender: {name}</text>')
    s += [f'<text x="75" y="695">0</text><text x="710" y="695">{cfg["adapt_episodes"]} adaptation episodes</text>','<text x="75" y="750">All checkpoints and partner versions retained. Success probability, not observed team welfare.</text>','</svg>']
    (target/'crossplay-adaptation.svg').write_text('\n'.join(s)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output',type=Path,default=Path(__file__).with_name('results'))
    args=parser.parse_args();cfg=json.loads(args.input.read_text());validate(cfg);args.output.mkdir(parents=True,exist_ok=True)
    with (args.output/'trajectory.csv.gz').open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
            with io.TextIOWrapper(zipped,encoding='utf-8',newline='') as txt:
                writer=csv.writer(txt);writer.writerow(HEADER);out=run(cfg,writer)
    (args.output/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    figures(out,args.output)
    print(json.dumps(dict(runs=len(out['runs']),adaptation_runs=len(out['adaptation']),
              final_mean_success={m:sum(r['checkpoints'][-1]['score']['success'] for r in out['runs'] if r['mode']==m)/len(cfg['seeds']) for m in cfg['modes']})))


if __name__=='__main__':main()
