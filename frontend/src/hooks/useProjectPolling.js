import { useCallback, useEffect, useRef, useState } from 'react';
import { getProject } from '../api/client.js';
import { TERMINAL_STATES, WAITING_STATES } from '../constants/stages.js';
import { MAX_POLL_ERRORS, POLL_MS } from '../lib/messages.js';
import { rememberProject } from '../lib/prefs.js';

const ENV_POLL = Number(import.meta.env.VITE_POLL_MS);
const INTERVAL = Number.isFinite(ENV_POLL) && ENV_POLL > 0 ? ENV_POLL : POLL_MS;

const shouldStop = (p) => p && (TERMINAL_STATES.includes(p.status) || WAITING_STATES.includes(p.status));

/**
 * Polls GET /projects/{id} every 3 s while the run is working.
 * Stops while the run waits for the user, once it has finished, or after
 * 3 failed requests in a row (`stalled`); `retry()` starts it again.
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
      if (!alive.current) return;
      errors.current = 0;
      setProject(p);
      setError(null);
      setStalled(false);
      rememberProject(p);
      if (!shouldStop(p)) timer.current = setTimeout(tick, INTERVAL);
    } catch (e) {
      if (!alive.current) return;
      setError(e);
      errors.current += 1;
      if (e.status === 404) return; // unknown project: nothing to poll
      if (errors.current >= MAX_POLL_ERRORS) setStalled(true);
      else timer.current = setTimeout(tick, INTERVAL);
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
