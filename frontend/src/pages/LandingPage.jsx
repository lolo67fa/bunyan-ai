import Logo, { Mark } from '../brand/Logo.jsx';
import AgentSteps from '../components/AgentSteps.jsx';

const AGENTS = [
  ['محلّل الأعمال', 'يقرأ فكرتك ويكتب المتطلبات، ويسألك إذا نقصت تفاصيل.'],
  ['المهندس', 'يصمّم الحقول والشاشات وطريقة الحفظ قبل كتابة أي كود.'],
  ['المطوّر', 'يكتب التطبيق في ثلاثة ملفات: HTML وCSS وJavaScript.'],
  ['مختبر الجودة', 'يشغّل ثمانية فحوصات في متصفح حقيقي، ويعيد العيب للمطوّر.'],
  ['مدير المشروع', 'يلخّص الخطة والمخاطر في وثيقة واحدة مع التسليم.'],
];

const GETS = [
  ['اكتب فكرتك بكلامك', 'بالعربية أو الإنجليزية، بدون مصطلحات تقنية.'],
  ['متطلبات واضحة', 'حقول وقواعد وقصص مستخدم تراجعها وتوافق عليها.'],
  ['هيكل قبل الكود', 'تعرف شكل التطبيق قبل أن يُكتب سطر واحد.'],
  ['اختبار في متصفح حقيقي', 'ثمانية فحوصات للإضافة والعرض والتعديل والحذف والحفظ.'],
  ['ملف ZIP جاهز', 'افتح index.html في أي متصفح، بدون تثبيت أو إنترنت.'],
  ['أنت تقرر', 'لا يبدأ البناء قبل موافقتك على المتطلبات.'],
];

const EXAMPLES = [
  ['مدير المهام', 'المهام مع المسؤول وتاريخ التسليم والأولوية والحالة.'],
  ['مدير المخزون', 'المنتجات بأسعارها وكمياتها، وتمييز الكميات المنخفضة.'],
  ['حجز المواعيد', 'اسم المراجع والخدمة والتاريخ والوقت، مع التعديل والإلغاء.'],
];

// A frozen, realistic moment of a run, rendered with the real component.
const DEMO = {
  project_id: 'demo',
  status: 'developing',
  current_agent: 'developer',
  repair_attempt: 0,
  updated_at: null,
  requirements: {
    entities: [{ fields: [1, 2, 3, 4, 5] }],
    functional_requirements: new Array(8).fill(0),
    user_stories: new Array(4).fill(0),
  },
  artifacts: [
    { name: 'architecture.json', available: true },
    { name: 'index.html', available: true },
    { name: 'style.css', available: true },
    { name: 'app.js', available: false },
  ],
};

export default function LandingPage() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <div className="landing-inner landing-nav-row">
          <Logo />
          <nav className="landing-links" aria-label="أقسام الصفحة">
            <a href="#/help">كيف يعمل</a>
            <a href="#/projects">مشاريعي</a>
          </nav>
          <a className="btn btn-primary btn-sm" href="#/new">ابدأ مشروعك</a>
        </div>
      </header>

      <main>
        <section className="landing-inner landing-hero">
          <div style={{ display: 'grid', gap: 'var(--bn-s4)', maxWidth: 560 }}>
            <h1 className="display landing-title">من فكرة إلى تطبيق.</h1>
            <p className="lead">
              اكتب فكرة تطبيقك بالعربية، ويحوّلها خمسة وكلاء ذكاء اصطناعي إلى متطلبات وهيكل وكود مختبَر، تراجع كل خطوة وتقرر.
            </p>
            <div className="actions">
              <a className="btn btn-primary btn-lg" href="#/new" data-testid="cta-start">ابدأ مشروعك</a>
              <a className="btn btn-lg" href="#/help">كيف يعمل</a>
            </div>
            <p className="muted small">تطبيقات ويب لإدارة البيانات: إضافة وعرض وتعديل وحذف.</p>
          </div>

          <figure className="landing-shot" aria-label="مثال من شاشة تقدّم البناء">
            <div className="landing-shot-side">
              <span className="logo" style={{ fontSize: 13 }}><Mark size={14} /> بُنيان</span>
              <span className="nav-link" aria-current="page">مدير المخزون</span>
              <span className="nav-link">مواعيد العيادة</span>
              <span className="nav-link">مهام الفريق</span>
            </div>
            <div className="landing-shot-main">
              <div style={{ display: 'grid', gap: 2 }}>
                <strong>مدير المخزون</strong>
                <span className="muted small">وافقت على المتطلبات · البناء جارٍ</span>
              </div>
              <AgentSteps project={DEMO} demo />
            </div>
          </figure>
        </section>

        <section className="landing-inner landing-section">
          <div className="landing-head">
            <h2 className="title">خمسة وكلاء، وأنت تقرر</h2>
            <p className="muted small">كل وكيل يبني على ما سلّمه الذي قبله، وتوقّف أنت السير عند المتطلبات.</p>
          </div>
          <ol className="landing-agents">
            {AGENTS.map(([n, d], i) => (
              <li key={n}>
                <span className="num muted small">{i + 1}</span>
                <strong>{n}</strong>
                <p className="muted small">{d}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-inner landing-section landing-split">
          <h2 className="title">ما تحصل عليه</h2>
          <div className="landing-grid">
            {GETS.map(([t, d]) => (
              <div key={t}>
                <strong className="small">{t}</strong>
                <p className="muted small">{d}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="landing-inner landing-section">
          <div className="landing-head"><h2 className="title">أمثلة لما يمكن بناؤه</h2></div>
          <div className="landing-examples">
            {EXAMPLES.map(([t, d]) => (
              <div key={t}>
                <strong>{t}</strong>
                <p className="muted small">{d}</p>
              </div>
            ))}
          </div>
          <p className="muted small">لا يبني بُنيان حالياً تطبيقات الجوال أو الألعاب، ولا أنظمة الدفع أو تسجيل الدخول.</p>
        </section>

        <section className="landing-inner landing-cta">
          <h2 className="title">فكرتك هي البداية. بُنيان يتولى البناء.</h2>
          <a className="btn btn-primary btn-lg" href="#/new">ابدأ مشروعك</a>
        </section>
      </main>

      <footer className="landing-inner landing-foot">
        <span className="muted small">بُنيان · نادي طويق، جامعة الملك سعود</span>
        <a className="small" href="#/help">المساعدة</a>
      </footer>
    </div>
  );
}
