"""Render the exact saved model sets and time/belief arrays as standalone SVG."""
from pathlib import Path
import argparse
import json
from xml.sax.saxutils import escape


def svg(title,desc,width,height,body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc><rect width="100%" height="100%" fill="white"/><g font-family="sans-serif" font-size="16" fill="#172638">{body}</g></svg>\n'


def default_plot(results):
    # Presentation contract: these named semantic fixtures only; atom order may
    # vary. Modified theories remain analyzable but need their own figure labels.
    cases={c["name"]:c for c in results["default_cases"]}
    for name in ("bird_before","bird_after_penguin"):
        c=cases[name]
        if set(c["atoms"])!={"Bird","Penguin","Fly"} or c["extension_count"]!=1 or c["status"]!="ok":
            raise ValueError("default figure requires the named bird fixtures; inspect JSON for changed theories")
        expected_hard=[]
        for row in range(8):
            v={a:bool(row&(1<<i)) for i,a in enumerate(c["atoms"])}
            if v["Bird"] and (not v["Penguin"] or not v["Fly"]) and (name=="bird_before" or v["Penguin"]):
                expected_hard.append(row)
        expected_literals={"Bird","Fly","!Penguin"} if name=="bird_before" else {"Bird","Penguin","!Fly"}
        if c["hard_models"]!=expected_hard or set(c["extensions"][0]["entailed_literals"])!=expected_literals:
            raise ValueError("default figure labels require original bird semantics, allowing atom reordering")
    groups=cases["two_groups"]
    if set(groups["atoms"])!={"Q","R","Approve"} or groups["status"]!="ok" or groups["extension_count"]!=2 or {frozenset(e["entailed_literals"]) for e in groups["extensions"]}!={frozenset({"Q","R","Approve"}),frozenset({"Q","R","!Approve"})}:
        raise ValueError("default figure requires the original conflicting group fixture")
    body='<text x="25" y="30" font-size="20">Added hard information can retract default conclusions</text>'
    for k,name in enumerate(("bird_before","bird_after_penguin")):
        c=cases[name]; ox=30+k*420
        body+=f'<rect x="{ox}" y="65" width="390" height="245" rx="8" fill="#f3f6f9" stroke="#9aabb8"/><text x="{ox+15}" y="95">{("W0: Bird; Penguin implies Bird and !Fly" if k==0 else "W1 = W0 plus Penguin")}</text><text x="{ox+15}" y="127">{c["extension_count"]} extension; model IDs {c["extensions"][0]["models"]}</text>'
        for i,lit in enumerate(c["extensions"][0]["entailed_literals"]):
            color="#09699b" if lit=="Bird" else ("#b32934" if k==0 else "#087746")
            body+=f'<text x="{ox+35}" y="{169+i*35}" fill="{color}">{escape(lit)}</text>'
    body+='<path d="M 395,333 H 480" stroke="#4c5d70" stroke-width="3"/><text x="25" y="365">The old Fly and !Penguin are retracted, not preserved alongside the new fact.</text>'
    same=cases["bird_before"]["atoms"]==cases["bird_after_penguin"]["atoms"]
    names=("bird_before",) if same else ("bird_before","bird_after_penguin")
    for i,name in enumerate(names):
        bits="; ".join(f"bit{j}={a}" for j,a in enumerate(cases[name]["atoms"]))
        label="Both bird cases" if same else name
        body+=f'<text x="25" y="{394+25*i}">{label}: {escape(bits)}. ! = negation.</text>'
    shift=25*(len(names)-1)
    c=cases["two_groups"]
    body+=f'<text x="25" y="{440+shift}" font-size="19">Conflicting defaults: alternatives are separate extensions</text>'
    for k,e in enumerate(c["extensions"]):
        ox=30+k*420
        body+=f'<rect x="{ox}" y="{462+shift}" width="390" height="115" rx="8" fill="#f3f6f9" stroke="#9aabb8"/><text x="{ox+15}" y="{493+shift}">Extension {k+1}: models {e["models"]}</text><text x="{ox+15}" y="{533+shift}">{escape(", ".join(e["entailed_literals"]))}</text>'
    bits="; ".join(f"bit{j}={a}" for j,a in enumerate(c["atoms"]))
    body+=f'<text x="25" y="{600+shift}" font-size="14">Group IDs: {escape(bits)}.</text>'
    q=c["queries"]["Approve"]
    body+=f'<text x="25" y="{635+shift}">Approve: credulous={str(q["credulous"]).lower()}, skeptical={str(q["skeptical"]).lower()}.</text><text x="25" y="{666+shift}">Do not union the alternatives into both Approve and !Approve.</text>'
    return svg("Default retraction versus multiple extensions","Exact saved extension model IDs and literal consequences for bird_before, bird_after_penguin and conflicting two_groups. Red denotes retracted default consequences, green new hard-supported consequences, blue shared Bird. These are logical sets, not probability weights.",880,700+shift,body)


def temporal_plot(results):
    time=results["time"]; atoms=time["atoms"]; states=time["states"]
    cols=len(states); width=max(880,245+160*(cols-1))
    step=160
    body='<text x="25" y="30" font-size="20">State changes and information changes are different operations</text>'
    for t,state in enumerate(states):
        x=190+step*t
        body+=f'<text x="{x-15}" y="79">t={t}</text>'
        if t<len(time["sequence"]):body+=f'<text x="{x+40}" y="58">{escape(time["sequence"][t])}</text>'
        for i,p in enumerate(atoms):
            y=110+35*i; truth=p in state
            body+=f'<rect x="{x-22}" y="{y-18}" width="45" height="27" fill="{("#09699b" if truth else "#e0e5e9")}"/><text x="{x-4}" y="{y+2}" fill="{("white" if truth else "#536478")}">{int(truth)}</text>'
            if t==0:body+=f'<text x="25" y="{y+2}">{p}</text>'
    body+='<text x="25" y="352">t counts modeled action steps, not seconds. 1=true; 0=false in each complete world.</text>'
    b=time["belief_example"]
    body+='<text x="25" y="400" font-size="19">A separate uncertain scenario: observe AtB, then Holding, then act Drop</text>'
    for i,key in enumerate(("before","after_AtB","after_Holding","after_Drop")):
        x=30+i*210; rows=b[key]
        body+=f'<rect x="{x}" y="425" width="195" height="190" rx="7" fill="#f3f6f9" stroke="#9aabb8"/><text x="{x+10}" y="452">{escape(key)}</text><text x="{x+10}" y="480">{len(rows)} possible {("world" if len(rows)==1 else "worlds")}</text>'
        for j,state in enumerate(rows):
            r="A" if "AtA" in state else "B"
            p="held" if "Holding" in state else ("A" if "PkgA" in state else "B")
            body+=f'<text x="{x+10}" y="{505+j*17}" font-size="14">robot {r}, package {p}</text>'
    body+='<text x="25" y="652">Both observations keep actual world (B, held). Only Drop changes it to (B, B).</text><text x="25" y="684">Before Holding is observed, Drop is not safe in all three possible worlds.</text><text x="25" y="716">An incompatible AtA observation reports conflict; empty belief is not omniscience.</text>'
    return svg("Successor-state truth table and observation filtering","Top: complete true/false fluent snapshots of the saved action sequence. Bottom: a separate six-world uncertainty example, filtered by AtB and Holding observations; the physical world is unchanged until Drop. Times are action indices and counts are world counts, not probabilities or durations.",width,750,body)


def main():
    root=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=root/"results/default-time-results.json")
    parser.add_argument("--output",type=Path,default=root/"results")
    args=parser.parse_args()
    results=json.loads(args.input.read_text())
    args.output.mkdir(parents=True,exist_ok=True)
    for name,content in (("default-extensions.svg",default_plot(results)),("time-and-observation.svg",temporal_plot(results))):
        (args.output/name).write_text(content)
    print("two same-result SVGs written")

if __name__=="__main__": main()
