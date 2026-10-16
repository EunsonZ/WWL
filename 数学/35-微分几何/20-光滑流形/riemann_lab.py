"""Exact metric 2-jets -> Levi-Civita and R, plus fixed shear/warped examples.
Standard library only. CLI writes the finite JSON and SVG to --output-dir.
The finite checks do not prove the general theorems or certify ODE integration.
"""
from fractions import Fraction as Q
from pathlib import Path
import argparse
import json


def zeros(*shape):
    return [zeros(*shape[1:]) for _ in range(shape[0])] if shape else Q(0)


def exact_array(a, shape):
    if not shape:
        if type(a) not in (int, Q):
            raise ValueError('only int/Fraction entries, excluding bool/float')
        return Q(a)
    if not isinstance(a, (list, tuple)) or len(a) != shape[0]:
        raise ValueError('array shape mismatch')
    return [exact_array(x, shape[1:]) for x in a]


def determinant(a):
    n = len(a)
    a = [row[:] for row in a]
    ans = Q(1)
    for i in range(n):
        j = next((j for j in range(i, n) if a[j][i]), None)
        if j is None:
            return Q(0)
        if j != i:
            a[i], a[j] = a[j], a[i]
            ans = -ans
        pivot = a[i][i]
        ans *= pivot
        for j in range(i + 1, n):
            factor = a[j][i] / pivot
            for k in range(i + 1, n):
                a[j][k] -= factor * a[i][k]
    return ans


def inverse(a):
    n = len(a)
    z = [row[:] + [Q(i == j) for j in range(n)] for i, row in enumerate(a)]
    for i in range(n):
        j = next((j for j in range(i, n) if z[j][i]), None)
        if j is None:
            raise ValueError('singular matrix')
        z[i], z[j] = z[j], z[i]
        pivot = z[i][i]
        z[i] = [x / pivot for x in z[i]]
        for j in range(n):
            if j != i:
                factor = z[j][i]
                z[j] = [x - factor * y for x, y in zip(z[j], z[i])]
    return [row[n:] for row in z]


def metric_jet(g, dg, ddg):
    """dg[a][i][j]=partial_a g_ij; ddg[a][b][i][j]=partial_a partial_b g_ij.
    Output Gamma[k][i][j], dGamma[a][k][i][j], R[l][k][i][j].
    Symmetric, positive g and symmetric metric/derivative slots are required.
    This is a pointwise exact evaluator, not a metric field or theorem prover.
    """
    if not isinstance(g, (list, tuple)) or not g:
        raise ValueError('positive dimension required')
    n = len(g)
    g = exact_array(g, (n, n))
    dg = exact_array(dg, (n, n, n))
    ddg = exact_array(ddg, (n, n, n, n))
    for i in range(n):
        for j in range(n):
            if g[i][j] != g[j][i]:
                raise ValueError('g must be symmetric')
            for a in range(n):
                if dg[a][i][j] != dg[a][j][i]:
                    raise ValueError('dg metric slots must be symmetric')
                for b in range(n):
                    if ddg[a][b][i][j] != ddg[a][b][j][i] or ddg[a][b][i][j] != ddg[b][a][i][j]:
                        raise ValueError('ddg symmetries required')
    minors = [determinant([row[:k] for row in g[:k]]) for k in range(1, n + 1)]
    if any(x <= 0 for x in minors):
        raise ValueError('g must be positive definite')
    gi = inverse(g)
    dgi = zeros(n, n, n)
    for a in range(n):
        for k in range(n):
            for l in range(n):
                dgi[a][k][l] = -sum(gi[k][r] * dg[a][r][s] * gi[s][l] for r in range(n) for s in range(n))
    G = zeros(n, n, n)
    dG = zeros(n, n, n, n)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                for l in range(n):
                    c = dg[i][j][l] + dg[j][i][l] - dg[l][i][j]
                    G[k][i][j] += gi[k][l] * c / 2
                    for a in range(n):
                        dc = ddg[a][i][j][l] + ddg[a][j][i][l] - ddg[a][l][i][j]
                        dG[a][k][i][j] += (dgi[a][k][l] * c + gi[k][l] * dc) / 2
    R = zeros(n, n, n, n)
    for l in range(n):
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    R[l][k][i][j] = dG[i][l][j][k] - dG[j][l][i][k] + sum(G[m][j][k] * G[l][i][m] - G[m][i][k] * G[l][j][m] for m in range(n))
    return {'g': g, 'dg': dg, 'ddg': ddg, 'inverse': gi, 'positive_minors': minors, 'Gamma': G, 'dGamma': dG, 'R': R}


def dot(g, v, w):
    return sum(g[i][j] * v[i] * w[j] for i in range(len(g)) for j in range(len(g)))


def curvature(jet, X, Y):
    n = len(jet['g'])
    X, Y = exact_array(X, (n,)), exact_array(Y, (n,))
    gram = dot(jet['g'], X, X) * dot(jet['g'], Y, Y) - dot(jet['g'], X, Y) ** 2
    if gram <= 0:
        raise ValueError('independent vectors required')
    rxyy = [sum(jet['R'][l][k][i][j] * X[i] * Y[j] * Y[k] for i in range(n) for j in range(n) for k in range(n)) for l in range(n)]
    return dot(jet['g'], rxyy, X) / gram


def identities(jet):
    """Finite point checks, never used as a proof of the identities."""
    g, G, R, dg = (jet[k] for k in ('g', 'Gamma', 'R', 'dg'))
    n = len(g)
    count = 0
    for i in range(n):
        for j in range(n):
            for k in range(n):
                assert G[k][i][j] == G[k][j][i]
                assert dg[k][i][j] == sum(g[l][j] * G[l][k][i] + g[i][l] * G[l][k][j] for l in range(n))
                count += 2
                for l in range(n):
                    assert R[l][k][i][j] == -R[l][k][j][i]
                    assert R[l][k][i][j] + R[l][i][j][k] + R[l][j][k][i] == 0
                    for w in range(n):
                        assert sum(g[l2][w] * R[l2][k][i][j] + g[k][l2] * R[l2][w][i][j] for l2 in range(n)) == 0
                        count += 1
                    count += 2
    return count


def warped(f, fp, fpp, dimension=2):
    f, fp, fpp = exact_array([f, fp, fpp], (3,))
    if type(dimension) is not int or dimension not in (2, 3) or f <= 0:
        raise ValueError('positive f and dimension 2 or 3 required')
    n = dimension
    g, dg, ddg = zeros(n, n), zeros(n, n, n), zeros(n, n, n, n)
    for i in range(n):
        g[i][i] = Q(1)
    g[1][1] = f * f
    dg[0][1][1] = 2 * f * fp
    ddg[0][0][1][1] = 2 * (fp * fp + f * fpp)
    return metric_jet(g, dg, ddg)


def shear(u):
    u = exact_array(u, ())
    g = [[1 + 4*u*u, 2*u], [2*u, Q(1)]]
    dg, ddg = zeros(2, 2, 2), zeros(2, 2, 2, 2)
    dg[0] = [[8*u, Q(2)], [Q(2), Q(0)]]
    ddg[0][0][0][0] = Q(8)
    return metric_jet(g, dg, ddg)


def residual(jet, velocity, derivative, vector=None):
    n = len(jet['g'])
    velocity = exact_array(velocity, (n,))
    derivative = exact_array(derivative, (n,))
    vector = velocity if vector is None else exact_array(vector, (n,))
    return [derivative[k] + sum(jet['Gamma'][k][i][j]*velocity[i]*vector[j] for i in range(n) for j in range(n)) for k in range(n)]


def serial(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def build_results():
    rows = []
    checks = 0
    for a in range(-4, 5):
        u = Q(a, 2)
        z = shear(u)
        checks += identities(z)
        expected = zeros(2, 2, 2)
        expected[1][0][0] = Q(2)
        assert z['Gamma'] == expected
        assert z['R'] == zeros(2, 2, 2, 2)
        vel = [Q(1), -2*u]
        res = residual(z, vel, [0, -2])
        par = residual(z, vel, [0, -2], vel)
        assert res == par == [0, 0] and dot(z['g'], vel, vel) == 1
        rows.append({'family': 'flat_shear', 'u': u, 'coordinate_path': [u, -u*u], 'velocity': vel, 'geodesic_residual': res, 'parallel_residual': par, 'norm_squared': Q(1), 'wrong_zero_Gamma_residual': [0, -2], 'jet': z})
    for a in range(-4, 5):
        x = Q(a, 2)
        f, fp, fpp = 1+x*x, 2*x, Q(2)
        for n in (2, 3):
            z = warped(f, fp, fpp, n)
            checks += identities(z)
            X, Y = [1, 0] + ([0] if n == 3 else []), [0, 1] + ([0] if n == 3 else [])
            K = curvature(z, X, Y)
            assert K == -fpp/f
            Kxz = curvature(z, [1,0,0], [0,0,1]) if n == 3 else None
            assert n == 2 or Kxz == 0
            # Along theta=0, x=t, V=2 e1 +3 e2 has components (2,3/f,0).
            V, Vdot = [Q(2), 3/f]+([Q(0)] if n==3 else []), [Q(0), -3*fp/f**2]+([Q(0)] if n==3 else [])
            par = residual(z, X, Vdot, V)
            assert par == [0]*n and dot(z['g'], V, V) == 13
            rows.append({'family': 'warped_polynomial', 'x': x, 'dimension': n, 'f_jet': [f,fp,fpp], 'K_xtheta': K, 'K_xz': Kxz, 'parallel_components': V, 'parallel_residual': par, 'parallel_norm_squared': Q(13), 'jet': z})
    for radius in (Q(1), Q(2), Q(3)):
        for label, f, fp, fpp, target in (
            ('sphere_equator', radius, Q(0), -1/radius, 1/radius**2),
            ('sphere_sin3over5', 3*radius/5, Q(4,5), -Q(3,5)/radius, 1/radius**2),
            ('cylinder', radius, Q(0), Q(0), Q(0))):
            z = warped(f, fp, fpp)
            checks += identities(z)
            assert curvature(z, [1,0], [0,1]) == target
            rows.append({'family': label, 'radius': radius, 'f_jet': [f,fp,fpp], 'K': target, 'jet': z})
    # Nonorthogonal basis test for Gauss equation: II=[[2,1],[1,-3]], g=I.
    X, Y = [Q(2),Q(0)], [Q(1),Q(1)]
    b = [[Q(2),Q(1)],[Q(1),Q(-3)]]
    eye = [[Q(1),Q(0)],[Q(0),Q(1)]]
    numerator = dot(b, Y,Y)*dot(b,X,X)-dot(b,X,Y)**2
    gram = dot(eye,X,X)*dot(eye,Y,Y)-dot(eye,X,Y)**2
    assert (numerator, gram, numerator/gram) == (-28,4,-7)
    holonomy = {'f': '1+x^2', 'a': Q(0), 'b': Q(1), 'Theta': Q(1), 'edge_integrals_omega_ccw': [Q(0),Q(2),Q(0),Q(0)], 'area': Q(4,3), 'integral_KdA': Q(-2), 'parallel_angle_radians': Q(-2), 'half_height_angle_radians': Q(-1)}
    # Public rejection paths: malformed shapes/types, degeneracy, and dependent plane.
    bad = []
    cases = [
        ('empty', lambda: metric_jet([],[],[])),
        ('shape', lambda: metric_jet([[1]],[],[])),
        ('float', lambda: metric_jet([[1.0]],[[[0]]],[[[[0]]]])),
        ('bool', lambda: metric_jet([[True]],[[[0]]],[[[[0]]]])),
        ('zero_metric', lambda: metric_jet([[0]],[[[0]]],[[[[0]]]])),
        ('indefinite', lambda: metric_jet([[1,0],[0,-1]],zeros(2,2,2),zeros(2,2,2,2))),
        ('nonsymmetric', lambda: metric_jet([[1,1],[0,1]],zeros(2,2,2),zeros(2,2,2,2))),
        ('nonpositive_f', lambda: warped(0,1,1)),
        ('dimension', lambda: warped(1,0,0,True)),
        ('dependent_plane', lambda: curvature(shear(0),[1,2],[2,4]))]
    dg = zeros(2,2,2); dg[0][0][1]=Q(1)
    cases.append(('dg_symmetry', lambda: metric_jet(eye,dg,zeros(2,2,2,2))))
    ddg = zeros(2,2,2,2); ddg[0][1][0][0]=Q(1)
    cases.append(('ddg_derivative_symmetry', lambda: metric_jet(eye,zeros(2,2,2),ddg)))
    for name, call in cases:
        try:
            call()
        except ValueError as e:
            bad.append({'case':name,'exception':str(e)})
        else:
            raise AssertionError('expected rejection '+name)
    return {'status': 'PASS', 'date': '2026-10-17', 'convention': 'R[l][k][i][j] means R(partial_i,partial_j)partial_k; K=g(R(X,Y)Y,X)/Gram', 'arithmetic': 'exact fractions as strings; dimensionless fixed inputs; restore curvature unit L^-2', 'rows': rows, 'identity_checks': checks, 'gauss_nonorthogonal': {'II':b,'X':X,'Y':Y,'numerator':numerator,'Gram':gram,'K':numerator/gram}, 'holonomy': holonomy, 'rejections':bad, 'boundary': 'finite metric jets and analytic residuals, not numerical ODE solving, general proof, global geodesic completion, or Obsidian/human acceptance'}


def svg(results):
    # SVG samples are taken from the same exact rows; pixels are display coordinates.
    flat = [r for r in results['rows'] if r['family']=='flat_shear']
    warp = [r for r in results['rows'] if r['family']=='warped_polynomial' and r['dimension']==2]
    def path(points):
        return 'M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in points)
    a = path([(285+90*float(r['u']),130-45*float(r['coordinate_path'][1])) for r in flat])
    k = path([(890+90*float(r['x']),170-70*float(r['K_xtheta'])) for r in warp])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="480" viewBox="0 0 1200 480">
<title>弯坐标与内在曲率分开核验</title><desc>左：欧氏直线在剪切图中为v等于负u平方，Christoffel非零但曲率零。右：正定度量dx平方加(1加x平方)平方dtheta平方，高斯曲率为负2除以1加x平方。同一有限有理输入生成折线，不是空间嵌入图。</desc>
<rect width="1200" height="480" fill="#f8fafc"/><g font-family="sans-serif" fill="#0f172a">
<text x="34" y="36" font-size="24">Nonzero connection coefficients do not determine curvature</text>
<text x="40" y="80" font-size="20">Euclidean shear: x=u, y=v+u²</text><text x="650" y="80" font-size="20">Abstract metric: g=dx²+(1+x²)²dθ²</text>
<path d="M70,130 H510 M285,105 V350 M670,170 H1110 M890,145 V340" stroke="#94a3b8" fill="none"/>
<path d="{a}" fill="none" stroke="#2563eb" stroke-width="3"/><path d="{k}" fill="none" stroke="#b45309" stroke-width="3"/>
<text x="514" y="134" font-size="16">u</text><text x="294" y="112" font-size="16">v</text><text x="1114" y="174" font-size="16">x</text><text x="900" y="154" font-size="16">K</text>
<text x="98" y="155" font-size="16">−2</text><text x="459" y="155" font-size="16">2</text><text x="302" y="318" font-size="16">−4</text>
<text x="704" y="194" font-size="16">−2</text><text x="1067" y="194" font-size="16">2</text><text x="900" y="320" font-size="16">−2</text>
<text x="45" y="377" font-size="18">v=−u²; Gamma^v_uu=2; R=0; speed²=1</text><text x="650" y="377" font-size="18">K=−2/(1+x²); no 3D embedding asserted</text>
<text x="45" y="414" font-size="17">Acceleration (0,−2) + correction (0,2) = 0</text><text x="650" y="414" font-size="17">[0,1]×[0,1]: integral omega=2; turn=−2 rad</text>
<text x="34" y="459" font-size="15">Dimensionless inputs; physical K has unit L^-2. Polylines join 9 rational samples; general proofs are in the lessons.</text>
</g></svg>'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()
    result = build_results()
    (args.output_dir/'实践结果').mkdir(parents=True, exist_ok=True)
    (args.output_dir/'assets').mkdir(parents=True, exist_ok=True)
    (args.output_dir/'实践结果/riemann-20261017.json').write_text(json.dumps(serial(result),ensure_ascii=False,indent=2)+'\n')
    (args.output_dir/'assets/connection-curvature.svg').write_text(svg(result))
    print(json.dumps({'status':result['status'],'rows':len(result['rows']),'identity_checks':result['identity_checks'],'rejections':len(result['rejections']),'output_dir':str(args.output_dir)},ensure_ascii=False))


if __name__ == '__main__':
    main()
