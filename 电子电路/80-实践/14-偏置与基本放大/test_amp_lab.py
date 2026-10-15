import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import amp_lab as a

class AmplifierContracts(unittest.TestCase):
    def test_q_and_derivative(self):
        for rs in (0.,500.):
            p=a.mos_bias(rs=rs)
            self.assertAlmostEqual(p['vd']+p['id']*2000,5.)
            self.assertAlmostEqual(p['vs'],p['id']*rs)
            self.assertGreater(p['vds'],p['vov'])
            h=1e-6
            gm=(a.mos_point(p['vgs']+h,p['vds'])['id']-a.mos_point(p['vgs']-h,p['vds'])['id'])/(2*h)
            go=(a.mos_point(p['vgs'],p['vds']+h)['id']-a.mos_point(p['vgs'],p['vds']-h)['id'])/(2*h)
            self.assertAlmostEqual(gm,p['gm'],places=10);self.assertAlmostEqual(go,p['go'],places=10)
        b=a.bjt_bias()
        self.assertAlmostEqual(b['vb']+b['ib']*7500,1.25)
        self.assertAlmostEqual(b['ic'],1e-15*math.exp(b['vbe']/.026),places=14)
        self.assertAlmostEqual(b['vc']+4000*b['ic'],5.)
        self.assertGreater(b['vc'],b['vb'])
        self.assertLess(a.bjt_bias(beta=50)['ic'],b['ic'])
        self.assertGreater(a.bjt_bias(beta=200)['ic'],b['ic'])
        with self.assertRaises(ValueError):a.bjt_bias(rc=10000)

    def test_cs_ce_independent_kcl_and_output_test(self):
        for gm in (.001,.003,.02):
          for go in (0.,.00002):
            rs=500.;rd=2000.;rl=10000.;yd=1/rd+1/rl;ys=1/rs
            matrix=np.array([[yd+go,-go-gm],[-go,ys+go+gm]])
            vd,vs=np.linalg.solve(matrix,[-gm,gm])
            self.assertAlmostEqual(a.cs(gm,go,rd,rs,rl)['av'],vd)
            vx=1.;sv=go/(ys+go+gm)
            ix=1/rd+go*(vx-sv)-gm*sv
            self.assertAlmostEqual(a.cs(gm,go,rd,rs,rl)['rout'],1/ix)
            beta=100.;gp=gm/beta;re=1000.;rc=4000.;yc=1/rc+1/rl;ye=1/re
            mat=np.array([[yc+go,-go-gm],[-go,ye+go+gm+gp]])
            vc,ve=np.linalg.solve(mat,[-gm,gm+gp]);q=a.ce(gm,beta,go,rc,re,rl)
            self.assertAlmostEqual(q['av'],vc);self.assertAlmostEqual(q['rin_base'],1/(gp*(1-ve)),places=6)
            sev=go/(ye+go+gm+gp);ixc=1/rc+go*(1-sev)-gm*sev
            self.assertAlmostEqual(q['rout'],1/ixc)
        self.assertAlmostEqual(a.cs(.002,0,2000,0,10000)['av'],-10/3)
        self.assertAlmostEqual(a.ce(.02,100,0,4000,1000)['rin_base'],106000.)

    def test_ports_and_followers(self):
        p=a.mos_bias();g=a.cg(p['gm'],p['go'],2000,10000,1000)
        vd=g['av'];idrain=-p['gm']+p['go']*(vd-1)
        self.assertAlmostEqual(vd*(1/2000+1/10000)+idrain,0.)
        self.assertAlmostEqual(1/g['rin'],-idrain)
        f=a.follower_bias();self.assertAlmostEqual(f['vs'],1000*f['id'])
        r=a.follower(f['gm'],f['go'],1000,10000);vs=r['av']
        self.assertAlmostEqual((.001+.0001+f['go'])*vs,f['gm']*(1-vs))
        b=a.bjt_bias();cb=a.cb(b['gm'],100,0,4000,10000)
        self.assertAlmostEqual(cb['ai_delivered'],100/101)
        ef=a.emitter_follower(.02,100,0,1000,rsource=10000)
        self.assertAlmostEqual(ef['rout'],1/(.001+101/15000))
        self.assertGreater(a.emitter_follower(.02,100,0,1000,rsource=10000)['rout'],a.emitter_follower(.02,100,0,1000)['rout'])

    def test_mirrors_kcl_and_slope(self):
        for vo in (1.2,2.,3.,4.):
            p=a.mirror(vo);self.assertAlmostEqual(a.mirror(p['vg'])['id'],.001)
            h=1e-5;slope=(a.mirror(vo+h)['id']-a.mirror(vo-h)['id'])/(2*h)
            self.assertAlmostEqual(slope,1/p['ro'],places=11)
        vg=a.mos_reference();q=a.cascode(2*vg);self.assertAlmostEqual(q['id'],.001)
        for vo in (3.2,2*vg,4.5):
            q=a.cascode(vo);i1=a.mos_point(q['vg'],q['vx'])['id'];i2=a.mos_point(q['vc']-q['vx'],vo-q['vx'])['id']
            self.assertAlmostEqual(i1,i2,places=14)
            h=1e-4;slope=(a.cascode(vo+h)['id']-a.cascode(vo-h)['id'])/(2*h)
            self.assertAlmostEqual(slope,1/q['rout'],places=11)
        for va in (None,100.):
            b=a.bjt_mirror(2,va=va)
            self.assertAlmostEqual(b['ic_ref']+b['ib_ref']+b['ib_out'],.001,places=14)
        self.assertAlmostEqual(a.bjt_mirror(2)['ratio'],100/102)
        with self.assertRaises(ValueError):a.mirror(.5)
        with self.assertRaises(ValueError):a.cascode(2.5)
        with self.assertRaises(ValueError):a.bjt_mirror(.2)

    def test_active_q_and_limits(self):
        p=a.active_load(rl=10000)
        n=a.mos_point(p['vg_n'],3.);m=a.mos_point(5-p['vg_p'],2.)
        self.assertAlmostEqual(n['id'],.001);self.assertAlmostEqual(m['id'],.001)
        self.assertGreater(3.,p['lower']);self.assertLess(3.,p['upper'])
        self.assertAlmostEqual(p['av'],-14.910539500031621)
        self.assertLess(abs(a.cs(.002,.00002,2000,10000)['av']),abs(a.cs(.002,.00002,2000,500)['av']))

    def test_invalid_before_cast_and_derived_failure(self):
        invalid=(True,complex(2,0),float('nan'),float('inf'),[2],[[2]],np.array([2.]),np.array(2+0j),np.array([2],dtype=object))
        for x in invalid:
          for fn in (lambda:a.mos_bias(vg=x),lambda:a.cs(x,.00002,2000),lambda:a.bjt_bias(beta=x),lambda:a.mirror(x)):
            with self.assertRaises((TypeError,ValueError)):fn()
        with self.assertRaises(ValueError):a.cs(1e308,1e308,1000,1e308)
        with self.assertRaises(ValueError):a.follower(1e308,1e308,1000)
        with self.assertRaises(ValueError):a.mos_point(2,.2)
        with self.assertRaises(ValueError):a.cs(.002,0,0)
        with self.assertRaises(RuntimeError):a.bisect(lambda x:x*x-2,1,2,budget=1)
        lo=1.;hi=math.nextafter(lo,2.)
        self.assertIn(a.bisect(lambda x:-1 if x==lo else 1,lo,hi),[lo,hi])

    def test_tiny_residual_brackets_and_actual_mirror_no_root(self):
        for sign in (1., -1.):
            with self.assertRaisesRegex(ValueError, 'root not bracketed'):
                a.bisect(lambda x:sign*1e-300*(x+1),0.,1.)
        with self.assertRaisesRegex(ValueError, 'root not bracketed'):
            a.bjt_mirror(1.,iref=1e-299,beta=.1,isat=1e-300)
        self.assertEqual(a.bisect(lambda x:1e-300*(x-.375),0.,1.),.375)
        self.assertEqual(a.bisect(lambda x:1e-300*x,0.,1.),0.)
        self.assertEqual(a.bisect(lambda x:1e-300*(x-1),0.,1.),1.)

    def test_import_and_cli_contract(self):
        script=Path(__file__).with_name('generate.py')
        with tempfile.TemporaryDirectory() as d:
            env=__import__('os').environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
            import_run=subprocess.run([sys.executable,'-B','-c',f'import sys;sys.path.insert(0,{str(script.parent)!r});import amp_lab,generate'],cwd=d,env=env,capture_output=True,text=True)
            self.assertEqual(import_run.returncode,0,import_run.stderr);self.assertEqual(list(Path(d).iterdir()),[])
            cli=subprocess.run([sys.executable,'-B',str(script)],cwd=d,env=env,capture_output=True,text=True)
            self.assertNotEqual(cli.returncode,0);self.assertEqual(list(Path(d).iterdir()),[])

if __name__=='__main__':unittest.main()
