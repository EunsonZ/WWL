"""Same committed row set: Fraction, independent SQL and optional NumPy."""
import argparse
from contextlib import closing
from fractions import Fraction
import json
import math
from pathlib import Path
import sqlite3
import sys
from measurement_import.core import Record

def compare(path):
    import numpy as np
    if not path.is_file():
        raise FileNotFoundError(path)
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True,isolation_level=None)) as db:
        # Both independent queries see the same read snapshot, even with another writer.
        db.execute("BEGIN")
        rows=db.execute("SELECT sample_id,tick_ms,code FROM samples ORDER BY sample_id").fetchall()
        sql=db.execute("""WITH center AS (SELECT AVG(code) AS mu FROM samples)
            SELECT COUNT(*), SUM(code), AVG(code),
                AVG((code-mu)*(code-mu)),
                CASE WHEN COUNT(*)>1 THEN SUM((code-mu)*(code-mu))/(COUNT(*)-1) END,
                AVG(code*code) FROM samples CROSS JOIN center""").fetchone()
        db.execute("COMMIT")
    if not rows:
        raise ValueError("comparison requires at least one committed record")
    for row in rows:
        Record(*row) # Recheck the declared field contract if another writer touched the DB.
    # The optional branch deliberately materializes its finite selected dataset.
    count=len(rows); values=[r[2] for r in rows]
    mean=Fraction(sum(values),count)
    centered=sum((Fraction(v)-mean)**2 for v in values)
    scalar=[count,sum(values),mean,centered/count,
            centered/(count-1) if count>1 else None,
            Fraction(sum(v*v for v in values),count)]
    codes=np.asarray(values,dtype=np.int64)
    voltage=codes.astype(np.float64) # 1 mV/code, zero offset
    array=[count,float(np.sum(voltage,dtype=np.float64)),
           float(np.mean(voltage,dtype=np.float64)),
           float(np.var(voltage,ddof=0,dtype=np.float64)),
           float(np.var(voltage,ddof=1,dtype=np.float64)) if count>1 else None,
           float(np.mean(voltage*voltage,dtype=np.float64))]
    for reference,query,vector in zip(scalar,sql,array):
        if reference is None:
            assert query is None and vector is None
        else:
            assert math.isclose(float(reference),float(query),rel_tol=1e-12,abs_tol=1e-12)
            assert math.isclose(float(reference),float(vector),rel_tol=1e-12,abs_tol=1e-12)
    return {"row_ids":[r[0] for r in rows],"shape":list(voltage.shape),
            "code_dtype":str(codes.dtype),"voltage_dtype":str(voltage.dtype),
            "columns":["n","sum_mV","mean_mV","pvariance_mV2","variance_mV2","rms2_mV2"],
            "scalar":[str(v) if isinstance(v,Fraction) else v for v in scalar],
            "sql":list(sql),"numpy":array,"ddof":[0,1],
            "versions":{"python":sys.version.split()[0],"numpy":np.__version__,"sqlite":sqlite3.sqlite_version}}

def policy_example():
    import numpy as np
    # Explicit input: a=2, b=missing, c=6, identical c replay. d is absent.
    raw=[("a",2),("b",None),("c",6),("c",6)]
    identities={}; rejected=duplicates=0
    for identity,value in raw:
        if value is None:
            rejected+=1; continue
        if identity in identities:
            if identities[identity]!=value:
                raise ValueError("conflicting identity")
            duplicates+=1
        else: identities[identity]=value
    selected=np.asarray(list(identities.values()),dtype=np.float64)
    raw_array=np.asarray([np.nan if value is None else value for _,value in raw],dtype=np.float64)
    return {"input_ids":[r[0] for r in raw],"policy":"reject missing; identical identity replay skipped; conflict rejected",
            "selected_ids":list(identities),"rejected":rejected,"duplicates":duplicates,
            "selected_mean_mV":float(np.mean(selected)),"selected_pvariance_mV2":float(np.var(selected,ddof=0)),
            "selected_rms2_mV2":float(np.mean(selected*selected)),
            "raw_mean_is_nan":bool(np.isnan(np.mean(raw_array))),
            "drop_missing_only_mean_mV":float(np.nanmean(raw_array)),
            "note":"nanmean still counts the c replay; an array index does not enforce sample identity"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("database",type=Path)
    args=parser.parse_args()
    print(json.dumps({"committed":compare(args.database),"policy_example":policy_example()},sort_keys=True,allow_nan=False))

if __name__=="__main__":
    main()
