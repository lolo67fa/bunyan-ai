import { useEffect, useMemo, useState } from 'react';
import { getProject } from '../api/client.js';
import { EmptyState, Notice, StatusText } from '../components/ui.jsx';
import { go, goToProject, projectHref } from '../hooks/useHashRoute.js';
import { formatDate, projectStage, projectStatus, statusGroup } from '../lib/labels.js';
import { MSG } from '../lib/messages.js';
import { forgetProject, getRecent, projectLabel, rememberProject } from '../lib/prefs.js';

const FILTERS = [
  ['all', 'الكل'],
  ['running', 'جارية'],
  ['waiting', 'بانتظارك'],
  ['done', 'مكتملة'],
];

/** All projects opened in this browser (the API has no list endpoint yet). */
export default function ProjectsPage() {
  const [items, setItems] = useState(() => getRecent().map((r) => ({ ...r, project: null })));
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let alive = true;
    Promise.all(
      getRecent().map((r) =>
        getProject(r.id)
          .then((p) => { rememberProject(p); return { ...r, project: p }; })
          .catch((e) => {
            if (e.status === 404) { forgetProject(r.id); return null; }
            if (alive) setOffline(true);
            return { ...r, project: null };
          }),
      ),
    ).then((list) => alive && setItems(list.filter(Boolean)));
    return () => { alive = false; };
  }, []);

  const rows = items.map((r) => {
    const p = r.project ?? { project_id: r.id, idea: r.idea, status: r.status, created_at: r.created_at, requirements: r.name ? { app: { name: r.name } } : null };
    return { r, p, group: statusGroup(p) };
  });
  const counts = useMemo(() => {
    const c = { all: rows.length, running: 0, waiting: 0, done: 0 };
    rows.forEach((x) => { if (c[x.group] != null) c[x.group] += 1; });
    return c;
  }, [rows]);
  const waiting = rows.find((x) => x.p.status === 'awaiting_approval' || x.p.status === 'awaiting_clarification');
  const q = query.trim();
  const shown = rows.filter((x) => (filter === 'all' || x.group === filter) && (!q || `${projectLabel(x.r)} ${x.p.idea}`.includes(q)));

  return (
    <div className="page" data-testid="projects-page">
      <div className="page-head">
        <div><h1 className="title">المشاريع</h1></div>
        <a className="btn btn-primary" href="#/new">مشروع جديد</a>
      </div>

      {offline && <Notice tone="error">{MSG.serverDown}</Notice>}
      {waiting && (
        <Notice
          tone="waiting"
          action={{
            label: waiting.p.status === 'awaiting_approval' ? 'مراجعة المتطلبات' : 'الإجابة عن الأسئلة',
            onClick: () => goToProject(waiting.p.project_id),
          }}
        >
          {waiting.p.status === 'awaiting_approval' ? (
            <>متطلبات <strong>{projectLabel(waiting.r)}</strong> جاهزة وتنتظر موافقتك قبل البدء بالبناء.</>
          ) : (
            <>يحتاج المحلّل إجاباتك عن <strong>{projectLabel(waiting.r)}</strong> قبل كتابة المتطلبات.</>
          )}
        </Notice>
      )}

      {rows.length === 0 ? (
        <EmptyState title="لا توجد مشاريع بعد" action={<button type="button" className="btn btn-primary" onClick={() => go('/new')}>مشروع جديد</button>}>
          {MSG.noProjects}
        </EmptyState>
      ) : (
        <>
          <div className="page-head" style={{ alignItems: 'center' }}>
            <div className="tabs" role="tablist" aria-label="تصفية المشاريع" style={{ borderBottom: 0, display: 'flex' }}>
              {FILTERS.map(([k, label]) => (
                <button key={k} type="button" role="tab" className="tab" aria-selected={filter === k} onClick={() => setFilter(k)}>
                  <span className="num">{counts[k]}</span> {label}
                </button>
              ))}
            </div>
            <input
              className="input"
              type="search"
              placeholder="بحث"
              aria-label="بحث في المشاريع"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ maxWidth: 240 }}
            />
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>المشروع</th><th>المرحلة</th><th>الحالة</th><th>أُنشئ</th><th><span className="sr-only">إجراء</span></th></tr>
              </thead>
              <tbody>
                {shown.map(({ r, p }) => {
                  const st = projectStatus(p);
                  const needsYou = ['awaiting_approval', 'awaiting_clarification'].includes(p.status);
                  return (
                    <tr key={r.id} className="row-link" onClick={() => goToProject(r.id)}>
                      <td>
                        <a className="strong" href={projectHref(r.id)} onClick={(e) => e.stopPropagation()} style={{ color: 'var(--bn-text)' }}>
                          {projectLabel(r)}
                        </a>
                        <div className="muted small" style={{ maxWidth: 420, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} dir="auto">
                          {p.requirements?.app?.description ?? p.idea}
                        </div>
                      </td>
                      <td className="num" style={{ whiteSpace: 'nowrap' }}>{projectStage(p)}</td>
                      <td><StatusText tone={st.tone}>{st.text}</StatusText></td>
                      <td className="muted" style={{ whiteSpace: 'nowrap' }}>{formatDate(p.created_at ?? r.created_at)}</td>
                      <td><a href={projectHref(r.id)} onClick={(e) => e.stopPropagation()}>{needsYou ? 'مراجعة' : 'فتح'}</a></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {shown.length === 0 && <p className="muted small">لا توجد مشاريع مطابقة.</p>}
        </>
      )}
      <p className="muted small">تظهر هنا المشاريع التي فتحتها من هذا المتصفح.</p>
    </div>
  );
}
