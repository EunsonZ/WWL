"""Reproducible retrospective NOAA annual CO2 comparison, no network access.
Python >=3.10, NumPy. Plotting only in run() additionally needs Matplotlib.
All ppm errors are prediction minus observation; data uncertainty is not model error.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import numpy as np

BASE = Path(__file__).resolve().parent
CENTER = 1979.0
SCALE = 20.0

def vector(value, name):
    a = np.asarray(value, dtype=float)
    if a.ndim != 1 or a.size == 0 or not np.isfinite(a).all():
        raise ValueError(f'{name} must be a nonempty finite vector')
    return a

def design(years, degree, center=CENTER, scale=SCALE):
    y = vector(years, 'years')
    if type(degree) is not int or degree not in (1, 2):
        raise ValueError('degree must be integer 1 or 2')
    if not math.isfinite(center) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('finite center and positive scale required')
    with np.errstate(over='ignore', invalid='ignore'):
        x = (y-center)/scale
        a = np.column_stack([x**i for i in range(degree+1)])
    if not np.isfinite(a).all():
        raise ValueError('design overflow')
    return a

def fit(years, values, degree, center=CENTER, scale=SCALE):
    a = design(years, degree, center, scale)
    b = vector(values, 'values')
    if len(b) != len(a) or len(b) < degree+1:
        raise ValueError('matching lengths and sufficient observations required')
    beta, _, rank, singular = np.linalg.lstsq(a, b, rcond=None)
    if rank != degree+1:
        raise ValueError('rank deficient design: coefficients not identifiable')
    if not np.isfinite(beta).all():
        raise ValueError('nonfinite fitted coefficients')
    return beta, float(singular[0]/singular[-1])

def predict(years, beta, center=CENTER, scale=SCALE):
    b = vector(beta, 'beta')
    if len(b) not in (2, 3):
        raise ValueError('beta must have length 2 or 3')
    with np.errstate(over='ignore', invalid='ignore'):
        p = design(years, len(b)-1, center, scale) @ b
    if not np.isfinite(p).all():
        raise ValueError('prediction overflow')
    return p

def metrics(observed, predicted):
    y, p = vector(observed, 'observed'), vector(predicted, 'predicted')
    if y.shape != p.shape:
        raise ValueError('matching lengths required')
    with np.errstate(over='ignore', invalid='ignore'):
        e = p-y
        rmse = np.sqrt(np.mean(e*e))
    if not np.isfinite(e).all() or not np.isfinite(rmse):
        raise ValueError('metric overflow')
    return {'n':len(y), 'rmse':float(rmse), 'mae':float(np.mean(abs(e))),
            'bias':float(np.mean(e))}

def load_data(path):
    with Path(path).open(encoding='utf-8') as f:
        reader = csv.DictReader(line for line in f if not line.startswith('#'))
        rows = list(reader)
        fields = reader.fieldnames
    expected = {'year', 'mean', 'unc'}
    if not rows or fields is None or len(fields) != 3 or set(fields) != expected:
        raise ValueError('expected exactly NOAA year,mean,unc columns')
    for row in rows:
        if set(row) != expected or any(row[k] is None or not row[k].strip() for k in expected):
            raise ValueError('every row must contain exactly three nonempty fields')
    try:
        a = np.array([[float(r[k]) for k in ('year','mean','unc')] for r in rows])
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid numeric data') from exc
    if not np.isfinite(a).all() or (np.diff(a[:,0]) <= 0).any():
        raise ValueError('finite, strictly increasing years required')
    if (a[:,0] != np.floor(a[:,0])).any() or (a[:,1] <= 0).any() or (a[:,2] < 0).any():
        raise ValueError('integer years, positive mole fractions and nonnegative uncertainties required')
    return a

def interval(data, first, last):
    if type(first) is not int or type(last) is not int or first > last:
        raise ValueError('ordered integer endpoints required')
    part = data[(data[:,0] >= first) & (data[:,0] <= last)]
    if len(part) != last-first+1 or not np.array_equal(part[:,0], np.arange(first,last+1)):
        raise ValueError('incomplete requested year interval')
    return part

def choose_degree(scores):
    if set(scores) != {1,2} or not all(math.isfinite(s) and s >= 0 for s in scores.values()):
        raise ValueError('finite nonnegative scores for degrees 1 and 2 required')
    return 1 if scores[1] <= scores[2]+1e-9 else 2

def save_svg(fig, path):
    """Remove trailing spaces/tabs from SVG lines without changing plot objects."""
    path = Path(path)
    fig.savefig(path, metadata={'Date': None})
    path.write_bytes(b'\n'.join(line.rstrip(b' \t') for line in path.read_bytes().split(b'\n')))

def run(output=BASE):
    """Write deterministic JSON and figures only to caller-selected output directory."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'svg.hashsalt':'wwl-co2-m4','font.family':'DejaVu Sans'})
    out = Path(output)
    (out/'图').mkdir(parents=True, exist_ok=True)
    path = BASE/'数据/co2_annmean_mlo.csv'
    data = load_data(path)
    train = interval(data,1959,1999)
    selection = interval(data,2000,2009)
    holdout = interval(data,2010,2025)
    result = {'data_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'center':CENTER,'scale':SCALE,'models':{},'refit':False}
    fits = {}
    for degree in (1,2):
        beta, cond = fit(train[:,0],train[:,1],degree)
        fits[degree] = beta
        result['models'][str(degree)] = {'beta':beta.tolist(),'condition':cond,
           'train':metrics(train[:,1],predict(train[:,0],beta)),
           'selection':metrics(selection[:,1],predict(selection[:,0],beta))}
    selected = choose_degree({d:result['models'][str(d)]['selection']['rmse'] for d in fits})
    result['selected_degree'] = selected
    # Holdout metrics are computed only after the selection rule has chosen a model.
    for d,beta in fits.items():
        result['models'][str(d)]['holdout'] = metrics(holdout[:,1],predict(holdout[:,0],beta))
        result['models'][str(d)]['prediction_2025'] = float(predict([2025],beta)[0])
    beta = fits[selected]
    clean = holdout[~np.isin(holdout[:,0],[2022,2023])]
    recent = interval(data,1979,1999)
    rb, rc = fit(recent[:,0],recent[:,1],selected)
    plus = beta.copy(); plus[-1] += 0.1
    result['posthoc_diagnostics'] = {
      'holdout_excluding_2022_2023':metrics(clean[:,1],predict(clean[:,0],beta)),
      'train_1979_1999_beta':rb.tolist(), 'train_1979_1999_condition':rc,
      'train_1979_1999_holdout':metrics(holdout[:,1],predict(holdout[:,0],rb)),
      'beta_last_plus_0_1_change_2025':float(predict([2025],plus)[0]-predict([2025],beta)[0])}
    result['observed_2025'] = float(holdout[-1,1])
    # Both error and trajectory figures use original train-only fits.
    fig,ax = plt.subplots(figsize=(9,4.8),layout='constrained')
    ax.scatter(data[:,0],data[:,1],s=13,color='black',label='NOAA annual observations')
    for d,b in fits.items(): ax.plot(data[:,0],predict(data[:,0],b),label=f'Degree {d}, fit 1959-1999')
    ax.axvspan(1999.5,2009.5,color='gold',alpha=.13,label='Model selection')
    ax.axvspan(2009.5,2025.5,color='green',alpha=.08,label='Holdout')
    ax.set(xlabel='Year',ylabel='Dry-air CO2 mole fraction (ppm)',title='Retrospective prediction: no refit after model selection')
    ax.legend(fontsize=8)
    save_svg(fig, out/'图/co2_models.svg')
    fig.savefig(out/'图/co2_models.png',dpi=150)
    plt.close(fig)
    fig,ax = plt.subplots(figsize=(9,4.8),layout='constrained')
    for d,b in fits.items():
        ax.plot(holdout[:,0],predict(holdout[:,0],b)-holdout[:,1],marker='o',label=f'Degree {d}')
    ax.axhline(0,color='black',lw=.8)
    ax.axvspan(2021.7,2023.3,color='grey',alpha=.14,label='Station transition note')
    ax.set(xlabel='Held-out year',ylabel='Prediction - observed (ppm)',title='Temporal residual structure is part of the result')
    ax.legend(fontsize=8)
    save_svg(fig, out/'图/co2_errors.svg')
    fig.savefig(out/'图/co2_errors.png',dpi=150)
    plt.close(fig)
    (out/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    return result

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE)
    print(json.dumps(run(parser.parse_args().output),indent=2,ensure_ascii=False))
