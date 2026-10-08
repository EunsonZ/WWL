"""Bounded CPU contracts. Import uses only the standard library and writes nothing."""
import math
import numbers
import bisect
from itertools import islice


def bounded(values, limit=4096):
    try:
        data = tuple(islice(iter(values), limit+1))
    except TypeError as exc:
        raise ValueError("finite iterable required") from exc
    if len(data)>limit:
        raise ValueError("item budget exceeded")
    return data



def real(x, name, lo, hi):
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        raise ValueError(name + ': real scalar required')
    x = float(x)
    if not math.isfinite(x) or not lo <= x <= hi:
        raise ValueError(name + ': outside finite domain')
    return x


def integer(x, name, lo, hi):
    if isinstance(x, bool) or not isinstance(x, numbers.Integral) or not lo <= x <= hi:
        raise ValueError(name + ': bounded integer required')
    return int(x)


def adc(v):
    """Ideal 12-bit floor quantizer; endpoint Vref has a distinct clipped flag."""
    v = real(v, 'voltage V', 0, 3.3)
    delta = 3.3 / 4096
    # The public bins are defined by these computed floating thresholds.  Select
    # with the same thresholds, rather than a separately rounded v/delta.
    edges = tuple(k*delta for k in range(4097))
    code = min(4095, bisect.bisect_right(edges, v)-1)
    return {'code': code, 'lo_V': edges[code], 'hi_V': edges[code+1],
            'mid_V': (code+.5)*delta, 'upper_endpoint': v == 3.3}


def schedule(blocks=8, block_size=4, period_ns=1000000, jitter_ns=300000, cpu_ns=2000000):
    """Two DMA buffers; ready=(k+1)B Ts, reuse=(k+2)B Ts. Serial CPU."""
    n = integer(blocks, 'blocks', 1, 256)
    b = integer(block_size, 'block size', 1, 4096)
    t = integer(period_ns, 'period ns', 1, 10**9)
    j = integer(jitter_ns, 'IRQ delay ns', 0, 10**9)
    c = integer(cpu_ns, 'CPU WCET ns', 1, 10**9)
    if n*b > 262144:
        raise ValueError('sample budget')
    rows, finish = [], 0
    for k in range(n):
        ready = (k+1)*b*t
        irq = ready+j
        start = max(irq, finish)
        finish = start+c
        reuse = (k+2)*b*t
        rows.append(dict(block=k, epoch=0, slot=k%2, start_index=k*b,
                         first_sample_ns=k*b*t, last_sample_ns=(k*b+b-1)*t,
                         ready_ns=ready, irq_ns=irq, cpu_start_ns=start,
                         cpu_finish_ns=finish, reuse_ns=reuse,
                         slack_ns=reuse-finish, status='valid' if finish <= reuse else 'discard'))
    return rows


class OwnedRing:
    """Software ownership oracle, NOT a mechanism that stalls circular DMA hardware."""
    def __init__(self, capacity=2):
        self.capacity = integer(capacity, 'capacity', 1, 16)
        self.epoch = 0
        self.generation = 0
        self.slots = [None]*self.capacity

    def publish(self, slot, values):
        s = integer(slot, 'slot', 0, self.capacity-1)
        data = tuple(integer(v, 'code', 0, 4095) for v in bounded(values))
        if not 1 <= len(data) <= 4096:
            raise ValueError('block size')
        if self.slots[s] is not None:
            raise OverflowError('busy slot; stop/resynchronize producer')
        self.generation += 1
        token = (self.epoch, self.generation, s)
        self.slots[s] = ('READY', token, data)
        return token

    def _token(self, token):
        # Validate every field BEFORE tuple equality or any state access/change.
        if not isinstance(token, tuple) or len(token) != 3:
            raise ValueError('token')
        epoch = integer(token[0], 'token epoch', 0, self.epoch)
        generation = integer(token[1], 'token generation', 1, self.generation)
        slot = integer(token[2], 'slot', 0, self.capacity-1)
        return epoch, generation, slot

    def take(self, token):
        token = self._token(token)
        s = token[2]
        row = self.slots[s]
        if row is None or row[1] != token or row[0] != 'READY':
            raise ValueError('stale/not ready token')
        self.slots[s] = ('CPU', token, row[2])
        return row[2]

    def release(self, token):
        token = self._token(token)
        s = token[2]
        if self.slots[s] is None or self.slots[s][:2] != ('CPU', token):
            raise ValueError('stale/not owned token')
        self.slots[s] = None

    def reset(self):
        self.epoch += 1
        self.slots = [None]*self.capacity


class CountFilter:
    """Signed count FIR [1,2,1]/4 and IIR (3s+q)/4; one ties-even round each."""
    def __init__(self, epoch=0, origin=0):
        self.epoch = integer(epoch, 'epoch', 0, 10**9)
        self.next = integer(origin, 'origin', 0, 10**12)
        self.history = []
        self.state = 0

    def process(self, codes, start_index, epoch):
        # Validate all fields before mutating memory.
        e = integer(epoch, 'epoch', 0, 10**9)
        i = integer(start_index, 'start index', 0, 10**12)
        vals = tuple(integer(c, 'code', 0, 4095) for c in bounded(codes))
        if not 1 <= len(vals) <= 4096 or i+len(vals) > 10**12:
            raise ValueError('block budget')
        if (e, i) != (self.epoch, self.next):
            raise ValueError('gap/epoch mismatch; explicit reset required')
        out = []
        for code in vals:
            q = code-2048
            old1 = self.history[-1] if self.history else 0
            old2 = self.history[-2] if len(self.history)>1 else 0
            fir = round((q+2*old1+old2)/4)
            self.state = round((3*self.state+q)/4)
            out.append((fir, self.state, len(self.history)>=2))
            self.history = (self.history+[q])[-2:]
        self.next += len(vals)
        return out


def fit_calibration(codes, volts, temps=None):
    """OLS with exact predictors and iid homoscedastic voltage errors, max 4096 rows."""
    import numpy as np
    c = [integer(x, 'code', 0, 4095) for x in bounded(codes)]
    v = [real(x, 'reference V', -10, 10) for x in bounded(volts)]
    if len(c) != len(v) or not 3 <= len(c) <= 4096:
        raise ValueError('row budget/length')
    cols = [np.ones(len(c)), np.asarray(c)/4096]
    if temps is not None:
        tt = [real(x, 'temperature C', -50, 150) for x in bounded(temps)]
        if len(tt) != len(c) or len(c) < 4:
            raise ValueError('temperature rows')
        cols.append((np.asarray(tt)-25)/20)
    x = np.column_stack(cols)
    _, singular, vh = np.linalg.svd(x, full_matrices=False)
    if singular[-1] <= singular[0]*1e-10:
        raise ValueError('unidentifiable/ill-conditioned design')
    beta, _, _, _ = np.linalg.lstsq(x, v, rcond=None)
    scale = np.array([1, 1/4096] + ([1/20] if temps is not None else []))
    physical = beta*scale
    if physical[1] <= 0:
        raise ValueError('nonpositive gain outside ADC calibration model')
    residual = np.asarray(v)-x@beta
    dof = len(c)-len(beta)
    sigma2 = float(residual@residual/dof)
    cov = (vh.T @ np.diag(1/singular**2) @ vh)*sigma2
    cov *= scale[:, None]*scale[None, :]
    return dict(coefficients=physical.tolist(), residual_V=residual.tolist(),
                sigma_V=math.sqrt(sigma2), covariance=cov.tolist(), dof=dof,
                design_condition=float(singular[0]/singular[-1]))


def held_matrix(tau_p=.02, tau_a=.005, period=.01, gain=3):
    """State [plant V, actuator V, previous command V]; u[k]=-K*x[k]."""
    ptime = real(tau_p, 'tau plant s', 1e-6, 1e3)
    atime = real(tau_a, 'tau actuator s', 1e-6, 1e3)
    t = real(period, 'period s', 1e-8, 1)
    k = real(gain, 'gain V/V', 0, 100)
    r, s = t/ptime, t/atime
    if not 1e-6 <= min(r,s) <= max(r,s) <= 20:
        raise ValueError('dimensionless step outside numeric contract')
    p, q = math.exp(-r), math.exp(-s)
    z = s-r
    phi = 1 if z == 0 else -math.expm1(-z)/z
    coupling = p*r*phi
    bx = -math.expm1(-r)-coupling
    ba = -math.expm1(-s)
    return [[p, coupling, bx], [0, q, ba], [-k, 0, 0]]


def control_trace(steps=100, **params):
    n = integer(steps, 'steps', 1, 4096)
    m = held_matrix(**params)
    state = [1., 0., 0.]
    rows = [state[:]]
    for _ in range(n):
        state = [sum(a*b for a,b in zip(row,state)) for row in m]
        if any(not math.isfinite(x) or abs(x)>1e6 for x in state):
            raise OverflowError('linear model state budget exceeded')
        rows.append(state[:])
    return rows


def pullup(r=2200, c=100e-12):
    r = real(r, 'pullup ohm', 100, 1e6)
    c = real(c, 'bus capacitance F', 1e-12, 1e-6)
    return -math.log(.3/.7)*r*c
