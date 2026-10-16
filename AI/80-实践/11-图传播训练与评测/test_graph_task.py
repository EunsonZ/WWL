"""Author regression tests; an independent oracle must still check important claims."""
import copy
import unittest
import numpy as np
import graph_task as g


class GraphTaskTests(unittest.TestCase):
    def setUp(self):
        self.a = np.array([[[0., 1., 0.], [1., 0., 1.], [0., 1., 0.]]])
        self.x = np.array([[[.2, -.1], [.5, .3], [-.4, .7]]])
        self.y = np.array([[0, 1, 1]])

    def test_every_parameter_gradient(self):
        for family in ('no_graph', 'fixed', 'joint'):
            p = g.initialize(family, 2, 2, 2, 17)
            _, grad = g.objective(p, family, 2, self.a, self.x, self.y, .001)
            for key in p:
                for index in np.ndindex(p[key].shape):
                    plus, minus = copy.deepcopy(p), copy.deepcopy(p)
                    plus[key][index] += 1e-6
                    minus[key][index] -= 1e-6
                    numeric = (g.objective(plus, family, 2, self.a, self.x, self.y, .001)[0] -
                               g.objective(minus, family, 2, self.a, self.x, self.y, .001)[0]) / 2e-6
                    self.assertAlmostEqual(numeric, grad[key][index], places=7, msg=(family, key, index))

    def test_permutation_and_no_graph(self):
        order = [2, 0, 1]
        for family in ('no_graph', 'fixed', 'joint'):
            p = g.initialize(family, 2, 3, 2, 17)
            original = g.forward(p, family, 2, self.a, self.x)[0]
            moved = g.forward(p, family, 2, self.a[:, order][:, :, order], self.x[:, order])[0]
            np.testing.assert_allclose(moved, original[:, order], atol=1e-12)
            if family == 'no_graph':
                np.testing.assert_equal(g.forward(p, family, 2, self.a * 0, self.x)[0], original)

    def test_spectrum(self):
        s = g.spectral()
        np.testing.assert_allclose(s['cycle6']['eigenvalues'], [-1/3, 0, 0, 2/3, 2/3, 1], atol=1e-14)
        self.assertEqual(s['two_triangles']['history'][1]['h'], [1/3, 1/3, 1/3, 0, 0, 0])
        for row in s['cycle6']['history']:
            k = row['k']
            exact = np.sqrt((1/3)*(4/9)**k + (1/6)*(1/9)**k) if k > 0 else np.sqrt(5/6)
            self.assertAlmostEqual(row['distance_to_limit'], exact, places=13)

    def test_split_inputs_and_metrics(self):
        proto = g.load(__import__('pathlib').Path(__file__).with_name('protocol.json'))
        data = g.generate(proto)['graphs']
        ids = [row['id'] for row in data]
        self.assertEqual(len(ids), len(set(ids)))
        for seed in proto['seeds']:
            for regime in proto['regimes']:
                group = [r for r in data if r['seed'] == seed and r['regime'] == regime]
                for split, count in proto['splits'].items():
                    rows = [r for r in group if r['split'] == split]
                    self.assertEqual(len(rows), count)
                    self.assertTrue(all(sum(r['y']) == 12 for r in rows))
        result = g.metrics(np.array([[0, 1, 1]]), np.array([[-1., 0., -1.]]))[0]
        self.assertEqual(result['correct'], 2)
        tiny = g.metrics(np.array([[0, 1, 1]]), np.array([[-1e-20, 0., 1e-20]]))[0]
        self.assertEqual(tiny['correct'], 3)
        self.assertAlmostEqual(result['accuracy'], 2/3)
        self.assertRaises(ValueError, g.arrays, [{'A': [[0, 1], [0, 0]], 'X': [[1], [2]]}])


if __name__ == '__main__':
    unittest.main()
