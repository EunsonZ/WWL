"""Real SQLite integrity/index/snapshot probes; not Neo4j execution."""
import argparse
import json
from pathlib import Path
import sqlite3

SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE node(id TEXT PRIMARY KEY NOT NULL, label TEXT NOT NULL, title TEXT NOT NULL);
CREATE TABLE edge(id TEXT PRIMARY KEY NOT NULL, src TEXT NOT NULL REFERENCES node(id), dst TEXT NOT NULL REFERENCES node(id), type TEXT NOT NULL CHECK(type IN ('REQUIRES','TEACHES')), catalog TEXT NOT NULL);
'''


def run(spec, path):
    if path.exists(): raise FileExistsError('use a fresh database path')
    db=sqlite3.connect(path,isolation_level=None)
    try:
        assert db.execute('PRAGMA journal_mode=WAL').fetchone()[0]=='wal'
        db.execute('PRAGMA synchronous=FULL')
        db.executescript(SCHEMA)
        db.execute('BEGIN')
        db.executemany('INSERT INTO node VALUES(:id,:label,:title)',spec['nodes'])
        db.executemany('INSERT INTO edge VALUES(:id,:src,:dst,:type,:catalog)',spec['edges'])
        db.execute('COMMIT')
        failures=[]
        probes=[('duplicate_node','INSERT INTO node VALUES(?,?,?)',('a','Course','dup')),
                ('duplicate_edge','INSERT INTO edge VALUES(?,?,?,?,?)',('e1','a','c','REQUIRES','T1')),
                ('missing_endpoint','INSERT INTO edge VALUES(?,?,?,?,?)',('bad','a','absent','REQUIRES','T1')),
                ('null_endpoint','INSERT INTO edge VALUES(?,?,?,?,?)',('bad','a',None,'REQUIRES','T1')),
                ('unknown_type','INSERT INTO edge VALUES(?,?,?,?,?)',('bad','a','c','UNKNOWN','T1'))]
        for name,sql,args in probes:
            before=db.total_changes
            try: db.execute(sql,args)
            except sqlite3.IntegrityError as error:
                failures.append({'probe':name,'error_name':error.sqlite_errorname,'message':str(error),'rows_changed':db.total_changes-before})
            else: raise AssertionError(name)
        query='SELECT id FROM edge WHERE src=? AND type=? ORDER BY id'
        before_plan=[list(r) for r in db.execute('EXPLAIN QUERY PLAN '+query,('a','REQUIRES'))]
        rows_before=[r[0] for r in db.execute(query,('a','REQUIRES'))]
        db.execute('CREATE INDEX edge_src_type ON edge(src,type)')
        after_plan=[list(r) for r in db.execute('EXPLAIN QUERY PLAN '+query,('a','REQUIRES'))]
        rows_after=[r[0] for r in db.execute(query,('a','REQUIRES'))]
        assert rows_before==rows_after==['e1','e4','e5']
        # A whole finite import is one actual transaction. A later failure undoes the earlier insert.
        db.execute('BEGIN')
        db.execute("INSERT INTO edge VALUES('transient','c','a','REQUIRES','T1')")
        try: db.execute("INSERT INTO edge VALUES('e1','a','c','REQUIRES','T1')")
        except sqlite3.IntegrityError: db.execute('ROLLBACK')
        assert not db.execute("SELECT 1 FROM edge WHERE id='transient'").fetchall()
        constraint_state={'node_count':db.execute('SELECT count(*) FROM node').fetchone()[0],
                          'edge_count':db.execute('SELECT count(*) FROM edge').fetchone()[0],
                          'foreign_key_check':list(db.execute('PRAGMA foreign_key_check')),
                          'parallel_ids':[r[0] for r in db.execute("SELECT id FROM edge WHERE src='a' AND dst='b' ORDER BY id")],
                          'rolled_back_transient':True}
        # Two real connections: unpinned multi-statement traversal can mix revisions.
        db.execute('BEGIN'); db.execute('DELETE FROM edge');
        e1=next(e for e in spec['edges'] if e['id']=='e1'); e3=next(e for e in spec['edges'] if e['id']=='e3')
        db.execute('INSERT INTO edge VALUES(:id,:src,:dst,:type,:catalog)',e1); db.execute('COMMIT')
        reader=sqlite3.connect(path,isolation_level=None)
        try:
            reader.execute('PRAGMA foreign_keys=ON')
            first=[r[0] for r in reader.execute(query,('a','REQUIRES'))]
            reader.execute('BEGIN')
            pinned_before=[r[0] for r in reader.execute('SELECT id FROM edge ORDER BY id')]
            db.execute('BEGIN'); db.execute('DELETE FROM edge'); db.execute('INSERT INTO edge VALUES(:id,:src,:dst,:type,:catalog)',e3); db.execute('COMMIT')
            pinned_after=[r[0] for r in reader.execute('SELECT id FROM edge ORDER BY id')]
            reader.execute('COMMIT')
            second=[r[0] for r in reader.execute(query,('b','REQUIRES'))]
            final=[r[0] for r in reader.execute('SELECT id FROM edge ORDER BY id')]
        finally: reader.close()
        assert first==pinned_before==pinned_after==['e1'] and second==final==['e3']
        return {'sqlite_version':sqlite3.sqlite_version,'journal_mode':'wal','synchronous':'FULL',
                'failures':failures,'integrity':constraint_state,
                'index':{'query':query,'parameters':['a','REQUIRES'],'without_index_plan':before_plan,'with_index_plan':after_plan,'edge_ids':rows_after},
                'snapshot':{'before_edges':['e1'],'after_edges':final,'unbound_first_hop':first,'unbound_second_hop':second,
                            'fabricated_path':['e1','e3'],'path_in_either_snapshot':False,'pinned_before':pinned_before,'pinned_after_writer_commit':pinned_after},
                'boundary':'two actual local SQLite connections, no Neo4j or distributed consistency test'}
    finally: db.close()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--spec',type=Path,required=True); p.add_argument('--db',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); r=run(json.loads(a.spec.read_text()),a.db)
    a.out.write_text(json.dumps(r,ensure_ascii=True,indent=2)+'\n'); print(json.dumps({'failures':len(r['failures']),'snapshot':r['snapshot']}))
if __name__=='__main__': main()
