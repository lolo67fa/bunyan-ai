import { useState } from 'react';
import { CopyButton } from '../components/ui.jsx';
import { projectSlug } from '../lib/labels.js';
import { useArtifact } from './useArtifact.js';

const FILES = ['index.html', 'style.css', 'app.js'];

function size(text) {
  if (text == null) return '';
  const kb = new Blob([text]).size / 1024;
  return `${kb.toFixed(1)} KB`;
}

function FileRow({ project, name, current, onSelect }) {
  const { text } = useArtifact(project, name);
  return (
    <li>
      <button type="button" className="file-btn" aria-current={current} onClick={() => onSelect(name)}>
        <span>{name}</span>
        <span className="muted">{size(text)}</span>
      </button>
    </li>
  );
}

/** "الملفات": the generated code with line numbers and copy. */
export default function FilesView({ project }) {
  const [file, setFile] = useState(FILES[0]);
  const { text, loading, error } = useArtifact(project, file);
  const folder = `${projectSlug(project)}/`;
  const lines = (text ?? '').split('\n');
  return (
    <div className="files-grid" style={{ paddingTop: 'var(--bn-s5)' }} data-testid="files-view">
      <div style={{ display: 'grid', gap: 'var(--bn-s2)' }}>
        <span className="mono muted small ltr" style={{ textAlign: 'left' }}>{folder}</span>
        <ul className="file-list">
          {FILES.map((f) => (
            <FileRow key={f} project={project} name={f} current={f === file} onSelect={setFile} />
          ))}
        </ul>
      </div>
      <div className="code">
        <div className="code-head">
          <span className="mono ltr">{file}</span>
          {text && <CopyButton text={text} />}
        </div>
        <div className="code-body">
          {error && <p className="field-error" style={{ padding: 12 }}>{error.message}</p>}
          {loading && <p className="muted" style={{ padding: 12 }}>جاري التحميل…</p>}
          {text != null && (
            <table>
              <tbody>
                {lines.map((l, i) => (
                  <tr key={i}>
                    <td className="ln">{i + 1}</td>
                    <td className="src">{l}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
