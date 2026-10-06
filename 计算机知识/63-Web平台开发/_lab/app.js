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
