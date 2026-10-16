"""Finite Reiter fixed points and explicit successor-state progression.

Standard-library teaching interpreter: <=8 proposition atoms and <=8 defaults;
CNF hard knowledge; conjunctive literal prerequisites, one literal justification
and one literal consequent. The temporal branch imports the published delivery
Action/domain, rather than maintaining a second action table.
"""
from pathlib import Path
from itertools import product
from fractions import Fraction
import argparse
import json
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from symbolic_ai_lab import delivery_domain, result as strips_result


def negate(literal):
    return literal[1:] if literal.startswith("!") else "!"+literal


def validate_case(case):
    atoms=case["atoms"]
    if (not isinstance(atoms,list) or not 1<=len(atoms)<=8
            or any(not isinstance(a,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*",a) for a in atoms)
            or len(set(atoms))!=len(atoms)):
        raise ValueError("expected 1..8 distinct ASCII proposition names")
    def literal(lit):
        if not isinstance(lit,str) or (lit[1:] if lit.startswith("!") else lit) not in atoms:
            raise ValueError("literal must be declared atom or !atom")
    hard=case["hard"]
    if not isinstance(hard,list) or len(hard)>16: raise ValueError("hard CNF needs <=16 clauses")
    for clause in hard:
        if not isinstance(clause,list): raise ValueError("clause must be a literal list; [] is false")
        for lit in clause: literal(lit)
    defaults=case["defaults"]
    if not isinstance(defaults,list) or len(defaults)>8: raise ValueError("expected <=8 defaults")
    names=[]
    for d in defaults:
        names.append(d["id"])
        if not isinstance(d["id"],str) or not d["id"]: raise ValueError("default ID must be nonempty string")
        if not isinstance(d["pre"],list): raise ValueError("prerequisite must be literal conjunction list")
        for lit in d["pre"]: literal(lit)
        literal(d["just"]); literal(d["head"])
    if len(set(names))!=len(names): raise ValueError("duplicate default ID")
    for q in case["queries"]: literal(q)
    return tuple(atoms)


def true_at(row,literal,atoms):
    atom=literal[1:] if literal.startswith("!") else literal
    value=bool(row & (1<<atoms.index(atom)))
    return not value if literal.startswith("!") else value


def models_of(atoms,clauses):
    return frozenset(row for row in range(1<<len(atoms))
                     if all(any(true_at(row,lit,atoms) for lit in clause) for clause in clauses))


def entails(models,literal,atoms):
    # Empty models internally denotes classical inconsistency/Th(false).
    # Public query reporting below separately blocks inconsistent/no-extension inputs.
    return all(true_at(row,literal,atoms) for row in models)


def literals_of(models,atoms):
    return [lit for atom in atoms for lit in (atom,"!"+atom) if entails(models,lit,atoms)]


def gamma(atoms,hard_models,defaults,candidate):
    """Candidate E tests consistency; growing T_i tests prerequisites."""
    current=hard_models
    allowed=[d for d in defaults if not entails(candidate,negate(d["just"]),atoms)]
    trace=[]
    for stage in range(len(defaults)+2):
        enabled=[d for d in allowed if all(entails(current,p,atoms) for p in d["pre"])]
        after=frozenset(row for row in current if all(true_at(row,d["head"],atoms) for d in enabled))
        trace.append({"stage":stage,"before_models":sorted(current),"entailed_literals":literals_of(current,atoms),
                      "enabled_defaults":[d["id"] for d in enabled],"after_models":sorted(after)})
        if after==current:
            return after,trace
        current=after
    raise AssertionError("finite consequent closure exceeded bound")


def analyze(case):
    atoms=validate_case(case)
    hard=models_of(atoms,case["hard"])
    base={"name":case["name"],"atoms":list(atoms),"valuation_encoding":"bit i is atoms[i]; rows 0..2^n-1",
          "hard_models":sorted(hard),"normal":all(d["just"]==d["head"] for d in case["defaults"])}
    if not hard:
        # Reiter has the unique inconsistent extension Th(false), NOT no extension.
        return base|{"status":"hard_inconsistent","extension_count":1,
            "extensions":[{"inconsistent":True,"models":[],"entailed_literals":literals_of(hard,atoms)}],
            "queries":{q:{"status":"blocked_inconsistent_hard_knowledge"} for q in case["queries"]}}
    candidates={}
    for bits in product((False,True),repeat=len(case["defaults"])):
        selected=[d["head"] for bit,d in zip(bits,case["defaults"]) if bit]
        candidate=frozenset(row for row in hard if all(true_at(row,h,atoms) for h in selected))
        # With consistent W any inconsistent E disables all justified defaults,
        # so Gamma(E)=Th(W) != E. Such candidates cannot be extensions.
        if candidate and candidate not in candidates: candidates[candidate]=selected
    extensions=[]; checks=[]
    for candidate,selected in candidates.items():
        generated,trace=gamma(atoms,hard,case["defaults"],candidate)
        fixed=generated==candidate
        record={"candidate_models":sorted(candidate),"selected_heads":selected,"fixed":fixed,
                "blocked_defaults":[d["id"] for d in case["defaults"] if entails(candidate,negate(d["just"]),atoms)],
                "gamma_models":sorted(generated),"trace":trace}
        checks.append(record)
        if fixed: extensions.append({"inconsistent":False,"models":sorted(candidate),
             "entailed_literals":literals_of(candidate,atoms),"selected_heads":selected})
    status="ok" if extensions else "no_extension"
    queries={}
    for q in case["queries"]:
        if not extensions:
            queries[q]={"status":"not_reported_no_extension"}
        else:
            values=[entails(e["models"],q,atoms) for e in extensions]
            queries[q]={"status":"ok","skeptical":all(values),"credulous":any(values),"per_extension":values}
    return base|{"status":status,"extension_count":len(extensions),"extensions":extensions,
       "queries":queries,"candidate_count":len(candidates),"candidate_checks":checks}


def temporal_domain():
    initial,actions,goal=delivery_domain()
    atoms=tuple(sorted(set(initial)|set(goal)|{p for a in actions for s in (a.pre,a.add,a.delete) for p in s}))
    names=[a.name for a in actions]
    if len(names)!=len(set(names)): raise ValueError("primitive action names must be unique")
    table={p:{"positive_actions":[a.name for a in actions if p in a.add],
              "negative_actions":[a.name for a in actions if p in a.delete]} for p in atoms}
    return initial,actions,goal,atoms,table


def state_checked(state,atoms):
    if not isinstance(state,(set,frozenset)) or not state<=set(atoms):
        raise ValueError("state must be a set of declared true atoms; other declared atoms false")
    return frozenset(state)


def ssa_step(state,action,atoms,table):
    state=state_checked(state,atoms)
    if not action.pre<=state: raise ValueError("inapplicable action: missing "+",".join(sorted(action.pre-state)))
    rows=[]; after=set()
    for p in atoms:
        plus=action.name in table[p]["positive_actions"]
        minus=action.name in table[p]["negative_actions"]
        value=plus or (p in state and not minus)
        if value: after.add(p)
        rows.append({"fluent":p,"before":p in state,"positive_cause":plus,"negative_cause":minus,"after":value})
    return frozenset(after),rows


def valid_delivery(state):
    return (sum(p in state for p in ("AtA","AtB"))==1 and
            sum(p in state for p in ("PkgA","PkgB","Holding"))==1 and
            (("HandEmpty" in state)==("Holding" not in state)))


def all_states(atoms):
    return [frozenset(p for p,bit in zip(atoms,bits) if bit) for bits in product((False,True),repeat=len(atoms))]


def observe(belief,atom,value,atoms):
    if not belief: raise ValueError("empty belief is model/observation conflict, not certainty")
    if atom not in atoms or type(value) is not bool: raise ValueError("observation needs declared atom and bool")
    worlds={state_checked(s,atoms) for s in belief}
    after={s for s in worlds if (atom in s)==value}
    if not after: raise ValueError("observation conflicts with every modeled world")
    return after


def act_belief(belief,action,atoms,table):
    if not belief: raise ValueError("cannot execute from empty belief")
    if not all(action.pre<=s for s in belief):
        raise ValueError("action is not applicable in every possible world; cannot silently discard worlds")
    return {ssa_step(s,action,atoms,table)[0] for s in belief}


def encode_belief(belief):
    return sorted([sorted(s) for s in belief])


def time_run(config):
    initial,actions,goal,atoms,table=temporal_domain()
    by_name={a.name:a for a in actions}
    sequence=config["sequence"]
    if not isinstance(sequence,list) or len(sequence)>16: raise ValueError("finite sequence must have <=16 named steps")
    states=[initial]; records=[]
    for t,name in enumerate(sequence):
        if name not in by_name: raise ValueError("unknown primitive action")
        after,rows=ssa_step(states[-1],by_name[name],atoms,table)
        records.append({"time_before":t,"time_after":t+1,"action":name,"rows":rows})
        states.append(after)
    # Relevant finite comparison: same old Action contract, new SSA evaluation.
    comparisons=[]
    for state in all_states(atoms):
        for action in actions:
            if action.pre<=state:
                after,_=ssa_step(state,action,atoms,table)
                expected=strips_result(state,action)
                if after!=expected: raise AssertionError("SSA differs from existing STRIPS")
                comparisons.append({"state":sorted(state),"action":action.name,"after":sorted(after)})
    failures={}
    invalid=initial
    try:
        for name in config["invalid_sequence"]: invalid=ssa_step(invalid,by_name[name],atoms,table)[0]
    except (ValueError,KeyError) as exc: failures["invalid_sequence"]=str(exc)
    else: raise AssertionError("expected bad-order failure")
    # A different, explicitly uncertain initial knowledge scenario.
    belief={s for s in all_states(atoms) if valid_delivery(s)}
    actual=state_checked(frozenset(config["actual_state"]),atoms)
    if actual not in belief: raise ValueError("actual state outside declared belief")
    filtered=observe(belief,config["observation_atom"],True,atoms)
    if actual not in filtered: raise ValueError("supplied observation not true in actual world")
    try: act_belief(filtered,by_name["Drop"],atoms,table)
    except ValueError as exc: failures["drop_before_holding_observation"]=str(exc)
    else: raise AssertionError("expected unsafe action refusal")
    informed=observe(filtered,config["then_observe_atom"],True,atoms)
    after_action=act_belief(informed,by_name["Drop"],atoms,table)
    try: observe(filtered,config["incompatible_observation_atom"],True,atoms)
    except ValueError as exc: failures["conflicting_observation"]=str(exc)
    else: raise AssertionError("expected observation conflict")
    moving=by_name["MoveAB"]
    effect_only=[s for s in all_states(atoms) if moving.add<=s and not moving.delete&s]
    effect_valid=[s for s in effect_only if valid_delivery(s)]
    holding=ssa_step(initial,by_name["Pick"],atoms,table)[0]
    expected=ssa_step(holding,moving,atoms,table)[0]
    omitted_actual=frozenset({"AtB","PkgB","HandEmpty"})
    return {"atoms":list(atoms),"actions":[{"name":a.name,"pre":sorted(a.pre),"add":sorted(a.add),"delete":sorted(a.delete)} for a in actions],
      "ssa_cause_table":table,"sequence":sequence,"states":[sorted(s) for s in states],"steps":records,
      "goal_satisfied":goal<=states[-1],"ssa_strips_comparison_count":len(comparisons),"ssa_strips_comparisons":comparisons,
      "belief_example":{"independent_scenario":True,"before":encode_belief(belief),"after_AtB":encode_belief(filtered),
          "after_Holding":encode_belief(informed),"after_Drop":encode_belief(after_action),
          "actual_before_observations":sorted(actual),"actual_after_observations":sorted(actual),
          "actual_after_Drop":sorted(ssa_step(actual,by_name["Drop"],atoms,table)[0])},
      "effects_only_after_MoveAB":{"model_count":len(effect_only),"valid_delivery_model_count":len(effect_valid),
          "valid_models":[sorted(s) for s in effect_valid],"with_ssa":sorted(expected)},
      "omitted_event":{"predicted_after_MoveAB":sorted(expected),"constructed_actual_after_omitted_Drop":sorted(omitted_actual),
          "match":expected==omitted_actual,"meaning":"declared omitted physical event, not diagnosis from mismatch alone"},
      "failures":failures}


def bayes_comparison():
    prior,lf,ln=Fraction(4,5),Fraction(1,10),Fraction(3,5)
    posterior=prior*lf/(prior*lf+(1-prior)*ln)
    return {"prior_F":str(prior),"likelihood_e_given_F":str(lf),
            "likelihood_e_given_not_F":str(ln),"posterior_F":str(posterior),
            "meaning":"separate stipulated probability model; no conversion of a default to hard negation"}


def run(config):
    return {"model":"finite proposition Reiter defaults; separate finite deterministic action progression",
      "default_cases":[analyze(c) for c in config["default_cases"]],"time":time_run(config["time"]),
      "bayes_comparison":bayes_comparison()}


def main():
    root=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=root/"inputs/default-time.json")
    parser.add_argument("--output",type=Path,default=root/"results/default-time-results.json")
    args=parser.parse_args()
    result=run(json.loads(args.input.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"default_cases":[{k:c[k] for k in ("name","status","extension_count")} for c in result["default_cases"]],
        "temporal_states":result["time"]["states"],"ssa_comparisons":result["time"]["ssa_strips_comparison_count"],
        "failures":result["time"]["failures"]},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
