import { useEffect, useState } from 'react';
import Logo from '../brand/Logo.jsx';
import Icon from '../components/icons.jsx';
import { projectHref } from '../hooks/useHashRoute.js';
import { getRecent, onRecentChange, projectLabel } from '../lib/prefs.js';
import { statusGroup } from '../lib/labels.js';
import { MODE } from '../api/client.js';

const DOT_TONE = { waiting: 'var(--bn-warning)', running: 'var(--bn-accent)' };

function NavLink({ href, current, children, testId }) {
  return (
    <a className="nav-link" href={href} aria-current={current ? 'page' : undefined} data-testid={testId}>
      {children}
    </a>
  );
}

/** Product layout: side bar at the start of reading (right in Arabic) and the page. */
export default function AppShell({ route, children }) {
  const [recent, setRecent] = useState(getRecent);
  const [open, setOpen] = useState(false);
  useEffect(() => onRecentChange(setRecent), []);
  useEffect(() => setOpen(false), [route]);

  const sidebar = (
    <aside className="sidebar" data-open={open} aria-label="التنقل">
      <div className="sidebar-brand">
        <Logo />
        {MODE === 'mock' && <span className="mock-flag" title="بيانات تجريبية، الخادم غير مربوط">تجريبي</span>}
      </div>
      <a className="btn btn-block" href="#/new" data-testid="nav-new">
        <Icon name="plus" size={14} /> مشروع جديد
      </a>
      <nav className="sidebar-nav">
        <NavLink href="#/projects" current={route.page === 'projects'} testId="nav-projects">
          المشاريع
        </NavLink>
        {recent.length > 0 && <div className="sidebar-label">الأخيرة</div>}
        {recent.slice(0, 6).map((p) => {
          const tone = DOT_TONE[statusGroup(p)];
          return (
            <NavLink key={p.id} href={projectHref(p.id)} current={route.page === 'project' && route.id === p.id}>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{projectLabel(p)}</span>
              {tone && <span className="dot" style={{ color: tone }} aria-label="يحتاج متابعة" />}
            </NavLink>
          );
        })}
      </nav>
      <nav className="sidebar-foot">
        <NavLink href="#/settings" current={route.page === 'settings'} testId="nav-settings">
          الإعدادات
        </NavLink>
        <NavLink href="#/help" current={route.page === 'help'}>
          المساعدة
        </NavLink>
      </nav>
    </aside>
  );

  return (
    <div className="shell">
      {sidebar}
      {open && <div className="scrim" onClick={() => setOpen(false)} />}
      <div style={{ minWidth: 0 }}>
        <div className="topbar">
          <Logo />
          <button type="button" className="btn icon-btn menu-btn" aria-label="القائمة" onClick={() => setOpen(true)}>
            <Icon name="menu" size={18} />
          </button>
        </div>
        <main className="main" id="main">
          {children}
        </main>
      </div>
    </div>
  );
}
