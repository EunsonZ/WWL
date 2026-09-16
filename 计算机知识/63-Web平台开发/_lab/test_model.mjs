import test from 'node:test';
import assert from 'node:assert/strict';
import {QueryMachine, normalizeQuery, validateCourses, toggleReading, PayloadError} from './model.mjs';
const course = (id, minutes = 35) => ({id, title: id, minutes, level: 'core'});
const response = courses => ({ok: true, json: async () => ({courses})});
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}
test('query limits use UTF-16; invalid forms are rejected', () => {
  assert.equal(normalizeQuery('  Web  '), 'Web');
  assert.equal(normalizeQuery('😀'.repeat(40)).length, 80);
  for (const q of ['', '  ', '😀'.repeat(41), null, 4]) assert.throws(() => normalizeQuery(q));
});
test('boundary rejects shape, duplicate identity, invalid numeric units', () => {
  assert.deepEqual(validateCourses({courses: []}), []);
  assert.deepEqual(validateCourses({courses: [course('a')]}), [course('a')]);
  for (const body of [{}, {courses: [course('a'), course('a')]},
    {courses: [course('a', NaN)]}, {courses: [course('a', Infinity)]},
    {courses: [course('a', 0)]}, {courses: [course('a', 1.5)]},
    {courses: [course('<x>')]}, {courses: Array.from({length: 101}, (_, i) => course(`c${i}`))}]) {
    assert.throws(() => validateCourses(body), PayloadError);
  }
});
test('all subsets and twice-toggle preserve unique identities and total', () => {
  const catalog = [course('a', 10), course('b', 20), course('c', 30)];
  for (let mask = 0; mask < 8; mask++) {
    const list = catalog.filter((_, i) => (mask >> i) & 1);
    for (const c of catalog) {
      const once = toggleReading(list, c), twice = toggleReading(once, c);
      assert.deepEqual(new Set(twice.map(c => c.id)), new Set(list.map(c => c.id)));
      assert.equal(new Set(once.map(c => c.id)).size, once.length);
      const expected = list.reduce((s, x) => s + x.minutes, 0) + (list.includes(c) ? -c.minutes : c.minutes);
      assert.equal(once.reduce((s, x) => s + x.minutes, 0), expected);
    }
  }
});
test('all completion orders accept only most recent intent even transport ignores abort', async () => {
  for (const order of [[0, 1], [1, 0]]) {
    const requests = [deferred(), deferred()]; let calls = 0;
    const machine = new QueryMachine(() => requests[calls++].promise);
    const runs = [machine.run('old'), machine.run('new')];
    for (const i of order) { requests[i].resolve(response([course(`r${i}`)])); await runs[i]; }
    assert.equal(machine.state.query, 'new');
    assert.deepEqual(machine.state.courses.map(c => c.id), ['r1']);
  }
});
test('stale body after headers and stale rejection cannot overwrite new result', async () => {
  const body = deferred(), failure = deferred(); let calls = 0;
  const machine = new QueryMachine(() => {
    calls++;
    return calls === 1 ? Promise.resolve({ok: true, json: () => body.promise})
      : calls === 2 ? failure.promise : Promise.resolve(response([course('latest')]));
  });
  const old = machine.run('old'); await Promise.resolve();
  const middle = machine.run('middle'); await machine.run('latest');
  body.resolve({courses: [course('old')]}); failure.reject(new TypeError('connection lost'));
  await Promise.all([old, middle]);
  assert.equal(machine.state.status, 'success');
  assert.equal(machine.state.courses[0].id, 'latest');
});
test('explicit cancel is immediate and late success remains ignored', async () => {
  const request = deferred(); let signal;
  const machine = new QueryMachine((_, options) => {signal = options.signal; return request.promise;});
  const pending = machine.run('slow'); machine.cancel();
  assert.equal(signal.aborted, true); assert.equal(machine.state.status, 'cancelled');
  request.resolve(response([course('late')])); await pending;
  assert.equal(machine.state.status, 'cancelled'); assert.deepEqual(machine.state.courses, []);
});
test('abort-aware transport rejects and no error flashes after supersession', async () => {
  let calls = 0; const states = [];
  const machine = new QueryMachine((_, {signal}) => ++calls === 1
    ? new Promise((_, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))))
    : Promise.resolve(response([course('new')])), s => states.push(s.status));
  const old = machine.run('old'); await machine.run('new'); await old;
  assert.deepEqual(states, ['loading', 'loading', 'success']);
});
test('HTTP, network, JSON syntax and field failure stay distinct; retry can recover', async () => {
  const cases = [
    [async () => ({ok: false, status: 503}), 'http'],
    [async () => {throw new TypeError('offline');}, 'network'],
    [async () => ({ok: true, json: async () => {throw new SyntaxError('bad json');}}), 'payload'],
    [async () => response([course('bad', -3)]), 'payload'],
    [async () => ({ok: true, json: async () => {throw new TypeError('body stream broken');}}), 'network']
  ];
  for (const [transport, expected] of cases) {
    let first = true;
    const machine = new QueryMachine((...args) => {if (first) {first = false; return transport(...args);} return Promise.resolve(response([]));});
    await machine.run('Web'); assert.equal(machine.state.status, 'error'); assert.equal(machine.state.error.kind, expected);
    await machine.run(machine.state.query); assert.equal(machine.state.status, 'success');
  }
});
test('invalid new intent leaves valid current request in place', async () => {
  const request = deferred(); const machine = new QueryMachine(() => request.promise);
  const pending = machine.run('valid');
  await assert.rejects(machine.run('   '), RangeError);
  assert.equal(machine.state.status, 'loading');
  request.resolve(response([course('valid')])); await pending;
  assert.equal(machine.state.courses[0].id, 'valid');
});
