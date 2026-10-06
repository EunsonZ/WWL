"""SI-only real storage models. Import has no plotting or output side effects."""
from __future__ import annotations

import math
import numbers


def real(value, name):
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"{name} must be a finite real number")
    try:
        v = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} is outside binary64") from exc
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite")
    return v


def positive(value, name, *, allow_zero=False):
    value = real(value, name)
    if value < 0 or (not allow_zero and value == 0):
        raise ValueError(f"{name} must be {'nonnegative' if allow_zero else 'positive'}")
    return value


def finite_result(values):
    if any(not math.isfinite(x) for x in values):
        raise ValueError("derived value outside binary64")
    return values


def rc_interval(initial_V, duration_s, source_V, source_R_ohm, C_F, load_R_ohm=None):
    """One constant-input interval; None denotes absent load, not a numerical infinity."""
    v0 = real(initial_V, "initial_V")
    t = positive(duration_s, "duration_s", allow_zero=True)
    u = real(source_V, "source_V")
    rs, c = positive(source_R_ohm, "source_R_ohm"), positive(C_F, "C_F")
    if load_R_ohm is None:
        rth, final = rs, u
    else:
        rl = positive(load_R_ohm, "load_R_ohm")
        # Harmonic sum avoids overflow in rs*rl and rs+rl.
        rth = 1 / (1 / rs + 1 / rl)
        resistance_ratio = rs / rl
        finite_result((resistance_ratio,))
        final = u / (1 + resistance_ratio)
    tau = rth * c
    positive(tau, "derived tau")
    ratio = t / tau
    if not math.isfinite(ratio):
        raise ValueError("derived duration/tau is nonfinite")
    decay = math.exp(-ratio)
    out = v0 * decay + final * (-math.expm1(-ratio))
    return finite_result((out, final, tau))


def piecewise_rc(initial_V, intervals):
    """n intervals -> n+1 endpoint voltages, first exactly the initial voltage.

    intervals is a nonempty list/tuple of dicts holding rc_interval keyword args.
    Each duration is finite positive. Validate all intervals before returning.
    """
    v = real(initial_V, "initial_V")
    if not isinstance(intervals, (list, tuple)) or not intervals:
        raise ValueError("intervals must be a nonempty list or tuple")
    checked = []
    allowed = {"duration_s", "source_V", "source_R_ohm", "C_F", "load_R_ohm"}
    for row in intervals:
        if not isinstance(row, dict) or set(row) - allowed:
            raise ValueError("invalid interval fields")
        positive(row.get("duration_s"), "duration_s")
        try:
            rc_interval(0, **row)
        except TypeError as exc:
            raise ValueError("missing interval fields") from exc
        checked.append(dict(row))
    endpoints, times = [v], [0.0]
    for row in checked:
        v, _, _ = rc_interval(v, **row)
        t = times[-1] + float(row["duration_s"])
        finite_result((t, v))
        times.append(t)
        endpoints.append(v)
    return times, endpoints


def rlc_state(t_s, R_ohm, L_H, C_F, initial_V, initial_A, *, topology="series", source=0):
    """Constant-source two-state analytic solution, including all damping cases.

    source units: V for series, A for parallel. Returns (v_V, i_A).
    parallel requires R>0; series permits R=0 (lossless LC).
    """
    if topology not in {"series", "parallel"}:
        raise ValueError("topology must be series or parallel")
    t = positive(t_s, "t_s", allow_zero=True)
    r = positive(R_ohm, "R_ohm", allow_zero=(topology == "series"))
    l, c = positive(L_H, "L_H"), positive(C_F, "C_F")
    v, i, inp = real(initial_V, "initial_V"), real(initial_A, "initial_A"), real(source, "source")
    if topology == "series":
        a11, a12, a21, a22 = 0.0, 1 / c, -1 / l, -r / l
    else:
        a11, a12, a21, a22 = -1 / (r * c), -1 / c, 1 / l, 0.0
    finite_result((a11, a12, a21, a22))
    omega0 = math.sqrt((1 / l) * (1 / c))
    alpha = -(a11 + a22) / 2
    positive(omega0, "derived omega0")
    positive(alpha, "derived alpha", allow_zero=True)
    if t == 0:
        return v, i
    alpha_t, omega_t = alpha * t, omega0 * t
    finite_result((alpha_t, omega_t))
    if max(alpha_t, omega_t) <= 0.1:
        # z=(v, i*sqrt(L/C)) puts both coordinates in volts. Direct ODE
        # Taylor increments retain the original initial state and the tiny
        # second-order source response, without subtracting an equilibrium.
        scale = positive(math.sqrt(l / c), "derived current scale")
        zi = i * scale
        finite_result((zi,))
        if topology == "series":
            term_v = omega_t * zi
            term_i = math.fsum((omega_t * inp, -omega_t * v, -2 * alpha_t * zi))
        else:
            scaled_source = inp * scale
            finite_result((scaled_source,))
            term_v = math.fsum((omega_t * scaled_source, -omega_t * zi, -2 * alpha_t * v))
            term_i = omega_t * v
        finite_result((term_v, term_i))
        v_terms, i_terms = [v, term_v], [zi, term_i]
        # ||A*t||_inf <= 0.3 here; fixed 32 terms, no open-ended solver.
        for order in range(2, 33):
            if topology == "series":
                next_v = omega_t * term_i / order
                next_i = math.fsum((-omega_t * term_v, -2 * alpha_t * term_i)) / order
            else:
                next_v = math.fsum((-2 * alpha_t * term_v, -omega_t * term_i)) / order
                next_i = omega_t * term_v / order
            term_v, term_i = finite_result((next_v, next_i))
            v_terms.append(term_v)
            i_terms.append(term_i)
        return finite_result((math.fsum(v_terms), math.fsum(i_terms) / scale))
    zeta = alpha / omega0
    if zeta < 1:
        wd = omega0 * math.sqrt((1 - zeta) * (1 + zeta))
        decay = math.exp(-alpha * t)
        arg = wd * t
        # sin(x)/x tends to 1; no cancellation at critical damping.
        sinc = 1.0 if arg == 0 else math.sin(arg) / arg
        g = decay * t * sinc
        h = decay * math.cos(arg)
        shift = alpha
        source_weight = math.fsum((-math.expm1(-alpha_t), decay * 2 * math.sin(arg / 2) ** 2, -alpha * g))
    elif zeta == 1:
        h = math.exp(-alpha * t)
        g = t * h
        shift = alpha
        source_weight = math.fsum((-math.expm1(-alpha_t), -alpha * g))
    else:
        # Compute slow root without subtracting two nearly equal large numbers.
        delta = omega0 * math.sqrt(zeta - 1) * math.sqrt(zeta + 1)
        fast = -alpha - delta
        slow = -(omega0 / (alpha + delta)) * omega0
        finite_result((fast, slow, (fast - slow) * t))
        e1 = math.exp(slow * t)
        g = e1 * (-math.expm1((fast - slow) * t)) / (slow - fast)
        h, shift = e1, -slow
        source_weight = math.fsum((-math.expm1(slow * t), slow * g))
    # exp(A t) = h I + g(A + shift I), in this branch's convention.
    finite_result((h, g, shift, source_weight))
    if topology == "series":
        source_v, source_i = source_weight * inp, g * (inp / l)
    else:
        source_v, source_i = g * (inp / c), source_weight * inp
    vout = math.fsum((h * v, g * (a11 + shift) * v, g * a12 * i, source_v))
    iout = math.fsum((h * i, g * a21 * v, g * (a22 + shift) * i, source_i))
    return finite_result((vout, iout))


def storage_energy(v_V, i_A, L_H, C_F):
    v, i = real(v_V, "v_V"), real(i_A, "i_A")
    l, c = positive(L_H, "L_H"), positive(C_F, "C_F")
    energy = 0.5 * c * v * v + 0.5 * l * i * i
    return finite_result((energy,))[0]


def mutual_energy(i1_A, i2_A, L1_H, L2_H, k):
    """Reference currents both enter dots. Signed k accounts for reversed coordinates."""
    i1, i2 = real(i1_A, "i1_A"), real(i2_A, "i2_A")
    l1, l2 = positive(L1_H, "L1_H"), positive(L2_H, "L2_H")
    kval = real(k, "k")
    if abs(kval) > 1:
        raise ValueError("passive reciprocal model requires |k|<=1")
    # Normalized-energy form avoids catastrophic cancellation in the k=1 null direction.
    x, y = math.sqrt(l1) * i1, math.sqrt(l2) * i2
    e = 0.5 * ((x + kval * y) ** 2 + (1 - kval) * (1 + kval) * y * y)
    mutual = math.sqrt(l1) * math.sqrt(l2) * kval
    lam1, lam2 = l1 * i1 + mutual * i2, mutual * i1 + l2 * i2
    return finite_result((e, lam1, lam2, mutual))
