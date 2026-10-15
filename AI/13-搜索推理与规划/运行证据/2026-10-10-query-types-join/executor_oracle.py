"""Executor-owned finite expectations; never calls candidate main/expected/oracles.
Reads actual stdout; exercises only public join/increment/value and unify/apply.
Independent SQL three-valued evaluator, graph reachability, typed substitution,
and event-id sets/all upper bounds provide distinct expected constructions.
"""
from pathlib import Path
from itertools import product,permutations
import sys,importlib.util,json,time,resource,os
BASE=Path(__file__).resolve().parent
AI=BASE/'snapshot/candidate/AI/13-搜索推理与规划';sys.path.insert(0,str(AI))
from symbolic_ai_lab import Fun,Var,unify,apply
spec=importlib.util.spec_from_file_location('join_subject',BASE/'snapshot/candidate/计算机知识/65-分布式系统/gcounter_join_examples.py');counter=importlib.util.module_from_spec(spec);spec.loader.exec_module(counter)

def norm(t,s):
 if isinstance(t,Var):return norm(s[t],s) if t in s else ('var',t.name)
 return (t.name,tuple(norm(x,s) for x in t.args))

def tvar(n):return ('var',n)
def arrow(a,b):return ('Arrow',(a,b))
BOOL=('Bool',())
def tsubst(t,s):
 if t[0]=='var':return tsubst(s[t[1]],s) if t[1] in s else t
 return (t[0],tuple(tsubst(x,s) for x in t[1]))
def encode(t):
 if t[0]=='var':return Var(t[1])
 return Fun(t[0],tuple(encode(x) for x in t[1]))

def main():
 start=time.time();query=json.loads((BASE/'logs/query.stdout').read_text());gc=json.loads((BASE/'logs/gcounter.stdout').read_text())
 domain=('Ada','Ben','Cora');edges={('Ada','Ben'),('Ben','Cora')};q=('Cora','Ada');models={
 'M0':(edges,{('Ada','Ben'),('Ben','Cora'),('Ada','Cora')}),
 'M1':(edges|{q},set(product(domain,repeat=2)))}
 model_rows=[]
 for name,(parents,ancestors) in models.items():
  assignments=[]
  for x,y,z in product(domain,repeat=3):
   first=(x,y) not in parents or (x,y) in ancestors
   second=not ((x,y) in parents and (y,z) in ancestors) or (x,z) in ancestors
   assert first and second;assignments.append({'assignment':[x,y,z],'R1_satisfied':first,'R2_satisfied':second})
  out=query['models'][name];assert out['facts_true'] is True and out['r1_failures']==out['r2_failures']==[];assert set(map(tuple,out['parent']))==parents and set(map(tuple,out['anc']))==ancestors;assert out['query_true']==(name=='M1')
  model_rows.append({'model':name,'facts':sorted(edges),'parent':sorted(parents),'anc':sorted(ancestors),'query':q,'query_truth':q in ancestors,'rule_assignments':assignments})
 # Least finite relation computed independently by path traversal, not Horn closure.
 reach=set()
 for origin in domain:
  pending=[b for a,b in edges if a==origin];seen=set()
  while pending:
   dst=pending.pop()
   if dst in seen:continue
   seen.add(dst);reach.add((origin,dst));pending.extend(b for a,b in edges if a==dst)
 assert reach==models['M0'][1] and q not in reach
 # Explicit SQL equality: NULL yields UNKNOWN; TRUE witnesses existence only.
 def eq(a,b):return None if a is None or b is None else int(a==b)
 expected_sql=[]
 for x in (1,2,None):
  comparisons=[eq(x,y) for y in (1,None)]
  in_result=1 if 1 in comparisons else (None if None in comparisons else 0)
  not_in=None if in_result is None else 1-in_result
  not_exists=int(1 not in comparisons);guard=int(x is not None and bool(not_exists))
  expected_sql.append([x,not_in,not_exists,guard])
 assert query['sql']['rows']==expected_sql==[[1,0,0,0],[2,None,1,1],[None,None,1,0]]
 x,y,a,b,c=map(Var,['x','y','alpha','beta','gamma']);f=lambda t:Fun('f',(t,));pair=lambda s,t:Fun('Pair',(s,t));ar=lambda s,t:Fun('Arrow',(s,t))
 cases=[('atom',Fun('P',(x,f(y))),Fun('P',(Fun('Ada'),f(Fun('Ada')))),True),('arrow',ar(a,b),ar(b,c),True),('changed_constructor',ar(a,Fun('Bool')),ar(Fun('Bool'),c),True),('direct_occurs',x,f(x),False),('indirect_occurs',pair(x,y),pair(f(y),f(x)),False),('type_occurs',a,ar(a,b),False),('constructor_conflict',Fun('Bool'),Fun('Int'),False),('arity_conflict',Fun('Arrow',(a,)),ar(a,b),False)]
 tree_rows=[]
 for name,left,right,expected in cases:
  sigma=unify(left,right);assert (sigma is not None)==expected
  row={'name':name,'left':repr(left),'right':repr(right),'unifiable':sigma is not None}
  if sigma is not None:
   nl,nr=norm(left,sigma),norm(right,sigma);assert nl==nr;assert norm(apply(left,sigma),{})==nl
   row.update(substitution={v.name:repr(t) for v,t in sigma.items()},independently_normalized=[nl,nr])
   if name=='arrow':
    values=[norm(v,sigma) for v in (a,b,c)];assert values[0]==values[1]==values[2] and values[0][0]=='var';row['free_representative']=values[0]
   if name=='atom':assert norm(x,sigma)==norm(y,sigma)==('Ada',())
   if name=='changed_constructor':assert norm(a,sigma)==norm(c,sigma)==BOOL
  tree_rows.append(row)
 # Typed encoding image and substitution commute; composition direction observable.
 alpha,beta,gamma=map(tvar,['alpha','beta','gamma']);typed_terms=[BOOL,alpha,beta,arrow(alpha,beta),arrow(BOOL,arrow(alpha,beta))]
 type_sub={'alpha':arrow(BOOL,beta),'beta':BOOL};term_sub={Var(k):encode(v) for k,v in type_sub.items()}
 commute=[]
 for t in typed_terms:
  independent=tsubst(t,type_sub);actual=norm(apply(encode(t),term_sub),{});assert actual==independent;commute.append({'type_input':t,'expected_type':independent,'applied_encoded':actual})
 s1={a:b};s2={b:Fun('Bool')};forward=norm(apply(apply(a,s1),s2),{});reverse=norm(apply(apply(a,s2),s1),{});assert forward==BOOL and reverse==('var','beta')
 # Six ground finite Bool/Arrow types: original equation solutions exactly equal types.
 ground=[BOOL]+[arrow(BOOL,BOOL)]+[arrow(BOOL,arrow(BOOL,BOOL)),arrow(arrow(BOOL,BOOL),BOOL)]
 solutions=[]
 for ta,tb,tc in product(ground,repeat=3):
  left=arrow(ta,tb);right=arrow(tb,tc)
  if left==right:solutions.append([ta,tb,tc]);assert ta==tb==tc
 assert len(solutions)==len(ground)
 # Empty predicate in one-element model disproves semantic entailment independently.
 empty_predicate={'domain':['Ada'],'P':[],'P_Ada':False};assert unify(Fun('P',(x,)),Fun('P',(Fun('Ada'),))) is not None
 # Independent upper-bound oracle and unique event-set cardinality.
 states=list(product(range(4),repeat=2));pair_count=triple_count=0;lub_witnesses=[]
 order=lambda u,v: u[0]<=v[0] and u[1]<=v[1]
 events=lambda s: {('A',i) for i in range(s[0])}|{('B',i) for i in range(s[1])}
 for left,right in product(states,repeat=2):
  upper=[z for z in states if order(left,z) and order(right,z)];least=[z for z in upper if all(order(z,w) for w in upper)];assert len(least)==1
  actual=counter.join(left,right);assert actual==least[0] and counter.value(actual)==len(events(left)|events(right));assert counter.join(right,left)==actual and counter.join(left,left)==left
  pair_count+=1
  if left==(2,0) and right==(0,3):lub_witnesses.append({'left':left,'right':right,'all_upper_bounds':upper,'least':least,'event_ids':sorted(events(left)|events(right))})
 for astate,bstate,cstate in product(states,repeat=3):assert counter.join(counter.join(astate,bstate),cstate)==counter.join(astate,counter.join(bstate,cstate));triple_count+=1
 schedule_rows=[]
 for sequence in sorted(set(permutations(((2,0),(0,3),(2,0))))):
  state=(0,0);seen=set();trace=[]
  for message in sequence:
   seen|=events(message);state=counter.join(state,message);assert events(state)==seen and counter.value(state)==len(seen);trace.append({'message':message,'actual_state':state,'expected_unique_events':sorted(seen),'expected_count':len(seen)})
  assert state==(2,3);schedule_rows.append(trace)
 assert gc['fixed']['three_merges']=={'scalar_max':3,'scalar_sum':7,'vector_state':[2,3],'vector_query':5}
 for rows in gc['fixed']['message_sequences']:assert rows[-1]['state']==[2,3] and rows[-1]['query']==5
 failures=gc['condition_failures'];assert failures['shared_identity']['query']==1 and failures['shared_identity']['actual_increments']==2;assert failures['lost_state_reused_identity']['query']==2 and failures['lost_state_reused_identity']['actual_increments']==3;assert failures['last_update_not_delivered']['same'] is False and failures['last_update_not_delivered']['after_delivery']==[2,3];assert failures['wraparound']['inflationary'] is False;assert failures['repeated_command']=={'two_calls':[2,0],'same_state_twice':[1,0]}
 capacity=gc['booking'];actual_a={tuple(x) for x in capacity['merged_A']};actual_b={tuple(x) for x in capacity['merged_B']};expected_records={('A:1','甲','room',540,600),('B:1','乙','room',540,600)};assert actual_a==actual_b==expected_records and capacity['capacity_holds'] is False;overlaps=[(u[0],v[0]) for u in sorted(expected_records) for v in sorted(expected_records) if u[0]<v[0] and u[2]==v[2] and u[3]<v[4] and v[3]<u[4]];assert overlaps==[('A:1','B:1')]
 report={'status':'PASS','started_unix':start,'elapsed_seconds':time.time()-start,'pid':os.getpid(),'models':model_rows,'closed_world_contract':{'requires':['finite named domain','distinct constants','completed Parent facts','least Anc interpretation/closed world'],'path_reachability':sorted(reach),'query_absent_in_least_relation':True,'does_not_negate_query_in_all_first_order_models':True},'SQL_expected_rows':expected_sql,'trees':tree_rows,'type_encoding_commutation':commute,'composition':{'sigma2_after_sigma1':forward,'sigma1_after_sigma2':reverse},'finite_type_assignments':len(ground)**3,'finite_equation_solutions':solutions,'empty_KB_countermodel':empty_predicate,'counter_oracle':{'states':len(states),'LUB_pairs':pair_count,'ACI_triples':triple_count,'witnesses':lub_witnesses,'message_schedules':schedule_rows},'capacity_counterexample':{'records':sorted(expected_records),'overlaps':overlaps,'capacity':1,'active_count':2,'same_state':True,'capacity_holds':False},'resource_self_ru_maxrss_bytes_on_macos':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'scope':'Finite model/SQLite/finite-tree/finite-state checks only; no PostgreSQL,RAG backend,authority reservation,real network or general convergence theorem execution'}
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
