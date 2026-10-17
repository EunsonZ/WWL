#!/usr/bin/env python3
"""Two PUBLIC synthetic Android UIDs + an already-running loopback TLS authority.
No install/clear/server restart/device discovery. Only known reverse mapping18751.
Outputs are new; stop only exact named app PIDs when exporting their SQLite files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sqlite3
import subprocess
import time

IDENTITY='dual-shared-1'
PACKAGES={a:'org.wwl.networkdemo.'+a.lower() for a in 'DE'}
ACTIVITY='org.wwl.networkdemo.NetworkActivity'

class Driver:
    def __init__(self,args):
        self.a=args;self.out=args.output;self.out.mkdir(parents=True,exist_ok=False)
        self.commands=[];self.checks=[]
        (self.out/'executed-driver.py').write_bytes(Path(__file__).read_bytes())
    def save(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    def adb(self,*parts,check=True,binary=False):
        argv=[self.a.adb,'-s',self.a.serial,*parts]
        r=subprocess.run(argv,capture_output=True,timeout=20)
        self.commands.append({'argv':argv,'returncode':r.returncode,'stdout':None if binary else r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')})
        self.save('commands',self.commands)
        if check and r.returncode:raise RuntimeError(str(self.commands[-1]))
        return r.stdout if binary else r.stdout.decode().strip()
    def shell(self,*parts,**kw):
        # adb shell concatenates argv; explicitly quote each remote argument.
        return self.adb('shell',' '.join(shlex.quote(str(p)) for p in parts),**kw)
    def assert_(self,name,value,detail=None):
        self.checks.append({'name':name,'passed':bool(value),'detail':detail});self.save('assertions',self.checks)
        if not value:raise AssertionError(name+': '+str(detail))
    def state(self,a):
        return json.loads(self.shell('run-as',PACKAGES[a],'cat','files/network-state.json'))
    def wait(self,a,predicate,timeout=10):
        end=time.monotonic()+timeout;last=None
        while time.monotonic()<end:
            try:
                last=self.state(a)
                if predicate(last):return last
            except (ValueError,RuntimeError):pass
            time.sleep(.15)
        raise AssertionError('state timeout '+a+': '+str(last))
    def command(self,a,command,**extras):
        argv=['am','start','-W','-n',PACKAGES[a]+'/'+ACTIVITY,'--es','lab_command',command]
        for k,v in extras.items():argv+=['--es',k,str(v)]
        self.shell(*argv)
    def capture(self,name):
        value={a:self.state(a) for a in 'DE'};value['authority']=self.authority();self.save(name,value);return value
    def authority(self):
        db=sqlite3.connect(self.a.authority_db.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
        try:return {t:[dict(x) for x in db.execute('SELECT * FROM '+t+' ORDER BY '+('id' if t=='bookings' else 'actor,intent_id' if t=='intents' else 'booking_id'))] for t in ['bookings','intents','outbox']}
        finally:db.close()
    def current(self,s):return s['client']['current']
    def screenshot(self,a,name):
        # Bring same activity foreground without replaying a business command.
        self.command(a,'snapshot');time.sleep(.8)
        (self.out/(name+'.png')).write_bytes(self.adb('exec-out','screencap','-p',binary=True))
    def terminate(self,a):
        pkg=PACKAGES[a];pid=self.shell('pidof',pkg)
        self.assert_('exact single PID '+a,pid.isdecimal(),pid)
        raw=self.shell('run-as',pkg,'cat','/proc/'+pid+'/cmdline')
        self.assert_('PID cmdline belongs to exact app '+a,raw.rstrip('\x00')==pkg,repr(raw))
        self.shell('run-as',pkg,'kill','-9',pid)
        for _ in range(30):
            if not self.shell('pidof',pkg,check=False):break
            time.sleep(.1)
        self.assert_('old PID gone '+a,not self.shell('pidof',pkg,check=False))
        return pid
    def run(self):
        self.assert_('explicit synthetic serial',self.a.serial.startswith('emulator-'))
        self.assert_('emulator guest',self.shell('getprop','ro.kernel.qemu')=='1')
        for a in 'DE':
            self.command(a,'snapshot')
            s=self.wait(a,lambda s:s['actor']==a)
            self.assert_('fresh private intent store '+a,len(s['client']['intents'])==0)
        self.assert_('fresh authority seeds',len(self.authority()['bookings'])==3 and not self.authority()['intents'])
        self.adb('reverse','tcp:18751','tcp:18751')
        for a in 'DE':
            self.command(a,'fetch')
            self.wait(a,lambda s:s['projection'] is not None and len(s['projection']['snapshot']['bookings'])==3)
        initial=self.capture('01-two-cached-seeds')
        self.assert_('two independent UIDs',initial['D']['uid']!=initial['E']['uid'],[initial[x]['uid'] for x in 'DE'])
        self.assert_('same cached empty interval',initial['D']['projection']['snapshot']==initial['E']['projection']['snapshot'])
        self.adb('reverse','--remove','tcp:18751')
        try:
            for a in 'DE':
                self.command(a,'queue',intent_id=IDENTITY,start_raw='690',end_raw='720')
                self.wait(a,lambda s:self.current(s) is not None and self.current(s)['phase']=='queued')
                self.command(a,'send')
                self.wait(a,lambda s:self.current(s)['phase']=='unknown')
            offline=self.capture('02-real-route-removed')
            for a in 'DE':
                p=self.current(offline[a]);self.assert_('offline original id '+a,p['intent_id']==IDENTITY and p['result'] is None)
                self.assert_('cached 3 retained '+a,len(offline[a]['projection']['snapshot']['bookings'])==3)
            self.assert_('real IO failure no authority effect',len(offline['authority']['bookings'])==3 and not offline['authority']['intents'])
        finally:self.adb('reverse','tcp:18751','tcp:18751')
        self.command('D','drop')
        self.wait('D',lambda s:self.current(s)['phase']=='unknown' and len(self.authority()['bookings'])==4)
        dropped=self.capture('03-commit-then-wire-close')
        original=json.loads(dropped['authority']['intents'][0]['outcome'])
        self.assert_('D committed but client has no result',original['status']=='accepted' and self.current(dropped['D'])['result'] is None)
        self.command('E','send')
        self.wait('E',lambda s:self.current(s)['phase']=='rejected')
        conflict=self.capture('04-E-authority-rejected')
        self.assert_('E same text id separate actor key',self.current(conflict['E'])['intent_id']==IDENTITY and self.current(conflict['E'])['result']['reason']=='conflict_with_buffer')
        self.assert_('one accepted capacity and event',len(conflict['authority']['bookings'])==4 and len(conflict['authority']['intents'])==2 and len(conflict['authority']['outbox'])==1)
        self.screenshot('E','04-E-rejected')
        for credential,code in [('invalid',401),('other',403)]:
            self.command('D','credential_'+credential)
            self.wait('D',lambda s:s['credential_mode']==credential)
            self.command('D','send')
            s=self.wait('D',lambda s:'HTTP '+str(code) in s['transport_hint'])
            self.assert_('HTTP '+str(code)+' not business final',self.current(s)['phase']=='unknown' and self.current(s)['result'] is None)
            self.save('05-auth-'+str(code),s)
        old=self.terminate('D')
        self.command('D','snapshot')
        restarted=self.wait('D',lambda s:str(s['pid'])!=old)
        self.assert_('new process same id/fp unknown',self.current(restarted)['intent_id']==IDENTITY and self.current(restarted)['fingerprint']==original['fingerprint'] and self.current(restarted)['phase']=='unknown')
        self.assert_('credential mode separately persisted',restarted['credential_mode']=='other')
        self.save('06-new-process-unknown',restarted)
        self.command('D','credential_self');self.wait('D',lambda s:s['credential_mode']=='self')
        self.command('D','recover')
        recovered=self.wait('D',lambda s:self.current(s)['phase']=='accepted')
        self.assert_('recovered ORIGINAL complete accepted',self.current(recovered)['result']==original)
        self.command('D','send');time.sleep(.4)
        self.assert_('same id replay ORIGINAL complete accepted',self.current(self.state('D'))['result']==original)
        self.command('E','query');time.sleep(.4)
        self.assert_('E query cannot read D accepted',self.current(self.state('E'))['phase']=='rejected')
        for a in 'DE':
            self.command(a,'fetch');self.wait(a,lambda s:len(s['projection']['snapshot']['bookings'])==4)
        final=self.capture('07-restored-original-results')
        self.assert_('no new booking from recovery',len(final['authority']['bookings'])==4 and len(final['authority']['outbox'])==1)
        self.screenshot('D','07-D-original-accepted')
        self.command('D','delay')
        self.wait('D',lambda s:any(x['kind']=='local_reply_held' for x in s['client']['trace']))
        self.command('D','queue',intent_id='dual-next-D',start_raw='810',end_raw='840')
        self.wait('D',lambda s:self.current(s)['intent_id']=='dual-next-D')
        time.sleep(3.5)
        newer=self.state('D')
        rows={p['intent_id']:p for p in newer['client']['intents']}
        self.assert_('late response persisted ORIGINAL row',rows[IDENTITY]['result']==original)
        self.assert_('late response does not replace new UI',self.current(newer)['intent_id']=='dual-next-D' and self.current(newer)['phase']=='queued')
        self.assert_('publication guard actually rejected old callback',any(x['kind']=='ui_ignored' and 'reply:' in x['detail'] for x in newer['client']['trace']))
        self.capture('08-late-response-new-intent');self.screenshot('D','08-D-new-queued')
        for a in 'DE':
            self.terminate(a)
            (self.out/(a+'-client.db')).write_bytes(self.adb('exec-out','run-as',PACKAGES[a],'cat','databases/client.db',binary=True))
        self.save('results',{'passed':len(self.checks),'participants':0,'two_physical_devices':False,'transport':'native HTTPS over adb reverse; remove route is not airplane mode',
            'old_D_pid':old,'new_D_pid':restarted['pid'],'original_D_result':original,'assertions':self.checks})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb',required=True);p.add_argument('--serial',required=True)
    p.add_argument('--authority-db',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();d=Driver(args)
    try:d.run()
    finally:d.save('commands',d.commands);d.save('assertions',d.checks)
if __name__=='__main__':main()
