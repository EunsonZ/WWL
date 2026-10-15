"""U6 finite real-vector detection; known sigma and finite search grid.
All simulation streams split by SeedSequence; no output is written on import.
"""
import argparse
import json
from pathlib import Path
from statistics import NormalDist
import numpy as np

NORMAL = NormalDist()


def real_array(x, name):
    """Reject complex values before float conversion, including object arrays."""
    try:
        raw = np.asarray(x)
        if np.iscomplexobj(raw) or (raw.dtype == object and any(
                isinstance(v, (complex, np.complexfloating)) or np.iscomplexobj(v)
                for v in raw.flat)):
            raise ValueError(name + ' must be real')
        a = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as e:
        raise ValueError(name + ' must contain real finite numeric values') from e
    if not np.all(np.isfinite(a)):
        raise ValueError(name + ' must contain real finite numeric values')
    return a


def vector(x, name='vector'):
    a = real_array(x, name)
    if a.ndim != 1 or a.size == 0:
        raise ValueError(name + ' must be a nonempty finite real vector')
    return a


def positive(x, name):
    a = real_array(x, name)
    if a.ndim != 0 or a <= 0:
        raise ValueError(name + ' must be a positive finite real scalar')
    return float(a)


def template(s):
    s = vector(s, 'template')
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        energy = float(np.dot(s, s))
    if not np.isfinite(energy) or energy <= 0:
        raise ValueError('template energy must be positive and numerically finite')
    return s


def threshold(alpha):
    a = real_array(alpha, 'alpha')
    if a.ndim != 0 or not 0 < a < 1:
        raise ValueError('alpha must lie strictly between zero and one')
    return -NORMAL.inv_cdf(float(a))


def known_score(x, s, sigma=1.0):
    x, s = vector(x), template(s)
    if x.shape != s.shape:
        raise ValueError('x and template shapes differ')
    sigma = positive(sigma, 'sigma')
    with np.errstate(over='ignore', divide='ignore', invalid='ignore', under='ignore'):
        numerator = float(x @ s)
        denominator = sigma * float(np.linalg.norm(s))
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator <= 0:
        raise ValueError('score intermediate is outside numerical support')
    score = numerator / denominator
    if not np.isfinite(score):
        raise ValueError('score must be numerically finite')
    return score


def white_scores(x, s, sigma=1.0):
    x, s = vector(x), template(s)
    if x.size < s.size:
        raise ValueError('record shorter than template')
    sigma = positive(sigma, 'sigma')
    with np.errstate(over='ignore', divide='ignore', invalid='ignore', under='ignore'):
        numerator = np.correlate(x, s, mode='valid')
        denominator = sigma * float(np.linalg.norm(s))
        scores = numerator / denominator
    if (not np.all(np.isfinite(numerator)) or not np.isfinite(denominator)
            or denominator <= 0 or not np.all(np.isfinite(scores))):
        raise ValueError('scores or intermediates are outside numerical support')
    return scores


def colored_score(x, s, covariance):
    """Real SPD C; symmetry tolerance is 1e-12 of max(abs(C)), unit invariant.
    Roundoff within that relative tolerance is explicitly symmetrized before
    Cholesky; inconsistent triangles are never silently read as another model.
    """
    x, s = vector(x), template(s)
    c = real_array(covariance, 'covariance')
    if x.shape != s.shape or c.shape != (s.size,s.size):
        raise ValueError('covariance shape and vectors must match')
    scale = float(np.max(np.abs(c)))
    if scale <= 0:
        raise ValueError('covariance must be positive definite')
    cn = c / scale
    if np.max(np.abs(cn-cn.T)) > 1e-12:
        raise ValueError('covariance must be symmetric within relative tolerance 1e-12')
    cn = 0.5 * (cn + cn.T)
    try:
        l = np.linalg.cholesky(cn)
        wx = np.linalg.solve(l, x / np.sqrt(scale))
        ws = np.linalg.solve(l, s / np.sqrt(scale))
    except np.linalg.LinAlgError as e:
        raise ValueError('covariance must be positive definite and solvable') from e
    norm = float(np.linalg.norm(ws))
    if not np.isfinite(norm) or norm <= 0 or not np.all(np.isfinite(wx)):
        raise ValueError('whitened vectors must have finite values and nonzero template norm')
    score = float(wx @ (ws / norm))
    if not np.isfinite(score):
        raise ValueError('score must be numerically finite')
    return score


def periodogram(x, fs, demean=False):
    """Rectangular, one-sided density: unit(x)^2/Hz; exact bin-area identity."""
    x = vector(x)
    fs = positive(fs,'fs')
    if demean:
        x = x - np.mean(x)
    scale=float(np.max(np.abs(x)))
    if not np.isfinite(scale): raise ValueError('PSD outside supported range')
    if scale==0: return np.fft.rfftfreq(x.size,1/fs),np.zeros(x.size//2+1)
    p = abs(np.fft.rfft(x/scale))**2 * (scale*scale/(fs*x.size))
    if not np.all(np.isfinite(p)): raise ValueError('PSD outside supported range')
    if x.size % 2 == 0:
        p[1:-1] *= 2
    else:
        p[1:] *= 2
    return np.fft.rfftfreq(x.size,1/fs), p


def sample_variance(x):
    x = vector(x)
    if x.size < 2:
        raise ValueError('unbiased iid variance needs at least two samples')
    scale=float(np.max(np.abs(x)))
    if not np.isfinite(scale): raise ValueError('variance outside supported range')
    if scale==0: return 0.
    value=float(np.sum((x/scale-(x/scale).mean())**2)/(x.size-1))*scale*scale
    if not np.isfinite(value): raise ValueError('variance outside supported range')
    return value


def evaluate(labels, decisions):
    """FPR/TPR conditional denominators; absent class is unknown (None)."""
    y, d = real_array(labels, 'labels'), real_array(decisions, 'decisions')
    if y.ndim != 1 or y.size == 0 or d.shape != y.shape or not np.all(np.isin(y,[0,1])) or not np.all(np.isin(d,[0,1])):
        raise ValueError('matching nonempty binary labels and decisions required')
    n0,n1 = int(np.sum(y==0)), int(np.sum(y==1))
    fp,tp = int(np.sum((y==0)&(d==1))),int(np.sum((y==1)&(d==1)))
    return {'n0':n0,'n1':n1,'fp':fp,'tp':tp,'fpr':fp/n0 if n0 else None,'tpr':tp/n1 if n1 else None}


def calibrate_maxima(maxima, alpha):
    """Noise-only training quantile; empirical, no population guarantee."""
    m=vector(maxima,'maxima')
    threshold(alpha)
    return float(np.quantile(m,1-alpha,method='higher'))


def simulation(seed=62026, ntrain=6000, ntest=12000):
    if not isinstance(seed,(int,np.integer)) or seed<0 or min(ntrain,ntest)<2:
        raise ValueError('nonnegative integer seed and at least two train/test records')
    s=np.array([0.0,1.0,2.0,1.0,0.0]); n=24; amplitude=1.25; alpha=.01
    streams=[np.random.default_rng(v) for v in np.random.SeedSequence(seed).spawn(3)]
    def bank(rng,count):
        x=rng.normal(size=(count,n))
        return x, np.array([white_scores(row,s) for row in x])
    _, train=bank(streams[0],ntrain)
    x0,z0=bank(streams[1],ntest)
    x1=streams[2].normal(size=(ntest,n)); starts=streams[2].integers(0,n-s.size+1,size=ntest)
    for i,k in enumerate(starts): x1[i,k:k+s.size]+=amplitude*s
    z1=np.array([white_scores(row,s) for row in x1])
    g=calibrate_maxima(train.max(axis=1),alpha)
    single=threshold(alpha); bonf=threshold(alpha/z0.shape[1])
    estimate=z1.argmax(axis=1); detected=z1.max(axis=1)>g
    result={'seed':seed,'ntrain':ntrain,'ntest_per_class':ntest,'sigma':1.0,'amplitude':amplitude,'template':s.tolist(),'record_length':n,'search_positions':z0.shape[1],'alpha':alpha,'threshold_single':single,'threshold_bonferroni':bonf,'threshold_calibrated':g,
      'fpr_at_one_position':float(np.mean(z0[:,0]>single)),
      'fpr_global_using_single':float(np.mean(z0.max(axis=1)>single)),
      'fpr_global_bonferroni':float(np.mean(z0.max(axis=1)>bonf)),
      'fpr_global_calibrated':float(np.mean(z0.max(axis=1)>g)),
      'tpr_global_calibrated':float(detected.mean()),
      'arrival_mae_all_h1_samples':float(np.mean(abs(estimate-starts))),
      'arrival_mae_detected_only_samples':float(np.mean(abs(estimate[detected]-starts[detected]))) if detected.any() else None,
      'known_arrival_theory_tpr':1-NORMAL.cdf(single-amplitude*np.linalg.norm(s)),
      'evidence':'finite simulated records, not confidence interval or NP proof'}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',required=True,type=Path); a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'results.json').write_text(json.dumps(simulation(),indent=2)+'\n')

if __name__=='__main__': main()
