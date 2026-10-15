"""Independent Fraction coefficient checks; does not import business API."""
import pathlib,json,ast,itertools,math
from fractions import Fraction as F
root=pathlib.Path(__file__).resolve().parent;cfg=json.loads((root/'snapshot/code/fixed-inputs.json').read_text());got=json.loads((root/'fixed-cli-stdout.json').read_text());manual=json.loads((root/'snapshot/code/independent-expected.json').read_text());api=json.loads((root/'api-probe-stdout.json').read_text());checks=[]
def check(name,a,b):checks.append({'check':name,'match':a==b,'actual':str(a),'expected':str(b)})
def read(e):return {tuple(v['powers']):F(v['numerator'],v['denominator']) for v in e['terms'] if v['numerator']}
def clean(p):return {e:v for e,v in p.items() if v}
def add(*ps):
    result={}
    for p in ps:
        for e,v in p.items():result[e]=result.get(e,F(0))+v
    return clean(result)
def scale(p,a):return clean({e:v*a for e,v in p.items()})
def mul(p,q):
    result={}
    for e,c in p.items():
        for d,a in q.items():
            powers=tuple(x+y for x,y in zip(e,d));result[powers]=result.get(powers,F(0))+c*a
    return clean(result)
def power(p,n,vars=2):
    r={(0,)*vars:F(1)}
    for i in range(n):r=mul(r,p)
    return r
def evaluate(p,point):return sum((c*math.prod(F(x)**e for x,e in zip(point,powers)) for powers,c in p.items()),F(0))
def diff(p,i):return clean({tuple(v-int(j==i) for j,v in enumerate(e)):c*e[i] for e,c in p.items() if e[i]})
def sub(p,images):
    result={};n=len(next(iter(images[0])))
    for e,c in p.items():
        term={(0,)*n:c}
        for degree,img in zip(e,images):term=mul(term,power(img,degree,n))
        result=add(result,term)
    return result
def manualdict(d):return {ast.literal_eval(k):F(v) for k,v in d.items()}
ps={name:read(v) for name,v in cfg['polynomials'].items()};x={(1,0):F(1)};y={(0,1):F(1)}
expectedps={'f':{(2,0):F(1),(0,1):F(-1)},'g':{(0,2):F(1),(1,0):F(-1)},'parabola':{(0,1):F(1),(2,0):F(-1)},'cusp':{(0,2):F(1),(3,0):F(-1)},'node':{(0,2):F(1),(2,0):F(-1),(3,0):F(-1)},'axis':y,'double_axis':{(0,2):F(1)},'hyperbola':{(1,1):F(1),(0,0):F(-1)}}
check('eight_input_names',set(ps),set(expectedps));check('output_eight_names',set(got['inputs']),set(expectedps))
for name,p in expectedps.items():check('input/'+name,ps[name],p);check('reported_input/'+name,read(got['inputs'][name]),p)
g1=add(x,scale(power(y,2),-1));g2=add(power(y,4),scale(y,-1))
check('basis/g1',read(got['basis'][0]),g1);check('basis/g2',read(got['basis'][1]),g2)
identities={'g1_plus_g':add(g1,ps['g']),'g2_minus_f_minus_x_plus_y2_times_g':add(g2,scale(ps['f'],-1),scale(mul(add(x,power(y,2)),ps['g']),-1)),'f_minus_x_plus_y2_times_g1_minus_g2':add(ps['f'],scale(mul(add(x,power(y,2)),g1),-1),scale(g2,-1))}
t={(1,):F(1)};one={(0,):F(1)}
identities.update(parabola_parameter=sub(ps['parabola'],[t,power(t,2,1)]),cusp_parameter=sub(ps['cusp'],[power(t,2,1),power(t,3,1)]),node_parameter=sub(ps['node'],[add(power(t,2,1),scale(one,-1)),mul(t,add(power(t,2,1),scale(one,-1)))]))
check('identity_names',set(got['identities']),set(identities));check('manual/identity_names',set(manual['identity_names_all_zero']),set(identities))
for name,p in identities.items():check('independent_identity/'+name,p,{});check('reported_identity/'+name,read(got['identities'][name]),p)
S=add(mul(power(y,4),g1),scale(mul(x,g2),-1));q0=y;q1=scale(power(y,2),-1)
check('s_direct_expansion',S,{(1,1):F(1),(0,6):F(-1)});check('s_reported',read(got['s_polynomial']),S);check('manual/S',manualdict(manual['s_polynomial']),S)
for i,q in enumerate([q0,q1]):check('S/quotient'+str(i),read(got['s_quotients'][i]),q);check('manual/Squot'+str(i),manualdict(manual['s_quotients'][i]),q)
check('S/certificate_reassembly',add(mul(q0,g1),mul(q1,g2)),S);check('S/remainder',read(got['s_remainder']),{});check('manual/Sremainder',manual['s_remainder'],{})
for name,e in got['jacobians'].items():
    curve,pointname=name.split('@');point=cfg['points'][pointname];r=[evaluate(diff(ps[curve],j),point) for j in range(2)];rank=int(any(r))
    check('Jacobian/'+name+'/oncurve',evaluate(ps[curve],point),F(0));check('Jacobian/'+name+'/row',list(map(F,e['row'])),r);check('Jacobian/'+name+'/rank',e['rank'],rank);check('Jacobian/'+name+'/dimension',e['tangent_dimension'],2-rank)
    check('manual/Jacobian/'+name,manual['jacobians'][name],{'row':[int(v) for v in r],'rank':rank,'tangent_dimension':2-rank})
for name,e in got['homogeneous'].items():
    p=ps[name];degree=max(sum(powers) for powers in p);h={powers+(degree-sum(powers),):c for powers,c in p.items()}
    check('homogeneous/'+name,read(e),h);check('manual/homogeneous/'+name,manualdict(manual['homogeneous'][name]),h)
    for point in manual['infinity_points'][name]:check('infinity/'+name+'/'+str(point),evaluate(h,point),F(0));check('nonzero_projective/'+name+'/'+str(point),any(point),True)
    # At Z=0 the exact polynomials are -X^2, XY, -X^3 respectively.
    actual_infinity={powers[:2]:c for powers,c in h.items() if powers[2]==0}
    check('infinity_equation/'+name,actual_infinity,{'parabola':{(2,0):F(-1)},'hyperbola':{(1,1):F(1)},'cusp':{(3,0):F(-1)}}[name])
check('standard_monomials',manual['standard_monomials'],[[0,j] for j in range(4)])
# Fixed y(y^3-1): derivative4y^3-1 is -1 at0 and3 at any cube root1, all nonzero in char0.
check('zero_count_char0',manual['zero_count_over_algebraically_closed_characteristic_0'],4)
check('distinct_root_derivative_y0',4*F(0)**3-1,F(-1));check('distinct_root_derivative_cube_roots',4*F(1)-1,F(3))
char3=add(mul(y,power(add(y,{(0,0):F(-1)}),3)),scale(g2,-1))
check('char3_polynomial_coeffs_divisible3',all(c.denominator==1 and c.numerator%3==0 for c in char3.values()),True)
check('char3_manual_string',manual['characteristic_3_counterexample'],'y^4-y = y*(y-1)^3')
# Different ideals: every monomial of a multiple of y^2 has y exponent>=2; y violates this.
check('y_not_multiple_of_y2',any(e[1]<2 for e in y),True)
check('axis_same_field_zero_equivalence',[evaluate(ps['axis'],[3,v])==0 for v in [F(-2),F(-1,3),F(0),F(3,5),F(9)]],[evaluate(ps['double_axis'],[3,v])==0 for v in [F(-2),F(-1,3),F(0),F(3,5),F(9)]])
# Generated affine ideal (x,y-x^2) contains y; naive homogenization leaves false infinity point.
naive=[{(1,0,0):F(1)},{(0,1,1):F(1),(2,0,0):F(-1)}];fake=(0,1,0)
check('naive_fake_point_survives',[evaluate(p,fake) for p in naive],[F(0),F(0)])
check('full_ideal_added_y_excludes_fake',evaluate({(0,1,0):F(1)},fake),F(1))
check('affine_ideal_y_identity',add(ps['parabola'],power(x,2)),y)
obs={v['name']:v for v in api['observations']}
for name,e in obs.items():
    if e['expected_kind']=='ValueError':check('reject/'+name,e['kind'],'exception');check('reject/'+name+'/type',e.get('exception'),'ValueError')
    else:check('accept/'+name,e['kind'],'value')
p=read(obs['p']['value']);q=read(obs['q']['value'])
for name,v in [('sum',add(p,q)),('product',mul(p,q)),('dx',diff(p,0)),('dy',diff(p,1)),('substitution',sub(p,[{(1,):F(1),(0,):F(1)},{(2,):F(1)}]))]:check('general_ops/'+name,read(obs[name]['value']),v)
check('general_ops/eval',F(obs['eval']['value']),evaluate(p,[F(2,3),F(-3,5)]))
for name,ds in [('division_order1',[p,q]),('division_order2',[q,p])]:
    quot,r=obs[name]['value'];r=read(r);total=add(r,*(mul(read(qi),di) for qi,di in zip(quot,ds)))
    check('arbitrary_division/'+name+'/identity',total,add(mul(p,q),y))
    # Lex remainder condition: no remainder monomial divisible by any divisor leading monomial.
    check('arbitrary_division/'+name+'/irreducible',all(not all(i>=j for i,j in zip(e,max(di))) for e in r for di in ds),True)
check('zero_dividend/remainder',read(obs['zero_dividend']['value'][1]),{})
check('empty_poly',read(obs['empty']['value']),{});check('zero_coeff_poly',read(obs['zero_coeff']['value']),{})
check('rank_empty',obs['rank_empty']['value'],0);check('rank_empty_rows',obs['rank_empty_rows']['value'],0)
# A nonzero2x2 minor proves rank>=2; row2=2row1 proves rank<=2 independently of row-reduction.
check('rank_matrix',obs['rank_matrix']['value'],2)
check('rank_witness_minor',1*0-2*1,F(-2))
check('MAX_STEPS_constant',obs['MAX_STEPS_published']['value'],2000)
check('step_limit2_message',obs['step_limit_2'].get('message'),'division step bound exceeded')
qs,rr=obs['step_limit_3']['value'];check('step_exact3_quotient',read(qs[0]),{(2,0):F(1),(1,0):F(1),(0,0):F(1)});check('step_exact3_remainder',read(rr),{})
check('two_cli_outputs_bytes',(root/'fixed-cli-stdout.json').read_bytes()==(root/'examples-cli-stdout.json').read_bytes(),True)
check('accept/degree64_exact',read(obs['degree64']['value']),{(64,0):F(1)})
check('accept/num4096bits_exact',read(obs['num4096bits']['value']),{(0,):F(1<<4095)})
check('accept/den4096bits_exact',read(obs['den4096bits']['value']),{(0,):F(1,1<<4095)})
check('accept/terms256_exact_count',len(read(obs['terms256']['value'])),256)
check('accept/decode128_exact_count',len(read(obs['decode_128terms']['value'])),128)
check('accept/decode_max_exact',read(obs['decode_max']['value']),{(12,12):F(1)})
check('accept/power0_exact',read(obs['power0']['value']),{(0,0):F(1)})
check('accept/power12_exact',read(obs['power12']['value']),{(12,0):F(1)})
reject=json.loads((root/'fixed-reject-execution.json').read_text())
check('CLI_bool_point_exit',reject['exit_code'],1)
check('CLI_bool_point_no_success_output',(root/'fixed-reject-stdout.json').read_bytes(),b'')
check('CLI_bool_point_expected_reason','ValueError: integer fixed points required' in (root/'fixed-reject-stderr.txt').read_text(),True)
summary={'business_api_imported' :False,'checks_total':len(checks),'all_match':all(c['match'] for c in checks),'failed_checks':[c for c in checks if not c['match']],'api_cases':len(obs),'rejection_cases':sum(v['expected_kind']=='ValueError' for v in obs.values()),'step_scope':'in-memory guard2/3 branch tested; published2000 checked; natural2001-step witness not run','general_NS_Hilbert_or_scheme_proof_certified':False,'checks':checks}
(root/'oracle-results.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='checks'},indent=2))
if not summary['all_match']:raise SystemExit(1)
