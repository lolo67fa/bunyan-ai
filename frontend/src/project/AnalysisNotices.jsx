import { Notice } from '../components/ui.jsx';
import { analysisNotices } from '../lib/analysis.js';

/** The Business Analyst's last run: a kept error, what a revision changed, an Architect warning. */
export default function AnalysisNotices({ project }) {
  const notices = analysisNotices(project);
  if (!notices.length) return null;
  return (
    <div style={{ display: 'grid', gap: 'var(--bn-s2)', paddingBottom: 'var(--bn-s4)' }}>
      {notices.map((n) => (
        <Notice key={n.testId} tone={n.tone} testId={n.testId}>{n.text}</Notice>
      ))}
    </div>
  );
}
