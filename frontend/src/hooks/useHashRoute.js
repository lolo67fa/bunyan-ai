import { useEffect, useState } from 'react';

// Minimal hash router: "#/" → idea page, "#/projects/<id>" → project page.
// Hash routing needs no server config, so the build works on any static host.
function parse() {
  const m = window.location.hash.match(/^#\/projects\/([^/?#]+)/);
  return m ? { page: 'project', id: decodeURIComponent(m[1]) } : { page: 'home' };
}

export function useHashRoute() {
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    const onChange = () => setRoute(parse());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

export const goHome = () => {
  window.location.hash = '#/';
};
export const goToProject = (id) => {
  window.location.hash = `#/projects/${encodeURIComponent(id)}`;
};
