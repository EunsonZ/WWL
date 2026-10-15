"""Small fixed-input PDE checks; JSON stdout only, no external dependencies."""
import json
import math


def shock(left, right, epsilon, xi):
    midpoint = (left + right) / 2
    halfjump = (left - right) / 2
    th = math.tanh(halfjump * xi / (2 * epsilon))
    value = midpoint - halfjump * th
    derivative = -halfjump ** 2 / (2 * epsilon) * (1 - th * th)
    return {"xi": xi, "U": value, "U_prime": derivative,
            "epsilon_U_prime": epsilon * derivative,
            "product_rhs": (value - left) * (value - right) / 2}


def explicit_heat(r, steps):
    values = [(-1.0) ** j for j in range(8)]
    for _ in range(steps):
        values = [values[j] + r * (values[(j+1) % 8] - 2*values[j] + values[(j-1) % 8])
                  for j in range(8)]
    return {"r": r, "steps": steps, "values": values,
            "mean_square": sum(x*x for x in values) / len(values)}


def main():
    alpha = 2/3
    result = {
        "burgers": {"left": 2, "right": -2, "epsilon": 0.1,
                    "speed": 0, "entropy_production": -(2-(-2))**3/12,
                    "samples": [shock(2, -2, .1, x) for x in (-.1, 0, .1)]},
        "material": [{"a": a, "slope": 1/a, "flux": a*(1/a)} for a in (1, 2)],
        "corner": {
            "alpha": alpha, "laplace_coefficient": alpha*(alpha-1)+alpha-alpha**2,
            "H1_radial_integral_0_to_quarter": .25**(2*alpha)/(2*alpha),
            "H2_radial_truncations": [
                {"cutoff": eps, "integral": (eps**(-2/3)-.25**(-2/3))*1.5}
                for eps in (.1, .01, .001)]},
        "heat_mode": [{"t": t, "amplitude": math.exp(-16*t),
                       "mean_square": 1 + .5*math.exp(-32*t)} for t in (0, .1, .25)],
        "explicit_heat": [explicit_heat(r, n) for r in (.4, .6) for n in (1, 2)],
        "constant_reaction": {"c": 2, "blowup_time": .5,
                              "samples": [{"t": t, "u": 2/(1-2*t)} for t in (0, .1, .25, .4)]},
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
