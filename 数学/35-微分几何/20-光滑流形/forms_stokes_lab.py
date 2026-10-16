#!/usr/bin/env python3
"""Exact polynomial exterior calculus and finite Stokes sign checks.

Standard library only. Zero-based axis indices in JSON correspond to dx^1,... .
This does not numerically prove partitions of unity or the general Stokes theorem.
"""
import argparse
from fractions import Fraction as Q
from itertools import combinations
import json
from math import factorial
from pathlib import Path


def natural(x, name):
    if type(x) is not int or x < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return x


def exact(x):
    if type(x) not in (int, Q):
        raise ValueError("coefficients must be exact integers or Fractions")
    return Q(x)


class Poly:
    def __init__(self, n, terms):
        self.n = natural(n, 'dimension')
        self.terms = {}
        for exps, value in terms.items():
            if not isinstance(exps, tuple) or len(exps) != n:
                raise ValueError("monomial shape mismatch")
            for e in exps:
                natural(e, 'exponent')
            value = exact(value)
            if value:
                self.terms[exps] = value

    @classmethod
    def constant(cls, n, c):
        return cls(n, {(0,)*n: c})

    @classmethod
    def variable(cls, n, i):
        if type(i) is not int or not 0 <= i < n:
            raise ValueError("variable index out of range")
        return cls(n, {tuple(int(j == i) for j in range(n)): 1})

    def coerce(self, other):
        other = other if isinstance(other, Poly) else Poly.constant(self.n, other)
        if other.n != self.n:
            raise ValueError("polynomial dimension mismatch")
        return other

    def __add__(self, other):
        other = self.coerce(other)
        terms = dict(self.terms)
        for e, c in other.terms.items():
            terms[e] = terms.get(e, Q(0))+c
        return Poly(self.n, terms)

    __radd__ = __add__

    def __neg__(self):
        return Poly(self.n, {e: -c for e, c in self.terms.items()})

    def __sub__(self, other):
        return self + -self.coerce(other)

    def __rsub__(self, other):
        return self.coerce(other) + -self

    def __mul__(self, other):
        other = self.coerce(other)
        terms = {}
        for a, c in self.terms.items():
            for b, d in other.terms.items():
                e = tuple(x+y for x, y in zip(a, b))
                terms[e] = terms.get(e, Q(0))+c*d
        return Poly(self.n, terms)

    __rmul__ = __mul__

    def __pow__(self, k):
        natural(k, 'power')
        result = Poly.constant(self.n, 1)
        for _ in range(k):
            result = result*self
        return result

    def diff(self, i):
        if type(i) is not int or not 0 <= i < self.n:
            raise ValueError("derivative index out of range")
        terms = {}
        for e, c in self.terms.items():
            if e[i]:
                f = list(e)
                f[i] -= 1
                terms[tuple(f)] = c*e[i]
        return Poly(self.n, terms)

    def substitute(self, mapping):
        if len(mapping) != self.n or not mapping or any(p.n != mapping[0].n for p in mapping):
            raise ValueError("substitution shape mismatch")
        out = Poly.constant(mapping[0].n, 0)
        for e, c in self.terms.items():
            term = Poly.constant(mapping[0].n, c)
            for p, k in zip(mapping, e):
                term = term*p**k
            out = out+term
        return out

    def __eq__(self, other):
        return isinstance(other, Poly) and self.n == other.n and self.terms == other.terms

    def dump(self):
        return [{'powers': list(e), 'coefficient': str(c)} for e, c in sorted(self.terms.items())]


class Form:
    def __init__(self, n, degree, terms):
        self.n, self.degree = natural(n, 'dimension'), natural(degree, 'degree')
        self.terms = {}
        for axes, p in terms.items():
            if (not isinstance(axes, tuple) or len(axes) != degree or
                any(type(i) is not int or not 0 <= i < n for i in axes) or
                tuple(sorted(set(axes))) != axes):
                raise ValueError("form axes must be increasing, distinct and in range")
            p = p if isinstance(p, Poly) else Poly.constant(n, p)
            if p.n != n:
                raise ValueError("form coefficient dimension mismatch")
            if p.terms:
                self.terms[axes] = p

    def __add__(self, other):
        if (self.n, self.degree) != (other.n, other.degree):
            raise ValueError("form type mismatch")
        terms = dict(self.terms)
        for axes, p in other.terms.items():
            terms[axes] = terms.get(axes, Poly.constant(self.n, 0))+p
        return Form(self.n, self.degree, terms)

    def scale(self, p):
        return Form(self.n, self.degree, {axes: value*p for axes, value in self.terms.items()})

    def wedge(self, other):
        if self.n != other.n:
            raise ValueError("wedge dimension mismatch")
        terms = {}
        for a, p in self.terms.items():
            for b, q in other.terms.items():
                if set(a) & set(b):
                    continue
                sign = (-1)**sum(i > j for i in a for j in b)
                axes = tuple(sorted(a+b))
                terms[axes] = terms.get(axes, Poly.constant(self.n, 0))+sign*p*q
        return Form(self.n, self.degree+other.degree, terms)

    def d(self):
        out = Form(self.n, self.degree+1, {})
        for axes, p in self.terms.items():
            for j in range(self.n):
                one = Form(self.n, 1, {(j,): p.diff(j)})
                out = out+one.wedge(Form(self.n, self.degree, {axes: 1}))
        return out

    def pullback(self, mapping):
        if len(mapping) != self.n or not mapping or any(p.n != mapping[0].n for p in mapping):
            raise ValueError("pullback map shape mismatch")
        m = mapping[0].n
        out = Form(m, self.degree, {})
        for axes, p in self.terms.items():
            term = Form(m, 0, {(): p.substitute(mapping)})
            for i in axes:
                term = term.wedge(Form(m, 1, {(j,): mapping[i].diff(j) for j in range(m)}))
            out = out+term
        return out

    def __eq__(self, other):
        return (isinstance(other, Form) and self.n == other.n and self.degree == other.degree
                and self.terms == other.terms)

    def dump(self):
        return {'dimension': self.n, 'degree': self.degree,
                'terms': [{'axes_zero_based': list(a), 'polynomial': p.dump()} for a, p in sorted(self.terms.items())]}


def unit_box(form):
    if form.degree != form.n:
        raise ValueError("box integration needs a top form")
    p = form.terms.get(tuple(range(form.n)), Poly.constant(form.n, 0))
    answer = Q(0)
    for e, c in p.terms.items():
        for k in e:
            c /= k+1
        answer += c
    return answer


def box_boundary(form):
    if form.degree != form.n-1:
        raise ValueError("boundary integration needs an (n-1)-form")
    n = form.n
    faces = []
    for axis in range(n):
        for end in (0, 1):
            mapping, j = [], 0
            for i in range(n):
                mapping.append(Poly.constant(n-1, end) if i == axis else Poly.variable(n-1, j))
                if i != axis:
                    j += 1
            orientation = (-1)**axis * (1 if end else -1)
            value = orientation*unit_box(form.pullback(mapping))
            faces.append({'axis': axis, 'endpoint': end, 'orientation': orientation, 'integral': str(value)})
    return sum((Q(f['integral']) for f in faces), Q(0)), faces


def circle_moment_pi(a, b):
    """Integral cos(t)^a sin(t)^b dt, 0..2pi, divided by pi."""
    if a % 2 or b % 2:
        return Q(0)
    a, b = a//2, b//2
    return Q(2*factorial(2*a)*factorial(2*b), 4**(a+b)*factorial(a)*factorial(b)*factorial(a+b))


def disk_integral_pi(form):
    if (form.n, form.degree) != (2, 2):
        raise ValueError("disk requires a two-form in two variables")
    p = form.terms.get((0, 1), Poly.constant(2, 0))
    return sum((c*circle_moment_pi(a, b)/(a+b+2) for (a, b), c in p.terms.items()), Q(0))


def circle_integral_pi(form):
    if (form.n, form.degree) != (2, 1):
        raise ValueError("circle requires a one-form in two variables")
    answer = Q(0)
    for axis, p in form.terms.items():
        for (a, b), c in p.terms.items():
            answer += (-c*circle_moment_pi(a, b+1) if axis == (0,) else c*circle_moment_pi(a+1, b))
    return answer


def family(n, k):
    variables = [Poly.variable(n, i) for i in range(n)]
    return Form(n, k, {axes: sum(((i+j+1)*x**2 for j, x in enumerate(variables)),
                                Poly.constant(n, i+1))
                       for i, axes in enumerate(combinations(range(n), k))})


def build_data():
    derivative_checks = []
    for n in range(1, 5):
        for k in range(n+1):
            f = family(n, k)
            assert not f.d().d().terms
            derivative_checks.append({'n': n, 'degree': k, 'd_squared_zero': True})
    pullbacks = []
    for source_n, target_n in ((1, 3), (2, 2), (2, 3), (3, 3)):
        x = [Poly.variable(source_n, i) for i in range(source_n)]
        mapping = [x[i % source_n]+(i+1)*x[(i+1) % source_n]**2 for i in range(target_n)]
        for k in range(target_n+1):
            form = family(target_n, k)
            left, right = form.pullback(mapping).d(), form.d().pullback(mapping)
            assert left == right
            pullbacks.append({'source_n': source_n, 'target_n': target_n, 'degree': k,
                              'map': [p.dump() for p in mapping], 'result': left.dump()})
    x, y = [Poly.variable(2, i) for i in range(2)]
    alpha = Form(2, 1, {(0,): 2*y, (1,): x})
    mapping = [x, y+x**2]
    transformed = alpha.pullback(mapping)
    assert transformed == Form(2, 1, {(0,): 2*y+4*x**2, (1,): x})
    domain, faces = box_boundary(transformed)
    assert unit_box(transformed.d()) == domain == -1
    reflected = Form(2, 2, {(0, 1): 1+x}).pullback([y, x])
    assert unit_box(reflected) == Q(-3, 2)
    # This is the product-rule cancellation identity only: these polynomial
    # weights are not a subordinate compactly supported chart partition of unity.
    rhos = [(1+x)*Q(1, 2), (1-x)*Q(1, 2)]
    pieces = [alpha.scale(rho).d() for rho in rhos]
    extra = [Form(2, 0, {(): rho}).d().wedge(alpha) for rho in rhos]
    assert pieces[0]+pieces[1] == alpha.d() and not (extra[0]+extra[1]).terms
    even = Form(4, 2, {(0, 1): 1, (2, 3): 1})
    assert even.wedge(even) == Form(4, 4, {(0, 1, 2, 3): 2})
    boxes = []
    for n in range(1, 5):
        form = family(n, n-1)
        boundary, fs = box_boundary(form)
        inside = unit_box(form.d())
        assert boundary == inside
        boxes.append({'n': n, 'form': form.dump(), 'interior': str(inside), 'boundary': str(boundary), 'faces': fs})
    disks = []
    for a, b in ((0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2)):
        f = Form(2, 1, {(0,): -Q(1, 2)*y*x**a*y**b, (1,): Q(1, 2)*x*x**a*y**b})
        interior, boundary = disk_integral_pi(f.d()), circle_integral_pi(f)
        assert interior == boundary
        disks.append({'a': a, 'b': b, 'form': f.dump(), 'interior_pi': str(interior), 'boundary_pi': str(boundary)})
    signs = [{'n': n, 'chart_sign': eps, 'boundary_orientation': eps*(-1)**n,
              'normal_form_coefficient': (-1)**(n-1), 'boundary_total_sign': -eps,
              'normal_FTC_sign': -eps}
             for n in range(1, 8) for eps in (1, -1)]
    assert all(r['boundary_orientation']*r['normal_form_coefficient'] == r['normal_FTC_sign'] for r in signs)
    invalid = [lambda: Poly(True, {}), lambda: Poly(2, {(1,): 1}),
               lambda: Poly(1, {(-1,): 1}), lambda: Poly.constant(1, 0.5),
               lambda: Form(2, 2, {(0, 0): 1}), lambda: Form(2, 1, {(2,): 1}),
               lambda: alpha.pullback([x]), lambda: alpha.wedge(Form(3, 1, {(0,): 1})),
               lambda: unit_box(alpha), lambda: disk_integral_pi(alpha)]
    for action in invalid:
        try:
            action()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid input accepted")
    return {'status': 'PASS', 'date': '2026-10-17', 'd_squared_checks': derivative_checks,
            'pullback_checks': pullbacks, 'nonlinear_change': {'original': alpha.dump(), 'pullback': transformed.dump(),
             'd_pullback': transformed.d().dump(), 'interior': str(domain), 'boundary_faces': faces},
            'reflection': {'standard_source': '-3/2', 'reversed_source': '3/2', 'density': '3/2'},
            'product_rule': {'weights': [p.dump() for p in rhos], 'extra_terms': [f.dump() for f in extra],
             'sum_extras_zero': True, 'limitation': 'algebra identity only, not a subordinate chart PoU'},
            'even_wedge_square': even.wedge(even).dump(), 'box_FTC': boxes, 'disk_circle': disks,
            'halfspace_signs': signs, 'hemisphere': {'flux_pi': disks[0]['interior_pi'], 'area_pi': '2',
             'boundary_CCW_pi': disks[0]['boundary_pi'], 'inward_flux_pi': '-1'},
            'noncompact_counterexample': {'M': '[0,infinity)', 'omega': '1', 'd_integral': '0', 'boundary_integral': '-1'},
            'invalid_inputs_rejected': len(invalid),
            'limits': 'Exact finite polynomial identities/signs. Boxes use facewise FTC, not a claim that corners are smooth boundaries. PoU existence and general Stokes are proved in text; old labs not run.'}


def write_svg(data, folder):
    folder.mkdir(parents=True, exist_ok=True)
    n2 = next(r for r in data['halfspace_signs'] if r['n'] == 2 and r['chart_sign'] == 1)
    circle = data['disk_circle'][0]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="420" viewBox="0 0 1000 420">',
           '<title>Boundary orientation and the same Stokes integral</title>',
           '<desc>Left: H2 has interior above y=0; outward points down and induced boundary goes right. Right: unit disk with positive area, CCW boundary, integral pi on both sides. Values come from exact JSON sign and disk-circle records.</desc>',
           '<rect width="1000" height="420" fill="#f8fafc"/>',
           '<g font-family="sans-serif" fill="#172b4d">',
           '<text x="30" y="40" font-size="23">Boundary orientation: outward first</text>',
           '<rect x="40" y="85" width="400" height="150" fill="#e3eff9"/>',
           '<line x1="40" x2="440" y1="235" y2="235" stroke="#284d72" stroke-width="3"/>',
           '<path d="M200 235 L200 305 l-6 -10 m6 10 l6 -10" fill="none" stroke="#b74455" stroke-width="3"/>',
           '<path d="M200 235 L305 235 l-10 -6 m10 6 l-10 6" fill="none" stroke="#20826b" stroke-width="3"/>',
           '<text x="70" y="125" font-size="18">H2: x2 &gt;= 0</text>',
           '<text x="210" y="300" font-size="17">outward -e2</text>',
           f'<text x="50" y="350" font-size="18">boundary sign (-1)^2 = {n2["boundary_orientation"]}</text>',
           '<text x="50" y="380" font-size="16">(-e2, +e1) has positive orientation.</text>',
           '<line x1="490" x2="490" y1="80" y2="385" stroke="#c3ceda"/>',
           '<circle cx="745" cy="205" r="105" fill="#e3eff9" stroke="#284d72" stroke-width="2"/>',
           '<path d="M850 205 A105 105 0 0 0 745 100 l11 -5 m-11 5 l10 6" fill="none" stroke="#20826b" stroke-width="4"/>',
           '<text x="630" y="70" font-size="18">positive disk, CCW boundary</text>',
           '<text x="680" y="195" font-size="19">d alpha = dx ^ dy</text>',
           f'<text x="680" y="227" font-size="19">interior = {circle["interior_pi"]} pi</text>',
           f'<text x="620" y="350" font-size="18">boundary = {circle["boundary_pi"]} pi</text>',
           '<text x="550" y="382" font-size="16">Reverse both orientations: both values become -pi.</text>',
           '</g></svg>']
    (folder/'stokes-orientation.svg').write_text('\n'.join(svg)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    data = build_data()
    output = args.output_dir/'实践结果'
    output.mkdir(parents=True, exist_ok=True)
    (output/'forms-stokes-20261017.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    write_svg(data, args.output_dir/'assets')
    print(json.dumps({'status': data['status'], 'd_squared': len(data['d_squared_checks']),
                      'pullbacks': len(data['pullback_checks']), 'boxes': len(data['box_FTC']),
                      'disks': len(data['disk_circle']), 'signs': len(data['halfspace_signs']),
                      'invalid_rejected': data['invalid_inputs_rejected']}))


if __name__ == '__main__':
    main()
