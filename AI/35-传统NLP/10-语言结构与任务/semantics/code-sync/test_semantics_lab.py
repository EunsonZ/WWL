"""Contract variants that distinguish semantic errors from lexical matching."""
import itertools
import unittest
import semantics_lab as lab

PEOPLE={'Mira':'M','Lena':'L','Noor':'N','Omar':'O'}


class ContractTests(unittest.TestCase):
    def test_voice_and_theme_variants(self):
        for giver,recipient in itertools.permutations(PEOPLE,2):
            for np in ('a book','a red book'):
                with self.subTest(giver=giver,recipient=recipient,np=np):
                    active=lab.parse(f'{giver} gave {np} to {recipient}.',PEOPLE)
                    passive=lab.parse(f'{recipient} was given {np} by {giver}.',PEOPLE)
                    fa=lab.frames(active,lab.assignments(active)[0])[0]
                    fp=lab.frames(passive,lab.assignments(passive)[0])[0]
                    self.assertEqual(fa,fp)
                    self.assertEqual(fa['roles'],{'giver':PEOPLE[giver],'theme':'b','recipient':PEOPLE[recipient]})
                    self.assertEqual(fa['theme_properties'],['red'] if np=='a red book' else [])

    def test_negation_and_additional_attitude(self):
        a=lab.parse('Lena thanked Mira.',PEOPLE)
        n=lab.parse('Lena did not thank Mira.',PEOPLE)
        h=lab.parse('Lena reluctantly thanked Mira.',PEOPLE)
        af=lab.frames(a,lab.assignments(a)[0])[0]
        nf=lab.frames(n,lab.assignments(n)[0])[0]
        hf=lab.frames(h,lab.assignments(h)[0])[0]
        self.assertEqual(af['roles'],nf['roles']);self.assertNotEqual(af['polarity'],nf['polarity'])
        self.assertEqual(af['roles'],hf['roles']);self.assertNotEqual(af['manner'],hf['manner'])

    def test_no_antecedent_or_reflexive_guess(self):
        self.assertEqual(lab.assignments(lab.parse('She thanked her.',PEOPLE)),[])
        self.assertEqual(lab.assignments(lab.parse('Mira thanked Mira.',PEOPLE)),[])
        d=lab.parse('Mira gave a book to Lena. She thanked her.',PEOPLE)
        self.assertEqual(len(lab.assignments(d)),2)
        self.assertEqual(len(lab.assignments(d,{'agent':'recipient','target':'recipient'})),0)

    def test_permutation_invariant_bag_does_not_preserve_roles(self):
        r='Mira thanked Lena.'; c='Lena thanked Mira.'
        self.assertEqual(lab.bleu(c,r,1)['score'],1)
        a=lab.parse(r,PEOPLE);b=lab.parse(c,PEOPLE)
        self.assertNotEqual(lab.frames(a,lab.assignments(a)[0]),lab.frames(b,lab.assignments(b)[0]))
        repeated=lab.bleu('Mira Mira Mira Mira.','Mira thanked Lena.',1)
        self.assertEqual(repeated['ngrams'][0]['matched'],2)  # Mira once + period once.
        self.assertIsNone(lab.bleu('Mira thanked Lena','Mira thanked Lena.',4)['score'])
        self.assertEqual(lab.bleu('', 'Mira thanked Lena.',4)['score'],0)

    def test_empty_typed_domains(self):
        self.assertEqual((lab.typed_scope([],['b'],[])['A'],lab.typed_scope([],['b'],[])['C']),(True,True))
        self.assertEqual((lab.typed_scope(['s'],[],[])['A'],lab.typed_scope(['s'],[],[])['C']),(False,False))
        self.assertEqual((lab.typed_scope([],[],[])['A'],lab.typed_scope([],[],[])['C']),(True,False))
        with self.assertRaises(ValueError):lab.typed_scope(['s'],['b'],[['b','s']])

    def test_prefix_mass_and_invalid_candidates(self):
        cs=[{'tokens':['a'],'weight':2},{'tokens':['a','b'],'weight':1},{'tokens':['c'],'weight':3}]
        mass,children,leaves=lab.build_prefix(cs)
        for leaf,p in leaves.items():
            prefix=();product=lab.Fraction(1)
            for token in leaf:product*=children[prefix][token];prefix+=(token,)
            self.assertEqual(product,p)
        with self.assertRaises(ValueError):lab.build_prefix([{'tokens':['a'],'weight':0}])
        with self.assertRaises(ValueError):lab.beam(cs,True)
        for text in ('Mira promised to give a book to Lena.','Mira did not give a book to Lena.','Mira thanked Lena?','米拉感谢莉娜。','Mira gave a book to Lena. Noor gave a book to Omar.'):
            with self.assertRaises(ValueError):lab.parse(text,PEOPLE)


if __name__=='__main__':unittest.main(verbosity=2)
