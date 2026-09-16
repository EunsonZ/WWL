"""Deterministic synthetic v2 fixtures. Importing only defines functions.

Run only in an owned, quiescent directory. Refuse existing destination and observed
symlinks; this is NOT a race-resistant sandbox for hostile concurrent filesystem edits.
The v1 fixtures and identities are deliberately not overwritten or silently migrated.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

VERSION = "reasoning-v2.0"


def _json(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+'\n').encode('utf-8')


def _scan(ports: str, scopes: str, finish: str) -> bytes:
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE nmaprun>\n'
            f'<!-- SYNTHETIC {VERSION}; not an executed Nmap scan. -->\n'
            f'<nmaprun scanner="nmap" version="SYNTHETIC" args="NOT-EXECUTED">\n'
            f'{scopes}\n<host><status state="up" reason="user-set"/>'
            f'<address addr="127.0.0.1" addrtype="ipv4"/><ports>{ports}</ports></host>\n'
            f'<runstats><finished exit="{finish}"/></runstats></nmaprun>\n').encode()


def _port(n: int, state: str, protocol: str = 'tcp') -> str:
    return f'<port protocol="{protocol}" portid="{n}"><state state="{state}" reason="synthetic"/></port>'


def contents() -> dict[str, bytes]:
    """All expected decisions are hand specified, not computed by the tested policy."""
    before_scope='<scaninfo type="syn" protocol="tcp" numservices="2" services="22,8000"/>'
    after_scope='<scaninfo type="syn" protocol="tcp" numservices="2" services="443,8000"/>'
    udp_scope='<scaninfo type="udp" protocol="udp" numservices="1" services="53"/>'
    files={
        'route-cases.json': _json({'fixture_version':VERSION,'synthetic':True,
            'routes':[{'prefix':'0.0.0.0/0','interface':'uplink','metric':1},
                      {'prefix':'192.168.56.0/24','interface':'lab','metric':10},
                      {'prefix':'192.168.56.32/27','interface':'lab-specific','metric':900}],
            'cases':[{'destination':'192.168.56.37','expected_prefix':'192.168.56.32/27'},
                     {'destination':'192.168.56.64','expected_prefix':'192.168.56.0/24'},
                     {'destination':'198.51.100.7','expected_prefix':'0.0.0.0/0'},
                     {'destination':'2001:db8::1','expected_prefix':None}]}),
        'scan-before.xml':_scan(_port(22,'open')+_port(8000,'open')+_port(53,'open|filtered','udp'),before_scope+udp_scope,'success'),
        'scan-after.xml':_scan(_port(443,'open')+_port(8000,'closed')+_port(53,'open|filtered','udp'),after_scope+udp_scope,'error'),
        'scan-aggregate.xml':_scan(_port(8000,'open')+'<extraports state="closed" count="2"/>',
                '<scaninfo type="syn" protocol="tcp" numservices="3" services="22,443,8000"/>','success'),
        'authorization-cases.json':_json({'fixture_version':VERSION,'synthetic':True,
            'model':'Separate from the v1 owner-only model; this file contains expected policy decisions, not credentials.',
            'cases':[{'identity':'alice','report_id':17,'action':'edit','expected':True},
                     {'identity':'bob','report_id':17,'action':'edit','expected':False},
                     {'identity':'bob','report_id':18,'action':'approve','expected':True},
                     {'identity':'bob','report_id':20,'action':'approve','expected':False},
                     {'identity':'carol','report_id':18,'action':'read','expected':False},
                     {'identity':'alice','report_id':21,'action':'submit','expected':False}]}),
        'timeline.json':_json({'fixture_version':VERSION,'synthetic':True,
            'events':[{'id':'A','time':'2026-09-05T16:00:00+08:00','uncertainty_seconds':3},
                      {'id':'B','time':'2026-09-05T08:00:02Z','uncertainty_seconds':1}],
            'expected_definitely_before':False,
            'invalid_examples':['2026-09-05T08:00:00','2026-09-05T08:00:00+01:60']}),
        'metrics.json':_json({'fixture_version':VERSION,'synthetic':True,
            'population':1000000,'positive':1000,'tp':900,'fp':9990,'tn':989010,'fn':100,
            'expected_precision_fraction':[10,121],'expected_recall':0.9,'expected_fpr':0.01}),
        'records.json':_json({'fixture_version':VERSION,'synthetic':True,
            'cases':[{'name':'empty-file','hex':'','exit':2,'stdout':''},
                     {'name':'empty-payload','hex':'4c00','exit':0,'stdout':'0\n'},
                     {'name':'AB','hex':'4c024142','exit':0,'stdout':'131\n'},
                     {'name':'short','hex':'4c034142','exit':2,'stdout':''},
                     {'name':'trailing','hex':'4c0041','exit':2,'stdout':''},
                     {'name':'max-payload','hex':'4c20'+'ff'*32,'exit':0,'stdout':'8160\n'}]})
    }
    manifest={'fixture_version':VERSION,'synthetic':True,'sha256':{name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())}}
    files['expected-v2.json']=_json(manifest)
    return files


def generate(destination: Path) -> None:
    destination=Path(os.path.abspath(os.fspath(destination)))
    for entry in [destination,*destination.parents]:
        if entry.is_symlink():
            raise ValueError('symlink path is not accepted')
    if destination.exists():
        raise FileExistsError(destination)
    if not destination.parent.is_dir():
        raise FileNotFoundError('parent must already exist')
    destination.mkdir(mode=0o700)
    for name,data in contents().items():
        with (destination/name).open('xb') as stream:
            stream.write(data)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    generate(args.destination)
    print(f'Created {VERSION} synthetic fixtures in a new directory.')