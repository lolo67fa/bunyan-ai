import { useState } from 'react';
import { submitAnswers } from '../api/client.js';

const OTHER = '__other__';

/**
 * Shows requirements.clarification_questions when status is needs_clarification.
 * Blocking questions must be answered; optional ones already have a suggested_default.
 * Sends { "Q-1": "...", "Q-2": "..." } — same shape as samples/answers/vague_idea_answers.json.
 */
export default function ClarificationForm({ project, onSubmitted }) {
  const req = project.requirements;
  const dir = req.language === 'ar' ? 'rtl' : 'ltr';
  const questions = req.clarification_questions ?? [];

  const [choice, setChoice] = useState({});
  const [text, setText] = useState({});
  const [errors, setErrors] = useState({});
  const [sending, setSending] = useState(false);
  const [serverError, setServerError] = useState('');

  const valueOf = (q) => {
    if (q.options?.length && choice[q.id] && choice[q.id] !== OTHER) return choice[q.id];
    return (text[q.id] ?? '').trim();
  };

  async function onSubmit(e) {
    e.preventDefault();
    const missing = {};
    const answers = {};
    for (const q of questions) {
      const v = valueOf(q);
      if (v) answers[q.id] = v;
      else if (q.blocking) missing[q.id] = 'هذا السؤال مطلوب';
    }
    setErrors(missing);
    if (Object.keys(missing).length) return;

    setSending(true);
    setServerError('');
    try {
      onSubmitted(await submitAnswers(project.id, answers));
    } catch (err) {
      setServerError(err.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="card" onSubmit={onSubmit} noValidate data-testid="clarification-form">
      <h2>محلل الأعمال يحتاج توضيح</h2>
      <p className="muted">جاوب على الأسئلة عشان يكمل تحليل فكرتك.</p>

      {questions.map((q) => (
        <fieldset key={q.id} className="question" dir={dir} data-testid={`question-${q.id}`}>
          <legend>
            <span className="ltr qid">{q.id}</span> {q.question}
            {q.blocking ? <span className="tag tag-red">مطلوب</span> : <span className="tag">اختياري</span>}
          </legend>
          {q.reason && <p className="muted small">{q.reason}</p>}

          {q.options?.length > 0 && (
            <div className="options">
              {[...q.options, OTHER].map((opt) => (
                <label key={opt} className="option">
                  <input
                    type="radio"
                    name={q.id}
                    value={opt}
                    checked={choice[q.id] === opt}
                    onChange={() => setChoice({ ...choice, [q.id]: opt })}
                  />
                  {opt === OTHER ? 'إجابة أخرى' : opt}
                </label>
              ))}
            </div>
          )}

          {(!q.options?.length || choice[q.id] === OTHER) && (
            <textarea
              rows={2}
              value={text[q.id] ?? ''}
              onChange={(e) => setText({ ...text, [q.id]: e.target.value })}
              placeholder={q.suggested_default ?? 'اكتب إجابتك'}
              aria-label={q.question}
            />
          )}

          {!q.blocking && q.suggested_default && (
            <p className="muted small">إذا ما جاوبت: {q.suggested_default}</p>
          )}
          {errors[q.id] && <p className="field-error">{errors[q.id]}</p>}
        </fieldset>
      ))}

      {serverError && <p className="alert alert-error">{serverError}</p>}
      <button className="btn btn-primary" disabled={sending} data-testid="submit-answers">
        {sending ? 'جاري الإرسال…' : 'إرسال الإجابات'}
      </button>
    </form>
  );
}
