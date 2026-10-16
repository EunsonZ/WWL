"""Lock parameters on development replicates before reading the separate evaluation fixture."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
import imaging_lab as m


def metrics(a,y,x,truth,repeat,maximum):
    x=np.asarray(x);truth=np.asarray(truth).ravel();error=x-truth;mse=float(np.mean(error*error))
    return {'measurement_residual_norm':float(np.linalg.norm(a@x-y)),'repeat_prediction_mse':float(np.mean((a@x-repeat)**2)),'mse':mse,'psnr_db':float(10*math.log10(maximum**2/mse)) if mse else None,'first_seven_rows_mse':float(np.mean(error[:-8]**2)),'unobserved_last_row_mse':float(np.mean(error[-8:]**2)),'range':[float(x.min()),float(x.max())]}


def validate(s):
    if s['input_version']!='psf-holdout-v2' or s['shape']!=[8,8] or s['bin_factor']!=2 or s['psf_origin']!=[1,1]:raise ValueError('finite_workload_shape_origin')
    m.kernel(s['psf'])
    if s['boundary']!='zero' or s['detector_rows']!=[0,1,2] or not 0<s['pixel_pitch_mm']<=1 or not 0<s['noise_sigma_after_binning']<1 or s['psnr_max']!=1:raise ValueError('finite_observation_protocol')
    if not 1<=len(s['candidates'])<=16 or any(c['method'] not in ('ridge','tsvd','tv') or not np.isfinite(c['parameter']) or not 0<=c['parameter']<=1 for c in s['candidates']):raise ValueError('candidate_budget')
    c=s['solver']
    if not .0001<=c['epsilon']<=1 or not .01<=c['rho']<=1 or not 1e-8<=c['tolerance']<=1e-5 or type(c['max_iterations'])!=int or not 1<=c['max_iterations']<=10000:raise ValueError('iteration_budget')


def run(spec_path,dev_path,evaluation_path,out):
    if out.exists():raise FileExistsError('new_output_required')
    s=json.loads(spec_path.read_text());validate(s);dev=json.loads(dev_path.read_text());shape=s['shape'];psf=s['psf'];rows=s['detector_rows'];a=m.dense_operator(shape,psf,'zero',rows);d=m.difference(shape);y_clean=m.acquire(dev['truth'],psf,'zero',rows);yfit=y_clean+dev['noise_fit'];yval=y_clean+dev['noise_validation']
    chosen=m.select(a,yfit,yval,d,s['candidates'],s['solver']);out.mkdir(parents=True);(out/'selection.json').write_text(json.dumps(chosen,indent=2)+'\n')
    # This read happens only after the lock artifact exists. Fixtures are public synthetic data.
    evaluation=json.loads(evaluation_path.read_text());truth=np.asarray(evaluation['truth'],float);clean=m.acquire(truth,psf,'zero',rows);testfit=clean+evaluation['noise_fit'];testrepeat=clean+evaluation['noise_repeat'];result={'input_version':s['input_version'],'numpy':np.__version__,'source_sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest(),'input_sha256':{str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in [spec_path,dev_path,evaluation_path]},'operator':a.tolist(),'difference':d.tolist(),'development':{'clean':y_clean.tolist(),'fit':yfit.tolist(),'validation':yval.tolist()},'locked_selection':{'by_family':chosen['by_family'],'overall':chosen['overall'],'selection_sha256':hashlib.sha256((out/'selection.json').read_bytes()).hexdigest()},'evaluation':{'clean':clean.tolist(),'fit':testfit.tolist(),'repeat':testrepeat.tolist()},'reconstructions':[],'mismatch':[]}
    probes=np.arange(64,dtype=float).reshape(shape)/63;z=np.linspace(-.4,.7,12);xadj=m.acquire_adjoint(z,shape,psf,'zero',rows);left=float(m.acquire(probes,psf,'zero',rows)@z);right=float(probes.ravel()@xadj.ravel());wx=s['pixel_pitch_mm']**2;wy=4*wx
    corner=np.zeros(shape);corner[0,0]=1;null=np.zeros(shape);null[-1,3]=1
    result['operator_checks']={'inner_left':left,'inner_right':right,'weighted_left':wy*left,'weighted_right':float(wx*probes.ravel()@((wy/wx)*xadj.ravel())),'scatter_adjoint':xadj.tolist(),'matrix_adjoint':(a.T@z).reshape(shape).tolist(),'probe_x':probes.tolist(),'probe_z':z.tolist(),'zero_corner':m.acquire(corner,psf,'zero',rows).tolist(),'periodic_corner':m.acquire(corner,psf,'periodic',rows).tolist(),'AtA_corner':(a.T@a@corner.ravel()).reshape(shape).tolist(),'null_input':null.tolist(),'null_observation':(a@null.ravel()).tolist(),'singular_values':np.linalg.svd(a,compute_uv=False).tolist(),'rank_tolerance':1e-12,'numerical_rank':int(np.linalg.matrix_rank(a,tol=1e-12)),'unknown_dimension':64,'fft_zero_max_difference':float(np.max(np.abs(m.blur(probes,psf,'zero')-m.blur_fft(probes,psf,'zero')))),'fft_periodic_max_difference':float(np.max(np.abs(m.blur(probes,psf,'periodic')-m.blur_fft(probes,psf,'periodic')))),'zero_constant_response':m.blur(np.ones(shape),psf,'zero').tolist(),'periodic_constant_response':m.blur(np.ones(shape),psf,'periodic').tolist()}
    jobs=[('pinv',{'method':'tsvd','parameter':0}),('truncated_fixed',{'method':'tsvd','parameter':s['fixed_truncated_reference']})]+[(key+'_selected',val) for key,val in chosen['by_family'].items() if key!='tsvd']
    for name,candidate in jobs:
        estimate=m.fit(a,testfit,d,candidate,s['solver'])
        if not estimate.get('converged',True):raise RuntimeError('evaluation_not_converged')
        result['reconstructions'].append({'id':name,'candidate':candidate,'fit':estimate,'metrics':metrics(a,testfit,estimate['x'],truth,testrepeat,s['psnr_max'])})
    candidate=chosen['by_family']['tv']
    for name,wrong_psf,boundary in [('wrong_periodic',psf,'periodic'),('wrong_reversed_psf',np.asarray(psf)[::-1,::-1].tolist(),'zero')]:
        wrong=m.dense_operator(shape,wrong_psf,boundary,rows);estimate=m.fit(wrong,testfit,d,candidate,s['solver'])
        if not estimate.get('converged',True):raise RuntimeError('mismatch_not_converged')
        result['mismatch'].append({'id':name,'operator':wrong.tolist(),'candidate_locked_from_correct_model':candidate,'fit':estimate,'metrics_assumed_model':metrics(wrong,testfit,estimate['x'],truth,testrepeat,s['psnr_max']),'true_model_residual':float(np.linalg.norm(a@estimate['x']-testfit))})
    # 1D finite matrices are independent explanatory probes, not a second reconstruction dataset.
    h=[.25,.5,.25];zero=np.array([[.5,.25,0],[.25,.5,.25],[0,.25,.5]]);periodic=np.full((3,3),.25);np.fill_diagonal(periodic,.5);impulse=np.array([1.,0,0]);full=np.fft.ifft(np.fft.fft(impulse,5)*np.fft.fft(h,5)).real
    result['one_dimensional']={'zero':zero.tolist(),'periodic':periodic.tolist(),'zero_impulse':(zero@impulse).tolist(),'periodic_impulse':(periodic@impulse).tolist(),'linear_fft_same_crop':full[1:4].tolist(),'periodic_fft':np.fft.ifft(np.fft.fft(impulse)*np.fft.fft([.5,.25,.25])).real.tolist()}
    physical=s['physical_interface'];mu0=4*math.pi*1e-7;eps0=1/(mu0*299792458**2);coefficient=2*math.pi*eps0*physical['length_m']/math.log(physical['b_m']/physical['a_m'])*1e12;er=physical['epsilon_r'];cp=physical['parasitic_pF'];expected=np.array([cp,cp+coefficient,cp+er*coefficient]);observed=expected+physical['open_reference_sample_errors_pF'];estimated=(observed[2]-observed[0])/(observed[1]-observed[0]);result['physical_interface']={'coax_coefficient_pF_per_epsilon_r':coefficient,'nominal_open_reference_sample_pF':expected.tolist(),'synthetic_readings_pF':observed.tolist(),'epsilon_r_from_open_reference_sample':float(estimated),'single_sample_equivalent_pair':[[er,cp],[er+.25,cp-.25*coefficient]],'boundary_and_measurement':'published ideal coax model plus additive parasitic/readout; no actual instrument or material calibration'}
    (out/'actual.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--development',type=Path,required=True);p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();result=run(a.spec,a.development,a.evaluation,a.out);print(json.dumps({'operator':[12,64],'reconstructions':len(result['reconstructions']),'mismatch':len(result['mismatch']),'locked':result['locked_selection']['overall']}))
if __name__=='__main__':main()
