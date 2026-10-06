import os
import csv
from fractions import Fraction
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import generate

class GenerateContracts(unittest.TestCase):
    def test_import_and_required_output(self):
        script=Path(generate.__file__)
        with tempfile.TemporaryDirectory() as d:
            env=dict(os.environ,MPLCONFIGDIR=d+'/mpl',XDG_CACHE_HOME=d+'/xdg')
            code="import sys; sys.path.insert(0,"+repr(str(script.parent))+"); import generate, models; assert 'matplotlib' not in sys.modules; assert 'numpy' not in sys.modules"
            p=subprocess.run([sys.executable,'-B','-c',code],cwd=d,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr); self.assertEqual(list(Path(d).iterdir()),[])
            p=subprocess.run([sys.executable,'-B',str(script)],cwd=d,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,2); self.assertEqual(list(Path(d).iterdir()),[])

    def test_global_state_success_and_failure(self):
        saved={k:os.environ.get(k) for k in ('MPLCONFIGDIR','XDG_CACHE_HOME')}
        with tempfile.TemporaryDirectory() as d:
            try:
                os.environ['MPLCONFIGDIR']=d+'/caller-mpl'; os.environ['XDG_CACHE_HOME']=d+'/caller-xdg'
                import matplotlib
                before=matplotlib.rcParams.copy() # raw backend sentinel: avoid observing/resolving it
                expected={k:os.environ.get(k) for k in saved}
                generate.generate(Path(d)/'success')
                self.assertEqual(matplotlib.rcParams.copy(),before)
                self.assertEqual({k:os.environ.get(k) for k in saved},expected)
                self.assertEqual(len(list((Path(d)/'success/assets').glob('*.svg'))),9)
                self.assertEqual(len(list((Path(d)/'success/assets').glob('*.png'))),18)
                with (Path(d)/'success/pipeline.csv').open() as f:
                    rows=list(csv.DictReader(f))
                self.assertEqual(len(rows),32)
                history=[]; state=0
                for n,row in enumerate(rows):
                    self.assertEqual(int(row['index']),n)
                    self.assertEqual(int(row['capture_ns']),n*1000000)
                    self.assertEqual(int(row['processing_finish_ns']),(n//4+1)*4000000+2300000)
                    code=int(row['code']); q=code-2048
                    state=round(Fraction(3*state+q,4))
                    fir=round(Fraction(q+2*(history[-1] if history else 0)+(history[-2] if len(history)>1 else 0),4))
                    self.assertEqual(int(row['IIR_count']),state)
                    self.assertEqual(int(row['FIR_count']),fir)
                    self.assertEqual(row['FIR_valid'],str(n>=2))
                    self.assertAlmostEqual(float(row['calibrated_V']),.0108+.0007998*code,places=12)
                    self.assertAlmostEqual(float(row['output_deviation_V']),.0007998*state,places=12)
                    self.assertEqual(row['status'],'CPU_result_only')
                    history.append(q)
                with patch.object(generate,'_native_figures',side_effect=RuntimeError('injected')):
                    with self.assertRaises(RuntimeError): generate.generate(Path(d)/'failure')
                self.assertEqual(matplotlib.rcParams.copy(),before)
                self.assertEqual({k:os.environ.get(k) for k in saved},expected)
            finally:
                for k,v in saved.items():
                    if v is None: os.environ.pop(k,None)
                    else: os.environ[k]=v

if __name__=='__main__': unittest.main()
