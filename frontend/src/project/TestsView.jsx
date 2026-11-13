import { Notice, StatusText } from '../components/ui.jsx';
import { checkLabels, formatDuration } from '../lib/labels.js';
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
  const attempt = r.run?.attempt ?? project.repair_attempt ?? 0;
  const final = s.all_passed ? ['ناجح', 'done'] : ['لم ينجح', 'failed'];

  return (
    <div style={{ display: 'grid', gap: 'var(--bn-s4)', paddingTop: 'var(--bn-s5)' }} data-testid="tests-view">
      <div className="section-head">
        <div className="score">
          <b>{s.passed}</b>
          <span className="lead">من {s.total} فحوصات ناجحة</span>
          <StatusText tone={final[1]}>النتيجة النهائية: {final[0]}</StatusText>
        </div>
        <span className="muted small">
          التشغيل {attempt + 1}
          {r.run?.duration_ms ? ` · ${formatDuration(r.run.duration_ms)}` : ''} · Playwright
        </span>
      </div>

      {attempt > 0 && s.all_passed && (
        <Notice>
          فشل فحص في التشغيل الأول، وأصلحه المطوّر في المحاولة {attempt} من 2، ثم نجحت الفحوصات الثمانية كلها.
        </Notice>
      )}
      {!s.all_passed && (
        <Notice tone={attempt >= 2 ? 'error' : 'waiting'}>
          {attempt >= 2
            ? 'ما زال فحص يفشل بعد محاولتين. يمكنك تحميل الكود مع تقرير العيوب.'
            : `فشل ${s.failed} من ${s.total} فحوصات. أُرسل العيب للمطوّر لإصلاحه.`}
        </Notice>
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
        يشغّل مختبر الجودة ثمانية فحوصات على التطبيق في متصفح حقيقي. إذا فشل فحص يصلحه المطوّر، بحد أقصى محاولتان.
      </p>
    </div>
  );
}
