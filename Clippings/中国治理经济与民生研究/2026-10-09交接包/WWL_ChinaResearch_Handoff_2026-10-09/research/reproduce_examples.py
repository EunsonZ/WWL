#!/usr/bin/env python3
"""Recompute observed teacher stock changes and explicitly synthetic teaching examples.
No external dependencies or network access. Does not estimate causal effects.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 28
D = Decimal
ROOT = Path(__file__).resolve().parents[1]

def verify_package() -> int:
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        path = (ROOT / entry['path']).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"Unsafe manifest path: {entry['path']}")
        blob = path.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        if len(blob) != entry['bytes'] or digest != entry['sha256']:
            raise ValueError(f"File verification failed: {entry['path']}")
    return len(manifest['files'])

def compute() -> dict:
    raw = [
        ('各级各类专任教师', '1885.10', '1870.10'),
        ('学前专任教师', '283.19', '261.26'),
        ('小学专任教师', '659.01', '645.82'),
    ]
    observed = []
    for label, before, after in raw:
        a, b = D(before), D(after)
        observed.append({
            'label': label, 'unit': '万人', 'year_2024': before, 'year_2025': after,
            'change': str(b-a), 'pct_change': str(((b/a-D(1))*D(100)).quantize(D('0.0001'))),
            'interpretation': '净存量变化；不能据此识别新招聘流量',
            'sources': ['S02a', 'S02b'],
        })
    other = ((D('1870.10')-D('261.26')-D('645.82'))
             -(D('1885.10')-D('283.19')-D('659.01')))
    probability = D('.8')*D('.75')*D('.9')*D('.95')
    recipients = D(1000)*probability
    assert recipients == D(513)
    assert other == D('20.12')
    debts = []
    for nominal_growth in (D('.01'), D('.04')):
        debt = D(100)*(D(1)+D('.03'))/(D(1)+nominal_growth)
        debts.append({'nominal_growth': str(nominal_growth), 'next_debt_pct_gdp': str(debt.quantize(D('.000001')))})
    return {
        'date': '2026-10-09',
        'observed_statistics': observed,
        'residual_other_teacher_stock_change_wan': str(other),
        'residual_condition': 'Only meaningful if year-to-year classification/perimeter is comparable; not a hiring estimate.',
        'synthetic_examples': {
            'benefit_funnel': {
                'eligible_population': 1000, 'conditional_probabilities': ['0.8','0.75','0.9','0.95'],
                'expected_recipients': str(recipients), 'benefit_per_recipient_yuan': 1000,
                'expected_delivered_yuan': str(recipients*D(1000)),
                'note': 'Synthetic; chain of conditional probabilities, no independence assumption.',
            },
            'debt_dynamics': {
                'initial_debt_pct_gdp': 100, 'effective_nominal_interest_rate': '.03',
                'primary_deficit_ratio': 0, 'stock_flow_adjustment_ratio': 0,
                'cases': debts, 'note': 'Synthetic accounting demonstration, not a China debt forecast.',
            },
        },
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-package', action='store_true')
    args = parser.parse_args()
    result = compute()
    if args.verify_package:
        result['verified_file_count'] = verify_package()
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
