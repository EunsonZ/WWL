// UNEXECUTED interface for an explicitly owned, empty Neo4j 5.26 database.
// Do not run against an existing database. All data below are teaching fixtures.
CREATE CONSTRAINT fixture_entity_id FOR (n:Entity) REQUIRE n.id IS UNIQUE;
CREATE (a:Entity:Course {id:'a'}), (b:Entity:Course {id:'b'}),
       (c:Entity:Course {id:'c'}), (d:Entity:Course {id:'d'}),
       (z:Entity:Course {id:'z'}), (t:Entity:Teacher {id:'t7'}),
       (a)-[:REQUIRES {id:'e1',catalog:'T1'}]->(b),
       (b)-[:REQUIRES {id:'e2',catalog:'T1'}]->(a),
       (b)-[:REQUIRES {id:'e3',catalog:'T1'}]->(c),
       (a)-[:REQUIRES {id:'e4',catalog:'T1'}]->(b),
       (a)-[:REQUIRES {id:'e5',catalog:'T1'}]->(d),
       (d)-[:REQUIRES {id:'e6',catalog:'T1'}]->(c),
       (a)-[:TEACHES {id:'e7',catalog:'T1'}]->(c),
       (t)-[:TEACHES {id:'e8',catalog:'T1'}]->(a);
// Default: relationships do not repeat in a matched path; nodes may repeat.
MATCH p=(a:Course {id:'a'})-[:REQUIRES*1..5]->(c:Course {id:'c'})
WHERE all(n IN nodes(p) WHERE n:Course)
  AND all(r IN relationships(p) WHERE r.catalog='T1')
RETURN [n IN nodes(p) | n.id] AS node_ids,
       [r IN relationships(p) | r.id] AS edge_ids
ORDER BY size(edge_ids), edge_ids;
// Further restrict to node-simple paths BEFORE selecting any minimum length.
MATCH p=(a:Course {id:'a'})-[:REQUIRES*1..5]->(c:Course {id:'c'})
WHERE all(n IN nodes(p) WHERE n:Course)
  AND all(r IN relationships(p) WHERE r.catalog='T1')
  AND all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m=n))
RETURN [r IN relationships(p) | r.id] AS edge_ids ORDER BY edge_ids;
// All minimum-hop paths among the already filtered bounded candidates.
MATCH p=(a:Course {id:'a'})-[:REQUIRES*1..5]->(c:Course {id:'c'})
WHERE all(n IN nodes(p) WHERE n:Course)
  AND all(r IN relationships(p) WHERE r.catalog='T1')
WITH collect(p) AS candidates, min(length(p)) AS hops
UNWIND [p IN candidates WHERE length(p)=hops] AS p
RETURN hops,[r IN relationships(p) | r.id] AS edge_ids ORDER BY edge_ids;
// For the exact fixture, expected counts are trail 7, simple 3, shortest 3 at 2 hops.
// This does not express repeatable-edge walks. No Cypher 25-only keywords used.
