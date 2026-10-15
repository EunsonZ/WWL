---
stage: 1
aliases: []
sources: []
prerequisites:
  - "[[电子电路/80-实践/01-RC跨层/README]]"
---
# RC 标杆与生成入口回归测试源码

真源是上一级的 `test_rc_revision.py`。数值标杆与生成器进程边界分别检查；使用已有依赖并将 TMPDIR 指向新的库外可写目录，避免在主库产生临时文件。测试不证明实体测量或学习效果。

<!-- code-sync: ../test_rc_revision.py -->
```python
"""Independent RC benchmarks and process contracts for existing generators.

Run with an interpreter that already has numpy/matplotlib/CairoSVG, and -B.
All subprocess output and caches use a fresh temporary directory. Set TMPDIR
outside the vault. Source snapshots cover the electronics subtree, including
its delivered assets. Numerical oracles below do not call plot generators.
"""
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from rc_lab import RC

EE = Path(__file__).resolve().parents[2]
GENERATORS = (
    EE / "80-实践/01-RC跨层/plot_rc.py",
    EE / "20-器件与模拟/device_examples.py",
    EE / "80-实践/02-弱信号前端预算/plot_frontend_budget.py",
    EE / "80-实践/02-弱信号前端预算/frontend_budget.py",
    EE / "80-实践/03-FSM到RTL/assets/build_visuals.py",
)


def snapshot():
    return {str(p.relative_to(EE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in EE.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


class BenchmarkTests(unittest.TestCase):
    def test_nonzero_initial_state_and_samples(self):
        model = RC()
        self.assertAlmostEqual(model.tau, .001, places=15)
        t = [0., .00025, .001, .005]
        expected = [1-.6*math.exp(-x/.001) for x in t]
        for actual, reference in zip(model.step(t, v0=.4), expected):
            self.assertAlmostEqual(actual, reference, places=14)
        samples = model.simulate([1]*4, .00025, v0=.4)
        self.assertEqual(len(samples), 5)
        self.assertEqual(samples[0], .4)
        self.assertAlmostEqual(samples[-1], 1-.6/math.e, places=14)

    def test_frequency_units_and_corner(self):
        corner_hz = 1000/(2*math.pi)
        self.assertAlmostEqual(corner_hz, 159.15494309189535, places=10)
        h = RC().frequency([corner_hz])[0]
        self.assertAlmostEqual(h.real, .5, places=14)
        self.assertAlmostEqual(h.imag, -.5, places=14)
        self.assertAlmostEqual(abs(h), 1/math.sqrt(2), places=14)
        self.assertAlmostEqual(math.degrees(math.atan2(h.imag, h.real)), -45, places=13)
        # 1000 Hz is a different argument from 1000 rad/s.
        self.assertGreater(abs(h-RC().frequency([1000])[0]), .4)

    def test_zoh_delay_and_arbitrary_held_input(self):
        model = RC()
        a, b = model.coefficients(.00025)
        self.assertAlmostEqual(a, .7788007831, delta=5e-11)
        self.assertAlmostEqual(b, .2211992169, delta=5e-11)
        actual = model.simulate([0., 1., -.2], .00025, v0=.4)
        previous = .4
        self.assertEqual(actual[0], previous)
        for index, u in enumerate([0., 1., -.2]):
            # Solve each constant-input interval from its boundary value.
            previous = u+(previous-u)*math.exp(-.25)
            self.assertAlmostEqual(actual[index+1], previous, places=14)
        impulse = model.simulate([1., 0.], .00025)
        self.assertEqual(impulse[0], 0.)
        self.assertAlmostEqual(impulse[1], b, places=14)
        self.assertAlmostEqual(impulse[2], a*b, places=14)

    def test_loaded_coefficients(self):
        model = RC(rs=200, rl=10000)
        tau, gain = 3/2800, 25/28
        self.assertAlmostEqual(model.tau, tau, places=15)
        self.assertAlmostEqual(model.gain, gain, places=15)
        a, b = model.coefficients(.00025)
        self.assertAlmostEqual(a, math.exp(-.00025/tau), places=14)
        self.assertAlmostEqual(b, gain*(1-a), places=14)
        self.assertGreater(abs(b-(1-a)), .02)
        output = model.simulate([1]*4, .00025, v0=.4)
        self.assertAlmostEqual(output[-1], gain+(.4-gain)*math.exp(-.001/tau), places=14)

    def test_euler_boundary_is_not_convergence(self):
        output = RC().simulate([1]*6, .002, method="euler")
        self.assertEqual(list(output), [0., 2., 0., 2., 0., 2., 0.])
        self.assertEqual([abs(x-1) for x in output], [1.]*7)

    def test_same_tau_voltage_and_distinct_current(self):
        first, second = RC(r=1000, c=1e-6), RC(r=2000, c=.5e-6)
        self.assertEqual(first.tau, second.tau)
        for v0 in [0., .4]:
            self.assertEqual(list(first.step([0., .001, .004], v0=v0)),
                             list(second.step([0., .001, .004], v0=v0)))
        self.assertEqual(list(first.frequency([1., 159.154943, 10000.])),
                         list(second.frequency([1., 159.154943, 10000.])))
        self.assertEqual((1/first.r, 1/second.r), (.001, .0005))
        impedances = [complex(m.r, -1/(1000*m.c)) for m in (first, second)]
        self.assertEqual(impedances, [1000-1000j, 2000-2000j])


class GeneratorProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wwl-ee-generator-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.before = snapshot()
        self.env = dict(os.environ, MPLCONFIGDIR=str(self.work/"mplconfig"),
                        XDG_CACHE_HOME=str(self.work/"cache"), PYTHONDONTWRITEBYTECODE="1")

    def tearDown(self):
        self.assertEqual(snapshot(), self.before, "source or delivered asset changed")

    def run_python(self, args):
        return subprocess.run([sys.executable, "-B", *args], cwd=self.work,
                              env=self.env, capture_output=True, text=True, timeout=120)

    def test_imports_ignore_stranger_argv_and_create_no_files(self):
        script = r"""
import importlib.util, sys
from pathlib import Path
p=Path(sys.argv[1]);sys.path.insert(0,str(p.parent))
sys.argv=['unrelated-program','--stranger-flag','not-a-generator-output']
spec=importlib.util.spec_from_file_location('candidate_generator',p)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m
spec.loader.exec_module(m)
if p.name in ('plot_rc.py','plot_frontend_budget.py','device_examples.py'):
    assert 'matplotlib' not in sys.modules, 'import initialized matplotlib'
    assert callable(m.generate) and callable(m.main)
"""
        for path in GENERATORS:
            with self.subTest(generator=path.name):
                result = self.run_python(["-c", script, str(path)])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(list(self.work.iterdir()), [])

    def test_import_preserves_callers_plot_configuration(self):
        script = r"""
import importlib.util, sys
from pathlib import Path
import matplotlib
matplotlib.rcParams['font.size']=37
matplotlib.rcParams['svg.fonttype']='path'
old=dict(matplotlib.rcParams)  # Resolve lazy backend BEFORE taking baseline.
p=Path(sys.argv[1]);sys.path.insert(0,str(p.parent))
spec=importlib.util.spec_from_file_location('candidate_generator',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert dict(matplotlib.rcParams)==dict(old)
"""
        for path in GENERATORS[:3]:
            with self.subTest(generator=path.name):
                result = self.run_python(["-c", script, str(path)])
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_output_exits_two_without_files(self):
        for path in GENERATORS:
            with self.subTest(generator=path.name):
                result = self.run_python([str(path)])
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("--output", result.stderr)
                self.assertEqual(list(self.work.iterdir()), [])

    def test_nested_output_has_valid_models_and_figures(self):
        for path in GENERATORS:
            with self.subTest(generator=path.name):
                output = self.work/path.stem/"nested"/"assets"
                result = self.run_python([str(path), "--output", str(output)])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(output.is_dir())
                if path.name == 'plot_rc.py':
                    data = json.loads((output/'results.json').read_text())
                    self.assertAlmostEqual(data['nominal']['tau_s'], .001, places=14)
                    self.assertAlmostEqual(data['nominal']['fc_Hz'], 1000/(2*math.pi), places=11)
                    self.assertAlmostEqual(data['loaded']['gain'], 25/28, places=14)
                    with (output/'rc-discrete.csv').open() as f:
                        rows=list(csv.DictReader(f))
                    self.assertEqual(len(rows), 46)
                    self.assertEqual(float(rows[0]['exact_V']), 0.)
                    self.assertAlmostEqual(float(rows[1]['exact_V']), 1-math.exp(-.25), places=14)
                elif path.name == 'device_examples.py':
                    data=json.loads((output/'results.json').read_text())
                    self.assertLess(abs(data['diode']['kcl_A']), 1e-16)
                    self.assertLess(abs(data['mos']['kcl_A']), 1e-16)
                    self.assertAlmostEqual(data['mos']['current'], (.001+.00002*5)/(1+.00002*2000), places=14)
                elif path.name == 'plot_frontend_budget.py':
                    with (output/'noise-integral.csv').open() as f:
                        rows=list(csv.DictReader(f))
                    self.assertEqual(len(rows), 700)
                    self.assertEqual(float(rows[0]['cumulative_RTI_RMS_V']), 0.)
                    self.assertTrue(all(float(row['stage1_output_PSD_V2_per_Hz'])>0 for row in rows))
                    cumulative=[float(row['cumulative_RTI_RMS_V']) for row in rows]
                    self.assertTrue(all(a<=b for a,b in zip(cumulative,cumulative[1:])))
                elif path.name == 'frontend_budget.py':
                    data=json.loads((output/'budget-results.json').read_text())
                    self.assertTrue(data['good']['result']['teaching_budget_pass'])
                    self.assertFalse(data['bad']['result']['teaching_budget_pass'])
                svgs=list(output.glob('*.svg'))
                if path.name != 'frontend_budget.py':
                    self.assertGreater(len(svgs), 0)
                for svg in svgs:
                    self.assertEqual(ET.parse(svg).getroot().tag, '{http://www.w3.org/2000/svg}svg')
                for png in output.glob('*.png'):
                    self.assertEqual(png.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')


if __name__ == '__main__':
    unittest.main()
```
