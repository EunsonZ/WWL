"""Independent pole/transfer, Decimal difference-equation and fixed-code checks."""
import cmath
from decimal import Decimal, localcontext
from fractions import Fraction
import math
import unittest
import iir_lab as lab


def independent_order(fs, fp, fsb):
    # Find integer feasibility by repeated multiplication, no ceil/log formula.
    ratio = math.tan(math.pi*fsb/fs)/math.tan(math.pi*fp/fs)
    target = (1000**2-1)/((100/99)**2-1)
    product, n = 1., 0
    while product < target:
        product *= ratio**2
        n += 1
    return n


def explicit_decimal_difference(b, a, inputs):
    # Independent direct I form with input/output history, no DFII/SOS state.
    with localcontext() as ctx:
        ctx.prec = 80
        x = [Decimal.from_float(float(v)) for v in inputs]
        y = []
        for n in range(len(x)):
            forward = sum((b[k]*x[n-k] for k in range(min(n+1, len(b)))), Decimal(0))
            feedback = sum((a[k]*y[n-k] for k in range(1, min(n+1, len(a)))), Decimal(0))
            y.append(forward-feedback)
        return y


class IIRTests(unittest.TestCase):
    def close(self, actual, expected, tolerance=1e-11):
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertLess(abs(a-b), tolerance*(1+abs(b)))

    def test_orders_frequency_units_and_complete_bands(self):
        for fs, fp, expected in [(48000, 6000, 27), (96000, 6000, 30), (48000, 5000, 17)]:
            design = lab.design(fs=fs, fp=fp)
            self.assertEqual(design['order'], independent_order(fs, fp, 8000))
            self.assertEqual(design['order'], expected)
            for f in [0, fp, 8000, fs/2]:
                angle = 2*math.pi*f/fs
                actual = abs(lab.response(design['sections'], angle))
                self.assertAlmostEqual(actual, lab.ideal_amplitude(design, angle), places=11)
            self.assertGreaterEqual(lab.ideal_amplitude(design, 2*math.pi*fp/fs), .99)
            self.assertLessEqual(lab.ideal_amplitude(design, 2*math.pi*8000/fs), .001)
            # Dense points are a coefficient/model check; monotonic ideal formula
            # in the manuscript certifies the intervening ideal bands.
            for k in range(501):
                angle = math.pi*k/500
                self.assertAlmostEqual(abs(lab.response(design['sections'], angle)),
                                       lab.ideal_amplitude(design, angle), places=10)
        self.assertAlmostEqual(2/.00025*math.tan(math.pi/4), 8000)

    def test_local_band_enclosure_and_rounded_coefficients(self):
        design = lab.design()
        for theta in [0., .4, .785, 1.047, 2.5, math.pi]:
            cell = lab.amplitude_cell(design['sections'], theta, 1e-5)
            for delta in [-1e-5, -2e-6, 0., 3e-6, 1e-5]:
                value = abs(lab.response(design['sections'], theta+delta))
                self.assertGreaterEqual(value+1e-12, cell['lower'])
                self.assertLessEqual(value-1e-12, cell['upper'])
        for row in design['sections']:
            rounded = [lab.binary32(v) for v in row]
            self.assertLess(lab.section_radius(rounded), 1.)
        for intervals in [0, True, 2.5]:
            with self.assertRaises(ValueError):
                lab.amplitude_estimate(design, intervals=intervals)

    def test_poles_and_sos_signs(self):
        design = lab.design()
        self.assertTrue(all(abs(p) < 1 for p in design['poles']))
        self.assertEqual(len(design['sections']), 14)
        for row in design['sections']:
            b0, b1, b2, _, a1, a2 = row
            self.assertAlmostEqual(b0+b1+b2, 1+a1+a2, places=13)
            self.assertLess(lab.section_radius(row), 1)
        a1, a2 = -1.9802, .9801
        root = (-a1+math.sqrt(a1*a1-4*a2))/2
        self.assertGreater(root, 1)

    def test_exact_section_and_expanded_zero_state_equivalence(self):
        design = lab.design()
        b, a = lab.expand(design['sections'])
        x = [1., 0., 0., 0., 0.] + [.6*math.cos(2*math.pi*n/17) for n in range(75)]
        reference = explicit_decimal_difference(b, a, x)
        direct = lab.decimal_direct(b, a, x)
        sections = lab.decimal_sos(design['sections'], x)
        self.assertEqual(len(a), 28)
        for values in [direct, sections]:
            for actual, target in zip(values, reference):
                self.assertLess(abs(actual-target), Decimal('1e-55'))
        for theta in [.13, .53, .91]:
            q = cmath.exp(-1j*theta)
            product = lab.response(design['sections'], theta)
            poles = design['poles']
            numerator = 1+0j
            denominator = 1+0j
            for p in poles:
                numerator *= (1-p)*(1+q)/2
                denominator *= (1-p*q)
            self.assertLess(abs(product-numerator/denominator), 2e-12)

    def test_phase_derivative_and_ideal_pole_delay_estimate(self):
        design = lab.design()
        for theta in [0., .1, .4, .78]:
            step = 1e-6
            ratio = lab.response(design['sections'], theta+step)/lab.response(design['sections'], theta-step)
            self.assertAlmostEqual(-cmath.phase(ratio)/(2*step),
                                   lab.delay(design['poles'], theta), places=6)
        certificate = lab.ideal_pole_delay_estimate(design)
        self.assertLessEqual(certificate['upper_samples'], certificate['budget_samples'])
        r = .99
        self.assertAlmostEqual((1-r*r)/(1-r)**2, 199)
        self.assertGreater(199/48000, .002)

    def test_outward_operations_against_exact_fraction(self):
        iv = lab.Outward(24)  # force nonterminating ratios and arithmetic rounding
        def enclosed(result, exact):
            self.assertLessEqual(Fraction(result[0]), exact)
            self.assertGreaterEqual(Fraction(result[1]), exact)
        enclosed(iv.div(iv.point(1), iv.point(7)), Fraction(1, 7))
        x = (Decimal('-1.234567890123456789012345678901'), Decimal('2.75'))
        y = (Decimal('-3.1'), Decimal('-0.99999999999999999999999999999'))
        for a in x:
            for b in y:
                enclosed(iv.add(x, y), Fraction(a)+Fraction(b))
                enclosed(iv.sub(x, y), Fraction(a)-Fraction(b))
                enclosed(iv.mul(x, y), Fraction(a)*Fraction(b))
                enclosed(iv.div(x, y), Fraction(a)/Fraction(b))
        enclosed(iv.square(x), Fraction(0))
        for a in x:
            enclosed(iv.square(x), Fraction(a)**2)
        # point converts binary coefficients exactly, independently of context precision.
        with localcontext() as ctx:
            ctx.prec = 3
            self.assertEqual(Fraction(iv.point(.1)[0]), Fraction.from_float(.1))
            enclosed(iv.div(iv.point(1), iv.point(7)), Fraction(1, 7))
        for bad in [True, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                iv.point(bad)
        with self.assertRaises(ValueError):
            iv.div(iv.point(1), (Decimal(-1), Decimal(1)))

    def test_strict_cell_exact_rational_transfer_and_delay(self):
        iv = lab.Outward(40)
        rows = [[.25, .25, 0., 1., -.5, 0.],
                [.0625, .125, .0625, 1., -1., .25]]
        prepared, records = lab.strict_sections(rows, iv)
        self.assertTrue(all(r['exact_schur_conditions'] for r in records))
        # For the second row, Q(c)=(5/4-c)^2. The exact Horner lower
        # bounds on these cells are 2737/10000 and 1209/10000 (>0).
        # The first row has Q(c)=5/4-c, also positive throughout.
        for left, right in [('0.71', '0.72'), ('0.90', '0.901')]:
            cell = lab.strict_cell(prepared, Decimal(left), Decimal(right), iv, True)
            self.assertIsNotNone(cell, 'narrow fixture must prove Q.lower > 0')
            for point in [Fraction(Decimal(left)), Fraction(Decimal(right)),
                          (Fraction(Decimal(left))+Fraction(Decimal(right)))/2]:
                amp, delay = Fraction(1), Fraction(0)
                for row in rows:
                    b0, b1, b2, _, a1, a2 = map(Fraction.from_float, row)
                    # Independent direct polynomial expansion, not lab interval Horner.
                    P = (b0*b0+b1*b1+b2*b2+2*b1*(b0+b2)*point
                         +2*b0*b2*(2*point*point-1))
                    Q = (1+a1*a1+a2*a2+2*a1*(1+a2)*point
                         +2*a2*(2*point*point-1))
                    degree = 1 if b2 == 0 else 2
                    E = a1*a1+2*a2*a2+a1*(1+3*a2)*point+2*a2*(2*point*point-1)
                    amp *= P/Q
                    delay += Fraction(degree, 2)-E/Q
                for name, expected in [('amplitude_squared', amp),
                                       ('group_delay_samples', delay)]:
                    self.assertLessEqual(Fraction(cell[name][0]), expected)
                    self.assertGreaterEqual(Fraction(cell[name][1]), expected)
        # Genuine Nyquist zero, no sqrt or cancellation that turns it negative.
        cell = lab.strict_cell(prepared, Decimal(-1), Decimal(-1), iv, False)
        self.assertEqual(cell['amplitude_squared'], (Decimal(0), Decimal(0)))
        for rows in [[[.1, .2, .1, 1., -2., 1.]],
                     [[.1, .3, .1, 1., -.5, .1]]]:
            with self.assertRaises(ValueError):
                lab.strict_sections(rows, iv)

    def test_strict_cell_wide_positive_denominator_is_unproved(self):
        iv = lab.Outward(40)
        rows = [[.25, .25, 0., 1., -.5, 0.],
                [.0625, .125, .0625, 1., -1., .25]]
        prepared, _ = lab.strict_sections(rows, iv)
        # This is the original failed fixture. Its second denominator is
        # Q(c)=(5/4-c)^2, so Q >= 1/16 > 0 on the entire [.9,1].
        # Horner repeats c: (c-5/2)c+25/16 instead encloses it with
        # lower 25/16-(8/5)*1 = -3/80. Thus a valid transfer function
        # need not be proved by this wide cell; refusal must stay explicit.
        self.assertEqual((Fraction(5, 4)-1)**2, Fraction(1, 16))
        self.assertEqual(Fraction(25, 16)-Fraction(8, 5), Fraction(-3, 80))
        self.assertIsNone(lab.strict_cell(prepared, Decimal('0.9'),
                                         Decimal('1'), iv, True))

    def test_strict_certificate_limits_and_domain(self):
        design = lab.design()
        exhausted = lab.strict_machine_certificate(design, max_depth=1, max_cells=1)
        self.assertFalse(exhausted['certified'])
        self.assertTrue(all(v['partition_covers_closed_domain']
                            for v in exhausted['bands'].values()))
        self.assertTrue(any(v['unresolved_cells'] for v in exhausted['bands'].values()))
        unsupported = lab.strict_machine_certificate(lab.design(fs=96000))
        self.assertFalse(unsupported['certified'])
        self.assertEqual(unsupported['status'], 'unsupported_specification')
        for kwargs in [{'max_depth': 29}, {'max_depth': True}, {'max_cells': 0}]:
            with self.assertRaises(ValueError):
                lab.strict_machine_certificate(design, **kwargs)

    def test_binary32_sos_against_independent_decimal(self):
        design = lab.design()
        x = [.6*math.cos(2*math.pi*1000*n/48000)+.3*math.cos(2*math.pi*10000*n/48000)
             for n in range(512)]
        target = [float(v) for v in lab.decimal_sos(design['sections'], x)]
        for sections in [design['sections'], design['sections'][::-1]]:
            result = lab.float_sos(sections, x)
            self.assertEqual(result['status'], 'complete')
            self.close(result['output'], target, 2e-5)
        self.assertEqual(lab.binary32(1+2**-24), 1.)

    def test_fixed_order_and_existing_limit_cycle(self):
        high, low = lab.fixed_order(True), lab.fixed_order(False)
        self.assertEqual(high['output_codes'][:5], [8, 12, 14, 15, 16])
        self.assertEqual(low['output_codes'][:7], [8, 16, 24, 28, 30, 31, 32])
        self.assertEqual(high['output_codes'][-1], 16)
        self.assertEqual(low['output_codes'][-1], 32)
        self.assertEqual(high['events'][0]['intermediate_codes'][0], 127)
        self.assertGreater(sum(high['saturations']), 0)
        self.assertEqual(sum(low['saturations']), 0)
        self.assertEqual(lab.round_even_ratio(12), 1)  # preserved .75*q0=1
        for numerator, expected in [(40, 2), (56, 4), (-40, -2), (-56, -4)]:
            self.assertEqual(lab.round_even_ratio(numerator), expected)

    def test_boundaries(self):
        for args in [{'fs': True}, {'fp': 0}, {'fsb': 24000}, {'stop': 1},
                     {'pass_error': 0}, {'fp': float('nan')}, {'fs': 1j}]:
            with self.assertRaises(ValueError):
                lab.design(**args)


if __name__ == '__main__':
    unittest.main()
