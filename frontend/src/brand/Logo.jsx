// Bunyan mark: three blocks on a 10-unit module with a 2-unit joint (22 x 22 grid).
// The green block sits on the base, on the side facing the wordmark:
// left in the Arabic lockup, right in the English one. Colours come from tokens.

export function Mark({ size = 20, lang = 'ar', title }) {
  const greenLeft = lang === 'ar';
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 22 22"
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : 'true'}
    >
      <rect x="6" y="0" width="10" height="10" rx="1.6" fill="var(--bn-brand-ink)" />
      <rect x="0" y="12" width="10" height="10" rx="1.6" fill={greenLeft ? 'var(--bn-brand)' : 'var(--bn-brand-ink)'} />
      <rect x="12" y="12" width="10" height="10" rx="1.6" fill={greenLeft ? 'var(--bn-brand-ink)' : 'var(--bn-brand)'} />
    </svg>
  );
}

export default function Logo({ size = 18, large = false, href = '#/', label = 'بُنيان' }) {
  return (
    <a className={`logo${large ? ' logo-lg' : ''}`} href={href} aria-label={`${label} — الصفحة الرئيسية`}>
      <Mark size={size} />
      <span>{label}</span>
    </a>
  );
}
