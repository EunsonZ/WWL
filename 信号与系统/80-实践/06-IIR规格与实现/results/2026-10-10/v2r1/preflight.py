from pathlib import Path
import sys,json,time
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'snapshot/candidate-v2/信号与系统/80-实践/06-IIR规格与实现'))
import iir_lab as lab
start=time.time();spec=lab.design();output={}
for name,rows in [('binary64',spec['sections']),('binary32',[[lab.binary32(v) for v in r] for r in spec['sections']])]:
 result=lab.strict_machine_certificate(spec,sections=rows,max_depth=1,max_cells=1)
 assert result['certified'] is False and all(v['partition_covers_closed_domain'] for v in result['bands'].values());output[name]=lab.json_ready(result)
print(json.dumps({'elapsed_seconds':time.time()-start,'bounded_preflight':output},ensure_ascii=False,indent=2))
