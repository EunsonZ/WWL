"""Fixed complex-coordinate and Cauchy-integral computations; stdout JSON only."""
import cmath
import json
import math


def pair(z):
    return [z.real, z.imag]


def cauchy_fill(z, w, rho, count):
    # d(zeta) = i*zeta*dtheta, so the 1/(2*pi*i) integral is this mean.
    terms = []
    for j in range(count):
        zeta = rho * cmath.exp(2j * math.pi * j / count)
        value = 1 / (2-z) + zeta*zeta
        terms.append(value * zeta / (zeta-w))
    return sum(terms) / count


def main():
    z1, z2 = 1+1j, 2-1j
    f1, f2 = z1, z2 + z1*z1
    inverse = (f1, f2-f1*f1)
    z = 1+1j
    w = 1/z
    jacobian = -1/(z*z)
    vector_z = 2+0j
    vector_w = jacobian*vector_z
    form_z = 1+0j
    form_w = form_z/jacobian
    fills = []
    for n in (16, 32):
        computed = cauchy_fill(.4, .2, .7, n)
        fills.append({"samples": n, "computed": pair(computed),
                      "absolute_error_against_formula": abs(computed-.665)})
    result = {
        "triangular_map": {"input": [pair(z1), pair(z2)],
                           "output": [pair(f1), pair(f2)],
                           "inverse": [pair(v) for v in inverse]},
        "projective_chart": {"z": pair(z), "w": pair(w), "dw_dz": pair(jacobian),
                             "vector_z": pair(vector_z), "vector_w": pair(vector_w),
                             "form_z": pair(form_z), "form_w": pair(form_w),
                             "pairing_z": pair(form_z*vector_z),
                             "pairing_w": pair(form_w*vector_w)},
        "hartogs_fill": fills,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
