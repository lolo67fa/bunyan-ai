import { useCallback, useEffect, useRef, useState } from 'react';
import { getProject } from '../api/client.js';
import { TERMINAL_STATES, WAITING_STATES } from '../constants/stages.js';

const POLL_MS = Number(import.meta.env.VITE_POLL_MS ?? 2000);

/**
 * Polls GET /projects/{id} while the run is working.
 * Stops while the run waits for the user, or once it is completed/failed.
 */
export function useProjectPolling(id) {
  const [project, setProject] = useState(null);
  const [error, setError] = useState(null);
  const timer = useRef(null);

  const fetchOnce = useCallback(async () => {
    try {
      const p = await getProject(id);
      setProject(p);
      setError(null);
      return p;
    } catch (e) {
      setError(e);
      return null;
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    setProject(null);
    setError(null);

    const tick = async () => {
      const p = await fetchOnce();
      if (cancelled) return;
      const stop = p && (TERMINAL_STATES.includes(p.status) || WAITING_STATES.includes(p.status));
      if (!stop) timer.current = setTimeout(tick, POLL_MS);
    };
    tick();

    return () => {
      cancelled = true;
      clearTimeout(timer.current);
    };
  }, [fetchOnce]);

  // After the user answers/approves, the screen sets the returned project and polling resumes.
  const resume = useCallback(
    (p) => {
      clearTimeout(timer.current);
      if (p) setProject(p);
      const tick = async () => {
        const next = await fetchOnce();
        const stop =
          next && (TERMINAL_STATES.includes(next.status) || WAITING_STATES.includes(next.status));
        if (!stop) timer.current = setTimeout(tick, POLL_MS);
      };
      timer.current = setTimeout(tick, POLL_MS);
    },
    [fetchOnce],
  );

  return { project, error, refresh: fetchOnce, resume };
}
