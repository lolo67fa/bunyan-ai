// Real backend client (FastAPI, owner: Alanoud).
// Matches PR #5: POST /projects takes { "prompt" }, projects are identified by "project_id".
// Endpoints/fields not in PR #5 yet are marked "proposed" in frontend/README.md.
import { MSG, REQUEST_TIMEOUT_MS } from '../lib/messages.js';

const BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let res;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
      signal: controller.signal,
      ...options,
    });
  } catch (e) {
    throw new ApiError(0, e.name === 'AbortError' ? MSG.timeout : MSG.serverDown);
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    let message = `خطأ من الخادم (${res.status})`;
    if (res.status === 404 && path.endsWith('/answers')) {
      message = 'إرسال الإجابات غير مدعوم في الباك إند بعد.';
    }
    try {
      const body = await res.json();
      // FastAPI puts errors in "detail" (string, or a list for validation errors)
      if (typeof body.detail === 'string' && body.detail !== 'Not Found') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join(' · ');
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message);
  }
  const type = res.headers.get('content-type') ?? '';
  return type.includes('application/json') ? res.json() : res.text();
}

/**
 * Fills fields the screens rely on but the backend may not send yet,
 * so a missing field never crashes a screen.
 */
function normalize(p) {
  return {
    current_agent: null,
    requirements: null,
    repair_attempt: 0,
    artifacts: [],
    metrics: null,
    error: null,
    ...p,
  };
}

// A full project always has "idea" and "status". Some action endpoints (approve in PR #5)
// return only part of it; in that case read the whole project again.
const isFullProject = (body) => body && typeof body === 'object' && 'idea' in body && 'status' in body;

async function fullProject(id, body) {
  return isFullProject(body) ? normalize(body) : getProject(id);
}

export async function createProject(idea) {
  try {
    return normalize(await request('/projects', { method: 'POST', body: JSON.stringify({ prompt: idea }) }));
  } catch (e) {
    if (e.status === 422) throw new ApiError(422, MSG.unclearIdea);
    throw e;
  }
}

export async function getProject(id) {
  try {
    return normalize(await request(`/projects/${encodeURIComponent(id)}`));
  } catch (e) {
    // 404 = unknown id, 422 = not a UUID (PR #5 validates the path)
    if (e.status === 404 || e.status === 422) throw new ApiError(404, MSG.notFound);
    throw e;
  }
}

export const submitAnswers = async (id, answers) =>
  fullProject(
    id,
    await request(`/projects/${encodeURIComponent(id)}/answers`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),
  );

export const approveRequirements = async (id, { approved, feedback = '' }) =>
  fullProject(
    id,
    await request(`/projects/${encodeURIComponent(id)}/approve`, {
      method: 'POST',
      body: JSON.stringify(approved ? { approved: true } : { approved: false, feedback }),
    }),
  );

export async function getArtifactText(id, name) {
  const body = await request(
    `/projects/${encodeURIComponent(id)}/artifacts/${encodeURIComponent(name)}`,
  );
  return typeof body === 'string' ? body : JSON.stringify(body, null, 2);
}

export const getPreviewHtml = async () => null;

export const previewUrl = (id) => `${BASE}/projects/${encodeURIComponent(id)}/preview`;

export const downloadUrl = (id) => `${BASE}/projects/${encodeURIComponent(id)}/download`;

export const MODE = 'http';
