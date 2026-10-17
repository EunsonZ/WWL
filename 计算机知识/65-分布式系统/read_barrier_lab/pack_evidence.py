"""Lossless gzip archive of completed self-owned worker evidence, no rerun."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists() or a.out.is_symlink():p.exit(2,'fresh archive directory required\n')
    receipt=json.loads((a.run/'run-receipt.json').read_text());assert len(receipt['stages'])==5 and all(x['exit_code']==0 for x in receipt['stages'])
    proc=json.loads((a.run/'process/results.json').read_text());assert len(proc['scenarios'])==8
    for case,lifecycle in proc['lifecycle'].items():assert lifecycle[-1]['kind']=='all_current_owned_ports_closed'
    a.out.mkdir(parents=True);mapping=[]
    for name,source in [('memory-results.json',a.run/'memory/results.json'),('process-results.json',a.run/'process/results.json'),('memory-oracle.json',a.run/'memory-oracle.json'),('process-oracle.json',a.run/'process-oracle.json'),('run-receipt.json',a.run/'run-receipt.json'),('parity.json',a.run/'parity.json')]:
        (a.out/name).write_bytes(source.read_bytes())
    for source in sorted((a.run/'process').rglob('*')):
        if not source.is_file() or source.name=='results.json':continue
        if source.name.endswith(('-wal','-shm')):raise AssertionError('worker storage not fully closed/checkpointed')
        rel=source.relative_to(a.run/'process');data=source.read_bytes();row={'original_relative_path':str(rel),'size_bytes':len(data),'uncompressed_sha256':hashlib.sha256(data).hexdigest()}
        if data:
            dest=Path('workers')/Path(str(rel)+'.gz')
            target=a.out/dest;target.parent.mkdir(parents=True,exist_ok=True);compressed=gzip.compress(data,mtime=0);target.write_bytes(compressed);row.update({'archive':str(dest),'compressed_sha256':hashlib.sha256(compressed).hexdigest()})
        else:row['archive']=None
        mapping.append(row)
    (a.out/'compression-map.json').write_text(json.dumps({'lossless':True,'empty_files_omitted':True,'files':mapping},indent=2)+'\n')
    print(json.dumps({'status':'PASS','original_worker_files':len(mapping),'bytes_before':sum(x['size_bytes'] for x in mapping),'compressed_bytes':sum(p.stat().st_size for p in (a.out/'workers').rglob('*') if p.is_file())}))
if __name__=='__main__':main()
