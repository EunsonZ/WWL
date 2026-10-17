"""Freeze final server cut and stop only the exact recorded lab server/reverse route."""
from pathlib import Path
import os,subprocess,signal,time,json,shutil,socket,hashlib
r=Path(__file__).resolve().parent;d=r/'delivery';m=json.loads((r/'network-runtime/owned-server.json').read_text());pid=m['pid'];cmd=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
expected=m['argv'];assert expected[2] in cmd and expected[6] in cmd and '--port 18751' in cmd,(pid,cmd)
# Review window must be explicitly returned before this script is called.
f=r/'network-runtime/server-events.jsonl';dest=d/'final-server-events.jsonl'
if dest.exists() or dest.is_symlink():raise FileExistsError('final cut already exists')
shutil.copy2(f,dest)
env=os.environ.copy();env.update({'ADB_SERVER_SOCKET':'tcp:127.0.0.1:15037','ANDROID_ADB_SERVER_PORT':'15037'});adb='/private/tmp/wwl-next-175-env/sdk/platform-tools/adb';base=[adb,'-P15037','-s','emulator-5580'];before=subprocess.check_output(base+['reverse','--list'],env=env,text=True);matches=[line for line in before.splitlines() if line.split()[-2:]==['tcp:18751','tcp:18751']]
if matches:subprocess.run(base+['reverse','--remove','tcp:18751'],env=env,check=True,capture_output=True)
else:raise RuntimeError('expected own route absent/different; do not remove another mapping: '+before)
os.kill(pid,signal.SIGINT)
for _ in range(60):
 p=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
 if not p.stdout.strip():break
 time.sleep(.1)
else:raise RuntimeError('own server did not exit after SIGINT; no forced kill')
after=subprocess.check_output(base+['reverse','--list'],env=env,text=True)
s=socket.socket();s.settimeout(1);code=s.connect_ex(('127.0.0.1',18751));s.close();assert code!=0
receipt={'server_pid':pid,'exact_observed_cmdline':cmd,'signal':'SIGINT','server_process_absent':True,'port18751_connect_ex_after':code,'reverse_before':before,'reverse_after':after,'events_final_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'events_final_lines':len(dest.read_text().splitlines()),'retained':'own emulator32285/adb33509, SDK/AVD disk/raw; user5037/devices untouched'};(d/'shutdown.json').write_text(json.dumps(receipt,indent=2));print('STOPPED exact owned server',pid,'and own route18751; emulator/adb retained')
