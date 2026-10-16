"""Bounded Wikidata REST reads for a fixed small panel; no training.

Structured data CC0: https://www.wikidata.org/wiki/Wikidata:Licensing
These per-property reads retain ranks/qualifiers; normalization is separate.
"""
import argparse
import datetime
import hashlib
from urllib.error import HTTPError
import json
from pathlib import Path
import time
from urllib.request import Request,urlopen


def fetch(panel,output):
    if output.exists():raise ValueError('output exists; choose a new file')
    checkpoint=output.with_suffix('.partial.json')
    records=json.loads(checkpoint.read_text())if checkpoint.exists()else[];total=sum(len(row['body'].encode('utf-8'))for row in records);base='https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items/'
    requests=[(qid,'label',base+qid+'/labels/en')for qid in panel['entities']+panel['candidate_continents']]
    requests += [(qid,prop,base+qid+'/statements?property='+prop)for qid in panel['entities']for prop in panel['properties']]
    for index,record in enumerate(records):
        if (record['entity'],record['property'],record['url'])!=requests[index]:raise ValueError('checkpoint plan differs')
    for number,(qid,prop,url)in enumerate(requests,1):
        if number<=len(records):continue
        for attempt in range(5):
            try:
                response=urlopen(Request(url,headers={'User-Agent':'WWL-graph-curriculum/1.0 (small educational snapshot; github.com/EunsonZ/WWL)','Accept':'application/json'}),timeout=30);break
            except HTTPError as error:
                if error.code not in (429,503):raise
                wait=max(60,int(error.headers.get('Retry-After','60')));print(f'HTTP {error.code}: obey Retry-After, wait {wait}s',flush=True);time.sleep(wait)
        else:raise RuntimeError('bounded retries exhausted; checkpoint retained')
        with response:
            raw=response.read(150001)
            if len(raw)>150000:raise ValueError('unexpectedly large property response')
            body=raw.decode('utf-8');data=json.loads(body)
            if isinstance(data,dict)and'error'in data:raise ValueError(data['error'])
            record={'entity':qid,'property':prop,'url':url,'http_status':response.status,'http_date':response.headers.get('Date'),'etag':response.headers.get('ETag'),'last_modified':response.headers.get('Last-Modified'),'retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'body':body}
        records.append(record);total+=len(raw);checkpoint.write_text(json.dumps(records,ensure_ascii=False)+'\n')
        if total>2_000_000:raise ValueError('total source size bound exceeded')
        if number%10==0:print(f'Fetched {number}/{len(requests)} responses, {total} bytes',flush=True)
        time.sleep(6.1)
    output.write_text(json.dumps({'license':'CC0-1.0 structured data','license_url':'https://www.wikidata.org/wiki/Wikidata:Licensing','api':'Wikibase REST per-property statements and English labels','responses':records,'response_body_bytes':total},ensure_ascii=False,indent=2)+'\n')
    checkpoint.unlink();print(f'Saved {len(records)} responses, {total} original response bytes',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--panel',type=Path,default=Path(__file__).with_name('panel.json'));ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();fetch(json.loads(args.panel.read_text()),args.output)
