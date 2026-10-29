import { useState } from 'react';
import { approveRequirements } from '../api/client.js';
import OutOfScopeList from './OutOfScopeList.jsx';

const TYPE_LABELS = {
  string: 'نص قصير',
  text: 'نص طويل',
  integer: 'رقم صحيح',
  decimal: 'رقم عشري',
  boolean: 'نعم / لا',
  date: 'تاريخ',
  time: 'وقت',
  datetime: 'تاريخ ووقت',
  email: 'بريد إلكتروني',
  phone: 'جوال',
  url: 'رابط',
  enum: 'قائمة خيارات',
  reference: 'ربط بكيان',
};

const PRIORITY = { must: 'إلزامي', should: 'مهم', could: 'اختياري' };

function rules(field) {
  const v = field.validation ?? {};
  const out = [];
  if (field.unique) out.push('فريد');
  if (v.min_length != null) out.push(`≥ ${v.min_length} حرف`);
  if (v.max_length != null) out.push(`≤ ${v.max_length} حرف`);
  if (v.min_value != null) out.push(`≥ ${v.min_value}`);
  if (v.max_value != null) out.push(`≤ ${v.max_value}`);
  if (v.pattern) out.push(`نمط ${v.pattern}`);
  if (v.date_constraint === 'not_in_past') out.push('ليس في الماضي');
  if (v.date_constraint === 'not_in_future') out.push('ليس في المستقبل');
  if (field.type === 'enum' && field.enum_values) out.push(field.enum_values.join(' / '));
  if (field.type === 'reference') out.push(`← ${field.reference_entity}`);
  if (field.default != null) out.push(`افتراضي: ${field.default}`);
  return out;
}

/** Approval screen for a requirements.json with status ready_for_review. */
export default function RequirementsReview({ project, onDone }) {
  const req = project.requirements;
  const dir = req.language === 'ar' ? 'rtl' : 'ltr';
  const optional = (req.clarification_questions ?? []).filter((q) => !q.blocking);

  const [mode, setMode] = useState('review'); // review | feedback
  const [feedback, setFeedback] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  async function send(approved) {
    if (!approved && feedback.trim().length < 3) {
      setError('اكتب التعديلات المطلوبة.');
      return;
    }
    setSending(true);
    setError('');
    try {
      onDone(await approveRequirements(project.id, { approved, feedback: feedback.trim() }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="card" data-testid="requirements-review">
      <div className="card-head">
        <h2>راجع المتطلبات</h2>
        <span className="muted ltr small">schema {req.schema_version}</span>
      </div>
      <p className="muted">ما راح يبدأ التوليد إلا بعد موافقتك.</p>

      <div className="app-summary" dir={dir}>
        <h3>{req.app.name}</h3>
        <p>{req.app.description}</p>
        {req.app.target_users?.length > 0 && (
          <p className="muted small">المستخدمون: {req.app.target_users.join('، ')}</p>
        )}
      </div>

      {req.entities.map((entity) => (
        <div key={entity.name} className="entity" dir={dir} data-testid={`entity-${entity.name}`}>
          <h3>
            {entity.plural_label} <span className="muted ltr small">{entity.name}</span>
          </h3>
          {entity.description && <p className="muted small">{entity.description}</p>}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>الحقل</th>
                  <th>النوع</th>
                  <th>إلزامي</th>
                  <th>القواعد</th>
                </tr>
              </thead>
              <tbody>
                {entity.fields.map((f) => (
                  <tr key={f.name}>
                    <td>
                      {f.label}
                      <div className="muted ltr small">{f.name}</div>
                    </td>
                    <td>{TYPE_LABELS[f.type] ?? f.type}</td>
                    <td>{f.required ? '✓' : '—'}</td>
                    <td className="small">{rules(f).join(' · ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      <details dir={dir}>
        <summary>المتطلبات الوظيفية ({req.functional_requirements.length})</summary>
        <ul className="plain">
          {req.functional_requirements.map((r) => (
            <li key={r.id}>
              <span className="ltr qid">{r.id}</span> <span className="tag">{PRIORITY[r.priority]}</span>{' '}
              {r.description}
            </li>
          ))}
        </ul>
      </details>

      <details dir={dir}>
        <summary>قصص المستخدم ({req.user_stories.length})</summary>
        <ul className="plain">
          {req.user_stories.map((s) => (
            <li key={s.id}>
              <span className="ltr qid">{s.id}</span> {s.role} — {s.goal} — {s.benefit}
            </li>
          ))}
        </ul>
      </details>

      <details dir={dir}>
        <summary>معايير القبول ({req.acceptance_criteria.length})</summary>
        <ul className="plain">
          {req.acceptance_criteria.map((a) => (
            <li key={a.id}>
              <span className="ltr qid">{a.id}</span> <b>Given</b> {a.given} · <b>When</b> {a.when} ·{' '}
              <b>Then</b> {a.then}
            </li>
          ))}
        </ul>
      </details>

      {req.assumptions?.length > 0 && (
        <details dir={dir}>
          <summary>الافتراضات ({req.assumptions.length})</summary>
          <ul className="plain">
            {req.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </details>
      )}

      {optional.length > 0 && (
        <div className="notice" dir={dir}>
          <strong>قرارات اتخذها المحلل بالنيابة عنك</strong>
          <ul className="plain">
            {optional.map((q) => (
              <li key={q.id}>
                {q.question} ← <b>{q.suggested_default}</b>
              </li>
            ))}
          </ul>
        </div>
      )}

      {req.out_of_scope?.length > 0 && (
        <>
          <h3>ميزات خارج النطاق</h3>
          <OutOfScopeList items={req.out_of_scope} dir={dir} />
        </>
      )}

      {mode === 'feedback' && (
        <label className="block">
          وش تبغى تعدّل؟
          <textarea
            rows={3}
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            data-testid="feedback-input"
          />
        </label>
      )}

      {error && <p className="alert alert-error">{error}</p>}

      <div className="actions">
        {mode === 'review' ? (
          <>
            <button className="btn btn-primary" disabled={sending} onClick={() => send(true)} data-testid="approve">
              {sending ? 'جاري الإرسال…' : 'موافق، ابدأ التوليد'}
            </button>
            <button className="btn" disabled={sending} onClick={() => setMode('feedback')}>
              أبغى تعديلات
            </button>
          </>
        ) : (
          <>
            <button className="btn btn-primary" disabled={sending} onClick={() => send(false)} data-testid="send-feedback">
              إرسال التعديلات
            </button>
            <button className="btn" disabled={sending} onClick={() => setMode('review')}>
              رجوع
            </button>
          </>
        )}
      </div>
    </section>
  );
}
