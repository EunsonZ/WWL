"""Author self-checks, not independent review or hardware acceptance."""
import csv
import json
import math
from pathlib import Path
import tempfile
import unittest

import thermal_diagnosis as lab

HERE = Path(__file__).resolve().parent


class ThermalDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.config = lab.load_config(HERE / 'input.json')

    def test_old_integral_and_exact_hold(self):
        student, truth = lab.simulate(self.config, self.config['cases'][0])
        self.assertEqual(student[0]['u_cmd_W'], 8.0)
        self.assertEqual(student[0]['z_old_K_s'], 0.0)
        self.assertEqual(student[0]['z_next_K_s'], 2.0)
        self.assertAlmostEqual(truth[0]['x_next_K'], -math.expm1(-.1) * 8, places=14)
        for case in self.config['cases']:
            rows, states = lab.simulate(self.config, case)
            for row, state in zip(rows, states):
                # Re-evaluate original ODE's held-input solution, independently of logging.
                steady = (row['u_applied_W'] + case['d_W']) / self.config['h_W_per_K']
                expected = steady + (state['x_K'] - steady) * math.exp(-.1)
                self.assertAlmostEqual(state['x_next_K'], expected, places=13)
                self.assertAlmostEqual(row['z_next_K_s'], row['z_old_K_s'] + 2-row['y_K'], places=12)

    def test_observation_equivalence_and_distinct_truth(self):
        left, xt = lab.simulate(self.config, self.config['cases'][1])
        right, yt = lab.simulate(self.config, self.config['cases'][2])
        for a, b, x, y in zip(left, right, xt, yt):
            for key in lab.STUDENT_FIELDS:
                if isinstance(a[key], float):
                    self.assertAlmostEqual(a[key], b[key], delta=1e-12)
                else:
                    self.assertEqual(a[key], b[key])
            self.assertAlmostEqual(y['x_K'] - x['x_K'], .2, places=12)
        with tempfile.TemporaryDirectory() as tmp:
            lab.generate(self.config, Path(tmp))
            # No label, parameter or true-state field is published in the student tree.
            student_dir = Path(tmp) / 'student'
            for path in student_dir.iterdir():
                text = path.read_text()
                for forbidden in ('beta', '"d_W"', 'x_K', 'healthy', 'sensor_offset',
                                  'heat_disturbance', 'insufficient_power', 'one_sample_delay'):
                    self.assertNotIn(forbidden, text)
            a = (student_dir / 'case-02.csv').read_bytes()
            b = (student_dir / 'case-03.csv').read_bytes()
            self.assertEqual(a, b)
            with (student_dir / 'case-02.csv').open() as stream:
                header = next(csv.reader(stream))
            self.assertTrue({'beta_K', 'd_W', 'x_K', 'x_next_K'}.isdisjoint(header))

    def test_positive_control_saturation_and_delay(self):
        healthy, _ = lab.simulate(self.config, self.config['cases'][0])
        saturated, _ = lab.simulate(self.config, self.config['cases'][3])
        delayed, _ = lab.simulate(self.config, self.config['cases'][4])
        self.assertLess(abs(healthy[-1]['y_next_K']-2), 1e-9)
        self.assertLess(abs(delayed[-1]['y_next_K']-2), 1e-9)
        self.assertTrue(all(0 <= row['u_cmd_W'] <= 10 for row in delayed))
        self.assertEqual(delayed[0]['u_applied_W'], 0.0)
        self.assertEqual(delayed[1]['u_applied_W'], delayed[0]['u_cmd_W'])
        self.assertEqual(delayed[0]['y_next_K'], 0.0)
        for prev, row in zip(delayed, delayed[1:]):
            self.assertEqual(row['u_applied_W'], min(10, max(0, prev['u_cmd_W'])))
        self.assertTrue(all(row['u_applied_W'] == 1.5 for row in saturated))
        self.assertGreater(2.0, self.config['cases'][3]['u_max_W'])
        self.assertLess(saturated[-1]['y_next_K'], 1.5)
        self.assertGreater(saturated[-1]['z_next_K_s'], 75)
        self.assertTrue(all(row['status'] == 'ok' for row in saturated))

    def test_acceptance_window_and_delay_schur(self):
        for i, case in enumerate(self.config['cases']):
            rows, truth = lab.simulate(self.config, case)
            observed = [row['y_K'] for row in rows if 140 <= row['t_sample_s'] <= 150]
            observed.append(rows[-1]['y_next_K'])
            actual = [row['x_K'] for row in truth[140:]] + [truth[-1]['x_next_K']]
            self.assertEqual(len(observed), 11)
            self.assertEqual(all(abs(y-2) <= .05 for y in observed), i != 3)
            self.assertEqual(all(abs(x-2) <= .05 for x in actual), i not in (1, 3))
        a, b = math.exp(-.1), -math.expm1(-.1)
        A, B, D = -(1+a), a+3*b, b*(.4-3)
        self.assertLess(abs(D), 1)
        B2, D2 = (A-D*B)/(1-D*D), (B-D*A)/(1-D*D)
        self.assertTrue(all(value > 0 for value in (1+B2+D2, 1-B2+D2, 1-D2)))

    def test_independent_reference_error_intervals(self):
        left, a = lab.simulate(self.config, self.config['cases'][1])
        right, b = lab.simulate(self.config, self.config['cases'][2])
        for x, y in zip(a, b):
            self.assertLess(x['x_K']+.02, y['x_K']-.02)
        # The sample at t=0 is enough: [-.22,-.18] and [-.02,.02] do not overlap.
        self.assertEqual(left[0]['y_K'], right[0]['y_K'])

    def test_dimensional_transfer(self):
        transfer = lab.load_config(HERE / 'input-transfer.json')
        for old, new in zip(self.config['cases'], transfer['cases']):
            first, _ = lab.simulate(self.config, old)
            second, _ = lab.simulate(transfer, new)
            for a, b in zip(first, second):
                self.assertEqual(a['y_K'], b['y_K'])
                self.assertEqual(a['z_old_K_s'], b['z_old_K_s'])
                self.assertEqual(2*a['u_cmd_W'], b['u_cmd_W'])
                self.assertEqual(2*a['u_applied_W'], b['u_applied_W'])

    def test_external_output_and_refuse_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'fresh'
            self.assertEqual(lab.external_output(str(out)), out.resolve())
            with self.assertRaises(FileExistsError):
                lab.external_output(str(out))
        with self.assertRaises(ValueError):
            lab.external_output('relative-output')
        with self.assertRaises(ValueError):
            lab.external_output(str(HERE / 'forbidden-output'))

    def test_reject_nonfinite_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'invalid.json'
            broken = dict(self.config, Ts_s=float('nan'))
            path.write_text(json.dumps(broken))
            with self.assertRaises(ValueError):
                lab.load_config(path)


if __name__ == '__main__':
    unittest.main()
