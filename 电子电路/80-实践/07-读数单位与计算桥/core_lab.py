"""SI quantities, analytic educational models; no hardware access or plotting on import."""
import math

def finite(x,name,positive=False):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or (positive and x<=0):
        raise ValueError(name+' must be finite'+(' and positive' if positive else ''))
    return float(x)

def divider(vs_v,r1_ohm,r2_ohm,rl_ohm=None):
    vs_v=finite(vs_v,'vs_v');r1_ohm=finite(r1_ohm,'r1_ohm',True);r2_ohm=finite(r2_ohm,'r2_ohm',True)
    lower=r2_ohm if rl_ohm is None else 1/(1/r2_ohm+1/finite(rl_ohm,'rl_ohm',True))
    return vs_v*lower/(r1_ohm+lower)

def source_ledger(e1_v=5,e2_v=1,r_ohm=4000):
    e1_v=finite(e1_v,'e1_v');e2_v=finite(e2_v,'e2_v');r_ohm=finite(r_ohm,'r_ohm',True)
    i=(e1_v-e2_v)/r_ohm
    return {'i_a_to_b_A':i,'source1_abs_W':-e1_v*i,'source2_abs_W':e2_v*i,'resistor_abs_W':r_ohm*i*i}

def rc_account(t_s,v0_v=.4,u_v=1,r_ohm=1000,c_f=1e-6):
    t_s=finite(t_s,'t_s');v0_v=finite(v0_v,'v0_v');u_v=finite(u_v,'u_v');r_ohm=finite(r_ohm,'r_ohm',True);c_f=finite(c_f,'c_f',True)
    if t_s<0:raise ValueError('t_s must be >=0')
    tau=r_ohm*c_f;a=u_v-v0_v;z=math.exp(-t_s/tau);v=u_v-a*z;i=a*z/r_ohm
    return {'v_V':v,'i_A':i,'p_source_abs_W':-u_v*i,'p_R_W':r_ohm*i*i,'p_C_W':v*i,'source_delivered_J':u_v*c_f*a*(1-z),'R_loss_J':.5*c_f*a*a*(1-z*z),'C_delta_J':.5*c_f*(v*v-v0_v*v0_v)}

def pulse_voltage(t_s,v0_v=.4,c_f=1e-6):
    t_s=finite(t_s,'t_s');v0_v=finite(v0_v,'v0_v');c_f=finite(c_f,'c_f',True)
    if not 0<=t_s<=.003:raise ValueError('pulse domain 0..0.003 s')
    q=.0002*min(t_s,.001)-.0001*min(max(t_s-.001,0),.001)
    return v0_v+q/c_f

def pulse_current(t_s):
    t_s=finite(t_s,'t_s')
    if not 0<=t_s<=.003:raise ValueError('pulse domain 0..0.003 s')
    return .0002 if t_s<.001 else -.0001 if t_s<.002 else 0

def probe_h(f_hz,rth_ohm=100000,rp_ohm=1000000,cp_f=100e-12):
    f_hz=finite(f_hz,'f_hz');rth_ohm=finite(rth_ohm,'rth_ohm',True);rp_ohm=finite(rp_ohm,'rp_ohm',True);cp_f=finite(cp_f,'cp_f',True)
    if f_hz<0:raise ValueError('f_hz must be >=0')
    return 1/(1+rth_ohm/rp_ohm+2j*math.pi*f_hz*rth_ohm*cp_f)

def amplitude_db(ratio):return 20*math.log10(finite(ratio,'amplitude ratio',True))
def power_db(ratio):return 10*math.log10(finite(ratio,'power ratio',True))
def decay_time(tau_s,remaining):
    tau_s=finite(tau_s,'tau_s',True);remaining=finite(remaining,'remaining',True)
    if remaining>1:raise ValueError('remaining must <=1')
    return -tau_s*math.log(remaining)

def two_nodes(g_ground_s=.0005,g_link_s=.001,b_a_A=.001,b_b_A=0):
    # Symmetric resistive two-node model; direct 2x2 solve without explicit inverse array.
    g=finite(g_ground_s,'g_ground_s',True);h=finite(g_link_s,'g_link_s',True);ba=finite(b_a_A,'b_a_A');bb=finite(b_b_A,'b_b_A')
    common=(ba+bb)/(2*g);difference=(ba-bb)/(2*(g+2*h))
    return common+difference,common-difference

def midpoint(fn,a,b,n=10000):
    if isinstance(n,bool) or not isinstance(n,int) or n<=0:raise ValueError('n must positive int')
    step=(b-a)/n
    return sum(fn(a+(k+.5)*step) for k in range(n))*step
