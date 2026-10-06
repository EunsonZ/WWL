"""Functional dependencies and an atomic local outbox example.
SQLite here does not model PostgreSQL SSI, distributed brokers or physical WAL.
"""
from __future__ import annotations
import hashlib,itertools,json,sqlite3

def closure(attributes:set[str],fds:list[tuple[set[str],str]])->set[str]:
    out=set(attributes)
    while True:
        old=len(out)
        for left,right in fds:
            if left<=out:out.add(right)
        if len(out)==old:return out

def subsets(schema:set[str]):
    xs=sorted(schema)
    for n in range(len(xs)+1):
        for values in itertools.combinations(xs,n):yield set(values)

def keys(schema:set[str],fds:list[tuple[set[str],str]])->list[set[str]]:
    result=[]
    for x in subsets(schema):
        if not any(k<=x for k in result) and schema<=closure(x,fds):result.append(x)
    return result

def projection(schema:set[str],fds:list[tuple[set[str],str]])->list[tuple[set[str],str]]:
    return [(x,a) for x in subsets(schema) for a in sorted((closure(x,fds)&schema)-x)]

class InjectedFailure(Exception):pass
class KeyConflict(Exception):pass

class Outbox:
    def __init__(self):
        self.db=sqlite3.connect(':memory:',isolation_level=None)
        self.db.executescript('''
        CREATE TABLE requests(principal TEXT NOT NULL, operation TEXT NOT NULL, key TEXT NOT NULL, digest TEXT NOT NULL,
          result INTEGER, PRIMARY KEY(principal,operation,key));
        CREATE TABLE orders(id INTEGER PRIMARY KEY, principal TEXT NOT NULL, cents INTEGER NOT NULL CHECK(cents>=0));
        CREATE TABLE outbox(message_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, sent INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE processed(message_id INTEGER PRIMARY KEY);
        CREATE TABLE effects(message_id INTEGER PRIMARY KEY, amount INTEGER NOT NULL);
        ''')
    def close(self):self.db.close()
    def create(self,principal:str,key:str,cents:int,failure:str='')->int:
        # The caller supplies an authenticated principal; this model does not implement authentication.
        if type(principal) is not str or not principal or type(key) is not str or not key:
            raise ValueError('nonempty principal and idempotency key required')
        if type(cents) is not int or not 0 <= cents <= 2**63-1:
            raise ValueError('nonnegative SQLite-range integer cents required')
        digest=hashlib.sha256(json.dumps({'cents':cents},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('SELECT digest,result FROM requests WHERE principal=? AND operation=? AND key=?',(principal,'create',key)).fetchone()
            if row:
                if row[0]!=digest:raise KeyConflict('same key with different intent')
                self.db.execute('COMMIT');return row[1]
            self.db.execute('INSERT INTO requests VALUES(?,?,?,?,NULL)',(principal,'create',key,digest))
            order=self.db.execute('INSERT INTO orders(principal,cents) VALUES(?,?)',(principal,cents)).lastrowid
            assert order is not None
            if failure=='after-business':raise InjectedFailure(failure)
            self.db.execute('INSERT INTO outbox(message_id,order_id) VALUES(?,?)',(order,order))
            self.db.execute('UPDATE requests SET result=? WHERE principal=? AND operation=? AND key=?',(order,principal,'create',key))
            self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise
        if failure=='lost-response':raise InjectedFailure(failure)
        return order
    def publish(self,wire:list[int],failure:str='')->None:
        for (message,) in self.db.execute('SELECT message_id FROM outbox WHERE sent=0 ORDER BY message_id').fetchall():
            wire.append(message)
            if failure=='after-send':raise InjectedFailure(failure)
            self.db.execute('UPDATE outbox SET sent=1 WHERE message_id=?',(message,))
    def consume(self,message:int,failure:str='')->None:
        self.db.execute('BEGIN IMMEDIATE')
        try:
            if self.db.execute('SELECT 1 FROM processed WHERE message_id=?',(message,)).fetchone():
                self.db.execute('COMMIT');return
            self.db.execute('INSERT INTO processed VALUES(?)',(message,))
            if failure=='after-mark':raise InjectedFailure(failure)
            self.db.execute('INSERT INTO effects VALUES(?,1)',(message,));self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise
