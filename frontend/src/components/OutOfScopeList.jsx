// Renders requirements.out_of_scope[] (feature, reason, action, alternative).
export default function OutOfScopeList({ items, dir }) {
  if (!items?.length) return null;
  return (
    <ul className="oos" dir={dir} data-testid="out-of-scope">
      {items.map((o, i) => (
        <li key={i}>
          <div>
            <strong>{o.feature}</strong>
            <span className={`tag ${o.action === 'excluded' ? 'tag-red' : 'tag-amber'}`}>
              {o.action === 'excluded' ? 'مستبعدة' : 'استُبدلت ببديل'}
            </span>
          </div>
          <p className="muted">{o.reason}</p>
          {o.alternative && <p>البديل: {o.alternative}</p>}
        </li>
      ))}
    </ul>
  );
}
