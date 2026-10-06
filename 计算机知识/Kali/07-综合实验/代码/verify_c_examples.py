"""Explicit, bounded checks of the two owned C examples; never install a compiler.

Run manually after reviewing hello.c and length_record.c. Builds in a temporary owned
directory, invokes fixed benign executables on finite inputs, and writes one NEW JSON
report. No fuzzing engine, network access, real samples, shell commands or global changes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import generate_reasoning_fixtures as fixtures


def run(compiler: str, sanitizer: str) -> dict:
    executable=shutil.which(compiler)
    if executable is None:
        raise FileNotFoundError(f'compiler not available: {compiler}; nothing installed')
    modes={'none':[], 'undefined':['-fsanitize=undefined'],
           'address-undefined':['-fsanitize=address,undefined']}
    if sanitizer not in modes:
        raise ValueError('unsupported sanitizer mode')
    base=Path(__file__).resolve().parent
    sources={name:base/name for name in ('hello.c','length_record.c')}
    for path in sources.values():
        if path.is_symlink() or not path.is_file():raise ValueError('regular owned source required')
    version=subprocess.run([executable,'--version'],capture_output=True,text=True,timeout=10,check=True).stdout.splitlines()[0]
    result={'compiler':executable,'compiler_version':version,'sanitizer':sanitizer,
            'platform':platform.platform(),'source_sha256':{k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in sources.items()},
            'builds':[], 'cases':[], 'not_run':['AFL++','libFuzzer','GDB','Kali native tool execution']}
    cases=json.loads(fixtures.contents()['records.json'])['cases']
    vectors=[(case['name'],bytes.fromhex(case['hex']),case['exit'],case['stdout']) for case in cases]
    for n in range(33):
        payload=bytes((i*17+3)%256 for i in range(n))
        vectors.append((f'valid-length-{n}',b'L'+bytes([n])+payload,0,str(sum(payload))+'\n'))
    vectors += [('header-only',b'L',2,''),('wrong-magic',b'X\0',2,''),
                ('declared-33',b'L\x21'+b'A'*33,2,''),('declared-255',b'L\xff'+b'A'*255,2,''),
                ('max-plus-trailing',b'L\x20'+b'A'*33,2,''),
                ('embedded-zero',b'L\x03A\0B',0,'131\n'),('all-ff',b'L\x20'+b'\xff'*32,0,'8160\n')]
    with tempfile.TemporaryDirectory(prefix='kali-owned-c-') as tmp:
        out=Path(tmp)
        for name,path in sources.items():
            target=out/path.stem
            flags=['-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fno-omit-frame-pointer']+modes[sanitizer]
            command=[executable,*flags,str(path),'-o',str(target)]
            build=subprocess.run(command,capture_output=True,text=True,timeout=30)
            result['builds'].append({'source':name,'flags':flags,'returncode':build.returncode,'stdout':build.stdout,'stderr':build.stderr})
            if build.returncode:
                result['status']='build_failed';return result
        for args,expected_rc,expected_out in [([],0,'Hello, learner. This is a local teaching program.\n'),
                                            (['Ethan'],0,'Hello, Ethan. This is a local teaching program.\n'),
                                            (['one','two'],2,'')]:
            proc=subprocess.run([str(out/'hello'),*args],capture_output=True,timeout=5)
            ok=(proc.returncode==expected_rc and proc.stdout.decode()==expected_out and
                (bool(proc.stderr) if expected_rc else not proc.stderr))
            result['cases'].append({'program':'hello','args':args,'expected_rc':expected_rc,'actual_rc':proc.returncode,
                                    'stdout':proc.stdout.decode(errors='replace'),'stderr':proc.stderr.decode(errors='replace'),'passed':ok})
        for name,data,expected_rc,expected_out in vectors:
            try:
                proc=subprocess.run([str(out/'length_record')],input=data,capture_output=True,timeout=5)
                stderr=proc.stderr.decode(errors='replace')
                ok=(proc.returncode==expected_rc and proc.stdout.decode()==expected_out and
                    (bool(stderr) if expected_rc else not stderr) and
                    not any(marker in stderr for marker in ('Sanitizer','runtime error:')))
                record={'program':'length_record','case':name,'input_hex':data.hex(),'input_sha256':hashlib.sha256(data).hexdigest(),
                        'expected_rc':expected_rc,'actual_rc':proc.returncode,'stdout':proc.stdout.decode(errors='replace'),
                        'stderr':stderr,'passed':ok}
            except subprocess.TimeoutExpired:
                record={'program':'length_record','case':name,'status':'timeout','passed':False}
            result['cases'].append(record)
    result['passed']=sum(row['passed'] for row in result['cases'])
    result['total']=len(result['cases'])
    result['status']='passed' if result['passed']==result['total'] else 'failed'
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler',default='cc')
    parser.add_argument('--sanitizer',choices=['none','undefined','address-undefined'],default='none')
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    # Reserve a new report before running; preserve failures rather than overwriting evidence.
    with args.report.open('x',encoding='utf-8') as stream:
        try:
            result=run(args.compiler,args.sanitizer)
        except Exception as exc:
            result={'status':'runner_failed','error_type':type(exc).__name__,'message':str(exc)}
        json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'status':result['status'],'total':result.get('total'),'passed':result.get('passed')},ensure_ascii=False))
    raise SystemExit(0 if result['status']=='passed' else 1)