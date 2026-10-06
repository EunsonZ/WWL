"""Exact finite examples, not a solver for infinite-space topology.

Labels are strings or integers (excluding bool); at most eight points.
The optional SVG output uses fixed sets/parameters and has no time metadata.
"""
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import argparse
import json
import math


def labels(values):
    if isinstance(values, (str, bytes)):
        raise ValueError('supply an iterable of labels, not one string')
    try:
        result = tuple(values)
    except TypeError as exc:
        raise ValueError('labels must be iterable') from exc
    if any(type(x) not in (str, int) for x in result):
        raise ValueError('labels must be strings or integers, excluding bool')
    if len(result) != len(set(result)):
        raise ValueError('labels must be distinct')
    if len(result) > 8:
        raise ValueError('exact powersets are limited to eight points')
    return result


def powerset(values):
    xs = labels(values)
    return tuple(frozenset(c) for k in range(len(xs) + 1)
                 for c in combinations(xs, k))


@dataclass(frozen=True)
class FiniteTopology:
    points: frozenset
    opens: frozenset

    def __post_init__(self):
        points = frozenset(labels(self.points))
        try:
            raw = tuple(self.opens)
            opens = frozenset(frozenset(labels(u)) for u in raw)
        except TypeError as exc:
            raise ValueError('opens must be an iterable of subsets') from exc
        if any(not u <= points for u in opens):
            raise ValueError('an open set contains a point outside the space')
        if frozenset() not in opens or points not in opens:
            raise ValueError('empty set and whole space must be open')
        if any(u | v not in opens or u & v not in opens
               for u in opens for v in opens):
            raise ValueError('opens are not closed under pairwise union/intersection')
        object.__setattr__(self, 'points', points)
        object.__setattr__(self, 'opens', opens)

    def subspace(self, subset):
        subset = frozenset(labels(subset))
        if not subset <= self.points:
            raise ValueError('subspace must be contained in the source')
        return FiniteTopology(subset, {u & subset for u in self.opens})

    def minimum_neighborhood(self, point):
        if type(point) not in (str, int) or point not in self.points:
            raise ValueError('point is outside the space')
        result = self.points
        for u in self.opens:
            if point in u:
                result = result & u
        return result

    def hausdorff(self):
        return all(any(x in u and y in v and not u & v
                       for u in self.opens for v in self.opens)
                   for x in self.points for y in self.points if x != y)

    def connected(self):
        return not any(u and u != self.points and self.points - u in self.opens
                       for u in self.opens)


def validate_map(source, target_points, mapping):
    if not isinstance(mapping, dict) or set(mapping) != source.points:
        raise ValueError('map must specify exactly every source point')
    if any(type(y) not in (str, int) or y not in target_points
           for y in mapping.values()):
        raise ValueError('map value is outside the declared target')


def continuous(source, target, mapping):
    validate_map(source, target.points, mapping)
    return all(frozenset(x for x in source.points if mapping[x] in u)
               in source.opens for u in target.opens)


def quotient(source, target_points, mapping):
    target_points = frozenset(labels(target_points))
    validate_map(source, target_points, mapping)
    if set(mapping.values()) != target_points:
        raise ValueError('quotient map must be surjective')
    opens = {u for u in powerset(target_points)
             if frozenset(x for x in source.points if mapping[x] in u)
             in source.opens}
    return FiniteTopology(target_points, opens)


def all_topologies(points):
    points = labels(points)
    if len(points) > 3:
        raise ValueError('all topology families are limited to three points')
    subsets = powerset(points)
    optional = tuple(u for u in subsets if u and u != frozenset(points))
    # Here we enumerate families of subsets, not labels. Avoid the label API.
    for mask in range(1 << len(optional)):
        family = {frozenset(), frozenset(points)}
        family.update(u for i, u in enumerate(optional) if mask & (1 << i))
        try:
            yield FiniteTopology(frozenset(points), family)
        except ValueError:
            continue


def write_figures(directory):
    """Fixed-coordinate quotient recipes and p(theta)=exp(2*pi*i*theta)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    header = '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="360" viewBox="0 0 960 360"><style>text{font-family:Arial,sans-serif;font-size:17px} .edge{stroke:#2459a6;stroke-width:3;fill:none} .arrow{stroke:#b64228;stroke-width:3;fill:none;marker-end:url(#a)}</style><defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#b64228"/></marker></defs><rect width="960" height="360" fill="#ffffff"/>'
    def circular_arrow(cx, cy):
        points = [(cx + 90 * math.cos(k * math.pi / 16),
                   cy - 90 * math.sin(k * math.pi / 16)) for k in range(9)]
        path = 'M' + ' L'.join(f'{x:.3f} {y:.3f}' for x, y in points)
        return f'<path class="arrow" d="{path}"/>'
    body = '<text x="25" y="30">Endpoint quotient: [0,1] / (0 ~ 1)</text><path class="edge" d="M50 170 L350 170"/><circle cx="50" cy="170" r="7" fill="#b64228"/><circle cx="350" cy="170" r="7" fill="#b64228"/><text x="45" y="205">0</text><text x="340" y="205">1</text><text x="70" y="135">same class [0]=[1]</text><path class="arrow" d="M390 170 L510 170"/><text x="400" y="140">exp(2 pi i t)</text><circle class="edge" cx="690" cy="170" r="90"/><circle cx="780" cy="170" r="7" fill="#b64228"/><text x="791" y="174">[0]=[1]</text>' + circular_arrow(690, 170) + '<text x="535" y="305">Circle inherits quotient topology.</text><text x="535" y="332">Drawing alone does not prove it.</text>'
    (directory / 'topology-circle.svg').write_text(header + body + '</svg>\n', encoding='utf-8')
    body = '<text x="20" y="28">Square coordinates (u,v): u right, v up. Arrows specify pairing.</text>'
    for x, title, reverse, horizontal in [(45,'Cylinder',False,False),(355,'Torus',False,True),(665,'Mobius band',True,False)]:
        body += f'<text x="{x+40}" y="65">{title}</text><rect class="edge" x="{x}" y="100" width="200" height="150"/><path class="arrow" d="M{x} 215 L{x} 140"/>'
        a,b = (140,215) if reverse else (215,140)
        body += f'<path class="arrow" d="M{x+200} {a} L{x+200} {b}"/>'
        if horizontal:
            body += f'<path class="arrow" d="M{x+55} 100 L{x+145} 100"/><path class="arrow" d="M{x+55} 250 L{x+145} 250"/>'
        body += f'<text x="{x}" y="278">(0,v) ~ (1,{"1-v" if reverse else "v"})</text>'
        if horizontal:
            body += f'<text x="{x}" y="305">(u,0) ~ (u,1)</text>'
        else:
            body += f'<text x="{x}" y="305">horizontal edges unpaired</text>'
    body += '<text x="20" y="342">No extra interior identifications. Boundary and orientation require definitions/proofs.</text>'
    (directory / 'topology-identifications.svg').write_text(header + body + '</svg>\n', encoding='utf-8')
    body = '<text x="25" y="28">Lift of gamma(t)=exp(4 pi i t): theta(t)=2t, 0 &lt;= t &lt;= 1</text><path class="edge" d="M70 280 L460 280 M70 280 L70 60"/><text x="465" y="286">t</text><text x="25" y="55">theta (turns)</text><text x="60" y="305">0</text><text x="420" y="305">1</text><text x="35" y="88">2</text><path class="arrow" d="M70 280 L420 80"/><text x="170" y="65">endpoint difference = 2</text>'
    for k in range(5):
        t=k/4
        px=70+350*t
        py=280-200*t
        body += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="#b64228"/>'
    body += '<circle class="edge" cx="720" cy="175" r="90"/>' + circular_arrow(720, 175) + '<circle cx="810" cy="175" r="7" fill="#b64228"/><text x="824" y="172">1</text><text x="606" y="305">p(theta) forgets integer turns</text><text x="565" y="334">Continuous loop, no derivative assumed.</text>'
    (directory / 'topology-winding.svg').write_text(header + body + '</svg>\n', encoding='utf-8')


def demo():
    source = FiniteTopology({'a','b','c'}, [set(), {'a'}, {'a','b'}, {'a','b','c'}])
    q = {'a':'A','b':'B','c':'A'}
    result = quotient(source, ['A','B'], q)
    return {'quotient_opens': sorted([sorted(u) for u in result.opens], key=lambda u:(len(u),u)),
            'quotient_connected': result.connected(),
            'quotient_hausdorff': result.hausdorff(),
            'labeled_topology_counts': [len(list(all_topologies(range(n)))) for n in range(4)]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', type=Path, help='write three deterministic educational SVGs here')
    args = parser.parse_args()
    if args.figures is not None:
        write_figures(args.figures)
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
