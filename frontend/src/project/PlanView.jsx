import Icon from '../components/icons.jsx';
import Markdown from '../lib/Markdown.jsx';
import { saveFile, useArtifact } from './useArtifact.js';

/** "الخطة": project_plan.md and risks.md from the Project Manager agent. */
export default function PlanView({ project }) {
  const plan = useArtifact(project, 'project_plan.md');
  const risks = useArtifact(project, 'risks.md');
  if (plan.error) return <p className="field-error">{plan.error.message}</p>;
  if (plan.loading || plan.text == null) return <p className="muted">جاري التحميل…</p>;
  return (
    <div style={{ display: 'grid', gap: 'var(--bn-s5)', paddingTop: 'var(--bn-s5)' }} data-testid="plan-view">
      <div className="section-head">
        <span className="muted small">أعدّها مدير المشروع بناءً على مخرجات الوكلاء الأربعة.</span>
        <div className="actions">
          <button type="button" className="btn btn-sm" onClick={() => saveFile('project_plan.md', plan.text)}>
            <Icon name="download" size={14} /> <span className="mono">project_plan.md</span>
          </button>
          {risks.text != null && (
            <button type="button" className="btn btn-sm" onClick={() => saveFile('risks.md', risks.text)}>
              <Icon name="download" size={14} /> <span className="mono">risks.md</span>
            </button>
          )}
        </div>
      </div>
      <Markdown text={plan.text} />
      {risks.text != null && <Markdown text={risks.text} />}
    </div>
  );
}
