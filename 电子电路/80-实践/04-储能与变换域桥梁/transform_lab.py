"""Teaching C/L state and Laplace benchmarks; finite SI inputs, no side effects."""
import math


def real(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("finite real required")
    if positive and value <= 0:
        raise ValueError("positive value required")
    return float(value)


def finite_result(values):
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("derived result outside numerical range")
    return values


def rc_state(time_s, source_V=1., initial_V=.4, r_ohm=1000., c_F=1e-6):
    t=real(time_s);u=real(source_V);v0=real(initial_V)
    r=real(r_ohm, True);c=real(c_F, True)
    if t < 0: raise ValueError("time must be nonnegative")
    tau=r*c
    if not 0 < tau < math.inf: raise ValueError("time constant outside range")
    decay=math.exp(-t/tau)
    rise=-math.expm1(-t/tau)
    # Separate weighted terms retain the initial state at zero and tiny t.
    v=v0*decay+u*rise
    current=(u/r-v0/r)*decay
    return finite_result({"v_V":v,"i_A":current,"q_C":c*v,"energy_J":.5*c*v*v})


def rl_state(time_s, source_V=1., initial_A=.02, r_ohm=100., l_H=.01):
    t=real(time_s);u=real(source_V);i0=real(initial_A)
    r=real(r_ohm, True);l=real(l_H, True)
    if t < 0: raise ValueError("time must be nonnegative")
    tau=l/r
    if not 0 < tau < math.inf: raise ValueError("time constant outside range")
    decay=math.exp(-t/tau)
    rise=-math.expm1(-t/tau)
    current=i0*decay+(u/r)*rise
    voltage=(u-r*i0)*decay
    return finite_result({"i_A":current,"vL_V":voltage,"energy_J":.5*l*current*current})


def modal(time_s, sigma_per_s, omega_rad_s):
    t=real(time_s);sigma=real(sigma_per_s);omega=real(omega_rad_s)
    if t < 0: raise ValueError("time must be nonnegative")
    exponent=sigma*t;phase=omega*t
    if not math.isfinite(exponent) or not math.isfinite(phase):
        raise ValueError("modal exponent or phase outside range")
    try: result=math.exp(exponent)*math.cos(phase)
    except OverflowError as exc: raise ValueError("mode overflow") from exc
    if not math.isfinite(result): raise ValueError("mode outside range")
    return result
