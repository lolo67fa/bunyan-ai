import { useArtifact } from './useArtifact.js';
import { BEHAVIORS, FIELD_TYPES, SCREEN_TYPES, fieldRules } from '../lib/labels.js';

const MESSAGE_LABELS = {
  empty: 'لا توجد سجلات',
  no_results: 'لا نتائج للبحث',
  created: 'بعد الإضافة',
  updated: 'بعد التعديل',
  deleted: 'بعد الحذف',
  confirm_delete: 'تأكيد الحذف',
  invalid: 'قيمة غير صحيحة',
};

/** "الهيكل": architecture.json from the Architect agent (Naifah's contract 0.3.0-proposal). */
export default function StructureView({ project }) {
  const { json: arch, error, loading } = useArtifact(project, 'architecture.json');
  if (error) return <p className="field-error">{error.message}</p>;
  if (loading || !arch) return <p className="muted">جاري التحميل…</p>;

  const entity = arch.entity;
  if (!entity?.fields) {
    return (
      <pre className="code" style={{ padding: 'var(--bn-s4)', direction: 'ltr', textAlign: 'left', overflow: 'auto' }}>
        {JSON.stringify(arch, null, 2)}
      </pre>
    );
  }
  const dir = arch.app?.direction ?? 'rtl';
  const behaviors = Object.entries(arch.behaviors ?? {}).filter(([k, v]) => v === true && BEHAVIORS[k]);
  const messages = Object.entries(arch.messages ?? {}).filter(([k]) => MESSAGE_LABELS[k]);

  return (
    <div data-testid="structure-view">
      <section className="section">
        <p className="lead">
          تطبيق من صفحة واحدة لإدارة كيان واحد هو <strong>{entity.plural_label ?? entity.label}</strong>. يحفظ البيانات في المتصفح،
          ويدعم البحث والترتيب{dir === 'rtl' ? '، والواجهة بالعربية' : '، والواجهة بالإنجليزية'}.
        </p>
      </section>

      <section className="section">
        <h2 className="section-title">الحقول</h2>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>الحقل</th><th>المعرّف</th><th>النوع</th><th>مطلوب</th><th>التحقق</th></tr>
            </thead>
            <tbody>
              {entity.fields.map((f) => (
                <tr key={f.name}>
                  <td className="strong" dir={dir}>{f.label}</td>
                  <td className="mono ltr">{f.name}</td>
                  <td className="mono ltr" title={FIELD_TYPES[f.type]}>{f.type}</td>
                  <td>{f.required ? 'نعم' : 'لا'}</td>
                  <td dir={dir}>{fieldRules(f) || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {entity.storage?.system_fields && (
          <p className="muted small">
            يُضاف تلقائياً: <span className="mono ltr">{entity.storage.system_fields.join(', ')}</span>
          </p>
        )}
      </section>

      <section className="section two-col">
        <div style={{ display: 'grid', gap: 'var(--bn-s2)', alignContent: 'start' }}>
          <h2 className="section-title">الشاشات</h2>
          <ol className="list small">
            {(arch.screens ?? []).map((s) => (
              <li key={s.id}>
                {SCREEN_TYPES[s.type] ?? s.type}: <span dir={dir}>{s.title}</span>
              </li>
            ))}
          </ol>
        </div>
        <div style={{ display: 'grid', gap: 'var(--bn-s2)', alignContent: 'start' }}>
          <h2 className="section-title">التخزين</h2>
          <p className="small lead">
            في <span className="mono ltr">{entity.storage?.engine ?? 'localStorage'}</span> تحت المفتاح{' '}
            <span className="mono ltr">{entity.storage?.key}</span>، ويُقرأ عند فتح الصفحة ويُكتب بعد كل عملية.
          </p>
          {behaviors.length > 0 && (
            <>
              <h2 className="section-title">قواعد السلوك</h2>
              <ul className="list small">{behaviors.map(([k]) => <li key={k}>{BEHAVIORS[k]}</li>)}</ul>
            </>
          )}
        </div>
      </section>

      {messages.length > 0 && (
        <section className="section">
          <h2 className="section-title">رسائل الواجهة</h2>
          <dl className="kv" style={{ margin: 0 }}>
            {messages.map(([k, v]) => (
              <div key={k} style={{ display: 'contents' }}>
                <dt>{MESSAGE_LABELS[k]}</dt>
                <dd dir={dir}>{v}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section className="section">
        <p className="muted small">
          وثيقة الهيكل:{' '}
          <span className="mono ltr">
            architecture.json{arch.schema_version ? ` · ${arch.schema_version}` : ''}
          </span>
        </p>
      </section>
    </div>
  );
}
