"""Independent rows for optional analysis and two-task cancellation examples."""
import asyncio
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from measurement_import.core import Record, import_records

EXAMPLES=Path(__file__).resolve().parents[1]/"examples"
def load(name):
    spec=importlib.util.spec_from_file_location(name,EXAMPLES/(name+".py"))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/"input.csv";self.db=self.root/"records.sqlite"
        self.source.write_text("sample_id,tick_ms,code\na,0,2\nb,1000,4\nc,2000,6\nd,3000,8\n")
        self.pipeline=load("bounded_pipeline")
    def rows(self):
        with closing(sqlite3.connect(self.db)) as db:
            return db.execute("SELECT sample_id,tick_ms,code FROM samples ORDER BY sample_id").fetchall()
    def test_failure_c_cancels_sibling_and_closes_then_replay(self):
        state={}
        with self.assertRaises(ExceptionGroup):
            asyncio.run(self.pipeline.run_pipeline(self.source,self.db,state,fail_id="c"))
        self.assertEqual(self.rows(),[("a",0,2),("b",1000,4)])
        self.assertEqual(state["accounted"],4)
        self.assertGreaterEqual(state["joined_before_commit"],2)
        self.assertTrue(state["producer_cancelled"])
        self.assertTrue(all(state[k] for k in ("producer_closed","consumer_closed","source_closed","connection_closed")))
        self.assertFalse(state["in_transaction_at_close"])
        retry={};asyncio.run(self.pipeline.run_pipeline(self.source,self.db,retry))
        self.assertEqual(self.rows(),[("a",0,2),("b",1000,4),("c",2000,6),("d",3000,8)])
        self.assertEqual(retry["committed_report"]["inserted"],2)
        self.assertEqual(retry["committed_report"]["duplicates"],2)
        self.assertLessEqual(retry["queue_high_water"],1)
        self.assertEqual(retry["tasks_created"],2)
    def test_batch_four_rolls_back_all_and_capacity_three_finishes(self):
        state={}
        with self.assertRaises(ExceptionGroup):
            asyncio.run(self.pipeline.run_pipeline(self.source,self.db,state,batch_size=4,fail_id="c"))
        self.assertEqual(self.rows(),[])
        success={};asyncio.run(self.pipeline.run_pipeline(self.source,self.db,success,capacity=3,producer_pause=0))
        self.assertEqual(len(self.rows()),4)
        self.assertLessEqual(success["queue_high_water"],3)
    def test_diagnostic_preview_is_bounded_and_counters_are_complete(self):
        self.source.write_text("sample_id,tick_ms,code\n"+"".join(f"s{i},{i},2\n" for i in range(20)))
        state={};asyncio.run(self.pipeline.run_pipeline(self.source,self.db,state,producer_pause=0))
        self.assertEqual(len(self.rows()),20)
        self.assertEqual(state["final_row_count"],20)
        self.assertEqual(len(state["final_rows"]),8)
        self.assertTrue(state["final_rows_truncated"])
        self.assertEqual(state["committed_report"],{"read":20,"rejected":0,"inserted":20,"duplicates":0})
        self.assertEqual(state["completed_batch_count"],10)
    def test_external_cancel_unstarted_batch_and_tasks_cleaned(self):
        state={}
        async def scenario():
            task=asyncio.create_task(self.pipeline.run_pipeline(self.source,self.db,state,producer_pause=1))
            while state.get("accounted",0)<1:
                await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertEqual(len([t for t in asyncio.all_tasks() if t is not asyncio.current_task()]),0)
        asyncio.run(scenario())
        self.assertEqual(self.rows(),[])
        self.assertTrue(state["connection_closed"] and state["source_closed"])

class ScienceTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("numpy"),"optional NumPy not installed; standard-library tests still run")
    def test_exact_row_set_and_numpy_ddof_policy(self):
        science=load("scientific_compare")
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"db.sqlite"
            with closing(sqlite3.connect(path,isolation_level=None)) as db:
                import_records(db,[Record("a",0,2),Record("b",1000,4),Record("c",2000,6),Record("d",3000,8)])
            result=science.compare(path)
            self.assertEqual(result["row_ids"],["a","b","c","d"])
            self.assertEqual(result["shape"],[4]);self.assertEqual(result["voltage_dtype"],"float64")
            self.assertEqual(result["scalar"],[4,20,"5","5","20/3","30"])
            self.assertEqual(result["sql"],[4,20,5.0,5.0,20/3,30.0])
            self.assertEqual(result["numpy"],[4,20.0,5.0,5.0,20/3,30.0])
            policy=science.policy_example()
            self.assertEqual(policy["selected_ids"],["a","c"])
            self.assertEqual((policy["selected_mean_mV"],policy["selected_pvariance_mV2"],policy["selected_rms2_mV2"]),(4.0,4.0,20.0))
            self.assertTrue(policy["raw_mean_is_nan"])
            self.assertAlmostEqual(policy["drop_missing_only_mean_mV"],14/3)
            # A WAL writer changes a between the row and aggregate SELECTs.
            # The comparison must still see the original a=2 snapshot for both.
            real_connect=sqlite3.connect
            with closing(real_connect(path,isolation_level=None)) as db:
                db.execute("PRAGMA journal_mode=WAL")
            class HookedConnection(sqlite3.Connection):
                def execute(self,query,*args,**kwargs):
                    if query.lstrip().startswith("WITH center"):
                        with closing(real_connect(path,isolation_level=None)) as writer:
                            writer.execute("UPDATE samples SET code=9 WHERE sample_id='a'")
                    return super().execute(query,*args,**kwargs)
            def reader(*args,**kwargs):
                return real_connect(*args,factory=HookedConnection,**kwargs)
            with patch.object(science.sqlite3,"connect",reader):
                snapshot=science.compare(path)
            self.assertEqual(snapshot["scalar"],[4,20,"5","5","20/3","30"])
            with closing(real_connect(path)) as db:
                self.assertEqual(db.execute("SELECT code FROM samples WHERE sample_id='a'").fetchone()[0],9)
            with closing(real_connect(path,isolation_level=None)) as db:
                db.execute("DELETE FROM samples WHERE sample_id!='a'")
            single=science.compare(path)
            self.assertIsNone(single["scalar"][4]);self.assertIsNone(single["numpy"][4])
            with closing(real_connect(path,isolation_level=None)) as db:db.execute("DELETE FROM samples")
            with self.assertRaises(ValueError):science.compare(path)

class BenchmarkTests(unittest.TestCase):
    def test_small_fresh_process_case_counts_and_units(self):
        proc=subprocess.run([sys.executable,"-I","-B",str(EXAMPLES/"benchmark_import.py"),"--n","12","--batch","4","--repeat","1"],capture_output=True,text=True,check=True)
        result=json.loads(proc.stdout)
        self.assertEqual(len(result["observations"]),5)
        for item in result["observations"]:
            expected=0 if item["case"]=="replay" else item["n"]
            self.assertEqual(item["report"]["inserted"],expected)
            self.assertGreater(item["python_peak_bytes"],0)
            self.assertGreaterEqual(item["rss_peak_after_raw"],item["rss_peak_before_raw"])

if __name__=="__main__":unittest.main()
