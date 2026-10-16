"""Scientific 2D plots of saved arm outputs; no 3D renderer or physical execution."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({'svg.hashsalt': 'wwl-164-planar-2r', 'font.family': 'DejaVu Sans',
                     'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
BLUE, ORANGE, GREEN = '#1264a3', '#cc651b', '#228552'


def save(fig, path, title, description):
    fig.savefig(path, format='svg', metadata={'Date': None, 'Title': title, 'Description': description})
    plt.close(fig)


def render(result, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), layout='constrained')
    ax = axes[0]
    case = next(x for x in result['targets'] if x['id'] == 'two_solutions')
    a = case['lengths_m'][0]
    for branch, color, label in zip(case['forward_checks'], [BLUE, ORANGE], ['q2 > 0', 'q2 < 0']):
        q = branch['q_rad']
        elbow = [a*np.cos(q[0]), a*np.sin(q[0])]
        p = branch['endpoint_W_m']
        ax.plot([0, elbow[0], p[0]], [0, elbow[1], p[1]], 'o-', color=color, lw=3,
                label=f'{label}: ({q[0]:.3f}, {q[1]:.3f}) rad')
    ax.scatter(*case['target_W_m'], s=150, marker='x', c='black', zorder=5)
    ax.annotate('same target (1, 1) m', (1,1), xytext=(.25,1.28), arrowprops={'arrowstyle':'->'})
    ax.set(xlabel='x_W (m)', ylabel='y_W (m)', title='A. Position IK: two branches, different tool angles',
           xlim=(-.2,1.6), ylim=(-.2,1.6), aspect='equal')
    ax.legend(loc='lower right', fontsize=8)
    ax.grid(alpha=.2)
    ax = axes[1]
    curve = result['null_curve']
    eps = np.array([x['epsilon_rad'] for x in curve])
    inward = np.array([x['inward_displacement_m'] for x in curve])
    ax.plot(eps, inward, 'o-', color=BLUE, label='exact FK: 2 - x_W')
    ax.plot(eps, eps**2, '--', color=ORANGE, label='epsilon^2 (leading term, m)')
    ax.set(xlabel='epsilon (rad), q = (epsilon, -2 epsilon)', ylabel='inward displacement (m)',
           title='B. Zero first derivative permits finite inward motion')
    ax.text(.02,.96, 'qdot proportional to (1, -2)\nJ(0) qdot = 0; y_W = 0', transform=ax.transAxes, va='top')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(alpha=.2)
    save(fig, output/'arm-branches-and-null-curve.svg',
         'Two position IK branches and finite motion along an instantaneous null direction',
         'Fixed unit links, counterclockwise positive joint angles, world x right and y up. '
         'Left: two arms reach (1,1) metres. Right: saved finite FK inward displacement versus '
         'epsilon, compared with the second-order prediction; a zero first derivative is not global immobility.')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), layout='constrained')
    rows = result['near_singular']
    eps = np.array([x['epsilon_rad'] for x in rows])
    demands = np.abs(np.array([x['demand_rad_s'] for x in rows]))
    ax = axes[0]
    for j, color in enumerate([BLUE, ORANGE]):
        ax.loglog(eps, demands[:,j], 'o-', color=color, label=f'abs(qdot{j+1})')
    ax.axhline(1., color='black', ls='--', label='joint speed limit: 1 rad/s')
    ax.set(xlabel='q2 = epsilon (rad), q1 = 0', ylabel='required joint speed (rad/s)',
           title='C. Fixed request vx = -0.1 m/s, vy = 0')
    ax.legend(fontsize=9)
    ax.grid(which='both', alpha=.2)
    row = next(x for x in rows if x['epsilon_rad'] == .02)
    ax = axes[1]
    values = np.array([[-.1,0.], row['scaled_velocity_m_s'], row['clipped_velocity_m_s']])
    positions = np.arange(3)
    for j, color, label in [(0,BLUE,'vx'),(1,ORANGE,'vy')]:
        bars = ax.bar(positions+(j-.5)*.3, values[:,j], .3, color=color, label=label)
        ax.bar_label(bars, labels=['0' if abs(v) < 1e-12 else f'{v:+.5f}' for v in values[:,j]], fontsize=8, padding=3)
    ax.axhline(0, color='black', lw=.8)
    ax.set(xticks=positions, xticklabels=['requested', 'uniform scale', 'component clip'],
           ylabel='endpoint velocity (m/s)', ylim=(-1.14,.17),
           title='D. At epsilon = 0.02 rad: clipping changes direction')
    ax.legend(loc='center left', bbox_to_anchor=(.03, .4))
    ax.grid(axis='y', alpha=.2)
    save(fig, output/'arm-near-singular-speed.svg',
         'Near singularity amplifies joint speed and component clipping changes endpoint direction',
         'Same unit-link model and fixed -0.1 m/s horizontal request. Log-log panel shows both '
         'absolute demanded joint speeds and the 1 rad/s limit. At epsilon .02 rad the second panel '
         'compares saved requested, uniformly scaled and component-clipped endpoint velocity components.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    render(json.loads(args.results.read_text()), args.output)
