"""Explicit-output bounded runner; absence of HDL tools is not simulated away."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess


def run(output, *, fault=False):
    if type(fault) is not bool:raise ValueError('fault must be bool')
    out=Path(output).expanduser().resolve()
    main_vault=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
    if out==main_vault or main_vault in out.parents:raise ValueError('output must be outside the main vault')
    src=Path(__file__).resolve().parent
    if out==src or src in out.parents:raise ValueError('use a new output outside frozen source/assets')
    compile_exe=shutil.which('iverilog');sim_exe=shutil.which('vvp')
    out.mkdir(parents=True,exist_ok=True)
    exe=out/'slot.vvp';trace=out/'slot.vcd'
    compile_cmd=[compile_exe or 'iverilog','-g2012','-Wall','-s','tb_slot','-o',str(exe)]
    if fault:compile_cmd.append('-DU26_FAULT_OVERWRITE')
    compile_cmd += [str(src/'elastic_slot.sv'),str(src/'tb_slot.sv')]
    sim_cmd=[sim_exe or 'vvp',str(exe),'+VCD='+str(trace)]
    record={'fault':fault,'commands':[compile_cmd,sim_cmd],'tools':{'iverilog':compile_exe,'vvp':sim_exe},
            'status':'not_run','reason':'missing HDL compiler/runtime','expected_fault':'post-head mismatch at cycle 2, 36 ns' if fault else None}
    if compile_exe and sim_exe:
        record['runs']=[]
        for index,cmd in enumerate((compile_cmd,sim_cmd)):
            try:
                result=subprocess.run(cmd,capture_output=True,text=True,timeout=45,cwd=out)
            except subprocess.TimeoutExpired as exc:
                record['status']='timeout';record['reason']='45 s budget';break
            (out/f'actual-{index}.stdout.txt').write_text(result.stdout)
            (out/f'actual-{index}.stderr.txt').write_text(result.stderr)
            record['runs'].append({'argv':cmd,'returncode':result.returncode})
            if result.returncode:
                record['status']='compile_failed' if index==0 else 'simulation_failed';break
        else:record['status']='simulation_passed'
        record['vcd_exists']=trace.is_file()
    (out/'execution-status.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--fault',action='store_true')
    args=parser.parse_args()
    result=run(args.output,fault=args.fault)
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='simulation_passed' else 2 if result['status']=='not_run' else 1

if __name__=='__main__':raise SystemExit(main())
