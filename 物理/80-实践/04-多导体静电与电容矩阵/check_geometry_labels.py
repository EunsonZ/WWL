#!/usr/bin/env python3
"""Run default and common-potential-shift cases, parse actual SVG voltage labels."""
import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'


def svg_text(path):
    root = ET.parse(path).getroot()
    return '\n'.join(''.join(t.itertext()) for t in root.findall('{http://www.w3.org/2000/svg}text'))


def check(input_path, report_path):
    base = json.loads(input_path.read_text(encoding='utf-8'))
    source = Path(__file__).with_name('solve_capacitance.py')
    rows = []
    with tempfile.TemporaryDirectory(prefix='wwl-cap-labels-') as temporary:
        scratch = Path(temporary)
        for name, offset in [('default', 0.0), ('common_shift_plus_7_V', 7.0)]:
            data = copy.deepcopy(base)
            data['voltages_V'] = [v + offset for v in base['voltages_V']]
            case_input = scratch / f'{name}.json'
            case_input.write_text(json.dumps(data), encoding='utf-8')
            output = scratch / name
            process = subprocess.run([sys.executable, '-I', '-B', str(source),
                                      '--input', str(case_input), '--output-dir', str(output)],
                                     check=True, capture_output=True, text=True, timeout=60)
            geometry = svg_text(output / 'geometry.svg')
            fields = svg_text(output / 'fields.svg')
            match = re.search(r'Conductor 3: r = c, U3 = (' + NUMBER + r') V\b', geometry)
            assert match, f'{name}: missing numeric reference potential and V unit in geometry'
            observed = float(match[1])
            assert math.isclose(observed, data['voltages_V'][2], rel_tol=5e-6, abs_tol=1e-12), name
            field_match = re.search(r'U1/U2/U3=(' + NUMBER + r')/(' + NUMBER + r')/(' + NUMBER + r') V\b', fields)
            assert field_match, f'{name}: missing voltage triplet and V unit in fields'
            field_values = [float(x) for x in field_match.groups()]
            assert all(math.isclose(a, b, rel_tol=5e-6, abs_tol=1e-12)
                       for a, b in zip(field_values, data['voltages_V'])), name
            assert observed == field_values[2], f'{name}: geometry and field references disagree'
            rows.append({'case': name, 'input_voltages_V': data['voltages_V'],
                         'geometry_label': match[0], 'fields_label': field_match[0],
                         'solver_exit_code': process.returncode, 'labels_match_input': True})
    result = {'solver_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
              'cases': rows, 'checks': 'PASS'}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    check(args.input, args.report)


if __name__ == '__main__':
    main()
