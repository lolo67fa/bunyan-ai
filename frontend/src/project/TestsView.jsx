import { Notice, StatusText } from '../components/ui.jsx';
import { checkLabels, formatDuration } from '../lib/labels.js';
import { MSG } from '../lib/messages.js';
import { QA_NOTES, repairCount } from '../lib/qa.js';
import { useArtifact } from './useArtifact.js';

const RESULT = {
  passed: ['نجح', 'done'],
  failed: ['فشل', 'failed'],
  skipped: ['تخطى', 'neutral'],
  not_run: ['لم يعمل', 'neutral'],
};

/** "الاختبار": Sara's test_report.json (contract 0.1.0-proposal). */
export default function TestsView({ project }) {
  const { json: r, error, loading } = useArtifact(project, 'test_report.json');
  if (error) return <p className="field-error">{error.message}</p>;
  if (loading || !r) return <p className="muted">جاري التحميل…</p>;

  const entity = project.requirements?.entities?.[0]?.label ?? 'السجل';
  const names = checkLabels(entity);
  const s = r.summary;
  const attempt = r.run?.attempt ?? 0;
  // A repair is mentioned only when the backend made one; the report's attempt alone is not enough.
  const repairs = Math.min(repairCount(project), attempt);
  const status = project.qa?.status ?? (s.all_passed ? 'passed' : 'failed');
  const final = {
    passed: ['ناجح', 'done'],
    failed: ['لم ينجح', 'failed'],
    blocked: ['غير مؤكد', 'waiting'],
    not_run: ['لم يُشغَّل', 'neutral'],
  }[status] ?? ['لم ينجح', 'failed'];

  return (
    <div style={{ display: 'grid', gap: 'var(--bn-s4)', paddingTop: 'var(--bn-s5)' }} data-testid="tests-view">
      <div className="section-head">
        <div className="score">
          <b>{s.passed}</b>
          <span className="lead">من {s.total} فحوصات ناجحة</span>
          <StatusText tone={final[1]}><span data-testid="qa-final" data-qa={status}>النتيجة النهائية: {final[0]}</span></StatusText>
        </div>
        <span className="muted small">
          التشغيل {attempt + 1}
          {r.run?.duration_ms ? ` · ${formatDuration(r.run.duration_ms)}` : ''} · Playwright
        </span>
      </div>

      {repairs > 0 && status === 'passed' && (
        <Notice testId="repair-note">
          فشل فحص في التشغيل الأول، وأصلحه المطوّر في المحاولة {repairs} من 2، ثم نجحت الفحوصات كلها.
        </Notice>
      )}
      {status === 'failed' && (
        <Notice tone="error" testId="qa-note">
          {project.status === 'repairing'
            ? MSG.repairSent(s.failed, s.total)
            : repairs >= 2
              ? MSG.repairsExhausted
              : MSG.checksFailed(s.failed, s.total)}
        </Notice>
      )}
      {(status === 'blocked' || status === 'not_run') && (
        <Notice tone="waiting" testId="qa-note">{QA_NOTES[status]}</Notice>
      )}
      {status === 'passed' && s.skipped > 0 && (
        <p className="muted small" data-testid="qa-skipped">
          {s.skipped} فحوصات لم تنطبق على هذا التطبيق، ولا تُحسب ناجحة.
        </p>
      )}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>#</th><th>الفحص</th><th>ما يتحقق منه</th><th>النتيجة</th></tr>
          </thead>
          <tbody>
            {r.checks.map((c, i) => {
              const [name, what] = names[c.id] ?? [c.id, c.description];
              const [label, tone] = RESULT[c.status] ?? [c.status, 'neutral'];
              return (
                <tr key={c.id} data-testid={`check-${c.id}`}>
                  <td className="num muted">{i + 1}</td>
                  <td className="strong">{name}</td>
                  <td>
                    {what}
                    {c.error?.message && (
                      <div className="small" style={{ color: 'var(--bn-danger)' }}>
                        {c.error.message}
                        {c.evidence?.trace && <span className="mono ltr"> · trace.zip</span>}
                      </div>
                    )}
                  </td>
                  <td><StatusText tone={tone}>{label}</StatusText></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="muted small">
        يشغّل مختبر الجودة ثمانية فحوصات على التطبيق في متصفح حقيقي، ويسجّل نتيجة كل فحص وسبب أي فشل.
      </p>
    </div>
  );
}
