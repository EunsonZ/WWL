"""Batch verifier from raw SPICE outputs. No joint_ota import and no model re-execution."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def read(path):return np.atleast_2d(np.loadtxt(path,skiprows=1))

def complex_columns(a):return a[:,1::2]+1j*a[:,2::2]


def verify(lab,out):
    spec=json.loads((lab/'spec.json').read_text());r=json.loads((out/'results.json').read_text());assert r['spec_sha256']==hashlib.sha256((lab/'spec.json').read_bytes()).hexdigest()
    for n,h in r['source_sha256'].items():assert hashlib.sha256((lab/n).read_bytes()).hexdigest()==h
    assert len(r['cases'])==9;record={};raw=out/'spice'
    for name,row in r['cases'].items():
        v=read(raw/(name+'-op')/'operating.txt')[0,1:];err=float(max(abs(v-row['Q'])));assert err<1e-6;record[name+'_op_V']=err
        J=np.array(row['linear']['J_S']);C=np.array(row['linear']['C_F']);A=np.array(row['linear']['A_s_inv']);np.testing.assert_allclose(C,C.T,rtol=0,atol=0);assert min(np.linalg.eigvalsh(C))>0;np.testing.assert_allclose(C@A,-J,rtol=1e-10,atol=1e-14)
        assert len(row['linear']['sources'])==15
        # Every current-noise incidence has either two opposite terminals or one grounded ideal-source terminal.
        for source in row['linear']['sources']:
            b=np.array(source['incidence']);assert set(b)<=set([-1,0,1]);assert 1<=np.count_nonzero(b)<=2;assert source['psd_A2_Hz']>=0
    Ypath=raw/'balanced-Y';voltage=np.column_stack([complex_columns(read(Ypath/('node-'+str(k)+'.txt')))[0] for k in range(10)]);Y=-np.linalg.inv(voltage);J=Y.real;C=Y.imag/(2*np.pi*1000);target=r['cases']['balanced']['linear'];np.testing.assert_allclose(J,target['J_S'],rtol=1e-7,atol=1e-14);np.testing.assert_allclose(C,target['C_F'],rtol=1e-7,atol=1e-17);record['raw_Y_max_J_error_S']=float(np.max(abs(J-target['J_S'])));record['raw_Y_max_C_error_F']=float(np.max(abs(C-target['C_F'])));roots=np.linalg.eigvals(-np.linalg.solve(C,J));expected=np.array([complex(*z) for z in target['roots']]);record['raw_Y_root_nearest_max_s_inv']=float(max(min(abs(z-expected)) for z in roots));assert all(z.real<0 for z in roots)
    for name in ['starting','dm_only','balanced','mismatch']:
        row=r['cases'][name]['linear'];p=raw/(name+'-ac-noise');dm=read(p/'noise-dm.txt');cm=read(p/'noise-cm.txt');spectrum=row['spectrum'];f=np.array([z['frequency_Hz'] for z in spectrum]);np.testing.assert_allclose(f,dm[:,0],rtol=1e-12,atol=1e-12)
        # sqrnoise makes ALL retained density vectors PSD [V²/Hz], not ASD.
        expected_dm=np.array([z['dm_source_psd'] for z in spectrum]);expected_cm=np.array([z['cm_source_psd'] for z in spectrum]);np.testing.assert_allclose(dm[:,3:],expected_dm,rtol=1e-5,atol=1e-24);np.testing.assert_allclose(cm[:,2:],expected_cm,rtol=1e-5,atol=1e-24);np.testing.assert_allclose(dm[:,1],dm[:,3:].sum(axis=1),rtol=1e-10,atol=1e-24);np.testing.assert_allclose(cm[:,1],cm[:,2:].sum(axis=1),rtol=1e-10,atol=1e-24)
        np.testing.assert_allclose(dm[:,2],[z['input_equivalent_psd'] for z in spectrum],rtol=1e-5,atol=1e-24)
        for n,col in [('dm',0),('cm',1)]:
            measured=complex_columns(read(p/('ac-'+n+'.txt')));observed=np.column_stack((measured[:,0]-measured[:,1],(measured[:,0]+measured[:,1])/2));truth=np.array([[[complex(*z) for z in hrow] for hrow in q['signal']] for q in spectrum]);# shape frequency,output,input
            np.testing.assert_allclose(observed,truth[:,:,col],rtol=1e-5,atol=1e-10)
        rms=float(np.sqrt(np.trapezoid(dm[:,1],dm[:,0])));np.testing.assert_allclose(rms,row['noise_dm_rms_V'],rtol=1e-5,atol=1e-12);record[name+'_raw_dm_RMS_V']=rms
        record[name+'_maximum_total_PSD_relative_error']=float(np.max(abs(dm[:,1]-np.array([z['dm_psd'] for z in spectrum]))/dm[:,1]))
    for amplitude,trace in [(.06,r['cases']['balanced']['step']),(.35,r['balanced_other_amplitudes'][1])]:
        rawtrace=read(raw/('balanced-step-'+str(amplitude))/'transient.txt');t=np.array(trace['time_s']);v=np.array(trace['states_V']);interpolated=np.column_stack([np.interp(t,rawtrace[:,0],rawtrace[:,i+1]) for i in range(10)]);valid=t>=rawtrace[0,0];error=float(np.max(abs(interpolated[valid]-v[valid])));assert error<1e-4;record['step_'+str(amplitude)+'_first_SPICE_time_s']=float(rawtrace[0,0]);record['step_'+str(amplitude)+'_max_node_error_V']=error
    balanced=r['cases']['balanced']['budget'];assert balanced['all_met'];assert 'dm_margin' in r['cases']['starting']['budget']['failed'];assert 'cm_margin' in r['cases']['dm_only']['budget']['failed'];assert r['cases']['dm_only']['linear']['cuts']['dm']['crossings'][0]['phase_margin_deg']>r['cases']['starting']['linear']['cuts']['dm']['crossings'][0]['phase_margin_deg'];assert r['cases']['dm_only']['linear']['cuts']['cm']['crossings'][0]['phase_margin_deg']<r['cases']['starting']['linear']['cuts']['cm']['crossings'][0]['phase_margin_deg']
    return {'status':'PASS','independent_layer':'raw SPICE op/AC/noise/Y/transient; no author model import; not physical device','cases':9,'noise_sources':15,'noise_frequencies_each':401,'raw_Y_dimension':10,'checks':record}


def main():
    p=argparse.ArgumentParser();p.add_argument('--lab',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();v=verify(a.lab,a.results);a.out.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
if __name__=='__main__':main()
