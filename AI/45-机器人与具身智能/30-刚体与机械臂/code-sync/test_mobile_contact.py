"""New model checks; old IK/rigid/dynamics suites are deliberately not rerun."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('mc',Path(__file__).with_name('mobile_contact.py'))
mc=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mc)


class MobileContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mc.set_sources(os.environ.get('WWL_RIGID_SOURCE'))
        cls.config=json.loads((ROOT/'mobile-contact-inputs.json').read_text())

    def test_wheel_diamond_and_constant_arc(self):
        np.testing.assert_allclose(mc.wheels(.4,1.6,.1,.5),[0.,8.],atol=1e-14)
        for speed,yaw in [(.2,-.4),(0.,1.2),(.3,0.)]:
            rates=mc.wheels(speed,yaw,.1,.5)
            np.testing.assert_allclose(mc.body_control(rates,.1,.5),[speed,yaw],atol=1e-14)
        np.testing.assert_allclose(mc.exact_mobile_step([0.,0.,0.],1.,1.,np.pi/2),[1.,1.,np.pi/2],atol=1e-14)
        np.testing.assert_allclose(mc.exact_mobile_step([0.,0.,np.pi/2],.3,0.,2.),[0.,.6,np.pi/2],atol=1e-14)

    def test_finite_commutator_and_continuous_peaks(self):
        x=mc.examples(self.config)
        np.testing.assert_allclose(x['commutator']['terminal_q'],x['commutator']['analytic_terminal_q'],atol=1e-14)
        peaks=x['continuous_mobile_peaks']
        np.testing.assert_allclose(peaks[0]['phase_wheel_peaks_rad_s'],[1.875*np.pi/2*.25/(.1*2),3.75,1.875*np.pi/2*.25/(.1*2)],atol=1e-14)
        np.testing.assert_allclose(peaks[1]['phase_wheel_peaks_rad_s'],10*np.array(peaks[0]['phase_wheel_peaks_rad_s']),atol=1e-13)
        self.assertGreater(max(r['no_slip_residual_m_s'] for r in x['illegal_configuration_interpolation']),.2)

    def test_impulse_momentum_restitution_and_work(self):
        velocity,ledger=mc.impact([1.2,-3.],2.,.5,.2)
        np.testing.assert_allclose(velocity,[.3,1.5],atol=1e-14)
        self.assertAlmostEqual(ledger['normal_impulse_N_s'],9.)
        self.assertAlmostEqual(ledger['tangent_impulse_N_s'],-1.8)
        self.assertAlmostEqual(ledger['normal_loss_J'],6.75)
        self.assertAlmostEqual(ledger['tangent_loss_J'],1.35)
        self.assertAlmostEqual(ledger['impulse_work_J'],-8.1)
        with self.assertRaises(ValueError):mc.impact([0.,1.],1.,.5,.1)
        with self.assertRaises(ValueError):mc.impact([0.,-1.],1.,1.2,.1)

    def test_inelastic_flight_then_slide_stop(self):
        t_hit=np.sqrt(2/9.81);incoming=np.sqrt(2*9.81)
        post_vx=1.5-.1*incoming
        t_stop=t_hit+post_vx/(.1*9.81)
        final_x=1.5*t_hit+post_vx**2/(2*.1*9.81)
        state,loss,events,segments=mc.advance_contact([0.,1.,1.5,0.],2.,1.,9.81,0.,.1,0.)
        np.testing.assert_allclose(state,[final_x,0.,0.,0.],atol=1e-13)
        self.assertAlmostEqual(events[0]['t_s'],t_hit,places=13)
        self.assertAlmostEqual(events[-1]['t_s'],t_stop,places=13)
        self.assertAlmostEqual(sum(loss),10.935,places=12)
        for segment in segments:
            if segment['mode']=='support':self.assertEqual(segment['normal_force_N'],9.81)
        # Re-entering rest must not fabricate sliding time or a second stop event.
        state,loss,events,segments=mc.advance_contact(state,.1,1.,9.81,0.,.1,2.)
        self.assertEqual(events,[])
        self.assertEqual(segments[0]['sliding_duration_s'],0.)

    def test_elastic_event_sampling_invariance(self):
        state0=np.array([0.,1.,1.5,0.]);g=9.81
        direct,loss,events,_=mc.advance_contact(state0,2.,1.,g,1.,0.,0.)
        state=state0.copy();total=np.zeros(3)
        for i in range(200):
            state,dl,_,_=mc.advance_contact(state,.01,1.,g,1.,0.,i*.01);total+=dl
        np.testing.assert_allclose(state,direct,atol=2e-13,rtol=0)
        self.assertEqual(len(events),2)
        self.assertAlmostEqual(mc.mechanical_energy(state,1.,g),10.935,places=12)
        np.testing.assert_array_equal(total,[0.,0.,0.])

    def test_force_modes_and_arm_pressure_feasibility(self):
        stick=mc.static_point_contact(1.,9.81,.2,.8,4.81)
        slip=mc.static_point_contact(1.,9.81,.2,1.2,4.81)
        lift=mc.static_point_contact(1.,9.81,.2,0.,10.81)
        self.assertEqual(stick['mode'],'stick');self.assertAlmostEqual(stick['normal_force_N'],5.)
        np.testing.assert_allclose(stick['acceleration_m_s2'],[0.,0.],atol=1e-14)
        np.testing.assert_allclose(slip['acceleration_m_s2'],[.2,0.],atol=1e-14)
        self.assertEqual(lift['mode'],'lift');self.assertEqual(lift['normal_force_N'],0.)
        x=mc.examples(self.config)['arm_contact']
        self.assertTrue(x['pressures'][0]['within_20_8_N_m'])
        self.assertFalse(x['pressures'][1]['within_20_8_N_m'])
        np.testing.assert_allclose(x['pressures'][0]['motor_torque_N_m'],np.sqrt(3)*np.array([9.81-5,9.81/4-2.5]),atol=1e-13)
        self.assertAlmostEqual(x['pure_normal_feasible_interval_N'][1],9.81/2+16/np.sqrt(3))

    def test_clamp_energy_failure_and_zeno_rejection(self):
        x=mc.examples(self.config)['projection_counterexample']
        self.assertAlmostEqual(x['exact_energy_J'],9.81)
        self.assertAlmostEqual(x['clamp_y_only_energy_J'],12.0295125)
        self.assertEqual(x['clamp_y_vy_energy_J'],0.)
        # This request crosses the inelastic accumulation time: do not silently settle it.
        with self.assertRaisesRegex(ValueError,'Zeno'):
            mc.advance_contact([0.,1.,0.,0.],3.,1.,9.81,.6,0.,0.)


if __name__=='__main__':unittest.main(verbosity=2)
