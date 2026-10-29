import AgentTimeline from '../components/AgentTimeline.jsx';
import ArtifactList from '../components/ArtifactList.jsx';
import ClarificationForm from '../components/ClarificationForm.jsx';
import OutOfScopeList from '../components/OutOfScopeList.jsx';
import RequirementsReview from '../components/RequirementsReview.jsx';
import ResultsPanel from '../components/ResultsPanel.jsx';
import { STATUS_LABELS } from '../constants/stages.js';
import { useProjectPolling } from '../hooks/useProjectPolling.js';
import { goHome } from '../hooks/useHashRoute.js';

export default function ProjectPage({ id }) {
  const { project, error, refresh, resume } = useProjectPolling(id);

  if (error && !project) {
    return (
      <div className="page">
        <div className="card">
          <p className="alert alert-error">{error.message}</p>
          <div className="actions">
            <button className="btn" onClick={refresh}>
              إعادة المحاولة
            </button>
            <button className="btn" onClick={goHome}>
              فكرة جديدة
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="page">
        <div className="card loading" data-testid="loading">
          جاري التحميل…
        </div>
      </div>
    );
  }

  const req = project.requirements;
  const outOfScope = req?.status === 'rejected_out_of_scope';
  const working = !['awaiting_clarification', 'awaiting_approval', 'completed', 'failed'].includes(project.status);
  const anyArtifact = project.artifacts?.some((a) => a.available);

  return (
    <div className="page">
      <section className="card idea-echo">
        <span className="muted small">فكرتك</span>
        <p dir="auto">{project.idea}</p>
      </section>

      {error && <p className="alert alert-error">انقطع التحديث: {error.message}</p>}

      <AgentTimeline project={project} />

      {working && (
        <p className="working" aria-live="polite" data-testid="working">
          <span className="spinner" aria-hidden="true" /> {STATUS_LABELS[project.status]}…
        </p>
      )}

      {project.status === 'awaiting_clarification' && req && (
        <ClarificationForm project={project} onSubmitted={resume} />
      )}

      {project.status === 'awaiting_approval' && req && <RequirementsReview project={project} onDone={resume} />}

      {project.status === 'failed' && (
        <section className="card" data-testid="failed">
          <h2>{outOfScope ? 'الفكرة خارج نطاق النسخة الأولى' : 'توقف التشغيل'}</h2>
          {!outOfScope && project.error?.message && <p className="alert alert-error">{project.error.message}</p>}
          {outOfScope && (
            <>
              <p className="muted">بنيان يبني حالياً تطبيقات ويب للإضافة والعرض والتعديل والحذف فقط.</p>
              <OutOfScopeList items={req.out_of_scope} dir={req.language === 'ar' ? 'rtl' : 'ltr'} />
            </>
          )}
          <div className="actions">
            <button className="btn btn-primary" onClick={goHome}>
              جرّب فكرة ثانية
            </button>
          </div>
        </section>
      )}

      {project.status === 'completed' && <ResultsPanel project={project} />}

      {anyArtifact && <ArtifactList project={project} />}
    </div>
  );
}
