from pathlib import Path
import os,subprocess,json,socket,time
r=Path(__file__).resolve().parent;o=r/'android-runtime';m=json.loads((o/'owned-processes.json').read_text());env=os.environ.copy();env.update(m['environment']);adb=str(r/'sdk/platform-tools/adb');cmd=[adb,'-L','tcp:localhost:15037','--one-device','WWL175_NO_PHYSICAL_DEVICE','server','nodaemon'];f=(o/'adb-server-fixed.log').open('w');p=subprocess.Popen(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);m['initial_failed_adb_pid']=m['adb_pid'];m['adb_pid']=p.pid;m['adb_argv']=cmd;(o/'owned-processes.json').write_text(json.dumps(m,indent=2));time.sleep(.5)
if p.poll() is not None:raise RuntimeError('explicit dedicated adb failed before any client query')
# Register only our own known emulator, without scanning local ports or USB devices.
s=socket.create_connection(('127.0.0.1',15037),timeout=5);v=b'host:emulator:5581';s.sendall(f'{len(v):04x}'.encode()+v);answer=s.recv(4096);s.close();(o/'explicit-owned-emulator-registration.txt').write_text(repr(answer));start=time.monotonic();rows=[]
for i in range(120):
 q=subprocess.run([adb,'-P','15037','-s','emulator-5580','shell','getprop','sys.boot_completed'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=8);rows.append({'elapsed_s':time.monotonic()-start,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr})
 if q.returncode==0 and q.stdout.strip()=='1':break
 time.sleep(1)
else:raise RuntimeError('boot not complete')
(o/'boot-probes.json').write_text(json.dumps(rows,indent=2));(o/'boot-success.json').write_text(json.dumps({'boot_completed':'1','serial':'emulator-5580','after_registration_s':time.monotonic()-start},indent=2));print('BOOT_COMPLETE',rows[-1],flush=True)
