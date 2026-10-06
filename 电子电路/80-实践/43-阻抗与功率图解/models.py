"""Four fixed sinusoidal series-network examples, SI and RMS throughout."""
import cmath
import math


def cases():
    """Return fresh fixed examples. No arbitrary-network or transient solver."""
    result = []
    for name, inductance, capacitance in (
        ('R', 0.0, None), ('RL', 0.01, None),
        ('RC', 0.0, 100e-6), ('RLC', 0.01, 200e-6),
    ):
        resistance, omega, voltage = 10.0, 1000.0, complex(10.0)
        zr, zl = complex(resistance), complex(0, omega * inductance)
        zc = complex(0) if capacitance is None else 1 / (1j * omega * capacitance)
        z = zr + zl + zc
        current = voltage / z
        power = voltage * current.conjugate()
        result.append(dict(name=name, R_ohm=resistance, L_H=inductance,
                           C_F=capacitance, omega_rad_s=omega, V_rms=voltage,
                           ZR_ohm=zr, ZL_ohm=zl, ZC_ohm=zc, Z_ohm=z,
                           I_rms=current, VR_rms=zr * current,
                           VL_rms=zl * current, VC_rms=zc * current,
                           S_VA=power, P_W=power.real, Q_var=power.imag,
                           apparent_VA=abs(power)))
    return result


def waveform(case, count=4096):
    """Fixed periodic data on [0,T); no repeated endpoint in the mean."""
    if isinstance(count, bool) or not isinstance(count, int) or not 256 <= count <= 65536:
        raise ValueError('count must be an integer from 256 through 65536')
    # The supported case is one of our fresh fixed records, not arbitrary inputs.
    if case not in cases():
        raise ValueError('case must equal one of the four fixed case records')
    omega = case['omega_rad_s']
    rows = []
    for k in range(count):
        theta = 2 * math.pi * k / count
        rotation = cmath.exp(1j * theta)
        v = math.sqrt(2) * (case['V_rms'] * rotation).real
        i = math.sqrt(2) * (case['I_rms'] * rotation).real
        vr, vl, vc = [math.sqrt(2) * (case[n] * rotation).real
                      for n in ('VR_rms', 'VL_rms', 'VC_rms')]
        rows.append(dict(t_s=theta / omega, v_V=v, i_A=i, p_W=v * i,
                         vR_V=vr, vL_V=vl, vC_V=vc,
                         pR_W=vr * i, pL_W=vl * i, pC_W=vc * i))
    return rows
