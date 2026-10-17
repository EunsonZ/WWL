"""Fetch immutable UD Talbanken files; network acquisition is separate from CPU runs."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request,urlopen

COMMIT='3fd9c4123f155560ebb68c324b346fa9fa33991c'
BASE='https://raw.githubusercontent.com/UniversalDependencies/UD_Swedish-Talbanken/'+COMMIT+'/'
EXPECTED_SHA256={'README.md': 'f46b14ceec36998c5e41e7a83cb98ca7d259e679ee07f2d7de28a15bc8d018bc', 'LICENSE.txt': '55d116ac4f9bc34715c7823a5f5ca2e4c0cac4917db9e58a470a3d48033d261c', 'sv_talbanken-ud-train.conllu': 'fcc4bed5885e3d95f34a0e1bf813783135d38ae76d5822c3530b371fe78fc35f', 'sv_talbanken-ud-dev.conllu': '2e30e94a73a6db89b09fe80767df0c8c1194a48525879126a793015e868f8265', 'sv_talbanken-ud-test.conllu': 'eb3950dfb820d13634bed35c1d0f69872851754e0b19af1a9705ce6978580434'}
FILES=['README.md','LICENSE.txt','sv_talbanken-ud-train.conllu','sv_talbanken-ud-dev.conllu','sv_talbanken-ud-test.conllu']


def fetch(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);records=[]
    for name in FILES:
        url=BASE+name
        with urlopen(Request(url,headers={'User-Agent':'WWL-163-fixed-UD-teaching-baseline'}),timeout=45) as response:
            raw=response.read(12_000_001)
            if len(raw)>12_000_000:raise ValueError('unexpected source size')
            row=dict(name=name,url=url,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),retrieved_at_utc=datetime.now(timezone.utc).isoformat(),http_date=response.headers.get('Date'),etag=response.headers.get('ETag'))
        if row['sha256']!=EXPECTED_SHA256[name]:raise ValueError('fixed source identity mismatch: '+name)
        (output/name).write_bytes(raw);records.append(row)
    record=dict(repository='UniversalDependencies/UD_Swedish-Talbanken',release='r2.16',commit=COMMIT,files=records)
    (output/'fetch-record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=fetch(a.output)
    print(json.dumps({x['name']:x['bytes'] for x in r['files']}))
