// Real backend client (FastAPI, owner: Alanoud).
// Endpoints follow docs/architecture.md §5 — payload shapes are a PROPOSAL until agreed.
const BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
      ...options,
    });
  } catch {
    throw new ApiError(0, 'تعذّر الاتصال بالخادم. تأكد أن الباك إند يعمل.');
  }
  if (!res.ok) {
    let message = `خطأ من الخادم (${res.status})`;
    try {
      const body = await res.json();
      // FastAPI puts errors in "detail" (string, or a list for validation errors)
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join(' · ');
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message);
  }
  const type = res.headers.get('content-type') ?? '';
  return type.includes('application/json') ? res.json() : res.text();
}

export const createProject = (idea) =>
  request('/projects', { method: 'POST', body: JSON.stringify({ idea }) });

export const getProject = (id) => request(`/projects/${encodeURIComponent(id)}`);

export const submitAnswers = (id, answers) =>
  request(`/projects/${encodeURIComponent(id)}/answers`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  });

export const approveRequirements = (id, { approved, feedback = '' }) =>
  request(`/projects/${encodeURIComponent(id)}/approve`, {
    method: 'POST',
    body: JSON.stringify(approved ? { approved: true } : { approved: false, feedback }),
  });

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
