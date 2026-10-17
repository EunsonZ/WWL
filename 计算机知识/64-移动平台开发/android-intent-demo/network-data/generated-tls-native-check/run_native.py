from pathlib import Path
import os,subprocess,json,zipfile,hashlib,signal,time,socket
r=Path(__file__).resolve().parent;p=r/'project';meta=json.loads((r/'host-fixture.json').read_text());env=os.environ.copy();env.update({'ADB_SERVER_SOCKET':'tcp:127.0.0.1:15037','ANDROID_ADB_SERVER_PORT':'15037'});adb='/private/tmp/wwl-next-175-env/sdk/platform-tools/adb';base=[adb,'-P15037','-s','emulator-5580'];rows=[]
def run(cmd,label):
 q=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=120);(r/(label+'.stdout.txt')).write_text(q.stdout);(r/(label+'.stderr.txt')).write_text(q.stderr);rows.append({'argv':cmd,'returncode':q.returncode,'stdout':label+'.stdout.txt','stderr':label+'.stderr.txt'});(r/'native-commands.json').write_text(json.dumps(rows,indent=2));assert q.returncode==0,label;return q.stdout
app=p/'networkApp/build/outputs/apk/d/debug/networkApp-d-debug.apk';test=p/'networkApp/build/outputs/apk/androidTest/d/debug/networkApp-d-debug-androidTest.apk';ca=p/'network-server/fixtures/generated/ca.pem';sha=hashlib.sha256(ca.read_bytes()).hexdigest();assert sha=='a314e642a29e770d8c965f3f455e0fd8d22f81d2d4cbfff7cd2171376ea93433'
with zipfile.ZipFile(app) as z:
 raw=z.read('res/raw/wwl_public_ca.pem');assert raw==ca.read_bytes();assert not any(n.endswith('.key') for n in z.namelist())
(r/'apk-identity.json').write_text(json.dumps({'package':'org.wwl.networkdemo.fixturecheck.d','apk_sha256':hashlib.sha256(app.read_bytes()).hexdigest(),'test_apk_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),'trusted_CA_sha256':sha,'raw_CA_same_bytes':True,'no_key_entries':True,'instrumentation_sha256':hashlib.sha256((p/'networkApp/src/androidTest/java/org/wwl/networkdemo/GeneratedTlsContractTest.kt').read_bytes()).hexdigest()},indent=2))
run(base+['install','-r',str(app)],'install-app');run(base+['install','-r',str(test)],'install-tests');before=run(base+['reverse','--list'],'reverse-before');assert 'tcp:18751' not in before
methods=['generatedCaTrustedByActualTransport','sameCaWrongHostnameRejected','differentCaWithCorrectNameRejected'];results={}
try:
 for server,method in zip(meta['servers'],methods):
  run(base+['reverse','tcp:18751','tcp:'+str(server['port'])],'reverse-'+server['name']);cmd=base+['shell','am','instrument','-w','-e','class','org.wwl.networkdemo.GeneratedTlsContractTest#'+method,'org.wwl.networkdemo.fixturecheck.d.test/androidx.test.runner.AndroidJUnitRunner'];text=run(['python3','/private/tmp/wwl-next-context/run_local.py','--timeout','180','--',*cmd],'test-'+server['name']);assert 'OK (1 test)' in text and 'FAILURES' not in text,(method,text);results[method]='PASS'
finally:
 run(base+['reverse','--remove','tcp:18751'],'remove-own-reverse')
 shutdown=[]
 for server in meta['servers']:
  cmd=subprocess.check_output(['ps','-p',str(server['pid']),'-o','command='],text=True);assert str(p/'network-server/http_authority.py') in cmd and str(r/('server-'+server['name'])/'authority.db') in cmd;os.kill(server['pid'],signal.SIGINT)
  for _ in range(50):
   q=subprocess.run(['ps','-p',str(server['pid']),'-o','command='],capture_output=True,text=True)
   if not q.stdout.strip():break
   time.sleep(.1)
  else:raise RuntimeError('server not stopped')
  s=socket.socket();s.settimeout(1);code=s.connect_ex(('127.0.0.1',server['port']));s.close();assert code!=0;shutdown.append({'name':server['name'],'pid':server['pid'],'observed_cmdline':cmd.strip(),'signal':'SIGINT','process_absent':True,'connect_ex_after':code})
 (r/'shutdown.json').write_text(json.dumps(shutdown,indent=2))
(r/'results.json').write_text(json.dumps({'passed':len(results),'methods':results,'scope':'same frozen generated CA actual Android HttpsTransport in isolated fixturecheck.d only; no old35/r-resource replay','reverse_before':before,'reverse_final':run(base+['reverse','--list'],'reverse-after')},indent=2));print('PASS three exact generated-CA native TLS tests; own servers/reverse stopped')
