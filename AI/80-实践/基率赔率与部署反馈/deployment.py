"""Exact ideal retraining and performative-risk calculations; no file writes."""
import json
from fractions import Fraction as F
from pathlib import Path


def calculate(config):
    initial = F(config['theta_initial'])
    steps = config['steps']
    if not 0 <= initial <= F(1,2) or type(steps) is not int or not 0 <= steps <= 100:
        raise ValueError('Use theta in [0,1/2] and an integer step count in [0,100].')
    theta = initial
    trajectory = [str(theta)]
    for _ in range(steps):
        theta = theta/2 + F(1,4)
        trajectory.append(str(theta))
    def risk(x):
        return (x/2-F(1,4))**2+x*x
    fixed_mean, fixed_noise = F(config['fixed_mean']), F(config['fixed_noise'])
    if not (0 <= fixed_mean <= F(1,2) and fixed_noise >= 0
            and 0 <= fixed_mean-fixed_noise <= fixed_mean+fixed_noise <= 1):
        raise ValueError('The fixed-distribution control must fit the declared ranges.')
    return {'trajectory': trajectory, 'stable': '1/2', 'optimal': '1/10',
            'stable_risk': str(risk(F(1,2))), 'optimal_risk': str(risk(F(1,10))),
            'retrain_from_optimal': str(F(1,10)/2+F(1,4)),
            'fixed_stable': str(fixed_mean), 'fixed_optimal': str(fixed_mean),
            'fixed_risk': str(fixed_noise**2)}


if __name__ == '__main__':
    config = json.loads(Path(__file__).with_name('deployment_inputs.json').read_text())
    print(json.dumps(calculate(config), indent=2))
