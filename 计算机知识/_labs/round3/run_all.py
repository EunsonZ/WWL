#!/usr/bin/env python3
"""Run reviewed local labs. Writes only the requested report and temporary build files.
No downloads, privileged commands, package installation or remote connections.
Python 3.11+. Optional compilers are reported as SKIP when unavailable.
"""
from __future__ import annotations
import argparse, json, os, platform, shutil, subprocess, sys, tempfile, time
from datetime import datetime
from pathlib import Path
BASE=Path(__file__).resolve().parent
def vault_root(start: Path) -> Path:
    """Locate the vault boundary instead of relying on the lab's depth."""
    for candidate in (start, *start.parents):
        if (candidate / 'AGENTS.md').is_file():
            return candidate
    raise RuntimeError(f'Cannot locate vault root from {start}')

ROOT=vault_root(BASE)
def default_output_dir() -> Path:
    stamp=datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
    return ROOT/'Logs/运行/round3-labs'/stamp/'计算机知识'
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,
                        default=default_output_dir()/'round3_lab_results.json',
                        help='Independent report path; defaults below Logs/运行, never historical _meta.')
    args=parser.parse_args();results=[]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    def run(name,cmd,expect=0,scope='',timeout=40):
        start=time.monotonic()
        try:
            p=subprocess.run([str(c) for c in cmd],cwd=BASE,env=env,capture_output=True,text=True,timeout=timeout)
            ok=p.returncode==expect if expect is not None else p.returncode!=0
            item={'name':name,'status':'PASS' if ok else 'FAIL','command':[str(c) for c in cmd],'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'scope':scope}
        except (OSError,subprocess.TimeoutExpired) as e:
            item={'name':name,'status':'FAIL','command':[str(c) for c in cmd],'error':str(e),'scope':scope}
        item['seconds']=round(time.monotonic()-start,4);results.append(item)
        print(item['status'],name,flush=True)
        if item['status']=='FAIL':print(item.get('stderr',item.get('error','')),flush=True)
        return item['status']=='PASS'
    def skip(name,why):results.append({'name':name,'status':'SKIP','reason':why});print('SKIP',name,why)
    tools={}
    for name in ('cc','g++','node','tsc','rustc','bash'):
        if path:=shutil.which(name):
            p=subprocess.run([path,'--version'],capture_output=True,text=True,timeout=10)
            tools[name]={'path':path,'version':(p.stdout or p.stderr).splitlines()[0]}
        else:tools[name]={'available':False}
    with tempfile.TemporaryDirectory(prefix='obsidian-labs-') as build:
        build=Path(build)
        for name,source,std,compiler,extra in [('C','C/vector.c','c17','cc',[]),('CPP','CPP/raii_queue.cpp','c++20','g++',['-pthread'])]:
            if not shutil.which(compiler):skip(name,'compiler unavailable');continue
            exe=build/name
            if run(name+' compile',[compiler,'-std='+std,'-O2','-Wall','-Wextra','-Werror','-pedantic','-fsanitize=undefined','-fno-sanitize-recover=all',*extra,source,'-o',exe],scope='warnings as errors; UndefinedBehaviorSanitizer instrumented'):
                run(name+' run',[exe],scope='reviewed bounded local test; does not prove absence of all UB/data races')
        for name,source in [('PY','test_python.py'),('DS','structures.py'),('ALG','algorithms.py'),('CO','hardware_models.py'),('OS','os_models.py'),('NET','network_models.py'),('DB','sqlite_lab.py'),('COMP','compiler_lab.py')]:
            run(name,[sys.executable,BASE/name/source])
        if shutil.which('tsc') and shutil.which('node'):
            opts=['tsc','--strict','--noUncheckedIndexedAccess','--exactOptionalPropertyTypes','--target','ES2022','--module','commonjs','--lib','ES2022,DOM','--outDir',build/'ts']
            if run('TS compile',opts+['TS/contracts.ts','TS/type_checks.ts'],scope='Includes 3 @ts-expect-error rejection checks'):
                run('TS run',['node',build/'ts/contracts.js'])
            run('JS regex regression',['node','-e',r'const assert=require("node:assert/strict");assert.throws(()=>new RegExp("\\A","u"),SyntaxError);assert.equal(new RegExp("\\A").test("A"),true);console.log("PASS: engine-specific buffer-anchor regression")'],scope='Node engine version recorded; not a universal future-JavaScript claim')
        else:skip('TS','tsc or node unavailable')
        if shutil.which('rustc'):
            if run('RUST compile',['rustc','--edition=2021','--test','RUST/ownership.rs','-o',build/'rust_test']):run('RUST run',[build/'rust_test'])
            run('RUST expected compile rejection',['rustc','--edition=2021','RUST/borrow_compile_fail.rs','-o',build/'bad'],expect=None,scope='Expected nonzero compiler exit for conflicting borrow')
        else:skip('RUST','rustc unavailable; source and expected-failure fixture included but not compiled here')
        if shutil.which('bash'):run('LINUX',['bash','LINUX/shell_lab.sh'])
        else:skip('LINUX','bash unavailable')
    report={'python':sys.version,'platform':platform.platform(),'tools':tools,'results':results,'summary':{s:sum(r['status']==s for r in results) for s in ('PASS','FAIL','SKIP')},'limits':['Only listed labs executed.','PostgreSQL concurrency, CUDA/GPU, privileged Linux administration and full Obsidian GUI not executed.','Passing tests is not a complete proof of all notes or programs.']}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report['summary']));return 1 if report['summary']['FAIL'] else 0
if __name__=='__main__':raise SystemExit(main())
