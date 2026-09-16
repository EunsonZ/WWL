from __future__ import annotations
import itertools, random, unittest
from structures import AffineSumTree,RollbackDSU,build,persistent_set,persistent_sum,prefix_function,kmp,suffix_model
from algorithms import knapsack,exact_knapsack,intervals,Flow,matching

class StructureTests(unittest.TestCase):
    def test_affine_worked_example_and_bounds(self):
        tree=AffineSumTree([1,2,3,4]);tree.update(1,4,1,2);tree.update(0,3,0,5);tree.update(2,4,-1,0)
        self.assertEqual([tree.query(i,i+1) for i in range(4)],[5,5,-5,-6]);self.assertEqual(tree.query(0,4),-1)
        empty=AffineSumTree([]);empty.update(0,0,0,1);self.assertEqual(empty.query(0,0),0)
        for l,r in [(-1,0),(0,5),(3,2)]:
            with self.assertRaises(ValueError):tree.query(l,r)
    def test_affine_random_against_list(self):
        rng=random.Random(20260906)
        for n in range(1,25):
            a=[rng.randrange(-10,11) for _ in range(n)];tree=AffineSumTree(a)
            for _ in range(180):
                l,r=sorted([rng.randrange(n+1),rng.randrange(n+1)])
                if rng.randrange(3):
                    c,d=rng.randrange(-2,3),rng.randrange(-4,5);tree.update(l,r,c,d)
                    a[l:r]=[c*x+d for x in a[l:r]]
                else:self.assertEqual(tree.query(l,r),sum(a[l:r]))
            self.assertEqual(tree.query(0,n),sum(a))
    def test_composition_order_and_law(self):
        def comp(new,old):a,b=new;c,d=old;return a*c,a*d+b
        def call(f,x):return f[0]*x+f[1]
        self.assertEqual(comp((0,5),(1,2)),(0,5));self.assertEqual(comp((1,2),(0,5)),(0,7))
        for f,g,h in itertools.product([(1,0),(0,3),(2,1),(-1,2)],repeat=3):
            self.assertEqual(comp(f,comp(g,h)),comp(comp(f,g),h))
            self.assertEqual(call(comp(f,g),7),call(f,call(g,7)))
    def test_rollback_nested_and_noop(self):
        d=RollbackDSU(6);m0=d.snapshot();d.union(0,1);m1=d.snapshot();d.union(2,3);d.union(1,2)
        old=d.snapshot();self.assertFalse(d.union(0,3));self.assertEqual(d.snapshot(),old)
        self.assertEqual(d.find(0),d.find(3));d.rollback(m1);self.assertNotEqual(d.find(0),d.find(2))
        self.assertEqual(d.find(0),d.find(1));d.rollback(m0);self.assertEqual(d.parent,list(range(6)));self.assertEqual(d.size,[1]*6)
        with self.assertRaises(ValueError):d.rollback(10)
        with self.assertRaises(IndexError):d.find(-1)
    def test_persistent_forks_share_unchanged_subtrees(self):
        a=list(range(8));r0=build(a);r1=persistent_set(r0,1,99);r2=persistent_set(r0,6,-7)
        self.assertIs(r0.right,r1.right);self.assertIs(r0.left,r2.left)
        self.assertEqual(persistent_sum(r0,0,8),28);self.assertEqual(r1.total,126);self.assertEqual(r2.total,15)
        rng=random.Random(4);roots=[r0];arrays=[a]
        for _ in range(100):
            k=rng.randrange(len(roots));i=rng.randrange(8);v=rng.randrange(-20,20)
            roots.append(persistent_set(roots[k],i,v));new=arrays[k].copy();new[i]=v;arrays.append(new)
        for root,arr in zip(roots,arrays):
            for l in range(9):
                for r in range(l,9):self.assertEqual(persistent_sum(root,l,r),sum(arr[l:r]))
    def test_kmp_all_short_binary_strings(self):
        self.assertEqual(prefix_function('ababaca'),[0,0,1,2,3,0,1]);self.assertEqual(kmp('aaaaa','aaa'),[0,1,2])
        words=[''.join(p) for n in range(6) for p in itertools.product('ab',repeat=n)]
        for text in words:
            for pat in words[:15]:self.assertEqual(kmp(text,pat),[i for i in range(len(text)+1) if text.startswith(pat,i)])
    def test_suffix_lcp_and_distinct_substrings(self):
        sa,h=suffix_model('banana');self.assertEqual(sa,[5,3,1,0,4,2]);self.assertEqual(h,[0,1,3,0,0,2]);self.assertEqual(21-sum(h),15)
        for s in ['', 'a','aaaa','ababa','你你我']:
            _,h=suffix_model(s);self.assertEqual(len(s)*(len(s)+1)//2-sum(h),len({s[i:j] for i in range(len(s)) for j in range(i+1,len(s)+1)}))
        sa,h=suffix_model('banana')
        for l in range(6):
            for r in range(l+1,6):
                a,b='banana'[sa[l]:],'banana'[sa[r]:];k=0
                while k<min(len(a),len(b)) and a[k]==b[k]:k+=1
                self.assertEqual(k,min(h[l+1:r+1]))

class AlgorithmTests(unittest.TestCase):
    def test_knapsack_direction_and_exact_fill(self):
        self.assertEqual(knapsack([(2,3)],4),3);self.assertIsNone(exact_knapsack([(2,3)],3));self.assertEqual(exact_knapsack([(2,3)],2),3)
        dp=[0]*5
        for c in range(2,5):dp[c]=max(dp[c],dp[c-2]+3)
        self.assertEqual(dp[4],6)
        with self.assertRaises(ValueError):knapsack([(0,1)],2)
    def test_knapsack_against_subsets(self):
        rng=random.Random(12)
        for _ in range(100):
            items=[(rng.randrange(1,7),rng.randrange(-2,15)) for _ in range(7)];cap=rng.randrange(15)
            possibilities=[(sum(items[i][0] for i in range(7) if mask>>i&1),sum(items[i][1] for i in range(7) if mask>>i&1)) for mask in range(1<<7)]
            self.assertEqual(knapsack(items,cap),max(v for w,v in possibilities if w<=cap))
            vals=[v for w,v in possibilities if w==cap];self.assertEqual(exact_knapsack(items,cap),max(vals) if vals else None)
    def test_intervals_worked_and_bruteforce(self):
        self.assertEqual(intervals([(0,3,5),(1,4,6),(3,5,5),(4,7,4),(5,8,11)]),(21,[0,0,1,2,3],[0,5,6,10,10,21]))
        rng=random.Random(5)
        for _ in range(70):
            jobs=[(s:=rng.randrange(10),s+rng.randrange(1,5),rng.randrange(1,15)) for _ in range(7)]
            best=0
            for mask in range(1<<7):
                sub=sorted(jobs[i] for i in range(7) if mask>>i&1)
                if all(a[1]<=b[0] for a,b in zip(sub,sub[1:])):best=max(best,sum(v for _,_,v in sub))
            self.assertEqual(intervals(jobs)[0],best)
    def test_reverse_residual_edge_cancels_bad_choice(self):
        f=Flow(4)
        for u,v in [(0,1),(0,2),(1,2),(1,3),(2,3)]:f.add(u,v,1)
        f.augment_path([0,1,2,3]);f.augment_path([0,2,1,3])
        self.assertEqual(f.maxflow(0,3),0)
        forward=[e for e in f.adj[1] if e[0]==2][0];self.assertEqual(forward[2],1)
    def test_maxflow_against_every_cut(self):
        rng=random.Random(2026)
        for n in range(2,7):
            for _ in range(30):
                edges=[(u,v,rng.randrange(4)) for u in range(n) for v in range(n) if u!=v and rng.random()<.3]
                if n==2:edges += [(0,1,2),(0,1,3)]
                f=Flow(n)
                for edge in edges:f.add(*edge)
                cut=min(sum(c for u,v,c in edges if u in side and v not in side) for bits in range(1<<(n-2)) for side in [{0}|{i+1 for i in range(n-2) if bits>>i&1}])
                self.assertEqual(f.maxflow(0,n-1),cut)
    def test_matching_against_exhaustive_edge_subsets(self):
        rng=random.Random(9)
        for _ in range(45):
            edges=[(u,v) for u in range(3) for v in range(3) if rng.random()<.5];best=0
            for m in range(1<<len(edges)):
                e=[edges[i] for i in range(len(edges)) if m>>i&1]
                if len({u for u,_ in e})==len(e)==len({v for _,v in e}):best=max(best,len(e))
            self.assertEqual(matching(3,3,edges),best)
    def test_cover_complement_and_two_approximation(self):
        rng=random.Random(3)
        for _ in range(80):
            n=6;edges=[(u,v) for u in range(n) for v in range(u+1,n) if rng.random()<.4];opt=n;chosen=set()
            for u,v in edges:
                if u not in chosen and v not in chosen:chosen.update((u,v))
            for bits in range(1<<n):
                cover={i for i in range(n) if bits>>i&1};ind=set(range(n))-cover
                valid=all(u in cover or v in cover for u,v in edges)
                self.assertEqual(valid,all(not(u in ind and v in ind) for u,v in edges))
                if valid:opt=min(opt,len(cover))
            self.assertTrue(all(u in chosen or v in chosen for u,v in edges));self.assertLessEqual(len(chosen),2*opt)
    def test_random_error_union_bound(self):
        self.assertAlmostEqual(1_000_000*(.25**10),.95367431640625);self.assertLess(1_000_000*.25**20,1e-6)

if __name__=='__main__':unittest.main(verbosity=2)
