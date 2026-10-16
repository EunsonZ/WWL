"""Independent finite coefficient oracle and convex dual certificates; no imaging_lab import."""
import argparse,json,math
from pathlib import Path
from fractions import Fraction as Q
import numpy as np


def matrix(psf,boundary):
    a=[[Q(0) for _ in range(64)] for _ in range(12)]
    for source in range(64):
        r,c=divmod(source,8)
        for i in range(3):
            for j in range(3):
                rr,cc=r+i-1,c+j-1
                if boundary=='periodic':rr%=8;cc%=8
                if not (0<=rr<8 and 0<=cc<8) or rr//2>=3:continue
                a[(rr//2)*4+cc//2][source]+=Q(str(psf[i][j]))/4
    return a


def rank(a):
    a=[row[:] for row in a];pivot=0
    for col in range(len(a[0])):
        found=next((r for r in range(pivot,len(a)) if a[r][col]),None)
        if found is None:continue
        a[pivot],a[found]=a[found],a[pivot];v=a[pivot][col];a[pivot]=[x/v for x in a[pivot]]
        for r in range(pivot+1,len(a)):
            v=a[r][col]
            if v:a[r]=[x-v*y for x,y in zip(a[r],a[pivot])]
        pivot+=1
        if pivot==len(a):break
    return pivot


def incidence():
    d=[]
    for r in range(8):
        for c in range(8):
            for a,b in [(r*8+c,r*8+c+1) if c<7 else (-1,-1),(r*8+c,(r+1)*8+c) if r<7 else (-1,-1)]:
                if a<0:continue
                row=np.zeros(64);row[a]=-1;row[b]=1;d.append(row)
    return np.array(d)


def close(a,b,tol=1e-10):np.testing.assert_allclose(a,b,rtol=tol,atol=tol)


def reference_quadratic(a,y,candidate):
    # AAt eigensystem, distinct from the implementation's thin SVD of A.
    gram=a@a.T;v,u=np.linalg.eigh(gram);parameter=candidate['parameter']
    if candidate['method']=='ridge':return a.T@np.linalg.solve(gram+parameter*np.eye(len(y)),y)
    cutoff=max(parameter*parameter*max(v),1e-24*max(v));f=np.divide(1,v,out=np.zeros_like(v),where=v>cutoff);return a.T@u@(f*(u.T@y))


def certificate(a,y,d,lam,epsilon,fit):
    x=np.array(fit['x']);p=np.array(fit['dual_data']);q=np.array(fit['dual_tv']);assert max(abs(q))<=lam+1e-14;close(p,a@x-y)
    primal=.5*np.linalg.norm(a@x-y)**2+.5*epsilon*(x@x)+lam*np.abs(d@x).sum();v=a.T@p+d.T@q;dual=-.5*(p@p)-y@p-(v@v)/(2*epsilon);gap=float(primal-dual);close(primal,fit['objective']);close(gap,fit['gap']);assert -1e-10<=gap<=1e-6 and fit['converged']
    station=float(np.linalg.norm(a.T@p+epsilon*x+d.T@q));return {'gap':gap,'stationarity_norm':station,'model_distance_upper_from_floating_gap':math.sqrt(2*max(0,gap)/epsilon),'not_interval_arithmetic':True}


def check(spec,dev,evaluation,actual,selection):
    exact=matrix(spec['psf'],'zero');assert rank(exact)==12;assert all(not v for row in exact for v in row[-8:]);a=np.array(exact,float);close(a,actual['operator'],tol=0);d=incidence();close(d,actual['difference'],tol=0)
    development=np.array(dev['truth']).ravel();test=np.array(evaluation['truth']).ravel();yf=a@development+dev['noise_fit'];yv=a@development+dev['noise_validation'];yt=a@test+evaluation['noise_fit'];yr=a@test+evaluation['noise_repeat'];close(yf,actual['development']['fit']);close(yv,actual['development']['validation']);close(yt,actual['evaluation']['fit']);close(yr,actual['evaluation']['repeat']);certificates=[]
    for row,candidate in zip(selection['rows'],spec['candidates']):
        assert row['candidate']==candidate
        if candidate['method']=='tv':certificates.append(certificate(a,yf,d,candidate['parameter'],spec['solver']['epsilon'],row['fit']))
        else:close(reference_quadratic(a,yf,candidate),row['fit']['x'])
        close(np.mean((a@row['fit']['x']-yv)**2),row['validation_mse'])
    by_family={}
    for method in ['tsvd','ridge','tv']:
        candidates=[(i,row) for i,row in enumerate(selection['rows']) if row['candidate']['method']==method];by_family[method]=min(candidates,key=lambda item:(item[1]['validation_mse'],item[0]))[1]['candidate']
    assert by_family==actual['locked_selection']['by_family'];assert min(enumerate(selection['rows']),key=lambda item:(item[1]['validation_mse'],item[0]))[1]['candidate']==actual['locked_selection']['overall']
    expected_jobs={'pinv':{'method':'tsvd','parameter':0},'truncated_fixed':{'method':'tsvd','parameter':spec['fixed_truncated_reference']},'ridge_selected':by_family['ridge'],'tv_selected':by_family['tv']}
    for row in actual['reconstructions']:
        assert row['candidate']==expected_jobs[row['id']];c=row['candidate'];fit=row['fit'];x=np.array(fit['x'])
        if c['method']=='tv':certificates.append(certificate(a,yt,d,c['parameter'],spec['solver']['epsilon'],fit))
        else:close(reference_quadratic(a,yt,c),x)
        e=x-test;metric=row['metrics'];mse=np.mean(e*e);close(mse,metric['mse']);close(10*math.log10(spec['psnr_max']**2/mse),metric['psnr_db']);close(np.linalg.norm(a@x-yt),metric['measurement_residual_norm']);close(np.mean((a@x-yr)**2),metric['repeat_prediction_mse']);close(np.mean(e[-8:]**2),metric['unobserved_last_row_mse'])
    for row in actual['mismatch']:
        h=spec['psf'] if row['id']=='wrong_periodic' else np.asarray(spec['psf'])[::-1,::-1];b='periodic' if row['id']=='wrong_periodic' else 'zero';wrong=np.array(matrix(h,b),float);close(wrong,row['operator'],tol=0);certificates.append(certificate(wrong,yt,d,by_family['tv']['parameter'],spec['solver']['epsilon'],row['fit']));close(np.linalg.norm(a@row['fit']['x']-yt),row['true_model_residual'])
    probes=actual['operator_checks'];z=np.array(probes['probe_z']);x=np.array(probes['probe_x']).ravel();close(a.T@z,np.array(probes['scatter_adjoint']).ravel());close(x@(a.T@z),probes['inner_left']);close(.04*(a@x)@z,probes['weighted_right']);assert probes['zero_corner'][0]==13/64;assert sum(probes['periodic_corner'])==15/64;assert probes['AtA_corner'][0][0]==169/4096;assert probes['fft_zero_max_difference']<1e-12 and probes['fft_periodic_max_difference']<1e-12
    physical=actual['physical_interface'];p=spec['physical_interface'];coefficient=2*math.pi/(4*math.pi*1e-7*299792458**2)*p['length_m']/math.log(p['b_m']/p['a_m'])*1e12;close(coefficient,physical['coax_coefficient_pF_per_epsilon_r']);pair=physical['single_sample_equivalent_pair'];assert all(er>0 and cp>=0 for er,cp in pair);close(coefficient*pair[0][0]+pair[0][1],coefficient*pair[1][0]+pair[1][1])
    return {'status':'PASS','exact_operator_shape':[12,64],'rational_rank':12,'nullity':52,'selection_candidates':len(selection['rows']),'certificate_count':len(certificates),'certificates':certificates,'linear_reference':'AAt eigensystem/normal solves; explicit rational scatter matrix','tv_reference':'independent primal-dual certificate, not repeated ADMM; floating arithmetic not interval proof','absolute_relative_tolerance':1e-10,'scope':'fixed raw development/evaluation/PSF; no imaging_lab import; not real acquisition or generic pixel oracle'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--development',type=Path,required=True);p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--result-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();load=lambda p:json.loads(p.read_text());r=check(load(a.spec),load(a.development),load(a.evaluation),load(a.result_dir/'actual.json'),load(a.result_dir/'selection.json'));a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'certificates':r['certificate_count'],'rank':r['rational_rank']}))
if __name__=='__main__':main()
