import { useCallback, useEffect, useRef, useState } from 'react';
import { getProject } from '../api/client.js';
import { shouldStopPolling } from '../constants/stages.js';

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
      return { project: p, error: null };
    } catch (e) {
      setError(e);
      return { project: null, error: e };
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    setProject(null);
    setError(null);

    const tick = async () => {
      const result = await fetchOnce();
      if (cancelled) return;
      if (!shouldStopPolling(result.project, result.error)) timer.current = setTimeout(tick, POLL_MS);
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
        const result = await fetchOnce();
        if (!shouldStopPolling(result.project, result.error)) timer.current = setTimeout(tick, POLL_MS);
      };
      timer.current = setTimeout(tick, POLL_MS);
    },
    [fetchOnce],
  );

  const refresh = useCallback(async () => (await fetchOnce()).project, [fetchOnce]);

  return { project, error, refresh, resume };
}
