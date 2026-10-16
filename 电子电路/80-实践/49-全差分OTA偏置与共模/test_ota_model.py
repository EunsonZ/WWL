"""Local model checks. Independent simulator evidence is separate, not mocked here."""
import math, unittest
from dataclasses import replace
import numpy as np
from scipy.linalg import expm
import ota_model as m

class OTATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.q,cls.dc=m.operating_point();cls.c=m.Config()
    def test_bias_current_and_headroom(self):
        # Scalar reference diode equation solved by independent bisection.
        lo,hi=.6,1.5
        for _ in range(80):
            b=(lo+hi)/2
            if .5*1e-3*(b-.6)**2*(1+.04*b)>50e-6:hi=b
            else:lo=b
        self.assertAlmostEqual(self.q[3],(lo+hi)/2,delta=1e-12)
        ds={d['name']:d for d in self.dc['devices']}
        self.assertEqual(len(ds),11)
        for d in ds.values():
            self.assertEqual(d['region'],'saturation');self.assertGreater(d['saturation_headroom_V'],.24)
        self.assertAlmostEqual(ds['M1']['Id_A']+ds['M2']['Id_A'],ds['M5']['Id_A'],delta=1e-14)
        self.assertAlmostEqual(ds['M7']['Id_A']+ds['M8']['Id_A'],ds['M9']['Id_A'],delta=1e-14)
        self.assertAlmostEqual(ds['M10']['Id_A']+ds['M7']['Id_A'],0,delta=1e-14)
        self.assertAlmostEqual(ds['M11']['Id_A']+ds['M8']['Id_A'],0,delta=1e-14)
        self.assertNotAlmostEqual(self.q[0],1.65,delta=1e-4) # finite controller/mirror systematic error is retained
    def test_jacobian_from_independent_voltage_perturbations(self):
        for cfg in (self.c,replace(self.c,plus_mismatch=1.02)):
            q,_=m.operating_point(cfg);f,j,fu,_=m.circuit(q,cfg);h=1e-6
            numerical=np.column_stack([(m.circuit(q+np.eye(8)[k]*h,cfg)[0]-m.circuit(q-np.eye(8)[k]*h,cfg)[0])/(2*h) for k in range(8)])
            self.assertLess(np.max(abs(j-numerical)),1e-12)
            for k,key in enumerate(('ud','uc')):
                num=(m.circuit(q,cfg,**{key:h})[0]-m.circuit(q,cfg,**{key:-h})[0])/(2*h)
                self.assertLess(np.max(abs(num-fu[:,k])),1e-12)
    def test_symmetry_coupling_and_hidden_common_instability(self):
        base=m.linearization(self.q,self.c);A=np.array(base['A_s_inv']);T=np.array(base['transform_new_from_node'])
        self.assertLess(np.max(abs(np.linalg.eigvals(A).real)),1e9)
        self.assertTrue(all(z[0]<0 for z in base['roots_s_inv']))
        self.assertEqual(base['modal_cross_max_s_inv'],0)
        self.assertLess(base['A_modal_s_inv'][0][0],0)
        bad=replace(self.c,control_c=20e-12);qb,dc=m.operating_point(bad);bl=m.linearization(qb,bad)
        np.testing.assert_allclose(qb,self.q,rtol=0,atol=1e-14)
        self.assertAlmostEqual(bl['A_modal_s_inv'][0][0],base['A_modal_s_inv'][0][0])
        self.assertGreater(max(z[0] for z in bl['roots_s_inv']),1e5)
        cfg=replace(self.c,plus_mismatch=1.02);q,_=m.operating_point(cfg);coupled=m.linearization(q,cfg)
        self.assertGreater(coupled['modal_cross_max_s_inv'],1e4)
        self.assertGreater(abs(coupled['H_DC_output_d_c_from_input_d_c'][0][1]),1e-4)
        self.assertGreater(abs(coupled['H_DC_output_d_c_from_input_d_c'][1][0]),1e-6)
    def test_unregulated_common_voltage_and_recovery(self):
        fixed=float(self.q[7]);bad=replace(self.c,cmfb=False,fixed_gate=fixed,load_scale=1.1)
        q,d=m.operating_point(bad,self.q)
        self.assertGreater((q[0]+q[1])/2,2.9)
        self.assertTrue(any(x['name']=='M3' and x['region']=='triode' for x in d['devices']))
        q,d=m.operating_point(replace(self.c,load_scale=1.1),self.q)
        self.assertLess(abs((q[0]+q[1])/2-1.65),.005)
        self.assertTrue(all(x['region']=='saturation' for x in d['devices']))
    def test_finite_perturbation_against_linear_local_limit(self):
        A=np.array(m.linearization(self.q,self.c)['A_s_inv']);delta=np.array([1.05e-4,.95e-4,0,0,0,0,0,0])
        errors=[]
        for scale in (1,.5):
            rows=m.transient(self.c,self.q,delta*scale,duration=.0002,count=41)
            error=0
            for row in rows:
                actual=np.array([row[n] for n in m.NAMES])-self.q
                expected=expm(A*row['time_s'])@(delta*scale)
                error=max(error,float(np.max(abs(actual-expected))))
            errors.append(error)
        self.assertLess(errors[0],2e-8)
        self.assertLess(errors[1],errors[0]*.4) # quadratic local nonlinear defect
    def test_configuration_failures(self):
        for value in (True,float('nan'),float('inf'),-1,0):
            with self.assertRaises(ValueError):m.operating_point(replace(self.c,control_c=value))
        with self.assertRaises(ValueError):m.circuit([0]*7)
        for key in ('ud','uc'):
            for value in (True,float('nan'),float('inf'),-float('inf'),1j,'0',10**1000):
                with self.assertRaises(ValueError):m.circuit(self.q,**{key:value})
        for initial in (None,[1.65],[1.65]*9,[[1.65]*8],[True]+[1.65]*7,[float('nan')]+[1.65]*7,[float('inf')]+[1.65]*7,[-.1]+[1.65]*7,[3.4]+[1.65]*7):
            with self.assertRaises(ValueError):m.netlist(analysis='tran',initial=initial)
        self.assertEqual(m.netlist(analysis='tran',initial=self.q).count('v(op)='),1)

if __name__=='__main__':unittest.main()
