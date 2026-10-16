"""Small exact graph checks; no general theorem is inferred from enumeration.

Python standard library only. Fixed exhaustive sweep: labelled simple graphs,
1 <= n <= 6, excluding K3 or K4. Outputs stay beside this source.
"""
from fractions import Fraction
from itertools import combinations, product
from math import cos, pi, sin
from pathlib import Path
import json


def edge_set(n, pairs):
    result = set()
    for u, v in pairs:
        if not (0 <= u < n and 0 <= v < n) or u == v:
            raise ValueError("expected distinct vertices in range(n)")
        result.add(tuple(sorted((u, v))))
    return result


def invariants(n, edges):
    """Exhaustive subsets and assignments, only for named small examples."""
    clique = independent = ()
    for size in range(n + 1):
        for subset in combinations(range(n), size):
            pairs = list(combinations(subset, 2))
            if all(e in edges for e in pairs):
                clique = subset
            if all(e not in edges for e in pairs):
                independent = subset
    for k in range(1, n + 1):
        witness = next((a for a in product(range(k), repeat=n)
                        if all(a[u] != a[v] for u, v in edges)), None)
        if witness is not None:
            return {"omega": len(clique), "alpha": len(independent),
                    "chi": k, "clique": clique,
                    "independent_set": independent, "coloring": witness}
    raise AssertionError("finite simple graph must be n-colorable")


def laplacian_rank(n, edges):
    matrix = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    for u, v in edges:
        matrix[u][u] += 1
        matrix[v][v] += 1
        matrix[u][v] -= 1
        matrix[v][u] -= 1
    assert all(sum(row) == 0 for row in matrix)
    rows = [row[:] for row in matrix]
    rank = 0
    for col in range(n):
        pivot = next((j for j in range(rank, n) if rows[j][col]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        scale = rows[rank][col]
        rows[rank] = [x / scale for x in rows[rank]]
        for j in range(n):
            if j != rank:
                scale = rows[j][col]
                rows[j] = [a - scale*b for a, b in zip(rows[j], rows[rank])]
        rank += 1
    return {"matrix": [[int(x) for x in row] for row in matrix],
            "rank_exact": rank, "nullity_exact": n-rank}


def forbidden_extrema(n, clique_size):
    pairs = list(combinations(range(n), 2))
    positions = {e: j for j, e in enumerate(pairs)}
    forbidden = [sum(1 << positions[e] for e in combinations(vs, 2))
                 for vs in combinations(range(n), clique_size)]
    best, maximizers, first = -1, 0, 0
    for mask in range(1 << len(pairs)):
        if any(mask & clique == clique for clique in forbidden):
            continue
        count = mask.bit_count()
        if count > best:
            best, maximizers, first = count, 1, mask
        elif count == best:
            maximizers += 1
    return {"n": n, "forbidden_clique": clique_size,
            "graphs_examined": 1 << len(pairs), "max_edges": best,
            "labelled_maximizers": maximizers,
            "first_maximizer": [e for j, e in enumerate(pairs) if first >> j & 1]}


def render_figure(path, cases):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="380" viewBox="0 0 960 380" role="img" aria-labelledby="title desc">',
             '<title id="title">C5 and K2,3: same clique number, different coloring</title>',
             '<desc id="desc">A five-cycle needs three colors but has no triangle. A complete two-part graph with parts of size two and three needs two colors and reaches the six-edge Mantel bound.</desc>',
             '<rect width="960" height="380" fill="#fafafa"/>']
    colors = ['#cfe5ff', '#ffe1bb', '#d4efdc']
    for index, (name, edges, coloring, coords, caption) in enumerate(cases):
        offset = index * 480
        parts.append(f'<text x="{offset+240}" y="34" text-anchor="middle" font-size="22" font-family="sans-serif">{name}</text>')
        for u, v in sorted(edges):
            x1, y1 = coords[u]; x2, y2 = coords[v]
            parts.append(f'<line x1="{offset+x1:.2f}" y1="{y1:.2f}" x2="{offset+x2:.2f}" y2="{y2:.2f}" stroke="#555" stroke-width="3"/>')
        for v, (x, y) in enumerate(coords):
            letter = 'ABC'[coloring[v]]
            parts.append(f'<circle cx="{offset+x:.2f}" cy="{y:.2f}" r="24" fill="{colors[coloring[v]]}" stroke="#222" stroke-width="2"/>')
            parts.append(f'<text x="{offset+x:.2f}" y="{y+5:.2f}" text-anchor="middle" font-size="16" font-family="sans-serif">{v}:{letter}</text>')
        parts.append(f'<text x="{offset+240}" y="351" text-anchor="middle" font-size="17" font-family="sans-serif">{caption}</text>')
    parts.append('</svg>')
    path.write_text('\n'.join(parts)+'\n')


def main():
    root = Path(__file__).resolve().parent
    c5 = edge_set(5, [(j, (j+1) % 5) for j in range(5)])
    k23 = edge_set(5, product(range(2), range(2, 5)))
    path5 = c5 - {(0, 4)}
    cases = {"C5": (5, c5), "K2_3": (5, k23), "P5": (5, path5)}
    expected = {"C5": (2, 2, 3), "K2_3": (2, 3, 2), "P5": (2, 3, 2)}
    outputs = {}
    for name, (n, edges) in cases.items():
        result = invariants(n, edges)
        assert tuple(result[k] for k in ('omega', 'alpha', 'chi')) == expected[name]
        outputs[name] = result
    lap = laplacian_rank(5, c5)
    assert lap['rank_exact'] == 4 and lap['nullity_exact'] == 1
    # Independent expectations: balanced complete-part constructions and
    # counts of unordered labelled partitions (see the lab's derivation).
    expected_mantel = [(0, 1), (1, 1), (2, 3), (4, 3), (6, 10), (9, 10)]
    expected_k4 = [(0, 1), (1, 1), (3, 1), (5, 6), (8, 15), (12, 15)]
    extrema = []
    for n in range(1, 7):
        for size, expected_rows in ((3, expected_mantel), (4, expected_k4)):
            row = forbidden_extrema(n, size)
            assert (row['max_edges'], row['labelled_maximizers']) == expected_rows[n-1]
            extrema.append(row)
    report = {"status": "PASS", "arithmetic": "integers and fractions; zero tolerance",
              "examples": outputs, "C5_laplacian": lap, "extrema": extrema,
              "boundary": "Only 1<=n<=6 labelled simple graphs; not a proof for general n."}
    (root/'实践结果').mkdir(exist_ok=True)
    (root/'实践结果'/'coloring-extremal-20261017.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    (root/'assets').mkdir(exist_ok=True)
    coords = [(240+109*cos(-pi/2+2*pi*j/5), 185+109*sin(-pi/2+2*pi*j/5)) for j in range(5)]
    render_figure(root/'assets'/'c5-vs-k23.svg', [
        ('C5', c5, [0, 1, 0, 1, 2], coords, 'omega=2, alpha=2, chi=3; 5 edges'),
        ('K2,3', k23, [0, 0, 1, 1, 1], [(145,125),(145,245),(335,85),(335,185),(335,285)],
         'omega=2, alpha=3, chi=2; 6 edges')])
    print(json.dumps({"status": report['status'], "named_graphs": len(outputs),
                      "extremal_rows": len(extrema), "largest_graph_sweep": 32768}))


if __name__ == '__main__':
    main()
