"""Finite teaching model for surrogate and decision risks; standard library only.

The single probability Brier convention is used. Log losses use natural logs.
Writes JSON to stdout and never changes input files.
"""
import argparse
from fractions import Fraction
from itertools import product
import json
from math import log, sqrt
from pathlib import Path


def log_risk(eta, q):
    # Sum only true-support labels; zero predicted support gives +infinity.
    values = []
    for weight, predicted in ((eta, q), (1 - eta, 1 - q)):
        if weight:
            if not predicted:
                return float("inf")
            values.append(-float(weight) * log(float(predicted)))
    return sum(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    if data["fixed_tie_rule"] != "predict 1 when probability >= threshold or score >= 0":
        raise ValueError("This script implements only the declared predict-1 tie rule")
    eta = Fraction(data["eta"])
    if not 0 <= eta <= 1:
        raise ValueError("eta outside [0,1]")
    b_star = eta * (1 - eta)
    l_star = log_risk(eta, eta)
    r_star = min(eta, 1 - eta)
    probs = []
    for probe in data["probability_probes"]:
        q = Fraction(probe)
        if not 0 < q < 1:
            raise ValueError("Finite log table requires q in (0,1)")
        # Primary route directly averages losses over observed label values.
        b = sum(weight * (q - y) ** 2 for y, weight in ((0, 1-eta), (1, eta)))
        r = sum(weight * (int(q >= Fraction(1, 2)) != y) for y, weight in ((0, 1-eta), (1, eta)))
        l = log_risk(eta, q)
        probs.append(dict(q=probe, brier=str(b), brier_excess=str(b-b_star), log_nat=l,
                          log_excess_nat=l-l_star, action=int(q >= Fraction(1,2)),
                          classification=str(r), classification_excess=str(r-r_star),
                          brier_conversion=2*sqrt(float(b-b_star)), log_conversion=sqrt(max(0,2*(l-l_star)))))
    hinge = []
    for posterior in data["hinge_etas"]:
        p = Fraction(posterior)
        row = {"eta":posterior, "risks":{}}
        for score in data["hinge_score_probes"]:
            f = Fraction(score)
            row["risks"][score] = str(sum(weight * max(1-y*f, 0) for y,weight in ((1,p),(-1,1-p))))
        hinge.append(row)
    points = [(Fraction(x),int(y),Fraction(weight)) for x,y,weight in data["four_point_distribution"]]
    required_points = [(-1,-1,Fraction(3,8)),(-1,1,Fraction(1,8)),(1,-1,Fraction(1,8)),(1,1,Fraction(3,8))]
    if points != required_points:
        raise ValueError("This interface uses the original four-point distribution")
    four = []
    for ws in data["four_point_w_probes"]:
        w = Fraction(ws)
        if abs(w)>1:
            raise ValueError("Half hinge equality requires abs(w)<=1")
        risk = sum(p*(1-y*w*x)/2 for x,y,p in points)
        crisk = sum(p*(int(w*x >= 0) != int(y==1)) for x,y,p in points)
        four.append(dict(w=ws, score_risk=str(risk), score_excess=str(risk-Fraction(1,4)),
                         classification=str(crisk), classification_excess=str(crisk-Fraction(1,4))))
    n = data["four_point_n"]
    lam = Fraction(data["four_point_lambda"])
    if n != 4 or lam != Fraction(1,2):
        raise ValueError("The training migration uses n=4 and lambda=1/2")
    mean_classification = Fraction(0)
    mean_score = Fraction(0)
    for indices in product(range(len(points)), repeat=n):
        sample = [points[i] for i in indices]
        sample_probability = Fraction(1)
        for _,_,p in sample:
            sample_probability *= p
        avg_t = sum(x*y for x,y,_ in sample)/n
        w = min(Fraction(1),max(Fraction(-1),avg_t/(2*lam)))
        mean_score += sample_probability*sum(p*(1-y*w*x)/2 for x,y,p in points)
        mean_classification += sample_probability*sum(p*(int(w*x>=0)!=int(y==1)) for x,y,p in points)
    eps = Fraction(data["clip_epsilon"])
    if not 0 < eps < Fraction(1,2):
        raise ValueError("epsilon outside (0,1/2)")
    eta_clipped = min(1-eps,max(eps,eta))
    clip_approx = log_risk(eta,eta_clipped)-l_star
    c = -log(float(eps))
    clip_bound = sqrt(2*(c*float(data["normalized_clip_gap"])+clip_approx))
    cfp,cfn=Fraction(data["cost_false_positive"]),Fraction(data["cost_false_negative"])
    threshold=cfp/(cfp+cfn)
    q=Fraction("0.6")
    costs=[cfn*eta,cfp*(1-eta)]
    output=dict(bayes=dict(brier=str(b_star),log_nat=l_star,classification=str(r_star)),
                probability_table=probs,hinge_table=hinge,four_point_table=four,
                finite_training=dict(n=n,lam=str(lam),mean_score=str(mean_score),
                                     mean_classification=str(mean_classification),
                                     mean_classification_excess=str(mean_classification-Fraction(1,4))),
                migration=dict(brier_excess_conversion=2*sqrt(float(data["true_brier_excess"])),
                               restricted_constant_gap="0",restricted_brier_approximation=str((Fraction("0.4")-eta)**2),
                               clip_approx_nat=clip_approx,clip_C_nat=c,clip_bound=clip_bound,
                               cost_threshold=str(threshold),cost_action=int(q>=threshold),
                               cost_risk=str(costs[int(q>=threshold)]),cost_regret=str(costs[int(q>=threshold)]-min(costs))))
    print(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False))


if __name__ == "__main__":
    main()
