import AgentSteps, { agentName, useNow } from '../components/AgentSteps.jsx';
import { Notice } from '../components/ui.jsx';
import { go } from '../hooks/useHashRoute.js';
import { MSG, WAIT } from '../lib/messages.js';

/** "مراحل البناء": the five agents while the run is working. */
export default function ProgressView({ project, onRetry }) {
  const now = useNow(true);
  const since = project.updated_at ? Date.parse(project.updated_at) : null;
  const waited = since ? now - since : 0;
  const agent = agentName(project.current_agent);
  return (
    <section style={{ display: 'grid', gap: 'var(--bn-s3)' }} data-testid="progress">
      <div className="section-head">
        <h2 className="section-title">مراحل البناء</h2>
        <span className="muted small">يمكنك مغادرة الصفحة، سيستمر العمل.</span>
      </div>
      {project.status === 'repairing' && <Notice tone="waiting">{MSG.repairing(project.repair_attempt || 1)}</Notice>}
      {waited > WAIT.verySlow && (
        <Notice
          tone="waiting"
          testId="very-slow"
          action={{ label: 'العودة لاحقاً', onClick: () => go('/projects') }}
        >
          {MSG.verySlow(agent)}{' '}
          <button type="button" className="link-btn" onClick={onRetry}>
            إعادة التحقق
          </button>
        </Notice>
      )}
      <AgentSteps project={project} />
    </section>
  );
}
