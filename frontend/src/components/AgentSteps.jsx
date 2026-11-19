import { useEffect, useState } from 'react';
import { AGENTS, agentState } from '../constants/stages.js';
import { projectHref } from '../hooks/useHashRoute.js';
import { formatDuration } from '../lib/labels.js';
import { WAIT } from '../lib/messages.js';
import Icon from './icons.jsx';

const NAMES = {
  business_analyst: 'محلّل الأعمال',
  software_architect: 'المهندس',
  developer: 'المطوّر',
  qa_tester: 'مختبر الجودة',
  project_manager: 'مدير المشروع',
};
export const agentName = (key) => NAMES[key] ?? 'الوكيل';

const CODE_FILES = ['index.html', 'style.css', 'app.js'];

export function useNow(active) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!active) return undefined;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [active]);
  return now;
}

function has(project, name) {
  return project.artifacts?.some((a) => a.name === name && a.available);
}

function detail(key, state, project, demo) {
  const A = demo ? 'span' : 'a'; // the landing page shows a static example without links
  const req = project.requirements;
  const s = project.status;
  const id = project.project_id;
  switch (key) {
    case 'business_analyst':
      if (s === 'rejected') return <span>الفكرة خارج نطاق النسخة الأولى</span>;
      if (s === 'awaiting_clarification') return <span><span className="step-state">ينتظر إجاباتك</span></span>;
      if (s === 'awaiting_approval') return <span><span className="step-state">المتطلبات بانتظار موافقتك</span></span>;
      if (state === 'done' && req) {
        const fields = req.entities.reduce((n, e) => n + e.fields.length, 0);
        return <span>المتطلبات: {fields} حقول، {req.functional_requirements.length} متطلبات، {req.user_stories.length} قصص مستخدم</span>;
      }
      return <span className="step-state">يحلّل فكرتك</span>;
    case 'software_architect':
      if (state === 'done') {
        const n = req?.entities.length ?? 1;
        return (
          <span>
            وثيقة الهيكل: {n === 1 ? 'كيان واحد' : `${n} كيانات`} وشاشتان ·{' '}
            <A href={demo ? undefined : projectHref(id, 'structure')}>عرض</A>
          </span>
        );
      }
      if (state === 'active') return <span className="step-state">يصمّم الهيكل</span>;
      return <span>يبدأ بعد موافقتك على المتطلبات</span>;
    case 'developer': {
      if (state === 'pending') return <span>يبدأ بعد المهندس · 3 ملفات</span>;
      const files = (
        <ul className="step-files">
          {CODE_FILES.map((f) => (
            <li key={f} className={has(project, f) ? '' : 'pending'}>
              {f} {has(project, f) ? <Icon name="check" size={12} className="ok" /> : '…'}
            </li>
          ))}
        </ul>
      );
      if (s === 'repairing') {
        return (
          <span>
            <span className="step-state">يصلح عيباً · المحاولة {project.repair_attempt} من 2</span>
          </span>
        );
      }
      if (state === 'active') return <span><span className="step-state">يكتب الملفات</span>{files}</span>;
      return <span>index.html · style.css · app.js</span>;
    }
    case 'qa_tester':
      if (state === 'done' && project.metrics) {
        return <span>اجتاز {project.metrics.checks_passed} من {project.metrics.checks_total} فحوصات · <A href={demo ? undefined : projectHref(id, 'tests')}>التقرير</A></span>;
      }
      if (state === 'active') return <span className="step-state">يشغّل 8 فحوصات في متصفح حقيقي</span>;
      if (state === 'done') return <span>اكتملت الفحوصات</span>;
      return <span>يبدأ بعد المطوّر · 8 فحوصات</span>;
    case 'project_manager':
      if (state === 'active') return <span className="step-state">يكتب الخطة والمخاطر</span>;
      if (state === 'done') return <span>الخطة والمخاطر · <A href={demo ? undefined : projectHref(id, 'plan')}>عرض</A></span>;
      return <span>الخطة والمخاطر</span>;
    default:
      return null;
  }
}

const ICON = { done: 'check', active: 'spinner', waiting: 'alert', failed: 'alert', pending: 'circle' };

/** The five agents in order, with live state, details and elapsed time for the active one. */
export default function AgentSteps({ project, demo = false }) {
  const anyActive = AGENTS.some((_, i) => agentState(i, project) === 'active');
  const now = useNow(anyActive);
  const since = project.updated_at ? Date.parse(project.updated_at) : null;
  return (
    <div className="steps" data-testid="agent-steps">
      {AGENTS.map((a, i) => {
        const state = agentState(i, project);
        const elapsed = state === 'active' && since ? now - since : null;
        return (
          <div key={a.key} className={`step step-${state}`} data-testid={`agent-${a.key}`} data-state={state}>
            <span className="step-icon">
              <Icon name={ICON[state]} size={state === 'pending' ? 18 : 14} />
            </span>
            <div style={{ minWidth: 0, display: 'grid', gap: 2 }}>
              <span className="step-name">{agentName(a.key)}</span>
              <span className="step-detail">{detail(a.key, state, project, demo)}</span>
              {elapsed != null && elapsed > WAIT.slow && (
                <span className="step-detail" data-testid="slow-note">يستغرق وقتاً أطول من المعتاد</span>
              )}
            </div>
            <span className="step-time num">{elapsed != null ? formatDuration(elapsed) : ''}</span>
          </div>
        );
      })}
    </div>
  );
}
