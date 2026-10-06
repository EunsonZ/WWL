const assert = require("node:assert/strict");

assert.equal(/^\w+$/.test("中文"), false);
assert.equal(/^\d+$/.test("１２３"), false);
assert.equal(/^[A-Za-z0-9_]+$/.test("中文"), false);
assert.equal(/^.$/.test("🙂"), false);
assert.equal(/^.$/u.test("🙂"), true);
assert.equal(/^.$/u.test("e\u0301"), false);
assert.equal("é".normalize("NFC"), "e\u0301".normalize("NFC"));

const date = /^(?<year>[0-9]{4})-(?<month>[0-9]{2})-(?<day>[0-9]{2})$/;
const match = date.exec("2026-08-31");
assert.notEqual(match, null);
assert.deepEqual({ ...match.groups }, { year: "2026", month: "08", day: "31" });
assert.equal("2026-08-31".replace(date, "$<day>/$<month>/$<year>"), "31/08/2026");

const stateful = /ERR-[0-9]{3}/g;
assert.equal(stateful.test("ERR-404"), true);
assert.equal(stateful.test("ERR-404"), false);
stateful.lastIndex = 0;
assert.equal(stateful.test("ERR-404"), true);

console.log(`Node ${process.version} regex difference assertions: passed`);
