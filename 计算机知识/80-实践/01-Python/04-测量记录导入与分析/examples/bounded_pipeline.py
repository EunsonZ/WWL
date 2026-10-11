"""Two fixed tasks, bounded queue, one connection owner; not a speed claim."""
import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from measurement_import.core import import_records, read_records
from measurement_import.cli import ensure_distinct

async def run_pipeline(csv_path, database_path, state, *, batch_size=2, capacity=1,
                       fail_id=None, producer_pause=0.001):
    if type(batch_size) is not int or batch_size<=0 or type(capacity) is not int or capacity<=0:
        raise ValueError("batch_size and capacity must be positive non-bool integers")
    ensure_distinct([csv_path,Path(database_path)])
    state.update({"tasks_created":2,"capacity":capacity,"batch_size":batch_size,
                  "queue_high_water":0,"accounted":0,"joined_before_commit":0,
                  "producer_cancelled":False,"producer_closed":False,"consumer_closed":False,
                  "connection_closed":False,"source_closed":False,"completed_batch_count":0,
                  "committed_report":{"read":0,"rejected":0,"inserted":0,"duplicates":0}})
    queue=asyncio.Queue(maxsize=capacity)
    sentinel=object()
    source=None
    db=sqlite3.connect(database_path,isolation_level=None)
    try:
        import_records(db,[],batch_size) # Establish schema before tasks, no data rows.
        with csv_path.open("r",encoding="utf-8",errors="strict",newline="") as source:
            async def producer():
                stream=read_records(source)
                try:
                    for event in stream:
                        await queue.put(event)
                        state["queue_high_water"]=max(state["queue_high_water"],queue.qsize())
                        # Models an awaitable upstream source; no I/O speed benefit is claimed.
                        await asyncio.sleep(producer_pause)
                    await queue.put(sentinel)
                except asyncio.CancelledError:
                    state["producer_cancelled"]=True
                    raise
                finally:
                    stream.close()
                    state["producer_closed"]=True

            def inserted(record):
                if record.sample_id==fail_id:
                    assert db.execute("SELECT code FROM samples WHERE sample_id=?",(record.sample_id,)).fetchone() is not None
                    raise RuntimeError(f"injected after INSERT {fail_id}")

            def completed(report):
                # Aggregate counters, rather than one ever-growing log entry per batch.
                state["completed_batch_count"]+=1
                for key,value in asdict(report).items():
                    state["committed_report"][key]+=value

            async def consumer():
                pending=[]
                try:
                    while True:
                        event=await queue.get()
                        # Dequeue accounting deliberately precedes the business transaction.
                        queue.task_done()
                        if event is sentinel:
                            if pending:
                                report=import_records(db,pending,batch_size,on_insert=inserted)
                                completed(report)
                            return
                        state["accounted"]+=1
                        pending.append(event)
                        if len(pending)==batch_size:
                            # A momentarily empty and fully accounted queue can already join.
                            # This observation says nothing about the following SQLite commit.
                            if queue.empty():
                                await queue.join()
                                state["joined_before_commit"]+=1
                            report=import_records(db,pending,batch_size,on_insert=inserted)
                            completed(report)
                            pending.clear()
                finally:
                    pending.clear()
                    state["consumer_closed"]=True

            try:
                async with asyncio.TaskGroup() as group:
                    group.create_task(producer(),name="measurement-producer")
                    group.create_task(consumer(),name="single-committer")
                await queue.join()
            finally:
                state["final_row_count"]=db.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
                state["final_rows"]=db.execute("SELECT sample_id,tick_ms,code FROM samples ORDER BY sample_id LIMIT 8").fetchall()
                state["final_rows_truncated"]=state["final_row_count"]>8
        state["source_closed"]=source.closed
    finally:
        # File with-statement unwinds before connection cleanup even on ExceptionGroup.
        state["source_closed"]=source is not None and source.closed
        state["in_transaction_at_close"]=db.in_transaction
        db.close()
        state["connection_closed"]=True
    return state

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("csv",type=Path);parser.add_argument("database",type=Path)
    parser.add_argument("--fail-id");parser.add_argument("--capacity",type=int,default=1)
    parser.add_argument("--batch-size",type=int,default=2)
    args=parser.parse_args();state={}
    try:
        asyncio.run(run_pipeline(args.csv,args.database,state,batch_size=args.batch_size,capacity=args.capacity,fail_id=args.fail_id))
    except ExceptionGroup as error:
        state["error_group"]=str(error)
        print(json.dumps(state,sort_keys=True))
        return 1
    print(json.dumps(state,sort_keys=True));return 0

if __name__=="__main__":
    raise SystemExit(main())
