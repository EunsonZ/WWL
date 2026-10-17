#!/usr/bin/env python3
"""PUBLIC synthetic package only, explicit owned emulator, new outputs; never pm clear.
APK signing/build preparation is separate. Real permission UI, sensor injection,
JobScheduler/battery constraints, own-PID termination and same-id update evidence.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import shutil
import time
import xml.etree.ElementTree as ET

PACKAGE='org.wwl.networkdemo.resources'
COMPONENT=PACKAGE+'/org.wwl.networkdemo.ResourceActivity'
IDENTITY='resources-D-original-1'
NEXT='resources-D-next-1'
JOB='17503'

class Driver:
    def __init__(self,a):
        self.a=a;self.out=a.output;self.out.mkdir(parents=True,exist_ok=False)
        self.commands=[];self.checks=[]
        (self.out/'executed-driver.py').write_bytes(Path(__file__).read_bytes())
    def save(self,n,v): (self.out/(n+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
    def call(self,*args,check=True,binary=False):
        argv=[self.a.adb,'-s',self.a.serial,*map(str,args)]
        r=subprocess.run(argv,capture_output=True,timeout=30)
        self.commands.append(dict(argv=argv,returncode=r.returncode,stdout=None if binary else r.stdout.decode(errors='replace'),stderr=r.stderr.decode(errors='replace')));self.save('commands',self.commands)
        if check and r.returncode: raise RuntimeError(str(self.commands[-1]))
        return r.stdout if binary else r.stdout.decode(errors='replace').strip()
    def shell(self,*args,**kw):return self.call('shell',' '.join(shlex.quote(str(x)) for x in args),**kw)
    def require(self,n,v,detail=None):
        self.checks.append(dict(name=n,passed=bool(v),detail=detail));self.save('assertions',self.checks)
        if not v:raise AssertionError(n+': '+str(detail))
    def read(self,name):return json.loads(self.shell('run-as',PACKAGE,'cat','files/'+name+'.json'))
    def wait(self,fn,timeout=15):
        end=time.monotonic()+timeout;last=None
        while time.monotonic()<end:
            try:
                last=fn()
                if last:return last
            except (ValueError,RuntimeError,KeyError):pass
            time.sleep(.15)
        raise AssertionError('condition timeout; last='+str(last))
    def state(self):return self.read('resource-state')
    def ui(self):return self.read('network-ui')
    def pending(self,s):return s['network']['client']['current']
    def launch(self,command='snapshot',**extras):
        argv=['am','start','-W','-n',COMPONENT,'--es','lab_command',command]
        for k,v in extras.items():argv+=['--es',k,str(v)]
        return self.shell(*argv)
    def click(self,label=None,resource=None):
        # Actual UI traversal. Scroll only this foreground synthetic app/dialog.
        for _ in range(8):
            self.shell('uiautomator','dump','/sdcard/wwl175-resource-ui.xml')
            xml=self.shell('cat','/sdcard/wwl175-resource-ui.xml')
            root=ET.fromstring(xml)
            for n in root.iter('node'):
                if (label is not None and n.get('text')==label) or (resource is not None and n.get('resource-id')==resource):
                    a,b,c,d=map(int,re.findall(r'\d+',n.get('bounds','')))
                    self.shell('input','tap',(a+c)//2,(b+d)//2);return xml
            self.shell('input','swipe','540','1900','540','600','250')
        raise AssertionError('visible UI action absent '+str((label,resource)))
    def capture(self,name,with_screen=False):
        v={'state':self.state(),'ui':self.ui()};self.save(name,v)
        if with_screen:(self.out/(name+'.png')).write_bytes(self.call('exec-out','screencap','-p',binary=True))
        return v
    def authority(self):
        db=sqlite3.connect(self.a.authority_db.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
        try:return {t:[dict(x) for x in db.execute('SELECT * FROM '+t)] for t in ['bookings','intents','outbox']}
        finally:db.close()
    def stop_own(self):
        pid=self.shell('pidof',PACKAGE)
        self.require('single own app PID',pid.isdecimal(),pid)
        observed=self.shell('run-as',PACKAGE,'cat','/proc/'+pid+'/cmdline')
        self.require('exact package PID cmdline',observed.rstrip('\x00')==PACKAGE,repr(observed))
        self.shell('run-as',PACKAGE,'kill','-9',pid)
        self.wait(lambda:not self.shell('pidof',PACKAGE,check=False))
        return pid
    def export_db(self,stage):
        folder=self.out/stage;folder.mkdir()
        for n in ['client.db','resources.db']:(folder/n).write_bytes(self.call('exec-out','run-as',PACKAGE,'cat','databases/'+n,binary=True))
        result={}
        for n in ['client.db','resources.db']:
            db=sqlite3.connect((folder/n).resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
            tables=[x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            result[n]={'user_version':db.execute('PRAGMA user_version').fetchone()[0],'integrity':db.execute('PRAGMA integrity_check').fetchone()[0],
                       'tables':{t:[dict(x) for x in db.execute('SELECT * FROM '+t)] for t in tables},
                       'work_columns':[] if n=='client.db' else [x[1] for x in db.execute('PRAGMA table_info(work)')]}
            db.close()
        self.save(stage+'-readback',result);return result
    def run(self):
        if self.a.resume_from is not None:return self.resume()
        self.require('explicit emulator serial',self.a.serial.startswith('emulator-'))
        self.require('guest qemu',self.shell('getprop','ro.kernel.qemu')=='1')
        routes=self.call('reverse','--list')
        self.require('task route starts absent',not any('tcp:18751' in row for row in routes.splitlines()),routes)
        self.call('install','-r',self.a.apk_v1)
        self.launch()
        self.wait(lambda:self.state()['version_code']==1)
        self.require('fresh synthetic intents',not self.state()['network']['client']['intents'])
        self.require('fresh authority seeds',len(self.authority()['bookings'])==3 and not self.authority()['intents'])
        self.launch('queue',intent_id=IDENTITY,start_raw='690',end_raw='720')
        self.wait(lambda:self.pending(self.state()) is not None and self.pending(self.state())['intent_id']==IDENTITY)
        original_pending=self.pending(self.state());self.capture('01-v1-queued',True)
        self.launch('camera')
        self.click(resource='com.android.permissioncontroller:id/permission_deny_button')
        self.wait(lambda:self.ui()['resources_observation'].get('camera')=='denied_booking_unchanged')
        denied=self.capture('02-camera-denied',True)
        self.require('denial visible without business cancellation','已拒绝' in denied['ui']['resource_message'] and self.pending(denied['state'])['intent_id']==IDENTITY and self.pending(denied['state'])['phase']=='queued')
        self.launch('camera');self.click(label='继续请求')
        self.click(resource='com.android.permissioncontroller:id/permission_allow_foreground_only_button')
        self.wait(lambda:self.ui()['resources_observation'].get('camera')=='granted_click_to_open')
        self.launch('camera')
        self.wait(lambda:self.ui()['resources_observation'].get('camera')=='opened_then_closed')
        opened=self.capture('03-camera-opened-closed',True)
        self.require('camera open close visibly reported','设备已打开并关闭' in opened['ui']['resource_message'])
        self.launch('sensor_start')
        self.call('emu','sensor','set','acceleration','1:2:9.81')
        def sample():
            v=self.ui()['resources_observation'].get('acceleration_m_s2')
            return v if v and all(abs(a-b)<.01 for a,b in zip(v,[1,2,9.81])) else False
        self.wait(sample);sensor=self.capture('04-sensor-injected',True)
        self.require('sensor units visible','m/s²' in sensor['ui']['resource_message'])
        (self.out/'04-sensorservice.txt').write_text(self.shell('dumpsys','sensorservice'))
        self.shell('input','keyevent','KEYCODE_HOME')
        self.wait(lambda:self.ui()['resources_observation'].get('sensor')=='unregistered' and not self.ui()['foreground'])
        count=self.ui()['resources_observation']['sensor_samples']
        self.call('emu','sensor','set','acceleration','4:5:6');time.sleep(.5)
        self.require('no callbacks published after pause unregister',self.ui()['resources_observation']['sensor_samples']==count)
        (self.out/'04-paused-sensorservice.txt').write_text(self.shell('dumpsys','sensorservice'))
        self.launch();self.wait(lambda:self.ui()['foreground'])
        self.shell('dumpsys','battery','unplug');self.shell('dumpsys','battery','set','status','3')
        self.launch('schedule')
        self.wait(lambda:self.ui()['resources_observation'].get('schedule')=='registered')
        self.shell('cmd','jobscheduler','run','-s',PACKAGE,JOB,check=False)
        blocked_command=self.commands[-1]
        blocked=(blocked_command['stdout'] or '')+'\n'+blocked_command['stderr']
        self.save('05-job-blocked',{'run_output':blocked,'job_state':self.shell('cmd','jobscheduler','get-job-state',PACKAGE,JOB,check=False),'battery':self.shell('dumpsys','battery')})
        self.require('charging constraint actually prevents run',blocked_command['returncode']!=0 and ('not satisfied' in blocked.lower() or 'not currently' in blocked.lower() or 'functional constraints' in blocked.lower()),blocked)
        self.require('blocked means no logical background attempt',not self.state()['resources']['work'])
        self.shell('input','keyevent','KEYCODE_HOME');old=self.stop_own()
        self.require('system job retained after process death',JOB in self.shell('dumpsys','jobscheduler'))
        # Android network availability is true, but the specific localhost route is absent.
        self.shell('dumpsys','battery','set','ac','1');self.shell('dumpsys','battery','set','status','2')
        self.shell('cmd','jobscheduler','run','-s',PACKAGE,JOB,check=False)
        def first_failed():
            s=self.state();w=s['resources']['work']
            return s if w and w[0]['attempts']==1 and self.pending(s)['phase']=='unknown' else False
        s=self.wait(first_failed,40)
        self.require('JobService new process same durable id',str(s['network']['pid'])!=old and self.pending(s)['intent_id']==IDENTITY and self.pending(s)['fingerprint']==original_pending['fingerprint'])
        self.require('unreachable peer had no service write',len(self.authority()['bookings'])==3 and not self.authority()['intents'])
        self.capture('06-background-attempt1-unreachable')
        self.call('reverse','tcp:18751','tcp:18751')
        # Allow real backoff timing; -s requests only currently satisfied jobs, not -f.
        held=False;end=time.monotonic()+75
        while time.monotonic()<end:
            events=self.a.events.read_text() if self.a.events.exists() else ''
            if 'lab_query_held_before_read' in events:held=True;break
            self.shell('cmd','jobscheduler','run','-s',PACKAGE,JOB,check=False);time.sleep(.2)
        self.require('second logical attempt reached explicit server hold',held)
        self.shell('dumpsys','battery','unplug');self.shell('dumpsys','battery','set','status','3')
        self.wait(lambda:any(x['kind']=='job_stopped' for x in self.state()['resources']['events']),20)
        stopped=self.capture('07-real-job-stop')
        self.require('stop kept same intent unknown',self.pending(stopped['state'])['intent_id']==IDENTITY and self.pending(stopped['state'])['phase']=='unknown')
        self.require('no reserve after cancelled held query',len(self.authority()['bookings'])==3)
        self.shell('dumpsys','battery','set','ac','1');self.shell('dumpsys','battery','set','status','2')
        end=time.monotonic()+100;accepted=None
        while time.monotonic()<end:
            try:
                s=self.state()
                if self.pending(s)['phase']=='accepted':accepted=s;break
            except (RuntimeError,ValueError):pass
            self.shell('cmd','jobscheduler','run','-s',PACKAGE,JOB,check=False);time.sleep(.3)
        self.require('third bounded background attempt recovered original',accepted is not None)
        outcome=self.pending(accepted)['result']
        self.require('background logical budget exactly three',accepted['resources']['work'][0]['attempts']==3)
        self.require('one authority effect',len(self.authority()['bookings'])==4 and len(self.authority()['outbox'])==1 and len(self.authority()['intents'])==1)
        self.launch();self.wait(lambda:self.pending(self.state())['phase']=='accepted');self.capture('08-background-original-accepted',True)
        self.updates(original_pending,outcome)

    def resume(self):
        prefix=self.a.resume_from.resolve()
        if not prefix.is_dir() or prefix==self.out.resolve() or prefix in self.out.resolve().parents:
            raise ValueError('resume prefix must be a different preserved evidence directory')
        shutil.copytree(prefix,self.out/'prefix')
        original=json.loads((prefix/'01-v1-queued.json').read_text())
        original_pending=original['state']['network']['client']['current']
        current=self.state();p=self.pending(current)
        self.require('resume explicit owned emulator',self.a.serial.startswith('emulator-') and self.shell('getprop','ro.kernel.qemu')=='1')
        self.require('resume original immutable identity',p['actor']=='D' and p['intent_id']==IDENTITY and (p['start'],p['end'],p['fingerprint'])==(690,720,original_pending['fingerprint']) and p['result'] is None)
        self.require('resume exact observed second-attempt cut',current['version_code']==1 and current['resources']['schema_version']==1 and len(current['resources']['work'])==1 and current['resources']['work'][0]['attempts']==2 and p['phase']=='unknown')
        self.require('resume no service decision',len(self.authority()['bookings'])==3 and not self.authority()['intents'] and not self.authority()['outbox'])
        self.require('resume route still absent',not any('tcp:18751' in x for x in self.call('reverse','--list').splitlines()))
        self.save('resume-provenance',{'prefix':str(prefix),'input_cut':'two real automatic ConnectException attempts after old driver finally reset battery; no counter rollback', 'current':current,'original_pending':original_pending})
        self.shell('dumpsys','battery','unplug');self.shell('dumpsys','battery','set','status','3')
        # Re-check the original failed assertion from its RAW argv/exit/stderr, not rerun it as a new result.
        commands=json.loads((prefix/'commands.json').read_text())
        blocked=[c for c in commands if c['argv'][-1].startswith('cmd jobscheduler run -s ')][0]
        merged=(blocked.get('stdout') or '')+'\n'+blocked.get('stderr','')
        self.require('old charging rejection identified from actual exit/stderr',blocked['returncode']!=0 and 'functional constraints' in merged.lower(),blocked)
        self.shell('input','keyevent','KEYCODE_HOME');old=self.stop_own()
        self.call('reverse','tcp:18751','tcp:18751')
        self.shell('dumpsys','battery','set','ac','1');self.shell('dumpsys','battery','set','status','2')
        end=time.monotonic()+75;held=False
        while time.monotonic()<end:
            if self.a.events.exists() and 'lab_query_held_before_read' in self.a.events.read_text():held=True;break
            self.shell('cmd','jobscheduler','run','-s',PACKAGE,JOB,check=False);time.sleep(.2)
        self.require('third background query reached explicit hold',held)
        self.shell('dumpsys','battery','unplug');self.shell('dumpsys','battery','set','status','3')
        self.wait(lambda:any(e['kind']=='job_stopped' for e in self.state()['resources']['events']),20)
        stopped=self.capture('07-third-background-stopped')
        self.require('new process same original id on third background attempt',str(stopped['state']['network']['pid'])!=old and self.pending(stopped['state'])['intent_id']==IDENTITY)
        self.require('three background attempts exhausted but not rejected',stopped['state']['resources']['work'][0]['attempts']==3 and self.pending(stopped['state'])['phase']=='unknown' and self.pending(stopped['state'])['result'] is None)
        self.require('stopped query did not reserve',len(self.authority()['bookings'])==3 and not self.authority()['intents'])
        self.launch('schedule')
        self.wait(lambda:self.ui()['resources_observation'].get('schedule')=='refused')
        self.require('budget refuses a new background schedule',self.state()['resources']['work'][0]['attempts']==3)
        # EXPLICIT USER recovery is a different, documented cost domain. Same durable id/fp.
        self.launch('recover')
        accepted=self.wait(lambda:self.state() if self.pending(self.state())['phase']=='accepted' else False,20)
        outcome=self.pending(accepted)['result']
        self.require('manual recovery retained original identity after budget',outcome['intent_id']==IDENTITY and outcome['fingerprint']==original_pending['fingerprint'] and accepted['resources']['work'][0]['attempts']==3)
        self.require('one effect after explicit user recovery',len(self.authority()['bookings'])==4 and len(self.authority()['intents'])==1 and len(self.authority()['outbox'])==1)
        self.capture('08-manual-original-recovery-after-background-budget',True)
        self.updates(original_pending,outcome)

    def updates(self,original_pending,outcome):
        # Permission revocation may kill the process, but cannot cancel the booking.
        self.shell('pm','revoke',PACKAGE,'android.permission.CAMERA');self.launch()
        self.wait(lambda:self.pending(self.state())['result']==outcome)
        self.require('permission revoke preserves accepted',self.pending(self.state())['result']==outcome)
        self.launch('queue',intent_id=NEXT,start_raw='810',end_raw='840')
        self.wait(lambda:self.pending(self.state())['intent_id']==NEXT)
        self.stop_own();v1=self.export_db('09-v1-before-update')
        self.require('v1 resource schema persisted',v1['resources.db']['user_version']==1 and 'last_http' not in v1['resources.db']['work_columns'])
        self.call('install','-r',self.a.apk_bad_v2);self.launch()
        self.wait(lambda:self.ui()['resources_observation'].get('resource_storage')=='unavailable')
        self.save('10-bad-v2-ui',self.ui());(self.out/'10-bad-v2.png').write_bytes(self.call('exec-out','screencap','-p',binary=True))
        self.stop_own();bad=self.export_db('10-bad-v2-rollback')
        self.require('failed migration kept user_version one and no column',bad['resources.db']['user_version']==1 and 'last_http' not in bad['resources.db']['work_columns'])
        self.require('failed migration kept exact original budget rows',bad['resources.db']['tables']['work']==v1['resources.db']['tables']['work'])
        self.require('failed migration kept business intents',bad['client.db']['tables']['intents']==v1['client.db']['tables']['intents'])
        self.call('install','-r',self.a.apk_v2);self.launch()
        self.wait(lambda:self.state()['version_code']==2 and self.state()['resources']['schema_version']==2)
        self.stop_own();good=self.export_db('11-good-v2')
        self.require('successful migration retained identity and attempts',good['resources.db']['tables']['work'][0]['attempts']==3 and good['resources.db']['tables']['work'][0]['fp']==original_pending['fingerprint'] and good['resources.db']['tables']['work'][0]['last_http']=='none')
        self.require('successful migration preserved business rows',good['client.db']['tables']['intents']==v1['client.db']['tables']['intents'])
        self.call('install','-r',self.a.apk_other_v3,check=False)
        wrong=self.commands[-1];self.save('12-wrong-signature',wrong)
        self.require('different signer update rejected','INSTALL_FAILED_UPDATE_INCOMPATIBLE' in wrong['stdout']+wrong['stderr'])
        self.call('install','-r',self.a.apk_v1,check=False)
        down=self.commands[-1];self.save('13-downgrade',down)
        self.require('lower version update rejected','INSTALL_FAILED_VERSION_DOWNGRADE' in down['stdout']+down['stderr'])
        self.call('install','-r',self.a.apk_release_v3)
        self.shell('am','start','-W','-n',COMPONENT)
        self.click(label='导出合成实验状态')
        external='/sdcard/Android/data/'+PACKAGE+'/files/synthetic-state.json'
        final=self.wait(lambda:json.loads(self.shell('cat',external)))
        self.save('14-release-v3-explicit-export',final)
        self.require('release nondebuggable same-id current draft preserved',final['version_code']==3 and not final['debuggable'] and self.pending(final)['intent_id']==NEXT and self.pending(final)['phase']=='queued')
        byid={x['intent_id']:x for x in final['network']['client']['intents']}
        self.require('release preserved exact original accepted',byid[IDENTITY]['result']==outcome)
        self.require('release preserved migrated budget',final['resources']['schema_version']==2 and final['resources']['work'][0]['attempts']==3)
        self.shell('run-as',PACKAGE,'id',check=False)
        self.require('release run-as denied','not debuggable' in self.commands[-1]['stdout']+self.commands[-1]['stderr'])
        self.click(label='获取服务预约投影');time.sleep(3)
        self.click(label='导出合成实验状态');time.sleep(.4)
        rejected_tls=json.loads(self.shell('cat',external));self.save('15-release-no-debug-ca',rejected_tls)
        self.require('release does not silently trust debug CA','SSL' in rejected_tls['network']['transport_hint'])
        self.require('release TLS failure does not erase accepted',next(x for x in rejected_tls['network']['client']['intents'] if x['intent_id']==IDENTITY)['result']==outcome)
        (self.out/'14-release-v3.png').write_bytes(self.call('exec-out','screencap','-p',binary=True))
        self.save('final-authority',self.authority())
        self.save('results',{'passed':len(self.checks),'original_result':outcome,'original_id':IDENTITY,'next_id':NEXT,'participants':0,'physical_sensor_measurement':False,'assertions':self.checks})

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb',required=True);p.add_argument('--serial',required=True)
    for x in ['apk-v1','apk-bad-v2','apk-v2','apk-other-v3','apk-release-v3']:p.add_argument('--'+x,required=True)
    p.add_argument('--resume-from',type=Path)
    p.add_argument('--authority-db',type=Path,required=True);p.add_argument('--events',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();d=Driver(a)
    try:d.run()
    finally:
        # Release only task-owned battery simulation; never clear/uninstall an app.
        d.shell('dumpsys','battery','reset',check=False)
        d.save('commands',d.commands);d.save('assertions',d.checks)
if __name__=='__main__':main()
