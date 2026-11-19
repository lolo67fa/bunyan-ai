import { downloadUrl } from '../api/client.js';
import Icon from '../components/icons.jsx';
import { projectHref } from '../hooks/useHashRoute.js';
import { projectSlug } from '../lib/labels.js';
import { MSG } from '../lib/messages.js';

const FILES = [
  ['index.html', 'الصفحة والنموذج'],
  ['style.css', 'التنسيق واتجاه الصفحة'],
  ['app.js', 'الإضافة والتعديل والحذف والحفظ'],
];

/** "تطبيقك جاهز!": shown when the run has completed. */
export default function DeliveryView({ project }) {
  const req = project.requirements;
  const m = project.metrics;
  const id = project.project_id;
  const zip = downloadUrl(id);
  const name = `${projectSlug(project)}.zip`;
  const entity = req?.entities?.[0];
  const passedAll = m && m.checks_passed === m.checks_total;

  return (
    <div className="page page-narrow" data-testid="delivery">
      <nav className="crumbs" aria-label="المسار">
        <a href="#/projects">المشاريع</a> / <span>{req?.app?.name}</span>
      </nav>

      <div style={{ display: 'grid', gap: 'var(--bn-s3)', justifyItems: 'start' }}>
        <span className={`result-mark${passedAll ? '' : ' warn'}`}>
          <Icon name={passedAll ? 'check' : 'alert'} size={20} />
        </span>
        <h1 className="title">{passedAll ? 'تطبيقك جاهز!' : 'تطبيقك جاهز مع ملاحظات'}</h1>
        <p className="lead">
          {req?.app?.name}: {req?.app?.description}
        </p>
        <div className="actions">
          {zip ? (
            <a className="btn btn-primary" href={zip} download={name} data-testid="download-zip">
              <Icon name="download" size={16} /> تحميل <span className="mono ltr">{name}</span>
            </a>
          ) : (
            <button type="button" className="btn btn-primary" disabled title={MSG.downloadNotReady}>
              <Icon name="download" size={16} /> تحميل <span className="mono ltr">{name}</span>
            </button>
          )}
          <a className="btn" href={projectHref(id, 'preview')}>
            <Icon name="eye" size={16} /> فتح المعاينة
          </a>
        </div>
        {!zip && <p className="muted small">يتوفر ملف ZIP عند ربط الخادم.</p>}
      </div>

      <section className="section">
        <h2 className="section-title">محتوى الملف</h2>
        <dl className="kv" style={{ margin: 0 }}>
          {FILES.map(([f, what]) => (
            <div key={f} style={{ display: 'contents' }}>
              <dt className="mono ltr" style={{ color: 'var(--bn-text)', textAlign: 'right' }}>{f}</dt>
              <dd className="muted">{what}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="section">
        <h2 className="section-title">الملخص</h2>
        <dl className="kv" style={{ margin: 0 }}>
          <dt>الاختبار</dt>
          <dd>
            {m ? `${m.checks_passed} من ${m.checks_total} ناجحة` : '—'} · <a href={projectHref(id, 'tests')}>التقرير</a>
          </dd>
          <dt>المتطلبات</dt>
          <dd>
            {entity ? `${entity.label}، ${entity.fields.length} حقول` : '—'} · <a href={projectHref(id, 'requirements')}>عرض</a>
          </dd>
          <dt>الهيكل</dt>
          <dd><a href={projectHref(id, 'structure')}>وثيقة الهيكل</a></dd>
          <dt>الخطة</dt>
          <dd><a href={projectHref(id, 'plan')}>الخطة والمخاطر</a></dd>
        </dl>
      </section>

      <section className="section">
        <h2 className="section-title">تشغيله على جهازك</h2>
        <ol className="list small">
          <li>حمّل الملف وفك الضغط في أي مجلد.</li>
          <li>افتح <span className="mono ltr">index.html</span> في المتصفح. لا يحتاج تثبيت أو إنترنت.</li>
          <li>البيانات تبقى في نفس المتصفح، وتُمسح إذا مسحت بيانات التصفح.</li>
        </ol>
      </section>
    </div>
  );
}
