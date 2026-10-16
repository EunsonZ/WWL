"""Materialize one-current-booking grain with customer-history/day/channel dimensions."""
import argparse
import json
from pathlib import Path
import sqlite3


STAR_QUERY = """SELECT f.resolution,c.region,SUM(f.duration_seconds),COUNT(*)
FROM booking_fact f JOIN day_dim d ON f.day_id=d.day_id
JOIN channel_dim h ON f.channel_id=h.channel_id
LEFT JOIN customer_dim c ON f.customer_sk=c.sk
GROUP BY f.resolution,c.region ORDER BY f.resolution,c.region"""


def materialize(entities, dimensions, attribution, path):
    if path.exists():
        raise ValueError("star demonstration requires a NEW database")
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE customer_dim(sk TEXT PRIMARY KEY,customer_id TEXT,region TEXT,valid_from INTEGER,valid_to INTEGER)")
        db.execute("CREATE TABLE day_dim(day_id INTEGER PRIMARY KEY,teaching_period INTEGER)")
        db.execute("CREATE TABLE channel_dim(channel_id INTEGER PRIMARY KEY,label TEXT UNIQUE)")
        db.execute("CREATE TABLE booking_fact(fact_id TEXT PRIMARY KEY,customer_id TEXT,day_id INTEGER NOT NULL REFERENCES day_dim(day_id),"
                   "channel_id INTEGER NOT NULL REFERENCES channel_dim(channel_id),customer_sk TEXT REFERENCES customer_dim(sk),"
                   "resolution TEXT NOT NULL,duration_seconds INTEGER NOT NULL,version INTEGER NOT NULL)")
        live = {key: row["after"] for key, row in entities.items() if row["op"] == "put"}
        channels = {s: i+1 for i, s in enumerate(sorted({r["channel"] for r in live.values()}))}
        db.executemany("INSERT INTO customer_dim VALUES(?,?,?,?,?)", [(r["sk"],r["customer_id"],r["region"],r["valid_from"],r["valid_to"]) for r in dimensions])
        db.executemany("INSERT INTO day_dim VALUES(?,?)", [(day,day//10) for day in sorted({r["occurred_day"] for r in live.values()})])
        db.executemany("INSERT INTO channel_dim VALUES(?,?)", [(i,s) for s,i in channels.items()])
        assignments = {r[0]: r for r in attribution["assignments"]}
        for key, r in sorted(live.items()):
            matches, status = assignments[key][1:3]
            sk = matches[0] if status == "matched" else None
            db.execute("INSERT INTO booking_fact VALUES(?,?,?,?,?,?,?,?)", (key,r["customer_id"],r["occurred_day"],channels[r["channel"]],sk,status,r["duration_seconds"],r["version"]))
        db.execute("COMMIT")
        star = [list(row) for row in db.execute(STAR_QUERY)]
        if star != attribution["groups"]:
            raise AssertionError("star keys lost or multiplied the declared grain")
        current = [list(r) for r in db.execute("""SELECT CASE COUNT(c.sk) WHEN 0 THEN 'unmatched' WHEN 1 THEN 'matched' ELSE 'ambiguous' END,
CASE WHEN COUNT(c.sk)=1 THEN MIN(c.region) END,MAX(f.duration_seconds),COUNT(*)
FROM booking_fact f LEFT JOIN customer_dim c ON f.customer_id=c.customer_id AND c.valid_to IS NULL
GROUP BY f.fact_id ORDER BY f.fact_id""")]
        # Collapse per-fact current-dimension classifications; no event-time predicate here.
        grouped = {}
        for status, region, total, count in current:
            key = (status, region)
            s,n = grouped.get(key,(0,0))
            grouped[key] = (s+total,n+1)
        current_groups = [[s,r,*grouped[s,r]] for s,r in sorted(grouped,key=lambda k:(k[0],k[1] or ""))]
        natural = db.execute("SELECT SUM(f.duration_seconds),COUNT(*) FROM booking_fact f LEFT JOIN customer_dim c ON f.customer_id=c.customer_id").fetchone()
        known_only = db.execute("SELECT SUM(f.duration_seconds),COUNT(*) FROM booking_fact f JOIN customer_dim c ON f.customer_sk=c.sk").fetchone()
        distinct = db.execute("SELECT SUM(DISTINCT duration_seconds),COUNT(DISTINCT duration_seconds) FROM booking_fact").fetchone()
        return {"star_query": STAR_QUERY, "star_groups": star,
                "fact_rows": [list(r) for r in db.execute("SELECT * FROM booking_fact ORDER BY fact_id")],
                "customer_rows": [list(r) for r in db.execute("SELECT * FROM customer_dim ORDER BY sk")],
                "day_rows": [list(r) for r in db.execute("SELECT * FROM day_dim ORDER BY day_id")],
                "channel_rows": [list(r) for r in db.execute("SELECT * FROM channel_dim ORDER BY channel_id")],
                "current_dimension_groups": current_groups,
                "wrong_natural_key_join": {"sum_seconds":natural[0],"count":natural[1]},
                "known_only_inner_join": {"sum_seconds":known_only[0],"count":known_only[1]},
                "wrong_sum_distinct": {"sum_seconds":distinct[0],"distinct_measure_values":distinct[1]},
                "foreign_key_check": [list(r) for r in db.execute("PRAGMA foreign_key_check")],
                "integrity": db.execute("PRAGMA integrity_check").fetchone()[0]}
    finally:
        db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--actual",type=Path,required=True)
    p.add_argument("--work",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    spec=json.loads(args.input.read_text())
    actual=json.loads(args.actual.read_text())
    args.work.mkdir()
    entities=dict(actual["final"]["entities"])
    reports={d["revision"]:materialize(entities,d["rows"],actual["dimension_reports"][d["revision"]],args.work/(d["revision"]+".sqlite")) for d in spec["dimension_snapshots"]}
    args.out.write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')


if __name__=="__main__":
    main()
