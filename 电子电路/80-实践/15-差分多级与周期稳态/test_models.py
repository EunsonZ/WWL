import unittest
import math
import importlib
import sys
import subprocess
from pathlib import Path
import models as m

class Models(unittest.TestCase):
    def test_invalid_scalar(self):
        for v in (True,1j,'2',[1],[[1]],float('nan'),float('inf')):
            for fun,args in ((m.mos_steering,(v,.001,.002)),(m.bjt_steering,(v,.001,.026)),(m.coupling,(v,2,1,100,2000,10000,1e-6)),(m.class_b,(v,5,8))):
                with self.assertRaises((ValueError,TypeError)): fun(*args)
        with self.assertRaises(ValueError): m.differential(.001,2000,100000,ro=math.inf)
        with self.assertRaises((OverflowError,ValueError)): m.cgd_coefficients(1e300,1e300,1e300,1,1,1)
        with self.assertRaises(OverflowError): m.legacy_periodic(0,.1,1e300,1e300)
    def test_import_pure(self):
        code="import models,build; import sys; assert not any(x.startswith(('numpy','matplotlib','cairosvg','PIL')) for x in sys.modules)"
        r=subprocess.run([sys.executable,'-B','-c',code],cwd=Path(__file__).parent,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(r.stdout,'')
    def test_mos_independent(self):
        # independently reconstruct both overdrives from returned currents
        for vd in (-.9,-.2,0,.2,.9):
            i1,i2=m.mos_steering(vd,.001,.002)
            self.assertAlmostEqual(i1+i2,.001,14)
            self.assertAlmostEqual(math.sqrt(2*i1/.002)-math.sqrt(2*i2/.002),vd,13)
        self.assertEqual(m.mos_steering(2,.001,.002),(.001,0))
    def test_bjt_ratio(self):
        vt=.02585; vd=vt*math.log(100); i1,i2=m.bjt_steering(vd,.001,vt)
        self.assertAlmostEqual(i1/i2,100,10); self.assertAlmostEqual(i1+i2,.001,14)
    def test_three_node(self):
        import numpy as np
        gm=.0014; rd=2000; rt=1e5; ro=5e4; gd=1/rd; go=1/ro
        matrix=np.array([[gd+go,0,-gm-go],[0,gd+go,-gm-go],[-go,-go,2*(gm+go)+1/rt]])
        d=np.linalg.solve(matrix,[-gm/2,gm/2,0]); c=np.linalg.solve(matrix,[-gm,-gm,2*gm])
        ans=m.differential(gm,rd,rt,ro)
        self.assertAlmostEqual(d[0]-d[1],ans['ad_differential'],12)
        self.assertAlmostEqual(c[0],ans['ac_single'],12); self.assertAlmostEqual(c[0]-c[1],0,12)
    def test_cascade(self):
        # resistor-divider KCL equations independent of multiplication implementation
        v2=(-20/20000)/(1/20000+1/5000); out=(-10*v2/1000)/(1/1000+1/10000)
        self.assertAlmostEqual(out,m.cascade(-20,20000,5000,-10,1000,10000),12)
    def test_cascode_nodes(self):
        import numpy as np
        gm=.001; go=1/50000; load=20000
        # independent KCL at x and output for input 1 V
        mat=np.array([[gm+2*go,-go],[-gm-go,go+1/load]])
        vx,vo=np.linalg.solve(mat,[-gm,0])
        rout,gme,gain=m.cascode(gm,gm,50000,50000,load)
        self.assertAlmostEqual(vo,gain,11); self.assertAlmostEqual(rout,2600000,5)
    def test_cgd_matrix(self):
        import numpy as np
        rg=1e4; ro=1e4; gm=.001; cgs=20e-12; cgd=2e-12; co=10e-12
        for f in (0,1e3,3e5,3e6,8e7):
            s=2j*math.pi*f
            mat=np.array([[1/rg+s*(cgs+cgd),-s*cgd],[gm-s*cgd,1/ro+s*(co+cgd)]])
            vg,vo=np.linalg.solve(mat,[1/rg,0]); h=m.cgd_response_s(s,rg,ro,gm,cgs,cgd,co)
            self.assertAlmostEqual(abs(vo-h),0,11)
        self.assertEqual(m.cgd_response_s(gm/cgd,rg,ro,gm,cgs,cgd,co),0j)
        b1,b2,t1,t2,z=m.cgd_coefficients(rg,ro,gm,cgs,cgd,co)
        self.assertAlmostEqual(t1+t2,b1,18); self.assertAlmostEqual(t1*t2,b2,24)
    def test_b_power_integrals(self):
        n=16384; rail=5; amp=4; load=8
        waves=[amp*math.sin(2*math.pi*k/n) for k in range(n)]
        pout=math.fsum(v*v/load for v in waves)/n
        pdc=rail*math.fsum(abs(v)/load for v in waves)/n
        a,b,eta=m.class_b(amp,rail,load)
        self.assertAlmostEqual(a,pout,12); self.assertAlmostEqual(b,pdc,7)
        self.assertAlmostEqual(m.class_b(5,5,8)[2],math.pi/4,14)
    def test_crossover_fundamental(self):
        th=math.asin(.6); analytic=(math.pi-2*th+math.sin(2*th)-2.4*math.cos(th))/math.pi
        b1,b3,b5=m.harmonics(1,.6,32768)
        self.assertAlmostEqual(b1,analytic,8); self.assertGreater(abs(b3),.01)
        self.assertEqual(m.harmonics(1,0,2048)[0],1.)
    def test_thermal_equilibrium(self):
        iq,p,dt,loop=m.thermal_idle(.01,5,1,.002,10)
        self.assertAlmostEqual(iq,.01+.002*dt,14); self.assertAlmostEqual(dt,10*2*5*iq,14)
        with self.assertRaises(ValueError): m.thermal_idle(.01,5,.1,.002,10)
    def test_coupling_state_and_ode(self):
        args=(2,1,100,2000,10000,1e-6); vc,vb=m.coupling(0,*args,initial=0)
        self.assertEqual(vc,0); self.assertAlmostEqual(vb,5/3,13)
        for t in (.001,.004,.008):
            h=1e-8; v,_=m.coupling(t,*args); vp,_=m.coupling(t+h,*args); vm,_=m.coupling(t-h,*args)
            e=2+math.sin(2*math.pi*100*t)
            self.assertAlmostEqual((vp-vm)/(2*h),(e-v)/.012,5)
        n=4096
        avg=math.fsum(m.coupling(k/(100*n),*args)[1] for k in range(n))/n
        self.assertAlmostEqual(avg,0,13)
    def test_periodic_closure(self):
        vals,cycles,res=m.periodic_rk4(.35,100,1e-6)
        self.assertLess(res,1e-8); self.assertLess(cycles,200)
        err=max(abs(v-m.legacy_periodic(k/(100*len(vals)),.35,100,1e-6)[0]) for k,v in enumerate(vals))
        self.assertLess(err,1e-8)
        self.assertGreater(min(m.legacy_periodic(k/(100*4096),.35,100,1e-6)[2] for k in range(4096)),0)
        with self.assertRaises(RuntimeError): m.periodic_rk4(.35,100,1e-6,max_cycles=2)
        with self.assertRaises(TypeError): m.periodic_rk4(.35,100,1e-6,steps=True)
        with self.assertRaises(ValueError): m.periodic_rk4(.35,100,1e-6,steps=1000000,max_cycles=2)

    def test_stable_minority_currents(self):
        from decimal import Decimal, localcontext
        with localcontext() as ctx:
            ctx.prec=90
            v=math.nextafter(1.,0.); d=Decimal.from_float(v)
            z=(Decimal('.5')-d*d/4).sqrt()
            reference=float(Decimal('.001')*(z-d/2)**2)
            for sign in (-1,1):
                currents=m.mos_steering(sign*v,.001,.002)
                self.assertAlmostEqual(min(currents)/reference,1.,14)
                self.assertAlmostEqual(sum(currents),.001,14)
            vd=1.; vt=.02585
            ratio=Decimal.from_float(vd)/Decimal.from_float(vt)
            reference=float(Decimal.from_float(.001)/(1+ratio.exp()))
            for sign in (-1,1):
                self.assertAlmostEqual(min(m.bjt_steering(sign*vd,.001,vt))/reference,1.,13)
    def test_stable_initial_state(self):
        # Original-dimensional Taylor coefficients: v'= (E0 + A sin(wt)-v)/tau.
        from decimal import Decimal, localcontext
        with localcontext() as ctx:
            ctx.prec=90
            t=Decimal('1e-30'); tau=Decimal('.012'); e0=Decimal('1e16'); initial=Decimal.from_float(.4)
            slope=(e0-initial)/tau
            curvature=(Decimal.from_float(2*math.pi*100)-slope)/tau
            reference=float(initial+slope*t+curvature*t*t/2)
            self.assertEqual(m.coupling(0,1e16,1,100,2000,10000,1e-6,initial=.4)[0],.4)
            self.assertAlmostEqual(m.coupling(float(t),1e16,1,100,2000,10000,1e-6,initial=.4)[0],reference,15)
    def test_power_underflow_efficiency(self):
        pout,pdc,eta=m.class_b(1e-100,5,1e200)
        self.assertGreater(eta,0); self.assertAlmostEqual(eta/(math.pi/4*1e-100/5),1,14)
        self.assertEqual(m.class_b(0,5,8),(0.,0.,0.))
    def test_mismatch_branch_contract(self):
        for delta in (.1,-.3):
            ans=m.differential(.001,2000,100000,mismatch=delta)
            self.assertAlmostEqual(ans['ad_single'],-.001*2000*(1+delta)/2,14)
            self.assertAlmostEqual(ans['ac_single'],-.001*2000*(1+delta)/(1+2*.001*100000),14)
            self.assertEqual(ans['ad_single_nominal'],-1.)
            self.assertAlmostEqual(ans['cmrr_single'],abs(ans['ad_single']/ans['ac_single']),12)
    def test_periodic_rejects_slow_and_precision_domains(self):
        for c in (1e4,1e7,1e16):
            with self.assertRaisesRegex(ValueError,'supported domain'): m.periodic_rk4(.35,100,c)
        with self.assertRaises(ValueError): m.periodic_rk4(.35,100,1e-6,tol=1e-15)

    def test_bjt_scaled_exponent(self):
        from decimal import Decimal, localcontext
        with localcontext() as ctx:
            ctx.prec=90
            ref=float(Decimal.from_float(1e308)/(1+Decimal(750).exp()))
        for sign in (-1,1):
            ans=m.bjt_steering(sign*750,1e308,1)
            self.assertGreater(min(ans),0); self.assertAlmostEqual(min(ans)/ref,1,12)
    def test_coupling_sine_startup_series(self):
        # Independent original-dimensional derivative recurrence at t=0.
        from decimal import Decimal, localcontext
        with localcontext() as ctx:
            ctx.prec=90; tau=Decimal('.012'); w=Decimal.from_float(2*math.pi*100)
            for value in (1e-30,1e-20,1e-18,1e-12,1e-6):
                t=Decimal.from_float(value); derivative=Decimal(0); total=Decimal(0); factorial=Decimal(1)
                for n in range(1,30):
                    forcing=Decimal(0) if (n-1)%2==0 else (-1)**((n-2)//2)*w**(n-1)
                    derivative=(forcing-derivative)/tau
                    factorial*=n; total+=derivative*t**n/factorial
                ref=float(total)
                for sign in (-1,1):
                    vc,vb=m.coupling(value,0,sign,100,2000,10000,1e-6,initial=0)
                    self.assertGreater(sign*vc,0); self.assertAlmostEqual(vc/(sign*ref),1,12)
    def test_coupling_periodic_ac_independent_dc(self):
        # Independently evaluate complex voltage divider H(jw).
        w=2*math.pi*100; zc=1/(1j*w*1e-6); transfer=10000/(2000+zc+10000)
        for t in (0,.001,.0025):
            expected=(transfer*complex(math.cos(w*t),math.sin(w*t))).imag
            for e0 in (0,1e16,-1e16):
                vc,vb=m.coupling(t,e0,1,100,2000,10000,1e-6)
                self.assertAlmostEqual(vb,expected,14)
        # No forcing: exact initial-state exponential response.
        vc,vb=m.coupling(.001,0,0,100,2000,10000,1e-6,initial=.4)
        self.assertAlmostEqual(vc,.4*math.exp(-.001/.012),14)
        self.assertAlmostEqual(vb,-5/6*vc,14)

    def test_coupling_large_weights_and_scaled_decay(self):
        # High-pass coordinate from independently scaled complex impedances.
        w=2*math.pi*100
        for c in (1e100,1e140):
            x=w*c*12000; phase=w*.001
            expected_load=5/6*1e-100*((complex(0,x)/(1+complex(0,x)))*complex(math.cos(phase),math.sin(phase))).imag
            expected_state=1e-100/x*(math.sin(phase)/x-math.cos(phase))/(1+1/(x*x))
            vc,vb=m.coupling(.001,0,1e-100,100,2000,10000,c)
            self.assertGreater(vb,0); self.assertAlmostEqual(vb/expected_load,1,13)
            self.assertAlmostEqual(vc/expected_state,1,13)
            # Original convolution to first order in u (u below 1e-100);
            # relative neglected damping below 1e-100.
            reference=1e-100/x*2*math.sin(phase/2)**2
            vc,vb=m.coupling(.001,0,1e-100,100,2000,10000,c,initial=0)
            self.assertAlmostEqual(vc/reference,1,13)
        from decimal import Decimal,localcontext
        with localcontext() as ctx:
            ctx.prec=110; reference=float(Decimal.from_float(1e308)*(-Decimal(750)).exp())
        for sign in (-1,1):
            vc,vb=m.coupling(9,0,0,100,2000,10000,1e-6,initial=sign*1e308)
            self.assertAlmostEqual(vc/(sign*reference),1,12)
            self.assertAlmostEqual(vb/(-sign*reference*5/6),1,12)
            vc,vb=m.coupling(9,sign*1e308,0,100,2000,10000,1e-6,initial=0)
            self.assertAlmostEqual(vb/(sign*reference*5/6),1,12)
    def test_coupling_dimensionless_edges(self):
        # Original complex impedance divider at the supported x edges.
        w=2*math.pi*100
        for x in (1.00000000000001e-150,9.9999999999999e149):
            c=x/(w*12000)
            zc=1/(1j*w*c); load=10000/(2000+zc+10000)
            state=zc/(2000+zc+10000)
            vc,vb=m.coupling(0,0,1,100,2000,10000,c)
            self.assertAlmostEqual(vc/state.imag,1,13)
            self.assertAlmostEqual(vb/load.imag,1,13)
        for ratio in (1e12,1e-12):
            rs=10000*ratio; rl=10000; c=1e-6
            zc=1/(1j*w*c); expected=(rl/(rs+zc+rl)).imag
            self.assertAlmostEqual(m.coupling(0,0,1,100,rs,rl,c)[1]/expected,1,13)

    def test_coupling_declared_domain(self):
        for c in (1e145,1e-160):
            with self.assertRaisesRegex(ValueError,'domain'): m.coupling(.001,0,1,100,2000,10000,c)
        with self.assertRaises(ValueError): m.coupling(1e20,0,1,100,2000,10000,1e-6)
        with self.assertRaises(ValueError): m.coupling(1,0,1,100,1e20,1,1e-6)

if __name__=='__main__': unittest.main()
