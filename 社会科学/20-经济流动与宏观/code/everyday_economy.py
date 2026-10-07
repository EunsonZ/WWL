"""Exact arithmetic for four fictional general-education lessons; no tax/product advice.

Import is silent. CLI requires --output to write its JSON; no default write path.
"""
import argparse
import json
from fractions import Fraction as F
from pathlib import Path


def nonnegative_integer(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("expected a nonnegative integer")
    return F(value)


def pit(income):
    x = nonnegative_integer(income)
    return F(min(max(x - 100, 0), 100)) / 10 + F(max(x - 200, 0)) / 5


def indemnity(loss):
    x = nonnegative_integer(loss)
    return min(max(x - 20, 0), 70)


def tariff(amount):
    t = nonnegative_integer(amount)
    p = min(40 + t, F(60))
    demand, supply = 100 - p, p - 20
    imports = demand - supply
    cs, ps = (100 - p) * demand / 2, (p - 20) * supply / 2
    revenue = t * imports
    return {"price": p, "demand": demand, "supply": supply,
            "imports": imports, "cs": cs, "ps": ps,
            "revenue": revenue, "dwl": 2000 - cs - ps - revenue}


def examples():
    sales = [F(100), F(160), F(200)]
    output = [x / 10 for x in sales]
    credits = [F(0), output[0], output[1]]
    net = [a - b for a, b in zip(output, credits)]
    return {"vat": {"output": output, "credit": credits, "net": net,
                    "total": sum(net), "consumer": F(220)},
            "pit": {str(x): pit(x) for x in (180, 220, 250, 260)},
            "budget": {"combined_tax": F(100), "combined_services": F(110),
                       "combined_deficit": F(10), "internal_transfer": F(30)},
            "finance": {"pv": F(105) / F(105, 100),
                        "real_return": F(105, 103) - 1,
                        "expected_terminal": F(99, 100) * 104,
                        "claim_50": indemnity(50), "claim_100": indemnity(100),
                        "claim_200": indemnity(200), "expected_claim": F(7)},
            "trade": {"production_cloth": F(4), "production_wine": F(6),
                      "H_consumption": [F(2), F(3, 2)],
                      "F_consumption": [F(2), F(9, 2)],
                      "H_va": F(140), "F_va": F(60), "world_va": F(200)},
            "tariff": {str(x): tariff(x) for x in (0, 5, 10, 20, 30)},
            "fx": {"E_old": F(7), "E_new": F(77, 10),
                   "inverse_change": F(10, 11) - 1,
                   "forward": F(7) * F(104, 102),
                   "china_CA": F(-100), "china_FA": F(-100),
                   "foreign_CA": F(100), "foreign_FA": F(100),
                   "reserve_example_CA": F(30),
                   "reserve_example_FA": F(10) + 25 - 5}}


def encode(value):
    if isinstance(value, (F, int)) and not isinstance(value, bool):
        value = F(value)
        return {"exact": str(value), "decimal": float(value)}
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [encode(x) for x in value]
    raise TypeError("unexpected output type")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(encode(examples()), ensure_ascii=False,
                                      indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
