"""Exact coordinate/penalty and two-dimensional update examples."""
import json
from fractions import Fraction as F
from pathlib import Path


def mm(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(len(b)))
             for j in range(len(b[0]))] for i in range(len(a))]


def transpose(a):
    return [list(x) for x in zip(*a)]


def stringify(value):
    if isinstance(value,list):return [stringify(x) for x in value]
    if isinstance(value,dict):return {k:stringify(v) for k,v in value.items()}
    return str(value)


def calculate(config):
    scales=[F(x) for x in config['feature_scales']]
    if any(x <= 0 for x in scales):raise ValueError('Scales must be positive.')
    eta=F(config['step_size'])
    h=[[F(1),F(0)],[F(0),F(100)]]
    d=[[F(1),F(0)],[F(0),F(1,10)]]
    w=[[F(1)],[F(1)]]
    hv=mm(mm(transpose(d),h),d)
    preconditioner=mm(d,transpose(d))
    gradient=mm(h,w)
    preconditioned=mm(preconditioner,gradient)
    scalar=[]
    for scale in scales:
        raw=scale/(scale*scale+1)
        preserved=scale/(2*scale*scale)
        scalar.append({'scale':scale,'untransformed_coefficient':raw,
                       'untransformed_prediction':scale*raw,
                       'transformed_penalty':scale*scale,
                       'preserved_coefficient':preserved,
                       'preserved_prediction':scale*preserved})
    return stringify({'scalar':scalar,'hessian_v':hv,'dd_transpose':preconditioner,
                      'ordinary_w_step':[w[i][0]-eta*gradient[i][0] for i in range(2)],
                      'mapped_v_step':[w[i][0]-eta*preconditioned[i][0] for i in range(2)]})


if __name__ == '__main__':
    config=json.loads(Path(__file__).with_name('scaling_inputs.json').read_text())
    print(json.dumps(calculate(config),indent=2))
