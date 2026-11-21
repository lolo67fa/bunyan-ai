// Per-browser conveniences: theme, reduced motion and the list of recent projects.
// Stored in localStorage; every access is guarded because storage can be blocked.

const PREFS_KEY = 'bunyan.prefs';
const RECENT_KEY = 'bunyan.recent';
const MAX_RECENT = 12;

function read(key, fallback) {
  try {
    const v = JSON.parse(localStorage.getItem(key));
    return v ?? fallback;
  } catch {
    return fallback;
  }
}
function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable */
  }
}

export const DEFAULT_PREFS = { theme: 'light', reduceMotion: false };

export function getPrefs() {
  return { ...DEFAULT_PREFS, ...read(PREFS_KEY, {}) };
}

export function applyPrefs(prefs = getPrefs()) {
  const root = document.documentElement;
  if (prefs.theme === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', prefs.theme);
  if (prefs.reduceMotion) root.setAttribute('data-motion', 'reduce');
  else root.removeAttribute('data-motion');
}

export function savePrefs(prefs) {
  write(PREFS_KEY, prefs);
  applyPrefs(prefs);
}

// ---------- recent projects (the API has no list endpoint yet) ----------
const listeners = new Set();

export function getRecent() {
  return read(RECENT_KEY, []);
}

export function rememberProject(project) {
  if (!project?.project_id) return;
  // Only a reviewed requirements document has a real app name; drafts keep the idea as label.
  const name = project.requirements?.status === 'ready_for_review' ? project.requirements.app?.name ?? null : null;
  const list = getRecent();
  const existing = list.find((p) => p.id === project.project_id);
  if (existing && existing.name === name && existing.status === project.status) return;
  const entry = {
    id: project.project_id,
    name,
    idea: project.idea,
    status: project.status,
    created_at: project.created_at ?? existing?.created_at ?? new Date().toISOString(),
  };
  const next = [entry, ...list.filter((p) => p.id !== entry.id)].slice(0, MAX_RECENT);
  write(RECENT_KEY, next);
  listeners.forEach((fn) => fn(next));
}

export function forgetProject(id) {
  const next = getRecent().filter((p) => p.id !== id);
  write(RECENT_KEY, next);
  listeners.forEach((fn) => fn(next));
}

export function onRecentChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function projectLabel(p) {
  if (p.name) return p.name;
  const idea = (p.idea ?? '').trim();
  return idea.length > 28 ? `${idea.slice(0, 28)}…` : idea || 'مشروع';
}
