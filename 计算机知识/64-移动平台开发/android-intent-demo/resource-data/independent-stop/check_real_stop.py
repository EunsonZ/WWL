"""Independent forced-run/explicit-timeout JobService probe; no authority DB or real booking."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import subprocess,threading,time,ssl,json
root=Path(__file__).resolve().parent
package='org.wwl.networkdemo.reviewfinal.resources';identity='review-stop-original'
adb=['/private/tmp/wwl-next-175-env/sdk/platform-tools/adb','-P','15037','-s','emulator-5580']
commands=[];events=[];held=threading.Event();restoring=False;previous=None
class Server(ThreadingHTTPServer):daemon_threads=True
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  events.append({'kind':'GET','path':self.path});held.set();time.sleep(5)
  b=json.dumps({'protocol':'wwl-reservation-v2/1','actor':'D','intent_id':identity,'status':'unknown','reason':'not_registered'}).encode()
  try:
   self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
  except OSError:pass
 def do_POST(self):
  events.append({'kind':'FORBIDDEN_POST','path':self.path});self.send_error(409)
def run(args,check=True):
 p=subprocess.run(adb+args,text=True,capture_output=True,timeout=15)
 commands.append({'argv':adb+args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 (root/'real-stop-commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
 if check and p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout

def wait(f,seconds=8):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:
   v=f()
   if v:return v
  except (ValueError,KeyError,RuntimeError):pass
  time.sleep(.04)
 raise RuntimeError('independent stop probe state timeout')
def state():return json.loads(run(['shell','run-as',package,'cat','files/resource-state.json']))
def current(s):return s['network']['client']['current']
def launch(command,extra=[]):run(['shell','am','start','-W','-n',package+'/org.wwl.networkdemo.ResourceActivity','--es','lab_command',command]+extra)
server=None
try:
 assert run(['shell','getprop','ro.kernel.qemu']).strip()=='1'
 routes=run(['reverse','--list'])
 for row in routes.splitlines():
  cols=row.split()
  if len(cols)>=3 and cols[-2]=='tcp:18751':previous=cols[-1]
 server=Server(('127.0.0.1',18765),Handler)
 material=Path('/private/tmp/wwl-next-175-final-env/resource-final-source/network-server/fixtures/generated')
 ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.minimum_version=ssl.TLSVersion.TLSv1_2
 ctx.load_cert_chain(material/'server.pem',material/'server-public-fixture.key');server.socket=ctx.wrap_socket(server.socket,server_side=True)
 threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True).start()
 run(['reverse','tcp:18751','tcp:18765']);restoring=True
 launch('queue',['--es','intent_id',identity,'--es','start_raw','810','--es','end_raw','840'])
 s=wait(lambda: (v if current(v).get('intent_id')==identity else None) if (v:=state()) else None)
 original=current(s);(root/'real-stop-before.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
 launch('schedule');wait(lambda:any(e['kind']=='job_scheduled' and identity in e['detail'] for e in state()['resources']['events']))
 # Explicitly bypasses constraints ONLY in this independent stop probe.
 run(['shell','cmd','jobscheduler','run','-f',package,'17503'])
 assert held.wait(4),'query never reached independent held GET'
 run(['shell','cmd','jobscheduler','timeout',package,'17503'])
 def stopped():
  s=state();p=current(s)
  return s if p['phase']=='unknown' and any(e['kind']=='job_stopped' and 'reason=3' in e['detail'] for e in s['resources']['events']) else None
 after=wait(stopped)
 p=current(after);rows=[w for w in after['resources']['work'] if w['intent_id']==identity]
 assert p['intent_id']==original['intent_id'] and p['fingerprint']==original['fingerprint'] and p['result'] is None
 assert len(rows)==1 and rows[0]['attempts']==1
 assert not any(e['kind']=='FORBIDDEN_POST' for e in events)
 (root/'real-stop-after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n')
 (root/'real-stop-result.json').write_text(json.dumps({'passed':True,'explicit_forced_run':True,'explicit_timeout_stop_reason':3,'not_charging_trigger':True,'authority_database_used':False,'attempts':1,'same_id_and_fp':True,'business_phase':'unknown','server_events':events},ensure_ascii=False,indent=2)+'\n')
 print('PASS: actual JobService onStop reason3; same local id/fp; attempt1 unknown; no POST/no authority.')
finally:
 run(['shell','cmd','jobscheduler','cancel',package,'17503'],False)
 run(['shell','am','force-stop',package],False)
 if restoring:
  run(['reverse','--remove','tcp:18751'],False)
  if previous:run(['reverse','tcp:18751',previous])
 if server:server.shutdown();server.server_close()
 (root/'real-stop-server-events.json').write_text(json.dumps(events,indent=2)+'\n')
