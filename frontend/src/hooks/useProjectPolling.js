import { useCallback, useEffect, useRef, useState } from 'react';
import { getProject } from '../api/client.js';
import { shouldStopPolling } from '../constants/stages.js';
import { MAX_POLL_ERRORS, POLL_MS } from '../lib/messages.js';
import { rememberProject } from '../lib/prefs.js';

const ENV_POLL = Number(import.meta.env.VITE_POLL_MS);
const INTERVAL = Number.isFinite(ENV_POLL) && ENV_POLL > 0 ? ENV_POLL : POLL_MS;

/**
 * Polls GET /projects/{id} every 3 s while the run is working.
 * Stops while the run waits for the user, once it has finished, when the project
 * does not exist (404, or 422 for an id that is not a UUID), or after 3 failed
 * requests in a row (`stalled`); `retry()` starts it again.
 */
export function useProjectPolling(id) {
  const [project, setProject] = useState(null);
  const [error, setError] = useState(null);
  const [stalled, setStalled] = useState(false);
  const timer = useRef(null);
  const errors = useRef(0);
  const alive = useRef(true);

  const tick = useCallback(async () => {
    clearTimeout(timer.current);
    try {
      const p = await getProject(id);
      if (!alive.current) return p;
      errors.current = 0;
      setProject(p);
      setError(null);
      setStalled(false);
      rememberProject(p);
      if (!shouldStopPolling(p, null)) timer.current = setTimeout(tick, INTERVAL);
      return p;
    } catch (e) {
      if (!alive.current) return null;
      setError(e);
      errors.current += 1;
      if (shouldStopPolling(null, e)) return null; // the project does not exist: asking again cannot change that
      if (errors.current >= MAX_POLL_ERRORS) setStalled(true);
      else timer.current = setTimeout(tick, INTERVAL);
      return null;
    }
  }, [id]);

  useEffect(() => {
    alive.current = true;
    errors.current = 0;
    setProject(null);
    setError(null);
    setStalled(false);
    tick();
    return () => {
      alive.current = false;
      clearTimeout(timer.current);
    };
  }, [tick]);

  /** After an action (answers, approve) use the returned project and keep polling. */
  const resume = useCallback(
    (p) => {
      if (p) {
        setProject(p);
        rememberProject(p);
      }
      clearTimeout(timer.current);
      timer.current = setTimeout(tick, INTERVAL);
    },
    [tick],
  );

  const retry = useCallback(() => {
    errors.current = 0;
    setStalled(false);
    tick();
  }, [tick]);

  return { project, error, stalled, resume, retry, refresh: tick };
}
