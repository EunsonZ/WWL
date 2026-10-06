"""Bounded synthetic 2x2 resistor networks and single constant-current LIF.
Pure standard-library import. SI throughout; no hardware simulation claim.
"""
import math
from numbers import Real


def real(x, lo, hi, name):
    if isinstance(x, bool) or not isinstance(x, Real):
        raise ValueError(name + ': finite real required')
    try:
        x = float(x)
    except (OverflowError, ValueError, TypeError) as e:
        raise ValueError(name + ': finite real required') from e
    if not math.isfinite(x) or not lo <= x <= hi:
        raise ValueError(name + ': out of bounded model range')
    return x


def matrix2(g):
    try:
        if len(g) != 2 or any(len(row) != 2 for row in g):
            raise ValueError('2x2 conductance required')
        return [[real(x, 0, 1e-3, 'G [S]') for x in row] for row in g]
    except TypeError as e:
        raise ValueError('2x2 conductance required') from e


def volts2(v):
    try:
        if len(v) != 2:
            raise ValueError('two row voltages required')
        return [real(x, -.2, .2, 'V [V]') for x in v]
    except TypeError as e:
        raise ValueError('two row voltages required') from e


def solve(a, b):
    """Scaled-pivot Gaussian elimination, internally fixed 8-node SPD network."""
    n = len(b)
    m = [list(a[i]) + [b[i]] for i in range(n)]
    for k in range(n):
        p = max(range(k, n), key=lambda i: abs(m[i][k]))
        if abs(m[p][k]) <= 1e-15 * max(abs(x) for row in a for x in row):
            raise ValueError('numerically unresolved matrix')
        m[k], m[p] = m[p], m[k]
        for i in range(k + 1, n):
            f = m[i][k] / m[k][k]
            for j in range(k, n + 1):
                m[i][j] -= f * m[k][j]
    x = [0.] * n
    for i in reversed(range(n)):
        x[i] = (m[i][n] - sum(m[i][j] * x[j] for j in range(i + 1, n))) / m[i][i]
    return x


def array(g, v, wire_ohm=0):
    """Rows i, columns j. r nodes 0..3; c nodes 4..7.
Ui--r--ri1--r--ri2; c1j--r--c2j--r--0. Cell Gij ri,j--ci,j.
Ideal wire=0 is analytic specialization; finite wire restricted to [1,1e6] ohm.
Iout positive from c2j into 0-V clamp. All clamps/drivers share reference 0.
"""
    g, v = matrix2(g), volts2(v)
    r = real(wire_ohm, 0, 1e6, 'wire [ohm]')
    if 0 < r < 1:
        raise ValueError('finite wire must be >= 1 ohm; 0 uses ideal specialization')
    if r == 0:
        out = [sum(g[i][j] * v[i] for i in range(2)) for j in range(2)]
        drivers = [sum(g[i]) * v[i] for i in range(2)]
        power = sum(g[i][j] * v[i]**2 for i in range(2) for j in range(2))
        return dict(output_A=out, driver_A=drivers, cell_W=power, wire_W=0., supplied_W=power, nodes_V=[v[0],v[0],v[1],v[1],0.,0.,0.,0.], residual_A=0.)
    a, b, edges = [[0.] * 8 for _ in range(8)], [0.] * 8, []
    def edge(x, y, conductance, known=None):
        a[x][x] += conductance
        if y is None:
            b[x] += conductance * known
        else:
            a[y][y] += conductance
            a[x][y] -= conductance
            a[y][x] -= conductance
        edges.append((x, y, conductance, known))
    for i in range(2):
        edge(2*i, None, 1/r, v[i])
        edge(2*i, 2*i+1, 1/r)
    for j in range(2):
        edge(4+j, 6+j, 1/r)
        edge(6+j, None, 1/r, 0.)
    for i in range(2):
        for j in range(2):
            edge(2*i+j, 4+2*i+j, g[i][j])
    x = solve(a, b)
    cell = sum(g[i][j]*(x[2*i+j]-x[4+2*i+j])**2 for i in range(2) for j in range(2))
    total = sum(q*(x[k]-(x[l] if l is not None else known))**2 for k,l,q,known in edges)
    driver = [(v[i]-x[2*i])/r for i in range(2)]
    residual = max(abs(sum(a[i][j]*x[j] for j in range(8))-b[i]) for i in range(8))
    return dict(output_A=[x[6+j]/r for j in range(2)], driver_A=driver, cell_W=cell, wire_W=total-cell, supplied_W=sum(v[i]*driver[i] for i in range(2)), nodes_V=x, residual_A=residual)


def differential(w, x, wire_ohm=0, base_S=1e-6, scale_S=1e-5, input_V=.1):
    base = real(base_S, 0, 1e-5, 'baseline S')
    scale = real(scale_S, 1e-8, 1e-4, 'scale S')
    voltage = real(input_V, 1e-4, .1, 'input scale V')
    try:
        if len(w) != 2 or any(len(row)!=2 for row in w) or len(x)!=2:
            raise ValueError('2x2 weights and two inputs required')
        w = [[real(t,-4,4,'weight') for t in row] for row in w]
        v = [voltage*real(t,-2,2,'input') for t in x]
    except TypeError as e:
        raise ValueError('invalid differential shape') from e
    p = array([[base+scale*max(t,0) for t in row] for row in w], v, wire_ohm)
    m = array([[base+scale*max(-t,0) for t in row] for row in w], v, wire_ohm)
    return dict(plus=p, minus=m, difference_A=[p['output_A'][j]-m['output_A'][j] for j in range(2)], core_W=p['supplied_W']+m['supplied_W'])


def quantize_current(i, bits=4, fullscale_A=20e-6):
    """Unipolar midrise, [0,FS] legal; ties upper, top endpoint last code."""
    if isinstance(bits,bool) or not isinstance(bits,int) or not 1<=bits<=16:
        raise ValueError('bits integer 1..16')
    fs = real(fullscale_A,1e-9,1e-2,'fullscale A')
    i = real(i,0,fs,'input A (no overload accepted)')
    n = 2**bits
    # Compare actual thresholds rather than trust division at a floating tie.
    code = 0
    while code+1 < n and i >= fs*(code+1)/n:
        code += 1
    return code, fs*(code+.5)/n


def drift(g, seconds, reference_s=1, exponent=.1):
    g = real(g,0,1e-3,'G S')
    t0 = real(reference_s,1e-3,1e6,'t0 s')
    t = real(seconds,t0,1e9,'t s')
    nu = real(exponent,0,1,'drift exponent')
    return g*math.exp(-nu*math.log(t/t0))


def energy(core_W, dwell_s=1e-6, adc_count=4, adc_J=50e-12, dac_count=2, dac_J=5e-12, digital_J=5e-12, calibration_J=100e-9, uses=1000, communication_J=0., idle_J=0.):
    def count(n,name,low=0):
        if isinstance(n,bool) or not isinstance(n,int) or not low<=n<=10**9:
            raise ValueError(name+' integer range')
        return n
    p = real(core_W,0,1,'power W')
    t = real(dwell_s,1e-9,1,'dwell s')
    ad = count(adc_count,'ADC count')*real(adc_J,0,1,'ADC J')
    da = count(dac_count,'DAC count')*real(dac_J,0,1,'DAC J')
    d = real(digital_J,0,1,'digital J')
    c = real(calibration_J,0,1,'calibration J')/count(uses,'uses',1)
    comm = real(communication_J,0,1,'communication J')
    idle = real(idle_J,0,1,'idle J')
    items = dict(array_J=p*t, ADC_J=ad,DAC_J=da,digital_J=d,calibration_J=c,communication_J=comm,idle_J=idle)
    return dict(components=items,total_J=sum(items.values()))


def lif(duration_s, current_A, initial_V=0., refractory_s=.001):
    """Fixed synthetic R=10 Mohm C=1 nF rest/reset=0 threshold=.01 V.
Constant input only; immediate reset then ideal clamp for refractory time.
At final-time spike, returns right-limit reset state. Max 10000 events.
"""
    duration = real(duration_s,0,1,'duration s')
    current = real(current_A,-1e-8,1e-8,'current A')
    v = real(initial_V,-.1,.01,'initial V')
    if v >= .01:
        raise ValueError('initial must be below threshold')
    refractory = real(refractory_s,0,.1,'refractory s')
    steady, tau, threshold = 1e7*current, .01, .01
    t, events, segments = 0., [], []
    while t < duration:
        crossing = math.inf if steady<=threshold else tau*math.log1p((threshold-v)/(steady-threshold))
        stop = min(duration,t+crossing)
        if stop<=t:
            raise ValueError('unrepresentable event time')
        end = v+(steady-v)*(-math.expm1(-(stop-t)/tau))
        segments.append((t,stop,v,end,'integrate'))
        if crossing > duration-t:
            v=end
            break
        t=stop
        events.append(t)
        if len(events)>10000:
            raise ValueError('event budget')
        v=0.
        hold=min(duration,t+refractory)
        if hold>t:
            segments.append((t,hold,0.,0.,'hold'))
        t=hold
    return dict(events_s=events,final_V=v,segments=segments,steady_V=steady,tau_s=tau)
