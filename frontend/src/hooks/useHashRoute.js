import { useEffect, useState } from 'react';

// Hash routes (no server config needed on a static host):
//   #/                      landing page
//   #/new                   new project
//   #/projects              all projects
//   #/projects/<id>[/<tab>] one project, optional tab
//   #/settings  #/help      settings and help
function parse() {
  const h = window.location.hash.replace(/^#/, '') || '/';
  const m = h.match(/^\/projects\/([^/?#]+)(?:\/([a-z]+))?/);
  if (m) return { page: 'project', id: decodeURIComponent(m[1]), tab: m[2] ?? null };
  if (h.startsWith('/new')) return { page: 'new' };
  if (h.startsWith('/projects')) return { page: 'projects' };
  if (h.startsWith('/settings')) return { page: 'settings' };
  if (h.startsWith('/help')) return { page: 'help' };
  return { page: 'home' };
}

export function useHashRoute() {
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    const onChange = () => {
      setRoute(parse());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

export const go = (path) => {
  window.location.hash = `#${path}`;
};
export const goHome = () => go('/');
export const goToProject = (id, tab) => go(`/projects/${encodeURIComponent(id)}${tab ? `/${tab}` : ''}`);
export const projectHref = (id, tab) => `#/projects/${encodeURIComponent(id)}${tab ? `/${tab}` : ''}`;
