#!/usr/bin/env python3
"""Teaching synthesis only: no network, devices, packages, or hardware claims."""
import argparse
import csv
import json
import math
from pathlib import Path

STUDENT_FIELDS = (
    'k', 't_sample_s', 'y_K', 'z_old_K_s', 'u_cmd_W', 'ack_time_s',
    'status', 'apply_start_s', 'apply_end_s', 'u_applied_W',
    'z_next_K_s', 'next_sample_time_s', 'y_next_K',
)
TRUTH_FIELDS = ('k', 'x_K', 'x_next_K', 'beta_K', 'd_W', 'u_limited_W')


def finite_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def load_config(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate input key')
            result[key] = value
        return result
    c = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)
    global_keys = {'schema', 'C_J_per_K', 'h_W_per_K', 'Ts_s', 'r_K',
                   'kp_W_per_K', 'ki_W_per_K_s', 'steps', 'cases'}
    if set(c) != global_keys or c['schema'] != 'wwl-thermal-diagnosis-input-v1':
        raise ValueError('wrong input schema or keys')
    for key in global_keys - {'schema', 'cases', 'steps'}:
        if not finite_number(c[key]) or c[key] <= 0:
            raise ValueError('global physical values must be finite and positive')
    if type(c['steps']) is not int or not 1 <= c['steps'] <= 100000:
        raise ValueError('steps must be an integer in [1, 100000]')
    if not isinstance(c['cases'], list) or len(c['cases']) != 5:
        raise ValueError('exactly five cases required')
    case_keys = {'id', 'meaning', 'beta_K', 'd_W', 'x0_K', 'z0_K_s',
                 'u_min_W', 'u_max_W', 'delay_samples', 'previous_limited_command_W'}
    for i, case in enumerate(c['cases'], 1):
        if set(case) != case_keys or case['id'] != f'case-{i:02d}':
            raise ValueError('case keys or neutral identifiers differ')
        if not isinstance(case['meaning'], str):
            raise ValueError('meaning must be text')
        for key in case_keys - {'id', 'meaning', 'delay_samples'}:
            if not finite_number(case[key]):
                raise ValueError('case physical values must be finite')
        if type(case['delay_samples']) is not int or case['delay_samples'] not in (0, 1):
            raise ValueError('delay_samples must be 0 or 1')
        if not case['u_min_W'] <= case['previous_limited_command_W'] <= case['u_max_W']:
            raise ValueError('invalid limits or previous power')
    return c


def simulate(c, case):
    """Return transitions. The current command uses old z; delay uses old power."""
    h, ts = c['h_W_per_K'], c['Ts_s']
    a = math.exp(-h * ts / c['C_J_per_K'])
    b = -math.expm1(-h * ts / c['C_J_per_K']) / h
    x, z = case['x0_K'], case['z0_K_s']
    previous = case['previous_limited_command_W']
    students, truths = [], []
    for k in range(c['steps']):
        y = x + case['beta_K']
        error = c['r_K'] - y
        command = h * c['r_K'] + c['kp_W_per_K'] * error + c['ki_W_per_K_s'] * z
        limited = min(case['u_max_W'], max(case['u_min_W'], command))
        applied = previous if case['delay_samples'] else limited
        z_next = z + ts * error
        x_next = a * x + b * (applied + case['d_W'])
        if not all(math.isfinite(v) for v in (command, z_next, x_next)):
            raise ValueError('nonfinite simulated state')
        students.append(dict(zip(STUDENT_FIELDS, (
            k, k * ts, y, z, command, k * ts, 'ok', k * ts,
            (k + 1) * ts, applied, z_next, (k + 1) * ts,
            x_next + case['beta_K'],
        ))))
        truths.append(dict(zip(TRUTH_FIELDS, (
            k, x, x_next, case['beta_K'], case['d_W'], limited,
        ))))
        x, z, previous = x_next, z_next, limited
    return students, truths


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format(value, '.12g') if isinstance(value, float)
                             else value for key, value in row.items()})


def external_output(path):
    """Require an absolute, new output directory outside source and vault roots."""
    raw = Path(path).expanduser()
    if not raw.is_absolute():
        raise ValueError('--output-dir must be absolute')
    output = raw.resolve()
    source = Path(__file__).resolve().parent
    protected = [source]
    for parent in source.parents:
        if (parent / 'AGENTS.md').exists():
            protected.append(parent)
            break
    if any(output == root or output.is_relative_to(root) for root in protected):
        raise ValueError('output must be outside source and repository')
    for parent in (output, *output.parents):
        if ((parent / '.obsidian').exists()
                or ((parent / 'AGENTS.md').exists() and (parent / '控制论').exists())):
            raise ValueError('output must be outside a vault')
    # Exclusive mkdir rejects even an existing empty directory; no file is overwritten.
    output.mkdir(exist_ok=False)
    return output


def generate(c, output):
    student_dir, teacher_dir = output / 'student', output / 'teacher'
    student_dir.mkdir()
    teacher_dir.mkdir()
    public = {key: c[key] for key in (
        'C_J_per_K', 'h_W_per_K', 'Ts_s', 'r_K', 'kp_W_per_K', 'ki_W_per_K_s', 'steps')}
    public.update({'data_kind': 'teaching_synthetic',
                   'cases': [case['id'] for case in c['cases']],
                   'status_semantics': 'command received only',
                   'comparison_tolerance_K': 1e-9})
    (student_dir / 'experiment.json').write_text(
        json.dumps(public, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (teacher_dir / 'input.json').write_text(
        json.dumps(c, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = {}
    references = []
    for case in c['cases']:
        student, truth = simulate(c, case)
        write_csv(student_dir / (case['id'] + '.csv'), student, STUDENT_FIELDS)
        write_csv(teacher_dir / (case['id'] + '.csv'), truth, TRUTH_FIELDS)
        if case['id'] in ('case-02', 'case-03'):
            reference_error = .01 if case['id'] == 'case-02' else -.01
            references.append({'case': case['id'], 't_sample_s': c['steps'] * c['Ts_s'],
                               'reference_K': truth[-1]['x_next_K'] + reference_error,
                               'absolute_error_bound_K': .02})
        summary[case['id']] = {
            'meaning': case['meaning'], 'last_y_K': student[-1]['y_next_K'],
            'last_x_K': truth[-1]['x_next_K'], 'last_z_K_s': student[-1]['z_next_K_s'],
            'max_abs_command_W': max(abs(row['u_cmd_W']) for row in student),
            'max_applied_W': max(row['u_applied_W'] for row in student),
        }
    write_csv(teacher_dir / 'reference-release.csv', references,
              ('case', 't_sample_s', 'reference_K', 'absolute_error_bound_K'))
    (teacher_dir / 'summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (student_dir / 'README.md').write_text(
        '# 温控记录调查\n\n全部为教学合成数据。case-01.csv 至 case-05.csv 为中性编号，'
        '编号不提供原因标签。experiment.json 给公开参数。\n\n'
        '每行在 t_sample_s 读取 y_K，使用 z_old_K_s 计算 u_cmd_W；'
        'status=ok 仅表示在 ack_time_s 收到命令。u_applied_W 是本模型'
        '在 [apply_start_s, apply_end_s) 施加的功率；z_next_K_s 供下一拍使用，'
        'y_next_K 是 next_sample_time_s 的新读数。\n\n'
        '调查任务、单位与判断标准见课程项目的学生入口 README.md。\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).with_name('input.json'))
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    try:
        config = load_config(args.input)
        output = external_output(args.output_dir)
        generate(config, output)
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as error:
        parser.exit(2, f'error: {error}\n')
    print(f'generated teaching synthetic records: {output}')


if __name__ == '__main__':
    main()
