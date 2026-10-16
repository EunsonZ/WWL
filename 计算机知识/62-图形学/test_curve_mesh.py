import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
import curve_mesh_lab as m
HERE=Path(__file__).parent
class Geometry(unittest.TestCase):
    def setUp(self):self.p=[[0,0,0],[1,2,0],[2,0,0]]
    def test_construct_point_and_join(self):
        np.testing.assert_allclose(m.casteljau(self.p,.5),[1,1,0]);np.testing.assert_allclose(m.tangent(self.p,1),[2,-4,0])
        q=[[2,0,0],[3,-2,0],[4,0,0]];np.testing.assert_allclose(m.tangent(q,0),m.tangent(self.p,1))
        q[1]=[2.5,-1,0];np.testing.assert_allclose(2*m.tangent(q,0),m.tangent(self.p,1))
    def test_strip_topology_and_error(self):
        for N in [1,4,8,16]:
            x=m.band(self.p,np.linspace(0,1,N+1),.25);t=x['topology']
            self.assertEqual([t[k] for k in ['V','E','F','chi','boundary_count']],[2*N+2,4*N+1,2*N,1,2*N+2])
            self.assertAlmostEqual(x['exact_matched_parameter_max'],1/N**2)
    def test_bad_indices_and_degenerate(self):
        x=m.band(self.p,[0,.5,1],.25);f=np.array(x['triangles']);f[0,0]=99
        with self.assertRaisesRegex(ValueError,'face_index'):m.topology(x['positions'],f)
        with self.assertRaisesRegex(ValueError,'numerically_degenerate'):m.topology([[0,0,0],[1,0,0],[2,0,0]],[[0,1,2]])
        with self.assertRaisesRegex(ValueError,'duplicate_face'):m.topology([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2],[2,1,0]])
    def test_nonmanifold_edge_and_vertex(self):
        p=[[0,0,0],[1,0,0],[0,1,0],[0,-1,0],[0,0,1]]
        with self.assertRaisesRegex(ValueError,'nonmanifold_edge'):m.topology(p,[[0,1,2],[1,0,3],[0,1,4]])
        p=[[0,0,0],[1,0,0],[0,1,0],[-1,0,0],[0,-1,0]]
        with self.assertRaisesRegex(ValueError,'disconnected_vertex_link'):m.topology(p,[[0,1,2],[0,3,4]])
    def test_wrong_orientation_and_band_domain(self):
        with self.assertRaisesRegex(ValueError,'shared_edge_orientation'):m.topology([[0,0,0],[1,0,0],[0,1,0],[0,-1,0]],[[0,1,2],[0,1,3]])
        for p,ts,w in [([[0,0,0],[0,1,0],[0,2,0]],[0,1],.25),(self.p,[0,.5,.5,1],.25),(self.p,[0,1],0),([[0,0,0],[1,2,1],[2,0,0]],[0,1],.25)]:
            with self.assertRaises(ValueError):m.band(p,ts,w)
    def test_parameters_and_output_ownership(self):
        with self.assertRaises(ValueError):m.casteljau(self.p,1.1)
        with self.assertRaises(ValueError):m.casteljau(self.p,float('nan'))
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):m.run({},Path('not-used'),Path(d))
if __name__=='__main__':unittest.main(verbosity=2)
