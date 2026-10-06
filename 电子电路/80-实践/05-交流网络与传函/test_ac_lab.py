import unittest, math, cmath
import ac_lab as a

class ACContracts(unittest.TestCase):
    def test_loaded_node_and_unloaded_kvl(self):
        for w in (100,1000,10000):
            d=a.rc(w,rs=200,rl=10000)
            self.assertLess(abs(d['I_A']-d['IC_A']-d['IL_A']),1e-15)
            self.assertLess(abs(1200*d['I_A']+d['H']-1),1e-14)
        self.assertEqual(a.rc(1000)['H'],.5-.5j)
        d=a.rc(1000,rs=200,rl=10000)
        self.assertAlmostEqual(d['tau_s'],3/2800)
        self.assertAlmostEqual(d['K'],25/28)
    def test_cycle_power_against_complex_account(self):
        d=a.power_rc();self.assertAlmostEqual(d['P_network_W'],.0005,places=13)
        self.assertAlmostEqual(d['P_resistor_W']+d['P_capacitor_W'],d['P_network_W'],places=13)
        self.assertAlmostEqual(d['P_capacitor_W'],0,places=13)
        V=cmath.exp(.43j);I=(.0005+.0005j)*V
        self.assertLess(abs(V*I.conjugate()-(.0005-.0005j)),1e-15)
        n=4000;T=2*math.pi
        irms=math.sqrt(a.mid_integral(lambda t:(math.sqrt(2)*(.001*math.cos(t)+.001*math.cos(3*t)))**2,0,T,n)/T)
        p=a.mid_integral(lambda t:math.sqrt(2)*math.cos(t)*math.sqrt(2)*(.001*math.cos(t)+.001*math.cos(3*t)),0,T,n)/T
        self.assertAlmostEqual(p/irms,1/math.sqrt(2),places=12)
    def test_resonance_half_power_source_contract(self):
        for r in (25,50,100):
            d=a.resonance(r=r)
            self.assertAlmostEqual(d['lo_rad_s']*d['hi_rad_s'],d['w0_rad_s']**2,places=6)
            for w in (d['lo_rad_s'],d['hi_rad_s']):self.assertAlmostEqual(abs(a.series(w,r=r)['HR'])**2,.5,places=12)
            self.assertAlmostEqual(d['hi_rad_s']-d['lo_rad_s'],r/.01)
        for r in (100,200):
            d=a.resonance(r=r,parallel=True)
            for w in (d['lo_rad_s'],d['hi_rad_s']):self.assertAlmostEqual(abs(a.parallel(w,r=r))**2/r**2,.5,places=12)
        q=2;wp=10000*math.sqrt(1-1/(2*q*q))
        self.assertGreater(abs(a.series(wp)['HC']),abs(a.series(10000)['HC']))
    def test_initial_value_ode_residual(self):
        for v0 in (0,.4,1.4):
            self.assertAlmostEqual(a.rc_step(0,v0),v0)
            for t in (.0002,.001,.004):
                dt=1e-8;v=a.rc_step(t,v0);dv=(a.rc_step(t+dt,v0)-a.rc_step(t-dt,v0))/(2*dt)
                self.assertAlmostEqual(.001*dv+v,1,places=9)
    def test_inverse_transform_by_independent_integral(self):
        p=2+.3j
        targets={'distinct':1/((p+1)*(p+2)),'repeated':(p+3)/(p+1)**2,'conjugate':(p+1)/((p+1)**2+4),'step':1/(p*(p+1)*(p+2)),'delay':cmath.exp(-.5*p)/((p+1)*(p+2))}
        for case,target in targets.items():
            # Truncated positive half-line integral, tail exp(-40) negligible here.
            integral=a.mid_integral(lambda q:a.inverse(q,case)*cmath.exp(-p*q),0,20,80000)
            self.assertLess(abs(integral-target),4e-8,case)
    def test_rhp_zero_initial_reverse_and_frequency_phase(self):
        self.assertEqual(a.inverse(0,'rhp_step'),0)
        dt=1e-6;self.assertAlmostEqual(a.inverse(dt,'rhp_step')/dt,-1,places=5)
        self.assertAlmostEqual(a.inverse(.5,'rhp_step'),1-2*math.exp(-.5))
        for nu in (.1,1,10):
            hm=(1-1j*nu)/(1+1j*nu)**2;hp=1/(1+1j*nu)
            self.assertAlmostEqual(abs(hm),abs(hp),places=13)
        q=1.3;area=a.mid_integral(lambda x:a.inverse(x,'rhp_impulse'),0,q,8000)
        self.assertAlmostEqual(area,a.inverse(q,'rhp_step'),places=8)
    def test_invalid_physical_inputs(self):
        for w in (0,-1,float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):a.rc(w)
        with self.assertRaises(ValueError):a.rc(1000,rs=-1)
        with self.assertRaises(ValueError):a.resonance(c=0)
        with self.assertRaises(ValueError):a.inverse(1,'unknown')
if __name__=='__main__':unittest.main()
