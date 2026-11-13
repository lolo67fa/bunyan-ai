import { useMemo, useState } from 'react';
import { submitAnswers } from '../api/client.js';
import { useToast } from '../components/ui.jsx';
import { go } from '../hooks/useHashRoute.js';
import { saveDraft } from './draft.js';

const OTHER = '__other__';

/** "بعض التفاصيل قبل كتابة المتطلبات" — answers the analyst's questions. */
export default function ClarificationView({ project, onDone }) {
  const req = project.requirements;
  const dir = req.language === 'ar' ? 'rtl' : 'ltr';
  const questions = req.clarification_questions ?? [];
  const toast = useToast();

  // Pre-select the suggested option where the analyst gave one.
  const initial = useMemo(() => {
    const o = {};
    questions.forEach((q) => {
      if (q.options?.includes(q.suggested_default)) o[q.id] = q.suggested_default;
    });
    return o;
  }, [questions]);
  const [choice, setChoice] = useState(initial);
  const [text, setText] = useState({});
  const [errors, setErrors] = useState({});
  const [sending, setSending] = useState(false);
  const [serverError, setServerError] = useState('');

  const valueOf = (q) =>
    q.options?.length && choice[q.id] && choice[q.id] !== OTHER ? choice[q.id] : (text[q.id] ?? '').trim();
  const required = questions.filter((q) => q.blocking);
  const answered = required.filter((q) => valueOf(q)).length;

  async function onSubmit(e) {
    e.preventDefault();
    const missing = {};
    const answers = {};
    questions.forEach((q) => {
      const v = valueOf(q);
      if (v) answers[q.id] = v;
      else if (q.blocking) missing[q.id] = q.options?.length ? 'اختر إجابة للمتابعة.' : 'اكتب إجابة للمتابعة.';
    });
    setErrors(missing);
    if (Object.keys(missing).length) return;
    setSending(true);
    setServerError('');
    try {
      const p = await submitAnswers(project.project_id, answers);
      toast('أُرسلت إجاباتك. يكمل المحلّل الآن.');
      onDone(p);
    } catch (err) {
      setServerError(err.message);
      setSending(false);
    }
  }

  return (
    <div className="page page-narrow">
      <nav className="crumbs" aria-label="المسار">
        <a href="#/projects">المشاريع</a> / <span>فكرة جديدة</span>
      </nav>
      <div style={{ display: 'grid', gap: 6 }}>
        <span className="eyebrow" style={{ color: 'var(--bn-warning)' }}>محلّل الأعمال · ينتظر إجاباتك</span>
        <h1 className="title">بعض التفاصيل قبل كتابة المتطلبات</h1>
        <p className="lead small">أجب عن الأسئلة المطلوبة. إذا لم تكن متأكداً اترك الاختيار المقترح، وستراه لاحقاً ضمن الافتراضات.</p>
      </div>

      <div className="quote">
        <span dir="auto">«{project.idea}»</span>
        <button type="button" className="link-btn small" onClick={() => { saveDraft(project.idea); go('/new'); }}>
          تعديل
        </button>
      </div>

      <form onSubmit={onSubmit} noValidate data-testid="clarification-form">
        {questions.map((q) => (
          <fieldset
            key={q.id}
            className="section"
            style={{ border: 0, margin: 0, paddingInline: 0 }}
            dir={dir}
            data-testid={`question-${q.id}`}
          >
            <legend className="field-label" style={{ padding: 0, display: 'flex', gap: 8, alignItems: 'baseline' }}>
              <strong>{q.question}</strong>
              <span className="muted small">{q.blocking ? 'مطلوب' : 'اختياري'}</span>
            </legend>
            {q.reason && <p className="muted small">{q.reason}</p>}
            {q.options?.length > 0 && (
              <div className="choice-list" role="radiogroup">
                {[...q.options, OTHER].map((opt) => (
                  <label key={opt} className="choice">
                    <input
                      type="radio"
                      name={q.id}
                      value={opt}
                      checked={choice[q.id] === opt}
                      onChange={() => { setChoice({ ...choice, [q.id]: opt }); setErrors({ ...errors, [q.id]: null }); }}
                    />
                    {opt === OTHER ? 'إجابة أخرى' : opt}
                    {opt === q.suggested_default && <span className="muted">(مقترح)</span>}
                  </label>
                ))}
              </div>
            )}
            {(!q.options?.length || choice[q.id] === OTHER) && (
              <textarea
                className="textarea"
                rows={2}
                value={text[q.id] ?? ''}
                aria-label={q.question}
                aria-invalid={Boolean(errors[q.id])}
                placeholder={q.suggested_default ?? 'اكتب إجابتك'}
                onChange={(e) => { setText({ ...text, [q.id]: e.target.value }); setErrors({ ...errors, [q.id]: null }); }}
              />
            )}
            {!q.blocking && q.suggested_default && !q.options?.includes(q.suggested_default) && (
              <p className="muted small">إذا تركته فارغاً: {q.suggested_default}</p>
            )}
            {errors[q.id] && <p className="field-error" role="alert">{errors[q.id]}</p>}
          </fieldset>
        ))}

        {serverError && <p className="field-error" role="alert">{serverError}</p>}

        <div className="page-head" style={{ alignItems: 'center', borderTop: '1px solid var(--bn-border)', paddingTop: 'var(--bn-s4)' }}>
          <div className="actions">
            <button className="btn btn-primary" disabled={sending} data-testid="submit-answers">
              {sending ? 'جاري الإرسال…' : 'إرسال الإجابات'}
            </button>
            <span className="muted small num">{answered} من {required.length} أسئلة مطلوبة</span>
          </div>
          <a className="btn" href="#/projects">رجوع</a>
        </div>
      </form>
    </div>
  );
}
