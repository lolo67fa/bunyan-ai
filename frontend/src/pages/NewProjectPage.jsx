import { useState } from 'react';
import { createProject } from '../api/client.js';
import { goToProject } from '../hooks/useHashRoute.js';
import { rememberProject } from '../lib/prefs.js';
import { takeDraft } from '../project/draft.js';

const MIN = 20;
const MAX = 1000;

const EXAMPLES = [
  ['إدارة المخزون', 'أبغى موقع لإدارة المخزون أقدر أضيف فيه المنتجات وأعدل كمياتها وأسعارها وأحذف المنتجات.'],
  ['مهام الفريق', 'أريد تطبيقاً لمهام الفريق: أضيف المهمة مع المسؤول عنها وتاريخ التسليم وحالتها، وأعدّلها وأحذفها.'],
  ['مواعيد العيادة', 'أحتاج موقعاً لحجز مواعيد العيادة: اسم المراجع ورقم جواله والخدمة والتاريخ والوقت، مع التعديل والإلغاء.'],
  ['سجلات الطلاب', 'أبغى سجل للطلاب فيه الاسم والرقم الجامعي والتخصص والمعدل، أقدر أضيف وأعدل وأحذف وأبحث.'],
  ['حجوزات القاعات', 'نظام بسيط لحجوزات القاعات: اسم القاعة والجهة الحاجزة والتاريخ ووقت البداية والنهاية.'],
];

export default function NewProjectPage() {
  const [idea, setIdea] = useState(takeDraft);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const len = idea.trim().length;

  async function onSubmit(e) {
    e.preventDefault();
    if (len < MIN) {
      setError(`اكتب ${MIN} حرفاً على الأقل: ما البيانات التي تريد حفظها وما الذي تريد فعله بها.`);
      return;
    }
    setSending(true);
    setError('');
    try {
      const project = await createProject(idea.trim());
      rememberProject(project);
      goToProject(project.project_id);
    } catch (err) {
      setError(err.message);
      setSending(false);
    }
  }

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <h1 className="title">مشروع جديد</h1>
          <p className="lead small">صف التطبيق الذي تريده بكلامك. إذا احتاج المحلّل تفاصيل أكثر سيسألك قبل أن يكمل.</p>
        </div>
      </div>

      <form onSubmit={onSubmit} noValidate style={{ display: 'grid', gap: 'var(--bn-s5)' }} data-testid="idea-form">
        <div className="field">
          <label htmlFor="idea">الفكرة</label>
          <textarea
            id="idea"
            className="textarea"
            rows={7}
            maxLength={MAX}
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            aria-invalid={Boolean(error)}
            aria-describedby="idea-help"
            placeholder="مثال: أبغى موقع لإدارة المخزون أقدر أضيف فيه المنتجات وأعدل كمياتها وأسعارها وأحذفها."
            data-testid="idea-input"
          />
          <div className="field-foot" id="idea-help">
            <span>العربية أو الإنجليزية. {MIN} حرفاً على الأقل.</span>
            <span className="num ltr">{idea.length} / {MAX}</span>
          </div>
          {error && (
            <p className="field-error" role="alert" data-testid="idea-error">
              {error}
            </p>
          )}
        </div>

        <div className="actions small" style={{ gap: 'var(--bn-s4)' }}>
          <span className="muted">أمثلة:</span>
          {EXAMPLES.map(([label, text]) => (
            <button key={label} type="button" className="link-btn" onClick={() => { setIdea(text); setError(''); }}>
              {label}
            </button>
          ))}
        </div>

        <div className="page-head" style={{ alignItems: 'center' }}>
          <details className="disclosure">
            <summary>ما الذي يمكن لبُنيان بناؤه؟</summary>
            <div>
              <p>مواقع ويب بسيطة لإدارة نوع واحد من البيانات: إضافة وعرض وتعديل وحذف، مع البحث والترتيب والتحقق من الحقول.</p>
              <p>لا يبني حالياً تطبيقات جوال أو ألعاباً، ولا أنظمة فيها دفع أو تسجيل دخول أو قاعدة بيانات خارجية.</p>
            </div>
          </details>
          <button className="btn btn-primary btn-lg" disabled={sending} data-testid="submit-idea">
            {sending ? 'جاري الإرسال…' : 'حلّل فكرتي'}
          </button>
        </div>
      </form>

      <p className="muted small" style={{ borderTop: '1px solid var(--bn-border)', paddingTop: 'var(--bn-s4)' }}>
        لن نبدأ بناء أي شيء قبل موافقتك على المتطلبات.
      </p>
    </div>
  );
}
