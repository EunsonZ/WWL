"""Checks of model invariants, discrete state counting and an independent FD series."""
import cmath
import math
import unittest
import band_dos_lab as lab


class BandDOSChecks(unittest.TestCase):
    def test_hermitian_two_state_residual_with_complex_coupling(self):
        # Construct each eigenvector from the first row, independently of band_pair.
        for k in (-.08, 0, .02, .08):
            reciprocal = 2*math.pi/.5
            d1=lab.ALPHA*(reciprocal/2+k)**2
            d2=lab.ALPHA*(-reciprocal/2+k)**2
            vg=.05*cmath.exp(.7j)
            for eigenvalue in lab.band_pair(k):
                vector=(vg, eigenvalue-d1)
                norm=math.sqrt(sum(abs(v)**2 for v in vector))
                v0,v1=(v/norm for v in vector)
                residual=(d1*v0+vg*v1-eigenvalue*v0,
                          vg.conjugate()*v0+d2*v1-eigenvalue*v1)
                self.assertLess(math.sqrt(sum(abs(v)**2 for v in residual)), 1e-13)

    def test_zero_coupling_returns_free_branches(self):
        for k in (-.1,0,.1):
            reciprocal=2*math.pi/.5
            bare=sorted((lab.ALPHA*(reciprocal/2+k)**2,
                         lab.ALPHA*(-reciprocal/2+k)**2))
            for actual,expected in zip(lab.band_pair(k,vg_ev=0),bare):
                self.assertAlmostEqual(actual, expected, places=13)
        lower,upper=lab.band_pair(0,vg_ev=.02)
        self.assertAlmostEqual(upper-lower,.04,places=14)

    def test_integer_grid_counts_are_not_continuous_DOS(self):
        # Radius 2.5: integer points in line/disk/ball are 5/21/81.
        length=100e-9
        eps=(lab.HBAR**2/(2*.2*lab.M0))*(2*math.pi*2.5/length)**2
        for dim,points in ((1,5),(2,21),(3,81)):
            self.assertEqual(lab.finite_box_count(dim,eps,.2*lab.M0,2,length),2*points)
        self.assertEqual(lab.states_below(1,0,.2*lab.M0,2),0)
        self.assertEqual(lab.finite_box_count(1,0,.2*lab.M0,2,length),2)
        # The continuum estimate loses the finite-box edge state at exactly E_c.

    def test_dos_derivative_and_integrable_1d_edge(self):
        eps=.05*lab.EV
        for dim in (1,2,3):
            step=eps*1e-5
            finite_difference=(lab.states_below(dim,eps+step,.2*lab.M0,2)-
                               lab.states_below(dim,eps-step,.2*lab.M0,2))/(2*step)
            self.assertLess(abs(finite_difference/lab.dos_j(dim,eps,.2*lab.M0,2)-1),1e-9)
        # eps=t^2 eliminates the 1D square-root singularity.
        integral=lab.midpoint_integral(lambda t:lab.dos_j(1,t*t,.2*lab.M0,2)*2*t,
                                      0,math.sqrt(eps),1000)
        self.assertLess(abs(integral/lab.states_below(1,eps,.2*lab.M0,2)-1),1e-12)

    def test_density_integral_against_independent_FD_fugacity_series(self):
        eta=-.1*lab.EV/(lab.KB*300)
        # For eta<0, expand 1/(1+exp(u-eta)); integrate each exponential term.
        series=math.fsum((-1)**(j+1)*math.exp(j*eta)/j**1.5 for j in range(1,25))
        oracle=lab.nc_3d(.2*lab.M0,2,300)*series
        actual=lab.density_3d(-.1)
        self.assertLess(abs(actual/oracle-1),1e-10)
        mb=lab.nc_3d(.2*lab.M0,2,300)*math.exp(eta)
        self.assertGreater(mb, actual)
        self.assertLess((mb-actual)/actual,.01)
        self.assertLess(abs(lab.density_3d(-.1,mode='mb')/mb-1),1e-10)

    def test_units_and_parameter_boundaries(self):
        eps=.05*lab.EV
        # An eV interval has EV times the density per joule.
        width_ev=1e-6
        dosev=lab.dos_j(3,eps,.2*lab.M0,2)*lab.EV
        self.assertAlmostEqual(dosev*width_ev/(lab.dos_j(3,eps,.2*lab.M0,2)*width_ev*lab.EV),1)
        # The bound concerns integer grid indices, not a hard radius <=100.
        length=100e-9
        for radius in (100.25,100.75):
            energy=(lab.HBAR**2/(2*.2*lab.M0))*(2*math.pi*radius/length)**2
            self.assertEqual(lab.finite_box_count(1,energy,.2*lab.M0,2,length),402)
        energy=(lab.HBAR**2/(2*.2*lab.M0))*(2*math.pi*101.25/length)**2
        with self.assertRaisesRegex(ValueError,r"floor\(radius\) <=100"):
            lab.finite_box_count(1,energy,.2*lab.M0,2,length)
        self.assertTrue(math.isinf(lab.dos_j(1,0,.2*lab.M0,2)))
        self.assertEqual(lab.dos_j(3,-eps,.2*lab.M0,2),0)
        for args in ((4,eps,.2*lab.M0,2),(3,eps,-lab.M0,2),(3,eps,lab.M0,0),
                     (3,math.nan,lab.M0,2),(3,eps,lab.M0,1.5)):
            with self.assertRaises(ValueError):lab.states_below(*args)


if __name__ == '__main__':
    unittest.main()
