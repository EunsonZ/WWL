"""No business imports. Exact population algebra; independent data/DFT/certificate reconstruction."""
import pathlib,json,csv,math,random,itertools
from fractions import Fraction as F
root=pathlib.Path(__file__).resolve().parent;cfg=json.loads((root/'fixed-inputs.json').read_text());expected=json.loads((root/'expected-before-run.json').read_text());checks=[];maxdiff=0.
ABS=cfg['comparison_tolerances_declared_before_run']['deterministic_absolute'];REL=cfg['comparison_tolerances_declared_before_run']['deterministic_relative']
def check(name,a,b):checks.append({'check':name,'match':a==b,'actual':str(a),'expected':str(b)})
def close(name,a,b):
    global maxdiff
    diff=abs(a-b);maxdiff=max(maxdiff,diff);checks.append({'check':name,'match':math.isclose(a,b,abs_tol=ABS,rel_tol=REL),'absolute_difference':diff})
def sequence(name,a,b):
    check(name+'/length',len(a),len(b));d=max((abs(x-y) for x,y in zip(a,b)),default=0.)
    checks.append({'check':name,'match':all(math.isclose(x,y,abs_tol=ABS,rel_tol=REL) for x,y in zip(a,b)),'max_absolute_difference':d,'points':len(a)})
def solve2(R,p):
    det=R[0][0]*R[1][1]-R[0][1]*R[1][0]
    return [(p[0]*R[1][1]-p[1]*R[0][1])/det,(R[0][0]*p[1]-R[1][0]*p[0])/det]
def quad(R,p,w):return F(1)-2*sum(x*y for x,y in zip(w,p))+sum(w[i]*R[i][j]*w[j] for i in range(len(w)) for j in range(len(w)))
R=[[F(2),F(1,2)],[F(1,2),F(2)]];p=[F(1),F(1,2)];w=solve2(R,p)
check('two_tap_weights',w,list(map(F,expected['weights'])));check('two_tap_mse',quad(R,p,w),F(expected['two_tap_mse']))
Rs=[[F(2),F(1,2),F(1,4)],[F(1,2),F(2),F(1,2)],[F(1,4),F(1,2),F(2)]];ps=[F(1,2),F(1),F(1,2)];ws=list(map(F,expected['smoothing_weights']))
check('smoothing_normal_eq',[sum(a*b for a,b in zip(row,ws)) for row in Rs],ps);check('smoothing_mse',quad(Rs,ps,ws),F(expected['smoothing_mse']))
points=[F(-1),F(0),F(1)];ds=[x*x-F(2,3) for x in points]
check('nonlinear_cross',sum(x*d for x,d in zip(points,ds)),F(0));check('nonlinear_linear_mse',sum(d*d for d in ds)/3,F(2,9));check('nonlinear_full_function_mse',sum((d-(x*x-F(2,3)))**2 for x,d in zip(points,ds))/3,F(0))
Rc=[[F(2),F(1)],[F(1),F(2)]];new=solve2(Rc,p)
check('noise_new_weights',new,[F(1,2),F(0)]);check('noise_old_mse',quad(Rc,p,w),F(119,225));check('noise_new_mse',quad(Rc,p,new),F(1,2))
check('noise_old_error_moments',[p[i]-sum(Rc[i][j]*w[j] for j in range(2)) for i in range(2)],[F(-1,15),F(-7,30)])
check('noise_new_error_moments',[p[i]-sum(Rc[i][j]*new[j] for j in range(2)) for i in range(2)],[F(0),F(0)])
gain=2*math.sqrt(3)-3;pole=2-math.sqrt(3);bilat=math.sqrt(3)/4
close('Riccati',gain*gain+6*gain-3,0.);close('causal_gain_pole_relation',.5*(1-gain),pole)
close('delay_real',math.cos(-2*math.pi/4),0.);close('delay_imag',math.sin(-2*math.pi/4),-1.)
for angle in [0.,.3,1.2,2.9]:
    spec=(2-math.cos(angle))/(1.25-math.cos(angle));factor=(2+math.sqrt(3))/2*(1+pole*pole-2*pole*math.cos(angle))/(1.25-math.cos(angle))
    close('spectral_factor/'+str(angle),spec,factor)
dc=[]
for N in expected['DC_N']:
    def innovation_coefficient_loss(a):
        # Expand target - sum a_j*(u[-j]-u[-j-1]); white u innovations independent variance1.
        coefficients=[1-a[0]]+[a[j-1]-a[j] for j in range(1,N)]+[a[-1]]
        return sum(c*c for c in coefficients)
    tapered=[F(N-j,N) for j in range(N)];direct=[F(1)]*N
    tr=innovation_coefficient_loss(tapered);dr=innovation_coefficient_loss(direct)
    check('DC_tapered/'+str(N),tr,F(1,N));check('DC_direct/'+str(N),dr,F(1));dc.append({'N':N,'tapered':str(tr),'direct':str(dr)})
check('DC_spectral_zero',2-2*math.cos(0),0.)
# Finite-lag covariance units: C_l[V²], normalized angular frequency[rad/sample], integral C0.
for M in [1,7,32]:
    for k in range(-M,M+1):check('finite_lag_cov_even/'+str(M)+'/'+str(k),F(1,2)**abs(k)+int(k==0),F(1,2)**abs(-k)+int(k==0))
    grid=512;values=[sum((float(F(1,2)**abs(k)+int(k==0))*math.cos(k*2*math.pi*j/grid) for k in range(-M,M+1))) for j in range(grid)]
    close('finite_lag_psd_integral/'+str(M),math.fsum(values)/grid,2.)
# Model reconstructor draws raw innovations before computing trajectories; no business helper.
def model(seed,size,rho):
    rng=random.Random(seed);normals=[rng.gauss(0,1) for _ in range(2*size+2)]
    state=normals[0];noise=normals[1];ss=[];xx=[]
    for n in range(size):
        state=.5*state+math.sqrt(.75)*normals[2*n+2]
        noise=rho*noise+math.sqrt(1-rho*rho)*normals[2*n+3]
        ss.append(state);xx.append(state+noise)
    return ss,xx
causal_coeff=[gain*pole**k for k in range(64)]
bilateral_coeff=[bilat*pole**k for k in range(33)]
population={'current':.5,'two_tap_theory':7/15,'three_tap_smoothing':7/16,'causal_infinite':gain,'bilateral_infinite':bilat,'wrong_noise_old_weights':119/225,'correlated_noise_current':.5}
summary_tables={};psd_observations={}
for run in ['preflight','standard']:
    data=json.loads((root/run/'results.json').read_text());settings=cfg[run];Ntrain=settings['train'];Ntest=settings['test'];repeat=settings['repeats'];observed={name:[] for name in data['observed_mse']}
    check(run+'/fixed_parameters',(data['fixed_inputs']['repeats'],data['fixed_inputs']['train'],data['fixed_inputs']['test']),(repeat,Ntrain,Ntest))
    check(run+'/window',(data['fixed_inputs']['evaluation_start'],data['fixed_inputs']['evaluation_stop']),(128,Ntest-32))
    check(run+'/train_test_seed_disjoint',set(179000+i for i in range(repeat)).isdisjoint(179100+i for i in range(repeat)),True)
    for name,v in population.items():close(run+'/analytic/'+name,data['analytic_predictions'][name],v)
    for rep in range(repeat):
        st,xt=model(179000+rep,Ntrain,0);s,x=model(179100+rep,Ntest,0);sc,xc=model(179200+rep,Ntest,.5)
        # Independent mean products and analytic2x2 Cramer solve, not source LU/fit.
        RR=[[math.fsum(xt[n-i]*xt[n-j] for n in range(1,Ntrain))/(Ntrain-1) for j in range(2)] for i in range(2)]
        pp=[math.fsum(xt[n-i]*st[n] for n in range(1,Ntrain))/(Ntrain-1) for i in range(2)];ww=solve2(RR,pp)
        fit=data['fits'][rep]
        for i in range(2):
            close(run+f'/rep{rep}/p{i}',fit['p'][i],pp[i]);close(run+f'/rep{rep}/w{i}',fit['weights'][i],ww[i])
            for j in range(2):close(run+f'/rep{rep}/R{i}{j}',fit['R'][i][j],RR[i][j])
        times=list(range(128,Ntest-32));est={
            'current':[.5*x[n] for n in times],
            'two_tap_theory':[float(w[0])*x[n]+float(w[1])*x[n-1] for n in times],
            'two_tap_fit':[ww[0]*x[n]+ww[1]*x[n-1] for n in times],
            'three_tap_smoothing':[float(ws[0])*x[n-1]+float(ws[1])*x[n]+float(ws[2])*x[n+1] for n in times],
            # Independent finite impulse convolution; tail at64 is below machine accuracy here.
            'causal_infinite':[math.fsum(causal_coeff[k]*x[n-k] for k in range(64)) for n in times],
            'bilateral_truncated':[bilateral_coeff[0]*x[n]+math.fsum(bilateral_coeff[k]*(x[n-k]+x[n+k]) for k in range(1,33)) for n in times]}
        if rep==0:
            for label,(ss,xx) in [('train',(st,xt)),('test',(s,x)),('correlated_test',(sc,xc))]:
                records=list(csv.DictReader((root/run/(label+'.csv')).open()))
                check(run+'/csv/'+label+'/index',[int(r['n']) for r in records],list(range(len(ss))))
                sequence(run+'/csv/'+label+'/signal',[float(r['s_V']) for r in records],ss);sequence(run+'/csv/'+label+'/observed',[float(r['x_V']) for r in records],xx)
            recorded=list(csv.DictReader((root/run/'estimates.csv').open()));check(run+'/csv/estimate_times',[int(r['n']) for r in recorded],times)
            for name,values in est.items():sequence(run+'/csv/estimates/'+name,[float(r[name]) for r in recorded],values)
        # Recompute each replica on the declared shared/changed-noise windows.
        for name,values in est.items():
            errors=[s[n]-v for n,v in zip(times,values)];mse=math.fsum(e*e for e in errors)/len(errors);observed[name].append(mse)
            close(run+f'/rep{rep}/mse/'+name,data['observed_mse'][name]['values'][rep],mse)
            actual=data['observed_error_moments'][name][rep];close(run+f'/rep{rep}/error_mean/'+name,actual['mean_error'],math.fsum(errors)/len(errors))
            for lag in [-1,0,1]:close(run+f'/rep{rep}/moment/'+name+'/'+str(lag),actual['error_observation_moments'][str(lag)],math.fsum(e*x[n-lag] for e,n in zip(errors,times))/len(errors))
        for name,weights in [('wrong_noise_old_weights',w),('correlated_noise_current',new)]:
            errors=[sc[n]-(float(weights[0])*xc[n]+float(weights[1])*xc[n-1]) for n in range(1,Ntest)];mse=math.fsum(e*e for e in errors)/len(errors);observed[name].append(mse)
            close(run+f'/rep{rep}/mse/'+name,data['observed_mse'][name]['values'][rep],mse);actual=data['observed_error_moments'][name][rep]
            close(run+f'/rep{rep}/error_mean/'+name,actual['mean_error'],math.fsum(errors)/len(errors))
            for lag in [0,1]:close(run+f'/rep{rep}/moment/'+name+'/'+str(lag),actual['error_observation_moments'][str(lag)],math.fsum(e*xc[n-lag] for e,n in zip(errors,range(1,Ntest)))/len(errors))
    table=[]
    for name,values in observed.items():
        mean=math.fsum(values)/repeat;std=math.sqrt(math.fsum((v-mean)**2 for v in values)/(repeat-1)) if repeat>1 else None
        close(run+'/summary/'+name+'/mean',data['observed_mse'][name]['mean'],mean)
        if std is not None:close(run+'/summary/'+name+'/std',data['observed_mse'][name]['sample_std'],std)
        table.append({'method':name,'population_mse':population.get(name),'observed_mean':mean,'sample_std':std,'standard_error':std/math.sqrt(repeat) if std is not None else None})
    summary_tables[run]=table
    # Independent real sine/cosine DFT for all1024 nonoverlapping white segments.
    rng=random.Random(179300);groups=[];first_segment=None
    c=[math.cos(2*math.pi*5*j/64) for j in range(64)];q=[math.sin(2*math.pi*5*j/64) for j in range(64)]
    for group in range(128):
        vals=[]
        for segment in range(8):
            raw=[rng.gauss(0,1) for _ in range(64)]
            if first_segment is None:first_segment=raw
            real=math.fsum(v*a for v,a in zip(raw,c));imag=-math.fsum(v*b for v,b in zip(raw,q));vals.append((real*real+imag*imag)/64)
        groups.append(vals);sequence(run+'/PSD/group'+str(group),data['psd_independent_segments']['segment_periodograms'][group],vals)
    singles=[v[0] for v in groups];averages=[math.fsum(v)/8 for v in groups];psd=data['psd_independent_segments']
    for name,values in [('single',singles),('averages',averages)]:
        sequence(run+'/PSD/'+name+'/all_values',psd[name]['values'],values);mean=math.fsum(values)/128;variance=math.fsum((v-mean)**2 for v in values)/127
        close(run+'/PSD/'+name+'/mean',psd[name]['mean'],mean);close(run+'/PSD/'+name+'/sample_variance',psd['single_sample_variance' if name=='single' else 'average_sample_variance'],variance)
    # Parseval checks two-sided angular PSD normalization, not a Hz assignment.
    bins=[]
    for k in range(64):
        real=math.fsum(v*math.cos(2*math.pi*k*j/64) for j,v in enumerate(first_segment));imag=math.fsum(-v*math.sin(2*math.pi*k*j/64) for j,v in enumerate(first_segment));bins.append((real*real+imag*imag)/64)
    close(run+'/PSD/Parseval',math.fsum(bins)/64,math.fsum(v*v for v in first_segment)/64)
    check(run+'/PSD/layout',(psd['groups'],psd['K'],psd['N'],psd['bin']),(128,8,64,5))
    psd_observations[run]={'single_mean':psd['single']['mean'],'single_sample_variance':psd['single_sample_variance'],'average_mean':psd['averages']['mean'],'average_sample_variance':psd['average_sample_variance'],'population_expectations':{'mean':1,'single_variance':1,'average_variance':.125},'statistical_pass_rule':'none; descriptive finite observations only','two_sided_angular_units':'V^2/(rad/sample)','physical_Hz_units':'fs not specified; conversion would divide angular PSD by fs with theta=2*pi*f/fs'}
report={'business_source_imported':False,'checks_total':len(checks),'all_match':all(c['match'] for c in checks),'failed_checks':[c for c in checks if not c['match']],'declared_tolerances':{'abs':ABS,'rel':REL},'scalar_max_abs_difference':maxdiff,'DC_exact':dc,'summary_tables':summary_tables,'psd_observations':psd_observations,'causal_independent_convolution_taps':64,'causal_tail_factor':pole**64,'general_log_outer_or_BIBO_or_real_sensor_certified':False,'checks':checks}
(root/'oracle-results.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
if not report['all_match']:raise SystemExit(1)
