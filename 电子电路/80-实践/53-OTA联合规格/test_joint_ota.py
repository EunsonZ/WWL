import json,os,tempfile,unittest
from pathlib import Path
from dataclasses import replace
import numpy as np
from scipy.linalg import expm
import joint_ota as m
from run_joint import run
LAB=Path(__file__).resolve().parent
BASE=Path(os.environ.get('OTA_BASE','电子电路/80-实践/49-全差分OTA偏置与共模/ota_model.py')).resolve()

class JointOTA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=m.load_base(BASE);cls.c=m.Design(cout=100e-12,ccontrol=30e-9);cls.q,cls.info=m.dc(cls.c,cls.base)

    def test_capacitor_energy_incidence(self):
        c=self.c;C=m.caps(c);v=np.arange(10)/9;diagonal=np.array([c.cout,c.cout,5e-12,5e-12,5e-12,5e-12,5e-12,c.ccontrol,c.cgate,c.cgate]);self.assertAlmostEqual(float(v@C@v),float(np.dot(diagonal,v*v)+c.cbridge*((v[0]-v[7])**2+(v[1]-v[7])**2)),places=20)
        self.assertEqual(C[0,7],-c.cbridge);self.assertEqual(C[7,1],-c.cbridge);self.assertTrue(np.linalg.eigvalsh(C).min()>0)

    def test_gate_RC_preserves_published_DC(self):
        q,_=self.base.operating_point(self.base.Config(detector_r=self.c.rdet));np.testing.assert_allclose(q,self.q[:8],atol=1e-10);np.testing.assert_allclose(self.q[8:],[1.5,1.5],atol=1e-12);self.assertTrue(all(x['region']=='saturation' for x in self.info['devices']))
        for d in self.info['devices']:self.assertAlmostEqual(d['gm_over_Id_V_inv'],2/d['overdrive_V'],places=10)

    def test_full_stamp_derivatives_and_real_cuts(self):
        f,j,fu,_,_=m.circuit(self.q,self.c,self.base);eps=1e-6;num=np.column_stack([(m.circuit(self.q+np.eye(10)[k]*eps,self.c,self.base)[0]-m.circuit(self.q-np.eye(10)[k]*eps,self.c,self.base)[0])/(2*eps) for k in range(10)]);np.testing.assert_allclose(j,num,rtol=1e-6,atol=1e-12)
        for k in (0,1):
            args1={'ud':eps} if k==0 else {'uc':eps};args2={'ud':-eps} if k==0 else {'uc':-eps};np.testing.assert_allclose(fu[:,k],(m.circuit(self.q,self.c,self.base,**args1)[0]-m.circuit(self.q,self.c,self.base,**args2)[0])/(2*eps),atol=1e-12)
        for cut in ('dm','cm'):
            fc,jc,*_=m.circuit(self.q,self.c,self.base,cut=cut);np.testing.assert_array_equal(f,fc);self.assertEqual(np.linalg.matrix_rank(j-jc,tol=1e-12),1)

    def test_two_dimensional_DM_and_fifteen_noise_ports(self):
        v=m.linear(self.q,self.c,self.base);self.assertLess(v['modal_cross_max_s_inv'],1e-6);self.assertGreater(abs(v['modal_A'][0][8]),1e3);self.assertEqual(len(v['sources']),15)
        for row in v['spectrum']:
            self.assertLess(max(abs(row['dm_source_psd'][k]) for k in range(4,11)),1e-25)
        c=replace(self.c,mismatch=1.02);q,_=m.dc(c,self.base);w=m.linear(q,c,self.base);self.assertGreater(w['modal_cross_max_s_inv'],1);self.assertGreater(max(row['dm_source_psd'][6] for row in w['spectrum']),1e-24)

    def test_small_step_matches_ten_state_linear_limit(self):
        trace=m.step(self.c,self.base,-1e-5,1e-5,duration=.0001,count=101);lin=m.linear(self.q,self.c,self.base);A=np.array(lin['A_s_inv']);target=np.array(trace['target']);start=np.array(trace['initial']);expected=np.array([target+expm(A*t)@(start-target) for t in trace['time_s']]);# State-scale Radau rtol=2e-8 gives tens of nV numerical tolerance at ~1.6 V.
        np.testing.assert_allclose(trace['states_V'],expected,atol=5e-8,rtol=0)

    def test_fixed_protocol_changes_rejected_before_output(self):
        original=json.loads((LAB/'spec.json').read_text())
        for key,value in [('log_grid_count',40),('kB_J_K',1.380649e-23),('gamma',1),('single_sided',False)]:
            with tempfile.TemporaryDirectory() as folder:
                spec=json.loads(json.dumps(original));spec['noise'][key]=value;p=Path(folder)/'spec.json';p.write_text(json.dumps(spec));out=Path(folder)/'new'
                with self.assertRaises(ValueError):run(p,BASE,out)
                self.assertFalse(out.exists())
        with self.assertRaisesRegex(ValueError,'step_work_budget'):m.step(self.c,self.base,-.01,.01,count=10**9)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileExistsError):run(Path('not_read'),Path('not_read'),Path(folder))

if __name__=='__main__':unittest.main(verbosity=2)
