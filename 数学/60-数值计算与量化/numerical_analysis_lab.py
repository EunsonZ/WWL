"""Synthetic numerical-analysis teaching lab. No writes unless --plots is supplied.

Scalar real roots/ODEs; small dense real matrices. NumPy required; plotting
requires the existing Matplotlib installation. This is not a production solver.
"""
import argparse
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np


def controls(tol, maxiter):
    if not math.isfinite(tol) or tol <= 0:
        raise ValueError('tol must be finite and positive')
    if isinstance(maxiter, bool) or not isinstance(maxiter, int) or maxiter < 1:
        raise ValueError('maxiter must be a positive integer')


def finite(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('nonfinite scalar or function value')
    return value


def bisect(f, a, b, tol=1e-10, maxiter=200):
    """Return a floating midpoint, outward position bound, and [point,bound] history.

    Caller must establish continuity and correct signs of computed f values.
    Computed endpoint zeros are rejected: this black-box interface cannot
    distinguish exact roots from underflow/cancellation. Verify any endpoint
    root separately. A midpoint zero retains the existing position bound.
    Reject a zero half-width or an endpoint-rounded midpoint before tolerance.
    The returned point may be rounded away from the exact center. Its bound is
    nextafter(max(point-a, b-point), +inf), which rounds the two endpoint
    distances outward under IEEE-754 round-to-nearest subtraction. This bounds
    position within an established bracket; f is not evaluated by interval arithmetic.
    """
    controls(tol, maxiter)
    a, b = finite(a), finite(b)
    if not a < b or not math.isfinite(b-a):
        raise ValueError('finite representable interval with a < b required')
    fa, fb = finite(f(a)), finite(f(b))
    if fa == 0 or fb == 0:
        raise ArithmeticError('computed endpoint zero; root or sign needs separate certification')
    if (fa > 0) == (fb > 0):
        raise ValueError('endpoint signs do not bracket a root')
    history = []
    for _ in range(maxiter):
        width = b-a
        half = width/2
        m = a+half
        if half == 0:
            raise ArithmeticError('interval half-width underflowed')
        if m == a or m == b:
            raise ArithmeticError('floating-point midpoint stagnated')
        bound = math.nextafter(max(m-a, b-m), math.inf)
        if not math.isfinite(bound):
            raise ArithmeticError('finite outward position bound unavailable')
        fm = finite(f(m))
        history.append([m, bound])
        if bound <= tol:
            return m, bound, history
        if fm == 0:
            # This residual stop retains the bound, which may exceed tol.
            return m, bound, history
        if (fa > 0) != (fm > 0):
            b, fb = m, fm
        else:
            a, fa = m, fm
    raise ArithmeticError('bisection iteration limit')


def newton(f, df, x, tol=1e-12, maxiter=50):
    """Residual-based stopping; no global convergence/error guarantee."""
    controls(tol, maxiter)
    x = finite(x)
    history = [x]
    for _ in range(maxiter):
        fx = finite(f(x))
        if abs(fx) <= tol:
            return x, history
        d = finite(df(x))
        if d == 0:
            raise ArithmeticError('zero derivative')
        y = finite(x-fx/d)
        if y == x:
            raise ArithmeticError('Newton stagnated with nonzero residual')
        history.append(y)
        x = y
    if abs(finite(f(x))) <= tol:
        return x, history
    raise ArithmeticError('Newton iteration limit; possible cycle or divergence')


def barycentric(nodes, values, query):
    """Moderate-degree teaching implementation; returns 1D query values."""
    t, y, x = (np.asarray(v, dtype=float) for v in (nodes, values, query))
    if t.ndim != 1 or len(t) == 0 or y.shape != t.shape or x.ndim != 1:
        raise ValueError('nodes/values/query must be compatible 1D arrays')
    if not all(np.all(np.isfinite(v)) for v in (t, y, x)):
        raise ValueError('finite data required')
    if len(np.unique(t)) != len(t):
        raise ValueError('nodes must be distinct')
    if len(t) == 1:
        return np.full_like(x, y[0])
    scale = np.max(np.abs(t))
    if scale == 0:
        raise ValueError('invalid node scale')
    ts, xs = t/scale, x/scale
    diff = ts[:, None]-ts[None, :]
    np.fill_diagonal(diff, 1.0)
    with np.errstate(over='raise', divide='raise', invalid='raise', under='ignore'):
        w = 1/np.prod(diff, axis=1)
        w /= np.max(np.abs(w))
        if not np.all(np.isfinite(w)) or np.any(w == 0):
            raise ArithmeticError('weight range exceeds teaching implementation')
        out = np.empty_like(x)
        for i, q in enumerate(xs):
            hit = np.flatnonzero(x[i] == t)
            if len(hit):
                out[i] = y[hit[0]]
            else:
                terms = w/(q-ts)
                out[i] = np.dot(terms, y)/np.sum(terms)
    if not np.all(np.isfinite(out)):
        raise ArithmeticError('nonfinite interpolant')
    return out


def ode(f, y0, T, n, method='euler'):
    """Uniform steps on [0,T], scalar real IVP."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError('n must be a positive integer')
    T, y0 = finite(T), finite(y0)
    if T <= 0 or method not in ('euler', 'rk4'):
        raise ValueError('T > 0 and euler/rk4 required')
    h = T/n
    t = np.linspace(0, T, n+1)
    y = np.empty(n+1)
    y[0] = y0
    for i in range(n):
        if method == 'euler':
            y[i+1] = finite(y[i]+h*finite(f(t[i], y[i])))
        else:
            k1 = finite(f(t[i], y[i]))
            k2 = finite(f(t[i]+h/2, y[i]+h*k1/2))
            k3 = finite(f(t[i]+h/2, y[i]+h*k2/2))
            k4 = finite(f(t[i]+h, y[i]+h*k3))
            y[i+1] = finite(y[i]+h*(k1+2*k2+2*k3+k4)/6)
    return t, y


def system(A, b):
    A, b = np.asarray(A, dtype=float), np.asarray(b, dtype=float)
    if A.ndim != 2 or A.shape[0] == 0 or A.shape[0] != A.shape[1] or b.shape != (len(A),):
        raise ValueError('nonempty square A and matching vector b required')
    if not np.all(np.isfinite(A)) or not np.all(np.isfinite(b)):
        raise ValueError('finite system required')
    return A, b


def linear_finite(value, name):
    """Reject unrepresentable intermediate values; finite inputs alone are insufficient."""
    if not np.all(np.isfinite(value)):
        raise ArithmeticError('nonfinite '+name+'; scale exceeds teaching solver range')
    return value


def linear_norm(value, name):
    linear_finite(value, name)
    with np.errstate(over='ignore', invalid='ignore'):
        norm = float(np.linalg.norm(value))
    return linear_finite(norm, name+' norm')


def stationary(A, b, method='jacobi', tol=1e-10, maxiter=200):
    controls(tol, maxiter)
    A, b = system(A, b)
    d = np.diag(A)
    if np.any(d == 0) or method not in ('jacobi', 'gs'):
        raise ValueError('nonzero diagonal and jacobi/gs required')
    x = np.zeros_like(b)
    hist = [x.copy()]
    threshold = linear_finite(tol*max(1.0, linear_norm(b, 'rhs')), 'residual threshold')
    for _ in range(maxiter):
        if linear_norm(b-A@x, 'true residual') <= threshold:
            return x, hist, True
        if method == 'jacobi':
            x = (b-(A-np.diag(d))@x)/d
        else:
            old = x.copy()
            for i in range(len(x)):
                x[i] = (b[i]-A[i, :i]@x[:i]-A[i, i+1:]@old[i+1:])/d[i]
        linear_finite(x, 'stationary iterate')
        hist.append(x.copy())
    return x, hist, bool(linear_norm(b-A@x, 'true residual') <= threshold)


def cg(A, b, tol=1e-10, maxiter=200):
    controls(tol, maxiter)
    A, b = system(A, b)
    # Require the supplied matrix itself to be symmetric; do not silently symmetrize.
    if not np.array_equal(A, A.T):
        raise ValueError('CG requires a symmetric matrix')
    try:
        np.linalg.cholesky(A)
    except np.linalg.LinAlgError as exc:
        raise ValueError('CG requires a positive definite matrix') from exc
    x = np.zeros_like(b)
    r, p = b.copy(), b.copy()
    hist = [x.copy()]
    threshold = linear_finite(tol*max(1.0, linear_norm(b, 'rhs')), 'residual threshold')
    for _ in range(maxiter):
        if linear_norm(b-A@x, 'true residual') <= threshold:
            return x, hist, True
        rr = linear_finite(float(r@r), 'CG residual inner product')
        Ap = linear_finite(A@p, 'CG matrix-vector product')
        curvature = linear_finite(float(p@Ap), 'CG curvature')
        if curvature <= 0 or rr == 0:
            raise ArithmeticError('CG breakdown before true residual tolerance')
        alpha = linear_finite(rr/curvature, 'CG step')
        x = linear_finite(x+alpha*p, 'CG iterate')
        rnew = linear_finite(r-alpha*Ap, 'CG recurrence residual')
        rrnew = linear_finite(float(rnew@rnew), 'CG new residual inner product')
        beta = linear_finite(rrnew/rr, 'CG direction coefficient')
        p = linear_finite(rnew+beta*p, 'CG direction')
        r = rnew
        hist.append(x.copy())
    return x, hist, bool(linear_norm(b-A@x, 'true residual') <= threshold)


def selfcheck():
    checks = []
    def check(name, ok):
        if not ok:
            raise AssertionError(name)
        checks.append(name)
    f = lambda x: x*x-2
    root, bound, bh = bisect(f, 1., 2.)
    with localcontext() as ctx:
        ctx.prec = 60
        true_error = abs(Decimal(root)-Decimal(2).sqrt())
        check('bisection bound vs 60-digit Decimal sqrt', true_error <= Decimal(bound))
    check('bisection requested width', bound <= 1e-10)
    midpoint, midpoint_bound, _ = bisect(lambda x:1e-300*(x-1e-100),-1.,1.)
    check('midpoint underflow retains outward bracket bound', midpoint == 0. and midpoint_bound >= 1.)
    tiny = math.ulp(0.)
    tiny_mid, tiny_bound, _ = bisect(lambda x:x-tiny,0.,2*tiny,tol=tiny)
    check('representable subnormal midpoint keeps outward positive bound', tiny_mid == tiny and tiny_bound >= tiny)
    odd_mid, odd_bound, _ = bisect(lambda x:2*x-5*tiny,0.,5*tiny,tol=5*tiny)
    check('odd subnormal width gets conservative endpoint-distance bound', odd_mid == 2*tiny and odd_bound >= 3*tiny)
    with localcontext() as ctx:
        ctx.prec = 100
        left, right = Decimal(.1), Decimal(.2)
        for side, target in [('left',left+Decimal(2)**-60), ('right',right-Decimal(2)**-60)]:
            point, radius, _ = bisect(lambda x:float(Decimal(x)-target),.1,.2,tol=.1)
            check(side+' near-endpoint root vs exact Decimal position error', abs(Decimal(point)-target) <= Decimal(radius))
            check(side+' outward bound covers exact distances to both endpoints', max(Decimal(point)-left,right-Decimal(point)) <= Decimal(radius))
        point, radius, trace = bisect(lambda x:float(Decimal(x)-(left+Decimal(2)**-60)),.1,.2,tol=.05)
        check('stop uses outward bound instead of nominal half-width', len(trace) > 1 and radius <= .05)
        check('refined returned point vs near-endpoint Decimal root', abs(Decimal(point)-(left+Decimal(2)**-60)) <= Decimal(radius))
    nr, nh = newton(f, lambda x: 2*x, 1.)
    check('Newton rational first two steps', nh[1] == 1.5 and abs(nh[2]-17/12) < 1e-15)
    check('Newton independent sqrt residual', abs(nr-math.sqrt(2)) < 1e-12)
    check('Newton convergence on final allowed update', newton(lambda x:x, lambda x:1.,1.,maxiter=1)[0] == 0.)
    q = np.linspace(-.5, 2.5, 31)
    check('barycentric exact quadratic including extrapolation', np.max(abs(barycentric([0,1,2],[1,2,5],q)-(q*q+1))) < 1e-13)
    check('barycentric node values', np.array_equal(barycentric([0,1,2],[1,2,5],[0,1,2]), [1,2,5]))
    R = lambda z: 1+z+z*z/2+z**3/6+z**4/24
    for method in ('euler','rk4'):
        _, y = ode(lambda t,y: -y, 1., 1., 8, method)
        expected = (1-1/8)**8 if method == 'euler' else R(-1/8)**8
        check(method+' vs independent closed recurrence', abs(y[-1]-expected) < 1e-14)
        errors = [abs(ode(lambda t,y:-y,1.,1.,n,method)[1][-1]-math.exp(-1)) for n in (16,32,64)]
        p = math.log2(errors[1]/errors[2])
        check(method+' observed order range', .9 < p < 1.1 if method == 'euler' else 3.9 < p < 4.1)
    A = np.array([[4.,1.],[1.,3.]])
    b = np.array([1.,2.])
    exact = np.array([1/11,7/11])
    for method in ('jacobi','gs','cg'):
        x,hist,ok = cg(A,b) if method=='cg' else stationary(A,b,method)
        check(method+' vs rational solution', ok and np.linalg.norm(x-exact) < 1e-9)
    _, hist, ok = stationary([[1.,2.],[2.,1.]],[1.,1.], maxiter=8)
    check('Jacobi invertible counterexample diverges', not ok and np.linalg.norm(hist[-1]) > np.linalg.norm(hist[1]))
    rejects = [
        ('minimum subnormal half-width underflow', lambda: bisect(lambda x:2*x-tiny,0.,tiny,tol=tiny), ArithmeticError),
        ('adjacent normal floats midpoint stagnation before tolerance', lambda: bisect(lambda x:(x-1.)-math.ulp(1.)/2,1.,math.nextafter(1.,math.inf),tol=1.), ArithmeticError),
        ('left endpoint underflow', lambda: bisect(lambda x:1e-300*(x-1e-100),0.,1.), ArithmeticError),
        ('right endpoint underflow', lambda: bisect(lambda x:1e-300*(x+1e-100),-1.,0.), ArithmeticError),
        ('exact left endpoint root needs separate certification', lambda: bisect(lambda x:x,0.,1.), ArithmeticError),
        ('exact right endpoint root needs separate certification', lambda: bisect(lambda x:x-1.,0.,1.), ArithmeticError),
        ('no sign bracket', lambda: bisect(lambda x:x*x+1,-1,1), ValueError),
        ('nonfinite f', lambda: bisect(lambda x:float('nan'),-1,1), ValueError),
        ('Newton zero derivative', lambda: newton(lambda x:x*x+1,lambda x:2*x,0), ArithmeticError),
        ('Newton cycle', lambda: newton(lambda x:x**3-2*x+2,lambda x:3*x*x-2,0,maxiter=6), ArithmeticError),
        ('repeated interpolation nodes', lambda: barycentric([0,0],[1,2],[.5]), ValueError),
        ('invalid ODE steps', lambda: ode(lambda t,y:y,1,1,0), ValueError),
        ('CG non-SPD', lambda: cg([[1.,2.],[2.,1.]],[1.,1.]), ValueError),
        ('zero Jacobi diagonal', lambda: stationary([[0.,1.],[1.,2.]],[1.,1.]), ValueError),
        ('system shape', lambda: cg([[1.,0.],[0.,1.]],[1.]), ValueError),
        ('stationary finite rhs with overflowing norm', lambda: stationary([[1.]],[1e308]), ArithmeticError),
        ('CG finite rhs with overflowing norm', lambda: cg([[1.]],[1e308]), ArithmeticError),
        ('stationary finite norm with overflowing threshold', lambda: stationary([[1.]],[1e150],tol=1e308), ArithmeticError),
        ('CG finite norm with overflowing threshold', lambda: cg([[1.]],[1e150],tol=1e308), ArithmeticError),
        ('stationary final residual norm overflow', lambda: stationary([[1.,1e308],[1e308,1.]],[1.,1.],maxiter=1), ArithmeticError),
        ('CG matrix-vector product overflow', lambda: cg([[1e308]],[1e100]), ArithmeticError),
        ('CG finite product with curvature overflow', lambda: cg([[1e200]],[1e100]), ArithmeticError),
    ]
    for name, call, error in rejects:
        try:
            call()
        except error:
            check(name+' rejected', True)
        else:
            check(name+' rejected', False)
    return checks


def experiment():
    _, _, bh = bisect(lambda x:x*x-2,1.,2.)
    _, nh = newton(lambda x:x*x-2,lambda x:2*x,1.)
    degrees = [4,8,12,16,20]
    grid = np.linspace(-1,1,4001)
    fun = lambda x: 1/(1+25*x*x)
    interpolation = {}
    for kind in ('equispaced','chebyshev_lobatto'):
        interpolation[kind] = []
        for n in degrees:
            t = np.linspace(-1,1,n+1) if kind=='equispaced' else np.cos(np.pi*np.arange(n+1)/n)
            interpolation[kind].append(float(np.max(abs(barycentric(t,fun(t),grid)-fun(grid)))))
    steps = [8,16,32,64,128]
    errors = {method:[abs(ode(lambda t,y:-y,1.,1.,n,method)[1][-1]-math.exp(-1)) for n in steps] for method in ('euler','rk4')}
    orders = {m:[math.log2(v[i]/v[i+1]) for i in range(len(v)-1)] for m,v in errors.items()}
    A = np.array([[4.,1.],[1.,3.]])
    b, exact = np.array([1.,2.]), np.array([1/11,7/11])
    linear = {}
    for m in ('jacobi','gs','cg'):
        x,hist,ok = cg(A,b) if m=='cg' else stationary(A,b,m)
        linear[m] = {'converged':ok, 'error':[float(np.linalg.norm(z-exact)) for z in hist], 'residual':[float(np.linalg.norm(b-A@z)) for z in hist]}
    return {'data':'synthetic deterministic, dimensionless unless time specified', 'checks':selfcheck(),
            'root':{'bisection':bh,'bisection_halfwidth':[math.ldexp(1.,-k-1) for k in range(len(bh))],'newton':nh}, 'interpolation':{'degrees':degrees,'grid_points':4001,'grid_sample_max':interpolation},
            'ode':{'T':1.,'steps':steps,'h':[1/n for n in steps],'endpoint_error':errors,'observed_orders':orders}, 'linear':linear}


def plot(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'wwl-numerical-analysis','font.family':'DejaVu Sans','font.size':10})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    def save(fig, name):
        fig.suptitle('Synthetic deterministic teaching data', fontsize=10)
        fig.tight_layout()
        fig.savefig(output/name, metadata={'Date':None, 'Creator':'WWL numerical_analysis_lab.py'})
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.4,4.4))
    bh = np.array(report['root']['bisection'])
    ax.semilogy(np.arange(len(bh)),abs(bh[:,0]-math.sqrt(2)),'.-',label='Bisection error')
    ax.semilogy(np.arange(len(bh)),report['root']['bisection_halfwidth'],'--',label='Bracket half-width')
    nh = report['root']['newton']
    ne = abs(np.array(nh)-math.sqrt(2))
    keep = ne>0
    ax.semilogy(np.arange(len(nh))[keep],ne[keep],'o-',label='Newton error')
    ax.set(xlabel='Iteration k (count)',ylabel='Absolute x error (dimensionless)',title='Root of x^2 - 2, bracket [1,2], Newton x0=1')
    ax.legend(); ax.grid(alpha=.3)
    save(fig,'root-convergence.svg')
    fig, axes = plt.subplots(1,2,figsize=(10,4.4))
    g = np.linspace(-1,1,4001)
    f = lambda x:1/(1+25*x*x)
    for kind,label in [('equispaced','Equispaced'),('chebyshev_lobatto','Chebyshev-Lobatto')]:
        n=20
        t = np.linspace(-1,1,n+1) if kind=='equispaced' else np.cos(np.pi*np.arange(n+1)/n)
        axes[0].plot(g,barycentric(t,f(t),g),label=label)
        axes[1].semilogy(report['interpolation']['degrees'],report['interpolation']['grid_sample_max'][kind],'o-',label=label)
    axes[0].plot(g,f(g),'k--',label='1/(1+25x^2)')
    axes[0].set(xlabel='x (dimensionless)',ylabel='Interpolated value (dimensionless)',title='Degree 20; edge oscillation')
    axes[1].set(xlabel='Degree n (count)',ylabel='Grid-sampled max error (dimensionless)',title='4001 test points, not a supremum proof')
    for ax in axes: ax.legend(); ax.grid(alpha=.3)
    save(fig,'interpolation-runge.svg')
    fig, axes = plt.subplots(1,2,figsize=(10,4.4))
    for m in ('euler','rk4'):
        axes[0].loglog(report['ode']['h'],report['ode']['endpoint_error'][m],'o-',label=m)
    axes[0].set(xlabel='h (time unit)',ylabel='Error at T=1 (y unit)',title="y'=-y, y(0)=1; rate=-1/time unit")
    for h in (.1,.25):
        n=round(1/h)
        t,y=ode(lambda t,y:-10*y,1.,1.,n)
        axes[1].plot(t,y,'o-',label=f'Euler h={h}')
    t=np.linspace(0,1,301)
    axes[1].plot(t,np.exp(-10*t),'k--',label='Exact exp(-10t)')
    axes[1].set(xlabel='t (time unit)',ylabel='y (y unit)',title='Stability: z=-1 versus z=-2.5')
    for ax in axes: ax.legend(); ax.grid(alpha=.3)
    save(fig,'ode-order-stability.svg')
    fig, axes = plt.subplots(1,2,figsize=(10,4.4))
    for m in ('jacobi','gs','cg'):
        v=report['linear'][m]
        # Zero points are omitted on log axes; no artificial replacement floor.
        for ax,key in zip(axes,('error','residual')):
            data=np.array(v[key]); keep=data>0
            ax.semilogy(np.arange(len(data))[keep],data[keep],'o-',label=m)
    axes[0].set(xlabel='Iteration k (count)',ylabel='2-norm x error (dimensionless)',title='A=[[4,1],[1,3]], b=[1,2]')
    axes[1].set(xlabel='Iteration k (count)',ylabel='2-norm residual (dimensionless)',title='Fresh residual b-Ax, not recurrence')
    for ax in axes: ax.legend(); ax.grid(alpha=.3)
    save(fig,'linear-convergence.svg')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plots',help='explicit output directory for four original SVG figures')
    args=parser.parse_args()
    report=experiment()
    if args.plots:
        plot(report,args.plots)
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
