"""Independent rational history, ODE integration, and normal-equation oracles."""
import unittest
import math
from fractions import Fraction
import models as m

class Contracts(unittest.TestCase):
    def test_bins(self):
        self.assertEqual(m.adc(1.65)['code'], 2048)
        self.assertEqual(m.adc(3.3)['code'], 4095)
        self.assertTrue(m.adc(3.3)['upper_endpoint'])
        for v in [0,.2,1,2,3.299]:
            r=m.adc(v); self.assertLessEqual(r['lo_V'],v); self.assertLess(v,r['hi_V'])

    def test_timing(self):
        r=m.schedule()[0]
        self.assertEqual((r['first_sample_ns'], r['last_sample_ns'],r['cpu_finish_ns'],r['slack_ns']),
                         (0,3000000,6300000,1700000))
        self.assertTrue(all(x['status']=='discard' for x in m.schedule(cpu_ns=5000000)))
        self.assertEqual(m.schedule(blocks=1,jitter_ns=0,cpu_ns=4000000)[0]['slack_ns'],0)
        # Independent release schedule: jobs arrive every 4ms, execution begins at max(arrival, prior exit).
        previous=0
        for row in m.schedule(blocks=15,cpu_ns=3500000):
            expected=max((row['block']+1)*4000000+300000,previous)+3500000
            self.assertEqual(row['cpu_finish_ns'], expected); previous=expected

    def test_ring(self):
        r=m.OwnedRing(); a=r.publish(0,[1,2]); self.assertEqual(r.take(a),(1,2))
        with self.assertRaises(OverflowError): r.publish(0,[3])
        r.release(a); b=r.publish(0,[3]); self.assertNotEqual(a,b)
        with self.assertRaises(ValueError): r.release(a)
        r.reset()
        with self.assertRaises(ValueError): r.take(b)

    def test_token_types_are_atomic(self):
        ring=m.OwnedRing(); token=ring.publish(0,[12,34])
        self.assertEqual(token,(0,1,0))
        invalid=[(False,True,0),(0.,1.,0),(False,1.,0),[0,1,0],(0,1)]
        for field in range(3):
            for value in [True,False,0.,1.,float('nan'),float('inf'),complex(0,0),'0',None,-1,10**20]:
                fields=list(token);fields[field]=value;invalid.append(tuple(fields))
        # READY take errors cannot publish CPU ownership.
        for bad in invalid:
            before=(ring.epoch,ring.generation,ring.slots[:])
            with self.assertRaises(ValueError):ring.take(bad)
            self.assertEqual((ring.epoch,ring.generation,ring.slots),before)
        self.assertEqual(ring.take(token),(12,34))
        # CPU release errors cannot free the slot or change payload/generation.
        for bad in invalid:
            before=(ring.epoch,ring.generation,ring.slots[:])
            with self.assertRaises(ValueError):ring.release(bad)
            self.assertEqual((ring.epoch,ring.generation,ring.slots),before)
        ring.release(token)
        new=ring.publish(0,[56])
        before=(ring.epoch,ring.generation,ring.slots[:])
        with self.assertRaises(ValueError):ring.take(token)
        with self.assertRaises(ValueError):ring.release(token)
        self.assertEqual((ring.epoch,ring.generation,ring.slots),before)
        ring.reset(); current=ring.publish(0,[78])
        before=(ring.epoch,ring.generation,ring.slots[:])
        with self.assertRaises(ValueError):ring.take(new)
        with self.assertRaises(ValueError):ring.release(new)
        self.assertEqual((ring.epoch,ring.generation,ring.slots),before)
        self.assertEqual(ring.take(current),(78,));ring.release(current)
        self.assertEqual(ring.slots,[None,None])

    def test_integer_history(self):
        codes=[2048,2052,2056,2060,2040,2041,2048,2047]*5
        q=[c-2048 for c in codes]; expected=[]; state=0
        for i,v in enumerate(q):
            numerator=v+2*(q[i-1] if i else 0)+(q[i-2] if i>1 else 0)
            state=round(Fraction(3*state+v,4))
            expected.append((round(Fraction(numerator,4)),state,i>=2))
        whole=m.CountFilter().process(codes,0,0)
        f=m.CountFilter(); chunks=f.process(codes[:3],0,0)+f.process(codes[3:],3,0)
        self.assertEqual(whole,expected); self.assertEqual(chunks,expected)
        before=(f.next,f.state,f.history[:])
        with self.assertRaises(ValueError): f.process([2048],99,0)
        self.assertEqual(before,(f.next,f.state,f.history))
        with self.assertRaises(ValueError): f.process([2048,4096],40,0)
        self.assertEqual(before,(f.next,f.state,f.history))

    def test_ls_closed_form(self):
        c=[0,1000,2000,3000]; v=[.010,.811,1.612,2.409]
        r=m.fit_calibration(c,v)
        cf=list(map(Fraction,c)); vf=[Fraction(str(x)) for x in v]
        cm=sum(cf)/4; vm=sum(vf)/4
        a=sum((x-cm)*(y-vm) for x,y in zip(cf,vf))/sum((x-cm)**2 for x in cf)
        b=vm-a*cm
        self.assertAlmostEqual(r['coefficients'][0],float(b),places=13)
        self.assertAlmostEqual(r['coefficients'][1],float(a),places=15)
        self.assertAlmostEqual(r['sigma_V']**2,2.4e-6,places=16)
        self.assertAlmostEqual(sum(r['residual_V']),0,places=13)
        with self.assertRaises(ValueError): m.fit_calibration(c,v,[25]*4)
        r=m.fit_calibration([0,1000,0,1000],[.01,.81,.012,.812],[25,25,45,45])
        for actual, expected in zip(r['coefficients'],[.01,.0008,.0001]):
            self.assertAlmostEqual(actual,expected,places=12)

    def test_ode_oracle(self):
        # Original differential equations, RK4 with 500 substeps per hold. No matrix formula.
        def integrate(x,a,d,tp,ta,T):
            h=T/500
            def f(s): return ((s[1]-s[0])/tp,(d-s[1])/ta)
            s=(x,a)
            for _ in range(500):
                k1=f(s); k2=f(tuple(s[j]+h*k1[j]/2 for j in range(2)))
                k3=f(tuple(s[j]+h*k2[j]/2 for j in range(2)))
                k4=f(tuple(s[j]+h*k3[j] for j in range(2)))
                s=tuple(s[j]+h*(k1[j]+2*k2[j]+2*k3[j]+k4[j])/6 for j in range(2))
            return s
        for tp,ta,T in [(.02,.005,.01),(.01,.01,.01),(.02,.02000000001,.004)]:
            matrix=m.held_matrix(tp,ta,T,3)
            for state in [(1,0,0),(0,1,0),(0,0,1),(.3,-.2,.7)]:
                actual=integrate(*state,tp,ta,T)
                for j in range(2):
                    self.assertAlmostEqual(actual[j],sum(matrix[j][k]*state[k] for k in range(3)),places=10)
            self.assertAlmostEqual(sum(matrix[0]),1,places=13)
            self.assertAlmostEqual(sum(matrix[1]),1,places=13)

    def test_stability_counterexample(self):
        import numpy as np
        stable=max(abs(np.linalg.eigvals(m.held_matrix(period=.001,gain=3))))
        unstable=max(abs(np.linalg.eigvals(m.held_matrix(period=.02,gain=3))))
        self.assertLess(stable,1); self.assertGreater(unstable,1)
        # Continuous characteristic roots for instantaneous u=-Kx.
        self.assertTrue(all(x.real<0 for x in np.roots([1,250,40000])))
        self.assertLess(m.control_trace(100,period=.001,gain=3)[-1][0],.1)

    def test_rc_rise(self):
        t=m.pullup()
        v=lambda t: 3.3*(1-math.exp(-t/(2200*100e-12)))
        low=-math.log(.7)*2200*100e-12
        self.assertAlmostEqual(v(low)/3.3,.3,places=14)
        self.assertAlmostEqual(v(low+t)/3.3,.7,places=14)

    def test_bounded_iterables(self):
        from itertools import repeat
        with self.assertRaises(ValueError): m.CountFilter().process(repeat(2048),0,0)
        with self.assertRaises(ValueError): m.OwnedRing().publish(0,repeat(1))
        with self.assertRaises(ValueError): m.fit_calibration(repeat(1),repeat(.1))

    def test_invalid(self):
        for x in [True,complex(1,0),float('nan'),float('inf'),-1,3.4]:
            with self.assertRaises(ValueError): m.adc(x)
        for kwargs in [dict(blocks=257),dict(cpu_ns=0),dict(period_ns=1.5),dict(jitter_ns=-1)]:
            with self.assertRaises(ValueError): m.schedule(**kwargs)
        for kwargs in [dict(tau_p=0),dict(gain=-1),dict(period=1e-8),dict(tau_a=complex(.01,0))]:
            with self.assertRaises(ValueError): m.held_matrix(**kwargs)
        for c,v in [([0,0,0],[1,2,3]),([0,1,2],[1,complex(2,0),3]),([0,1,2],[3,2,1])]:
            with self.assertRaises(ValueError): m.fit_calibration(c,v)

if __name__=='__main__': unittest.main()
