"""Own only this local Redis process; no global stop or existing instances."""
import json,os,signal,socket,subprocess,time
from pathlib import Path
from resp import Client
class Server:
    def __init__(self,root,output):
        self.root=Path(root);self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True);self.p=None;self.log=None;self.round=0
        self.binary=Path(os.environ.get('REDIS_SERVER',str(self.root/'redis-8.10.2/src/redis-server'))).resolve()
    def start(self):
        self.round+=1
        s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',16379));s.close()
        cmd=[str(self.binary),str(self.root/'redis.conf'),'--dir',str(self.output)]
        self.log=(self.output/f'server-{self.round}.log').open('w');self.p=subprocess.Popen(cmd,cwd=self.output,stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True)
        (self.output/f'launch-{self.round}.json').write_text(json.dumps({'argv':cmd,'owned_pid':self.p.pid},indent=2));start=time.monotonic()
        while time.monotonic()-start<15:
            if self.p.poll() is not None:raise RuntimeError('local Redis exited '+str(self.p.returncode))
            try:
                c=Client('127.0.0.1',16379,name='readiness',log=self.output/'readiness.jsonl');r=c.execute('PING');c.close()
                if r=={'type':'simple','value':'PONG'}:return
            except OSError:time.sleep(.03)
        raise RuntimeError('Redis startup exceeded15s')
    def stop(self):
        if self.p is None:return
        if self.p.poll() is None:
            try:
                c=Client('127.0.0.1',16379,name='shutdown',log=self.output/'shutdown.jsonl');c.execute('SHUTDOWN','NOSAVE');c.close()
            except OSError:pass
        try:self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(self.p.pid,signal.SIGTERM)
            try:self.p.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(self.p.pid,signal.SIGKILL);self.p.wait()
        (self.output/f'exit-{self.round}.json').write_text(json.dumps({'owned_pid':self.p.pid,'returncode':self.p.returncode}));self.log.close();self.p=None
