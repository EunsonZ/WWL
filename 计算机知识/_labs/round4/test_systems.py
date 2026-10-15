from __future__ import annotations
import decimal,fcntl,ipaddress,math,os,select,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from system_models import Buffer,ClosedQueue,replace_file,CrashFS,Frames,fragments,RTO

class HardwareTests(unittest.TestCase):
    def test_float_cancellation_and_stable_rewrite(self):
        self.assertEqual(sys.float_info.mant_dig,53);self.assertEqual(sys.float_info.epsilon,2**-52)
        x=1e-16;naive=math.sqrt(1+x)-1;stable=x/(math.sqrt(1+x)+1)
        with decimal.localcontext() as ctx:
            ctx.prec=80;dx=decimal.Decimal.from_float(x);reference=(decimal.Decimal(1)+dx).sqrt()-1
            error_stable=abs(decimal.Decimal.from_float(stable)-reference);error_naive=abs(decimal.Decimal.from_float(naive)-reference)
        self.assertEqual(naive,0);self.assertLess(error_stable,error_naive);self.assertEqual(math.nextafter(1.,math.inf)-1.,2**-52)
    def test_summation_and_nan_guard(self):
        nums=[1e16,1.,-1e16];sequential=0.
        for x in nums:sequential+=x
        self.assertEqual(sequential,0.);self.assertEqual(math.fsum(nums),1.)
        self.assertFalse(float('nan')<0);self.assertFalse(math.isfinite(float('nan')))
    def test_sv39_indices_and_page_counts(self):
        va=0x12345678;indices=[(va>>s)&511 for s in (30,21,12)]
        self.assertEqual(indices,[0,145,325]);self.assertEqual(va&4095,0x678);self.assertEqual((0xABC<<12)|(va&4095),0xABC678)
        self.assertEqual((512+1+1)*4096,2*1024**2+8192);self.assertEqual(3*4096,12288)
    def test_cow_and_stale_tlb_are_separate_state(self):
        memory={1:[10]};pt={'parent':(1,False),'child':(1,False)};tlb=dict(pt)
        memory[2]=memory[1].copy();pt['child']=(2,True)
        self.assertEqual(tlb['child'],(1,False));tlb.pop('child');tlb['child']=pt['child']
        pfn,writable=tlb['child'];self.assertTrue(writable);memory[pfn][0]=99
        self.assertEqual(memory[pt['parent'][0]][0],10);self.assertEqual(memory[pt['child'][0]][0],99)
    def test_reorder_completion_is_not_commit(self):
        arch={'r1':0,'r2':0};memory={'x':0}
        rob=[{'kind':'load','done':False,'fault':True},{'kind':'add','done':True,'reg':'r2','value':7},{'kind':'store','done':True,'key':'x','value':8}]
        self.assertTrue(rob[2]['done']);self.assertEqual(memory['x'],0)
        rob[0]['done']=True
        if rob[0]['fault']:rob.clear()
        self.assertEqual(arch,{'r1':0,'r2':0});self.assertEqual(memory['x'],0)
        # Register renaming preserves input identities even when later writers appear.
        rename={'r1':'p1'};source_for_old_reader=rename['r1'];rename['r1']='p7'
        self.assertEqual(source_for_old_reader,'p1');self.assertEqual(rename['r1'],'p7')
        self.assertAlmostEqual(.8+.18*.04*15,.908)

class OSTests(unittest.TestCase):
    def test_condition_queue_close_and_drain(self):
        b=Buffer(2);received=[];errors=[]
        def worker():
            try:
                while True:received.append(b.get())
            except ClosedQueue:pass
            except BaseException as e:errors.append(str(e))
        thread=threading.Thread(target=worker,daemon=True);thread.start()
        try:
            for i in range(30):b.put(i)
        finally:b.close()
        thread.join(3);self.assertFalse(thread.is_alive());self.assertEqual(received,list(range(30)));self.assertEqual(errors,[])
        with self.assertRaises(ClosedQueue):b.put(99)
    def test_wait_checks_predicate_not_notification(self):
        cv=threading.Condition();state={'ready':False,'closed':False};waiting=threading.Event();done=threading.Event()
        def worker():
            with cv:
                waiting.set()
                while not state['ready'] and not state['closed']:cv.wait()
                if state['ready']:done.set()
        t=threading.Thread(target=worker,daemon=True);t.start();self.assertTrue(waiting.wait(2))
        with cv:
            cv.notify_all();self.assertFalse(done.is_set());state['ready']=True;cv.notify_all()
        t.join(3);self.assertFalse(t.is_alive());self.assertTrue(done.is_set())
        # Model of a lost wake if check and enrolment are not atomic with release.
        events=['consumer sees empty','producer adds item','producer notifies nobody','consumer enrolls and sleeps']
        self.assertLess(events.index('producer notifies nobody'),events.index('consumer enrolls and sleeps'))
    def test_crash_ordering_model(self):
        fs=CrashFS();fs.prepare();self.assertEqual(fs.crash_read(),b'old');fs.sync_file();self.assertEqual(fs.crash_read(),b'old')
        fs.rename();self.assertEqual(fs.crash_read(),b'old');fs.sync_dir();self.assertEqual(fs.crash_read(),b'new')
        bad=CrashFS();bad.prepare();bad.rename();bad.sync_dir();self.assertIsNone(bad.crash_read())
    def test_safe_local_replace_and_old_fd(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'config';p.write_bytes(b'old')
            with p.open('rb') as old:
                replace_file(p,b'new'*1000);self.assertEqual(p.read_bytes(),b'new'*1000);self.assertEqual(old.read(),b'old')
            replace_file(p,b'');self.assertEqual(p.read_bytes(),b'');self.assertEqual(sorted(x.name for x in Path(directory).iterdir()),['config'])

class NetworkTests(unittest.TestCase):
    def test_route_longest_prefix_offline(self):
        routes=[('0.0.0.0/0','default'),('203.0.113.0/24','routerA'),('203.0.113.8/30','routerB')]
        dest=ipaddress.ip_address('203.0.113.9');matches=[(ipaddress.ip_network(n).prefixlen,v) for n,v in routes if dest in ipaddress.ip_network(n)]
        self.assertEqual(max(matches)[1],'routerB')
    def test_ipv4_fragment_sizes_offsets(self):
        f=fragments(4000,1500);self.assertEqual(f,[(1500,0,1),(1500,185,1),(1040,370,0)])
        self.assertEqual(sum(n-20 for n,_,_ in f),3980);self.assertEqual(sum(n for n,_,_ in f),4040)
        self.assertEqual(1500-20-8,1472);self.assertEqual(1500-40-8,1452)
    def test_tcp_window_rto_and_bdp(self):
        self.assertEqual(max(0,min(64000,10000)-8000),2000);self.assertEqual(1000+1+6000,7001)
        r=RTO();self.assertAlmostEqual(r.sample(.120),.360);self.assertEqual(r.timeout,1.)
        self.assertAlmostEqual(r.sample(.160),.345);self.assertAlmostEqual(r.s,.125);self.assertAlmostEqual(r.v,.055)
        r.retransmit();self.assertEqual(r.timeout,2.);self.assertEqual(100_000_000*.05/8,625000);self.assertAlmostEqual(65536/.05*8/1e6,10.48576)
    def test_framing_every_two_split_and_bytewise(self):
        payloads=[b'abc',b'',b'hello'];wire=b''.join(len(p).to_bytes(4,'big')+p for p in payloads)
        for a in range(len(wire)+1):
            for b in range(a,len(wire)+1):
                decoder=Frames();out=[]
                for piece in [wire[:a],wire[a:b],wire[b:]]:out.extend(decoder.feed(piece))
                decoder.finish();self.assertEqual(out,payloads)
        decoder=Frames();out=[]
        for c in wire:out.extend(decoder.feed(bytes([c])))
        self.assertEqual(out,payloads)
        with self.assertRaises(ValueError):Frames(2).feed((3).to_bytes(4,'big'))
        with self.assertRaises(ValueError):
            d=Frames();d.feed(b'\0');d.finish()

class LinuxTests(unittest.TestCase):
    def test_dup_offset_and_fd_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'file';p.write_bytes(b'abcdef');f1=os.open(p,os.O_RDONLY);f2=os.dup(f1);f3=os.open(p,os.O_RDONLY)
            try:
                self.assertEqual(os.read(f1,2),b'ab');self.assertEqual(os.read(f2,2),b'cd');self.assertEqual(os.read(f3,2),b'ab')
                os.set_inheritable(f1,True);os.set_inheritable(f2,False);self.assertTrue(os.get_inheritable(f1));self.assertFalse(os.get_inheritable(f2))
                flags=fcntl.fcntl(f1,fcntl.F_GETFL);fcntl.fcntl(f1,fcntl.F_SETFL,flags|os.O_NONBLOCK)
                self.assertTrue(fcntl.fcntl(f2,fcntl.F_GETFL)&os.O_NONBLOCK)
            finally:
                for f in [f1,f2,f3]:os.close(f)
    @unittest.skipUnless(hasattr(select,'epoll'),'Linux epoll unavailable')
    def test_epoll_drain_eagain_and_eof(self):
        r,w=os.pipe();os.set_blocking(r,False);ep=select.epoll()
        try:
            ep.register(r,select.EPOLLIN|select.EPOLLET);os.write(w,b'abcd');self.assertTrue(ep.poll(1))
            data=bytearray()
            while True:
                try:chunk=os.read(r,2)
                except BlockingIOError:break
                self.assertTrue(chunk);data.extend(chunk)
            self.assertEqual(bytes(data),b'abcd');self.assertEqual(ep.poll(0),[])
            os.close(w);w=-1;self.assertTrue(ep.poll(1));self.assertEqual(os.read(r,2),b'')
        finally:
            ep.close();os.close(r)
            if w>=0:os.close(w)
    def test_partial_write_keeps_unsent_suffix(self):
        remaining=b'abcdef';sent=b''
        for result in [2,None,4]:
            if result is None:self.assertEqual(remaining,b'cdef');continue
            sent+=remaining[:result];remaining=remaining[result:]
        self.assertEqual(sent,b'abcdef');self.assertEqual(remaining,b'')
    def test_symlink_escape_in_temporary_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);safe=root/'safe';safe.mkdir();outside=root/'outside';outside.write_text('outside');(safe/'link').symlink_to(outside)
            self.assertTrue(str(safe/'link').startswith(str(safe)));self.assertFalse((safe/'link').resolve().is_relative_to(safe.resolve()))
    def test_shell_redirection_order(self):
        with tempfile.TemporaryDirectory() as directory:
            for redir,expected_file,expected_stdout in [('>out 2>&1','OE',''),('2>&1 >out','O','E')]:
                p=subprocess.run(['bash','-c',"{ printf O; printf E >&2; } "+redir],cwd=directory,text=True,capture_output=True,timeout=3,check=True)
                self.assertEqual((Path(directory)/'out').read_text(),expected_file);self.assertEqual(p.stdout,expected_stdout)

if __name__=='__main__':unittest.main(verbosity=2)
