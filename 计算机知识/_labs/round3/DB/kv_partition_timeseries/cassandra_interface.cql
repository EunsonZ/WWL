-- UNEXECUTED Cassandra 5.0-style CQL interface, not evidence of Cassandra runtime.
-- An explicitly owned keyspace must already exist; do not apply to production.
CREATE TABLE enrollment_audit_by_student_day (
  student_id text, bucket bigint, event_ms bigint, event_id text,
  term text, course_id text, version int, deleted boolean, grade text,
  PRIMARY KEY ((student_id, bucket), event_ms, event_id)
) WITH CLUSTERING ORDER BY (event_ms ASC, event_id ASC);
-- D=86400000 milliseconds; one query per known partition.
SELECT * FROM enrollment_audit_by_student_day
WHERE student_id='S1' AND bucket=1
  AND event_ms >= 86400000 AND event_ms < 86400001;
-- Resume strictly after (event_ms,event_id); equality on partition key remains required.
SELECT * FROM enrollment_audit_by_student_day
WHERE student_id='S1' AND bucket=1
  AND (event_ms,event_id) > (86400000,'R12') LIMIT 2;
-- Expected fixed data: first returns R12,R13; resume returns R13,R15.
-- This is the daily unsharded interface only. Application must fan out/merge buckets.
-- Current state CAS, logical TTL and Redis Lua do not transfer to this CQL table.
