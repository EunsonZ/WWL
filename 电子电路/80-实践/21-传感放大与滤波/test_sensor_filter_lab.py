import unittest
import math
import cmath
import numpy as np
import sensor_filter_lab as m

class ModelTests(unittest.TestCase):
    def test_tia_independent_nodes(self):
        for cf in (0,1e-12,3e-12):
            for f in (0,1e3,1e5,1e7):
                s=2j*math.pi*f; a=1e5/(1+s/(2*math.pi*100)); yf=1e-6+s*cf
                # Unknown vx,vo: input KCL and controlled voltage-source equation.
                vx,vo=np.linalg.solve(np.array([[s*30e-12+yf,-yf],[a,1]],complex),[1,0])
                self.assertLess(abs(vo-m.tia(f,cf=cf)['z_ohm'])/abs(vo),2e-12)
    def test_tia_poles_and_loop(self):
        for cf in (0,1e-12,1e-10):
            r=m.tia_metrics(cf=cf);p=np.roots(r['denominator_s'])
            self.assertTrue(np.all(p.real<0))
            self.assertAlmostEqual(abs(m.tia(r['cross_Hz'],cf=cf)['loop']),1,places=12)
        self.assertGreater(m.tia_metrics()['PM_deg'],m.tia_metrics(cf=0)['PM_deg'])
        r=m.tia_metrics(rf=1,ct=1e-15,cf=0,a0=1e8,ft=1e3)
        c2,c1,c0=r['denominator_s']
        for p in r['poles_rad_s']:
            self.assertLess(p.real,0)
            self.assertLess(abs((c2*p+c1)*p+c0)/(abs(c2*p*p)+abs(c1*p)+abs(c0)),1e-14)
    def test_instrumentation_independent_kcl(self):
        for v1,v2,k2 in ((2.495,2.505,10),(2.5,2.5,10.01),(2.49,2.51,9.99)):
            # first two KCL and ideal virtual short; final plus divider and minus KCL
            o1=v1+5*(v1-v2);o2=v2+5*(v2-v1);vp=(k2*o2+2.5)/(1+k2)
            vo=11*vp-10*o1;r=m.instrumentation(v1,v2,k2=k2)
            self.assertAlmostEqual(r['vo_V'],vo,places=12)
            vc=(v1+v2)/2;vd=v2-v1
            self.assertAlmostEqual(vo,r['Ad']*vd+r['Acm']*vc+11*2.5/(1+k2),places=12)
    def test_comparator_loading_and_delay(self):
        r=m.thresholds(rpull=1e4);vh=r['released_high_V']
        self.assertAlmostEqual((5-vh)/1e4,(vh-2.5)/3e4,places=15)
        base=m.oscillator();delayed=m.oscillator(delay=1e-6)
        self.assertAlmostEqual(base['period_s'],2e-4*math.log(2),places=15)
        self.assertGreater(delayed['period_s'],base['period_s'])
        # Independently reconstruct capacitor at threshold and after fixed delay.
        tau=delayed['tau_s'];t=delayed['t_high_s']-1e-6
        self.assertAlmostEqual(4.9+(delayed['cap_min_V']-4.9)*math.exp(-t/tau),3.3,places=12)
        self.assertAlmostEqual(4.9+(3.3-4.9)*math.exp(-1e-6/tau),delayed['cap_max_V'],places=12)
    def test_prototypes_definition_and_group_delay(self):
        for kind in ('butterworth','chebyshev1','bessel'):
            self.assertAlmostEqual(abs(m.prototype_response(kind,0)['H']),1)
            self.assertAlmostEqual(abs(m.prototype_response(kind,1)['H']),2**-.5,places=12)
            for w in (.1,.5,2):
                e=1e-6;h1=m.prototype_response(kind,w+e)['H'];h0=m.prototype_response(kind,w-e)['H']
                tau=-cmath.phase(h1/h0)/(2*e)
                self.assertAlmostEqual(tau,m.prototype_response(kind,w)['group_delay_normalized'],places=8)
        p=m.prototype('chebyshev1');eps2=10**.1-1
        for wr in (0,.3,2**-.5,1):
            h=m.prototype_response('chebyshev1',wr/p['raw_corner'])['H']
            self.assertAlmostEqual(abs(h)**2,(1+eps2)/(1+eps2*(2*wr*wr-1)**2),places=12)
    def test_filter_independent_nodes_and_stability(self):
        for kind in ('sk','mfb'):
            for ft in (1e3,1e6):
                for f in (0,1e3,1e5):
                    s=2j*math.pi*f;a=1e5/(1+s/(2*math.pi*ft/1e5));g=1e-4;k=3-math.sqrt(2)
                    if kind=='sk':
                        # unknown x,y,vo. C1 from y to ground; C2 x to output.
                        mat=[[2*g+s*1e-8,-g,-s*1e-8],[-g,g+s*1e-8,0],[0,-a,1+a/k]]
                    else:
                        # C2 x to ground, C1 virtual node y to output.
                        mat=[[3*g+s*4.5e-8,-g,-g],[-g,g+s*1e-8,-s*1e-8],[0,a,1]]
                    vo=np.linalg.solve(np.array(mat,complex),[g,0,0])[2]
                    r=m.filter_model(kind,f,c2=1e-8 if kind=='sk' else 4.5e-8,a0=1e5,ft=ft)
                    self.assertLess(abs(vo-r['H'])/max(abs(vo),1e-15),2e-11)
                    stable=bool(np.all(np.roots(r['denominator']).real<0))
                    self.assertEqual(r['model_internal_stable'],stable)
    def test_precision_dc_independent_kcl(self):
        for ibp,ibm,vos in ((5e-9,6e-9,10e-6),(0,0,0),(-5e-9,5e-9,-10e-6)):
            vp=2.52-ibp*2000+vos;a=1e6;rf=190e3;rg=10e3
            vm,vo=np.linalg.solve([[1/rf+1/rg,-1/rf],[a,1]],[2.5/rg-ibm,a*vp])
            r=m.precision_dc(ibplus=ibp,ibminus=ibm,vos=vos)
            self.assertAlmostEqual(vo,r['output_V'],places=12)
        self.assertAlmostEqual(m.precision_dc()['input_error_V'],57e-6,places=15)
    def test_budget_bounds_and_sigma_are_distinct(self):
        r=m.reference_budget([500,375,20,40,2],[50,10,5,4,1])
        self.assertEqual(r['worst_ppm'],937)
        self.assertAlmostEqual(r['worst_V'],.0023425)
        self.assertAlmostEqual(r['uncorrelated_sigma_ppm']**2,50**2+10**2+5**2+4**2+1)
    def test_invalid_inputs_and_tiny_sign(self):
        for bad in (True,1+0j,float('nan'),float('inf'),[1],np.array([1]),np.array(1+0j)):
            for fn in (lambda:m.tia(bad),lambda:m.instrumentation(bad,2.5),lambda:m.oscillator(r=bad),
                       lambda:m.filter_model('sk',bad),lambda:m.reference_budget([bad]),lambda:m.precision_dc(vos=bad)):
                with self.assertRaises(ValueError):fn()
        with self.assertRaises(ValueError):m.bracket(lambda x:1e-300*(x+1),0,1)
        self.assertEqual(m.bracket(lambda x:x,0,1),0)
        with self.assertRaises(ValueError):m.oscillator(delay=1)
        with self.assertRaises(ValueError):m.thresholds(vref=4,vhi=4)

if __name__=='__main__':unittest.main()
