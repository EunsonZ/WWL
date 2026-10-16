"""Exact finite integer/congruence fixtures; no production cryptography.

Python 3.10+ standard library. Source generates its own JSON and SVG.
Finite scans check implementation/examples, not universally quantified proofs.
"""
from math import gcd
from pathlib import Path
import json


def extended_gcd(a, b, with_trace=False):
    """Return nonnegative g, s, t with g = s*a+t*b; gcd(0,0)=0."""
    a0, b0 = abs(a), abs(b)
    old_r, r, old_s, s, old_t, t = a0, b0, 1, 0, 0, 1
    trace = []
    while r:
        q, remainder = divmod(old_r, r)
        assert old_r == old_s*a0+old_t*b0 and r == s*a0+t*b0
        trace.append({'r0': old_r, 'r1': r, 'q': q, 'remainder': remainder,
                      'r0_coefficients_abs': [old_s, old_t],
                      'r1_coefficients_abs': [s, t]})
        old_r, r = r, remainder
        old_s, s = s, old_s-q*s
        old_t, t = t, old_t-q*t
    result = (old_r, old_s*(-1 if a < 0 else 1), old_t*(-1 if b < 0 else 1))
    assert result[0] == result[1]*a+result[2]*b
    return (*result, trace) if with_trace else result


def inverse(a, modulus):
    if modulus < 2:
        raise ValueError('unit inverse interface requires modulus >= 2')
    d, s, _ = extended_gcd(a, modulus)
    if d != 1:
        raise ValueError('not a unit')
    return s % modulus


def linear_solutions(a, b, modulus):
    if modulus < 1:
        raise ValueError('positive modulus required')
    d, _, _ = extended_gcd(a, modulus)
    if b % d:
        return []
    reduced = modulus//d
    x0 = 0 if reduced == 1 else inverse(a//d, reduced)*(b//d) % reduced
    return [x0+j*reduced for j in range(d)]


def merge_crt(a, m, b, n):
    if m < 1 or n < 1:
        raise ValueError('positive moduli required')
    d, _, _ = extended_gcd(m, n)
    if (b-a) % d:
        return None
    reduced = n//d
    t = 0 if reduced == 1 else inverse(m//d, reduced)*((b-a)//d) % reduced
    period = m*reduced
    return ((a+m*t) % period, period)


def unit_order(a, modulus):
    if gcd(a, modulus) != 1 or modulus < 2:
        raise ValueError('expected unit modulo at least 2')
    value = 1
    for exponent in range(1, modulus+1):
        value = value*a % modulus
        if value == 1:
            return exponent
    raise AssertionError('finite unit must return to 1')


def phi_by_factors(n):
    value, remaining, p = n, n, 2
    while p*p <= remaining:
        if remaining % p == 0:
            value -= value//p
            while remaining % p == 0:
                remaining //= p
        p += 1
    if remaining > 1:
        value -= value//remaining
    return value


def poly_multiply(a, b):
    """GF(2)[x] coefficients in integer bits, not integer multiplication."""
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        b >>= 1
    return result


def poly_divmod(numerator, denominator):
    if numerator < 0 or denominator <= 0:
        raise ValueError('nonnegative polynomial bits and nonzero divisor required')
    q, r = 0, numerator
    while r and r.bit_length() >= denominator.bit_length():
        shift = r.bit_length()-denominator.bit_length()
        q ^= 1 << shift
        r ^= denominator << shift
    assert numerator == poly_multiply(q, denominator) ^ r
    assert r == 0 or r.bit_length() < denominator.bit_length()
    return q, r


def render_phase(path):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="330" viewBox="0 0 1100 330" role="img" aria-labelledby="title desc">',
             '<title id="title">CRT compatibility in one complete twelve-position period</title>',
             '<desc id="desc">Top: positions 1,5,9 modulo four and 3,9 modulo six overlap at 9. Bottom: positions 1,5,9 and 2,8 do not overlap. Circles mark the first condition, squares the second; filled green marks a common solution.</desc>',
             '<rect width="1100" height="330" fill="#fafafa"/>']
    for row, b in enumerate((3, 2)):
        y = 95+150*row
        parts.append(f'<text x="25" y="{y-50}" font-family="sans-serif" font-size="20">x = 1 (mod 4), x = {b} (mod 6): '+('compatible; x = 9 (mod 12)' if b == 3 else 'incompatible; gcd 2 does not divide 1')+'</text>')
        parts.append(f'<line x1="65" y1="{y}" x2="1055" y2="{y}" stroke="#aaa"/>')
        for x in range(12):
            px = 65+90*x
            a_hit, b_hit = x % 4 == 1, x % 6 == b
            if b_hit:
                parts.append(f'<rect x="{px-22}" y="{y-22}" width="44" height="44" fill="none" stroke="#b54708" stroke-width="3"/>')
            parts.append(f'<circle cx="{px}" cy="{y}" r="15" fill="'+('#abefc6' if a_hit and b_hit else '#d1e9ff' if a_hit else 'white')+'" stroke="'+('#175cd3' if a_hit else '#999')+'" stroke-width="2"/>')
            parts.append(f'<text x="{px}" y="{y+5}" text-anchor="middle" font-family="sans-serif" font-size="14">{x}</text>')
    parts.append('</svg>')
    path.write_text('\n'.join(parts)+'\n')


def main():
    root = Path(__file__).resolve().parent
    egcd_cases = []
    for a, b in ((240, 46), (-240, 46), (0, 46), (240, 0), (0, 0)):
        d, s, t, trace = extended_gcd(a, b, True)
        assert d == gcd(a, b)
        egcd_cases.append({'a': a, 'b': b, 'gcd': d, 's': s, 't': t, 'trace': trace})
    egcd_count = 0
    for a in range(-30, 31):
        for b in range(-30, 31):
            d, s, t = extended_gcd(a, b)
            assert d == gcd(a, b) and d == s*a+t*b
            egcd_count += 1
    linear_count = 0
    for m in range(1, 17):
        for a in range(-12, 13):
            for b in range(m):
                actual = linear_solutions(a, b, m)
                direct = [x for x in range(m) if (a*x-b) % m == 0]
                assert actual == direct
                linear_count += 1
    crt_count = compatible = 0
    for m in range(1, 13):
        for n in range(1, 13):
            period = m*n//gcd(m, n)
            for a in range(m):
                for b in range(n):
                    result = merge_crt(a, m, b, n)
                    direct = [x for x in range(period)
                              if x % m == a and x % n == b]
                    assert direct == ([] if result is None else [result[0]])
                    if result is not None:
                        assert result[1] == period
                        compatible += 1
                    crt_count += 1
    unit_rows = []
    for m in range(2, 41):
        units = [a for a in range(m) if gcd(a, m) == 1]
        assert len(units) == phi_by_factors(m)
        orders = {a: unit_order(a, m) for a in units}
        for a in units:
            assert a*inverse(a, m) % m == 1
            assert pow(a, len(units), m) == 1 and len(units) % orders[a] == 0
        unit_rows.append({'modulus': m, 'phi': len(units), 'units': units,
                          'orders': orders})
    crt_cases = [{'a': a, 'm': m, 'b': b, 'n': n,
                  'solution_and_period': merge_crt(a, m, b, n)}
                 for a, m, b, n in ((2, 3, 3, 5), (1, 4, 3, 6), (1, 4, 2, 6),
                                    (-1, 4, 5, 6), (9, 1, 3, 6))]
    M, G = 0b1101, 0b1011
    q0, r0 = divmod(13, 11)
    q1, r1 = poly_divmod(M, G)
    q2, r2 = poly_divmod(M << 3, G)
    assert (q0, r0, q1, r1, q2, r2) == (1, 2, 1, 6, 15, 1)
    gf4_table = [[poly_divmod(poly_multiply(a, b), 0b111)[1]
                  for b in range(4)] for a in range(4)]
    gf4_inverses = {a: next(b for b in range(1, 4) if gf4_table[a][b] == 1)
                   for a in range(1, 4)}
    assert gf4_inverses == {1: 1, 2: 3, 3: 2}
    assert poly_divmod(poly_multiply(0b11, 0b111), 0b1001)[1] == 0
    assert poly_divmod(poly_multiply(0b10, 0b100), 0b1001)[1] == 1
    assert pow(2, 4, 8) == 0 and pow(3, 4, 8) == 1
    assert 341 == 11*31 and pow(2, 10, 341) == pow(2, 340, 341) == 1
    report = {'status': 'PASS', 'arithmetic': 'exact integers; zero numerical tolerance',
              'extended_gcd_cases': egcd_cases,
              'finite_sweeps': {'signed_gcd_pairs': egcd_count,
                                'linear_congruences': linear_count,
                                'two_modulus_systems': crt_count,
                                'compatible_systems': compatible,
                                'unit_moduli': len(unit_rows)},
              'crt_cases': crt_cases,
              'linear_cases': [{'a': a, 'b': b, 'modulus': m,
                                 'solutions': linear_solutions(a, b, m)}
                                for a, b, m in ((6, 8, 14), (6, 7, 14), (4, 0, 4), (4, 2, 4))],
              'unit_rows': unit_rows,
              'inverse_23_mod_120': inverse(23, 120), 'phi_120': phi_by_factors(120),
              'three_remainders': {'integer_13_by_11': {'q': q0, 'r': r0},
                                   'GF2_M_by_G': {'q_bits': format(q1, 'b'), 'r_bits': format(r1, '03b')},
                                   'GF2_shifted_M_by_G': {'q_bits': format(q2, 'b'), 'r_bits': format(r2, '03b')}},
              'GF4': {'modulus_bits': '111', 'multiplication_table': gf4_table,
                      'inverses': gf4_inverses, 'unit_count': 3},
              'Z4_units': [a for a in range(4) if gcd(a, 4) == 1],
              'reducible_GF2_quotient': {'modulus_bits': '1001', 'nonzero_zero_divisors_bits': ['11', '111'],
                                        'x_inverse_bits': '100'},
              'counterexamples': {'nonunit_2_pow_phi8': 0, 'composite_341': [11, 31], '2_pow_340_mod_341': 1},
              'boundary': 'finite fixtures only; no prime certification algorithm, production crypto or protocol execution'}
    (root/'实践结果').mkdir(exist_ok=True)
    (root/'assets').mkdir(exist_ok=True)
    (root/'实践结果'/'integer-congruence-20261017.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    render_phase(root/'assets'/'crt-phase.svg')
    print(json.dumps({'status': 'PASS', **report['finite_sweeps']}))


if __name__ == '__main__':
    main()
