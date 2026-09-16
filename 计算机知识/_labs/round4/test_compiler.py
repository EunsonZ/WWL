import itertools,re,unittest
from compiler_models import SLR,liveness,Var,Con,arrow,apply,free,unify,instantiate

class CompilerTests(unittest.TestCase):
    def parser(self):return SLR([('S',('C','C')),('C',('c','C')),('C',('d',))],'S')
    def test_slr_states_table_and_trace(self):
        p=self.parser();self.assertEqual(len(p.states),7);self.assertEqual(p.follow['C'],{'c','d','$'})
        expected={(0,'C'):1,(0,'S'):2,(0,'c'):3,(0,'d'):4,(1,'C'):5,(1,'c'):3,(1,'d'):4,(3,'C'):6,(3,'c'):3,(3,'d'):4}
        self.assertEqual(p.transitions,expected)
        self.assertEqual(p.parse(list('cdd')),(True,[('s',3),('s',4),('r',3),('r',2),('s',4),('r',3),('r',1),('a',0)]))
    def test_slr_against_independent_language(self):
        p=self.parser()
        for n in range(10):
            for seq in itertools.product('cd',repeat=n):
                s=''.join(seq);self.assertEqual(p.parse(list(s))[0],re.fullmatch('c*dc*d',s) is not None,s)
        self.assertFalse(p.parse(['$'])[0]);self.assertFalse(p.parse(['other'])[0])
    def test_epsilon_reduction_pops_zero(self):
        p=SLR([('S',('A',)),('A',('a','A')),('A',())],'S')
        for n in range(10):self.assertTrue(p.parse(['a']*n)[0])
    def test_slr_context_loss_conflict(self):
        with self.assertRaisesRegex(ValueError,'SLR conflict'):
            SLR([('S',('L','=','R')),('S',('R',)),('L',('*','R')),('L',('id',)),('R',('L',))],'S')
    def test_liveness_fixed_point(self):
        use=[set(),{'x','p'},{'y'},{'y'}];defs=[{'x'},{'y'},{'x'},set()];succ=[[1],[2,3],[1],[]]
        expected=([{'p'},{'x','p'},{'y','p'},{'y'}],[{'x','p'},{'y','p'},{'x','p'},set()])
        self.assertEqual(liveness(use,defs,succ),expected);self.assertEqual(liveness(use,defs,succ,False),expected)
        no_loop=liveness(use,defs,[[1],[2,3],[],[]]);self.assertNotIn('p',no_loop[0][2])
        self.assertEqual(liveness([{'x'}],[set()],[[0]])[0],[{'x'}])
    def test_interval_cover_and_lost_correlation(self):
        for alo,ahi,blo,bhi in [(-2,4,1,7),(0,0,-5,-2),(3,9,-9,2)]:
            concrete={a+b for a in range(alo,ahi+1) for b in range(blo,bhi+1)}
            self.assertEqual(min(concrete),alo+blo);self.assertEqual(max(concrete),ahi+bhi)
        states=[(0,1),(1,0)];self.assertEqual({x+y for x,y in states},{1})
        abstract={x+y for x in [0,1] for y in [0,1]};self.assertEqual(abstract,{0,1,2})
    def test_unification_composition_and_occurs(self):
        a,b,c=map(Var,'abc');integer=Con('int');s=unify([(a,b),(b,integer)])
        self.assertEqual(apply(a,s),integer)
        with self.assertRaisesRegex(ValueError,'occurs'):unify([(a,arrow(a,b))])
        with self.assertRaisesRegex(ValueError,'constructor'):unify([(integer,Con('bool'))])
        s=unify([(arrow(a,b),arrow(b,c))]);self.assertEqual(apply(a,s),apply(b,s));self.assertEqual(apply(b,s),apply(c,s))
        f=Var('f');s=unify([(f,arrow(a,b)),(f,arrow(b,c))]);t=apply(arrow(f,arrow(a,c)),s);v=apply(a,s)
        self.assertEqual(t,arrow(arrow(v,v),arrow(v,v)))
    def test_instantiation_and_environment_free_variables(self):
        a,b=Var('a'),Var('b');identity=arrow(a,a)
        i1,i2=instantiate(identity,{a},'one'),instantiate(identity,{a},'two')
        s=unify([(i1,arrow(Con('int'),Con('int'))),(i2,arrow(Con('bool'),Con('bool')))])
        self.assertEqual(apply(i1,s),arrow(Con('int'),Con('int')))
        with self.assertRaises(ValueError):unify([(identity,arrow(Con('int'),Con('int'))),(identity,arrow(Con('bool'),Con('bool')))])
        captured=arrow(a,b);environment_free={b};self.assertEqual(free(captured)-environment_free,{a})

if __name__=='__main__':unittest.main(verbosity=2)
