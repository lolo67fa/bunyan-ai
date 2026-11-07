import { useState } from 'react';
import { MODE, createProject } from '../api/client.js';
import { goToProject } from '../hooks/useHashRoute.js';
import { SAMPLE_IDEAS } from '../mocks/samples.js';

const MIN_LEN = 10;
const MAX_LEN = 2000;

export default function IdeaPage() {
  const [idea, setIdea] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    const text = idea.trim();
    if (text.length < MIN_LEN) {
      setError(`اكتب الفكرة بتفصيل أكثر (${MIN_LEN} أحرف على الأقل).`);
      return;
    }
    setSending(true);
    setError('');
    try {
      const project = await createProject(text);
      goToProject(project.id);
    } catch (err) {
      setError(err.message);
      setSending(false);
    }
  }

  return (
    <div className="page">
      <section className="hero">
        <h1>
          حوّل فكرتك إلى تطبيق <span className="accent">يشتغل</span>
        </h1>
        <p className="muted">
          اكتب فكرة تطبيقك بالعربي، وخمسة وكلاء ذكاء اصطناعي يحللونها ويصممونها ويبرمجونها ويختبرونها.
        </p>
      </section>

      <form className="card" onSubmit={onSubmit} noValidate data-testid="idea-form">
        <label htmlFor="idea" className="block">
          فكرة التطبيق
        </label>
        <textarea
          id="idea"
          rows={6}
          maxLength={MAX_LEN}
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="مثال: أبغى موقع لإدارة المخزون أقدر أضيف فيه المنتجات وأعدل كمياتها وأسعارها وأحذفها."
          data-testid="idea-input"
        />
        <div className="form-foot">
          <span className="muted small">
            {idea.length}/{MAX_LEN}
          </span>
          <span className="muted small">النطاق: تطبيقات إضافة وعرض وتعديل وحذف فقط</span>
        </div>
        {error && (
          <p className="alert alert-error" data-testid="idea-error">
            {error}
          </p>
        )}
        <button className="btn btn-primary" disabled={sending} data-testid="submit-idea">
          {sending ? 'جاري الإرسال…' : 'ابدأ البناء'}
        </button>
      </form>

      {MODE === 'mock' && (
        <section className="card">
          <h2 className="small-title">أفكار تجريبية (عينات محلل الأعمال)</h2>
          <div className="chips">
            {SAMPLE_IDEAS.map((s) => (
              <button key={s.key} type="button" className="chip" onClick={() => setIdea(s.idea)}>
                {s.label}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
