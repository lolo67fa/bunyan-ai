import { useEffect, useState } from 'react';
import { MODE, downloadUrl, getPreviewHtml, previewUrl } from '../api/client.js';

/** Shown when status is completed: QA numbers, live preview, ZIP download. */
export default function ResultsPanel({ project }) {
  const m = project.metrics;
  const [html, setHtml] = useState(null);

  useEffect(() => {
    let alive = true;
    getPreviewHtml(project.id)
      .then((h) => alive && setHtml(h))
      .catch(() => alive && setHtml(null));
    return () => {
      alive = false;
    };
  }, [project.id]);

  const src = previewUrl(project.id);
  const zip = downloadUrl(project.id);
  const passed = m && m.checks_passed === m.checks_total;

  return (
    <section className="card" data-testid="results">
      <h2>النتيجة</h2>

      {m && (
        <div className="tiles">
          <div className={`tile ${passed ? 'tile-ok' : 'tile-warn'}`} data-testid="metric-checks">
            <span className="tile-num ltr">
              {m.checks_passed}/{m.checks_total}
            </span>
            <span>اختبارات ناجحة</span>
          </div>
          <div className="tile" data-testid="metric-time">
            <span className="tile-num ltr">{m.run_time_seconds}s</span>
            <span>مدة التشغيل {m.run_time_seconds > 90 ? '(فوق الهدف)' : ''}</span>
          </div>
          <div className="tile">
            <span className="tile-num ltr">{project.repair_attempt}/2</span>
            <span>محاولات إصلاح</span>
          </div>
        </div>
      )}

      <h3>معاينة التطبيق</h3>
      <div className="preview">
        {src ? (
          // Generated apps use localStorage, so the preview must be served from the backend's
          // own origin (not this frontend's) for allow-same-origin to be safe. Confirm with Alanoud.
          <iframe title="معاينة التطبيق" src={src} sandbox="allow-scripts allow-forms allow-same-origin" />
        ) : html ? (
          <iframe title="معاينة التطبيق" srcDoc={html} sandbox="" data-testid="preview-frame" />
        ) : (
          <p className="muted">المعاينة غير متوفرة.</p>
        )}
      </div>

      <div className="actions">
        {zip ? (
          <a className="btn btn-primary" href={zip} download="bunyan-output.zip">
            تحميل كل الملفات (ZIP)
          </a>
        ) : (
          <button className="btn btn-primary" disabled title="يتوفر مع الباك إند">
            تحميل ZIP {MODE === 'mock' ? '(يتوفر مع الباك إند)' : ''}
          </button>
        )}
      </div>
    </section>
  );
}
