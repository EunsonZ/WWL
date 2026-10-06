"""Independent preorder oracle and exhaustive checks for n <= 3."""
from itertools import product
from pathlib import Path
import tempfile
import unittest
from topology_lab import FiniteTopology, all_topologies, continuous, quotient, powerset, write_figures


def preorder_topologies(n):
    pairs = [(i,j) for i in range(n) for j in range(n) if i != j]
    families = set()
    for bits in product([False,True], repeat=len(pairs)):
        r = {(i,i) for i in range(n)} | {p for p,b in zip(pairs,bits) if b}
        if any((a,c) not in r for a,b in r for bb,c in r if b == bb):
            continue
        families.add(frozenset(u for u in powerset(range(n))
                              if all(b in u for a,b in r if a in u)))
    return families


def local_continuity(source, target, mapping):
    for x in source.points:
        for v in target.opens:
            if mapping[x] in v and not any(x in u and all(mapping[a] in v for a in u)
                                           for u in source.opens):
                return False
    return True


class TopologyTests(unittest.TestCase):
    def test_preorder_oracle(self):
        for n,count in enumerate([1,1,4,29]):
            actual = {t.opens for t in all_topologies(range(n))}
            self.assertEqual(len(actual),count)
            self.assertEqual(actual,preorder_topologies(n))

    def test_continuity_all_two_point_maps(self):
        spaces = list(all_topologies(range(2)))
        for source,target in product(spaces,repeat=2):
            for values in product(range(2),repeat=2):
                m = dict(enumerate(values))
                self.assertEqual(continuous(source,target,m),local_continuity(source,target,m))

    def test_quotient_universal_property(self):
        targets = [FiniteTopology({0,1},[set(),{1},{0,1}]),
                   FiniteTopology({0,1},powerset([0,1]))]
        for source in all_topologies(range(3)):
            for values in product(range(2),repeat=3):
                if set(values) != {0,1}:
                    continue
                q = dict(enumerate(values))
                target = quotient(source,[0,1],q)
                self.assertTrue(continuous(source,target,q))
                image_opens = set()
                for u in source.opens:
                    image = frozenset(q[x] for x in u)
                    if frozenset(x for x in source.points if q[x] in image) == u:
                        image_opens.add(image)
                self.assertEqual(target.opens,frozenset(image_opens))
                for z in targets:
                    for pair in product(range(2),repeat=2):
                        f = dict(enumerate(pair))
                        self.assertEqual(continuous(target,z,f),
                            continuous(source,z,{x:f[q[x]] for x in source.points}))

    def test_subspaces_hausdorff(self):
        for s in all_topologies(range(3)):
            self.assertEqual(s.hausdorff(),len(s.opens)==8)
            for a in powerset(range(3)):
                sub = s.subspace(a)
                for x in a:
                    self.assertEqual(sub.minimum_neighborhood(x),s.minimum_neighborhood(x) & a)

    def test_compactness_every_cover(self):
        for s in all_topologies(range(3)):
            opens = list(s.opens)
            for bits in product([False,True],repeat=len(opens)):
                cover = [u for u,b in zip(opens,bits) if b]
                if frozenset().union(*cover) == s.points:
                    chosen = [next(u for u in cover if x in u) for x in s.points]
                    self.assertEqual(frozenset().union(*chosen),s.points)
                    self.assertLessEqual(len(chosen),len(s.points))

    def test_empty(self):
        e = FiniteTopology([],[set()])
        p = FiniteTopology(['p'],[set(),{'p'}])
        self.assertTrue(e.connected())
        self.assertTrue(e.hausdorff())
        self.assertTrue(continuous(e,p,{}))
        self.assertEqual(quotient(e,[],{}),e)
        with self.assertRaises(ValueError):
            quotient(e,['p'],{})

    def test_invalid(self):
        cases = [([0],[]),([0],[set()]),([0],[set(),{0},{1}]),
                 ([0,1,2],[set(),{0},{1},{0,1,2}]),([0,0],[set(),{0}]),
                 ([float('nan')],[set()]),([float('inf')],[set()]),([True],[set()]),
                 (range(9),[set()]),('ab',[set()])]
        for points,opens in cases:
            with self.assertRaises(ValueError):
                FiniteTopology(points,opens)
        p = FiniteTopology([0],[set(),{0}])
        for m in ({},{0:1},{0:float('nan')},{0:0,1:0},[0]):
            with self.assertRaises(ValueError):
                continuous(p,p,m)
        with self.assertRaises(ValueError):
            quotient(p,[0,1],{0:0})
        with self.assertRaises(ValueError):
            p.subspace([1])
        with self.assertRaises(ValueError):
            p.minimum_neighborhood(1)
        with self.assertRaises(ValueError):
            list(all_topologies(range(4)))

    def test_figures_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            write_figures(d)
            first = {p.name:p.read_bytes() for p in Path(d).glob('*.svg')}
            write_figures(d)
            second = {p.name:p.read_bytes() for p in Path(d).glob('*.svg')}
            self.assertEqual(first,second)
            self.assertEqual(len(first),3)
            self.assertTrue(all(b'Date' not in b and b'\r' not in b for b in first.values()))
            self.assertTrue(all(b'fill="#ffffff"' in b for b in first.values()))


if __name__ == '__main__':
    unittest.main()
