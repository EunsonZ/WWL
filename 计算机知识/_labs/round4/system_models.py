"""Explicit small models and safe local I/O helpers. No hardware or power-cut emulation."""
from __future__ import annotations
import os,tempfile
from pathlib import Path
from threading import Condition
from collections import deque

class ClosedQueue(Exception):pass
class Buffer:
    def __init__(self,capacity:int):
        if capacity<=0:raise ValueError('positive capacity required')
        self.capacity=capacity;self.items=deque();self.closed=False;self.cv=Condition()
    def put(self,item):
        with self.cv:
            while len(self.items)==self.capacity and not self.closed:self.cv.wait()
            if self.closed:raise ClosedQueue()
            self.items.append(item);self.cv.notify_all()
    def get(self):
        with self.cv:
            while not self.items and not self.closed:self.cv.wait()
            if not self.items:raise ClosedQueue()
            item=self.items.popleft();self.cv.notify_all();return item
    def close(self):
        with self.cv:self.closed=True;self.cv.notify_all()


def replace_file(path:Path,data:bytes)->None:
    """Trusted same directory; new mode is mkstemp's mode, not original metadata.
    fsync failures propagate. After replace, a directory fsync error is an
    uncertain durability outcome, not evidence that the old name was restored.
    """
    fd,name=tempfile.mkstemp(prefix='.publish-',dir=path.parent)
    try:
        try:
            offset=0
            while offset<len(data):
                try:n=os.write(fd,data[offset:])
                except InterruptedError:continue
                if n<=0:raise OSError('no write progress')
                offset+=n
            os.fsync(fd)
        finally:os.close(fd)
        os.replace(name,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        try:os.unlink(name)
        except FileNotFoundError:pass

class CrashFS:
    """Toy FS: only explicit sync copies state to a stable map.
    Actual filesystems may persist additional writes; this is not a POSIX model.
    """
    def __init__(self):
        self.data={'old':b'old'};self.stable_data=dict(self.data)
        self.names={'config':'old'};self.stable_names=dict(self.names)
    def prepare(self):self.data['new']=b'new'
    def sync_file(self):self.stable_data['new']=self.data['new']
    def rename(self):self.names['config']='new'
    def sync_dir(self):self.stable_names=dict(self.names)
    def crash_read(self):return self.stable_data.get(self.stable_names['config'])

class Frames:
    def __init__(self,max_size:int=1024):
        if max_size<0:raise ValueError('bad limit')
        self.buffer=bytearray();self.max_size=max_size
    def feed(self,chunk:bytes)->list[bytes]:
        self.buffer.extend(chunk);out=[]
        while len(self.buffer)>=4:
            n=int.from_bytes(self.buffer[:4],'big')
            if n>self.max_size:raise ValueError('oversize frame')
            if len(self.buffer)<4+n:break
            out.append(bytes(self.buffer[4:4+n]));del self.buffer[:4+n]
        return out
    def finish(self):
        if self.buffer:raise ValueError('truncated frame')


def fragments(total:int,mtu:int,header:int=20)->list[tuple[int,int,int]]:
    """IPv4 teaching subset: DF=0, no options, valid lengths, original not fragmented."""
    if header!=20 or not header<=total<=65535 or mtu<header+8:raise ValueError('unsupported header/length/MTU')
    if total<=mtu:return [(total,0,0)]
    chunk=(mtu-header)//8*8;remaining=total-header;offset=0;result=[]
    while remaining:
        n=min(chunk,remaining);remaining-=n;result.append((header+n,offset//8,int(remaining>0)));offset+=n
    return result

class RTO:
    def __init__(self,granularity:float=.001):self.g=granularity;self.s=None;self.v=None;self.timeout=1.
    def sample(self,r:float):
        if r<=0:raise ValueError('positive RTT required')
        if self.s is None:self.s=r;self.v=r/2
        else:
            assert self.v is not None
            self.v=.75*self.v+.25*abs(self.s-r)
            self.s=.875*self.s+.125*r
        raw=self.s+max(self.g,4*self.v);self.timeout=max(1.,raw);return raw
    def retransmit(self):self.timeout*=2
