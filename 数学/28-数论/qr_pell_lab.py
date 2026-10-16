"""Exact finite checks for reciprocity and continued-fraction/Pell lessons.

Standard library only; fixed small primes, exact integer surds and finite scans.
No floating root extraction is used for any mathematical assertion.
"""
from fractions import Fraction
from itertools import combinations
from math import isqrt, gcd
from pathlib import Path
import json


def is_prime(n):
    return n >= 2 and all(n % d for d in range(2, isqrt(n)+1))


def require_odd_prime(p):
    if p < 3 or p % 2 == 0 or not is_prime(p):
        raise ValueError('Legendre denominator must be an odd prime')


def legendre_power(a, p):
    require_odd_prime(p)
    r = pow(a, (p-1)//2, p)
    return -1 if r == p-1 else r


def prime_factors(a):
    result, factor = [], 2
    while factor*factor <= a:
        count = 0
        while a % factor == 0:
            a //= factor
            count += 1
        if count:
            result.append((factor, count))
        factor += 1
    if a > 1:
        result.append((a, 1))
    return result


def legendre_reciprocity(a, p):
    """Factor reduced numerator, use the two supplements and prime reciprocity.

    Each odd-prime recursive denominator is smaller than the previous one.
    Trial factoring is for these small fixtures, not a general fast root solver.
    """
    require_odd_prime(p)
    a %= p
    if a == 0:
        return 0
    sign = 1
    for q, exponent in prime_factors(a):
        if q == 2:
            value = -1 if p % 8 in (3, 5) else 1
        else:
            value = (-1 if p % 4 == q % 4 == 3 else 1)*legendre_reciprocity(p % q, q)
        sign *= value**exponent
    return sign


def gauss_data(a, p):
    require_odd_prime(p)
    if a % p == 0:
        raise ValueError('Gauss lemma requires a unit')
    h = (p-1)//2
    residues = [a*i % p for i in range(1, h+1)]
    folded = [min(r, p-r) for r in residues]
    flips = sum(2*r > p for r in residues)
    assert sorted(folded) == list(range(1, h+1))
    return {'a': a, 'p': p, 'positive_residues': residues,
            'folded': folded, 'flips': flips, 'symbol': (-1)**flips}


def lattice_data(p, q):
    require_odd_prime(p)
    require_odd_prime(q)
    if p == q:
        raise ValueError('reciprocity needs distinct primes')
    h, k = (p-1)//2, (q-1)//2
    below, above = [], []
    for i in range(1, h+1):
        for j in range(1, k+1):
            assert q*i != p*j
            (below if p*j < q*i else above).append((i, j))
    floor_q_over_p = [q*i//p for i in range(1, h+1)]
    floor_p_over_q = [p*j//q for j in range(1, k+1)]
    assert len(below) == sum(floor_q_over_p)
    assert len(above) == sum(floor_p_over_q)
    assert len(below)+len(above) == h*k
    assert legendre_power(q, p)*legendre_power(p, q) == (-1)**(h*k)
    return {'p': p, 'q': q, 'h': h, 'k': k, 'below': below, 'above': above,
            'floor_q_over_p': floor_q_over_p, 'floor_p_over_q': floor_p_over_q,
            'q_over_p_symbol': legendre_power(q, p), 'p_over_q_symbol': legendre_power(p, q)}


def sqrt_convergents(D, terms):
    if D < 2 or isqrt(D)**2 == D or terms < 1:
        raise ValueError('nonsquare integer D>=2 and positive term count required')
    s, P, Q = isqrt(D), 0, 1
    pm2, pm1, qm2, qm1 = 0, 1, 1, 0
    rows = []
    for n in range(terms+1):
        a = (s+P)//Q  # floor((sqrt(D)+P)/Q), Q positive integer
        p, q = a*pm1+pm2, a*qm1+qm2
        assert p*qm1-pm1*q == (-1)**(n+1) and gcd(p, q) == 1
        rows.append({'n': n, 'a': a, 'P': P, 'Q': Q, 'p': p, 'q': q,
                     'norm': p*p-D*q*q})
        next_P = a*Q-P
        assert (D-next_P*next_P) % Q == 0
        next_Q = (D-next_P*next_P)//Q
        assert next_Q > 0
        P, Q = next_P, next_Q
        pm2, pm1, qm2, qm1 = pm1, p, qm1, q
    for row, nxt in zip(rows, rows[1:]):
        p, q = row['p'], row['q']
        bound = Fraction(1, q*nxt['q'])
        low, high = Fraction(p, q)-bound, Fraction(p, q)+bound
        assert (low <= 0 or low*low < D) and D < high*high
        assert (row['norm'] < 0) == (row['n'] % 2 == 0)
        assert (abs(row['norm'])-1)**2 < 4*D
        row['error_bound_exact'] = str(bound)
        row['strict_error_bound_verified_by_rational_squares'] = True
    return rows[:-1]


def multiply_pair(a, b, D):
    x, y = a
    u, v = b
    return (x*u+D*y*v, x*v+y*u)


def pell_scan(D, cap):
    """Full positive-y scan up to a fixed cap, not a general CF solver."""
    solutions = []
    for y in range(1, cap+1):
        square = D*y*y+1
        x = isqrt(square)
        if x*x == square:
            solutions.append((x, y))
    assert solutions
    fundamental = solutions[0]
    generated, value = [], fundamental
    while value[1] <= cap:
        generated.append(value)
        value = multiply_pair(value, fundamental, D)
    assert generated == solutions
    return {'D': D, 'positive_y_cap': cap, 'fundamental_from_complete_scan': fundamental,
            'all_solutions_within_cap': solutions, 'powers_within_cap': generated}


def render_lattice(path, data):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="600" viewBox="0 0 760 600" role="img" aria-labelledby="title desc">',
             '<title id="title">Quadratic reciprocity lattice for p=7 q=11</title>',
             '<desc id="desc">Fifteen points with i=1,2,3 and j=1,...,5. Eight blue circles satisfy 7j less than 11i; seven orange squares satisfy 11i less than 7j. No point is on the line.</desc>',
             '<rect width="760" height="600" fill="#fafafa"/>',
             '<text x="380" y="32" text-anchor="middle" font-family="sans-serif" font-size="22">p=7, q=11: 8 + 7 = 15 lattice points</text>']
    origin_x, origin_y, dx, dy = 125, 500, 150, 78
    parts += [f'<line x1="{origin_x}" y1="{origin_y}" x2="{origin_x+3.5*dx}" y2="{origin_y}" stroke="#555"/>',
              f'<line x1="{origin_x}" y1="{origin_y}" x2="{origin_x}" y2="{origin_y-5.5*dy}" stroke="#555"/>',
              f'<line x1="{origin_x}" y1="{origin_y}" x2="{origin_x+3.5*dx}" y2="{origin_y-5.5*dy}" stroke="#666" stroke-width="2" stroke-dasharray="7 5"/>']
    for i in range(1, 4):
        parts.append(f'<text x="{origin_x+i*dx}" y="530" text-anchor="middle" font-family="sans-serif" font-size="18">i={i}</text>')
    for j in range(1, 6):
        parts.append(f'<text x="105" y="{origin_y-j*dy+6}" text-anchor="end" font-family="sans-serif" font-size="18">j={j}</text>')
    for group, color in (('below', '#175cd3'), ('above', '#b54708')):
        for i, j in data[group]:
            x, y = origin_x+i*dx, origin_y-j*dy
            if group == 'below':
                parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}"/>')
            else:
                parts.append(f'<rect x="{x-6}" y="{y-6}" width="12" height="12" fill="{color}"/>')
    parts.append('<text x="380" y="572" text-anchor="middle" font-family="sans-serif" font-size="18">circle: 7j &lt; 11i; square: 11i &lt; 7j; dashed: equality</text>')
    parts.append('</svg>')
    path.write_text('\n'.join(parts)+'\n')


def main():
    root = Path(__file__).resolve().parent
    primes = [p for p in range(3, 98, 2) if is_prime(p)]
    symbol_count = floor_count = 0
    for p in primes:
        squares = {x*x % p for x in range(1, p)}
        for a in range(-p, 2*p+1):
            expected = 0 if a % p == 0 else (1 if a % p in squares else -1)
            assert legendre_power(a, p) == legendre_reciprocity(a, p) == expected
            if a % p:
                assert gauss_data(a, p)['symbol'] == expected
            symbol_count += 1
        for a in range(1, 2*p, 2):
            if a % p:
                assert (-1)**sum(a*i//p for i in range(1, (p-1)//2+1)) == legendre_power(a, p)
                floor_count += 1
        assert legendre_power(-1, p) == (-1)**((p-1)//2)
        assert legendre_power(2, p) == (-1)**((p*p-1)//8)
    pair_count = 0
    for p, q in combinations(primes, 2):
        lattice_data(p, q)
        pair_count += 1
    lattice = lattice_data(7, 11)
    assert (len(lattice['below']), len(lattice['above'])) == (8, 7)
    ds = (2, 3, 5, 6, 7, 8, 10, 13)
    cf = {str(D): sqrt_convergents(D, 20) for D in ds}
    pell = [pell_scan(D, 1000) for D in ds]
    expected_fundamentals = [(3,2), (2,1), (9,4), (5,2), (8,3), (3,1), (19,6), (649,180)]
    assert [tuple(r['fundamental_from_complete_scan']) for r in pell] == expected_fundamentals
    power = (1, 0)
    for row in cf['2']:
        power = multiply_pair(power, (1, 1), 2)
        assert power == (row['p'], row['q']) and row['norm'] == (-1)**(row['n']+1)
    roots37 = [x for x in range(101) if x*x % 101 == 37]
    roots7 = [x for x in range(101) if x*x % 101 == 7]
    assert roots37 == [21, 80] and roots7 == []
    assert [x for x in range(11) if (x*x+3*x+1) % 11 == 0] == [2, 6]
    assert sorted({x*x % 15 for x in range(15)}) == [0, 1, 4, 6, 9, 10]
    report = {'status': 'PASS', 'arithmetic': 'exact integers and rational inequalities',
              'finite_sweeps': {'odd_primes': len(primes), 'symbol_inputs': symbol_count,
                                'odd_floor_inputs': floor_count, 'distinct_prime_pairs': pair_count,
                                'sqrt_D_cases': len(ds), 'convergents_per_D': 20,
                                'Pell_y_tests': 1000*len(ds)},
              'lattice_7_11': lattice, 'gauss_3_11': gauss_data(3, 11),
              'roots_mod_101': {'37': roots37, '7': roots7},
              'quadratic_roots_mod_11': [2, 6], 'square_set_mod_15': [0,1,4,6,9,10],
              'sqrt_convergents': cf, 'pell_scans': pell,
              'changed_conditions': {'decimal_pair_norm': 14142**2-2*10000**2,
                                     'reduced_decimal_pair_norm': 7071**2-2*5000**2,
                                     'same_norm_7_quotient_coefficients': ['9/7', '4/7'],
                                     'negative_Pell_D3_mod3_squares': [0,1]},
              'boundary': 'finite checks, not general proof, prime certification or arbitrary-D efficient Pell solver'}
    (root/'assets').mkdir(exist_ok=True)
    (root/'实践结果').mkdir(exist_ok=True)
    (root/'实践结果'/'qr-pell-20261017.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    render_lattice(root/'assets'/'reciprocity-lattice.svg', lattice)
    print(json.dumps({'status': 'PASS', **report['finite_sweeps']}))


if __name__ == '__main__':
    main()
