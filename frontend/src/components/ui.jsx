import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import Icon from './icons.jsx';

/** Status as coloured text with a small dot (no pills). tone: neutral|working|waiting|done|failed */
export function StatusText({ tone = 'neutral', children }) {
  return <span className={`status status-${tone}`}>{children}</span>;
}

/** Underlined tabs. items: [{ key, label, disabled }] */
export function Tabs({ items, active, onSelect, label = 'أقسام المشروع' }) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {items.map((t) => (
        <button
          key={t.key}
          type="button"
          role="tab"
          className="tab"
          aria-selected={active === t.key}
          disabled={t.disabled}
          title={t.disabled ? t.hint : undefined}
          onClick={() => onSelect(t.key)}
          data-testid={`tab-${t.key}`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

/** Inline notice. tone: neutral|waiting|error. action: { label, onClick } */
export function Notice({ tone = 'neutral', children, action, testId }) {
  return (
    <div className={`notice notice-${tone}`} role={tone === 'error' ? 'alert' : 'status'} data-testid={testId}>
      <span>{children}</span>
      {action && (
        <button type="button" className="notice-action" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="empty" data-testid="empty-state">
      <strong>{title}</strong>
      {children && <p className="muted small">{children}</p>}
      {action}
    </div>
  );
}

// ---------- toast ----------
const ToastCtx = createContext(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const timer = useRef(null);
  const show = useCallback((text, action) => {
    clearTimeout(timer.current);
    setToast({ text, action });
    timer.current = setTimeout(() => setToast(null), 4000);
  }, []);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {toast && (
        <div className="toast" role="status" data-testid="toast">
          <span>{toast.text}</span>
          {toast.action && (
            <button type="button" onClick={() => { toast.action.onClick(); setToast(null); }}>
              {toast.action.label}
            </button>
          )}
        </div>
      )}
    </ToastCtx.Provider>
  );
}

// ---------- dialog ----------
export function Dialog({ title, description, onClose, children, footer, testId }) {
  const ref = useRef(null);
  useEffect(() => {
    const prev = document.activeElement;
    ref.current?.querySelector('textarea, input, button')?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab' && ref.current) {
        const f = [...ref.current.querySelectorAll('button, textarea, input, select, a[href]')].filter((el) => !el.disabled);
        if (!f.length) return;
        if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
        else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      prev?.focus?.();
    };
  }, [onClose]);
  return (
    <div className="dialog-scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title" ref={ref} data-testid={testId}>
        <h2 id="dialog-title">{title}</h2>
        {description && <p className="muted small">{description}</p>}
        {children}
        {footer && <div className="actions">{footer}</div>}
      </div>
    </div>
  );
}

export function CopyButton({ text, label = 'نسخ' }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="btn btn-sm"
      onClick={() => {
        navigator.clipboard?.writeText(text).then(
          () => { setDone(true); setTimeout(() => setDone(false), 1500); },
          () => {},
        );
      }}
    >
      <Icon name={done ? 'check' : 'copy'} size={14} />
      {done ? 'تم النسخ' : label}
    </button>
  );
}
