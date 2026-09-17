"""Scientific plots tied to actual report; Matplotlib Agg, no GUI or downloads."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def save_figure(fig, directory, stem):
    svg = directory / (stem + '.svg')
    fig.savefig(svg, metadata={'Date': None})
    svg.write_text('\n'.join(line.rstrip(' \t') for line in svg.read_text().splitlines()) + '\n')
    fig.savefig(directory / (stem + '.png'), dpi=170)
    plt.close(fig)


def generate(report_path, out_dir):
    d=Path(out_dir)
    if d.exists() or d.is_symlink():
        raise ValueError('a new figure directory is required; refuse existing versions')
    report=json.loads(Path(report_path).read_text())
    d.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({'font.size':11, 'svg.fonttype':'none', 'svg.hashsalt':'bike-local-hour-v1'})
    pi=np.linspace(.01,.99,199)
    fig,ax=plt.subplots(figsize=(8,4.4),layout='constrained')
    ax.plot(pi,.8*pi/(.8*pi+.1*(1-pi)),label='TPR=0.8, FPR=0.1')
    for base,ppv,g in [(.2,160/240,'A'),(.6,480/520,'B')]:
        ax.scatter([base],[ppv],s=60,zorder=3)
        ax.annotate(f'{g}: base={base:.1f}, PPV={ppv:.3f}',(base,ppv),xytext=(8,-25 if g=='B' else 15),textcoords='offset points')
    ax.set(xlabel='Group base rate P(Y=1 | G)',ylabel='PPV P(Y=1 | decision=1,G)',
           title='Equal error rates do not equalize PPV',xlim=(0,1),ylim=(0,1))
    ax.grid(alpha=.25);ax.legend(loc='lower right')
    save_figure(fig,d,'bayes_ppv')
    groups=report['groups_test']['hour_band']; keys=list(groups)
    fig,axes=plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
    axes[0].bar(keys,[groups[k]['mae'] for k in keys],color='#356E9D')
    axes[0].set(xlabel='Recorded local hour band',ylabel='MAE (rentals per observed hour)',
                title='2012 Q4: error varies by hour')
    axes[1].bar(keys,[groups[k]['coverage'] for k in keys],color='#569772')
    axes[1].axhline(.9,color='#C05236',linestyle='--',label='Nominal target 0.90')
    axes[1].set(xlabel='Recorded local hour band',ylabel='Empirical interval coverage',
                title=f"Radius q={report['interval_radius']:.2f}; overall={report['test']['selected']['coverage']:.3f}",ylim=(0,1.05))
    axes[1].legend(loc='lower left')
    for ax in axes:
        ax.grid(axis='y',alpha=.2);ax.tick_params(axis='x',rotation=20)
    save_figure(fig,d,'bike_group_failures')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();generate(a.report,a.out)
