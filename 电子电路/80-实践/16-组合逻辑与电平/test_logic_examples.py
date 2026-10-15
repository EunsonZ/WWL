import math
import unittest
import logic_examples as m

class LogicTests(unittest.TestCase):
    def test_full_independent_integer_oracle(self):
        self.assertEqual(m.validate_all()['arithmetic'],768)
        self.assertEqual(m.validate_all()['comparison'],256)
        self.assertEqual(m.compare(15,1),dict(unsigned_lt=0,signed_lt=1))
        with self.assertRaises(ValueError):m.validate_all(8,budget=10000)
    def test_voltage_analytic(self):
        z=m.margins()
        for key,val in {'vil':1.3875,'vih':1.9125,'vol':.2625,'voh':3.0375,'nml':1.125,'nmh':1.125}.items():self.assertAlmostEqual(z[key],val)
        self.assertAlmostEqual(m.vtc(z['vil']),z['voh']);self.assertAlmostEqual(m.vtc(z['vih']),z['vol'])
        h=1e-6
        for x in (z['vil'],z['vih']):self.assertAlmostEqual((m.vtc(x+h)-m.vtc(x-h))/(2*h),-1,places=6)
        with self.assertRaises(ArithmeticError):m.vtc(1.65)
    def test_rc_energy(self):
        self.assertAlmostEqual(m.charge(20e-9*math.log(2)),1.65)
        self.assertAlmostEqual(m.charge(m.pullup_time(),4700,100e-12),2)
        self.assertAlmostEqual(m.power(),5.445e-4)
    def test_flags_counterexamples(self):
        self.assertEqual(m.add(7,3),dict(word=10,carry=0,overflow=1))
        self.assertEqual(m.add(15,1),dict(word=0,carry=1,overflow=0))
        self.assertEqual(m.sub(3,5),dict(word=14,carry=0,overflow=0,borrow=1))
    def test_bus(self):
        self.assertEqual(m.resolve(['Z','1']),'1');self.assertEqual(m.resolve(['0','1']),'X')
        self.assertEqual(m.resolve(['Z','Z']),'Z')
    def test_invalid_words(self):
        for x in (-1,16,True,1.0,1+0j,'1',None):
            with self.assertRaises(ValueError):m.add(x,0)
        for w in (0,9,True,4.0):
            with self.assertRaises(ValueError):m.add(0,0,w)
        for x in (-1,2,True):
            with self.assertRaises(ValueError):m.mux(x,0,1)
    def test_invalid_real_before_conversion(self):
        for x in (float('nan'),float('inf'),True,1+0j,'1',[1],None):
            with self.assertRaises(ValueError):m.charge(x)
        for call in (lambda:m.charge(-1),lambda:m.charge(1,r=0),lambda:m.margins(1,.6),lambda:m.vtc(4),lambda:m.pullup_time(3.3),lambda:m.power(alpha=2)):
            with self.assertRaises(ValueError):call()
    def test_driver_invalid(self):
        for ds in ([],['X'],[0],['Z']*17,'01'):
            with self.assertRaises(ValueError):m.resolve(ds)

if __name__=='__main__':unittest.main()
