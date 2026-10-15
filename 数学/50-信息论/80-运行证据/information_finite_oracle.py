"""Independent finite-input arithmetic for #148/#132; evidence, not course source."""
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import product
from math import inf, isclose, log2
import heapq
import json
import platform
import sys
import time


def entropy(probabilities):
    return -sum(float(p) * log2(float(p)) for p in probabilities if p)


def mutual_information(joint):
    left, right = defaultdict(Fraction), defaultdict(Fraction)
    for (x, y), mass in joint.items():
        left[x] += mass
        right[y] += mass
    return sum(float(mass) * log2(float(mass / (left[x] * right[y])))
               for (x, y), mass in joint.items() if mass)


def huffman_lengths(probabilities):
    # Merge the two smallest weights; node contents are symbol/depth pairs.
    queue = [(mass, index, [(symbol, 0)])
             for index, (symbol, mass) in enumerate(probabilities.items())]
    heapq.heapify(queue)
    serial = len(queue)
    while len(queue) > 1:
        p, _, a = heapq.heappop(queue)
        q, _, b = heapq.heappop(queue)
        heapq.heappush(queue, (p + q, serial, [(symbol, depth + 1) for symbol, depth in a + b]))
        serial += 1
    return dict(queue[0][2])


def decode_prefix(payload, code):
    """Decode this finite prefix code via a trie; reject malformed/truncated bits."""
    trie = {}
    for symbol, bits in code.items():
        node = trie
        for bit in bits:
            node = node.setdefault(bit, {})
        node["symbol"] = symbol
    node, symbols = trie, []
    for bit in payload:
        if bit not in ("0", "1") or bit not in node:
            raise ValueError("invalid coded bits")
        node = node[bit]
        if "symbol" in node:
            symbols.append(node["symbol"])
            node = trie
    if node is not trie:
        raise ValueError("truncated coded symbol")
    return "".join(symbols)


def run():
    started = time.perf_counter()
    p = dict(zip("ABCD", map(Fraction, ("1/2", "1/4", "1/8", "1/8"))))
    q = {symbol: Fraction(1, 4) for symbol in p}
    code = dict(zip("ABCD", ("0", "10", "110", "111")))
    fixed = dict(zip("ABCD", ("00", "01", "10", "11")))
    message = "AAAABBCD"
    assert all(not a.startswith(b) for a in code.values() for b in code.values() if a != b)
    assert sum(Fraction(1, 2 ** len(bits)) for bits in code.values()) == 1
    lengths = huffman_lengths(p)
    assert sum(p[s] * lengths[s] for s in p) == Fraction(7, 4)
    hp = entropy(p.values())
    ce = -sum(float(p[s]) * log2(float(q[s])) for s in p)
    kl = sum(float(p[s]) * log2(float(p[s] / q[s])) for s in p)
    nll_p = -sum(log2(float(p[s])) for s in message)
    nll_q = -sum(log2(float(q[s])) for s in message)
    coded = "".join(code[s] for s in message)
    fixed_payload = "".join(fixed[s] for s in message)
    decoded = decode_prefix(coded, code)
    inverse_fixed = {bits: symbol for symbol, bits in fixed.items()}
    fixed_decoded = "".join(inverse_fixed[fixed_payload[i:i + 2]] for i in range(0, len(fixed_payload), 2))
    assert decoded == fixed_decoded == message
    for malformed in ("11", "2"):
        try:
            decode_prefix(malformed, code)
        except ValueError:
            pass
        else:
            raise AssertionError("malformed payload was accepted")
    assert (hp, ce, kl, len(coded), len(fixed_payload), nll_p, nll_q) == (
        1.75, 2., .25, 14, 16, 14., 16.)
    phase_rows = []
    for n in (1, 2, 16, 256):
        paths = [tuple((u + t) % 256 for t in range(n)) for u in range(256)]
        joint = Counter(paths)
        joint_h = entropy(Fraction(count, 256) for count in joint.values())
        marginals = [entropy(Fraction(count, 256) for count in Counter(path[t] for path in paths).values())
                     for t in range(n)]
        assert joint_h == 8 and all(h == 8 for h in marginals)
        prefix_h = entropy(Fraction(count, 256) for count in Counter(path[:-1] for path in paths).values())
        phase_rows.append({"n": n, "enumerated_paths": len(paths), "joint_entropy_bits": joint_h,
                           "each_marginal_bits": 8, "entropy_per_symbol_bits": joint_h / n,
                           "conditional_after_first_bits": joint_h - prefix_h if n > 1 else None})
    window = tuple(range(256))
    damaged = list(window)
    damaged[128] = 0
    def q1_nll(path):
        if any(b != (a + 1) % 256 for a, b in zip(path, path[1:])):
            return inf
        return 8.
    assert entropy(Fraction(c, 256) for c in Counter(window).values()) == 8
    assert q1_nll(window) == 8 and q1_nll(damaged) == inf
    q0_nll = -sum(log2(1 / 256) for _ in window)
    assert q0_nll == 2048
    # Enumerate latent X and independent flip noises E1,E2, keeping rational mass.
    flip_p, flip_q = Fraction(1, 10), Fraction(1, 5)
    xy, xz = defaultdict(Fraction), defaultdict(Fraction)
    for x, e1, e2 in product((0, 1), repeat=3):
        mass = Fraction(1, 2) * (flip_p if e1 else 1 - flip_p) * (flip_q if e2 else 1 - flip_q)
        y, z = x ^ e1, x ^ e1 ^ e2
        xy[x, y] += mass
        xz[x, z] += mass
    cascade = sum(mass for (x, z), mass in xz.items() if x != z)
    assert cascade == Fraction(13, 50)
    ixy, ixz = mutual_information(xy), mutual_information(xz)
    assert isclose(ixy, 1 - entropy((flip_p, 1 - flip_p)), abs_tol=1e-14)
    assert isclose(ixz, 1 - entropy((cascade, 1 - cascade)), abs_tol=1e-14)
    assert ixz <= ixy
    bsc = Fraction(1, 10)
    grid = []
    for i in range(1001):
        input_p = Fraction(i, 1000)
        output_p = input_p * (1 - bsc) + (1 - input_p) * bsc
        grid.append(entropy((output_p, 1 - output_p)) - entropy((bsc, 1 - bsc)))
    maximizer = max(range(len(grid)), key=grid.__getitem__)
    assert maximizer == 500
    rd_rows = []
    for d in map(Fraction, ("0", "1/10", "1/4", "1/2")):
        joint = {(x, y): Fraction(1, 2) * (d if x != y else 1 - d)
                 for x, y in product((0, 1), repeat=2)}
        measured_distortion = sum(mass for (x, y), mass in joint.items() if x != y)
        rate = mutual_information(joint)
        assert measured_distortion == d
        assert isclose(rate, 1 - entropy((d, 1 - d)), abs_tol=1e-14)
        rd_rows.append({"distortion": str(d), "rate_bits": rate})
    return {"environment": {"python": sys.version, "platform": platform.platform()},
            "inputs": {"p": {s: str(v) for s, v in p.items()}, "q": "uniform four symbols",
                       "message": message, "prefix_code": code, "fixed_code": fixed,
                       "flip_p": str(flip_p), "flip_q": str(flip_q), "seed": None},
            "symbol_information": {"entropy_bits": hp, "cross_entropy_bits": ce, "kl_bits": kl,
                                   "perplexity": 2 ** hp, "huffman_lengths": lengths},
            "message": {"payload_bits": len(coded), "fixed_bits": 16,
                        "negative_log_p_bits": nll_p, "negative_log_q_bits": nll_q,
                        "payload": coded, "prefix_decoded": decoded,
                        "fixed_payload": fixed_payload, "fixed_decoded": fixed_decoded,
                        "malformed_prefix_checks": ["truncated 11 rejected", "nonbinary 2 rejected"],
                        "header_or_codebook_bits": "not included"},
            "phase_source_B": phase_rows,
            "source_A": "iid uniform256: analytically H(X1..Xn)=8*n; no exponentially large enumeration",
            "window256": {"frequency_entropy_bits": 8, "q0_nll_bits": q0_nll, "q1_nll_bits": 8,
                          "damaged_q1_nll": "infinity: deterministic transition has zero support"},
            "markov_chain": {"joint_XY": {str(k): str(v) for k, v in xy.items()},
                             "joint_XZ": {str(k): str(v) for k, v in xz.items()},
                             "cascade_flip_probability": str(cascade), "I_XY_bits": ixy, "I_XZ_bits": ixz},
            "BSC_capacity": {"noise": str(bsc), "grid_input_step": ".001", "argmax": ".5",
                             "capacity_bits": grid[maximizer]},
            "fair_bit_Hamming_RD": rd_rows,
            "elapsed_seconds": time.perf_counter() - started,
            "status": "pass", "scope": "finite numerical examples; no general capacity or RD theorem proof"}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
