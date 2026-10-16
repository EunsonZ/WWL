"""Finite checks for plane face walks, Ramsey edge colours and Sperner families.

Standard library, exact arithmetic for all assertions. Fixed small inputs only.
Rotations are not treated as unconditional certificates of plane embeddings.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations
from math import atan2, comb, cos, pi, sin
from pathlib import Path
import json


PLANE_CASES = {
    'P3': ([(0, 0), (1, 0), (2, 0)], [(0, 1), (1, 2)]),
    'C4': ([(0, 0), (2, 0), (2, 2), (0, 2)],
           [(0, 1), (1, 2), (2, 3), (0, 3)]),
    'K4_leaf': ([(180, 70), (60, 270), (300, 270), (180, 200), (180, 20)],
                list(combinations(range(4), 2)) + [(0, 4)]),
}


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def on_segment(a, b, c):
    return (cross(a, b, c) == 0 and
            min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and
            min(a[1], b[1]) <= c[1] <= max(a[1], b[1]))


def intersect(a, b, c, d):
    x, y, z, w = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    return ((x*y < 0 and z*w < 0) or on_segment(a, b, c) or
            on_segment(a, b, d) or on_segment(c, d, a) or on_segment(c, d, b))


def rotation_orbits(rotation):
    """All dart orbits; may describe a nonplanar surface, not a plane test."""
    darts = {(u, v) for u, row in enumerate(rotation) for v in row}
    assert all(u in rotation[v] for u, v in darts)
    unseen = set(darts)
    orbits = []
    while unseen:
        start = min(unseen)
        dart, orbit = start, []
        while dart in unseen:
            unseen.remove(dart)
            orbit.append(dart)
            u, v = dart
            row = rotation[v]
            dart = (v, row[(row.index(u)-1) % len(row)])
        assert dart == start
        orbits.append(orbit)
    return orbits


def plane_check(coords, edges):
    n = len(coords)
    assert len(set(coords)) == n
    assert all(u != v and 0 <= u < n and 0 <= v < n for u, v in edges)
    for u, v in edges:
        assert all(not on_segment(coords[u], coords[v], coords[w])
                   for w in range(n) if w not in (u, v))
    for (u, v), (a, b) in combinations(edges, 2):
        if len({u, v, a, b}) == 4:
            assert not intersect(coords[u], coords[v], coords[a], coords[b])
    adjacency = [[] for _ in coords]
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)
    reached, stack = {0}, [0]
    while stack:
        for v in adjacency[stack.pop()]:
            if v not in reached:
                reached.add(v)
                stack.append(v)
    assert len(reached) == n
    # Angular sort only derives the rotation; exact segment tests above
    # establish these particular straight drawings have no crossings.
    rotation = [sorted(row, key=lambda v: atan2(coords[v][1]-coords[u][1],
                                              coords[v][0]-coords[u][0]))
                for u, row in enumerate(adjacency)]
    faces = rotation_orbits(rotation)
    lengths = sorted(map(len, faces))
    assert sum(lengths) == 2*len(edges)
    assert n-len(edges)+len(faces) == 2
    return {'vertices': n, 'edges': len(edges), 'faces': len(faces),
            'coordinates': coords, 'edge_list': edges, 'rotation': rotation,
            'face_darts': faces, 'face_lengths': lengths,
            'sum_face_lengths': sum(lengths), 'euler': 2}


def clique_masks(n, k):
    edges = list(combinations(range(n), 2))
    position = {e: i for i, e in enumerate(edges)}
    return [sum(1 << position[e] for e in combinations(s, 2))
            for s in combinations(range(n), k)]


def count_bad(mask, cliques):
    return sum(mask & c in (0, c) for c in cliques)


def ramsey_sweep(n, k):
    cliques = clique_masks(n, k)
    total = 1 << comb(n, 2)
    distribution = Counter(count_bad(mask, cliques) for mask in range(total))
    average = Fraction(sum(x*count for x, count in distribution.items()), total)
    expected = Fraction(comb(n, k), 1 << (comb(k, 2)-1))
    assert average == expected
    return {'n': n, 'k': k, 'colourings': total, 'good': distribution[0],
            'bad_clique_histogram': dict(sorted(distribution.items())),
            'mean_exact': str(average), 'first_moment_exact': str(expected),
            'good_probability_exact': str(Fraction(distribution[0], total))}


def sperner_sweep():
    subsets = list(range(16))
    comparable = [(a, b) for a, b in combinations(subsets, 2)
                  if a & b == a or a & b == b]
    antichains = 0
    maximum, maximizers = -1, 0
    for family in range(1 << 16):
        if any(family >> a & 1 and family >> b & 1 for a, b in comparable):
            continue
        antichains += 1
        chosen = [a for a in subsets if family >> a & 1]
        assert sum((Fraction(1, comb(4, a.bit_count())) for a in chosen),
                   Fraction(0)) <= 1
        if len(chosen) > maximum:
            maximum, maximizers = len(chosen), 1
        elif len(chosen) == maximum:
            maximizers += 1
    assert (antichains, maximum, maximizers) == (168, 6, 1)
    return {'n': 4, 'families_examined': 65536, 'antichains': antichains,
            'maximum_size': maximum, 'labelled_maximizers': maximizers,
            'middle_layer_bitmasks': [a for a in subsets if a.bit_count() == 2],
            'all_antichains_satisfy_LYM': True}


def render(path):
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="380" viewBox="0 0 1200 380" role="img" aria-labelledby="title desc">',
           '<title id="title">Plane face counting versus a crossed attempt and Ramsey edge colours</title>',
           '<desc id="desc">Left: crossing-free K4 with leaf edge 04, counted twice by the outer face. Middle: K3,3 drawn with crossings that are not vertices. Right: red C5 and blue complementary C5, neither has a triangle.</desc>',
           '<rect width="1200" height="380" fill="#fafafa"/>']
    coords, edges = PLANE_CASES['K4_leaf']
    cases = [('K4 + leaf: n=5, m=7, f=4', coords, edges, None),
             ('K3,3: crossed attempt only',
              [(65, 75), (65, 180), (65, 285), (315, 75), (315, 180), (315, 285)],
              list((u, v) for u in range(3) for v in range(3, 6)), None),
             ('K5: red cycle, blue complement',
              [(195+120*cos(-pi/2+2*pi*j/5), 185+120*sin(-pi/2+2*pi*j/5))
               for j in range(5)], list(combinations(range(5), 2)),
              {tuple(sorted((j, (j+1) % 5))) for j in range(5)})]
    for index, (title, points, edges, red) in enumerate(cases):
        offset = index*400
        svg.append(f'<text x="{offset+200}" y="350" text-anchor="middle" font-family="sans-serif" font-size="18">{title}</text>')
        for u, v in edges:
            color = '#444' if red is None else ('#b42318' if (u, v) in red else '#175cd3')
            dash = ' stroke-dasharray="7 4"' if red is not None and (u, v) not in red else ''
            a, b = points[u], points[v]
            svg.append(f'<line x1="{offset+a[0]:.2f}" y1="{a[1]:.2f}" x2="{offset+b[0]:.2f}" y2="{b[1]:.2f}" stroke="{color}" stroke-width="3"{dash}/>')
        for vertex, (x, y) in enumerate(points):
            svg.append(f'<circle cx="{offset+x:.2f}" cy="{y:.2f}" r="13" fill="white" stroke="#222" stroke-width="2"/>')
            svg.append(f'<text x="{offset+x:.2f}" y="{y+5:.2f}" text-anchor="middle" font-family="sans-serif" font-size="15">{vertex}</text>')
    svg.append('</svg>')
    path.write_text('\n'.join(svg)+'\n')


def main():
    root = Path(__file__).resolve().parent
    plane = {name: plane_check(*case) for name, case in PLANE_CASES.items()}
    assert [plane[n]['face_lengths'] for n in ('P3', 'C4', 'K4_leaf')] == [[4], [4, 4], [3, 3, 3, 5]]
    # Deliberately arbitrary cyclic orders: K3,3 does not become plane just
    # because a program can enumerate its dart orbits.
    arbitrary = [[3, 4, 5]]*3 + [[0, 1, 2]]*3
    orbits = rotation_orbits(arbitrary)
    rotation_boundary = {'graph': 'K3_3', 'rotation': arbitrary,
                         'dart_orbits': orbits, 'orbit_count': len(orbits),
                         'n_minus_m_plus_orbits': 6-9+len(orbits),
                         'interpretation': 'not plane faces; arbitrary rotation'}
    assert rotation_boundary['n_minus_m_plus_orbits'] != 2
    rows = [ramsey_sweep(n, 3) for n in range(3, 7)] + [ramsey_sweep(6, 4)]
    assert [r['good'] for r in rows] == [6, 18, 12, 0, 22484]
    edges5 = list(combinations(range(5), 2))
    c5 = {tuple(sorted((j, (j+1) % 5))) for j in range(5)}
    red_mask = sum(1 << i for i, e in enumerate(edges5) if e in c5)
    assert count_bad(red_mask, clique_masks(5, 3)) == 0
    thresholds = []
    for k in range(3, 7):
        n = k
        while Fraction(comb(n+1, k), 1 << (comb(k, 2)-1)) < 1:
            n += 1
        thresholds.append({'k': k, 'largest_N_with_mean_lt_1': n,
                           'mean_at_N': str(Fraction(comb(n, k), 1 << (comb(k, 2)-1))),
                           'mean_at_next': str(Fraction(comb(n+1, k), 1 << (comb(k, 2)-1)))})
    biased = comb(6, 4)*(Fraction(1, 4)**6+Fraction(3, 4)**6)
    assert biased == Fraction(5475, 2048)
    report = {'status': 'PASS', 'plane_drawings': plane,
              'arbitrary_rotation_boundary': rotation_boundary,
              'ramsey_sweeps': rows, 'strict_first_moment_thresholds': thresholds,
              'witnesses': {'K5_red_cycle_edges': sorted(c5),
                            'K5_red_cycle_bad_triangles': 0,
                            'K5_all_red_bad_triangles': count_bad((1 << 10)-1, clique_masks(5, 3))},
              'biased_N6_k4_p_quarter_mean': str(biased),
              'sperner': sperner_sweep(),
              'boundary': 'finite exact cases only; no general planarity algorithm or general theorem proof'}
    (root/'实践结果').mkdir(exist_ok=True)
    (root/'assets').mkdir(exist_ok=True)
    (root/'实践结果'/'planar-ramsey-20261017.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    render(root/'assets'/'planar-ramsey.svg')
    print(json.dumps({'status': 'PASS', 'plane_cases': 3, 'ramsey_rows': len(rows),
                      'ramsey_colourings': sum(r['colourings'] for r in rows),
                      'set_families': 65536}))


if __name__ == '__main__':
    main()
