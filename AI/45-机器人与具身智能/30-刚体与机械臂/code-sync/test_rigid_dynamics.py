"""Checks of new rigid/dynamics assertions; does not rerun old IK/FD suite."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('rd',Path(__file__).with_name('rigid_dynamics.py'))
rd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rd)


def physical_mass(q,p):
    # Independent translational COM velocities plus scalar link angular energy.
    l1 = p['lengths_m'][0]; r1,r2 = p['com_m']; m1,m2 = p['masses_kg']; i1,i2 = p['inertia_kg_m2']
    tangent1 = np.array([-np.sin(q[0]),np.cos(q[0])])
    tangent2 = np.array([-np.sin(q.sum()),np.cos(q.sum())])
    def kinetic(v):
        v1 = r1*v[0]*tangent1
        v2 = l1*v[0]*tangent1+r2*(v[0]+v[1])*tangent2
        return .5*(m1*(v1@v1)+m2*(v2@v2)+i1*v[0]**2+i2*(v[0]+v[1])**2)
    k1,k2,ks = kinetic([1.,0.]),kinetic([0.,1.]),kinetic([1.,1.])
    return np.array([[2*k1,ks-k1-k2],[ks-k1-k2,2*k2]])


class DynamicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rd.set_sources(os.environ.get('WWL_ARM_SOURCE'),os.environ.get('WWL_ROBOTICS_BASE'))
        cls.config = json.loads((ROOT/'dynamics-inputs.json').read_text())
        cls.p = rd.parameters(cls.config['nominal'])

    def test_rotation_order_embed_inverse(self):
        for angle in [0.,1e-10,.3,-2.,np.pi]:
            r = rd.rotation_vector([0.,0.,angle])
            np.testing.assert_allclose(r[:2,:2],rd.arm().base().rotation(angle),atol=1e-14)
            np.testing.assert_allclose(r.T@r,np.eye(3),atol=1e-14)
        result = rd.examples(self.config)['rigid']
        np.testing.assert_allclose(result['Rz_Rx_on_y'],[0.,0.,1.],atol=1e-14)
        np.testing.assert_allclose(result['Rx_Rz_on_y'],[-1.,0.,0.],atol=1e-14)
        t = np.array(result['T_WB'])
        np.testing.assert_allclose(t@rd.inverse_transform(t),np.eye(4),atol=1e-14)
        self.assertEqual(result['ZYX_rate_rank'],2)
        self.assertLess(result['ZYX_equal_roll_yaw_rotation_difference'],1e-14)
        with self.assertRaises(ValueError):rd.transform(np.diag([1.,1.,-1.]),[0.,0.,0.])

    def test_twist_origin_and_wrench_power(self):
        result = rd.examples(self.config)['rigid']
        np.testing.assert_allclose(result['V_space'],[0.,1.,.5,-3.,-.5,1.2],atol=1e-14)
        np.testing.assert_allclose(result['body_origin_velocity_W_m_s'],[-1.,0.,.2],atol=1e-14)
        np.testing.assert_allclose(result['F_space'],[-7.,-4.,5.,-1.,3.,2.],atol=1e-14)
        self.assertAlmostEqual(result['body_power_W'],2.4)
        self.assertAlmostEqual(result['space_power_W'],2.4)
        self.assertAlmostEqual(result['wrong_tip_velocity_power_W'],-.1)
        t,tdot = np.array(result['T_WB']),np.array(result['T_dot'])
        np.testing.assert_allclose(tdot@rd.inverse_transform(t),rd.twist_matrix(result['V_space']),atol=1e-14)
        # Velocity of any attached point: pdot + omega cross (R r_B).
        rb = np.array([.2,-.3,.7]); rw = t[:3,:3]@rb+t[:3,3]
        direct = tdot@np.r_[rb,1.]
        vs = np.array(result['V_space'])
        np.testing.assert_allclose(direct[:3],np.cross(vs[:3],rw)+vs[3:],atol=1e-14)

    def test_lagrange_against_com_energy_and_christoffel(self):
        worst = 0.; step = 1e-5
        for q,v in [([0.,0.],[.3,-.2]),([.4,-.8],[1.,-2.]),([-.7,1.2],[-.4,.7]),([1.,np.pi],[.2,.8])]:
            q,v = np.array(q),np.array(v)
            m,c,g = rd.mechanics(q,v,self.p)
            np.testing.assert_allclose(m,physical_mass(q,self.p),atol=1e-14)
            self.assertGreater(np.linalg.eigvalsh(m).min(),0.)
            dm = np.array([(physical_mass(q+step*np.eye(2)[k],self.p)-physical_mass(q-step*np.eye(2)[k],self.p))/(2*step) for k in range(2)])
            cc = np.array([sum(.5*(dm[k,i,j]+dm[j,i,k]-dm[i,j,k])*v[j]*v[k] for j in range(2) for k in range(2)) for i in range(2)])
            worst = max(worst,float(np.max(np.abs(cc-c))))
            np.testing.assert_allclose(cc,c,atol=1e-8,rtol=0)
            l1=self.p['lengths_m'][0];r1,r2=self.p['com_m'];m1,m2=self.p['masses_kg']
            def potential(x):
                y1 = r1*np.sin(x[0]);y2 = l1*np.sin(x[0])+r2*np.sin(x.sum())
                return self.p['gravity_m_s2']*(m1*y1+m2*y2)
            fdg = np.array([(potential(q+step*np.eye(2)[k])-potential(q-step*np.eye(2)[k]))/(2*step) for k in range(2)])
            np.testing.assert_allclose(fdg,g,atol=1e-8,rtol=0)
            mdot = sum(v[k]*dm[k] for k in range(2))
            self.assertAlmostEqual(float(v@c),float(.5*v@mdot@v),places=9)
        print('new Christoffel finite-difference max_abs_error',worst)

    def test_straight_mass_static_balance_and_local_control(self):
        m,c,g = rd.mechanics([0.,0.],[0.,0.],self.p)
        np.testing.assert_allclose(m,[[8/3,5/6],[5/6,1/3]],atol=1e-14)
        self.assertAlmostEqual(np.linalg.det(m),7/36)
        np.testing.assert_allclose(g,[19.62,4.905],atol=1e-13)
        torque = [23.62,6.905]
        np.testing.assert_allclose(rd.acceleration([0.,0.],[0.,0.],torque,self.p,[0.,-2.]),[0.,0.],atol=1e-13)
        lin = rd.examples(self.config)['local_linearization']
        self.assertEqual(lin['controllability_B_AB_rank'],4)
        self.assertEqual(lin['observability_H_HA_rank'],4)

    def test_saved_physical_contract(self):
        path = ROOT/'assets/dynamics/trajectories.jsonl'
        groups = {}
        for line in path.read_text().splitlines():
            row = json.loads(line)
            groups.setdefault(row['case'],[]).append(row)
        for scenario in self.config['scenarios']:
            rows = groups[scenario['id']]
            self.assertEqual(len(rows),1201)
            raw = {**self.config['nominal'],
                   'masses_kg':(np.array(self.config['nominal']['masses_kg'])*scenario['mass_factor']).tolist(),
                   'inertia_kg_m2':(np.array(self.config['nominal']['inertia_kg_m2'])*scenario['mass_factor']).tolist()}
            p = rd.parameters(raw)
            energies = []
            for row in rows:
                q,v = np.array(row['q_rad']),np.array(row['qdot_rad_s'])
                m = physical_mass(q,p)
                m1,m2=p['masses_kg'];r1,r2=p['com_m'];l1=p['lengths_m'][0]
                potential=p['gravity_m_s2']*(m1*r1*np.sin(q[0])+m2*(l1*np.sin(q[0])+r2*np.sin(q.sum())))
                kinetic=.5*v@m@v
                energies.append(kinetic+potential)
                self.assertAlmostEqual(row['kinetic_J'],kinetic,places=10)
                self.assertAlmostEqual(row['potential_J'],potential,places=10)
                if row['applied_N_m'] is not None and scenario['torque_limit_N_m'] is not None:
                    self.assertTrue(np.all(np.abs(row['applied_N_m'])<=np.array(scenario['torque_limit_N_m'])+1e-12))
                self.assertGreaterEqual(row['dissipated_J'],-1e-12)
            residual=np.array(energies)-energies[0]-np.array([r['motor_work_J']+r['external_work_J']-r['dissipated_J'] for r in rows])
            self.assertLess(np.max(np.abs(residual)),5e-5)
            self.assertIsNone(rows[-1]['applied_N_m'])

    def test_reference_timing_and_hold_energy_step(self):
        q0,qg = self.config['start_q_rad'],self.config['goal_q_rad']
        for t in [0.,3.,6.]:
            q,v,a = rd.reference(t,q0,qg,3.)
            np.testing.assert_allclose(q,q0 if t==0 else qg,atol=1e-14)
            np.testing.assert_allclose(v,[0.,0.],atol=1e-14)
            np.testing.assert_allclose(a,[0.,0.],atol=1e-14)
        q=np.array([.4,-.8]);v=np.array([.3,-.2]); state=np.r_[q,v,0.,0.,0.]
        torque=np.array([3.,-1.]); force=np.array([.4,-.7]);e0=sum(rd.energy(q,v,self.p))
        nextstate=rd.step_rk4(state,torque,self.p,.001,force)
        e1=sum(rd.energy(nextstate[:2],nextstate[2:4],self.p))
        self.assertLess(abs(e1-e0-nextstate[4]-nextstate[5]+nextstate[6]),1e-9)
        self.assertGreaterEqual(nextstate[6],0.)


if __name__ == '__main__':unittest.main(verbosity=2)
