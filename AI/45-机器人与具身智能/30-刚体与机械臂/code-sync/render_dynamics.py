"""Saved-data scientific plots, reusing Matplotlib Agg; no new scene renderer."""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({'svg.hashsalt':'wwl-164-rigid-dynamics','font.family':'DejaVu Sans',
                     'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
COLORS = ['#1264a3','#cc651b','#24804d','#a63c57','#6958a6','#777777']


def save(fig,path,title,desc):
    fig.savefig(path,format='svg',metadata={'Date':None,'Title':title,'Description':desc})
    plt.close(fig)
    text = Path(path).read_text()
    Path(path).write_text(text.replace('</title>', '</title>\n <desc>'+escape(desc)+'</desc>', 1))


def render(root,output):
    root,output = Path(root),Path(output)
    output.mkdir(parents=True,exist_ok=True)
    results = json.loads((root/'results.json').read_text())
    rows = {}
    for line in (root/'trajectories.jsonl').read_text().splitlines():
        row = json.loads(line)
        rows.setdefault(row['case'],[]).append(row)
    example = results['examples']['rigid']
    fig,ax = plt.subplots(1,2,figsize=(11,4),layout='constrained')
    x = np.arange(3)
    for shift,values,color,label in [(-.17,example['body_origin_velocity_W_m_s'],COLORS[0],'p_dot: velocity of body origin'),
                                    (.17,example['V_space'][3:],COLORS[1],'v_s: space twist lower block')]:
        bars = ax[0].bar(x+shift,values,.34,color=color,label=label)
        ax[0].bar_label(bars,labels=['0' if abs(v)<1e-12 else f'{v:g}' for v in values],padding=3)
    ax[0].set(xticks=x,xticklabels=['x_W','y_W','z_W'],ylabel='linear components (m/s)',
              title='A. Same motion; the space lower block is not p_dot',ylim=(-3.5,2.))
    ax[0].axhline(0,color='black',lw=.8);ax[0].legend(fontsize=8,loc='lower right')
    power = [example['body_power_W'],example['space_power_W'],example['wrong_tip_velocity_power_W']]
    bars = ax[1].bar(np.arange(3),power,color=[COLORS[0],COLORS[2],COLORS[3]])
    ax[1].bar_label(bars,labels=[f'{v:+.1f} W' for v in power],padding=3)
    ax[1].set(xticks=np.arange(3),xticklabels=['F_b . V_b','F_s . V_s','wrong: F_s . (omega_s,p_dot)'],
              ylabel='power (W)',title='B. Power agrees only with matching reference points',ylim=(-.4,3.))
    ax[1].tick_params(axis='x',labelsize=8);ax[1].axhline(0,color='black',lw=.8)
    save(fig,output/'rigid-twist-power.svg','Space twist and endpoint velocity, matched wrench power',
         'Saved rigid example uses angular-first six-vectors, Rz(pi/2), translation (1,2,3) metres. '
         'Panel A compares linear components in the same world axes. Panel B shows 2.4 W in both '
         'correct representations and -0.1 W after falsely substituting p_dot into the space twist.')

    fig,axes = plt.subplots(2,2,figsize=(11,8),layout='constrained')
    ax=axes[0,0]
    for case,color,label in [('heavy_feedforward',COLORS[1],'heavy: feedforward'),
                             ('heavy_feedback',COLORS[0],'heavy: feedback'),
                             ('heavy_feedback_limited',COLORS[3],'heavy: feedback + limits')]:
        r=rows[case]; t=np.array([x['t_s'] for x in r])
        error=np.linalg.norm(np.array([x['q_rad'] for x in r])-np.array([x['q_ref_rad'] for x in r]),axis=1)
        ax.plot(t,error,color=color,label=label)
    ax.set(xlabel='time (s)',ylabel='joint error Euclidean norm (rad)',title='C. Feedback helps; saturation can defeat it')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[0,1]
    for case,color,label in [('nominal_fast_limited',COLORS[1],'fast T = 0.35 s'),
                             ('nominal_slow_limited',COLORS[0],'slow T = 3 s')]:
        r=rows[case];t=[x['t_s'] for x in r]
        ax.plot(t,[x['q_rad'][0] for x in r],color=color,label=label+' actual')
        ax.plot(t,[x['q_ref_rad'][0] for x in r],color=color,ls='--',label=label+' reference')
    ax.set(xlabel='time (s)',ylabel='shoulder angle q1 (rad)',title='D. Same geometric path; different timing and tracking')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[1,0];r=rows['heavy_feedback_limited'][:-1];t=[x['t_s'] for x in r]
    ax.plot(t,[x['requested_N_m'][0] for x in r],color=COLORS[3],ls='--',label='requested shoulder torque')
    ax.plot(t,[x['applied_N_m'][0] for x in r],color=COLORS[0],label='applied after clip')
    ax.axhline(20,color='black',ls=':',label='+20 N m limit');ax.axhline(-20,color='black',ls=':')
    ax.set(xlabel='time (s)',ylabel='shoulder motor torque (N m)',title='E. Heavy plant: requested torque is not actual input')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[1,1];r=rows['heavy_feedback_limited'];t=[x['t_s'] for x in r]
    e=np.array([x['kinetic_J']+x['potential_J'] for x in r]); change=e-e[0]
    net=np.array([x['motor_work_J']+x['external_work_J']-x['dissipated_J'] for x in r])
    ax.plot(t,change,color=COLORS[0],lw=2.5,label='mechanical E(t) - E(0)')
    ax.plot(t,net,color=COLORS[1],ls='--',label='motor + external work - dissipation')
    residual=max(abs(x['energy_residual_J']) for x in r)
    ax.text(.04,.08,f'max ledger residual = {residual:.2e} J',transform=ax.transAxes)
    ax.set(xlabel='time (s)',ylabel='energy change / net work (J)',title='F. Bad tracking can still obey the energy balance')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    save(fig,output/'arm-dynamics-feedback-energy.svg','Fixed 2R model mismatch, saturation, timing and energy ledger',
         'Six fixed runs, 5 ms zero-order-held motor torques, RK4 joint state and work integration. '
         'Panels C/E/F use mass and inertia 25 percent above the nominal controller. D compares '
         'the same joint path over .35 and 3 seconds with fixed limits (20,8) N m. Time rows are '
         'one deterministic trajectory, not independent robot trials. No contact model or physical robot.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    render(args.results,args.output)
