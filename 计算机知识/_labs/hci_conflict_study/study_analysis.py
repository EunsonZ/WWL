"""Finite HCI teaching records. Arithmetic is executable; no human outcome is simulated as evidence."""
from pathlib import Path
import argparse
import copy
import json
import math
import statistics

ROOT = Path(__file__).resolve().parent
OUTCOMES = {'unaided', 'assisted', 'failed', 'abandoned', 'technical_failure'}
SUCCESS = {'unaided', 'assisted'}


def duration(value):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 3600:
        raise ValueError('completion time must be finite positive seconds, not bool')
    return float(value)


def validate_outcome(row):
    if row['outcome'] not in OUTCOMES:
        raise ValueError('unknown outcome')
    value = duration(row['completion_s'])
    if row['outcome'] not in SUCCESS and value is not None:
        raise ValueError('noncompletion cannot have a completion time')
    return value


def summarize(records):
    if not records or len({r['id'] for r in records}) != len(records):
        raise ValueError('nonempty unique attempt identifiers required')
    for row in records:
        if type(row['started']) is not bool:
            raise ValueError('started must be bool')
        validate_outcome(row)
        if not row['started'] and row['outcome'] != 'technical_failure':
            raise ValueError('only pre-task technical failure is supported without a start')
    started = [r for r in records if r['started']]
    count = len(started)
    unaided = sum(r['outcome'] == 'unaided' for r in started)
    final = sum(r['outcome'] in SUCCESS for r in started)
    known = [duration(r['completion_s']) for r in started if r['outcome'] in SUCCESS and r['completion_s'] is not None]
    return {'registered_attempts': len(records), 'started': count,
        'prestart_technical_failure': len(records)-count,
        'outcomes_started': {k:sum(r['outcome'] == k for r in started) for k in sorted(OUTCOMES)},
        'unaided_fraction': [unaided, count], 'including_help_fraction': [final, count],
        'unaided_rate': unaided/count if count else None, 'including_help_rate': final/count if count else None,
        'completion_time_observed_n': len(known), 'completion_time_missing_n': final-len(known),
        'mean_observed_completion_s': statistics.mean(known) if known else None}


def paired(rows):
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('nonempty unique participant identifiers required')
    differences = {'AB':[], 'BA':[]}
    details, complete = [], []
    by_condition = {v:{'success':0, 'attempts':len(rows), 'times':[]} for v in 'AB'}
    for row in rows:
        if row['order'] not in ('AB','BA'):
            raise ValueError('order must be AB or BA')
        values = {v:validate_outcome(row[v]) for v in 'AB'}
        for v in 'AB':
            by_condition[v]['success'] += row[v]['outcome'] in SUCCESS
            if row[v]['outcome'] in SUCCESS and values[v] is not None:
                by_condition[v]['times'].append(values[v])
        if all(row[v]['outcome'] in SUCCESS and values[v] is not None for v in 'AB'):
            d = values['B']-values['A']
            differences[row['order']].append(d)
            complete.append(d)
            details.append({'id':row['id'], 'order':row['order'], 'B_minus_A_s':d})
    for v in 'AB':
        times = by_condition[v].pop('times')
        by_condition[v]['observed_completion_n'] = len(times)
        by_condition[v]['mean_observed_completion_s'] = statistics.mean(times) if times else None
    means = {o:statistics.mean(ds) if ds else None for o,ds in differences.items()}
    balanced = (means['AB']+means['BA'])/2 if all(v is not None for v in means.values()) else None
    return {'participants':len(rows), 'complete_pairs':len(complete), 'incomplete_pairs':len(rows)-len(complete),
        'by_condition':by_condition, 'paired_differences':details,
        'by_order_n':{o:len(ds) for o,ds in differences.items()}, 'by_order_mean_s':means,
        'naive_complete_pair_mean_s':statistics.mean(complete) if complete else None,
        'equal_order_contrast_s':balanced}


def conditional_interval(rows, critical=2.447):
    # Explicitly fixed df6 example, not an automatic CI for arbitrary HCI records.
    critical = duration(critical)
    if critical is None:
        raise ValueError('positive table critical value required')
    result = paired(rows)
    if result['by_order_n'] != {'AB':4,'BA':4} or result['incomplete_pairs']:
        raise ValueError('this fixed normal-error example requires 4 complete pairs per order')
    groups = [[r['B_minus_A_s'] for r in result['paired_differences'] if r['order']==o] for o in ('AB','BA')]
    pooled = sum(3*statistics.variance(g) for g in groups)/6
    se = math.sqrt(pooled*(1/4+1/4))/2
    effect = result['equal_order_contrast_s']
    return {'estimate_s':effect, 'pooled_residual_variance_s2':pooled, 'standard_error_s':se,
        'df':6, 'critical_rounded':critical, 'conditional_95_interval_s':[effect-critical*se,effect+critical*se],
        'meaning':'normal independent equal-variance difference errors and no differential carryover assumed; not verified human evidence'}


def load(name):
    return json.loads((ROOT/name).read_text())


def generate(output):
    legacy = load('legacy-outcomes.json')['records']
    comparison = load('comparison.json')
    additions = {}
    for name, started, outcome in [('withdraw_after_start',True,'abandoned'),
                                  ('technical_after_start',True,'technical_failure'),
                                  ('technical_before_start',False,'technical_failure')]:
        additions[name] = summarize(legacy+[{'id':'L6','started':started,'outcome':outcome,'completion_s':None}])
    balanced = comparison['balanced']['rows']
    dropout = copy.deepcopy(balanced)
    dropout[-1]['A'] = {'outcome':'abandoned','completion_s':None}
    carryover = copy.deepcopy(balanced)
    for row in carryover:
        if row['order'] == 'AB':
            row['B']['completion_s'] -= 12
    result = {'identity':'SIMULATED TEACHING INPUTS ONLY; no participants or observed human effects',
        'legacy_reused':summarize(legacy), 'one_new_alternative_record':additions,
        'fixed_AB':paired(comparison['fixed_AB']['rows']), 'balanced':paired(balanced),
        'conditional_interval':conditional_interval(balanced), 'dropout_alternative':paired(dropout),
        'differential_carryover_alternative':paired(carryover),
        'completion_selection':paired(comparison['completion_selection']['rows'])}
    output = Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    plot(output,result)
    return result


def plot(output,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1,3,figsize=(13,4),layout='constrained')
    axes[0].bar(['unaided','with help'],[.6,.8],color=['tab:blue','tab:orange'])
    axes[0].set(ylim=(0,1),ylabel='fraction / same five starts',title='Existing simulated aggregate, reused')
    axes[0].text(0,.62,'3/5',ha='center');axes[0].text(1,.82,'4/5',ha='center')
    groups = result['balanced']['paired_differences']
    for i,row in enumerate(groups):
        axes[1].scatter(i,row['B_minus_A_s'],color='tab:blue' if row['order']=='AB' else 'tab:orange')
    axes[1].axhline(-10,color='black',label='equal-order contrast -10 s')
    axes[1].set(xlabel='synthetic participant, one difference each',ylabel='B minus A / seconds',title='Period effects move AB and BA apart')
    axes[1].legend(fontsize=8)
    values=[result['fixed_AB']['naive_complete_pair_mean_s'],result['balanced']['equal_order_contrast_s'],result['differential_carryover_alternative']['equal_order_contrast_s']]
    axes[2].bar(['fixed AB','balanced','+carryover'],values)
    axes[2].set(ylabel='contrast / seconds',title='Different assumptions, different inference')
    axes[2].axhline(0,color='black',linewidth=.7)
    fig.suptitle('Constructed teaching records; no measured human usability or causal certification')
    fig.savefig(Path(output)/'comparison.png',dpi=130);plt.close(fig)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(generate(args.output),ensure_ascii=False,indent=2))
