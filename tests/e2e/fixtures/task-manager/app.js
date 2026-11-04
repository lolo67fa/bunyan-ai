// QA harness fixture: a hand-written Task Manager that follows the proposed
// data-testid rules. NOT the Developer agent's output. See index.html.

const STORAGE_KEY = 'bunyan_task';
const BUG = new URLSearchParams(location.search).get('bug'); // 'no-persist' simulates a storage defect

const FIELDS = [
  { name: 'title', label: 'Title', input: 'text', required: true, min_length: 3, max_length: 100 },
  { name: 'description', label: 'Description', input: 'textarea', required: false, max_length: 1000 },
  { name: 'due_date', label: 'Due date', input: 'date', required: false, not_in_past: true },
  { name: 'priority', label: 'Priority', input: 'select', required: true, default: 'medium',
    options: [['low', 'Low'], ['medium', 'Medium'], ['high', 'High']] },
  { name: 'status', label: 'Status', input: 'select', required: true, default: 'to_do',
    options: [['to_do', 'To do'], ['in_progress', 'In progress'], ['done', 'Done']] },
];
const COLUMNS = ['title', 'due_date', 'priority', 'status'];

let memory = [];
let editingId = null;

const $ = (id) => document.getElementById(id);

function load() {
  if (BUG === 'no-persist') return memory;
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; } catch { return []; }
}
function store(records) {
  memory = records;
  if (BUG !== 'no-persist') localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function label(field, value) {
  const opt = field.options?.find(([v]) => v === value);
  return opt ? opt[1] : value ?? '';
}

function toast(text) {
  const t = $('toast');
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 2000);
}

function el(tag, attrs = {}, text) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text != null) node.textContent = text;
  return node;
}

function renderList() {
  const records = load();
  const tbody = $('rows');
  tbody.replaceChildren();
  for (const r of records) {
    const tr = el('tr', { 'data-testid': 'record-row', 'data-id': r.id });
    for (const name of COLUMNS) {
      const field = FIELDS.find((f) => f.name === name);
      tr.append(el('td', { 'data-testid': `cell-${name}` }, label(field, r[name])));
    }
    const actions = el('td');
    const edit = el('button', { type: 'button', 'data-testid': 'btn-edit' }, 'Edit');
    edit.onclick = () => openForm(r);
    const del = el('button', { type: 'button', 'data-testid': 'btn-delete' }, 'Delete');
    del.onclick = () => {
      if (actions.querySelector('.confirm')) return;
      const box = el('span', { class: 'confirm' });
      box.append(el('span', {}, `Delete “${r.title}”?`));
      const yes = el('button', { type: 'button', 'data-testid': 'btn-confirm-delete' }, 'Confirm delete');
      const no = el('button', { type: 'button', 'data-testid': 'btn-cancel-delete' }, 'Keep');
      yes.onclick = () => { store(load().filter((x) => x.id !== r.id)); toast('Deleted'); renderList(); };
      no.onclick = () => box.remove();
      box.append(yes, no);
      actions.append(box);
    };
    actions.append(edit, del);
    tr.append(actions);
    tbody.append(tr);
  }
  $('empty-state').hidden = records.length > 0;
}

function openForm(record) {
  editingId = record ? record.id : null;
  const form = $('form');
  form.replaceChildren();
  for (const f of FIELDS) {
    const wrap = el('label', {}, f.label + (f.required ? ' *' : ''));
    let input;
    if (f.input === 'select') {
      input = el('select');
      for (const [v, l] of f.options) input.append(el('option', { value: v }, l));
    } else if (f.input === 'textarea') {
      input = el('textarea');
    } else {
      input = el('input', { type: f.input });
    }
    input.setAttribute('data-testid', `input-${f.name}`);
    input.name = f.name;
    input.value = record ? record[f.name] ?? '' : f.default ?? '';
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
  for (const f of FIELDS) {
    const v = (values[f.name] ?? '').trim();
    if (f.required && !v) errors[f.name] = 'This field is required';
    else if (v && f.min_length && v.length < f.min_length) errors[f.name] = `At least ${f.min_length} characters`;
    else if (v && f.max_length && v.length > f.max_length) errors[f.name] = `At most ${f.max_length} characters`;
    else if (v && f.not_in_past && v < today()) errors[f.name] = 'Date cannot be in the past';
  }
  return errors;
}

function save() {
  const values = {};
  for (const f of FIELDS) values[f.name] = document.querySelector(`[data-testid="input-${f.name}"]`).value;
  const errors = validate(values);
  for (const f of FIELDS) {
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
    toast('Changes saved');
  } else {
    records.push({ id: crypto.randomUUID(), ...values, created_at: now, updated_at: now });
    toast('Added successfully');
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

$('btn-add').onclick = () => openForm(null);
$('btn-save').onclick = save;
$('btn-cancel').onclick = closeForm;
renderList();
