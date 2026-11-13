// Icon set: 20px grid, 1.5px stroke, round joins, square-ish corners (2px radius)
// to echo the logo blocks. Icons inherit currentColor and never carry meaning alone.

const P = {
  plus: 'M10 4.5v11M4.5 10h11',
  check: 'M4.5 10.5l3.5 3.5 7.5-8',
  close: 'M5.5 5.5l9 9M14.5 5.5l-9 9',
  alert: 'M10 6v5M10 13.75v.5',
  download: 'M10 3.5v9M6.5 9l3.5 3.5L13.5 9M4 16h12',
  eye: 'M2.5 10s2.75-5 7.5-5 7.5 5 7.5 5-2.75 5-7.5 5-7.5-5-7.5-5z M10 12.25a2.25 2.25 0 1 0 0-4.5 2.25 2.25 0 0 0 0 4.5z',
  copy: 'M7 7h8.5a.5.5 0 0 1 .5.5V16a.5.5 0 0 1-.5.5H7a.5.5 0 0 1-.5-.5V7.5A.5.5 0 0 1 7 7z M4 13V4.5a.5.5 0 0 1 .5-.5H13',
  refresh: 'M15.5 8.5A5.75 5.75 0 1 0 15 13 M15.5 4v4.5H11',
  expand: 'M12 4h4v4M8 16H4v-4M16 4l-5 5M4 16l5-5',
  desktop: 'M3.5 4.5h13a.5.5 0 0 1 .5.5v8a.5.5 0 0 1-.5.5h-13A.5.5 0 0 1 3 13V5a.5.5 0 0 1 .5-.5z M7.5 16.5h5M10 13.5v3',
  phone: 'M6.5 3h7a.5.5 0 0 1 .5.5v13a.5.5 0 0 1-.5.5h-7a.5.5 0 0 1-.5-.5v-13a.5.5 0 0 1 .5-.5z M9.25 14.75h1.5',
  folder: 'M3 6V5a1 1 0 0 1 1-1h3.5l1.5 1.75H16a1 1 0 0 1 1 1V15a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6z',
  settings: 'M10 12.25a2.25 2.25 0 1 0 0-4.5 2.25 2.25 0 0 0 0 4.5z M10 2.75v2M10 15.25v2M2.75 10h2M15.25 10h2M4.9 4.9l1.4 1.4M13.7 13.7l1.4 1.4M4.9 15.1l1.4-1.4M13.7 6.3l1.4-1.4',
  help: 'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M8 8a2 2 0 1 1 2.75 1.85c-.45.2-.75.62-.75 1.1v.55M10 13.75v.25',
  menu: 'M3.5 6h13M3.5 10h13M3.5 14h13',
  file: 'M5.5 3h6l3.5 3.5V16.5a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5v-13a.5.5 0 0 1 .5-.5z M11.5 3v3.5H15',
  arrow: 'M15.5 10h-11M8.5 6l-4 4 4 4',
  search: 'M9 14.5a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11z M13 13l3.5 3.5',
};

export default function Icon({ name, size = 16, className, title }) {
  if (name === 'spinner') {
    return (
      <svg width={size} height={size} viewBox="0 0 20 20" className={`spin ${className ?? ''}`} aria-hidden="true">
        <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="1.75" />
        <path d="M10 3a7 7 0 0 1 7 7" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      </svg>
    );
  }
  if (name === 'circle') {
    return (
      <svg width={size} height={size} viewBox="0 0 20 20" className={className} aria-hidden="true">
        <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    );
  }
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      className={className}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : 'true'}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={P[name]} />
    </svg>
  );
}
