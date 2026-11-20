import { useEffect, useState } from 'react';
import { getArtifactText } from '../api/client.js';

const cache = new Map();

/** Loads one artifact's text once it is available. Returns { text, json, error, loading }. */
export function useArtifact(project, name) {
  const available = project.artifacts?.some((a) => a.name === name && a.available);
  const key = `${project.project_id}/${name}/${project.repair_attempt ?? 0}/${project.status === 'completed'}`;
  const [state, setState] = useState(() => (cache.has(key) ? { text: cache.get(key) } : {}));

  useEffect(() => {
    if (!available) return undefined;
    if (cache.has(key)) {
      setState({ text: cache.get(key) });
      return undefined;
    }
    let alive = true;
    setState({ loading: true });
    getArtifactText(project.project_id, name)
      .then((text) => {
        cache.set(key, text);
        if (alive) setState({ text });
      })
      .catch((error) => alive && setState({ error }));
    return () => {
      alive = false;
    };
  }, [available, key, name, project.project_id]);

  let json = null;
  if (state.text && name.endsWith('.json')) {
    try {
      json = JSON.parse(state.text);
    } catch {
      json = null;
    }
  }
  return { ...state, json, available };
}

export function saveFile(name, text) {
  const types = { json: 'application/json', md: 'text/markdown', html: 'text/html', css: 'text/css', js: 'text/javascript' };
  const ext = name.split('.').pop();
  const url = URL.createObjectURL(new Blob([text], { type: `${types[ext] ?? 'text/plain'};charset=utf-8` }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
