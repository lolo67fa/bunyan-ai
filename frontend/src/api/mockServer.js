// In-browser fake of the FastAPI backend, so the frontend can be built before
// the orchestrator exists. Same function names and response shape as httpClient.js.
//
// requirements.json comes from Ghala's real samples; later artifacts are placeholders.
// Runs survive a page refresh (stored in localStorage).
import { SAMPLES, pickSampleKey, pickSampleAfterAnswers } from '../mocks/samples.js';
import {
  mockArchitecture,
  mockTestReport,
  mockProjectPlan,
  mockRisks,
  mockPreviewHtml,
} from '../mocks/placeholders.js';

const STORE_KEY = 'bunyan.mock.projects';
const ANALYZE_MS = 2500;
// Mock repair demo: this sample fails one QA check on the first run, then gets repaired.
const REPAIR_DEMO_SAMPLE = 'inventory_dialect_ar';

const STEP_MS = {
  designing: 2500,
  developing: 3000,
  testing: 2500,
  repairing: 2500,
  documenting: 2000,
};

// Which artifacts exist once a given status has been reached.
const ARTIFACT_STAGES = [
  { name: 'requirements.json', after: 'analyzed' },
  { name: 'architecture.json', after: 'designing' },
  { name: 'index.html', after: 'developing' },
  { name: 'style.css', after: 'developing' },
  { name: 'app.js', after: 'developing' },
  { name: 'test_report.json', after: 'testing' },
  { name: 'project_plan.md', after: 'documenting' },
  { name: 'risks.md', after: 'documenting' },
];

// ---------- storage ----------
function load() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY)) ?? {};
  } catch {
    return {};
  }
}
function save(all) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(all));
  } catch {
    /* storage unavailable: runs only live until refresh */
  }
}
let memory = load();
function getRecord(id) {
  const rec = memory[id];
  if (!rec) throw new ApiError(404, 'المشروع غير موجود');
  return rec;
}
function putRecord(rec) {
  memory[rec.id] = rec;
  save(memory);
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms));
const now = () => Date.now();
const newId = () => `p_${now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

// ---------- timeline ----------
function analysisTimeline(start, sampleKey) {
  const doc = SAMPLES[sampleKey];
  const after =
    doc.status === 'needs_clarification'
      ? 'awaiting_clarification'
      : doc.status === 'rejected_out_of_scope'
        ? 'failed'
        : 'awaiting_approval';
  return [
    { status: 'analyzing', at: start, current_agent: 'business_analyst' },
    { status: after, at: start + ANALYZE_MS, current_agent: 'business_analyst', analyzed: true },
  ];
}

function buildTimeline(start, sampleKey) {
  const withRepair = sampleKey === REPAIR_DEMO_SAMPLE;
  const steps = withRepair
    ? ['designing', 'developing', 'testing', 'repairing', 'testing', 'documenting']
    : ['designing', 'developing', 'testing', 'documenting'];
  const agentOf = {
    designing: 'software_architect',
    developing: 'developer',
    testing: 'qa_tester',
    repairing: 'developer',
    documenting: 'project_manager',
  };
  let t = start;
  let repairs = 0;
  const out = steps.map((status) => {
    if (status === 'repairing') repairs += 1;
    const step = { status, at: t, current_agent: agentOf[status], repair_attempt: repairs, analyzed: true };
    t += STEP_MS[status];
    return step;
  });
  out.push({ status: 'completed', at: t, current_agent: null, repair_attempt: repairs, analyzed: true });
  return out;
}

function currentStep(rec) {
  const t = now();
  let step = rec.timeline[0];
  for (const s of rec.timeline) if (s.at <= t) step = s;
  return step;
}

function reached(rec, status) {
  const t = now();
  return rec.timeline.some((s) => s.at <= t && (status === 'analyzed' ? s.analyzed : s.status === status));
}

// ---------- response shape (proposal for GET /projects/{id}) ----------
function toProject(rec) {
  const step = currentStep(rec);
  const doc = SAMPLES[rec.sampleKey];
  const analyzed = Boolean(step.analyzed);
  const project = {
    id: rec.id,
    idea: rec.idea,
    status: step.status,
    current_agent: step.current_agent ?? null,
    repair_attempt: step.repair_attempt ?? 0,
    created_at: new Date(rec.created_at).toISOString(),
    updated_at: new Date(step.at).toISOString(),
    requirements: analyzed ? doc : null,
    artifacts: ARTIFACT_STAGES.map((a) => ({ name: a.name, available: reached(rec, a.after) })),
    metrics: null,
    error: null,
  };
  if (step.status === 'failed' && doc.status === 'rejected_out_of_scope') {
    project.error = { code: 'out_of_scope', message: 'الفكرة خارج نطاق النسخة الأولى (CRUD فقط).' };
  }
  if (step.status === 'completed') {
    const report = mockTestReport(doc);
    project.metrics = {
      pass_rate: report.pass_rate,
      checks_passed: report.passed,
      checks_total: report.total,
      run_time_seconds: Math.round((step.at - rec.approved_at) / 1000),
    };
  }
  return project;
}

// ---------- API ----------
export async function createProject(idea) {
  await delay();
  const text = (idea ?? '').trim();
  if (text.length < 5) throw new ApiError(422, 'اكتب فكرة التطبيق بشكل أوضح.');
  const start = now();
  const sampleKey = pickSampleKey(text);
  const rec = { id: newId(), idea: text, created_at: start, sampleKey, timeline: analysisTimeline(start, sampleKey) };
  putRecord(rec);
  return toProject(rec);
}

export async function getProject(id) {
  await delay(150);
  return toProject(getRecord(id));
}

export async function submitAnswers(id, answers) {
  await delay();
  const rec = getRecord(id);
  if (currentStep(rec).status !== 'awaiting_clarification') {
    throw new ApiError(409, 'المشروع لا ينتظر إجابات الآن.');
  }
  rec.answers = answers;
  rec.sampleKey = pickSampleAfterAnswers(answers);
  rec.timeline = analysisTimeline(now(), rec.sampleKey);
  putRecord(rec);
  return toProject(rec);
}

export async function approveRequirements(id, { approved, feedback = '' }) {
  await delay();
  const rec = getRecord(id);
  if (currentStep(rec).status !== 'awaiting_approval') {
    throw new ApiError(409, 'المشروع لا ينتظر الموافقة الآن.');
  }
  if (approved) {
    rec.approved_at = now();
    rec.timeline = buildTimeline(rec.approved_at, rec.sampleKey);
  } else {
    // Like the analyst's mock mode, feedback is recorded but the same document comes back.
    rec.feedback = feedback;
    rec.timeline = analysisTimeline(now(), rec.sampleKey);
  }
  putRecord(rec);
  return toProject(rec);
}

export async function getArtifactText(id, name) {
  await delay(150);
  const rec = getRecord(id);
  const project = toProject(rec);
  const art = project.artifacts.find((a) => a.name === name);
  if (!art?.available) throw new ApiError(404, 'الملف غير متوفر بعد.');
  const doc = SAMPLES[rec.sampleKey];
  const json = (o) => JSON.stringify(o, null, 2);
  switch (name) {
    case 'requirements.json':
      return json(doc);
    case 'architecture.json':
      return json(mockArchitecture(doc));
    case 'test_report.json':
      return json(mockTestReport(doc));
    case 'project_plan.md':
      return mockProjectPlan(project);
    case 'risks.md':
      return mockRisks(project);
    case 'index.html':
      return mockPreviewHtml(doc);
    case 'style.css':
      return '/* MOCK — generated by the Developer agent (Yara) */\n';
    case 'app.js':
      return '// MOCK — generated by the Developer agent (Yara)\n';
    default:
      throw new ApiError(404, 'ملف غير معروف');
  }
}

/** Mock: the preview is rendered with srcdoc. */
export async function getPreviewHtml(id) {
  return getArtifactText(id, 'index.html');
}

export function previewUrl() {
  return null;
}

/** Mock has no ZIP; the real backend serves GET /projects/{id}/download. */
export function downloadUrl() {
  return null;
}

export const MODE = 'mock';
