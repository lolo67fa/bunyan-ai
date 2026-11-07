import { useState } from 'react';
import { getArtifactText } from '../api/client.js';

const MIME = {
  json: 'application/json',
  md: 'text/markdown',
  html: 'text/html',
  css: 'text/css',
  js: 'text/javascript',
};

function saveFile(name, text) {
  const ext = name.split('.').pop();
  const url = URL.createObjectURL(new Blob([text], { type: `${MIME[ext] ?? 'text/plain'};charset=utf-8` }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Lists project.artifacts; each available file can be viewed or downloaded. */
export default function ArtifactList({ project }) {
  const [open, setOpen] = useState(null); // { name, text }
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  async function load(name, action) {
    setBusy(name);
    setError('');
    try {
      const text = await getArtifactText(project.id, name);
      if (action === 'view') setOpen({ name, text });
      else saveFile(name, text);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }

  return (
    <section className="card" data-testid="artifact-list">
      <h2>الملفات الناتجة</h2>
      <ul className="artifacts">
        {project.artifacts.map((a) => (
          <li key={a.name} className={a.available ? '' : 'is-pending'} data-testid={`artifact-${a.name}`}>
            <code className="ltr">{a.name}</code>
            {a.available ? (
              <span className="row-actions">
                <button className="btn btn-small" disabled={busy === a.name} onClick={() => load(a.name, 'view')}>
                  عرض
                </button>
                <button className="btn btn-small" disabled={busy === a.name} onClick={() => load(a.name, 'save')}>
                  تحميل
                </button>
              </span>
            ) : (
              <span className="muted small">لم يجهز بعد</span>
            )}
          </li>
        ))}
      </ul>
      {error && <p className="alert alert-error">{error}</p>}

      {open && (
        <div className="viewer" data-testid="artifact-viewer">
          <div className="card-head">
            <code className="ltr">{open.name}</code>
            <button className="btn btn-small" onClick={() => setOpen(null)}>
              إغلاق
            </button>
          </div>
          <pre className="ltr">{open.text}</pre>
        </div>
      )}
    </section>
  );
}
