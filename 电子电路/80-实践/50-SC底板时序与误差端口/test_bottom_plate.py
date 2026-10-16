import copy
from fractions import Fraction as F
import json
import os
from pathlib import Path
import tempfile
import unittest
import bottom_plate_lab as lab

ROOT=Path(os.environ.get('WWL_SC_ROOT','/Users/ysz/Misc/Obsidian/Valults/WLM/WWL'))
CARD=json.loads(Path(__file__).with_name('fixed-inputs.json').read_text())

def parsed(card):
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'input.json';path.write_text(json.dumps(card));return lab.load(path)

class Contracts(unittest.TestCase):
    def setUp(self):self.c,self.p=parsed(CARD)
    def test_independent_closed_form_bf_af(self):
        p=self.p;cs,cf,la,lb=lab.capacitances(p);dg=p['clock_low_absolute_V']-p['clock_high_absolute_V']
        for x in p['x_V']:
            uA=-p['kappaA_F']*(p['clock_high_absolute_V']-p['Vcm_absolute_V']-p['Vth_V']-x)+p['CgA_F']*dg
            uB=-p['kappaB_F']*(p['clock_high_absolute_V']-p['Vcm_absolute_V']-p['Vth_V'])+p['CgB_F']*dg
            bf=lab.edge_record(p,x,'bottom_first');af=lab.edge_record(p,x,'input_first')
            self.assertEqual(F(bf['qB_transfer_effective_C']),-cs*x+uB+p['Ccross_F']*dg)
            self.assertEqual(F(af['qB_transfer_effective_C']),-cs*x-cs/la*uA+uB)
    def test_clock_and_reference_shift_invariance(self):
        p=copy.deepcopy(self.p);delta=F(5,4)
        for k in ('clock_high_absolute_V','clock_low_absolute_V','Vcm_absolute_V'):p[k]+=delta
        self.assertEqual(lab.edge_record(p,F(1,5),'bottom_first'),lab.edge_record(self.p,F(1,5),'bottom_first'))
    def test_b_free_charge_protected_not_voltage(self):
        d=lab.edge_record(self.p,F(4,5),'bottom_first');st=d['stages']
        self.assertEqual(st[1]['qB_free_C'],st[2]['qB_free_C']);self.assertEqual(st[2]['qB_free_C'],st[3]['qB_free_C'])
        self.assertNotEqual(st[1]['B_V'],st[2]['B_V'])
    def test_off_charge_ideal_sign(self):
        rows=lab.sequence(self.p,'bottom_first')
        for row in rows:
            self.assertEqual(F(row['qf_after_off_C'])-F(row['qf_transfer_C']),self.p['qoff_C'])
            self.assertEqual(F(row['y_after_off_V'])-F(row['y_transfer_V']),-self.p['qoff_C']/self.p['Cf_F'])
    def test_swing_includes_initial_endpoint(self):
        c=copy.deepcopy(CARD);c['x_V']=['-1'];c['y0_V']='101/100';c['tight_limit_probe_V']='1'
        for k in ('aperture_shift_s','input_slope_V_per_s','T2_shift_s'):c[k]=['0']
        c,p=parsed(c);r=lab.run(c,p,ROOT)
        for name,rows in r['finite_cases'].items():
            self.assertLess(abs(rows[0]['w_transfer_V']),1);self.assertLess(abs(rows[0]['y_next_V']),1)
            self.assertFalse(rows[0]['within_linear_swing']);self.assertEqual(r['tight_swing_first_violation'][name],0)
    def test_rc_joint_covariance_from_innovations(self):
        r=lab.rc_memory(self.p);rho=r['rho'];eq=r['equilibrium_V2'];N=self.p['rc_count']
        for i in range(N):
            for j in range(N):
                expected=sum(rho**(i-k)*rho**(j-k)*(1-rho*rho)*eq for k in range(min(i,j)+1))
                self.assertAlmostEqual(r['zero_initial_covariance_V2'][i][j]/eq,expected/eq,places=14)
        self.assertGreater(r['stationary_average_V2'],r['incorrect_independent_stationary_average_V2'])
    def test_reject_singular_bool_and_shifted_domain(self):
        cards=[]
        c=copy.deepcopy(CARD);c['rc_count']=True;cards.append(c)
        c=copy.deepcopy(CARD);c['Cs_F']=1e-12;cards.append(c)
        c=copy.deepcopy(CARD);c['T2_shift_s'][0]=c['TH_s'];cards.append(c)
        c=copy.deepcopy(CARD);c['input_slope_V_per_s'][0]='1000000000000';cards.append(c)
        c=copy.deepcopy(CARD)
        for k in ('CpA_F','CpB_F','CgA_F','CgB_F'):c[k]='0'
        cards.append(c)
        for c in cards:
            with self.assertRaises(ValueError):parsed(c)
if __name__=='__main__':unittest.main()
