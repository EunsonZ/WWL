"""Physical/model oracles distinct from solver stopping criteria; no external packages."""
from dataclasses import replace
import math
import unittest
import equilibrium_hall_lab as lab


def composite_simpson_fhalf(eta,panels=40000):
    # Fixed-grid Simpson with a different cutoff, independent of adaptive integrator.
    end=math.sqrt(max(60,eta+60))
    step=end/panels
    def integrand(t):return 4/math.sqrt(math.pi)*t*t/(1+math.exp(t*t-eta))
    total=integrand(0)+integrand(end)
    total+=4*math.fsum(integrand(i*step) for i in range(1,panels,2))
    total+=2*math.fsum(integrand(i*step) for i in range(2,panels,2))
    return total*step/3


class EquilibriumHallChecks(unittest.TestCase):
    def test_normalized_FD_integral_series_and_degenerate_quadrature(self):
        for eta in (-10,-2,-1):
            oracle=math.fsum((-1)**(j+1)*math.exp(j*eta)/j**1.5 for j in range(1,60))
            self.assertLess(abs(lab.fhalf(eta)/oracle-1),1e-8)
        for eta in (0,1,2,5):
            self.assertLess(abs(lab.fhalf(eta)/composite_simpson_fhalf(eta)-1),1e-8)
        self.assertAlmostEqual(lab.fhalf(0),.765147024625408,places=8)

    def test_impurity_weights_and_monotone_neutrality(self):
        mat=lab.Material()
        donor=lab.population(-mat.donor_binding_ev,300,mat)
        acceptor=lab.population(-mat.eg_ev+mat.acceptor_binding_ev,300,mat)
        self.assertAlmostEqual(donor['NDplus_m3']/mat.nd_m3,1/3)
        self.assertAlmostEqual(acceptor['NAminus_m3']/mat.na_m3,1/5)
        for t in (40,300,1200):
            values=[lab.population(-mat.eg_ev+.01+(mat.eg_ev-.02)*i/20,t,mat)['balance_m3'] for i in range(21)]
            # Mid-gap carrier terms may be smaller than floating-point resolution.
            self.assertTrue(all(a>=b for a,b in zip(values,values[1:])))
            root=lab.solve_neutral(t,mat)
            local=[lab.population(root['EF_eV']+lab.KB_EV*t*i/5,t,mat)['balance_m3']
                   for i in range(-10,11)]
            self.assertTrue(all(a>b for a,b in zip(local,local[1:])))
            self.assertLess(root['scaled_charge_residual'],1e-7)
            self.assertLessEqual(root['final_bracket_width_eV'],1e-10)

    def test_compensated_freeze_solution_against_independent_quadratic(self):
        for na in (0,2e21):
            mat=replace(lab.Material(),na_m3=na)
            for t in (40,50):
                exact_quadratic=lab.freeze_mb_density(t,mat)
                actual=lab.solve_neutral(t,mat,mode='mb')['n_m3']
                self.assertLess(abs(actual/exact_quadratic-1),1e-7)
        # In compensated freeze-out, donors transfer charge to acceptors first.
        mat=lab.Material()
        root=lab.solve_neutral(40,mat)
        self.assertLess(root['n_m3']/mat.na_m3,.001)
        self.assertLess(abs(root['NDplus_m3']/mat.na_m3-1),.001)

    def test_intrinsic_solution_and_degenerate_MB_failure(self):
        pure=replace(lab.Material(),nd_m3=0,na_m3=0)
        for t in (300,1200):
            root=lab.solve_neutral(t,pure)
            self.assertLess(abs(root['n_m3']/root['p_m3']-1),1e-7)
        heavy=replace(lab.Material(),nd_m3=1e26,na_m3=0)
        fd=lab.solve_neutral(300,heavy); mb=lab.solve_neutral(300,heavy,mode='mb')
        self.assertGreater(fd['eta_n'],0)
        self.assertGreater((mb['n_m3']-fd['n_m3'])/fd['n_m3'],.25)
        self.assertLess(abs(fd['n_m3']/(fd['Nc_m3']*composite_simpson_fhalf(fd['eta_n']))-1),1e-8)

    def test_Hall_sign_identifiability_and_two_carrier_counterexample(self):
        one=lab.hall_observables(1e21,.135)
        two=lab.hall_observables(2e21,.0675)
        self.assertEqual(one['sigma_S_m'],two['sigma_S_m'])
        self.assertAlmostEqual(one['RH_m3_C'],2*two['RH_m3_C'])
        for n,mu,obs in ((1e21,.135,one),(2e21,.0675,two)):
            n_back=-1/(lab.Q*obs['RH_m3_C'])
            mu_back=obs['sigma_S_m']/(lab.Q*n_back)
            self.assertLess(abs(n_back/n-1),1e-14)
            self.assertLess(abs(mu_back/mu-1),1e-14)
            # Lorentz transverse cancellation: Ey=vx B for electrons, vx=-Jx/(q n).
            ey=obs['RH_m3_C']*100*.1
            self.assertAlmostEqual(ey-(-100/(lab.Q*n))*.1,0)
        cancelled=lab.hall_observables(1e21,.1,1e21,.1)
        self.assertEqual(cancelled['RH_m3_C'],0)
        self.assertGreater(cancelled['sigma_S_m'],0)
        holes=lab.hall_observables(0,0,1e21,.1)
        self.assertGreater(holes['RH_m3_C'],0)

    def test_declared_numeric_domain_and_finite_failure(self):
        for eta in (-701,41,math.nan):
            with self.assertRaises(ValueError):lab.fhalf(eta)
        self.assertGreater(lab.fhalf(-700),0)
        self.assertTrue(math.isfinite(lab.fhalf(40)))
        for t in (39,1201,math.inf):
            with self.assertRaises(ValueError):lab.solve_neutral(t)
        with self.assertRaises(ValueError):lab.Material(nd_m3=-1).validate()
        with self.assertRaises(ValueError):lab.Material(donor_binding_ev=2).validate()
        # A permitted positive dopant number may put the root outside this numerical bracket.
        with self.assertRaisesRegex(ValueError,'not bracketed'):
            lab.solve_neutral(300,replace(lab.Material(),nd_m3=1e28,na_m3=0))
        with self.assertRaises(RuntimeError):lab.adaptive_simpson(math.sin,0,10,tolerance=1e-20,max_depth=0)


if __name__=='__main__':unittest.main()
