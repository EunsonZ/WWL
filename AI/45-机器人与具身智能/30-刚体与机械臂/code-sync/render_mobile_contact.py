"""Render saved-data scientific plots, without a new geometry/physics engine."""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np

plt.rcParams.update({'svg.hashsalt':'wwl-164-mobile-contact','font.family':'DejaVu Sans',
                     'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
BLUE,ORANGE,GREEN,PURPLE='#1264a3','#cc651b','#24804d','#8b479c'


def save(fig,path,title,desc):
    fig.savefig(path,format='svg',metadata={'Date':None,'Title':title,'Description':desc})
    plt.close(fig)
    text=Path(path).read_text();Path(path).write_text(text.replace('</title>','</title>\n <desc>'+escape(desc)+'</desc>',1))


def read_groups(path):
    groups={}
    for line in Path(path).read_text().splitlines():
        row=json.loads(line);groups.setdefault(row['case'],[]).append(row)
    return groups


def contact_velocity_with_events(rows,events):
    points=[(r['t_s'],0,r['state_x_y_vx_vy'][2]) for r in rows]
    for event in events:
        if event['kind']=='impact':
            points.extend([(event['t_s'],1,event['state_before'][2]),(event['t_s'],2,event['state_after'][2])])
        else:points.append((event['t_s'],1,0.))
    points.sort()
    return np.array([p[0] for p in points]),np.array([p[2] for p in points])


def render(root,output):
    root,output=Path(root),Path(output);output.mkdir(parents=True,exist_ok=True)
    config=json.loads((Path(__file__).resolve().parents[1]/'mobile-contact-inputs.json').read_text())
    p=config['mobile'];center=p['obstacle_center_W_m'];radius=p['obstacle_radius_m']
    result=json.loads((root/'results.json').read_text());mobile=read_groups(root/'mobile.jsonl')
    contact=read_groups(root/'contact.jsonl');events=read_groups(root/'events.jsonl')
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),layout='constrained')
    ax=axes[0]
    ax.add_patch(Circle(center,radius,color='#777777',label=f'obstacle r = {radius:g} m'))
    ax.add_patch(Circle(center,radius+p['body_radius_m'],fill=False,ls=':',lw=1.6,color='#777777',label=f'inflated by robot r = {p["body_radius_m"]:g} m'))
    ax.plot([0.,0.],[0.,1.],ls='--',color='black',lw=3,alpha=.4,label='geometric centerline')
    for case,color,label in [('slow_feasible',BLUE,'slow: turn / drive / turn'),('fast_clipped',ORANGE,'fast wheel clip: misses target')]:
        q=np.array([r['q_x_y_heading'] for r in mobile[case]])
        ax.plot(q[:,0],q[:,1],color=color,lw=1.8,label=label)
        ax.scatter(q[-1,0],q[-1,1],color=color,s=35)
    ax.annotate('required heading while driving',xy=(0.,.55),xytext=(-.25,.9),fontsize=8,
                arrowprops={'arrowstyle':'->','color':BLUE},color=BLUE)
    ax.arrow(0.,.45,0.,.14,width=.008,color=BLUE,length_includes_head=True)
    ax.arrow(0.,.45,.14,0.,width=.008,color='black',length_includes_head=True)
    ax.annotate('heading 0 cannot drive upward',xy=(.1,.45),xytext=(-.3,.1),fontsize=7,arrowprops={'arrowstyle':'->','color':'black'})
    ax.scatter([0.],[1.],marker='x',s=70,color='black')
    ax.set(xlabel='world x (m)',ylabel='world y (m)',aspect='equal',xlim=(-.35,1.05),ylim=(-.2,1.25),
           title='A. Centerline alone does not specify a feasible pose path')
    ax.legend(loc='lower right',fontsize=7);ax.grid(alpha=.15)
    ax=axes[1]
    for case,color,style,label in [('slow_feasible',BLUE,'-','slow requested = applied (9 s)'),
                                  ('fast_unbounded_counterfactual',ORANGE,'--','fast requested (0.9 s), infeasible'),
                                  ('fast_clipped',GREEN,'-','fast applied after wheel clip')]:
        rows=mobile[case];end=rows[-1]['t_s'];rr=rows[:-1]
        rates=np.max(np.abs([r['applied_wheel_rad_s'] for r in rr]),axis=1)
        ax.plot(np.array([r['t_s'] for r in rr])/end,rates,color=color,ls=style,label=label)
    ax.axhline(4.,color='black',ls=':',label='4 rad/s wheel limit')
    ax.set(xlabel='t / maneuver duration (dimensionless)',ylabel='max(abs(left), abs(right)) (rad/s)',
           title='B. Compressing the same phases by 10 multiplies demand')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    save(fig,output/'mobile-feasibility.svg','Differential drive nonholonomic and wheel-rate feasibility',
         'Same circle footprint and fixed obstacle. A compares centerline with slow feasible reorientation '
         'and fast clipped actual path; black lateral arrow at heading zero is incompatible with no-slip. '
         'B uses normalized time explicitly: actual durations are 9 and .9 seconds, wheel rates remain rad/s. '
         'All paths and rates come from the saved held-input states; no wheel torque or traction model.')

    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    ax=axes[0,0]
    for case,color,label in [('inelastic_slide_stop',BLUE,'e = 0, support after first impact'),
                             ('partial_rebound',ORANGE,'e = 0.6, finite pre-Zeno horizon'),
                             ('elastic_no_friction',GREEN,'e = 1, frictionless')]:
        rows=contact[case]
        ax.plot([r['t_s'] for r in rows],[r['state_x_y_vx_vy'][1] for r in rows],color=color,label=label)
        impacts=[x for x in events[case] if x['kind']=='impact']
        ax.scatter([x['t_s'] for x in impacts],[0.]*len(impacts),color=color,marker='x')
    ax.axhline(0,color='black',lw=.8);ax.set(xlabel='time (s)',ylabel='height y (m)',title='C. Locate impact events, then continue the remaining time')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[0,1]
    for case,color,label in [('inelastic_no_friction',GREEN,'mu = 0: tangent velocity persists'),
                             ('inelastic_slide_stop',BLUE,'e = 0, mu = 0.1: impact + slide + stop'),
                             ('partial_rebound',ORANGE,'e = 0.6, mu = 0.1: impact jumps')]:
        t,v=contact_velocity_with_events(contact[case],events[case])
        ax.plot(t,v,color=color,label=label)
    ax.set(xlabel='time (s)',ylabel='tangent velocity vx (m/s)',title='D. Normal contact does not itself stop tangential motion')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[1,0];r=contact['inelastic_slide_stop'];t=[x['t_s'] for x in r]
    energy=np.array([x['mechanical_energy_J'] for x in r])
    loss=np.array([x['impact_normal_loss_J']+x['impact_tangent_loss_J']+x['slide_loss_J'] for x in r])
    ax.plot(t,energy,color=BLUE,label='mechanical energy')
    ax.plot(t,loss,color=ORANGE,label='cumulative impact + sliding loss')
    ax.plot(t,energy+loss,color=GREEN,ls='--',label='energy + loss = initial 10.935 J')
    ax.set(xlabel='time (s)',ylabel='energy / loss (J)',title='E. Ledger includes impact loss and sustained friction')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[1,1];x=result['examples']['projection_counterexample']
    values=[x['exact_energy_J'],x['clamp_y_only_energy_J'],x['clamp_y_vy_energy_J']]
    bars=ax.bar([0,1,2],values,color=[GREEN,ORANGE,PURPLE]);ax.bar_label(bars,labels=[f'{v:.5f}' for v in values],padding=3)
    ax.axhline(9.81,color='black',ls=':',label='initial 9.81 J')
    ax.set(xticks=[0,1,2],xticklabels=['event elastic','clamp y only','clamp y and vy'],ylabel='mechanical energy (J)',
           ylim=(0,14),title='F. Separate vertical drop: dt = 0.5 s, e = 1')
    ax.legend(fontsize=8)
    save(fig,output/'contact-events-energy.svg','Point contact events, Coulomb friction, and energy counterexamples',
         'C/D/E use mass 1 kg, initial height 1 m and vx 1.5 m/s. Exact event pre/post velocities '
         'are inserted at the same time to show jumps, not a fictitious ramp. Four fixed cases use '
         'single point contact without spin. F is a separate vertical-only elastic drop (initial '
         '9.81 J), contrasting exact event handling with two declared wrong coarse projections.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();render(args.results,args.output)
