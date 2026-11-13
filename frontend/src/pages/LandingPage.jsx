import { useEffect, useRef, useState } from 'react';
import { Mark } from '../brand/Logo.jsx';
import AgentSteps from '../components/AgentSteps.jsx';
import Icon from '../components/icons.jsx';
import '../styles/landing.css';

const IMG = (name, small, large) => ({
  src: `/landing/${name}-${large}.webp`,
  srcSet: `/landing/${name}-${small}.webp ${small}w, /landing/${name}-${large}.webp ${large}w`,
});

const AGENTS = [
  { key: 'analyst', name: 'محلّل الأعمال', role: 'يقرأ فكرتك ويكتب المتطلبات، ويسألك إذا نقصت تفاصيل.', input: 'فكرتك بالعربية', output: 'requirements.json' },
  { key: 'architect', name: 'المهندس', role: 'يصمّم الحقول والشاشات وقواعد التحقق قبل كتابة أي كود.', input: 'requirements.json', output: 'architecture.json' },
  { key: 'developer', name: 'المطوّر', role: 'يكتب التطبيق في ثلاثة ملفات، ويصلح العيوب التي يجدها المختبر.', input: 'architecture.json', output: 'index.html · style.css · app.js' },
  { key: 'qa', name: 'مختبر الجودة', role: 'يشغّل ثمانية فحوصات في متصفح حقيقي، ويعيد العيب للمطوّر.', input: 'index.html · app.js', output: 'test_report.json' },
  { key: 'pm', name: 'مدير المشروع', role: 'يجمع مخرجات الجميع ويكتب الخطة والمخاطر مع التسليم.', input: 'كل المخرجات', output: 'project_plan.md · risks.md' },
];

const FEATURES = [
  ['file', 'اكتب فكرتك بكلامك', 'بالعربية أو الإنجليزية، بلهجتك وبدون مصطلحات تقنية.'],
  ['check', 'أنت توافق قبل البناء', 'متطلبات واضحة بحقولها وقواعدها، لا يبدأ شيء قبل موافقتك.'],
  ['folder', 'هيكل قبل الكود', 'ترى الحقول والشاشات وطريقة الحفظ قبل أن يُكتب سطر واحد.'],
  ['refresh', 'اختبار وإصلاح تلقائي', 'ثمانية فحوصات، وإذا فشل فحص يصلحه المطوّر حتى محاولتين.'],
  ['eye', 'معاينة فورية', 'جرّب التطبيق على سطح المكتب والجوال قبل أن تحمّله.'],
  ['download', 'ملف جاهز للتشغيل', 'ملف ZIP يعمل في أي متصفح، بدون تثبيت أو إنترنت.'],
];

// A frozen, realistic moment of a run, drawn with the platform's own component.
const DEMO = {
  project_id: 'demo',
  status: 'developing',
  current_agent: 'developer',
  repair_attempt: 0,
  updated_at: null,
  requirements: { entities: [{ fields: [1, 2, 3, 4, 5] }], functional_requirements: new Array(8).fill(0), user_stories: new Array(4).fill(0) },
  artifacts: [
    { name: 'architecture.json', available: true },
    { name: 'index.html', available: true },
    { name: 'style.css', available: true },
    { name: 'app.js', available: false },
  ],
};

const reducedMotion = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || document.documentElement.dataset.motion === 'reduce';

/** Fade in sections that start below the fold; anything visible at load stays visible. */
function useReveal(root) {
  useEffect(() => {
    if (!root.current || reducedMotion() || !('IntersectionObserver' in window)) return undefined;
    const items = [...root.current.querySelectorAll('.lx-reveal')].filter((el) => el.getBoundingClientRect().top > window.innerHeight);
    items.forEach((el) => el.classList.add('is-hidden'));
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.remove('is-hidden'); io.unobserve(e.target); }
      }),
      { rootMargin: '0px 0px -10% 0px' },
    );
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [root]);
}

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start' });
}

function spotlight(e) {
  const r = e.currentTarget.getBoundingClientRect();
  e.currentTarget.style.setProperty('--mx', `${e.clientX - r.left}px`);
  e.currentTarget.style.setProperty('--my', `${e.clientY - r.top}px`);
}

// ---------- agents diagram ----------
const W = 560;
const H = 470;
const C = { x: W / 2, y: H / 2 - 4 };
const R = 172;
const NODE_R = 34;
const nodes = AGENTS.map((a, i) => {
  const ang = ((-90 + i * 72) * Math.PI) / 180;
  return { ...a, i, x: C.x + R * Math.cos(ang), y: C.y + R * Math.sin(ang) };
});
function edge(from, to, r1, r2) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const d = Math.hypot(dx, dy);
  return { x1: from.x + (dx / d) * r1, y1: from.y + (dy / d) * r1, x2: to.x - (dx / d) * r2, y2: to.y - (dy / d) * r2 };
}

function AgentsDiagram({ active, onSelect, isolated }) {
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="رسم يوضح خمسة وكلاء حول طبقة تنسيق واحدة" className={isolated ? 'lx-isolated' : undefined}>
      <defs>
        <radialGradient id="lx-hub-fill" cx="50%" cy="40%" r="70%">
          <stop offset="0%" stopColor="#4a3b8f" />
          <stop offset="100%" stopColor="#1e1b4b" />
        </radialGradient>
      </defs>
      <polyline className="lx-chain" points={nodes.map((n) => `${n.x},${n.y}`).join(' ')} />
      {nodes.map((n) => {
        const e = edge(C, n, 60, NODE_R + 4);
        return (
          <g key={`l-${n.key}`}>
            <line className={`lx-link${active === n.i ? ' is-active' : ''}`} {...e} />
            <line className="lx-pulse" {...e} style={{ animationDelay: `${n.i * 0.5}s` }} />
          </g>
        );
      })}
      <g className="lx-hub">
        <circle className="orbit" cx={C.x} cy={C.y} r="76" />
        <circle className="core" cx={C.x} cy={C.y} r="56" />
        <g transform={`translate(${C.x - 14} ${C.y - 30})`}>
          <rect x="6" y="0" width="10" height="10" rx="1.6" fill="#eceeec" transform="scale(1.3)" />
          <rect x="0" y="12" width="10" height="10" rx="1.6" fill="#4cc2b0" transform="scale(1.3)" />
          <rect x="12" y="12" width="10" height="10" rx="1.6" fill="#eceeec" transform="scale(1.3)" />
        </g>
        <text x={C.x} y={C.y + 24} textAnchor="middle" fontSize="12" fill="#c8c4da">طبقة التنسيق</text>
      </g>
      <g className="lx-person" aria-hidden="true">
        <circle cx={C.x} cy={C.y - 16} r="12" fill="none" stroke="#9692ae" strokeWidth="1.4" />
        <path d={`M${C.x - 22} ${C.y + 22} q22 -26 44 0`} fill="none" stroke="#9692ae" strokeWidth="1.4" />
        <text x={C.x} y={C.y + 46} textAnchor="middle" fontSize="12" fill="#9692ae">أنت تنسّق يدوياً</text>
      </g>
      {nodes.map((n) => (
        <g
          key={n.key}
          className={`lx-node${active === n.i ? ' is-active' : ''}`}
          tabIndex={0}
          role="button"
          aria-pressed={active === n.i}
          aria-label={n.name}
          onMouseEnter={() => onSelect(n.i, true)}
          onFocus={() => onSelect(n.i, true)}
          onClick={() => onSelect(n.i, true)}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(n.i, true)}
        >
          <circle className="halo" cx={n.x} cy={n.y} r={NODE_R + 14} />
          <circle className="ring" cx={n.x} cy={n.y} r={NODE_R} />
          <text className="num" x={n.x} y={n.y + 4} textAnchor="middle">{`0${n.i + 1}`}</text>
          <text x={n.x} y={n.y + NODE_R + 22} textAnchor="middle" fontSize="14" fontWeight="600">{n.name}</text>
        </g>
      ))}
    </svg>
  );
}

function AgentsSection() {
  const [active, setActive] = useState(0);
  const [isolated, setIsolated] = useState(false);
  const pinned = useRef(false);

  // Walk through the agents in order until the visitor picks one.
  useEffect(() => {
    if (reducedMotion() || isolated) return undefined;
    const t = setInterval(() => {
      if (!pinned.current) setActive((a) => (a + 1) % AGENTS.length);
    }, 3200);
    return () => clearInterval(t);
  }, [isolated]);

  const select = (i, pin) => {
    pinned.current = pin;
    setActive(i);
  };
  const a = AGENTS[active];

  return (
    <section className="lx-section lx-agents" id="agents" aria-labelledby="agents-title">
      <div className="lx-agents-bg" aria-hidden="true">
        <img {...IMG('agents', 900, 1376)} sizes="100vw" alt="" loading="lazy" decoding="async" />
      </div>
      <div className="lx-wrap">
        <div className="lx-head lx-reveal">
          <span className="lx-eyebrow">الوكلاء</span>
          <h2 className="lx-h2" id="agents-title">خمسة وكلاء متخصصين، وطبقة واحدة تنسّق بينهم.</h2>
          <p className="lx-lead">
            الوكلاء المتخصصون أثبتوا قدرتهم كلٌّ في مجاله، لكنهم يعملون منفصلين وينتظرون من ينسّق بينهم. بُنيان هو هذه الطبقة: كل وكيل يبني على ما سلّمه الذي قبله، وأنت توافق قبل أن يبدأ البناء.
          </p>
        </div>
        <div className="lx-agents-grid">
          <figure className="lx-diagram lx-reveal" style={{ margin: 0 }}>
            <div className="lx-diagram-bar">
              <span className="lx-small mono">FIG. 1 · BUNYAN</span>
              <div className="lx-toggle" role="group" aria-label="طريقة العمل">
                <button type="button" aria-pressed={isolated} onClick={() => setIsolated(true)}>منفصلون</button>
                <button type="button" aria-pressed={!isolated} onClick={() => setIsolated(false)}>مع بُنيان</button>
              </div>
            </div>
            <AgentsDiagram active={active} onSelect={select} isolated={isolated} />
            <figcaption className="lx-small" style={{ padding: '4px 4px 0' }}>
              {isolated
                ? 'بدون طبقة تنسيق: كل وكيل يعمل لوحده، وأنت تنقل النتائج بينهم بنفسك.'
                : 'مع بُنيان: تنتقل المخرجات من وكيل لآخر بالترتيب، وتمر عليك عند المتطلبات.'}
            </figcaption>
          </figure>

          <div className="lx-panel lx-reveal">
            <div className="lx-agent-card" aria-live="polite">
              <div className="role">
                <h3 className="lx-h3">{a.name}</h3>
                <span className="mono lx-small" style={{ color: 'var(--lx-gold)' }}>{`0${active + 1} / 05`}</span>
              </div>
              <p className="lx-lead" style={{ fontSize: 16 }}>{a.role}</p>
              <dl className="lx-io" style={{ margin: 0 }}>
                <dt>يستلم</dt>
                <dd>{a.input}</dd>
                <dt>يسلّم</dt>
                <dd>{a.output}</dd>
              </dl>
            </div>
            <div className="lx-agent-list" role="group" aria-label="اختر وكيلاً">
              {AGENTS.map((x, i) => (
                <button key={x.key} type="button" aria-pressed={active === i} onClick={() => select(i, true)}>
                  {x.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function LandingPage() {
  const root = useRef(null);
  const [solid, setSolid] = useState(false);
  useReveal(root);

  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 40);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="lx" ref={root}>
      <header className="lx-nav" data-solid={solid}>
        <div className="lx-wrap lx-nav-row">
          <a className="lx-logo" href="#/" aria-label="بُنيان، الصفحة الرئيسية">
            <Mark size={22} /> بُنيان
          </a>
          <nav className="lx-links" aria-label="أقسام الصفحة">
            <button type="button" onClick={() => scrollTo('vision')}>الرؤية</button>
            <button type="button" onClick={() => scrollTo('agents')}>الوكلاء</button>
            <button type="button" onClick={() => scrollTo('product')}>المنتج</button>
          </nav>
          <div className="lx-nav-cta">
            <a className="lx-btn lx-btn-ghost" href="#/projects">مشاريعي</a>
            <a className="lx-btn lx-btn-primary" href="#/new">ابدأ مشروعك</a>
          </div>
        </div>
      </header>

      <main>
        {/* 1 · Hero */}
        <section className="lx-hero" aria-labelledby="hero-title">
          <div className="lx-hero-bg" aria-hidden="true">
            <img {...IMG('hero', 900, 1600)} sizes="100vw" alt="" fetchpriority="high" decoding="async" />
          </div>
          <div className="lx-wrap lx-hero-meta">
            <div className="lx-hero-content">
              <span className="lx-eyebrow">شركة بُنيان للذكاء الاصطناعي · الرياض</span>
              <h1 className="lx-h1" id="hero-title">
                وكلاء ذكاء اصطناعي يبنون تطبيقك، <span className="lx-grad-text">من الرياض.</span>
              </h1>
              <p className="lx-lead">
                اكتب فكرتك بالعربية، ويحوّلها فريق من خمسة وكلاء إلى تطبيق ويب يعمل: متطلبات وهيكل وكود مختبَر. وأنت صاحب القرار في كل خطوة.
              </p>
              <div className="lx-actions">
                <a className="lx-btn lx-btn-primary" href="#/new" data-testid="cta-start">
                  ابدأ مشروعك <span className="arrow" aria-hidden="true">←</span>
                </a>
                <button type="button" className="lx-btn lx-btn-ghost" onClick={() => scrollTo('vision')}>تعرّف علينا</button>
              </div>
            </div>
            <p className="lx-coords" aria-label="الرياض، المملكة العربية السعودية">
              RUH · 24.7136° N · 46.6753° E
              <span>الرياض، المملكة العربية السعودية</span>
            </p>
          </div>
        </section>

        {/* 2 · Vision */}
        <section className="lx-section lx-vision lx-glow" id="vision" aria-labelledby="vision-title">
          <div className="lx-wrap lx-vision-grid">
            <figure className="lx-figure lx-vision-figure lx-reveal">
              <img {...IMG('vision', 900, 1290)} sizes="(max-width: 1000px) 100vw, 50vw" alt="أبراج مركز الملك عبدالله المالي في الرياض وقت الغروب" loading="lazy" decoding="async" />
              <figcaption className="lx-figcap">
                <span>مركز الملك عبدالله المالي</span>
                <span className="mono">KAFD</span>
              </figcaption>
            </figure>
            <div style={{ display: 'grid', gap: 28 }} className="lx-reveal">
              <span className="lx-eyebrow">رؤيتنا</span>
              <h2 className="lx-h2" id="vision-title">نتخيّل مدينة يستطيع فيها كل صاحب فكرة أن يبني أداته.</h2>
              <ol className="lx-statements">
                <li>أي شخص عنده فكرة يستطيع أن يبني التطبيق الذي يحتاجه، بدون فريق برمجة وبدون انتظار.</li>
                <li>يكتبها بلغته، ويراجع كل خطوة قبل أن تُبنى الخطوة التالية.</li>
                <li>ونبدأ من الرياض، بتطبيقات صغيرة تدير بيانات حقيقية، ونكبر معها.</li>
              </ol>
            </div>
          </div>
        </section>

        {/* 3 · Agents */}
        <AgentsSection />

        {/* 4 · Product */}
        <section className="lx-section lx-product" id="product" aria-labelledby="product-title">
          <div className="lx-wrap">
            <div className="lx-head lx-reveal">
              <span className="lx-eyebrow">المنتج</span>
              <h2 className="lx-h2" id="product-title">منصة واحدة، من الفكرة إلى ملف جاهز.</h2>
              <p className="lx-lead">تابع كل وكيل وهو يعمل، راجع المتطلبات قبل البناء، وشاهد التطبيق قبل تحميله.</p>
            </div>
            <div className="lx-stage lx-reveal">
              <img {...IMG('product', 900, 1290)} sizes="100vw" alt="" loading="lazy" decoding="async" aria-hidden="true" />
              <div className="lx-window" role="img" aria-label="شاشة تقدّم البناء في منصة بُنيان">
                <div className="lx-window-chrome" aria-hidden="true">
                  <i /><i /><i />
                  <span>bunyan.app/projects/inventory</span>
                </div>
                <div className="lx-window-side" aria-hidden="true">
                  <span className="logo"><Mark size={14} /> بُنيان</span>
                  <span className="nav-link" aria-current="page">مدير المخزون</span>
                  <span className="nav-link">مواعيد العيادة</span>
                  <span className="nav-link">مهام الفريق</span>
                </div>
                <div className="lx-window-main">
                  <div style={{ display: 'grid', gap: 2 }}>
                    <strong>مدير المخزون</strong>
                    <span className="muted small">وافقت على المتطلبات · البناء جارٍ</span>
                  </div>
                  <AgentSteps project={DEMO} demo />
                </div>
              </div>
            </div>
            <div className="lx-features">
              {FEATURES.map(([icon, title, text]) => (
                <div key={title} className="lx-card lx-reveal" onMouseMove={spotlight}>
                  <span className="lx-card-icon"><Icon name={icon} size={18} /></span>
                  <h3 className="lx-h3" style={{ fontSize: 16 }}>{title}</h3>
                  <p className="lx-small" style={{ color: 'var(--lx-text-2)' }}>{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 5 · Call to action */}
        <section className="lx-section lx-cta" aria-labelledby="cta-title">
          <div className="lx-cta-bg" aria-hidden="true">
            <img {...IMG('cta', 900, 1529)} sizes="100vw" alt="" loading="lazy" decoding="async" />
          </div>
          <div className="lx-wrap lx-cta-inner lx-reveal">
            <span className="lx-cta-mark"><Mark size={30} /></span>
            <h2 className="lx-h2" id="cta-title">
              كل فكرة تستحق فريقاً يبنيها.
              <br />
              <span className="lx-grad-text">بُنيان هو هذا الفريق.</span>
            </h2>
            <p className="lx-lead" style={{ marginInline: 'auto' }}>صُمّم في الرياض، لكل من عنده فكرة ويريد أن يراها تعمل.</p>
            <div className="lx-actions" style={{ justifyContent: 'center' }}>
              <a className="lx-btn lx-btn-primary" href="#/new">ابدأ مشروعك <span className="arrow" aria-hidden="true">←</span></a>
              <a className="lx-btn lx-btn-ghost" href="#/help">كيف يعمل</a>
            </div>
          </div>
        </section>
      </main>

      {/* 6 · Footer */}
      <footer className="lx-foot">
        <div className="lx-foot-bg" aria-hidden="true">
          <img {...IMG('footer', 1200, 2400)} sizes="100vw" alt="" loading="lazy" decoding="async" />
        </div>
        <div className="lx-wrap lx-foot-grid">
          <div style={{ display: 'grid', gap: 14, alignContent: 'start' }}>
            <a className="lx-logo" href="#/"><Mark size={22} /> بُنيان</a>
            <p className="lx-small" style={{ maxWidth: '36ch', color: 'var(--lx-text-2)' }}>
              خمسة وكلاء ذكاء اصطناعي يحوّلون فكرتك إلى تطبيق ويب يعمل.
            </p>
            <div className="lx-social">
              <a href="https://github.com/lolo67fa/bunyan-ai" target="_blank" rel="noreferrer" aria-label="بُنيان على GitHub">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.91.83.09-.65.35-1.08.63-1.33-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.5 9.5 0 0 1 5 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.93.36.31.68.92.68 1.86v2.75c0 .27.18.58.69.48A10 10 0 0 0 12 2z" />
                </svg>
              </a>
            </div>
          </div>
          <div>
            <h4>المنصة</h4>
            <ul>
              <li><a href="#/new">مشروع جديد</a></li>
              <li><a href="#/projects">مشاريعي</a></li>
              <li><a href="#/settings">الإعدادات</a></li>
            </ul>
          </div>
          <div>
            <h4>بُنيان</h4>
            <ul>
              <li><button type="button" onClick={() => scrollTo('vision')}>الرؤية</button></li>
              <li><button type="button" onClick={() => scrollTo('agents')}>الوكلاء</button></li>
              <li><button type="button" onClick={() => scrollTo('product')}>المنتج</button></li>
            </ul>
          </div>
          <div>
            <h4>المساعدة</h4>
            <ul>
              <li><a href="#/help">كيف يعمل بُنيان</a></li>
              <li><a href="#/help">الأسئلة الشائعة</a></li>
            </ul>
          </div>
        </div>
        <div className="lx-wrap">
          <div className="lx-foot-bar">
            <span>© 2026 بُنيان · نادي طويق، جامعة الملك سعود</span>
            <span className="mono ltr">MADE IN RIYADH · 24.7136° N</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
