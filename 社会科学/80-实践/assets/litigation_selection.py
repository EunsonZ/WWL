"""Enumerate finite synthetic disputes; never impute absent court records.

Run from the vault root, or pass --input and --output to use separate files.
Rates and covariance are exact rational strings; null means no denominator.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path


def ratio(a, b):
    return str(Fraction(a, b)) if b else None


def summarize(cells, selection, label_rule):
    def selected(c):
        return selection == 'all' or bool(c['resource'] or c['evidence'])
    def label(c):
        return 1 if label_rule == 'unseen_cell_wins' and (c['resource'], c['evidence']) == (0, 0) else c['evidence']
    records = []
    for cell in cells:
        r, h, n = cell['resource'], cell['evidence'], cell['count']
        entered, y = selected(cell), label(cell)
        records.extend({'resource': r, 'evidence': h, 'potential_label': y,
                        'entered': entered, 'observed_label': y if entered else None}
                       for _ in range(n))
    def group(items):
        visible = [x for x in items if x['entered']]
        wins = sum(x['observed_label'] for x in visible)
        return {'disputes': len(items), 'entered': len(visible), 'observed_wins': wins,
                'coverage': ratio(len(visible), len(items)),
                'record_win_rate': ratio(wins, len(visible)),
                'potential_wins': sum(x['potential_label'] for x in items),
                'potential_win_rate': ratio(sum(x['potential_label'] for x in items), len(items))}
    def covariance(items):
        if not items:
            return None
        n = len(items)
        return str(Fraction(sum(x['resource'] * x['evidence'] for x in items), n)
                   - Fraction(sum(x['resource'] for x in items), n)
                   * Fraction(sum(x['evidence'] for x in items), n))
    visible = [x for x in records if x['entered']]
    return {'selection': selection, 'label_rule': label_rule,
            'cells': cells, 'overall': group(records),
            'by_resource': {str(r): group([x for x in records if x['resource'] == r]) for r in (0, 1)},
            'resource_evidence_covariance': {'all': covariance(records), 'selected': covariance(visible)},
            'cell_labels': [dict(c, potential_label=label(c),
                                 observed_label=label(c) if selected(c) else None)
                            for c in cells]}


def compute(data):
    if data.get('synthetic') is not True:
        raise ValueError('input must explicitly identify synthetic data')
    scenarios = data.get('scenarios')
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError('require nonempty scenarios list')
    results = {}
    for scenario in scenarios:
        name = scenario['name']
        if not isinstance(name, str) or not name or name in results:
            raise ValueError('scenario names must be unique nonempty strings')
        selection, rule = scenario['selection'], scenario['label_rule']
        if selection not in ('resource_or_evidence', 'all'):
            raise ValueError('unknown selection rule')
        if rule not in ('evidence', 'unseen_cell_wins'):
            raise ValueError('unknown label rule')
        cells = scenario['cells']
        if len(cells) != 4 or {(c['resource'], c['evidence']) for c in cells} != {(0,0),(0,1),(1,0),(1,1)}:
            raise ValueError('require all four distinct binary cells')
        for c in cells:
            if any(type(c[k]) is not int for k in ('resource', 'evidence', 'count')) or c['count'] < 0:
                raise ValueError('binary fields and nonnegative counts must be integers')
        if sum(c['count'] for c in cells) != 100:
            raise ValueError('each scenario must contain exactly 100 disputes')
        results[name] = summarize(cells, selection, rule)
    return {'synthetic': True, 'units': {'counts': 'disputes', 'rates': 'dimensionless exact fractions'},
            'unobserved_label': None, 'scenarios': results}


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=here / 'litigation-selection-input.json')
    parser.add_argument('--output', type=Path, default=here / 'litigation-selection-output.json')
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('input and output must differ')
    output = compute(json.loads(args.input.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    for name, value in output['scenarios'].items():
        print(name, json.dumps(value['overall'], ensure_ascii=False))


if __name__ == '__main__':
    main()
