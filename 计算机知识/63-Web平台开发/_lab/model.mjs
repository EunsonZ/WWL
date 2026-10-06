// Pure boundary validation + asynchronous coordinator; DOM belongs to app.js.
export class PayloadError extends Error {}
export class HttpError extends Error {
  constructor(status) { super(`HTTP ${status}`); this.status = status; }
}
export function normalizeQuery(value) {
  if (typeof value !== 'string') throw new TypeError('关键词必须是字符串');
  const q = value.trim();
  if (q.length < 1 || q.length > 80) throw new RangeError('关键词去掉两端空白后须有1–80个UTF-16代码单元');
  return q;
}
export function validateCourses(value) {
  if (!value || !Array.isArray(value.courses) || value.courses.length > 100) throw new PayloadError('courses必须是最多100项的数组');
  const seen = new Set();
  return value.courses.map(c => {
    if (!c || typeof c.id !== 'string' || !/^[a-z0-9-]{1,40}$/.test(c.id) || seen.has(c.id)
      || typeof c.title !== 'string' || !c.title.trim() || c.title.length > 120
      || !Number.isInteger(c.minutes) || c.minutes < 1 || c.minutes > 240
      || !['basic', 'core', 'advanced'].includes(c.level)) throw new PayloadError('课程字段或唯一id无效');
    seen.add(c.id);
    return Object.freeze({ id: c.id, title: c.title, minutes: c.minutes, level: c.level });
  });
}
export function toggleReading(list, course) {
  const checked = validateCourses({courses: [course]})[0];
  return list.some(c => c.id === checked.id) ? list.filter(c => c.id !== checked.id) : [...list, checked];
}
const scenarios = ['success', 'slow', 'http-error', 'drop', 'bad-json', 'bad-data'];
export class QueryMachine {
  constructor(transport = globalThis.fetch, onChange = () => {}) {
    this.transport = transport; this.onChange = onChange; this.generation = 0; this.controller = null;
    this.state = Object.freeze({status: 'idle', query: '', scenario: 'success', courses: [], error: null});
  }
  publish(state) { this.state = Object.freeze(state); this.onChange(this.state); }
  async run(value, scenario = 'success') {
    // Invalid intent does not supersede an already valid in-flight query.
    const query = normalizeQuery(value);
    if (!scenarios.includes(scenario)) throw new RangeError('未知接口场景');
    const ticket = ++this.generation;
    this.controller?.abort();
    const controller = new AbortController(); this.controller = controller;
    this.publish({status: 'loading', query, scenario, courses: [], error: null});
    try {
      const params = new URLSearchParams({q: query, scenario});
      const response = await this.transport(`/api/courses?${params}`, {signal: controller.signal});
      if (!response.ok) throw new HttpError(response.status);
      let body;
      try { body = await response.json(); }
      catch (error) {
        if (controller.signal.aborted || !(error instanceof SyntaxError)) throw error;
        throw new PayloadError('JSON无法解析');
      }
      const courses = validateCourses(body);
      if (ticket !== this.generation) return;
      this.publish({status: 'success', query, scenario, courses, error: null});
    } catch (error) {
      if (ticket !== this.generation) return;
      if (controller.signal.aborted) {
        this.publish({status: 'cancelled', query, scenario, courses: [], error: null});
      } else {
        const kind = error instanceof HttpError ? 'http' : error instanceof PayloadError ? 'payload' : 'network';
        this.publish({status: 'error', query, scenario, courses: [], error: {kind, status: error.status ?? null}});
      }
    } finally { if (ticket === this.generation) this.controller = null; }
  }
  cancel() {
    if (this.state.status !== 'loading') return;
    ++this.generation; this.controller?.abort(); this.controller = null;
    this.publish({...this.state, status: 'cancelled', courses: [], error: null});
  }
}
