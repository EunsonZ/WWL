"""Fixed-input comparison for finite models, SQLite and existing finite-tree unify.

Run from this directory with Python 3.10+: python3 -B query_contract_examples.py
No service, files or network are opened. SQLite uses a disposable memory database.
Finite-model checks enumerate rule instances, not all first-order models.
The fixed expected answers are in the companion knowledge representation page; this module
reports observations without deriving an oracle from the solver it exercises.
"""
from itertools import product
import json
import sqlite3

from symbolic_ai_lab import Fun, Var, apply, unify

DOMAIN = ("Ada", "Ben", "Cora")
FACTS = frozenset({("Ada", "Ben"), ("Ben", "Cora")})
QUERY = ("Cora", "Ada")
MODELS = {
    "M0": (FACTS, frozenset({("Ada", "Ben"), ("Ben", "Cora"), ("Ada", "Cora")})),
    "M1": (FACTS | {QUERY}, frozenset(product(DOMAIN, repeat=2))),
}

SQL = """
WITH outer_values(x) AS (VALUES (1), (2), (NULL)),
     rhs(y) AS (VALUES (1), (NULL))
SELECT o.x,
       o.x NOT IN (SELECT y FROM rhs),
       NOT EXISTS (SELECT 1 FROM rhs AS r WHERE r.y = o.x),
       o.x IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM rhs AS r WHERE r.y = o.x)
FROM outer_values AS o
ORDER BY o.x IS NULL, o.x
"""


def finite_models():
    """Test every assignment to the universally quantified rule variables."""
    result = {}
    for name, (parent, anc) in MODELS.items():
        r1_failures = [[x, y] for x, y in product(DOMAIN, repeat=2)
                       if (x, y) in parent and (x, y) not in anc]
        r2_failures = [[x, y, z] for x, y, z in product(DOMAIN, repeat=3)
                       if (x, y) in parent and (y, z) in anc and (x, z) not in anc]
        result[name] = {
            "facts_true": FACTS <= parent,
            "r1_failures": r1_failures,
            "r2_failures": r2_failures,
            "query_true": QUERY in anc,
            "parent": sorted(parent),
            "anc": sorted(anc),
        }
    return result


def sql_rows():
    with sqlite3.connect(":memory:") as connection:
        rows = connection.execute(SQL).fetchall()
    return {"engine": "SQLite", "version": sqlite3.sqlite_version, "rows": rows,
            "encoding": "SQL FALSE=0, TRUE=1, UNKNOWN=None; not PostgreSQL execution"}


def render(term):
    if isinstance(term, Var):
        return term.name
    return term.name if not term.args else term.name + "(" + ",".join(map(render, term.args)) + ")"


def observe(left, right, tracked):
    sigma = unify(left, right)
    if sigma is None:
        return {"input": [render(left), render(right)], "unifiable": False}
    return {"input": [render(left), render(right)], "unifiable": True,
            "normalized_variables": [render(apply(v, sigma)) for v in tracked],
            "equal_after_apply": apply(left, sigma) == apply(right, sigma),
            "applied": [render(apply(left, sigma)), render(apply(right, sigma))]}


def finite_tree_examples():
    a, b, c = map(Var, ("alpha", "beta", "gamma"))
    x, y = map(Var, ("x", "y"))
    ada, boolean = Fun("Ada"), Fun("Bool")
    f = lambda t: Fun("f", (t,))
    arrow = lambda s, t: Fun("Arrow", (s, t))
    pair = lambda s, t: Fun("Pair", (s, t))
    return {
        "atom": observe(Fun("P", (x, f(y))), Fun("P", (ada, f(ada))), (x, y)),
        "arrow": observe(arrow(a, b), arrow(b, c), (a, b, c)),
        "changed_constructor": observe(arrow(a, boolean), arrow(boolean, c), (a, c)),
        "indirect_occurs": observe(pair(x, y), pair(f(y), f(x)), (x, y)),
        "type_occurs": observe(a, arrow(a, b), (a, b)),
        "constructor_conflict": observe(Fun("Bool"), Fun("Int"), ()),
        "unifiable_not_entailment": observe(Fun("P", (x,)), Fun("P", (ada,)), (x,)),
    }


def main():
    report = {"models": finite_models(), "sql": sql_rows(), "trees": finite_tree_examples()}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
