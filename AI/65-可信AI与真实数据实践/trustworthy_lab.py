"""Aggregate-bike regression and synthetic fairness; NumPy only, Python >=3.10.
Import has no I/O. --run writes only the explicit output directory. No downloads.
Time keys are recorded local date/hour; no assertion about UTC or station holdout.
"""
from pathlib import Path
from datetime import date, timedelta
import argparse
import csv
import hashlib
import json
import math
import os
import tempfile
import numpy as np

DATA_SHA = 'e03de4ee4ef4dc376ac6e04bf829673c6269e8eba5c60fa121640fa2f829504f'
CONTRACT = 'bike-local-hour-v1'
NUMERIC = ('temp', 'hum', 'windspeed')
CATEGORIES = {'hr': tuple(range(24)), 'workingday': (0, 1),
              'season': (1, 2, 3, 4), 'weathersit': (1, 2, 3, 4)}
LAMBDAS = (0.1, 1.0, 10.0, 100.0)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def canonical(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + '\n').encode('utf-8')


def finite_vector(values, nonnegative=False):
    a = np.asarray(values, dtype=float)
    if a.ndim != 1 or a.size == 0 or not np.isfinite(a).all():
        raise ValueError('expected nonempty finite vector')
    if nonnegative and (a < 0).any():
        raise ValueError('negative value')
    return a


def confusion_metrics(tp, fn, fp, tn):
    c = (tp, fn, fp, tn)
    if any(type(x) is not int or x < 0 for x in c) or sum(c) == 0:
        raise ValueError('counts must be nonnegative integers with positive total')
    ratio = lambda a, b: a / b if b else None
    return {'base_rate': ratio(tp + fn, sum(c)),
            'selection_rate': ratio(tp + fp, sum(c)),
            'tpr': ratio(tp, tp + fn), 'fpr': ratio(fp, fp + tn),
            'ppv': ratio(tp, tp + fp)}


def ppv_from_rates(base, tpr, fpr):
    if any(not math.isfinite(x) or not 0 <= x <= 1 for x in (base, tpr, fpr)):
        raise ValueError('probabilities outside [0,1]')
    d = base * tpr + (1 - base) * fpr
    return base * tpr / d if d else None


def synthetic_cases():
    # Rows are Y=1,Y=0; columns are decision=1,decision=0.
    cases = {'equal_errors': {'A': (160, 40, 80, 720),
                              'B': (480, 120, 40, 360)},
             'equal_selection': {'A': (160, 40, 240, 560),
                                 'B': (360, 240, 40, 360)}}
    return {name: {g: {'counts_tp_fn_fp_tn': list(c), **confusion_metrics(*c)}
                   for g, c in groups.items()} for name, groups in cases.items()}


def split_name(d):
    if not isinstance(d, date) or not date(2011, 1, 1) <= d <= date(2012, 12, 31):
        raise ValueError('date outside fixed data contract')
    if d < date(2012, 1, 1): return 'train'
    if d < date(2012, 7, 1): return 'dev'
    if d < date(2012, 10, 1): return 'cal'
    return 'test'


def load_rows(path, expected_sha=DATA_SHA):
    b = Path(path).read_bytes()
    if sha_bytes(b) != expected_sha:
        raise ValueError('dataset hash mismatch; create a new explicit contract')
    rows = []
    for raw in csv.DictReader(b.decode('utf-8').splitlines()):
        d = date.fromisoformat(raw['dteday'])
        split_name(d)
        row = {'date': d, **{k: int(raw[k]) for k in CATEGORIES},
               **{k: float(raw[k]) for k in NUMERIC}, 'cnt': int(raw['cnt'])}
        if any(row[k] not in allowed for k, allowed in CATEGORIES.items()):
            raise ValueError('unknown category')
        if any(not math.isfinite(row[k]) or not 0 <= row[k] <= 1 for k in NUMERIC):
            raise ValueError('normalized numeric feature outside contract')
        if row['cnt'] < 0 or row['cnt'] != int(raw['casual']) + int(raw['registered']):
            raise ValueError('invalid target or component-sum mismatch')
        rows.append(row)
    keys = [(r['date'], r['hr']) for r in rows]
    if not keys or keys != sorted(keys) or len(set(keys)) != len(keys):
        raise ValueError('empty, unordered, or duplicate recorded date/hour')
    return rows


def audit_rows(rows):
    keys = {(r['date'], r['hr']) for r in rows}
    missing = []
    d = date(2011, 1, 1)
    while d <= date(2012, 12, 31):
        for h in range(24):
            if (d, h) not in keys: missing.append(f'{d}T{h:02d}')
        d += timedelta(days=1)
    parts = {s: [r for r in rows if split_name(r['date']) == s]
             for s in ('train', 'dev', 'cal', 'test')}
    if any(not a for a in parts.values()): raise ValueError('empty split')
    return parts, {'recorded_rows': len(rows), 'calendar_grid_hours': 731 * 24,
                   'absent_grid_hours': len(missing), 'first_missing_keys': missing[:10],
                   'splits': {s: {'n': len(a), 'days': len({r['date'] for r in a}),
                                  'first': str(a[0]['date']), 'last': str(a[-1]['date'])}
                              for s, a in parts.items()}}


def raw_features(rows):
    features = []
    for r in rows:
        if any(r[k] not in v for k, v in CATEGORIES.items()):
            raise ValueError('unknown category')
        # Fixed schema, no future vocabulary fitting. All 24x2 hour/workday cells.
        x = [r[k] for k in NUMERIC]
        for k, values in CATEGORIES.items(): x.extend(float(r[k] == v) for v in values)
        x.extend(float(r['hr'] == h and r['workingday'] == w)
                 for h in range(24) for w in (0, 1))
        features.append(x)
    a = np.asarray(features, dtype=float)
    if a.ndim != 2 or len(a) == 0 or not np.isfinite(a).all():
        raise ValueError('invalid feature matrix')
    return a


def fit_scaler(x):
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or len(x) == 0 or not np.isfinite(x).all():
        raise ValueError('invalid fit matrix')
    mean, std = x.mean(axis=0), x.std(axis=0)
    std[std == 0] = 1.0
    return mean, std


def design(x, mean, scale):
    x = np.asarray(x, dtype=float)
    mean, scale = np.asarray(mean), np.asarray(scale)
    if x.ndim != 2 or mean.shape != (x.shape[1],) or scale.shape != mean.shape:
        raise ValueError('shape mismatch')
    if not np.isfinite(x).all() or not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError('invalid scale/features')
    return np.column_stack([np.ones(len(x)), (x - mean) / scale])


def fit_ridge(z, y, lam):
    z, y = np.asarray(z, float), finite_vector(y)
    if z.ndim != 2 or z.shape[0] != len(y) or not np.isfinite(z).all() or not math.isfinite(lam) or lam <= 0:
        raise ValueError('invalid ridge input; strictly positive lambda required')
    penalty = np.eye(z.shape[1]); penalty[0, 0] = 0
    return np.linalg.solve(z.T @ z + lam * penalty, z.T @ y)


def conformal_radius(residuals, alpha):
    a = finite_vector(residuals, nonnegative=True)
    if not math.isfinite(alpha) or not 0 < alpha < 1: raise ValueError('alpha outside (0,1)')
    k = math.ceil((len(a) + 1) * (1 - alpha))
    return float(np.sort(a)[k - 1]) if k <= len(a) else math.inf


def metrics(y, p, q=None):
    y, p = finite_vector(y, True), finite_vector(p, True)
    if y.shape != p.shape: raise ValueError('prediction shape mismatch')
    e = y - p
    out = {'n': len(y), 'mae': float(np.abs(e).mean()),
           'rmse': float(np.sqrt((e * e).mean())),
           'mean_error_y_minus_pred': float(e.mean()),
           'cost_under3_over1': float((3 * np.maximum(e, 0) + np.maximum(-e, 0)).mean())}
    if q is not None:
        if math.isnan(q) or q < 0: raise ValueError('invalid radius')
        lo, hi = np.maximum(0, p - q), p + q
        out.update(coverage=float(((y >= lo) & (y <= hi)).mean()),
                   mean_width=float((hi - lo).mean()))
    return out


def train_lookup(rows):
    global_mean = float(np.mean([r['cnt'] for r in rows]))
    sums = {}; counts = {}
    for r in rows:
        k = f"{r['hr']}:{r['workingday']}"
        sums[k] = sums.get(k, 0) + r['cnt']; counts[k] = counts.get(k, 0) + 1
    return {'kind': 'hour_workday_mean', 'fallback': global_mean,
            'cells': {k: sums[k] / counts[k] for k in sorted(sums)}}


def predict_lookup(model, rows):
    return np.array([model['cells'].get(f"{r['hr']}:{r['workingday']}", model['fallback']) for r in rows])


def predict_artifact(model, rows):
    if model['contract'] != CONTRACT: raise ValueError('unsupported contract')
    if model['kind'] == 'hour_workday_mean': return predict_lookup(model, rows)
    if model['kind'] != 'ridge': raise ValueError('unsupported model kind')
    return np.maximum(0, design(raw_features(rows), model['mean'], model['scale']) @ np.array(model['weights']))


def hour_band(h):
    return '00-05' if h < 6 else '06-09' if h < 10 else '10-15' if h < 16 else '16-19' if h < 20 else '20-23'


def grouped_metrics(rows, y, p, q):
    result = {}
    for name, fn in [('season_code', lambda r: str(r['season'])),
                     ('hour_band', lambda r: hour_band(r['hr'])),
                     ('weather_code', lambda r: str(r['weathersit']))]:
        groups = {}
        for g in sorted({fn(r) for r in rows}):
            idx = np.array([fn(r) == g for r in rows])
            groups[g] = metrics(y[idx], p[idx], q)
        result[name] = groups
    return result


def histogram_tv(a, b):
    a, b = finite_vector(a), finite_vector(b)
    if (a < 0).any() or (a > 1).any() or (b < 0).any() or (b > 1).any():
        raise ValueError('fixed normalized histogram requires [0,1]')
    edges = np.array([0., .2, .4, .6, .8, 1.])
    ha = np.histogram(a, edges)[0] / len(a); hb = np.histogram(b, edges)[0] / len(b)
    return {'edges': edges.tolist(), 'reference': ha.tolist(), 'current': hb.tolist(),
            'tv': float(np.abs(ha - hb).sum() / 2), 'threshold': 0.10}


def pointer_read(directory):
    path = Path(directory) / 'current.json'
    return path.read_bytes() if path.exists() else None


def pointer_switch(directory, expected, replacement):
    """Single-writer local drill, with third-state rejection; not concurrency-safe CAS.
    A true multi-writer deployment requires locking/transaction/remote version precondition.
    Replacement is already validated bytes for a model pointer.
    """
    d = Path(directory)
    if pointer_read(d) != expected: raise ValueError('third state; refuse overwrite')
    temp = d / 'current.pending'
    temp.write_bytes(replacement)
    os.replace(temp, d / 'current.json')


def validate_release(directory, pointer, probe_rows):
    """Validate bytes, safe fixed version name, deserialization and probe predictions."""
    d = Path(directory)
    try:
        info = json.loads(pointer)
        version = info['version']
        if version not in ('v0', 'v1'):
            raise ValueError('unsupported drill version')
        path = d / (version + '.json')
        if path.is_symlink(): raise ValueError('symlink model refused')
        b = path.read_bytes()
        if sha_bytes(b) != info['model_sha256']:
            raise ValueError('model hash mismatch')
        model = json.loads(b)
        predictions = predict_artifact(model, probe_rows)
        if predictions.shape != (len(probe_rows),) or not np.isfinite(predictions).all() or (predictions < 0).any():
            raise ValueError('invalid probe predictions')
        if 'interval_radius' in model:
            q = model['interval_radius']
            if not math.isfinite(q) or q < 0 or not 0 < model['alpha'] < 1:
                raise ValueError('invalid interval metadata')
        if 'capacity_shift_dev_q75' in model and not math.isfinite(model['capacity_shift_dev_q75']):
            raise ValueError('invalid decision metadata')
        return info
    except (KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        raise ValueError('invalid release artifact') from exc


def publish_checked(directory, expected, replacement, probe_rows):
    validate_release(directory, replacement, probe_rows)
    pointer_switch(directory, expected, replacement)


def release_drill(old_model, new_model):
    with tempfile.TemporaryDirectory(prefix='bike-release-') as temp:
        d = Path(temp)
        pointers = []
        for version, model in [('v0', old_model), ('v1', new_model)]:
            b = canonical(model); (d / f'{version}.json').write_bytes(b)
            pointers.append(canonical({'version': version, 'model_sha256': sha_bytes(b)}))
        probe = [{'hr': 12, 'workingday': 1, 'season': 1, 'weathersit': 1,
                  'temp': .4, 'hum': .5, 'windspeed': .2}]
        publish_checked(d, None, pointers[0], probe)
        previous = pointer_read(d)
        publish_checked(d, previous, pointers[1], probe)
        active = pointer_read(d)
        info = json.loads(active)
        publish_checked(d, active, previous, probe)
        return {'published': 'v1', 'rolled_back': json.loads(pointer_read(d))['version'],
                'v0_sha256': json.loads(previous)['model_sha256'],
                'v1_sha256': info['model_sha256'], 'scope': 'temporary local single-writer drill'}


def run_project(data_path, output_dir):
    d = Path(output_dir)
    if d.exists() or d.is_symlink():
        raise ValueError('a new output directory is required; refuse existing input/output versions')
    if Path(data_path).resolve() in { (d / name).resolve() for name in ('model.json', 'report.json', 'test_predictions.csv') }:
        raise ValueError('output path aliases input')
    rows = load_rows(data_path); parts, audit = audit_rows(rows)
    y = {s: np.array([r['cnt'] for r in a], float) for s, a in parts.items()}
    x = {s: raw_features(a) for s, a in parts.items()}
    mean, scale = fit_scaler(x['train'])
    z = {s: design(a, mean, scale) for s, a in x.items()}
    lookup = {'contract': CONTRACT, **train_lookup(parts['train'])}
    lp = {s: predict_lookup(lookup, a) for s, a in parts.items()}
    constant = float(y['train'].mean())
    candidates = []
    models = {}
    for lam in LAMBDAS:
        w = fit_ridge(z['train'], y['train'], lam)
        model = {'kind': 'ridge', 'contract': CONTRACT, 'lambda': lam,
                 'mean': mean.tolist(), 'scale': scale.tolist(), 'weights': w.tolist()}
        models[f'ridge_{lam}'] = model
        candidates.append({'name': f'ridge_{lam}', 'dev_mae': metrics(y['dev'], predict_artifact(model, parts['dev']))['mae']})
    candidates.append({'name': 'hour_workday_mean', 'dev_mae': metrics(y['dev'], lp['dev'])['mae']})
    models['hour_workday_mean'] = lookup
    chosen = min(candidates, key=lambda c: (c['dev_mae'], c['name']))['name']
    model = models[chosen]
    p = {s: predict_artifact(model, a) for s, a in parts.items()}
    # Freeze the decision shift on development data, before calibration/test.
    shift = float(np.quantile(y['dev'] - p['dev'], .75, method='higher'))
    q = conformal_radius(np.abs(y['cal'] - p['cal']), .10)
    final_model = {**model, 'data_sha256': DATA_SHA, 'alpha': .10,
                   'interval_radius': q, 'capacity_shift_dev_q75': shift}
    result = {'contract': CONTRACT, 'data_sha256': DATA_SHA,
              'audit': audit, 'feature_count': x['train'].shape[1],
              'selection_rule': 'minimum development MAE; tie by name; no refit',
              'candidates': candidates, 'selected': chosen, 'interval_radius': q,
              'capacity_shift_dev_q75': shift,
              'dev': metrics(y['dev'], p['dev']),
              'test': {'constant': metrics(y['test'], np.full(len(y['test']), constant)),
                       'hour_workday_mean': metrics(y['test'], lp['test']),
                       'selected': metrics(y['test'], p['test'], q),
                       'capacity_shift': metrics(y['test'], np.maximum(0, p['test'] + shift))},
              'groups_test': grouped_metrics(parts['test'], y['test'], p['test'], q),
              'drift_temp_train_test': histogram_tv(x['train'][:, 0], x['test'][:, 0]),
              'drift_temp_injected': histogram_tv(x['train'][:, 0], np.minimum(1, x['test'][:, 0] + .20)),
              'delayed_label_mean_train_test': [float(y['train'].mean()), float(y['test'].mean())],
              'release_drill': release_drill(lookup, final_model),
              'environment': {'numpy': np.__version__}, 'synthetic': synthetic_cases()}
    d.mkdir(parents=True, exist_ok=False)
    (d / 'model.json').write_bytes(canonical(final_model))
    (d / 'report.json').write_bytes(canonical(result))
    with (d / 'test_predictions.csv').open('w', newline='') as f:
        writer = csv.writer(f); writer.writerow(['recorded_date', 'hour', 'season_code', 'weather_code', 'y', 'pred', 'lower', 'upper', 'capacity'])
        for r, target, pred in zip(parts['test'], y['test'], p['test']):
            writer.writerow([r['date'], r['hr'], r['season'], r['weathersit'], int(target), format(pred, '.12g'),
                             format(max(0, pred-q), '.12g'), format(pred+q, '.12g'), format(max(0, pred+shift), '.12g')])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--data', type=Path, default=Path(__file__).parent / 'data/hour.csv')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not args.run: parser.error('--run required')
    report = run_project(args.data, args.out)
    print(json.dumps({'selected': report['selected'], 'test': report['test'],
                      'audit': report['audit'], 'q': report['interval_radius']}, ensure_ascii=False, indent=2))
