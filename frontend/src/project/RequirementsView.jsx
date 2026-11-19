import { useState } from 'react';
import { approveRequirements } from '../api/client.js';
import { Dialog, useToast } from '../components/ui.jsx';
import { FIELD_TYPES, fieldRules } from '../lib/labels.js';
import { MSG } from '../lib/messages.js';

/** Request-changes dialog ("طلب تعديل المتطلبات"). */
export function FeedbackDialog({ project, onClose, onDone }) {
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const toast = useToast();

  async function send() {
    if (text.trim().length < 3) {
      setError('اكتب ما تريد تغييره.');
      return;
    }
    setSending(true);
    setError('');
    try {
      const p = await approveRequirements(project.project_id, { approved: false, feedback: text.trim() });
      toast(MSG.feedbackSent);
      onDone(p);
      onClose();
    } catch (e) {
      setError(e.message);
      setSending(false);
    }
  }

  return (
    <Dialog
      title="طلب تعديل المتطلبات"
      description="اكتب ما تريد تغييره. سيعيد المحلّل كتابة المتطلبات ويرسلها لك للمراجعة."
      onClose={onClose}
      testId="feedback-dialog"
      footer={
        <>
          <button type="button" className="btn btn-primary" onClick={send} disabled={sending} data-testid="send-feedback">
            {sending ? 'جاري الإرسال…' : 'إرسال'}
          </button>
          <button type="button" className="btn" onClick={onClose}>
            إلغاء
          </button>
        </>
      }
    >
      <textarea
        className="textarea"
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="مثال: أضف حقل تاريخ آخر توريد."
        aria-label="التعديلات المطلوبة"
        aria-invalid={Boolean(error)}
        data-testid="feedback-input"
      />
      {error && <p className="field-error" role="alert">{error}</p>}
    </Dialog>
  );
}

/** Approve / request-changes buttons, used in the header and at the end of the review. */
export function ReviewActions({ project, onDone }) {
  const [dialog, setDialog] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  async function approve() {
    setSending(true);
    setError('');
    try {
      onDone(await approveRequirements(project.project_id, { approved: true }));
    } catch (e) {
      setError(e.message);
      setSending(false);
    }
  }
  return (
    <div style={{ display: 'grid', gap: 6, justifyItems: 'start' }}>
      <div className="actions">
        <button type="button" className="btn btn-primary" onClick={approve} disabled={sending} data-testid="approve">
          {sending ? 'جاري الإرسال…' : 'الموافقة على المتطلبات'}
        </button>
        <button type="button" className="btn" onClick={() => setDialog(true)} disabled={sending} data-testid="request-changes">
          طلب تعديل
        </button>
      </div>
      {error && <p className="field-error" role="alert">{error}</p>}
      {dialog && <FeedbackDialog project={project} onClose={() => setDialog(false)} onDone={onDone} />}
    </div>
  );
}

/** The requirements document (read-only, or with review actions while awaiting approval). */
export default function RequirementsView({ project, onDone }) {
  const req = project.requirements;
  const dir = req.language === 'ar' ? 'rtl' : 'ltr';
  const reviewing = project.status === 'awaiting_approval';
  const optional = (req.clarification_questions ?? []).filter((q) => !q.blocking && q.suggested_default);
  const assumptions = [...(req.assumptions ?? []), ...optional.map((q) => `${q.question} ${q.suggested_default}`)];

  return (
    <div data-testid="requirements-view">
      {reviewing && (
        <p className="muted small" style={{ paddingBottom: 'var(--bn-s4)' }}>
          راجع المتطلبات التالية. بعد موافقتك يبدأ المهندس بتصميم الهيكل بناءً عليها.
        </p>
      )}

      <section className="section" dir={dir}>
        <h2 className="section-title">نظرة عامة</h2>
        <p className="lead">{req.app.description}</p>
        {req.app.target_users?.length > 0 && (
          <p className="muted small">المستخدمون: {req.app.target_users.join('، ')}</p>
        )}
      </section>

      {req.entities.map((e) => (
        <section key={e.name} className="section" dir={dir} data-testid={`entity-${e.name}`}>
          <h2 className="section-title">{e.label}</h2>
          {e.description && <p className="muted small">{e.description}</p>}
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>الحقل</th>
                  <th>النوع</th>
                  <th>مطلوب</th>
                  <th>القواعد</th>
                </tr>
              </thead>
              <tbody>
                {e.fields.map((f) => (
                  <tr key={f.name}>
                    <td className="strong">
                      {f.label} <span className="mono muted ltr" style={{ fontWeight: 400, fontSize: 12 }}>{f.name}</span>
                    </td>
                    <td>{FIELD_TYPES[f.type] ?? f.type}</td>
                    <td>{f.required ? 'نعم' : 'لا'}</td>
                    <td>{fieldRules(f) || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      <section className="section" dir={dir}>
        <h2 className="section-title">المتطلبات الوظيفية</h2>
        <ol className="list">
          {req.functional_requirements.map((r) => (
            <li key={r.id}>{r.description}</li>
          ))}
        </ol>
      </section>

      <section className="section" dir={dir}>
        <h2 className="section-title">قصص المستخدم ومعايير القبول</h2>
        <ul className="plain-list">
          {req.user_stories.map((s) => {
            const criteria = req.acceptance_criteria.filter((a) => a.story_id === s.id);
            return (
              <li key={s.id} style={{ display: 'grid', gap: 2 }}>
                <strong className="small">
                  {dir === 'rtl'
                    ? `بصفتي ${s.role}: ${s.goal}${s.benefit ? `، حتى ${s.benefit}` : ''}.`
                    : `As ${s.role}, I want to ${s.goal}${s.benefit ? ` so that ${s.benefit}` : ''}.`}
                </strong>
                {criteria.map((a) => (
                  <span key={a.id} className="muted small">
                    {dir === 'rtl'
                      ? `${a.given}. ${a.when}. النتيجة: ${a.then}.`
                      : `Given ${a.given}, when ${a.when}, then ${a.then}.`}
                  </span>
                ))}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="section two-col" dir={dir}>
        <div style={{ display: 'grid', gap: 'var(--bn-s2)', alignContent: 'start' }}>
          <h2 className="section-title">الافتراضات</h2>
          {assumptions.length ? (
            <ul className="list small">{assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
          ) : (
            <p className="muted small">لا توجد افتراضات.</p>
          )}
        </div>
        <div style={{ display: 'grid', gap: 'var(--bn-s2)', alignContent: 'start' }}>
          <h2 className="section-title">خارج النطاق</h2>
          {req.out_of_scope?.length ? (
            <ul className="list small" data-testid="out-of-scope">
              {req.out_of_scope.map((o, i) => (
                <li key={i}>
                  {o.feature}
                  {o.alternative ? <span className="muted">: البديل {o.alternative}</span> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small">لم يُستبعد شيء من فكرتك.</p>
          )}
        </div>
      </section>

      {reviewing && (
        <section className="section">
          <ReviewActions project={project} onDone={onDone} />
        </section>
      )}
    </div>
  );
}
