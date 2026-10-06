import math
import unittest
import array_model as m

G=[[10e-6,20e-6],[30e-6,40e-6]]
V=[.1,.2]

class Tests(unittest.TestCase):
    def test_ideal_and_dimension_orientation(self):
        a=m.array(G,V)
        self.assertAlmostEqual(a['output_A'][0],7e-6, places=15)
        self.assertAlmostEqual(a['output_A'][1],10e-6, places=15)
        self.assertAlmostEqual(a['cell_W'],3.1e-6, places=15)
        self.assertEqual(a['nodes_V'],[.1,.1,.2,.2,0.,0.,0.,0.])

    def test_single_cell_series_oracle(self):
        for i,j in [(0,0),(0,1),(1,0),(1,1)]:
            g=[[0.,0.],[0.,0.]];g[i][j]=25e-6
            a=m.array(g,V,1000)
            # Row path contains j+1 line resistors, column contains 2-i.
            expected=V[i]/(1/g[i][j]+(j+3-i)*1000)
            self.assertAlmostEqual(a['output_A'][j],expected, places=15)
            self.assertAlmostEqual(a['output_A'][1-j],0., places=15)

    def test_independent_neighbor_relaxation(self):
        # Alternate algorithm: simultaneous weighted neighbor updates, explicit topology.
        r=1000.;h=1/r
        neighbors=[[(1,h),(4,G[0][0])],[(0,h),(5,G[0][1])],[(3,h),(6,G[1][0])],[(2,h),(7,G[1][1])],[(6,h),(0,G[0][0])],[(7,h),(1,G[0][1])],[(4,h),(2,G[1][0])],[(5,h),(3,G[1][1])]]
        anchors={0:(h,.1),2:(h,.2),6:(h,0.),7:(h,0.)}
        x=[0.]*8
        for _ in range(10000):
            y=[]
            for k,ns in enumerate(neighbors):
                a,u=anchors.get(k,(0.,0.))
                y.append((sum(q*x[n] for n,q in ns)+a*u)/(sum(q for _,q in ns)+a))
            if max(abs(x[k]-y[k]) for k in range(8))<1e-15:
                x=y;break
            x=y
        a=m.array(G,V,r)
        for actual,expected in zip(a['nodes_V'],x):
            self.assertAlmostEqual(actual,expected,places=12)
        self.assertLess(a['residual_A'],1e-18)
        self.assertAlmostEqual(a['supplied_W'],a['cell_W']+a['wire_W'],places=16)

    def test_limits_and_odd_response(self):
        ideal=m.array(G,V)
        near=m.array(G,V,1)
        finite=m.array(G,V,1000)
        neg=m.array(G,[-t for t in V],1000)
        for j in range(2):
            self.assertLess(abs(near['output_A'][j]/ideal['output_A'][j]-1),.0003)
            self.assertLess(finite['output_A'][j],ideal['output_A'][j])
            self.assertAlmostEqual(neg['output_A'][j],-finite['output_A'][j],places=15)
        zero=m.array([[0,0],[0,0]],V,1000)
        self.assertEqual(zero['output_A'],[0.,0.])

    def test_differential_and_common_mode_cost(self):
        d=m.differential([[1,-2],[-3,4]],[1,2])
        self.assertAlmostEqual(d['difference_A'][0],-5e-6,places=15)
        self.assertAlmostEqual(d['difference_A'][1],6e-6,places=15)
        z=m.differential([[0,0],[0,0]],[1,2])
        self.assertEqual(z['difference_A'],[0.,0.])
        self.assertGreater(z['core_W'],0)

    def test_quantizer_ties_and_bias(self):
        fs=20e-6;delta=fs/16
        for k in range(1,16):
            self.assertEqual(m.quantize_current(fs*k/16)[0],k)
        self.assertEqual(m.quantize_current(fs)[0],15)
        code,value=m.quantize_current(0.)
        self.assertEqual(code,0)
        self.assertEqual(value,delta/2)
        with self.assertRaises(ValueError):m.quantize_current(fs*1.01)

    def test_drift_and_scalar_calibration_counterexample(self):
        self.assertEqual(m.drift(20e-6,1),20e-6)
        self.assertAlmostEqual(m.drift(20e-6,100,exponent=.1)/20e-6,10**(-.2),places=14)
        q1=m.array(G,[.1,0],1000)['output_A'][0]
        q2=m.array(G,[0,.1],1000)['output_A'][0]
        gain=1e-6/q1
        self.assertGreater(abs(gain*q2-3e-6),1e-9)

    def test_energy_units_amortization(self):
        e=m.energy(3.3e-6)
        self.assertAlmostEqual(e['total_J'],318.3e-12,places=22)
        self.assertAlmostEqual(m.energy(0,uses=2000)['components']['calibration_J'],50e-12,places=22)
        with self.assertRaises(ValueError):m.energy(0,uses=0)

    def test_lif_analytic_events_and_threshold_limit(self):
        a=m.lif(.03,2e-9)
        first=.01*math.log(2);period=first+.001
        expected=[first+k*period for k in range(3)]
        for x,y in zip(a['events_s'],expected):self.assertAlmostEqual(x,y,places=15)
        self.assertEqual(len(a['events_s']),3)
        self.assertEqual(m.lif(1,1e-9)['events_s'],[])
        no=m.lif(.01,0,initial_V=.008)
        self.assertAlmostEqual(no['final_V'],.008/math.e,places=15)
        endpoint=m.lif(first,2e-9)
        self.assertEqual(endpoint['events_s'],[first])
        self.assertEqual(endpoint['final_V'],0.)
        hold=m.lif(first+.0005,2e-9)
        self.assertEqual(hold['final_V'],0.)

    def test_lif_euler_alternate_and_reset_charge(self):
        dt=1e-6;v=0.;t=0.
        while v<.01:
            v+=dt*(2e-9-v/1e7)/1e-9;t+=dt
        self.assertLess(abs(t-m.lif(.02,2e-9)['events_s'][0]),2*dt)
        self.assertAlmostEqual(1e-9*.01,10e-12,places=22)
        self.assertAlmostEqual(.5*1e-9*.01**2,50e-15,places=25)

    def test_invalid_inputs_fail_explicitly(self):
        for value in [True,complex(1,0),float('nan'),float('inf'),10**400]:
            with self.assertRaises(ValueError):m.array(G,[value,.1])
            with self.assertRaises(ValueError):m.lif(.1,value)
            with self.assertRaises(ValueError):m.energy(value)
        for g in [[[1e-6]],[[1e-6,1e-6]],[[1e-6,-1e-6],[0,0]]]:
            with self.assertRaises(ValueError):m.array(g,V)
        with self.assertRaises(ValueError):m.array(G,V,.1)
        with self.assertRaises(ValueError):m.lif(.1,1e-9,initial_V=.01)

if __name__=='__main__':unittest.main()
