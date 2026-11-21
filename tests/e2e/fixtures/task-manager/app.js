// QA harness fixture: a small CRUD app driven by architecture.json (contract 0.3.0),
// following the data-testid rules (§5) and messages (§6). It is NOT the Developer
// agent's template and passing tests here does NOT prove a generated app works.
//
// lib/serve.js serves the architecture given to the suite at /architecture.json.
// Without one, the built-in Task Manager below is used.
//
// Simulated defects for checking the suite itself (add to the URL):
//   ?bug=no-persist       records are not written to localStorage
//   ?bug=wrong-text       buttons and messages ignore the verbatim texts
//   ?bug=no-format        numbers ignore display_format
//   ?bug=no-empty-option  required selects without a default are pre-selected

const BUG = new URLSearchParams(location.search).get('bug');

const FALLBACK = {
  app: { name: 'Task Manager', language: 'en', direction: 'ltr' },
  entity: {
    name: 'Task', label: 'Task', plural_label: 'Tasks', display_field: 'title',
    storage: { key: 'bunyan_task' },
    fields: [
      { name: 'title', label: 'Title', type: 'string', input: 'text', required: true,
        validation: { min_length: 3, max_length: 100 },
        messages: { required: 'Title is required', min_length: 'Title must be at least 3 characters',
          max_length: 'Title must be at most 100 characters' } },
      { name: 'description', label: 'Description', type: 'text', input: 'textarea', required: false,
        validation: { max_length: 1000 }, messages: { max_length: 'Description must be at most 1000 characters' } },
      { name: 'due_date', label: 'Due date', type: 'date', input: 'date', required: false,
        validation: { date_constraint: 'not_in_past' }, messages: { date_constraint: 'Due date cannot be in the past' } },
      { name: 'priority', label: 'Priority', type: 'enum', input: 'select', required: true, default: 'medium',
        options: [{ value: 'low', label: 'Low' }, { value: 'medium', label: 'Medium' }, { value: 'high', label: 'High' }],
        validation: {}, messages: { required: 'Priority is required' } },
      { name: 'status', label: 'Status', type: 'enum', input: 'select', required: true, default: 'to_do',
        options: [{ value: 'to_do', label: 'To do' }, { value: 'in_progress', label: 'In progress' },
          { value: 'done', label: 'Done' }],
        validation: {}, messages: { required: 'Status is required' } },
    ],
  },
  screens: [
    { id: 'list', components: [{ type: 'add_button', label: 'Add Task' },
      { type: 'table', columns: ['title', 'due_date', 'priority', 'status'] }] },
    { id: 'form', components: [{ type: 'save_button', label: 'Save' }, { type: 'cancel_button', label: 'Cancel' }] },
  ],
  messages: {
    empty: 'No records yet.', created: 'Added successfully', updated: 'Changes saved', deleted: 'Deleted',
    confirm_delete: 'Delete “{display}”?', confirm_button: 'Confirm delete', cancel_delete_button: 'Keep',
    edit_button: 'Edit', delete_button: 'Delete',
  },
};

let A; // the architecture in use
let memory = [];
let editingId = null;

const $ = (id) => document.getElementById(id);
const component = (screenId, type) =>
  A.screens.find((s) => s.id === screenId)?.components.find((c) => c.type === type) || {};
const text = (value, fallback) => (BUG === 'wrong-text' ? `${fallback}!` : value ?? fallback);

function el(tag, attrs = {}, content) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (content != null) node.textContent = content;
  return node;
}

function load() {
  if (BUG === 'no-persist') return memory;
  try { return JSON.parse(localStorage.getItem(A.entity.storage.key)) || []; } catch { return []; }
}

function store(records) {
  memory = records;
  if (BUG !== 'no-persist') localStorage.setItem(A.entity.storage.key, JSON.stringify(records));
}

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** What a cell shows: the option label for enums, display_format for numbers. */
function display(field, value) {
  if (value == null || value === '') return '';
  if (field.options) return field.options.find((o) => o.value === value)?.label ?? value;
  if (field.display_format && BUG !== 'no-format') return Number(value).toFixed(field.display_format.decimals);
  return String(value);
}

function toast(message) {
  const t = $('toast');
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 2000);
}

function renderList() {
  const records = load();
  const columns = component('list', 'table').columns;
  const headRow = $('head-row');
  headRow.replaceChildren(
    ...columns.map((name) => el('th', {}, A.entity.fields.find((f) => f.name === name).label)),
    el('th'),
  );
  const tbody = $('rows');
  tbody.replaceChildren();
  for (const r of records) {
    const tr = el('tr', { 'data-testid': 'record-row', 'data-id': r.id });
    for (const name of columns) {
      const field = A.entity.fields.find((f) => f.name === name);
      tr.append(el('td', { 'data-testid': `cell-${name}` }, display(field, r[name])));
    }
    const actions = el('td');
    const edit = el('button', { type: 'button', 'data-testid': 'btn-edit' }, text(A.messages.edit_button, 'Edit'));
    edit.onclick = () => openForm(r);
    const del = el('button', { type: 'button', 'data-testid': 'btn-delete' }, text(A.messages.delete_button, 'Delete'));
    del.onclick = () => {
      if (actions.querySelector('.confirm')) return;
      const box = el('span', { class: 'confirm' });
      const question = text(A.messages.confirm_delete, 'Delete “{display}”?').split('{display}').join(r[A.entity.display_field]);
      box.append(el('span', { 'data-testid': 'confirm-delete-text' }, question));
      const yes = el('button', { type: 'button', 'data-testid': 'btn-confirm-delete' }, text(A.messages.confirm_button, 'Confirm delete'));
      const no = el('button', { type: 'button', 'data-testid': 'btn-cancel-delete' }, text(A.messages.cancel_delete_button, 'Keep'));
      yes.onclick = () => { store(load().filter((x) => x.id !== r.id)); toast(A.messages.deleted); renderList(); };
      no.onclick = () => box.remove();
      box.append(yes, no);
      actions.append(box);
    };
    actions.append(edit, del);
    tr.append(actions);
    tbody.append(tr);
  }
  const empty = $('empty-state');
  empty.textContent = text(A.messages.empty, 'No records yet.');
  empty.hidden = records.length > 0;
}

function openForm(record) {
  editingId = record ? record.id : null;
  const form = $('form');
  form.replaceChildren();
  for (const f of A.entity.fields) {
    const wrap = el('label', {}, f.label + (f.required ? ' *' : ''));
    let input;
    if (f.input === 'select') {
      input = el('select');
      if (f.empty_option && BUG !== 'no-empty-option') input.append(el('option', { value: '' }, f.empty_option));
      for (const o of f.options) input.append(el('option', { value: o.value }, o.label));
    } else if (f.input === 'textarea') {
      input = el('textarea');
    } else if (f.input === 'checkbox') {
      input = el('input', { type: 'checkbox' });
    } else {
      input = el('input', { type: f.input });
      if (f.step) input.setAttribute('step', f.step);
    }
    input.setAttribute('data-testid', `input-${f.name}`);
    input.name = f.name;
    const value = record ? record[f.name] : f.default;
    if (input.type === 'checkbox') input.checked = Boolean(value);
    else input.value = value ?? (f.input === 'select' && f.empty_option && BUG !== 'no-empty-option' ? '' : input.value);
    const error = el('span', { class: 'error', 'data-testid': `error-${f.name}` });
    error.hidden = true;
    wrap.append(input, error);
    form.append(wrap);
  }
  $('screen-list').hidden = true;
  $('screen-form').hidden = false;
}

function validate(values) {
  const errors = {};
  for (const f of A.entity.fields) {
    const raw = values[f.name];
    const v = typeof raw === 'string' ? raw.trim() : raw;
    const rules = f.validation || {};
    const m = f.messages || {};
    if (f.required && (v === '' || v == null)) errors[f.name] = m.required;
    else if (v === '' || v == null || typeof v === 'boolean') continue;
    else if (rules.min_length != null && v.length < rules.min_length) errors[f.name] = m.min_length;
    else if (rules.max_length != null && v.length > rules.max_length) errors[f.name] = m.max_length;
    else if (rules.min_value != null && Number(v) < rules.min_value) errors[f.name] = m.min_value;
    else if (rules.max_value != null && Number(v) > rules.max_value) errors[f.name] = m.max_value;
    else if (rules.pattern && !new RegExp(rules.pattern).test(v)) errors[f.name] = m.pattern;
    else if (rules.date_constraint === 'not_in_past' && v.slice(0, 10) < today()) errors[f.name] = m.date_constraint;
    else if (rules.date_constraint === 'not_in_future' && v.slice(0, 10) > today()) errors[f.name] = m.date_constraint;
    if (errors[f.name] !== undefined && BUG === 'wrong-text') errors[f.name] = 'Invalid';
  }
  return errors;
}

function save() {
  const values = {};
  for (const f of A.entity.fields) {
    const input = document.querySelector(`[data-testid="input-${f.name}"]`);
    values[f.name] = input.type === 'checkbox' ? input.checked : input.value;
  }
  const errors = validate(values);
  for (const f of A.entity.fields) {
    const box = document.querySelector(`[data-testid="error-${f.name}"]`);
    box.textContent = errors[f.name] || '';
    box.hidden = !errors[f.name];
  }
  if (Object.keys(errors).length) return;

  const records = load();
  const now = new Date().toISOString();
  if (editingId) {
    const i = records.findIndex((r) => r.id === editingId);
    records[i] = { ...records[i], ...values, updated_at: now };
    toast(A.messages.updated);
  } else {
    records.push({ id: crypto.randomUUID(), ...values, created_at: now, updated_at: now });
    toast(A.messages.created);
  }
  store(records);
  closeForm();
}

function closeForm() {
  editingId = null;
  $('screen-form').hidden = true;
  $('screen-list').hidden = false;
  renderList();
}

async function start() {
  try {
    const res = await fetch('architecture.json', { cache: 'no-store' });
    A = res.ok ? await res.json() : FALLBACK;
  } catch {
    A = FALLBACK;
  }
  document.documentElement.lang = A.app.language;
  document.documentElement.dir = A.app.direction || 'ltr';
  document.title = `${A.app.name} — QA harness fixture`;
  $('app-title').textContent = A.app.name;
  $('btn-add').textContent = component('list', 'add_button').label || `Add ${A.entity.label}`;
  $('btn-save').textContent = text(component('form', 'save_button').label, 'Save');
  $('btn-cancel').textContent = component('form', 'cancel_button').label || 'Cancel';
  $('btn-add').onclick = () => openForm(null);
  $('btn-save').onclick = save;
  $('btn-cancel').onclick = closeForm;
  renderList();
  $('screen-list').hidden = false;
}

start();
