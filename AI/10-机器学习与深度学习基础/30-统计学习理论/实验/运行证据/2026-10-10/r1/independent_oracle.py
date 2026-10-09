"""Independent objective minimization; never imports business source."""
import json,pathlib,itertools,math,hashlib
from fractions import Fraction as Q
root=pathlib.Path(__file__).resolve().parent
cfg=json.loads((root/'snapshot/inputs.json').read_text()); got=json.loads((root/'stdout-direct.json').read_text())
P=[(Q(r['x']),Q(r['y']),Q(r['mass'])) for r in cfg['distribution']]
D=[(Q(r['x']),Q(r['y']),Q(r['mass'])) for r in cfg['shifted_distribution']]
ls=list(map(Q,cfg['lambdas'])); checks=[]; rows=[]
def check(label,actual,expected):
    if isinstance(expected,Q):actual=Q(actual)
    ok=actual==expected
    checks.append({'check':label,'match':ok,'actual':str(actual),'expected':str(expected)})
    return ok
def loss(w,xy):x,y=xy;return (1-y*w*x)/2
def empirical(w,s):return sum((loss(w,xy) for xy in s),Q(0))/len(s)
def optimize(s,lam):
    # Empirical objective a+b*w+lambda*w^2/2; minimize candidate values.
    b=empirical(Q(1),s)-empirical(Q(0),s)
    candidates=[Q(-1),Q(1)]
    stationary=-b/lam
    if -1<=stationary<=1:candidates.append(stationary)
    return min(candidates,key=lambda w:empirical(w,s)+lam*w*w/2)
def risk(w,dist):return sum((p*loss(w,(x,y)) for x,y,p in dist),Q(0))
ordered={lam:{key:Q(0) for key in ['train','risk','gap','shifted_risk','weight','regularized_objective','mass']} for lam in ls}
for seq in itertools.product(P,repeat=4):
    sample=[(x,y) for x,y,p in seq];mass=math.prod(p for x,y,p in seq)
    for lam in ls:
        w=optimize(sample,lam);train=empirical(w,sample); true=risk(w,P)
        vals={'train':train,'risk':true,'gap':true-train,'shifted_risk':risk(w,D),'weight':w,'regularized_objective':train+lam*w*w/2,'mass':Q(1)}
        for key,v in vals.items():ordered[lam][key]+=mass*v
for entry in got['iid_integrals']:
    n=entry['n'];lam=Q(entry['lambda']);sums={key:Q(0) for key in ['train','risk','gap','shifted_risk','weight','mass']};weights=[]
    for k in range(n+1):
        sample=[(Q(1),Q(1))]*k+[(Q(1),Q(-1))]*(n-k)
        w=optimize(sample,lam); weights.append(w)
        probability=Q(math.comb(n,k))*Q(3,4)**k*Q(1,4)**(n-k)
        train=empirical(w,sample);true=risk(w,P)
        values={'mass':probability,'w':w,'train':train,'risk':true,'gap':true-train,'shifted_risk':risk(w,D)}
        state=entry['states'][k]
        check(f'n{n}/lambda{lam}/k{k}/k',state['k'],k)
        for key,v in values.items():check(f'n{n}/lambda{lam}/k{k}/{key}',state[key],v)
        for key,v in [('mass',Q(1)),('train',train),('risk',true),('gap',true-train),('shifted_risk',risk(w,D)),('weight',w)]:sums[key]+=probability*v
    for key in entry['totals']:check(f'n{n}/lambda{lam}/total/{key}',entry['totals'][key],sums[key])
    check(f'n{n}/lambda{lam}/gap',entry['expected_gap'],sums['gap'])
    check(f'n{n}/lambda{lam}/excess',entry['expected_excess'],sums['risk']-Q(1,4))
    sensitivity=max(abs(loss(weights[k],(x,y))-loss(weights[k+1],(x,y))) for k in range(n) for x,y,_ in P)
    beta=Q(1,2)/lam/n
    check(f'n{n}/lambda{lam}/sensitivity',entry['actual_uniform_replace_one'],sensitivity)
    check(f'n{n}/lambda{lam}/beta',entry['beta_upper'],beta)
    check(f'n{n}/lambda{lam}/sensitivity_le_beta',sensitivity<=beta,True)
    check(f'n{n}/lambda{lam}/comparator_upper',entry['comparator_upper'],beta+lam/2)
    if n==4:
        for key in sums:check(f'ordered_4points/lambda{lam}/{key}',sums[key],ordered[lam][key])
    if lam in [Q(1,2),Q(2)]:
        mu=Q(1,2);second=mu*mu+Q(3,4)/n
        check(f'moments/n{n}/lambda{lam}/train',entry['totals']['train'],Q(1,2)-second/(4*lam))
        check(f'moments/n{n}/lambda{lam}/risk',entry['totals']['risk'],Q(1,2)-mu/(8*lam))
        check(f'moments/n{n}/lambda{lam}/gap',entry['expected_gap'],Q(3,4)/n/(4*lam))
    rows.append({'n':n,'lambda':str(lam),'train':str(sums['train']),'risk':str(sums['risk']),'gap':str(sums['gap']),'shifted_risk':str(sums['shifted_risk']),'actual_replace_one':str(sensitivity)})
for e in got['repeated_rows']:
    lam=Q(e['lambda']); expected=ordered[lam]
    for key in ['train','risk','gap']:check(f'repeated/lambda{lam}/{key}',e['expected_'+key],expected[key])
    check(f'repeated/lambda{lam}/units',e['independent_units'],4)
    check(f'repeated/lambda{lam}/rows',e['row_count'],64)
    check(f'repeated/lambda{lam}/valid_beta',e['valid_beta_from_independent_units'],Q(1,8)/lam)
    check(f'repeated/lambda{lam}/invalid_beta',e['invalid_beta_if_rows_assumed_iid'],Q(1,128)/lam)
    for seq in itertools.product(P,repeat=4):
        s=[(x,y) for x,y,p in seq]
        check(f'repeated/objective_and_output/lambda{lam}/'+''.join(str(P.index(v)) for v in seq),optimize(s,lam),optimize(s*16,lam))
check('repeated_false_iid_claim_counterexample',ordered[Q(1,2)]['gap']>Q(1,64),True)
for e in got['growth']:
    m=e['m']; patterns=list(itertools.product([0,1],repeat=m))
    thresholds=sorted(p for p in patterns if all(a<=b for a,b in zip(p,p[1:])))
    intervals=sorted(p for p in patterns if sum(v==1 and (j==0 or p[j-1]==0) for j,v in enumerate(p))<=1)
    check(f'growth/m{m}/threshold_patterns',e['threshold_patterns'],[list(p) for p in thresholds])
    check(f'growth/m{m}/interval_patterns',e['interval_patterns'],[list(p) for p in intervals])
    check(f'growth/m{m}/threshold',e['threshold'],m+1)
    check(f'growth/m{m}/interval',e['interval'],1+m*(m+1)//2)
    check(f'growth/m{m}/all_labels',e['all_labels'],2**m)
    check(f'growth/m{m}/sauer1',e['sauer_d1'],1+m)
    check(f'growth/m{m}/sauer2',e['sauer_d2'],1+m+m*(m-1)//2)
for e in got['rademacher']:
    n=e['n'];exact=Q(math.comb(n,n//2),2**n)
    check(f'rademacher/n{n}',e['scalar_fraction'],exact)
    check(f'rademacher/n{n}/upper',e['upper_float'],1/math.sqrt(n))
    if n==4:check('rademacher/direct_sign_enumeration',sum(Q(abs(sum(s)),4*16) for s in itertools.product([-1,1],repeat=4)),exact)
check('erm_transfer',got['erm_transfer_bound'],Q(7,100))
eps=math.sqrt(math.log(320)/400)
check('finite_class_bound',got['finite_class_epsilon_float'],eps)
check('model_original_best_class_risk',got['model']['original_best_class_risk'],Q(1,4))
check('output_input_identity',got['input'],cfg)
check('first_observer_output_equals_direct_retry',hashlib.sha256((root/'stdout.json').read_bytes()).hexdigest(),hashlib.sha256((root/'stdout-direct.json').read_bytes()).hexdigest())
report={'oracle_method':'n4 all 256 ordered four-point samples; minimize explicit empirical quadratic via stationary and boundary objective values; n16/64 independent moments plus binomial exact sums; growth binary-string monotonicity and number of one-blocks; repeat original samples 16 times and independently minimize','business_source_imported':False,'checks_total':len(checks),'failed_checks':[c for c in checks if not c['match']],'all_match':all(c['match'] for c in checks),'tables':rows,'ordered_n4':{str(lam):{key:str(v) for key,v in vals.items()} for lam,vals in ordered.items()},'checks':checks,'general_theory_certified':False}
(root/'oracle-results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2,ensure_ascii=False))
if not report['all_match']:raise SystemExit(1)
