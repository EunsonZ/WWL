---
type: lab
stage: 0
aliases: []
prerequisites:
  - "[[计算机知识/63-Web平台开发/03-Fetch请求取消与陈旧响应]]"
sources:
  - https://html.spec.whatwg.org/multipage/forms.html
  - https://dom.spec.whatwg.org/#concept-event-dispatch
  - https://fetch.spec.whatwg.org/#abort-fetch
---
# 可交互Web小项目：课程查询与阅读列表

**想观察“文档→事件→模型→真实请求→界面”的完整小切片，从这里开始。** 四门课程、分钟和故障是原创合成材料。默认Web查询返回web-doc 35分钟与web-state 50分钟；网络返回network 45分钟；查询不存在关键词成功返回空数组。阅读列表只在当前页面内存中，刷新清空。

## 显式启动与停止

从本页所在目录进入 `_lab`，用已有Python 3标准库运行，不安装依赖。此服务只绑定127.0.0.1，默认600秒后自动退出，Ctrl+C可提前终止；不自启动，不注册后台服务。如果8763已占用，选另一个空闲端口或 `--port 0`，以终端打印的URL为准。

```bash
cd _lab
python3 -B server.py --port 8763 --duration 600
```

在实际浏览器打开 `http://127.0.0.1:8763/`。通过同一来源提供HTML、模块、CSS与 `/api/courses`，避免把file页面误当能访问此接口。静态路由白名单只公开index.html、app.js、model.mjs、styles.css；不会公开server.py、测试或上级库文件。服务器是教学服务，没有账户、持久化、TLS、授权、生产资源隔离或服务端写请求。

另一个终端可运行纯模型测试，无须先启动HTTP服务：

```bash
node --test test_model.mjs
```

源码分工：index.html定义原生控件；styles.css定义盒/Flex/Grid与可见焦点；app.js处理事件、阅读列表与焦点；model.mjs验证网络数据并协调请求；server.py提供有限loopback接口；test_model.mjs独立控制先后与边界。源码是真源，下面code-sync块保持完整镜像，修改须同时更新。

## 按现象做实验

| 操作 | 应观察到的结果 | 对应解释 |
| --- | --- | --- |
| 保持Web正常查询，选两门，再移出35分钟课程 | 返回2门；总量0→35→85→50；动作名称与列表一致 | [[计算机知识/63-Web平台开发/02-DOM事件委托与界面状态\|单向状态]] |
| 输入只有空格并提交 | 错误解释规则，输入保留，焦点回输入；已有合法请求不因此失效 | [[计算机知识/63-Web平台开发/01-HTML语义表单与CSS布局焦点\|表单约束与业务验证]] |
| slow查询后两秒内取消 | 立即报告停止等待；旧响应不回写；阅读列表保留 | [[计算机知识/63-Web平台开发/03-Fetch请求取消与陈旧响应\|取消与发布代号]] |
| slow Web后立刻改为正常网络并提交 | 最终显示network，旧Web无权覆盖 | [[计算机知识/63-Web平台开发/03-Fetch请求取消与陈旧响应\|异步时间线]] |
| 503、断连、错误JSON、错误字段分别查询 | HTTP、连接、格式的恢复文字区分；503不是200成功 | [[计算机知识/63-Web平台开发/03-Fetch请求取消与陈旧响应\|三层成功条件]] |
| 503后点重试，再改正常并提交 | 重试仍查上次503场景；新正常意图才恢复 | [[计算机知识/63-Web平台开发/04-Web交付验证与平台边界\|动作与证据]] |
| 删除阅读列表中间、末项、最后一项 | 焦点依次到下一项、前一项、阅读列表标题 | [[计算机知识/63-Web平台开发/02-DOM事件委托与界面状态\|动态焦点]] |

**练习：**让transport完全忽略abort，先后提交A、B并使B先成功，A后成功。最终可以有A吗？答案：不可以，ticket代号控制发布，资源取消不是唯一防线。测试文件还覆盖A先完成的另一顺序以及头/体分开完成。

## 执行证据与未验证范围

2026-09-17作者在Node v26.8.1执行 `node --test test_model.mjs`：9项通过，包括UTF-16长度、无效字段、三门8子集不变量、两种完成顺序、陈旧响应体和错误、显式取消与旧成功、观察signal的transport、HTTP/网络/体流/格式错误与恢复、无效意图保留当前合法请求。`node --check app.js`与 `node --check model.mjs`解析通过。测试采用注入transport控制异步顺序，未装DOM模拟器。

作者另显式启动随机空闲端口的30秒loopback服务，以HTTP客户端完成10项实际检查：页面与三项资源、非白名单与上级路径404、Web两门、503、无效关键词400、slow实际等待约2秒。Node原生Fetch连接同一服务完成8组检查：正常/空结果、4种错误、等待100ms后取消、等待100ms后新意图替代旧意图。最终query为网络、id为network；服务在检查结束的finally中终止，没有留下常驻进程。短期自动退出另以duration=1观察实际退出。候选冻结哈希与命令输出保存在本批库外证据，由发布者留一个实际结果指针。

这些是模型与真实loopback接口证据。作者未执行实际浏览器、读屏、真实用户研究或Obsidian显示验收；浏览器后续结果由发布者单独记录，不能用本节替代。未声称WCAG符合性、全部平台覆盖、生产部署、安全全审或人已掌握。[HTML表单规范](https://html.spec.whatwg.org/multipage/forms.html)、[DOM规范](https://dom.spec.whatwg.org/#concept-event-dispatch)与[Fetch规范](https://fetch.spec.whatwg.org/#abort-fetch)给平台核查依据；项目与故障数据为教学构造。

返回 [[计算机知识/63-Web平台开发/00-Web平台开发-MOC|Web路线入口]]。

## 源码完整镜像

### index.html

<!-- code-sync: ./_lab/index.html -->
```html
<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>课程查询与阅读列表 · Web实验</title><link rel="stylesheet" href="styles.css">
<script type="module" src="app.js"></script></head>
<body><a class="skip" href="#main">跳到查询</a>
<header><p>原创合成课程 · 同源请求实验</p><h1>课程查询与阅读列表</h1>
<p>输入“Web”“状态”或“网络”。列表只保存在此页面内存，刷新会清空。</p></header>
<main id="main"><form id="search" action="/api/courses" method="get">
<label for="query">课程关键词</label><input id="query" name="q" required maxlength="80" value="Web" aria-describedby="query-help query-error">
<p id="query-help">去掉两端空白后须有1–80个UTF-16代码单元。支持中文与英文关键词。</p>
<p id="query-error" class="error"></p>
<label for="scenario">接口场景（教学故障注入）</label><select id="scenario" name="scenario">
<option value="success">正常响应</option><option value="slow">慢响应（2秒）</option>
<option value="http-error">HTTP 503</option><option value="drop">断开连接</option>
<option value="bad-json">JSON语法错误</option><option value="bad-data">JSON字段错误</option></select>
<div class="actions"><button type="submit">查询</button><button id="cancel" type="button" disabled>取消当前查询</button>
<button id="retry" type="button" hidden>重试上次查询</button></div></form>
<p id="status" role="status" aria-atomic="true">尚未查询。</p>
<div class="columns"><section id="results-region" aria-labelledby="results-heading" aria-busy="false">
<h2 id="results-heading" tabindex="-1">查询结果</h2><ul id="results" class="cards"></ul></section>
<section aria-labelledby="reading-heading"><h2 id="reading-heading" tabindex="-1">阅读列表</h2>
<p id="reading-count">0门，合计0分钟</p><ul id="reading" class="cards"></ul></section></div>
<noscript>此交互实验需要JavaScript。表单仍可发送GET请求，但不会更新页面内存阅读列表。</noscript></main>
<footer><p>这是短期loopback教学服务，未实现账户、持久化、TLS或服务端写入。</p></footer></body></html>
```

### styles.css

<!-- code-sync: ./_lab/styles.css -->
```css
* { box-sizing: border-box; }
body { margin: 0; background: #f5f7fa; color: #152238; font: 1rem/1.65 system-ui, sans-serif; }
header, main, footer { max-width: 70rem; margin: auto; padding: 1.2rem; }
header p:first-child { color: #36536f; }
h1 { line-height: 1.25; } h2 { margin-top: 0; }
form, section { background: white; padding: 1.2rem; border: 1px solid #c5ceda; border-radius: .7rem; min-width: 0; }
label { display: block; font-weight: 650; }
input, select, button { font: inherit; }
input, select { width: 100%; padding: .5rem; border: 1px solid #627287; border-radius: .3rem; }
button { padding: .5rem .8rem; border: 1px solid #255485; border-radius: .3rem; background: #164c83; color: white; cursor: pointer; }
button:disabled { background: #e7edf3; color: #465568; border-color: #9cabbc; cursor: default; }
.actions { display: flex; flex-wrap: wrap; gap: .6rem; margin-top: 1rem; }
.columns { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 1rem; }
.cards { list-style: none; padding: 0; margin: 0; }
.cards li { padding: .8rem 0; border-bottom: 1px solid #ccd4df; overflow-wrap: anywhere; }
.cards h3 { margin: 0; font-size: 1.1rem; }.cards p { margin: .3rem 0; }
.error { color: #9e1f19; }[aria-invalid="true"] { border: 2px solid #9e1f19; }
:focus-visible { outline: 3px solid #9e4700; outline-offset: 3px; }
.skip { position: absolute; left: 1rem; top: -6rem; background: white; padding: .5rem; }.skip:focus { top: .2rem; }
#status { min-height: 1.7rem; }
@media (max-width: 45rem) { .columns { grid-template-columns: minmax(0, 1fr); } }
```

### app.js

<!-- code-sync: ./_lab/app.js -->
```javascript
import { QueryMachine, normalizeQuery, toggleReading } from './model.mjs';
const $ = id => document.getElementById(id);
const form = $('search'), query = $('query'), results = $('results'), reading = $('reading');
let readingList = [];
const levels = {basic: '入门', core: '核心', advanced: '进阶'};
function card(course, action) {
  const li = document.createElement('li');
  const h = document.createElement('h3'); h.textContent = course.title;
  const p = document.createElement('p'); p.textContent = `${levels[course.level]} · ${course.minutes}分钟`;
  const button = document.createElement('button'); button.type = 'button';
  button.dataset.action = action; button.dataset.id = course.id;
  li.append(h, p, button); return li;
}
function updateResultButtons() {
  for (const button of results.querySelectorAll('button')) {
    const course = machine.state.courses.find(c => c.id === button.dataset.id);
    const saved = readingList.some(c => c.id === course.id);
    button.textContent = `${saved ? '移出阅读列表' : '加入阅读列表'}：${course.title}`;
  }
}
function renderReading() {
  reading.replaceChildren(...readingList.map(c => {
    const li = card(c, 'remove'); li.querySelector('button').textContent = `移除：${c.title}`; return li;
  }));
  $('reading-count').textContent = `${readingList.length}门，合计${readingList.reduce((sum, c) => sum + c.minutes, 0)}分钟`;
  updateResultButtons();
}
function renderQuery(state) {
  // Save identity before replacement. Never steal focus from unrelated input.
  const activeCancel = document.activeElement === $('cancel');
  const activeResult = results.contains(document.activeElement);
  const activeId = activeResult ? document.activeElement.dataset.id : null;
  results.replaceChildren(...state.courses.map(c => card(c, 'toggle')));
  updateResultButtons();
  $('cancel').disabled = state.status !== 'loading';
  $('retry').hidden = state.status !== 'error';
  $('results-region').setAttribute('aria-busy', String(state.status === 'loading'));
  const errors = {http: `HTTP ${state.error?.status}：未取得课程，可重试读取。`, network: '连接失败：未取得响应，可重试读取。', payload: '响应格式不符合约定，重试不保证修复。'};
  $('status').textContent = ({idle: '尚未查询。', loading: `正在查询“${state.query}”，可取消或提交另一查询。`,
    success: `“${state.query}”返回${state.courses.length}门课程。`, cancelled: '已停止等待本次查询。阅读列表保留。', error: errors[state.error?.kind]})[state.status];
  if (activeResult) {
    const replacement = [...results.querySelectorAll('button')].find(b => b.dataset.id === activeId);
    (replacement ?? $('results-heading')).focus();
  }
  if (activeCancel && $('cancel').disabled) query.focus();
}
const machine = new QueryMachine(globalThis.fetch.bind(globalThis), renderQuery);
form.addEventListener('submit', event => {
  event.preventDefault();
  try {
    const q = normalizeQuery(query.value); query.removeAttribute('aria-invalid'); $('query-error').textContent = '';
    void machine.run(q, $('scenario').value);
  } catch (error) {
    query.setAttribute('aria-invalid', 'true'); $('query-error').textContent = error.message; query.focus();
  }
});
query.addEventListener('input', () => { query.removeAttribute('aria-invalid'); $('query-error').textContent = ''; });
$('cancel').addEventListener('click', () => { machine.cancel(); query.focus(); });
$('retry').addEventListener('click', () => {
  const {query: oldQuery, scenario} = machine.state;
  query.focus(); void machine.run(oldQuery, scenario);
});
results.addEventListener('click', event => {
  const button = event.target instanceof Element ? event.target.closest('button[data-action="toggle"]') : null;
  if (!button || !results.contains(button)) return;
  const course = machine.state.courses.find(c => c.id === button.dataset.id);
  if (!course) return;
  const wasSaved = readingList.some(c => c.id === course.id);
  readingList = toggleReading(readingList, course); renderReading();
  $('status').textContent = `${course.title}已${wasSaved ? '移出' : '加入'}阅读列表。`;
});
reading.addEventListener('click', event => {
  const button = event.target instanceof Element ? event.target.closest('button[data-action="remove"]') : null;
  if (!button || !reading.contains(button)) return;
  const index = readingList.findIndex(c => c.id === button.dataset.id);
  if (index < 0) return;
  const course = readingList[index]; readingList = toggleReading(readingList, course); renderReading();
  const buttons = reading.querySelectorAll('button');
  (buttons[Math.min(index, buttons.length - 1)] ?? $('reading-heading')).focus();
  $('status').textContent = `${course.title}已移除，剩余${readingList.length}门。`;
});
```

### model.mjs

<!-- code-sync: ./_lab/model.mjs -->
```javascript
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
```

### test_model.mjs

<!-- code-sync: ./_lab/test_model.mjs -->
```javascript
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
```

### server.py

<!-- code-sync: ./_lab/server.py -->
```python
"""Explicitly started, finite loopback demo. No accounts or persistent writes."""
import argparse
import json
from pathlib import Path
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from urllib.parse import parse_qs, urlsplit

CATALOG = [
    {"id": "web-doc", "title": "Web文档与语义表单", "minutes": 35, "level": "basic"},
    {"id": "web-state", "title": "Web事件与界面状态", "minutes": 50, "level": "core"},
    {"id": "network", "title": "网络请求与取消边界", "minutes": 45, "level": "core"},
    {"id": "layout", "title": "响应式布局与焦点", "minutes": 30, "level": "basic"},
]
STATIC = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"),
          "/app.js": ("app.js", "text/javascript"), "/model.mjs": ("model.mjs", "text/javascript"),
          "/styles.css": ("styles.css", "text/css")}
ROOT = Path(__file__).resolve().parent

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, kind="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Expected when client cancels the slow demonstration.

    def do_GET(self):
        if len(self.path) > 4096:
            self.reply(414, b'{"error":"URL too long"}')
            return
        path = urlsplit(self.path)
        if path.path in STATIC:
            file, kind = STATIC[path.path]
            self.reply(200, (ROOT / file).read_bytes(), kind)
            return
        if path.path != "/api/courses":
            self.reply(404, b'{"error":"not found"}')
            return
        params = parse_qs(path.query, keep_blank_values=True)
        q = params.get("q", [""])[0].strip(" \t\n\r\v\f\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff")
        scenario = params.get("scenario", ["success"])[0]
        # HTML maxlength and JS String.length use UTF-16 code units.
        units = len(q.encode("utf-16-le")) // 2
        if not 1 <= units <= 80 or scenario not in {"success", "slow", "http-error", "drop", "bad-json", "bad-data"}:
            self.reply(400, b'{"error":"invalid query or scenario"}')
            return
        if scenario == "slow":
            time.sleep(2)
        if scenario == "drop":
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        if scenario == "http-error":
            self.reply(503, b'{"error":"teaching outage"}')
            return
        if scenario == "bad-json":
            self.reply(200, b'{')
            return
        if scenario == "bad-data":
            self.reply(200, b'{"courses":[{"id":"x","minutes":-1}]}')
            return
        matches = [c for c in CATALOG if q.casefold() in c["title"].casefold()]
        self.reply(200, json.dumps({"courses": matches}, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # Queries are not recorded by this teaching server.

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8763)
    parser.add_argument("--duration", type=int, default=600, help="Stop after 1–3600 seconds")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535 or not 1 <= args.duration <= 3600:
        parser.error("port must be 0–65535; duration must be 1–3600")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    timer = threading.Timer(args.duration, server.shutdown)
    timer.daemon = True
    timer.start()
    print(f"http://127.0.0.1:{server.server_port}/ (stops after {args.duration}s)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        timer.cancel()
        server.server_close()
```
