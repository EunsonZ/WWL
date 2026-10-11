import math
import unittest
from contact_lab import Contact, Q, KB, HBAR, linear_error, barrier_diagnostic, bar_resistance, recover_length_series

def simpson(f,a,b,n=4000):
    dx=(b-a)/n
    return dx/3*(f(a)+f(b)+4*sum(f(a+(2*i-1)*dx) for i in range(1,n//2+1))+2*sum(f(a+2*i*dx) for i in range(1,n//2)))

class ContactTests(unittest.TestCase):
    def setUp(self): self.c=Contact()
    def close(self,a,b,rtol=1e-8): self.assertLess(abs(a-b),rtol*max(abs(a),abs(b),1e-300))
    def test_independent_maxwell_flux_and_detailed_balance(self):
        c=self.c
        for v in [-.1,0,.1]:
            # Direct one-dimensional normalized Maxwell velocity integration.
            u0=math.sqrt((c.vbi-v)/c.vt)
            integral=simpson(lambda u:u*math.exp(-u*u),u0,u0+7)
            outward=Q*c.donor_m3*math.sqrt(2*KB*c.temperature_K/(math.pi*c.mass))*integral
            self.close(outward,c.js*math.exp(v/c.vt),1e-9)
            self.close(outward-c.js,c.current(v),1e-8) if v else self.assertLess(abs(outward-c.js)/c.js,1e-9)
        self.assertEqual(c.current(0),0)
        self.close(c.current(.1)/abs(c.current(-.1)),math.exp(.1/c.vt))
    def test_poisson_field_potential_and_barrier_reference(self):
        c=self.c
        for v in [-.2,0,.2]:
            d=c.depletion(v);w=d['W_m'];dx=w*1e-4;x=.3*w
            left=c.spatial(x-dx,v);mid=c.spatial(x,v);right=c.spatial(x+dx,v)
            self.close(-(right['phi_V']-left['phi_V'])/(2*dx),mid['E_V_m'])
            self.close((right['E_V_m']-left['E_V_m'])/(2*dx),Q*c.donor_m3/c.eps)
            self.close(c.spatial(0,v)['Ec_eV']-(-c.xi_eV-v),c.barrier_V)
            self.assertEqual(c.spatial(w,v)['E_V_m'],0)
            self.close(simpson(lambda z:Q*c.donor_m3,0,w),d['Qsemi_C_m2'])
    def test_charge_derivative_cv_and_two_point_oracle(self):
        c=self.c;dv=1e-5
        for v in [-.2,0,.2]:
            # Metal charge is -Qsemi, so dQmetal/dV is positive.
            derivative=-(c.depletion(v+dv)['Qsemi_C_m2']-c.depletion(v-dv)['Qsemi_C_m2'])/(2*dv)
            self.close(derivative,c.depletion(v)['C_F_m2'],2e-9)
        v1,v2=-.2,.2;y1=1/c.depletion(v1)['C_F_m2']**2;y2=1/c.depletion(v2)['C_F_m2']**2
        slope=(y2-y1)/(v2-v1);intercept=y1-slope*v1
        self.close(-2/(c.eps*Q*slope),c.donor_m3)
        self.close(-intercept/slope,c.vbi)
    def test_tangent_does_not_certify_ohmic(self):
        c=self.c;dv=1e-7
        self.close((c.current(dv)-c.current(-dv))/(2*dv),c.js/c.vt)
        self.assertLess(abs(linear_error(.0025,c.vt)),.05)
        self.assertLess(abs(linear_error(-.0025,c.vt)),.05)
        self.assertGreater(abs(linear_error(.01,c.vt)),.2)
        self.assertGreater(abs(linear_error(-.01,c.vt)),.17)
    def test_wkb_independent_integral_and_scaling(self):
        c=self.c
        low=barrier_diagnostic(1e22,c.vbi,c.mass,c.eps,300);hi=barrier_diagnostic(1e25,c.vbi,c.mass,c.eps,300)
        w=low['W_m']
        action=2/HBAR*simpson(lambda x:math.sqrt(2*c.mass*(Q*Q*1e22/(2*c.eps)))*(w-x),0,w)
        self.close(action,low['WKB_action_zero_normal_energy'])
        self.close(hi['W_m']/w,1/math.sqrt(1000))
        self.close(hi['E00_J']/low['E00_J'],math.sqrt(1000))
        self.assertLess(low['E00_over_kT'],.05);self.assertGreater(hi['E00_over_kT'],1)
        self.assertGreater(1e25/c.nc,1)  # Cannot extend MB n=ND at this endpoint.
    def test_length_series_independent_difference_and_nonidentifiability(self):
        ls=[1e-6,2e-6,4e-6]
        rs=[bar_resistance(l,1e-12,1e21,.135,1e-12,1e-8)['Rtotal_ohm'] for l in ls]
        fit=recover_length_series(ls,rs)
        slope=(rs[-1]-rs[0])/(ls[-1]-ls[0]);rc=(rs[0]-slope*ls[0])/2
        self.close(fit['slope_ohm_m'],slope);self.close(rc,1e4)
        self.close(rs[0],bar_resistance(ls[0],1e-12,2e21,.0675,1e-12,1e-8)['Rtotal_ohm'])
        # A single R can also be explained by zero contact resistance and lower n*mu.
        effective_n_mu=ls[0]/(Q*rs[0]*1e-12)
        self.close(1/rs[0],Q*effective_n_mu*1e-12/ls[0])
    def test_invalid_boundary_contract(self):
        c=self.c
        for f in [lambda:c.depletion(c.vbi),lambda:c.depletion(math.nan),lambda:c.spatial(-1,0),
                  lambda:Contact(temperature_K=0),lambda:c.current(math.inf),lambda:linear_error(0,0),
                  lambda:barrier_diagnostic(0,1,c.mass,c.eps,300),lambda:recover_length_series([1,1],[1,2])]:
            with self.assertRaises(ValueError): f()

if __name__=='__main__': unittest.main()
