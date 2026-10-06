import unittest
from semantics_lab import B, TRUE, FALSE, fv, subst, type_of, step, run, terms, countdown, imp_step, aeval

V = lambda x: ('var', x)
L = lambda x, body: ('lam', x, B, body)
A = lambda f, a: ('app', f, a)


class SemanticsTests(unittest.TestCase):
    def test_hand_trace(self):
        t = A(L('x', ('if', V('x'), FALSE, TRUE)), FALSE)
        self.assertEqual(run(t), ('value', [t, ('if', FALSE, FALSE, TRUE), TRUE]))

    def test_strategy_trace(self):
        arg = A(L('y', V('y')), FALSE)
        t = A(L('x', TRUE), arg)
        self.assertEqual(run(t, 'cbv')[1], [t, A(L('x', TRUE), FALSE), TRUE])
        self.assertEqual(run(t, 'cbn')[1], [t, TRUE])

    def test_capture(self):
        r = subst(L('y', V('x')), 'x', V('y'))
        self.assertEqual(r, L('y_', V('y')))
        self.assertEqual(fv(r), {'y'})

    def test_shadow_and_fresh(self):
        t = L('y', A(V('x'), L('y_', V('y'))))
        self.assertEqual(subst(t, 'x', V('y')), L('y__', A(V('y'), L('y_', V('y__')))))
        self.assertEqual(subst(L('x', V('x')), 'x', TRUE), L('x', V('x')))

    def test_substitution_typing_open(self):
        t = L('y', V('x'))
        self.assertEqual(type_of(t, {'x': B}), ('arrow', B, B))
        self.assertEqual(type_of(subst(t, 'x', V('y')), {'y': B}), ('arrow', B, B))

    def test_closed_requirement(self):
        self.assertEqual(type_of(V('x'), {'x': B}), B)
        self.assertEqual(run(V('x'))[0], 'stuck')

    def test_reverse_preservation_false(self):
        t = A(L('x', TRUE), L('y', V('y')))
        with self.assertRaises(TypeError):
            type_of(t)
        self.assertEqual(step(t), TRUE)
        self.assertEqual(type_of(TRUE), B)

    def test_fix_divergence(self):
        loop = ('fix', L('x', V('x')))
        self.assertEqual(type_of(loop, allow_fix=True), B)
        with self.assertRaises(TypeError):
            type_of(loop)
        self.assertEqual(step(loop), loop)
        t = A(L('x', TRUE), loop)
        self.assertEqual(run(t, 'cbv', 8)[0], 'fuel')
        self.assertEqual(run(t, 'cbn', 1), ('value', [t, TRUE]))

    def test_stuck_and_function_value(self):
        self.assertEqual(run(A(TRUE, FALSE))[0], 'stuck')
        self.assertEqual(run(L('x', A(TRUE, FALSE)))[0], 'value')
        with self.assertRaises(TypeError):
            type_of(L('x', A(TRUE, FALSE)))

    def test_invalid_inputs(self):
        for t in [(), ('bool', 1), ('var', ''), ('app', TRUE), ('lam', 'x', 'Int', TRUE), ([],)]:
            with self.assertRaises(ValueError):
                run(t)
        for fuel in [-1, True, 0.5]:
            with self.assertRaises(ValueError):
                run(TRUE, fuel=fuel)
        with self.assertRaises(ValueError):
            run(TRUE, 'lazy')
        with self.assertRaises(TypeError):
            type_of(('if', TRUE, TRUE, L('x', V('x'))))

    def test_finite_safety_search(self):
        total = good = checked_steps = 0
        for n in range(1, 6):
            for t in terms(n):
                total += 1
                try:
                    ty = type_of(t)
                except TypeError:
                    continue
                good += 1
                status, trace = run(t, fuel=50)
                self.assertEqual(status, 'value')
                for r in trace:
                    self.assertEqual(type_of(r), ty)
                checked_steps += len(trace)-1
        self.assertGreater(good, 100)
        print(f'FINITE nodes<=5 total={total} well_typed={good} transitions={checked_steps}')

    def test_countdown_oracle(self):
        for n in range(31):
            state, heads, steps = countdown(n)
            self.assertEqual(steps, 5*n+1)
            self.assertEqual(state, {'x': 0, 's': n})
            # Independent arithmetic oracle for every loop head, not evaluator vs itself.
            self.assertEqual(heads, [{'x': n-k, 's': k} for k in range(n+1)])
            self.assertTrue(all(h['s'] + h['x'] == n for h in heads))

    def test_imp_assignment_and_bad_state(self):
        state = {'x': 2}
        self.assertEqual(imp_step(('set', 'x', ('+', 'x', 1)), state), (('skip',), {'x': 3}))
        self.assertEqual(state, {'x': 2})
        for c, s in [(('set', 'x', 'z'), {}), (('set', 'x', 1), {'x': True}), (('while', ('>', 1, 0), ('oops',)), {})]:
            with self.assertRaises(ValueError):
                imp_step(c, s)
        with self.assertRaises(ValueError):
            aeval(('/', 1, 0), {})
        with self.assertRaises(ValueError):
            countdown(-1)

    def test_false_invariant_and_nontermination(self):
        body = ('set', 'x', ('-', 'x', 1))
        _, state = imp_step(body, {'x': 1, 's': 0})
        self.assertNotEqual(state['s'] + state['x'], 1)
        c = ('while', ('>', 1, 0), ('skip',))
        s = {}
        for _ in range(12):
            c, s = imp_step(c, s)
        self.assertNotEqual(c, ('skip',))


if __name__ == '__main__':
    unittest.main()
