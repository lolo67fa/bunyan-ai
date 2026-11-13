import { downloadUrl } from '../api/client.js';
import Icon from '../components/icons.jsx';
import { Notice, StatusText, Tabs } from '../components/ui.jsx';
import { goToProject, projectHref } from '../hooks/useHashRoute.js';
import { useProjectPolling } from '../hooks/useProjectPolling.js';
import { STAGES, projectStatus, projectSlug } from '../lib/labels.js';
import { MSG } from '../lib/messages.js';
import { forgetProject } from '../lib/prefs.js';
import ClarificationView from '../project/ClarificationView.jsx';
import DeliveryView from '../project/DeliveryView.jsx';
import FilesView from '../project/FilesView.jsx';
import PlanView from '../project/PlanView.jsx';
import PreviewView from '../project/PreviewView.jsx';
import ProgressView from '../project/ProgressView.jsx';
import RequirementsView, { ReviewActions } from '../project/RequirementsView.jsx';
import StoppedView from '../project/StoppedView.jsx';
import StructureView from '../project/StructureView.jsx';
import TestsView from '../project/TestsView.jsx';

const RUNNING = ['created', 'analyzing', 'approved', 'designing', 'developing', 'testing', 'repairing', 'documenting'];

const TABS = [
  { key: 'requirements', label: 'المتطلبات', needs: null },
  { key: 'structure', label: 'الهيكل', needs: 'architecture.json' },
  { key: 'files', label: 'الملفات', needs: 'index.html' },
  { key: 'tests', label: 'الاختبار', needs: 'test_report.json' },
  { key: 'plan', label: 'الخطة', needs: 'project_plan.md' },
  { key: 'preview', label: 'المعاينة', needs: 'index.html' },
];

const VIEWS = {
  requirements: RequirementsView,
  structure: StructureView,
  files: FilesView,
  tests: TestsView,
  plan: PlanView,
  preview: PreviewView,
};

function available(project, key) {
  const t = TABS.find((x) => x.key === key);
  if (!t) return false;
  if (key === 'requirements') return Boolean(project.requirements) && project.status !== 'awaiting_clarification';
  return project.artifacts?.some((a) => a.name === t.needs && a.available);
}

function subtitle(project) {
  const s = project.status;
  if (s === 'analyzing' || s === 'created') return <span className="muted small">يقرأ محلّل الأعمال فكرتك ويكتب المتطلبات.</span>;
  if (s === 'awaiting_approval') return <StatusText tone="waiting">المتطلبات بانتظار موافقتك</StatusText>;
  if (s === 'completed') {
    return (
      <div className="stage-links">
        {STAGES.map((st, i) => (
          <a key={st.key} href={projectHref(project.project_id, ['requirements', 'structure', 'files', 'tests', 'plan'][i])}>
            ✓ {st.label}
          </a>
        ))}
        <span className="muted">· اكتملت كل المراحل</span>
      </div>
    );
  }
  return <span className="muted small">وافقت على المتطلبات · البناء جارٍ</span>;
}

export default function ProjectPage({ id, tab }) {
  const { project, error, stalled, resume, retry } = useProjectPolling(id);

  if (error && !project) {
    const notFound = error.status === 404;
    return (
      <div className="page page-narrow">
        <div style={{ display: 'grid', gap: 'var(--bn-s3)', justifyItems: 'start' }} data-testid="project-error">
          <span className="result-mark fail"><Icon name="alert" size={20} /></span>
          <h1 className="title">{notFound ? 'المشروع غير موجود' : 'تعذّر تحميل المشروع'}</h1>
          <p className="lead">{error.message}</p>
          <div className="actions">
            {notFound ? (
              <a className="btn btn-primary" href="#/projects" onClick={() => forgetProject(id)}>العودة للمشاريع</a>
            ) : (
              <button type="button" className="btn btn-primary" onClick={retry}>إعادة المحاولة</button>
            )}
            <a className="btn" href="#/new">مشروع جديد</a>
          </div>
        </div>
      </div>
    );
  }
  if (!project) {
    return (
      <div className="page page-narrow" aria-busy="true">
        <p className="muted" data-testid="loading">جاري التحميل…</p>
      </div>
    );
  }

  const s = project.status;
  const running = RUNNING.includes(s);
  const errorBar = stalled && (
    <Notice tone="error" testId="stalled" action={{ label: 'إعادة المحاولة', onClick: retry }}>
      {error?.message ?? MSG.serverDown}
    </Notice>
  );

  // Full-page states without tabs
  if (s === 'awaiting_clarification' && project.requirements && !tab) {
    return <>{errorBar}<ClarificationView project={project} onDone={resume} /></>;
  }
  if (s === 'rejected' || s === 'failed') return <StoppedView project={project} />;
  if (s === 'completed' && !tab) return <DeliveryView project={project} />;

  const req = project.requirements;
  const appName = req?.status === 'ready_for_review' ? req.app?.name : null;
  const tabs = TABS.map((t) => ({ ...t, disabled: !available(project, t.key), hint: 'يتوفر عند انتهاء المرحلة' }));
  const activeTab = tab && available(project, tab) ? tab : s === 'awaiting_approval' ? 'requirements' : null;
  const View = activeTab ? VIEWS[activeTab] : null;
  const zip = downloadUrl(project.project_id);

  return (
    <div className="page">
      {errorBar}
      <nav className="crumbs" aria-label="المسار">
        <a href="#/projects">المشاريع</a> / <span>{appName ?? 'فكرة جديدة'}</span>
      </nav>

      <div className="page-head">
        <div>
          <h1 className="title" data-testid="project-title">{appName ?? 'فكرة جديدة'}</h1>
          {subtitle(project)}
          <span className="sr-only" data-testid="project-status">{projectStatus(project).text}</span>
        </div>
        {s === 'awaiting_approval' && <ReviewActions project={project} onDone={resume} />}
        {s === 'completed' && (
          <div className="actions">
            <a className="btn" href={projectHref(project.project_id, 'preview')}>معاينة</a>
            {zip ? (
              <a className="btn btn-primary" href={zip} download={`${projectSlug(project)}.zip`}>تحميل ZIP</a>
            ) : (
              <button type="button" className="btn btn-primary" disabled title={MSG.downloadNotReady}>تحميل ZIP</button>
            )}
          </div>
        )}
      </div>

      <Tabs items={tabs} active={activeTab} onSelect={(k) => goToProject(project.project_id, k)} />

      {running && activeTab && (
        <a className="small" href={projectHref(project.project_id)}>← مراحل البناء</a>
      )}
      {View ? <View project={project} onDone={resume} /> : running && <ProgressView project={project} onRetry={retry} />}
    </div>
  );
}
