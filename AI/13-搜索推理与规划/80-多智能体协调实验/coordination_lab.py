#!/usr/bin/env python3
"""Finite one-step coordination. Stdlib training; reuse the published #194 deviations.
Actions 0=L, 1=R. Each actor sees only its own Q and its own random stream.
Joint action/version logging is evaluator information, never a learner input.
"""
import argparse
import csv
from fractions import Fraction as F
import importlib.util
import json
import math
from pathlib import Path
import random

A = [[F(2), F(0)], [F(0), F(1)]]
SHARED = Path('社会科学/20-经济流动与宏观/50-博弈与机制/80-实践/01-有限博弈与混合策略/finite_games.py')


def load_shared(vault):
    path = Path(vault) / SHARED
    if not path.is_file():
        raise ValueError('supply --vault pointing to the WWL root with the published #194 source')
    spec = importlib.util.spec_from_file_location('wwl_finite_games', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probability(value):
    x = F(str(value))
    if not 0 <= x <= 1:
        raise ValueError('probability must lie in [0,1]')
    return x


def transition(state, a, b):
    if state not in ('ready', 'success', 'failure') or a not in (0, 1) or b not in (0, 1):
        raise ValueError('invalid finite state/action')
    if state != 'ready':
        return state, (0, 0)
    return ('success' if a == b else 'failure'), ((2, 2) if a == b == 0 else (1, 1) if a == b == 1 else (0, 0))


def effective(q):
    q = probability(q)
    return {'L': {'success': q, 'failure': 1-q, 'expected_reward': 2*q},
            'R': {'success': 1-q, 'failure': q, 'expected_reward': 1-q}}


def evaluate(p, q, game):
    p, q = probability(p), probability(q)
    dev = game.deviations(A, A, p, q)
    success = p*q + (1-p)*(1-q)
    return dict(p=p, q=q, joint=[p*q, p*(1-q), (1-p)*q, (1-p)*(1-q)],
                individual=dev['current'], team=sum(dev['current']), success=success,
                mismatch=1-success, unilateral_gain=dev['max_unilateral_gain'])


def policy(q_values, epsilon):
    """Probability of L; ties randomize uniformly, never favor an action by its name."""
    if len(q_values) != 2 or not all(math.isfinite(x) for x in q_values):
        raise ValueError('Q requires two finite values')
    if not math.isfinite(epsilon) or not 0 <= epsilon <= 1:
        raise ValueError('epsilon must lie in [0,1]')
    greedy = 1 if q_values[0] > q_values[1] else 0 if q_values[0] < q_values[1] else .5
    e = F(str(epsilon))
    return float((1-e)*F(greedy) + e/2)


def action(p, rng):
    return 0 if rng.random() < p else 1


def validate(cfg):
    for key in ('episodes', 'window'):
        if type(cfg[key]) is not int or cfg[key] < 1:
            raise ValueError(key + ' must be a positive integer')
    if cfg['episodes'] % cfg['window']:
        raise ValueError('episodes must be divisible by window')
    if not cfg['seeds'] or len(set(cfg['seeds'])) != len(cfg['seeds']) or any(type(x) is not int or x < 0 for x in cfg['seeds']):
        raise ValueError('seeds must be distinct nonnegative integers')
    for key in ('alpha', 'epsilon'):
        if not math.isfinite(cfg[key]) or not 0 < cfg[key] < 1:
            raise ValueError(key + ' must lie strictly between zero and one')
    for key in ('fixed_opponents', 'heldout_opponents'):
        if not cfg[key]:
            raise ValueError('opponent families must be nonempty')
        for q in cfg[key]:
            probability(q)
    if set(map(probability, cfg['fixed_opponents'])) & set(map(probability, cfg['heldout_opponents'])):
        raise ValueError('heldout q values must not be used for training')


def train(cfg, seed, opponent, writer=None):
    """One RNG draw per actor per episode. No reward/partner action enters selection."""
    streams = [random.Random(2*seed), random.Random(2*seed+1)]
    qs = [[0., 0.], [0., 0.]]
    checkpoints = []
    successes = rewards = 0
    for t in range(1, cfg['episodes']+1):
        # Snapshot both policies before drawing either action or updating either Q.
        ps = [policy(qs[0], cfg['epsilon']), policy(qs[1], cfg['epsilon']) if opponent is None else float(opponent)]
        acts = [action(ps[i], streams[i]) for i in range(2)]
        end, rs = transition('ready', *acts)
        for i in range(2 if opponent is None else 1):
            a = acts[i]
            qs[i][a] += cfg['alpha']*(rs[i]-qs[i][a])
        if writer is not None:
            writer.writerow([seed, 'colearn' if opponent is None else str(opponent), t,
                             t-1, t-1 if opponent is None else 'fixed:'+str(opponent),
                             *ps, *acts, end, *rs, *qs[0], *(qs[1] if opponent is None else ['', ''])])
        successes += int(end == 'success')
        rewards += sum(rs)
        if t % cfg['window'] == 0:
            checkpoints.append(dict(episode=t, success=successes/cfg['window'], team=rewards/cfg['window']))
            successes = rewards = 0
    return dict(seed=seed, opponent='colearn' if opponent is None else str(opponent), Q=qs if opponent is None else [qs[0]],
                greedy=[policy(v, 0) for v in qs[:2 if opponent is None else 1]],
                behavior=[policy(v, cfg['epsilon']) for v in qs[:2 if opponent is None else 1]], checkpoints=checkpoints)


def run(cfg, game, writer=None):
    validate(cfg)
    colearn = [train(cfg, seed, None, writer) for seed in cfg['seeds']]
    fixed = [train(cfg, seed, probability(q), writer) for q in cfg['fixed_opponents'] for seed in cfg['seeds']]
    cross = [[evaluate(left['greedy'][0], right['greedy'][1], game) for right in colearn] for left in colearn]
    heldout = [dict(seed=row['seed'], trained_with=row['opponent'], q=str(q),
                    score=evaluate(row['greedy'][0], q, game))
               for row in colearn+fixed for q in map(probability, cfg['heldout_opponents'])]
    cycle = [[0, 1]]
    for _ in range(6):
        a, b = cycle[-1]
        cycle.append([b, a])  # Each matches the other's previous action, simultaneously.
    return dict(config=cfg, transition_table=[dict(s=s, actions=[a,b], next=transition(s,a,b)[0], rewards=transition(s,a,b)[1])
                    for s in ('ready','success','failure') for a in (0,1) for b in (0,1)],
                effective={str(probability(q)):effective(probability(q)) for q in cfg['fixed_opponents']},
                pure_equilibria=game.pure_equilibria(A,A),
                mixed=evaluate(F(1,3),F(1,3),game),
                public_coin=dict(joint=[F(1,3),F(0),F(0),F(2,3)], success=F(1), individual=[F(4,3)]*2, team=F(8,3)),
                stale_best_response_cycle=cycle, colearn=colearn, fixed=fixed, crossplay=cross,
                behavior_self=[evaluate(*r['behavior'],game) for r in colearn], heldout=heldout,
                replay=dict(old_q='4/5', current_q='1/5', equal_version_pool=effective(F(1,2)),
                            weights_other_L=F(1,4), weights_other_R=F(4)))


def serial(value):
    if isinstance(value, F):
        return str(value)
    raise TypeError(type(value).__name__)


def figures(out, target):
    """Only this fixed reward/absorbing-state model, variable training configuration."""
    def svg(title, desc, width, height):
        return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                f'<title>{title}</title><desc>{desc}</desc>', '<rect width="100%" height="100%" fill="white"/>',
                '<style>text{font:14px Arial,sans-serif;fill:#17212d}.head{font-weight:bold;font-size:19px}.grid{stroke:#d7dfe7;stroke-width:1}</style>']
    s = svg('Same marginal policies, different joint behavior', 'Fixed LL reward 2 and RR reward 1. Independent p=q=1/3 has four event probabilities; shared public coin has only diagonal events. Height is probability.', 940, 390)
    s.append('<text x="30" y="30" class="head">Joint events: independent randomization vs public signal</text>')
    for k, (name, values) in enumerate([('Independent p=q=1/3',out['mixed']['joint']),('Public coin: P(L signal)=1/3',out['public_coin']['joint'])]):
        ox=70+450*k
        s.append(f'<text x="{ox}" y="64">{name}</text>')
        for j, (label,v) in enumerate(zip(['LL','LR','RL','RR'], values)):
            x=ox+70*j; h=220*float(v)
            s.append(f'<rect x="{x}" y="{310-h:.4f}" width="42" height="{h:.4f}" fill="{"#2563a6" if j in (0,3) else "#b34438"}"/>')
            s.append(f'<text x="{x}" y="{300-h:.4f}">{v}</text><text x="{x}" y="334">{label}</text>')
        s.append(f'<text x="{ox}" y="363">Success {out["mixed" if k==0 else "public_coin"]["success"]}; reward each {out["mixed" if k==0 else "public_coin"]["individual"][0]}</text>')
    s.append('</svg>'); (target/'joint-events.svg').write_text('\n'.join(s)+'\n')
    n=len(out['colearn']); cell=min(43,520/n); left=620; top=90
    height=max(470, int(top+n*cell+90))
    s=svg('Training windows and frozen cross-play', 'Left individual-seed non-overlapping windows show sampled team reward. Right exact greedy deployment mismatch probabilities: rows agent zero from one seed, columns agent one from another. No learning during evaluation.', 1140,height)
    s += ['<text x="25" y="30" class="head">A. Co-learning: sampled team return / episode</text>', '<text x="600" y="30" class="head">B. Frozen greedy cross-play: mismatch</text>']
    x=lambda t:65+470*t/out['config']['episodes']; y=lambda r:375-65*r
    for r in range(5):
        s += [f'<line x1="65" y1="{y(r)}" x2="535" y2="{y(r)}" class="grid"/>',f'<text x="40" y="{y(r)+5}">{r}</text>']
    colors=['#2563a6','#b34438','#328451','#9459a4','#967009','#178b9f','#575861','#d05b12']
    for k,row in enumerate(out['colearn']):
        points=' '.join(f'{x(c["episode"]):.4f},{y(c["team"]):.4f}' for c in row['checkpoints'])
        s.append(f'<polyline points="{points}" fill="none" stroke="{colors[k%8]}" stroke-width="1.6"/>')
        s.append(f'<text x="{65+(k%4)*122}" y="{415+20*(k//4)}" style="fill:{colors[k%8]}">seed {row["seed"]}</text>')
    s += [f'<text x="65" y="397">0</text><text x="490" y="397">{out["config"]["episodes"]} episodes</text>',f'<text x="65" y="65">Window {out["config"]["window"]}; team sum in [0,4], not equilibrium evidence</text>']
    for i,row in enumerate(out['crossplay']):
        seed=out['colearn'][i]['seed']
        s += [f'<text x="{left-42}" y="{top+(i+.65)*cell:.3f}">{seed}</text>',f'<text x="{left+(i+.1)*cell:.3f}" y="{top-10}">{seed}</text>']
        for j,score in enumerate(row):
            v=float(score['mismatch']); xx=left+j*cell; yy=top+i*cell
            s.append(f'<rect x="{xx:.3f}" y="{yy:.3f}" width="{cell:.3f}" height="{cell:.3f}" fill="{"#f2ddd8" if v else "#dcebdd"}" stroke="white"/>')
            s.append(f'<text x="{xx+cell*.35:.3f}" y="{yy+cell*.65:.3f}">{score["mismatch"]}</text>')
    s += [f'<text x="600" y="{top+n*cell+30:.3f}">Row: actor 0 seed; column: actor 1 seed</text>',f'<text x="600" y="{top+n*cell+53:.3f}">0 = coordinated; 1 = wrong convention. Units: probability.</text>','</svg>']
    (target/'learning-crossplay.svg').write_text('\n'.join(s)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output',type=Path,default=Path(__file__).with_name('results'))
    parser.add_argument('--vault',type=Path,default=Path(__file__).resolve().parents[3])
    args=parser.parse_args()
    cfg=json.loads(args.input.read_text()); validate(cfg)
    shared=load_shared(args.vault); args.output.mkdir(parents=True,exist_ok=True)
    with (args.output/'trajectory.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['seed','opponent','episode','actor0_version','actor1_version','p0_L','p1_L','a0','a1','next','r0','r1','Q0L_after','Q0R_after','Q1L_after','Q1R_after'])
        out=run(cfg,shared,writer)
    (args.output/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=serial)+'\n')
    figures(out,args.output)
    print(json.dumps({'runs':len(out['colearn'])+len(out['fixed']),'episodes_each':cfg['episodes'],'seeds':cfg['seeds'],'greedy_profiles':[r['greedy'] for r in out['colearn']]}))


if __name__=='__main__':
    main()
