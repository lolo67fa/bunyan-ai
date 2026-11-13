import { useEffect, useRef, useState } from 'react';
import { getPreviewHtml, previewUrl } from '../api/client.js';
import Icon from '../components/icons.jsx';
import { projectSlug } from '../lib/labels.js';
import { MSG } from '../lib/messages.js';

/** "المعاينة": the generated app in a sandboxed frame, desktop or phone width. */
export default function PreviewView({ project }) {
  const [device, setDevice] = useState('desktop');
  const [html, setHtml] = useState(null);
  const [nonce, setNonce] = useState(0);
  const frame = useRef(null);
  const src = previewUrl(project.project_id);
  const ready = project.artifacts?.some((a) => a.name === 'index.html' && a.available);

  useEffect(() => {
    if (!ready || src) return undefined;
    let alive = true;
    getPreviewHtml(project.project_id).then((h) => alive && setHtml(h)).catch(() => alive && setHtml(null));
    return () => { alive = false; };
  }, [project.project_id, ready, src, nonce]);

  if (!ready) return <p className="muted" style={{ paddingTop: 'var(--bn-s5)' }}>{MSG.previewUnavailable}</p>;

  const m = project.metrics;
  return (
    <div style={{ display: 'grid', gap: 'var(--bn-s3)', paddingTop: 'var(--bn-s5)' }} data-testid="preview-view">
      <div className="preview-bar">
        {m ? (
          <span className="small" style={{ color: m.checks_passed === m.checks_total ? 'var(--bn-success)' : 'var(--bn-warning)' }}>
            اجتاز {m.checks_passed} من {m.checks_total} فحوصات
          </span>
        ) : <span />}
        <div className="actions">
          <div className="segmented" role="group" aria-label="حجم المعاينة">
            <button type="button" aria-pressed={device === 'desktop'} onClick={() => setDevice('desktop')}>
              سطح المكتب
            </button>
            <button type="button" aria-pressed={device === 'phone'} onClick={() => setDevice('phone')} data-testid="device-phone">
              جوال
            </button>
          </div>
          <button type="button" className="btn icon-btn" aria-label="إعادة التحميل" onClick={() => setNonce(nonce + 1)}>
            <Icon name="refresh" size={16} />
          </button>
          <button
            type="button"
            className="btn icon-btn"
            aria-label="ملء الشاشة"
            onClick={() => frame.current?.requestFullscreen?.().catch(() => {})}
          >
            <Icon name="expand" size={16} />
          </button>
        </div>
      </div>
      <div className="preview-stage">
        <div className="preview-frame" style={{ width: device === 'phone' ? 390 : '100%' }}>
          <div className="preview-path">preview / {projectSlug(project)} / index.html</div>
          {src ? (
            // Served by the backend from its own origin, so the generated app may use localStorage safely.
            <iframe key={nonce} ref={frame} title="معاينة التطبيق" src={src} sandbox="allow-scripts allow-forms allow-same-origin" />
          ) : html ? (
            <iframe key={nonce} ref={frame} title="معاينة التطبيق" srcDoc={html} sandbox="" data-testid="preview-frame" />
          ) : (
            <p className="muted" style={{ padding: 16 }}>جاري التحميل…</p>
          )}
        </div>
      </div>
      <p className="muted small">البيانات التي تضيفها في المعاينة تبقى في هذا المتصفح فقط.</p>
    </div>
  );
}
