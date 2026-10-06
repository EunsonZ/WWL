-- MANUAL ONLY. Requires an isolated PostgreSQL 17 test database.
-- Not executed in the delivery environment. Do not run on production tables.
-- SETUP (once; use a new database/schema rather than deleting existing data):
CREATE SCHEMA round4_lab;
CREATE TABLE round4_lab.doctors(name text PRIMARY KEY, on_call boolean NOT NULL);
INSERT INTO round4_lab.doctors VALUES ('Alice',true),('Bob',true);

-- Open two independent sessions. Execute the numbered steps in order.
-- 1. SESSION A:
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT count(*) FROM round4_lab.doctors WHERE on_call; -- 2
-- 2. SESSION B:
-- BEGIN ISOLATION LEVEL REPEATABLE READ;
-- SELECT count(*) FROM round4_lab.doctors WHERE on_call; -- 2
-- 3. SESSION A:
UPDATE round4_lab.doctors SET on_call=false WHERE name='Alice';
-- 4. SESSION B:
-- UPDATE round4_lab.doctors SET on_call=false WHERE name='Bob';
-- COMMIT;
-- 5. SESSION A:
COMMIT;
-- 6. Outside either transaction:
SELECT count(*) FROM round4_lab.doctors WHERE on_call; -- 0, after both commits

-- SERIALIZABLE variation:
-- Reset both rows to true outside the completed transactions in this isolated schema.
-- Repeat with BEGIN ISOLATION LEVEL SERIALIZABLE in BOTH sessions.
-- The complete read/read/write/write history cannot commit both transactions:
-- one transaction may fail during an operation or COMMIT with serialization_failure.
-- Retry the WHOLE transaction, re-read count, and update only if count >= 2.
-- Do not merely resend its final UPDATE.

-- Guard-row alternative: use READ COMMITTED in both sessions, lock the SAME
-- guard row with SELECT ... FOR UPDATE, THEN run a fresh count SELECT and decide.
-- A guard row without locking every competing decision path is insufficient.
