"""Own loopback worker: serial RPC -> Node -> changed stable state -> reply.
Whole-state SQLite persistence is a local teaching adapter, not a Raft snapshot.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import sqlite3
import time
from read_model import Node


def main():
    a=argparse.ArgumentParser();a.add_argument('--node',required=True);a.add_argument('--db',type=Path,required=True);a.add_argument('--audit',type=Path,required=True);z=a.parse_args()
    db=sqlite3.connect(z.db);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
    db.execute('CREATE TABLE IF NOT EXISTS stable(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL)')
    row=db.execute('SELECT payload FROM stable WHERE id=1').fetchone();node=Node(z.node,json.loads(row[0]) if row else None)
    def save():
        payload=json.dumps(node.persistent(),sort_keys=True,separators=(',',':'))
        with db:db.execute('INSERT INTO stable(id,payload) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(payload,))
    save();audit=z.audit.open('a',encoding='utf8')
    with socket.socket() as server:
        server.bind(('127.0.0.1',0));server.listen(8);server.settimeout(30)
        print(json.dumps({'node':z.node,'pid':os.getpid(),'port':server.getsockname()[1],'boot':node.boot,'db':str(z.db)}),flush=True)
        stop=False
        while not stop:
            conn,_=server.accept()
            with conn:
                conn.settimeout(2);f=conn.makefile('rwb');line=f.readline(65537)
                old=deepcopy(node);before=node.persistent();started=time.monotonic_ns()
                try:
                    if len(line)>65536 or not line.endswith(b'\n'):raise ValueError('bounded JSON line required')
                    command=json.loads(line)
                    if command['op']=='shutdown':result={'status':'shutdown'};stop=True
                    else:result=node.handle(command)
                    changed=node.persistent()!=before
                    if changed:save()
                    response={'ok':True,'result':result,'stable_changed':changed}
                except (ValueError,KeyError,TypeError,AssertionError) as error:
                    node=old;response={'ok':False,'error':type(error).__name__+': '+str(error),'stable_changed':False}
                audit.write(json.dumps({'start_monotonic_ns':started,'reply_ready_monotonic_ns':time.monotonic_ns(),'command':line.decode('utf8','backslashreplace').rstrip('\n'),'response':response},ensure_ascii=True)+'\n');audit.flush()
                f.write((json.dumps(response,ensure_ascii=True,allow_nan=False,separators=(',',':'))+'\n').encode());f.flush()
    audit.close();db.close()
if __name__=='__main__':main()
