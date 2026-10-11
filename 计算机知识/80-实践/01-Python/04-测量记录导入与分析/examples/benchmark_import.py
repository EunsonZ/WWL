"""Each measured case is a fresh child: elapsed, Python peak and process peak RSS."""
import argparse
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import sys
import tempfile
import time
import tracemalloc
from measurement_import.core import Record, import_records

def records(count,offset=0):
    for index in range(offset,offset+count):
        yield Record(f"s{index}",index,(index%4+1)*2)

def child(count,batch,case):
    with tempfile.TemporaryDirectory() as directory:
        with closing(sqlite3.connect(Path(directory)/"bench.sqlite",isolation_level=None)) as db:
            if case in ("replay","append"):
                import_records(db,records(count),batch)
            rss_before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            tracemalloc.start()
            start=time.perf_counter()
            report=import_records(db,records(count,count if case=="append" else 0),batch)
            elapsed=time.perf_counter()-start
            _,python_peak=tracemalloc.get_traced_memory()
            tracemalloc.stop()
            rss_after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            expected_count=count*2 if case=="append" else count
            assert db.execute("SELECT COUNT(*) FROM samples").fetchone()[0]==expected_count
            assert report.inserted==(0 if case=="replay" else count)
            # ru_maxrss is bytes on macOS, KiB on Linux; other OS not normalized.
            scale=1 if sys.platform=="darwin" else 1024 if sys.platform.startswith("linux") else None
            return {"case":case,"n":count,"batch_size":batch,"elapsed_seconds":elapsed,
                    "python_peak_bytes":python_peak,"rss_peak_before_raw":rss_before,
                    "rss_peak_after_raw":rss_after,"rss_peak_bytes":rss_after*scale if scale else None,
                    "rss_raw_unit":"bytes" if scale==1 else "KiB" if scale==1024 else "platform-specific",
                    "report":asdict(report),"final_rows":expected_count,
                    "python":sys.version.split()[0],"sqlite":sqlite3.sqlite_version,"platform":platform.platform()}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--child",action="store_true")
    parser.add_argument("--n",type=int,default=2000)
    parser.add_argument("--batch",type=int,default=64)
    parser.add_argument("--case",choices=["new","replay","append"],default="new")
    parser.add_argument("--repeat",type=int,default=3)
    args=parser.parse_args()
    if args.n<=0 or args.batch<=0 or args.repeat<=0:
        parser.error("counts and batch must be positive")
    if args.child:
        print(json.dumps(child(args.n,args.batch,args.case),sort_keys=True));return
    observations=[]
    for count,batch,case in [(args.n,args.batch,"new"),(2*args.n,args.batch,"new"),(args.n,4*args.batch,"new"),
                             (args.n,args.batch,"replay"),(args.n,args.batch,"append")]:
        for iteration in range(args.repeat):
            result=subprocess.run([sys.executable,"-I","-B",str(Path(__file__).resolve()),"--child","--n",str(count),"--batch",str(batch),"--case",case],capture_output=True,text=True,check=True)
            item=json.loads(result.stdout);item["repeat_index"]=iteration;observations.append(item)
    print(json.dumps({"observations":observations,"scope":"generated validated records, local temporary SQLite; elapsed excludes setup for replay/append, includes schema for new; RSS peak is whole process including setup"},sort_keys=True))

if __name__=="__main__":
    main()
