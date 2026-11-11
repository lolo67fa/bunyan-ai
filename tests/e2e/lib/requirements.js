// Reads requirements.json (Ghala's contract) and, when given, architecture.json
// (Naifah's contract, 0.3.0) and derives everything the fixed suite needs:
// entity, fields, which fields to fill, valid sample values, the texts that
// must match verbatim (rule M1) and number display formats.
// Field names are copied from these files, never invented here.

const fs = require('fs');
const path = require('path');

const E2E_DIR = path.resolve(__dirname, '..');
const REPO_DIR = path.resolve(E2E_DIR, '..', '..');

const DEFAULT_REQUIREMENTS = path.join(
  REPO_DIR, 'backend', 'agents', 'business_analyst', 'samples', 'outputs', 'task_manager_en.requirements.json',
);
const DEFAULT_ARCHITECTURE = path.join(
  REPO_DIR, 'backend', 'agents', 'architect', 'samples', 'outputs', 'task_manager_en.architecture.json',
);
const DEFAULT_APP_DIR = path.join(E2E_DIR, 'fixtures', 'task-manager');

const TEXT_TYPES = ['string', 'text', 'email', 'phone', 'url'];
// Required fields of these types can be left empty in a form. A select can be left
// empty only when it has no default (architecture: `empty_option`).
const EMPTIABLE_TYPES = [...TEXT_TYPES, 'integer', 'decimal', 'date', 'time', 'datetime', 'enum'];

// verbatim_messages paths (architecture §6) → the element whose text must match, and
// the check that compares it. Field rules (entity.fields.<f>.messages.required) are
// compared by error_message_visible.
const VERBATIM_TARGETS = {
  'screens.form.save_button': { testid: 'btn-save', check: 'create_item' },
  'messages.delete_button': { testid: 'btn-delete', check: 'delete_item' },
  'messages.confirm_button': { testid: 'btn-confirm-delete', check: 'delete_item' },
  'messages.confirm_delete': { testid: 'confirm-delete-text', check: 'delete_item' },
  'messages.empty': { testid: 'empty-state', check: 'empty_state' },
};

function requirementsPath() {
  return path.resolve(process.env.REQUIREMENTS || DEFAULT_REQUIREMENTS);
}

/** Path of architecture.json, or null when none is given and the default sample does not exist. */
function architecturePath() {
  if (process.env.ARCHITECTURE) return path.resolve(process.env.ARCHITECTURE);
  const usesDefaultRequirements = requirementsPath() === path.resolve(DEFAULT_REQUIREMENTS);
  return usesDefaultRequirements && fs.existsSync(DEFAULT_ARCHITECTURE) ? DEFAULT_ARCHITECTURE : null;
}

function appDir() {
  return path.resolve(process.env.APP_DIR || DEFAULT_APP_DIR);
}

function isHarnessFixture() {
  const rel = path.relative(path.join(E2E_DIR, 'fixtures'), appDir());
  return !rel.startsWith('..') && !path.isAbsolute(rel);
}

function rel(p) {
  return path.relative(REPO_DIR, p).split(path.sep).join('/');
}

/** Reads requirements.json and refuses documents the MVP suite cannot test. */
function loadRequirements() {
  const file = requirementsPath();
  if (!fs.existsSync(file)) {
    throw new Error(`requirements.json not found: ${file}`);
  }
  const doc = JSON.parse(fs.readFileSync(file, 'utf8'));
  const problems = [];

  if (doc.status !== 'ready_for_review') {
    problems.push(`status is "${doc.status}", only "ready_for_review" (approved) documents are tested`);
  }
  const entities = doc.entities || [];
  if (entities.length !== 1) {
    // Open team decision D9: the BA contract allows several entities, the
    // Architect (0.2.0-proposal) and this suite support exactly one.
    problems.push(`exactly one entity is supported, got ${entities.length}: ${entities.map((e) => e.name).join(', ')}`);
  }
  const entity = entities[0];
  if (entity) {
    const refs = entity.fields.filter((f) => f.type === 'reference').map((f) => f.name);
    if (refs.length) problems.push(`reference fields are not supported: ${refs.join(', ')}`);
    for (const op of ['create', 'read', 'update', 'delete']) {
      if (!entity.crud?.[op]?.enabled) problems.push(`CRUD operation "${op}" is disabled`);
    }
    const display = entity.fields.find((f) => f.name === entity.display_field);
    if (!display || !TEXT_TYPES.includes(display.type)) {
      problems.push(`display_field "${entity.display_field}" must be a text field so rows can be found by it`);
    }
  }
  if (problems.length) {
    throw new Error(`Cannot test ${rel(file)}:\n- ${problems.join('\n- ')}`);
  }
  return { doc, entity, file };
}

/**
 * Reads architecture.json when one is given. Returns null without it: the suite then
 * only checks that messages are visible and skips verbatim and format checks.
 */
function loadArchitecture(entityName) {
  const file = architecturePath();
  if (!file) return null;
  if (!fs.existsSync(file)) throw new Error(`architecture.json not found: ${file}`);
  const doc = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (doc.entity?.name !== entityName) {
    throw new Error(`architecture.json is for entity "${doc.entity?.name}", requirements.json for "${entityName}"`);
  }
  return { doc, file };
}

/** Texts that must match exactly (rule M1), keyed by path: { text, source }. */
function verbatimMap(arch) {
  const map = {};
  for (const v of arch?.doc.verbatim_messages ?? []) map[v.path] = { text: v.text, source: v.source };
  return map;
}

/** Verbatim paths the 8 checks cannot compare (e.g. no_results: search is not one of the 8). */
function uncoveredVerbatim(arch) {
  return (arch?.doc.verbatim_messages ?? []).filter(
    (v) => !VERBATIM_TARGETS[v.path] && !/^entity\.fields\.[^.]+\.messages\.required$/.test(v.path),
  );
}

function pad2(n) {
  return String(n).padStart(2, '0');
}

/** Local date (YYYY-MM-DD) shifted by `days`, matching what a date input expects. */
function isoDate(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function fitLength(text, v) {
  let s = text;
  if (v.max_length != null && s.length > v.max_length) s = s.slice(0, v.max_length);
  if (v.min_length != null && s.length < v.min_length) s = s.padEnd(v.min_length, 'x');
  return s;
}

/** A value that satisfies the field's type and validation rules. `tag` keeps records distinct. */
function sampleValue(field, tag) {
  const v = field.validation || {};
  switch (field.type) {
    case 'string':
    case 'text':
      return fitLength(`QA ${tag}`, v);
    case 'email':
      return `qa.${tag.toLowerCase().replace(/[^a-z0-9]/g, '')}@example.com`;
    case 'phone':
      return '0501234567';
    case 'url':
      return 'https://example.com/qa';
    case 'integer': {
      let n = v.min_value != null ? Math.ceil(v.min_value) : 1;
      if (v.max_value != null && n > v.max_value) n = Math.floor(v.max_value);
      return String(n);
    }
    case 'decimal': {
      let n = v.min_value != null ? v.min_value : 1.5;
      if (v.max_value != null && n > v.max_value) n = v.max_value;
      return String(n);
    }
    case 'date':
      return isoDate(v.date_constraint === 'not_in_future' ? -7 : 7);
    case 'datetime':
      return `${isoDate(v.date_constraint === 'not_in_future' ? -7 : 7)}T10:30`;
    case 'time':
      return '10:30';
    case 'boolean':
      return true;
    case 'enum': {
      const values = field.enum_values || [];
      return values.find((x) => x !== field.default) ?? values[0];
    }
    default:
      return undefined;
  }
}

/**
 * Which fields the suite fills when it creates a record: every required field,
 * the display field and every list column. Returns the plan plus any reason
 * the suite cannot build valid input (e.g. a regex it cannot satisfy).
 */
function buildPlan(entity, arch = null) {
  const listFields = entity.crud?.read?.list_fields ?? [];
  const fill = entity.fields.filter(
    (f) => f.required || f.name === entity.display_field || listFields.includes(f.name),
  );
  const problems = [];
  for (const f of fill) {
    const pattern = f.validation?.pattern;
    const value = sampleValue(f, 'Probe 1');
    if (value === undefined) problems.push(`no sample value for field "${f.name}" of type "${f.type}"`);
    else if (pattern && !new RegExp(pattern).test(String(value))) {
      problems.push(`cannot generate a value for "${f.name}" matching pattern ${pattern}`);
    }
  }
  const required = entity.fields.filter((f) => f.required);
  return {
    display: entity.display_field,
    listFields,
    fill,
    required,
    // A required field with a default is pre-filled, so it is not expected to be empty
    // (AC-2 rule, Business Analyst PR #8). A required select without a default starts empty.
    emptiable: required.filter((f) => f.default == null && EMPTIABLE_TYPES.includes(f.type)),
    verbatim: verbatimMap(arch),
    // { field: decimals } from architecture display_format, for list columns
    formats: Object.fromEntries(
      (arch?.doc.entity.fields ?? [])
        .filter((f) => f.display_format && listFields.includes(f.name))
        .map((f) => [f.name, f.display_format.decimals]),
    ),
    problems,
  };
}

/** Values for one record. The display field gets the full tag so it is unique and searchable. */
function recordValues(plan, tag) {
  const values = {};
  for (const f of plan.fill) values[f.name] = sampleValue(f, tag);
  return values;
}

module.exports = {
  E2E_DIR,
  REPO_DIR,
  VERBATIM_TARGETS,
  requirementsPath,
  architecturePath,
  appDir,
  isHarnessFixture,
  rel,
  loadRequirements,
  loadArchitecture,
  uncoveredVerbatim,
  buildPlan,
  recordValues,
};
