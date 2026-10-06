"""SQLite SQL/constraint/rollback lab; NOT a PostgreSQL SSI concurrency test."""
import sqlite3

def main():
    db=sqlite3.connect(':memory:');db.execute('PRAGMA foreign_keys=ON')
    assert db.execute('PRAGMA foreign_keys').fetchone()==(1,)
    db.executescript("""
    CREATE TABLE student(id INTEGER PRIMARY KEY,name TEXT NOT NULL);
    CREATE TABLE course(id INTEGER PRIMARY KEY,title TEXT NOT NULL);
    CREATE TABLE enrollment(student_id INTEGER NOT NULL REFERENCES student(id),
      course_id INTEGER NOT NULL REFERENCES course(id),term TEXT NOT NULL,
      grade INTEGER CHECK(grade BETWEEN 0 AND 100),PRIMARY KEY(student_id,course_id,term));
    INSERT INTO student VALUES(1,'A'),(2,'B');
    INSERT INTO course VALUES(10,'DB');
    INSERT INTO enrollment VALUES(1,10,'2026A',NULL);
    """)
    for sql in ("INSERT INTO enrollment VALUES(99,10,'2026A',50)",
                "INSERT INTO enrollment VALUES(1,10,'2026A',50)",
                "INSERT INTO enrollment VALUES(2,10,'2026A',101)"):
        try:db.execute(sql)
        except sqlite3.IntegrityError:db.rollback()
        else:raise AssertionError('constraint not enforced')
    rows=db.execute("SELECT s.id,COUNT(e.course_id) FROM student s LEFT JOIN enrollment e ON e.student_id=s.id AND e.term='2026A' GROUP BY s.id ORDER BY s.id").fetchall()
    assert rows==[(1,1),(2,0)]
    assert db.execute('SELECT COUNT(*),COUNT(grade),SUM(grade) FROM enrollment').fetchone()==(1,0,None)
    assert db.execute('SELECT 1 WHERE 1 NOT IN (2,NULL)').fetchall()==[]
    db.execute('CREATE TABLE payment(id INTEGER PRIMARY KEY,amount INTEGER)')
    db.executemany('INSERT INTO payment VALUES(?,?)',[(1,10),(2,20),(3,20)])
    result=db.execute('SELECT SUM(amount) OVER(ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM payment ORDER BY id').fetchall()
    assert result==[(10,),(30,),(50,)]
    db.commit();db.execute('UPDATE payment SET amount=999 WHERE id=1');db.rollback()
    assert db.execute('SELECT amount FROM payment WHERE id=1').fetchone()==(10,)
    db.close();print('PASS: SQLite',sqlite3.sqlite_version,'constraints, LEFT JOIN, NULL, window, rollback')
if __name__=='__main__':main()
