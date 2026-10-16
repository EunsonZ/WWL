"""Small RESP2 recorder using only Python's standard library."""
import base64,json,socket,time
from pathlib import Path

class Client:
    def __init__(self,host,port,*,name,log):
        self.name=name;self.log=Path(log);self.s=socket.create_connection((host,port),timeout=5);self.f=self.s.makefile('rb');self.serial=0
    def close(self):
        self.f.close();self.s.close()
    def execute(self,*args):
        atoms=[a if isinstance(a,bytes) else str(a).encode() for a in args]
        wire=b'*'+str(len(atoms)).encode()+b'\r\n'+b''.join(b'$'+str(len(a)).encode()+b'\r\n'+a+b'\r\n' for a in atoms)
        raw=[]
        def read(n):
            b=self.f.read(n)
            if len(b)!=n:raise EOFError('RESP peer closed')
            raw.append(b);return b
        def line():
            b=self.f.readline()
            if not b.endswith(b'\r\n'):raise EOFError('RESP incomplete line')
            raw.append(b);return b[:-2]
        def reply():
            tag=read(1);v=line()
            if tag==b'+':return {'type':'simple','value':v.decode()}
            if tag==b'-':return {'type':'error','value':v.decode()}
            if tag==b':':return {'type':'integer','value':int(v)}
            if tag==b'$':
                n=int(v)
                if n==-1:return {'type':'null','value':None}
                b=read(n);assert read(2)==b'\r\n';return {'type':'bulk','value':b.decode()}
            if tag==b'*':
                n=int(v)
                return {'type':'array','value':None if n==-1 else [reply() for _ in range(n)]}
            raise ValueError('unsupported RESP2 tag '+repr(tag))
        self.serial+=1;self.s.sendall(wire)
        try:result=reply()
        except EOFError:
            result={'type':'closed','value':None}
        record={'client':self.name,'serial':self.serial,'monotonic_ns':time.monotonic_ns(),'argv':[a.decode() for a in atoms],'request_b64':base64.b64encode(wire).decode(),'response_b64':base64.b64encode(b''.join(raw)).decode(),'reply':result}
        with self.log.open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
        return result
