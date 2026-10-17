"""Rebuild bounded evidence in a new directory. No cluster is left running."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();base=Path(__file__).parent
    if a.out.exists() or a.out.is_symlink():p.exit(2,'new output directory required\n')
    a.out.mkdir(parents=True);receipt=[]
    def run(args):
        command=[sys.executable,'-B',*map(str,args)];started=time.monotonic();r=subprocess.run(command,cwd=base,text=True,capture_output=True,timeout=60)
        row={'argv':command,'cwd':str(base),'elapsed_s':time.monotonic()-started,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr};receipt.append(row)
        (a.out/'run-receipt.json').write_text(json.dumps({'sequential':True,'threads_per_process':1,'stages':receipt},indent=2)+'\n')
        if r.returncode:raise RuntimeError('stage failed; original stdout/stderr preserved')
    for mode in ('memory','process'):
        run([base/'run_lab.py','--plans',base/'plans.json','--mode',mode,'--out',a.out/mode])
        run([base/'history_oracle.py','--results',a.out/mode/'results.json','--out',a.out/(mode+'-oracle.json')])
    run(['-m','unittest','-v','test_read_barriers.py'])
    mem=json.loads((a.out/'memory/results.json').read_text());proc=json.loads((a.out/'process/results.json').read_text())
    for left,right in zip(mem['scenarios'],proc['scenarios']):
        assert left['name']==right['name']
        for lm,lp in zip(left['steps'],right['steps']):
            assert lm['action']==lp['action'];assert lm['nodes']==lp['nodes'];assert lm['RPC']==lp['RPC']
            if lm['action']['op']!='restart':assert lm['result']==lp['result']
        for k in ('history_good','history_bad','pending_calls'):assert left[k]==right[k]
    (a.out/'parity.json').write_text(json.dumps({'status':'PASS','same_fixed_plan_scenarios':len(mem['scenarios']),'same_all_node_states_and_rpc':True,'exception':'restart result contains actual PID/lifecycle instead of memory marker'},indent=2)+'\n')
    print(json.dumps({'status':'PASS','stages':len(receipt),'elapsed_s':sum(x['elapsed_s'] for x in receipt),'out':str(a.out)}))
if __name__=='__main__':main()
