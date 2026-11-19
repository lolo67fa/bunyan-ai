import Icon from '../components/icons.jsx';
import { Notice } from '../components/ui.jsx';
import { hasGeneratedApp } from '../constants/stages.js';
import { go } from '../hooks/useHashRoute.js';
import { MSG } from '../lib/messages.js';
import { QA_NOTES } from '../lib/qa.js';
import { AppActions } from './DeliveryView.jsx';
import { saveDraft } from './draft.js';

/** Out of scope (rejected) or failed run. Says what happened and what to do next. */
export default function StoppedView({ project }) {
  const req = project.requirements;
  const outOfScope = project.status === 'rejected' || req?.status === 'rejected_out_of_scope';
  const dir = req?.language === 'en' ? 'ltr' : 'rtl';
  // The run stopped after the Developer (QA blocked, or the plan failed): the app itself is usable.
  const app = !outOfScope && hasGeneratedApp(project);
  const appName = req?.status === 'ready_for_review' ? req.app?.name : null;
  return (
    <div className="page page-narrow" data-testid="failed">
      <nav className="crumbs" aria-label="المسار">
        <a href="#/projects">المشاريع</a> / <span>{appName ?? 'فكرة جديدة'}</span>
      </nav>
      <div style={{ display: 'grid', gap: 'var(--bn-s3)', justifyItems: 'start' }}>
        <span className="result-mark fail"><Icon name="alert" size={20} /></span>
        <h1 className="title">
          {outOfScope ? 'الفكرة خارج نطاق النسخة الأولى' : app ? 'تطبيقك جاهز، لكن البناء لم يكتمل' : 'توقف البناء'}
        </h1>
        <p className="lead">{outOfScope ? MSG.outOfScope : project.error?.message ?? MSG.agentFailed}</p>
      </div>

      {app && (
        <section className="section" data-testid="app-available" style={{ display: 'grid', gap: 'var(--bn-s3)', justifyItems: 'start' }}>
          {project.qa?.status === 'blocked' && <Notice tone="waiting" testId="qa-note">{QA_NOTES.blocked}</Notice>}
          {project.qa?.status !== 'blocked' && (
            <Notice tone="waiting">ولّد المطوّر ملفات التطبيق، وهي متاحة للمعاينة والتحميل.</Notice>
          )}
          <AppActions project={project} />
        </section>
      )}

      <div className="quote"><span dir="auto">«{project.idea}»</span></div>

      {outOfScope && req?.out_of_scope?.length > 0 && (
        <section className="section" dir={dir}>
          <h2 className="section-title">ما لا يستطيع بُنيان بناءه الآن</h2>
          <div className="table-wrap">
            <table className="table" data-testid="out-of-scope">
              <thead>
                <tr><th>الميزة</th><th>السبب</th><th>البديل</th></tr>
              </thead>
              <tbody>
                {req.out_of_scope.map((o, i) => (
                  <tr key={i}>
                    <td className="strong">{o.feature}</td>
                    <td>{o.reason}</td>
                    <td>{o.alternative ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <div className="actions">
        <button type="button" className={`btn${app ? '' : ' btn-primary'}`} onClick={() => { saveDraft(project.idea); go('/new'); }}>
          تعديل الفكرة
        </button>
        <a className="btn" href="#/help">ما الذي يمكن بناؤه؟</a>
      </div>
    </div>
  );
}
