// WWL_DOCUMENT_MODEL_DBPATH=/private/tmp/wwl-document-model-.../db mongosh --quiet 'mongodb://127.0.0.1:PORT/?directConnection=true' --file PATH
// MongoDB Community 7.0.x; create and remove only a fresh temporary database.
const server = db.getSiblingDB("admin").runCommand({buildInfo: 1});
if (server.ok !== 1 || !/^7\.0\./.test(server.version)) {
  throw new Error("This lesson requires a MongoDB 7.0.x server");
}
const opts = db.getSiblingDB("admin").runCommand({getCmdLineOpts: 1});
const expectedDbPath = process.env.WWL_DOCUMENT_MODEL_DBPATH;
if (!expectedDbPath || !/^\/(?:private\/)?tmp\/wwl-(?:stage-)?document-model-/.test(expectedDbPath) ||
    opts.ok !== 1 || opts.parsed?.storage?.dbPath !== expectedDbPath ||
    opts.parsed?.net?.bindIp !== "127.0.0.1") {
  throw new Error("Use the isolated loopback teaching server with the declared temporary dbpath");
}
const labName = "wwl_document_model_" + new ObjectId().toHexString();
const lab = db.getSiblingDB(labName);
if (lab.getCollectionNames().length !== 0) throw new Error("Database is not empty");
print(JSON.stringify({serverVersion: server.version, temporaryDatabase: labName}));
let checks = 0;
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  }
  return value;
}
function same(label, actual, expected) {
  if (JSON.stringify(canonical(actual)) !== JSON.stringify(canonical(expected))) {
    throw new Error(label + ": " + JSON.stringify({actual, expected}));
  }
  checks += 1;
  print(JSON.stringify({check: label, result: actual}));
}
function ids(filter) {
  return lab.prereqCases.find(filter).sort({_id: 1}).toArray().map(x => x._id);
}
function embeddedRows(studentId) {
  return lab.schedules.aggregate([
    {$match: {studentId, term: "T1"}},
    {$unwind: "$enrollments"},
    {$project: {_id: 0, courseId: "$enrollments.courseId",
      currentPhone: "$enrollments.currentPhone",
      teacherPhoneAtEnrollment: "$enrollments.teacherPhoneAtEnrollment"}},
    {$sort: {courseId: 1}}
  ]).toArray();
}
function referencedRows(studentId) {
  return lab.enrollments.aggregate([
    {$match: {studentId, term: "T1"}},
    {$lookup: {from: "teachers", localField: "teacherId", foreignField: "_id", as: "teacher"}},
    {$unwind: "$teacher"},
    {$project: {_id: 0, courseId: 1, currentPhone: "$teacher.currentPhone",
      teacherPhoneAtEnrollment: 1}},
    {$sort: {courseId: 1}}
  ]).toArray();
}
function expectedRows(courses, phones) {
  return courses.map((courseId, i) => ({courseId, currentPhone: phones[i],
    teacherPhoneAtEnrollment: "555-0100"}));
}
try {
  lab.prereqCases.insertMany([
    {_id: 1}, {_id: 2, prereqs: null}, {_id: 3, prereqs: []},
    {_id: 4, prereqs: ["C1", "C1"]}
  ]);
  const queries = [
    ["missing", {prereqs: {$exists: false}}, [1]],
    ["null_equality", {prereqs: null}, [1, 2]],
    ["null_type", {prereqs: {$type: 10}}, [2]],
    ["exists", {prereqs: {$exists: true}}, [2, 3, 4]],
    ["array_type", {prereqs: {$type: "array"}}, [3, 4]],
    ["empty_array", {prereqs: []}, [3]],
    ["element_C1", {prereqs: "C1"}, [4]],
    ["exact_duplicates", {prereqs: ["C1", "C1"]}, [4]],
    ["exact_singleton", {prereqs: ["C1"]}, []],
    ["size_two", {prereqs: {$size: 2}}, [4]]
  ];
  for (const [label, filter, expected] of queries) same(label, ids(filter), expected);
  same("duplicate_unwind", lab.prereqCases.aggregate([
    {$match: {_id: 4}}, {$unwind: "$prereqs"},
    {$project: {_id: 0, prereqs: 1}}
  ]).toArray(), [{prereqs: "C1"}, {prereqs: "C1"}]);
  lab.students.insertMany([{_id: "S1", name: "Lin"}, {_id: "S2", name: "Mei"}]);
  lab.teachers.insertOne({_id: "T7", currentPhone: "555-0100"});
  const enrollments = [
    {_id: "E1", studentId: "S1", term: "T1", courseId: "C10", teacherId: "T7", grade: "A", teacherPhoneAtEnrollment: "555-0100"},
    {_id: "E2", studentId: "S1", term: "T1", courseId: "C20", teacherId: "T7", grade: "B", teacherPhoneAtEnrollment: "555-0100"},
    {_id: "E3", studentId: "S2", term: "T1", courseId: "C10", teacherId: "T7", grade: "A", teacherPhoneAtEnrollment: "555-0100"}
  ];
  lab.enrollments.insertMany(enrollments);
  lab.enrollments.createIndex({studentId: 1, term: 1, courseId: 1}, {unique: true});
  for (const studentId of ["S1", "S2"]) {
    lab.schedules.insertOne({_id: studentId + "/T1", studentId, term: "T1",
      enrollments: enrollments.filter(x => x.studentId === studentId).map(x => ({
        courseId: x.courseId, teacherId: x.teacherId, grade: x.grade,
        currentPhone: "555-0100", teacherPhoneAtEnrollment: x.teacherPhoneAtEnrollment
      }))});
  }
  same("reference_before", referencedRows("S1"), expectedRows(["C10", "C20"], ["555-0100", "555-0100"]));
  same("embedded_before", embeddedRows("S1"), referencedRows("S1"));
  const teacherUpdate = lab.teachers.updateOne({_id: "T7"}, {$set: {currentPhone: "555-0199"}});
  same("teacher_update_count", teacherUpdate.modifiedCount, 1);
  same("reference_after", referencedRows("S1"), expectedRows(["C10", "C20"], ["555-0199", "555-0199"]));
  same("embedded_stale", embeddedRows("S1"), expectedRows(["C10", "C20"], ["555-0100", "555-0100"]));
  // Deliberately faulty propagation: C20 and the entire S2 schedule are omitted.
  lab.schedules.updateOne({_id: "S1/T1"}, {$set: {"enrollments.$[e].currentPhone": "555-0199"}},
    {arrayFilters: [{"e.teacherId": "T7", "e.courseId": "C10"}]});
  same("embedded_missed_C20", embeddedRows("S1"), expectedRows(["C10", "C20"], ["555-0199", "555-0100"]));
  same("embedded_missed_S2", embeddedRows("S2"), expectedRows(["C10"], ["555-0100"]));
  const repair = lab.schedules.updateMany({"enrollments.teacherId": "T7"},
    {$set: {"enrollments.$[e].currentPhone": "555-0199"}}, {arrayFilters: [{"e.teacherId": "T7"}]});
  same("repair_modified_documents", repair.modifiedCount, 2);
  same("embedded_repaired_S1", embeddedRows("S1"), referencedRows("S1"));
  same("embedded_repaired_S2", embeddedRows("S2"), referencedRows("S2"));
  same("reference_snapshots", lab.enrollments.find().sort({_id: 1}).toArray().map(x => x.teacherPhoneAtEnrollment),
    ["555-0100", "555-0100", "555-0100"]);
  same("embedded_snapshots", lab.schedules.aggregate([
    {$sort: {_id: 1}}, {$unwind: "$enrollments"},
    {$project: {_id: 0, snapshot: "$enrollments.teacherPhoneAtEnrollment"}}
  ]).toArray().map(x => x.snapshot), ["555-0100", "555-0100", "555-0100"]);
  print(JSON.stringify({status: "PASS", checks,
    boundary: "finite sequential fixture; no concurrency, transaction, performance or failover test"}));
} finally {
  const cleanup = lab.dropDatabase();
  if (cleanup.ok !== 1) throw new Error("Temporary database cleanup failed");
  print(JSON.stringify({removedTemporaryDatabase: labName}));
}
