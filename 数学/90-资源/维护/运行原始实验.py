#!/usr/bin/env python3
"""执行原有七个实验，检查正文代码同步与部分非法输入契约。
仅运行知识库中明示的七个本地教学程序；不访问网络、不清理用户文件。
"""
from __future__ import annotations
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'90-资源/维护/原始文件基线.json'

def load(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise RuntimeError(f'无法加载{path}')
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod
    with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(mod)
    return mod

def main() -> int:
    baseline=json.loads(BASE.read_text(encoding='utf-8'));scripts=[ROOT/r['path'] for r in baseline if r['path'].endswith('.py')]
    executions=[];sync=[];contracts=[]
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['MPLBACKEND']='Agg'
    for p in scripts:
        begin=time.perf_counter()
        try:
            done=subprocess.run([sys.executable,str(p)],cwd=p.parent,env=env,text=True,capture_output=True,timeout=45)
            executions.append({'path':str(p.relative_to(ROOT)),'passed':done.returncode==0,'returncode':done.returncode,'seconds':round(time.perf_counter()-begin,3),'stdout':done.stdout,'stderr':done.stderr})
        except Exception as exc:executions.append({'path':str(p.relative_to(ROOT)),'passed':False,'error':str(exc)})
    pattern=re.compile(r'<!--\s*code-sync:\s*(.*?)\s*-->\s*```python\n(.*?)\n```',re.S)
    for p in ROOT.rglob('*.md'):
        for m in pattern.finditer(p.read_text(encoding='utf-8')):
            target=(p.parent/m.group(1)).resolve()
            good=target.is_file() and m.group(2).rstrip()+'\n'==target.read_text(encoding='utf-8').rstrip()+'\n'
            sync.append({'source':str(p.relative_to(ROOT)),'target':str(target.relative_to(ROOT)),'passed':good})
    mods={}
    for p in scripts:
        if p.name in ['low_rank_approximation.py','80-量化误差实验.py','80-多模态数学最小实验.py']:
            mods[p.name]=load(p,'_math_lesson_'+str(len(mods)))
    svd=mods['low_rank_approximation.py'];q=mods['80-量化误差实验.py'];sig=mods['80-多模态数学最小实验.py']
    cases=[('SVD浮点秩',lambda:svd.truncated_svd(np.eye(2),1.5)),('SVD布尔秩',lambda:svd.truncated_svd(np.eye(2),True)),('SVD非有限输入',lambda:svd.truncated_svd(np.array([[np.nan]]),1)),('量化浮点bits',lambda:q.affine_quantize([1.],bits=4.5,symmetric=True)),('量化布尔bits',lambda:q.affine_quantize([1.],bits=True,symmetric=True)),('分组浮点大小',lambda:q.grouped_quantize([1.],bits=4,group_size=1.5,symmetric=True)),('Patch非矩形',lambda:sig.patch_means([[1.],[1.,2.]],1)),('Patch非有限',lambda:sig.patch_means([[float('inf')]],1)),('DFT非有限',lambda:sig.dft_magnitudes([float('nan')])),('采样率非正',lambda:sig.dominant_positive_frequency([1.,2.],0))]
    for name,fn in cases:
        try:fn();contracts.append({'name':name,'passed':False,'error':'未拒绝非法输入'})
        except ValueError as exc:contracts.append({'name':name,'passed':True,'exception':str(exc)})
        except Exception as exc:contracts.append({'name':name,'passed':False,'error':f'错误异常类型: {type(exc).__name__}: {exc}'})
    report={'environment':{'python':platform.python_version(),'numpy':np.__version__},'scripts':executions,'code_sync':sync,'input_contracts':contracts,'summary':{'scripts_total':len(executions),'scripts_passed':sum(v['passed'] for v in executions),'code_sync_total':len(sync),'code_sync_passed':sum(v['passed'] for v in sync),'contracts_total':len(contracts),'contracts_passed':sum(v['passed'] for v in contracts)}}
    path=ROOT/'90-资源/维护/原始实验验收.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],ensure_ascii=False))
    return 0 if all(v['passed'] for v in executions+sync+contracts) else 1

if __name__=='__main__':raise SystemExit(main())
