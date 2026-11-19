import { downloadUrl } from '../api/client.js';
import Icon from '../components/icons.jsx';
import { Notice } from '../components/ui.jsx';
import { hasArtifact } from '../constants/stages.js';
import { projectHref } from '../hooks/useHashRoute.js';
import { projectSlug } from '../lib/labels.js';
import { MSG } from '../lib/messages.js';
import { qaSummary } from '../lib/qa.js';

const FILES = [
  ['index.html', 'الصفحة والنموذج'],
  ['style.css', 'التنسيق واتجاه الصفحة'],
  ['app.js', 'الإضافة والتعديل والحذف والحفظ'],
];

/** Preview and ZIP buttons; shared by the delivery screen and a failed run that still produced the app. */
export function AppActions({ project }) {
  const id = project.project_id;
  const zip = downloadUrl(id);
  const name = `${projectSlug(project)}.zip`;
  return (
    <>
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
        <a className="btn" href={projectHref(id, 'preview')} data-testid="open-preview">
          <Icon name="eye" size={16} /> فتح المعاينة
        </a>
      </div>
      {!zip && <p className="muted small">يتوفر ملف ZIP عند ربط الخادم.</p>}
    </>
  );
}

/** "تطبيقك جاهز!": shown when the run has completed. The headline follows project.qa.status. */
export default function DeliveryView({ project }) {
  const req = project.requirements;
  const id = project.project_id;
  const entity = req?.entities?.[0];
  const qa = qaSummary(project);
  const hasReport = hasArtifact(project, 'test_report.json');
  const hasPlan = hasArtifact(project, 'project_plan.md');

  return (
    <div className="page page-narrow" data-testid="delivery">
      <nav className="crumbs" aria-label="المسار">
        <a href="#/projects">المشاريع</a> / <span>{req?.app?.name}</span>
      </nav>

      <div style={{ display: 'grid', gap: 'var(--bn-s3)', justifyItems: 'start' }}>
        <span className={`result-mark${qa.ok ? '' : ' warn'}`}>
          <Icon name={qa.ok ? 'check' : 'alert'} size={20} />
        </span>
        <h1 className="title" data-testid="delivery-title">{qa.ok ? 'تطبيقك جاهز!' : 'تطبيقك جاهز مع ملاحظات'}</h1>
        <p className="lead">
          {req?.app?.name}: {req?.app?.description}
        </p>
        {qa.note && (
          <Notice tone={qa.status === 'not_run' ? undefined : 'error'} testId="qa-note">
            {qa.note}
            {qa.failedChecks.length > 0 && <span className="mono ltr"> ({qa.failedChecks.join(', ')})</span>}
          </Notice>
        )}
        <AppActions project={project} />
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
          <dd data-testid="qa-summary" data-qa={qa.status}>
            {qa.text}
            {hasReport && <> · <a href={projectHref(id, 'tests')}>التقرير</a></>}
          </dd>
          <dt>المتطلبات</dt>
          <dd>
            {entity ? `${entity.label}، ${entity.fields.length} حقول` : '—'} · <a href={projectHref(id, 'requirements')}>عرض</a>
          </dd>
          <dt>الهيكل</dt>
          <dd><a href={projectHref(id, 'structure')}>وثيقة الهيكل</a></dd>
          <dt>الخطة</dt>
          <dd>{hasPlan ? <a href={projectHref(id, 'plan')}>الخطة والمخاطر</a> : 'لم تُكتب'}</dd>
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
