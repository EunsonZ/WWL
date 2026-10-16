from pathlib import Path
import os,subprocess,json,socket,time
root=Path(os.environ['WWL175_ENV_ROOT']).resolve();env=os.environ.copy()
env.update({'JAVA_HOME':'/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home','ANDROID_SDK_ROOT':str(root/'sdk'),'ANDROID_HOME':str(root/'sdk'),'ANDROID_USER_HOME':str(root/'android-user'),'ANDROID_AVD_HOME':str(root/'avd'),'ANDROID_EMULATOR_HOME':str(root/'emulator-user'),'ANDROID_ADB_SERVER_PORT':'15037','ADB_SERVER_SOCKET':'tcp:127.0.0.1:15037','ADB_LOCAL_TRANSPORT_MAX_PORT':'0','ADB_MDNS_AUTO_CONNECT':'0','ADB_VENDOR_KEYS':str(root/'android-user/adbkey')})
(root/'emulator-user').mkdir(exist_ok=True);out=root/'android-runtime';out.mkdir(exist_ok=True)
for port in [15037,5580,5581,18554]:
 s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',port));s.close()
adb=str(root/'sdk/platform-tools/adb');emulator=str(root/'sdk/emulator/emulator')
if not (root/'android-user/adbkey').exists():subprocess.run([adb,'keygen',str(root/'android-user/adbkey')],env=env,check=True,stdout=subprocess.DEVNULL)
afile=(out/'adb-server.log').open('w');acmd=[adb,'-L','tcp:localhost:15037','--one-device','WWL175_NO_PHYSICAL_DEVICE','server','nodaemon'];a=subprocess.Popen(acmd,env=env,stdout=afile,stderr=subprocess.STDOUT,start_new_session=True)
time.sleep(.3)
if a.poll() is not None:raise RuntimeError('dedicated adb failed before emulator launch')
cmd=[emulator,'-avd','WWL175_API35_20261017','-no-window','-no-audio','-no-snapshot','-memory','2048','-cores','2','-gpu','swiftshader','-port','5580','-grpc','18554','-no-boot-anim','-no-metrics'];efile=(out/'emulator.log').open('w');e=subprocess.Popen(cmd,env=env,stdout=efile,stderr=subprocess.STDOUT,start_new_session=True)
meta={'adb_pid':a.pid,'emulator_pid':e.pid,'adb_argv':acmd,'emulator_argv':cmd,'environment':{k:env[k] for k in ['ANDROID_SDK_ROOT','ANDROID_USER_HOME','ANDROID_AVD_HOME','ANDROID_EMULATOR_HOME','ANDROID_ADB_SERVER_PORT','ADB_SERVER_SOCKET','ADB_LOCAL_TRANSPORT_MAX_PORT','ADB_MDNS_AUTO_CONNECT','ADB_VENDOR_KEYS']}};(out/'owned-processes.json').write_text(json.dumps(meta,indent=2));print('owned processes',a.pid,e.pid,flush=True)
start=time.monotonic();records=[]
for i in range(160):
 if a.poll() is not None or e.poll() is not None:raise RuntimeError(f'owned process exited adb={a.poll()} emulator={e.poll()}')
 try:
  with socket.create_connection(('127.0.0.1',15037),timeout=2) as registration:
   service=b'host:emulator:5581';registration.sendall(f'{len(service):04x}'.encode()+service);answer=registration.recv(4096)
  (out/'explicit-owned-emulator-registration.txt').write_text(repr(answer))
 except OSError:pass
 p=subprocess.run([adb,'-P','15037','-s','emulator-5580','shell','getprop','sys.boot_completed'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=6);records.append({'elapsed_s':time.monotonic()-start,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 if p.returncode==0 and p.stdout.strip()=='1':
  devices=subprocess.check_output([adb,'-P','15037','devices','-l'],env=env,text=True);(out/'devices.txt').write_text(devices);assert all(not l or l.startswith('List of devices') or l.startswith('emulator-5580') for l in devices.splitlines());print('BOOT_COMPLETE elapsed',time.monotonic()-start,devices,flush=True);break
 time.sleep(1)
else:raise RuntimeError('owned emulator did not boot in160 polls')
(out/'boot-probes.json').write_text(json.dumps(records,indent=2));(out/'boot-success.json').write_text(json.dumps({'elapsed_s':time.monotonic()-start,'serial':'emulator-5580','boot_completed':'1'},indent=2))
