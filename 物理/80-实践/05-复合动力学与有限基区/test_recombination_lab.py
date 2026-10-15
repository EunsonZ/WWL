"""Rate balance, independent analytic limits and discrete boundary-value oracle."""
import math
import unittest
from dataclasses import replace
import recombination_lab as lab

class PhysicsTests(unittest.TestCase):
    def test_trap_four_process_balance_and_generation(self):
        m=lab.Rates()
        for n,p in [(1e18,1e22),(1e24,1.01e24),(1e14,1e14)]:
            s=lab.trap_state(n,p,m)
            self.assertTrue(0<=s['f']<=1)
            self.assertAlmostEqual(s['U_n_m3_s']/s['U_closed_m3_s'],1,places=10)
            self.assertAlmostEqual(s['U_p_m3_s']/s['U_closed_m3_s'],1,places=10)
        self.assertLess(lab.trap_state(1e14,1e14,m)['U_closed_m3_s'],0)
        self.assertEqual(lab.trap_state(m.n0_m3,m.p0_m3,m)['U_closed_m3_s'],0)
        s=lab.trap_state(1e18,1e22,m);f0=.9
        f=s['f']+(f0-s['f'])*math.exp(-1)
        n1,p1=m.aux();a=1/(m.tau_n_s*m.nt_m3);b=1/(m.tau_p_s*m.nt_m3)
        rhs=a*1e18*(1-f)-a*n1*f-b*1e22*f+b*p1*(1-f)
        exact=-(f0-s['f'])*math.exp(-1)/s['relaxation_s']
        self.assertAlmostEqual(rhs/exact,1,places=12)

    def test_low_high_injection_and_differential_lifetime(self):
        m=lab.Rates();small=lab.rate_state(1e12,m);high=lab.rate_state(1e24,m)
        self.assertAlmostEqual(small['tau_secant_s']/m.linear_tau(),1,places=9)
        self.assertEqual(lab.rate_state(0,m)['quasi_fermi_split_ev'],0)
        self.assertGreater(m.linear_tau()/high['tau_secant_s'],100)
        self.assertGreater(high['tau_secant_s']/high['tau_differential_s'],2)
        d=1e22;h=d*1e-5
        derivative=(lab.rate_state(d+h,m)['U_total_m3_s']-lab.rate_state(d-h,m)['U_total_m3_s'])/(2*h)
        self.assertAlmostEqual(derivative*lab.rate_state(d,m)['tau_differential_s'],1,places=8)
        srh=replace(m,b_m3_s=0,cn_m6_s=0,cp_m6_s=0)
        self.assertAlmostEqual(lab.rate_state(1e25,srh)['tau_secant_s']/(srh.tau_n_s+srh.tau_p_s),1,delta=.001)

    def test_nonlinear_decay_against_radiative_closed_solution(self):
        m=replace(lab.Rates(),ni_m3=1e16,p0_m3=1e16,tau_n_s=1e6,tau_p_s=1e6,cn_m6_s=0,cp_m6_s=0)
        d0=1e22;end=1e-7;rows=lab.uniform_decay(d0,1e-10,end,m)
        a=2*m.b_m3_s*m.ni_m3;b=m.b_m3_s
        exact=d0*math.exp(-a*end)/(1+b*d0*(-math.expm1(-a*end))/a)
        self.assertAlmostEqual(rows[-1]['delta_m3']/exact,1,places=11)
        self.assertTrue(all(x['delta_m3']>=y['delta_m3'] for x,y in zip(rows,rows[1:])))

    def test_finite_base_flux_integral_robin_and_limits(self):
        tau=lab.Rates().linear_tau();d=.003;ln=math.sqrt(d*tau);edge=1e18;scale=d*edge/ln
        for beta in (None,0,1,10,1e6):
            s=lab.base_summary(ln,d,tau,edge,beta)
            self.assertLess(s['conservation_relative_error'],1e-14)
            self.assertAlmostEqual(lab.base_point(0,ln,d,tau,edge,beta)['delta_m3']/edge,1)
            if beta is not None:
                last=lab.base_point(ln,ln,d,tau,edge,beta)
                self.assertAlmostEqual(last['Fn_m2_s']/scale,s['S_m_s']*last['delta_m3']/scale,places=12)
        s=lab.base_summary(ln,d,tau,edge)
        self.assertAlmostEqual(s['Fn_left_m2_s']/scale,math.cosh(1)/math.sinh(1))
        self.assertAlmostEqual(s['Fn_right_m2_s']/scale,1/math.sinh(1))
        self.assertAlmostEqual(s['bulk_integral_m2_s']/scale,math.tanh(.5))
        self.assertAlmostEqual(s['tau_storage_s']/tau,1-1/math.cosh(1))
        self.assertAlmostEqual(lab.base_summary(ln,d,tau,edge,0)['tau_storage_s']/tau,1)
        self.assertAlmostEqual(lab.base_summary(20*ln,d,tau,edge)['Fn_left_m2_s']/scale,1,places=12)
        self.assertAlmostEqual(lab.base_summary(.001*ln,d,tau,edge)['tau_storage_s']/(.001**2*tau/2),1,delta=1e-6)

    def test_independent_tridiagonal_discretization(self):
        errors=[]
        for count in (80,160):
            h=1/count;diagonal=2+h*h;a=[0.]*(count-1);b=[0.]*(count-1)
            for i in range(count-1):
                denom=diagonal-(a[i-1] if i else 0)
                a[i]=1/denom;b[i]=(b[i-1] if i else 1)/denom
            u=[0.]*(count+1);u[0]=1
            for i in range(count-2,-1,-1):u[i+1]=b[i]+a[i]*u[i+2]
            exact=[math.sinh(1-i/count)/math.sinh(1) for i in range(count+1)]
            errors.append(max(abs(x-y) for x,y in zip(u,exact)))
            self.assertAlmostEqual((u[0]-u[1])/h-(u[-2]-u[-1])/h,sum(u[1:-1])*h,places=10)
        self.assertTrue(3.99<errors[0]/errors[1]<4.01)
        self.assertLess(errors[1],3e-7)

    def test_two_mode_pde_and_boundary_loss(self):
        tau=lab.Rates().linear_tau();d=.003;ln=math.sqrt(d*tau)
        for x in (0,ln/4,ln/2,ln):
            s=lab.mode_point(x,1e-8,ln,d,tau);scale=1e18/tau
            self.assertAlmostEqual(s['d_dt_m3_s']/scale,(d*s['d2_dx2_m5']-s['delta_m3']/tau)/scale,places=12)
            self.assertGreaterEqual(s['delta_m3'],-1e3)
        self.assertLess(tau/(1+math.pi**2),tau/10)
        t=1e-8;rate=1/tau+d*(math.pi/ln)**2
        stored=2*1e18*ln/math.pi*math.exp(-rate*t)
        f0=lab.mode_point(0,t,ln,d,tau)['Fn_m2_s'];f1=lab.mode_point(ln,t,ln,d,tau)['Fn_m2_s']
        self.assertAlmostEqual((-rate*stored-(f0-f1-stored/tau))/(rate*stored),0,places=12)

    def test_explicit_numeric_domains(self):
        for delta in (-1,float('nan'),1.01e25):
            with self.assertRaises(ValueError):lab.rate_state(delta)
        with self.assertRaises(ValueError):lab.trap_state(-1,1)
        with self.assertRaises(ValueError):lab.base_point(0,1,.003,1e-6,1e18)
        with self.assertRaises(ValueError):lab.base_point(0,1e-6,.003,1e-6,1e18,-1)
        with self.assertRaises(ValueError):lab.uniform_decay(1e18,1e-8,1.5e-8)
        with self.assertRaises(ValueError):lab.mode_point(0,-1,1,.003,1e-6)

if __name__=='__main__':unittest.main()
