"""Finite synthetic allocation arithmetic, not power measurement or certification."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import re


def nonnegative(x):
    if not isinstance(x,str) or not re.fullmatch(r'\d+(?:\.\d+)?',x) or len(x)>24:raise ValueError('bounded nonnegative decimal string required')
    return F(x)


def count(x):
    if type(x) is not int or not 0<=x<=10**9:raise ValueError('bounded integer count required')
    return x


def encode(x):return {'exact':str(x),'decimal':float(x)}


def calculate(data):
    if data['schema']!='professional-energy-v1' or data['data_kind']!='synthetic_no_hardware_measurement':raise ValueError('synthetic v1 card required')
    if not 1<=len(data['cases'])<=32:raise ValueError('finite 1..32 cases')
    common={k:nonnegative(v) for k,v in data['common'].items()};gate={k:nonnegative(v) for k,v in data['quality_gate'].items()}
    keys={'window_h','idle_node_W','reserved_share','aux_IT_kWh','facility_factor','external_network_kWh','grid_g_per_kWh','hardware_TE_g','hardware_life_h'}
    if set(common)!=keys or set(gate)!={'min_correct_rate','max_p99_ms'} or not 0<gate['min_correct_rate']<=1 or gate['max_p99_ms']<=0:raise ValueError('explicit common/gate schema')
    seen=set();rows=[]
    for c in data['cases']:
        if not isinstance(c['id'],str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,31}',c['id']) or c['id'] in seen:raise ValueError('unique bounded case id')
        seen.add(c['id']);p=common.copy()
        if set(c['override'])-keys:raise ValueError('unknown override')
        p.update({k:nonnegative(v) for k,v in c['override'].items()})
        if not 0<p['reserved_share']<=1 or not 0<p['window_h']<=p['hardware_life_h'] or p['facility_factor']<1:raise ValueError('share/time/facility domain')
        n=count(c['successful_requests']);failed=count(c['failed_attempts']);ej=nonnegative(c['success_J']);fj=nonnegative(c['failed_J']);correct=nonnegative(c['correct_rate']);latency=nonnegative(c['p99_ms'])
        if n==0 or correct>1:raise ValueError('nonzero denominator and probability')
        if correct<gate['min_correct_rate'] or latency>gate['max_p99_ms']:
            rows.append({'id':c['id'],'status':'not_comparable','reason':'quality_gate'});continue
        dyn=n*ej+failed*fj
        idle=p['idle_node_W']*p['reserved_share']*p['window_h']/1000
        facility=(dyn/3600000+idle+p['aux_IT_kWh'])*p['facility_factor']
        energy=facility+p['external_network_kWh'];operational=energy*p['grid_g_per_kWh']
        embodied=p['hardware_TE_g']*p['window_h']/p['hardware_life_h']*p['reserved_share'];total=operational+embodied
        row={'id':c['id'],'status':'calculated_synthetic','successful_requests':n,'failed_attempts':failed,'metrics':{k:encode(v) for k,v in {'dynamic_J':dyn,'dynamic_kWh':dyn/3600000,'idle_kWh':idle,'facility_included_kWh':facility,'total_energy_kWh':energy,'operational_g':operational,'embodied_allocated_g':embodied,'total_allocated_g':total,'g_per_functional_unit':total/n}.items()}}
        rows.append(row)
    return {'schema':'professional-energy-result-v1','input':data,'results':rows,'scope':'finite allocation, not measured energy; not a legal or sustainability certification'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists() or a.out.is_symlink():p.exit(2,'new output path required\n')
    result=calculate(json.loads(a.input.read_text()));a.out.write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n');print(json.dumps({'status':'PASS','cases':len(result['results']),'out':str(a.out)}))
if __name__=='__main__':main()
