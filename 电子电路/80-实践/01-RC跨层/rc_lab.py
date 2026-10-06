"""U1: scalar, time-invariant loaded RC model; CPU reference, SI units.

u[k] is held on [k*ts,(k+1)*ts). Output has n+1 states, including v0.
No SPICE, hardware, ADC or real-time scheduling is represented here.
"""
from dataclasses import dataclass
import math
import numpy as np


def finite_scalar(name, value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def vector(name, values):
    a = np.asarray(values, dtype=float)
    if a.ndim != 1 or not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be a finite one-dimensional vector")
    return a


@dataclass(frozen=True)
class RC:
    r: float = 1000.0
    c: float = 1e-6
    rs: float = 0.0
    rl: float = math.inf

    def __post_init__(self):
        for name in ("r", "c", "rs"):
            object.__setattr__(self, name, finite_scalar(name, getattr(self, name)))
        if self.r <= 0 or self.c <= 0 or self.rs < 0:
            raise ValueError("r,c must be positive; rs must be nonnegative")
        load = float(self.rl)
        if load <= 0 or math.isnan(load) or load == -math.inf:
            raise ValueError("rl must be positive, possibly +infinity")
        object.__setattr__(self, "rl", load)
        if not math.isfinite(self.series) or not (0 < self.tau < math.inf):
            raise ValueError("derived resistance/time constant is not representable")

    @property
    def series(self):
        return self.r + self.rs

    @property
    def gain(self):
        # This ratio avoids the product Rt*RL overflowing.
        return 1.0 if math.isinf(self.rl) else 1.0 / (1.0 + self.series / self.rl)

    @property
    def tau(self):
        return (self.series * self.gain) * self.c

    def step(self, times, level=1.0, v0=0.0):
        t = vector("times", times)
        if np.any(t < 0) or np.any(np.diff(t) < 0):
            raise ValueError("times must be nonnegative and nondecreasing")
        level, v0 = finite_scalar("level", level), finite_scalar("v0", v0)
        # expm1 preserves a tiny positive step, where 1-exp(-x) cancels.
        with np.errstate(over="ignore"):
            change = -np.expm1(-t / self.tau)
        with np.errstate(over="ignore", invalid="ignore"):
            out = v0 * (1.0 - change) + self.gain * level * change
        if not np.all(np.isfinite(out)):
            raise ValueError("response overflow")
        return out

    def frequency(self, hz):
        f = vector("hz", hz)
        if np.any(f < 0):
            raise ValueError("frequency must be nonnegative")
        with np.errstate(over="ignore", invalid="ignore"):
            omega_tau = (2 * np.pi * self.tau) * f
        if not np.all(np.isfinite(omega_tau)):
            raise ValueError("frequency product overflow")
        return self.gain / (1.0 + 1j * omega_tau)

    def coefficients(self, ts, method="exact"):
        ts = finite_scalar("ts", ts)
        if ts <= 0:
            raise ValueError("ts must be positive")
        x = ts / self.tau
        if method == "exact":
            a, b = math.exp(-x), -math.expm1(-x) * self.gain
        elif method == "euler":
            a, b = 1.0 - x, x * self.gain
        else:
            raise ValueError("method must be exact or euler")
        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError("coefficient overflow")
        return a, b

    def simulate(self, inputs, ts, v0=0.0, method="exact", quantizer=None):
        u = vector("inputs", inputs)
        v0 = finite_scalar("v0", v0)
        a, b = self.coefficients(ts, method)
        out = np.empty(u.size + 1)
        out[0] = v0 if quantizer is None else quantizer(v0)
        if quantizer is not None:
            a, b = quantizer(a), quantizer(b)
        for k, uk in enumerate(u):
            uk = uk if quantizer is None else quantizer(uk)
            nxt = a * out[k] + b * uk
            if not math.isfinite(nxt):
                raise ValueError("state overflow")
            out[k + 1] = nxt if quantizer is None else quantizer(nxt)
        return out


@dataclass(frozen=True)
class QFormat:
    """Reference Q-format emulation, not an integer DSP implementation.

    Signed two's-complement range; round-to-nearest ties-to-even; saturate.
    A multiply-add is computed in float64 then rounded once. Inputs, initial
    state and coefficients are rounded separately. No wraparound is used.
    """
    total_bits: int = 16
    fractional_bits: int = 14

    def __post_init__(self):
        if (type(self.total_bits) is not int or type(self.fractional_bits) is not int
                or not 2 <= self.total_bits <= 32
                or not 0 <= self.fractional_bits < self.total_bits):
            raise ValueError("require integer 2<=total_bits<=32 and 0<=fractional_bits<total_bits")

    @property
    def quantum(self):
        return 2.0 ** -self.fractional_bits

    def __call__(self, x):
        x = finite_scalar("fixed-point input", x)
        low = -(2 ** (self.total_bits - 1))
        high = 2 ** (self.total_bits - 1) - 1
        # Clip before scaling to avoid overflow on extreme finite inputs.
        x = min(high * self.quantum, max(low * self.quantum, x))
        return min(high, max(low, round(x / self.quantum))) * self.quantum
