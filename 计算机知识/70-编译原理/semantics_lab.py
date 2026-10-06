"""Named Bool STLC + optional fix; separate integer Imp. Python 3.10+.
Tuples are ASTs, never source strings. No general proof is claimed by enumeration.
"""
from functools import lru_cache

B = 'Bool'
TRUE, FALSE = ('bool', True), ('bool', False)


def valid_type(t):
    if t == B:
        return
    if isinstance(t, tuple) and len(t) == 3 and t[0] == 'arrow':
        valid_type(t[1]); valid_type(t[2]); return
    raise ValueError('invalid type')


def valid_term(t):
    if not isinstance(t, tuple) or not t:
        raise ValueError('AST must be a nonempty tuple')
    tag = t[0]
    if not isinstance(tag, str):
        raise ValueError('term tag must be a string')
    if tag == 'bool' and len(t) == 2 and type(t[1]) is bool:
        return
    if tag == 'var' and len(t) == 2 and isinstance(t[1], str) and t[1]:
        return
    if tag == 'lam' and len(t) == 4 and isinstance(t[1], str) and t[1]:
        valid_type(t[2]); valid_term(t[3]); return
    arity = {'app': 3, 'if': 4, 'fix': 2}.get(tag)
    if arity == len(t):
        for child in t[1:]:
            valid_term(child)
        return
    raise ValueError('malformed term')


def fv(t):
    valid_term(t)
    if t[0] == 'var':
        return {t[1]}
    if t[0] == 'bool':
        return set()
    if t[0] == 'lam':
        return fv(t[3]) - {t[1]}
    return set().union(*(fv(c) for c in t[1:]))


def names(t):
    if t[0] == 'lam':
        return {t[1]} | names(t[3])
    if t[0] == 'var':
        return {t[1]}
    if t[0] == 'bool':
        return set()
    return set().union(*(names(c) for c in t[1:]))


def subst(t, x, s):
    """Capture avoiding; fresh name absent from all names, including shadowed ones."""
    valid_term(t); valid_term(s)
    if not isinstance(x, str) or not x:
        raise ValueError('invalid substitution name')
    if t[0] == 'var':
        return s if t[1] == x else t
    if t[0] == 'bool':
        return t
    if t[0] == 'lam':
        y, ty, body = t[1:]
        if y == x or x not in fv(body):
            return t
        if y in fv(s):
            used = names(body) | names(s) | {x, y}
            z = y + '_'
            while z in used:
                z += '_'
            body = subst(body, y, ('var', z))  # stops at inner binders named y
            y = z
        return ('lam', y, ty, subst(body, x, s))
    return (t[0], *(subst(c, x, s) for c in t[1:]))


def type_of(t, env=None, *, allow_fix=False):
    valid_term(t)
    env = {} if env is None else dict(env)
    for ty in env.values():
        valid_type(ty)
    tag = t[0]
    if tag == 'bool':
        return B
    if tag == 'var':
        if t[1] not in env:
            raise TypeError('unbound variable: ' + t[1])
        return env[t[1]]
    if tag == 'lam':
        env[t[1]] = t[2]
        return ('arrow', t[2], type_of(t[3], env, allow_fix=allow_fix))
    ts = [type_of(c, env, allow_fix=allow_fix) for c in t[1:]]
    if tag == 'app' and isinstance(ts[0], tuple) and ts[0][0] == 'arrow' and ts[0][1] == ts[1]:
        return ts[0][2]
    if tag == 'if' and ts[0] == B and ts[1] == ts[2]:
        return ts[1]
    if tag == 'fix' and allow_fix and isinstance(ts[0], tuple) and ts[0][1] == ts[0][2]:
        return ts[0][1]
    raise TypeError('typing rule does not apply: ' + tag)


def value(t):
    valid_term(t)
    return t[0] in {'bool', 'lam'}


def step(t, strategy='cbv'):
    """Return next AST or None (value OR stuck); caller distinguishes them."""
    valid_term(t)
    if strategy not in {'cbv', 'cbn'}:
        raise ValueError('strategy must be cbv or cbn')
    tag = t[0]
    if tag == 'app':
        f, a = t[1:]
        if not value(f):
            r = step(f, strategy)
            return None if r is None else ('app', r, a)
        if strategy == 'cbv' and not value(a):
            r = step(a, strategy)
            return None if r is None else ('app', f, r)
        if f[0] == 'lam':
            return subst(f[3], f[1], a)
    if tag == 'if':
        c, a, b = t[1:]
        if c[0] == 'bool':
            return a if c[1] else b
        r = step(c, strategy)
        return None if r is None else ('if', r, a, b)
    if tag == 'fix':
        f = t[1]
        if f[0] == 'lam':
            return subst(f[3], f[1], t)
        r = step(f, strategy)
        return None if r is None else ('fix', r)
    return None


def run(t, strategy='cbv', fuel=100):
    if type(fuel) is not int or fuel < 0:
        raise ValueError('fuel must be a nonnegative integer')
    valid_term(t)
    if strategy not in {'cbv', 'cbn'}:
        raise ValueError('invalid strategy')
    trace = [t]
    for _ in range(fuel):
        if value(t):
            return 'value', trace
        r = step(t, strategy)
        if r is None:
            return 'stuck', trace
        t = r; trace.append(t)
    if value(t):
        return 'value', trace
    if step(t, strategy) is None:
        return 'stuck', trace
    return 'fuel', trace


@lru_cache(None)
def terms(size, scope=()):
    """Exact node size, binder annotations restricted to Bool / Bool->Bool, no fix."""
    if type(size) is not int or size < 1:
        raise ValueError('positive node size required')
    if size == 1:
        return (TRUE, FALSE, *(('var', x) for x in scope))
    out = []
    x = 'x' + str(len(scope))
    for ty in (B, ('arrow', B, B)):
        out += [('lam', x, ty, b) for b in terms(size-1, scope+(x,))]
    for i in range(1, size-1):
        out += [('app', f, a) for f in terms(i, scope) for a in terms(size-1-i, scope)]
    for i in range(1, size-2):
        for j in range(1, size-1-i):
            k = size-1-i-j
            out += [('if', c, a, b) for c in terms(i, scope) for a in terms(j, scope) for b in terms(k, scope)]
    return tuple(out)


# Imp uses unbounded signed integers, total +/-, > guard; no lambda terms.
def aeval(a, state):
    if type(a) is int:
        return a
    if isinstance(a, str) and a:
        if a not in state:
            raise ValueError('uninitialized variable: ' + a)
        if type(state[a]) is not int:
            raise ValueError('state contains non-integer')
        return state[a]
    if isinstance(a, tuple) and len(a) == 3 and a[0] in {'+', '-'}:
        x, y = aeval(a[1], state), aeval(a[2], state)
        return x+y if a[0] == '+' else x-y
    raise ValueError('invalid arithmetic expression')


def guard(b, state):
    if isinstance(b, tuple) and len(b) == 3 and b[0] == '>':
        return aeval(b[1], state) > aeval(b[2], state)
    raise ValueError('invalid guard')


def valid_command(c):
    if c == ('skip',):
        return
    if not isinstance(c, tuple) or len(c) != 3:
        raise ValueError('malformed command')
    if c[0] == 'set' and isinstance(c[1], str) and c[1]:
        # Validate expression syntax separately from state-dependent initialization.
        def check(a):
            if type(a) is int or isinstance(a, str) and a:
                return
            if isinstance(a, tuple) and len(a) == 3 and a[0] in {'+', '-'}:
                check(a[1]); check(a[2]); return
            raise ValueError('invalid arithmetic expression')
        check(c[2]); return
    if c[0] == 'seq':
        valid_command(c[1]); valid_command(c[2]); return
    if c[0] == 'while' and isinstance(c[1], tuple) and len(c[1]) == 3 and c[1][0] == '>':
        valid_command(('set', '_check', c[1][1])); valid_command(('set', '_check', c[1][2]))
        valid_command(c[2]); return
    raise ValueError('invalid command')


def imp_step(c, state):
    valid_command(c)
    if any(not isinstance(k, str) or not k or type(v) is not int for k, v in state.items()):
        raise ValueError('state must map names to integers')
    state = dict(state)
    if c[0] == 'skip':
        return None
    if c[0] == 'set':
        state[c[1]] = aeval(c[2], state)
        return ('skip',), state
    if c[0] == 'seq':
        if c[1] == ('skip',):
            return c[2], state
        first, state = imp_step(c[1], state)
        return ('seq', first, c[2]), state
    return (('seq', c[2], c) if guard(c[1], state) else ('skip',)), state


def countdown(n):
    if type(n) is not int or n < 0:
        raise ValueError('countdown input must be nonnegative integer')
    c = ('while', ('>', 'x', 0), ('seq', ('set', 's', ('+', 's', 1)), ('set', 'x', ('-', 'x', 1))))
    state = {'x': n, 's': 0}
    heads = [dict(state)]
    steps = 0
    while c != ('skip',):
        c, state = imp_step(c, state); steps += 1
        if c[0] == 'while':
            heads.append(dict(state))
    return state, heads, steps


if __name__ == '__main__':
    ident = ('lam', 'x', B, ('var', 'x'))
    print('identity:', run(('app', ident, FALSE)))
    loop = ('fix', ident)
    for strategy in ('cbv', 'cbn'):
        print(strategy, run(('app', ('lam', 'x', B, TRUE), loop), strategy, 4))
    print('countdown:', countdown(3))
