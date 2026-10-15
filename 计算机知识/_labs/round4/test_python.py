import asyncio,importlib,subprocess,sys,tempfile,unittest
from pathlib import Path
import python_snippets as snippet

class ObjectTests(unittest.TestCase):
    def test_descriptor_and_method_shadow(self):
        obj=snippet.Example();obj.__dict__['x']='instance';obj.__dict__['method']='shadow'
        self.assertEqual(obj.x,'descriptor');self.assertEqual(obj.method,'shadow')
        with self.assertRaises(AttributeError):obj.x='new'
    def test_set_only_descriptor_does_not_override_instance_read(self):
        class SetOnly:
            def __set__(self, instance, value):
                raise AttributeError('write forbidden')
        class Sample:
            value = SetOnly()
        obj = Sample()
        obj.__dict__['value'] = 'instance'
        self.assertEqual(obj.value, 'instance')
        with self.assertRaises(AttributeError):
            obj.value = 'other'

    def test_c3_and_inconsistent_mro(self):
        self.assertEqual(snippet.D.__mro__,(snippet.D,snippet.B,snippet.C,snippet.A,object))
        class X:pass
        class Y:pass
        class A(X,Y):pass
        class B(Y,X):pass
        with self.assertRaises(TypeError):type('Conflict',(A,B),{})
    def test_circular_import_fails_during_partial_initialization(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'r4a.py').write_text('from r4b import b\na=1\n');(root/'r4b.py').write_text('import sys\nassert \"r4a\" in sys.modules\nassert \"a\" not in vars(sys.modules[\"r4a\"])\nprint(\"observed-partial-module\", file=sys.stderr)\nfrom r4a import a\nb=2\n')
            p=subprocess.run([sys.executable,'-c','import r4a'],cwd=directory,capture_output=True,text=True,timeout=3)
            self.assertNotEqual(p.returncode,0);self.assertIn('ImportError',p.stderr);self.assertIn('observed-partial-module',p.stderr)

class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_cancel_runs_finally(self):
        await asyncio.wait_for(snippet.demonstration(),3)
    async def test_taskgroup_exception_cancels_sibling(self):
        ready=asyncio.Event();cleaned=[];errors=[]
        async def fail():await ready.wait();raise ValueError('planned')
        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(snippet.child(ready,cleaned));group.create_task(fail())
        except* ValueError as eg:errors.extend(eg.exceptions)
        self.assertEqual(len(errors),1);self.assertEqual(cleaned,['released'])
    async def test_bounded_queue_applies_backpressure(self):
        q=asyncio.Queue(maxsize=1);await q.put(1);started=asyncio.Event()
        async def producer():started.set();await q.put(2)
        task=asyncio.create_task(producer());await asyncio.wait_for(started.wait(),2)
        self.assertFalse(task.done());self.assertEqual(await q.get(),1);q.task_done();await asyncio.wait_for(task,2)
        self.assertEqual(await q.get(),2);q.task_done();await asyncio.wait_for(q.join(),2)
    async def test_bounded_pipeline_and_sentinel_accounting(self):
        q=asyncio.Queue(maxsize=2);out=[]
        async def produce():
            for n in range(30):await q.put(n);self.assertLessEqual(q.qsize(),2)
            for _ in range(2):await q.put(None)
        async def pipeline():
            async with asyncio.TaskGroup() as group:
                for _ in range(2):group.create_task(snippet.consume(q,out))
                group.create_task(produce())
            await q.join()
        await asyncio.wait_for(pipeline(),3);self.assertEqual(sorted(out),[i*i for i in range(30)])

if __name__=='__main__':unittest.main(verbosity=2)
