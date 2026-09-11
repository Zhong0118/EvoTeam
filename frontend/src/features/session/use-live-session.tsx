/* Live session replay — fixture-driven event stream behind one context, so
   Chat and the Execution Graph consume the same AgentEvent list (V3 §22/§23:
   one incoming event updates every projection; no per-view polling). The
   step timing is UI simulation only; the real stream arrives with
   POST /v1/executions (F1) and SSE later. */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { AgentEvent } from "../runtime/types";
import { sessionEventStream } from "../../fixtures/session-events";

const REPLAY_INTERVAL_MS = 850;

export type LiveMode = "idle" | "replay" | "completed";

export interface LiveSession {
  events: AgentEvent[];
  running: boolean;
  start: () => void;
  restart: () => void;
  stop: () => void;
}

const LiveSessionContext = createContext<LiveSession | null>(null);

export function LiveSessionProvider({
  mode = "idle",
  children,
}: {
  mode?: LiveMode;
  children: ReactNode;
}) {
  const [events, setEvents] = useState<AgentEvent[]>(
    mode === "completed" ? sessionEventStream : [],
  );
  const [running, setRunning] = useState(false);
  const cursor = useRef(mode === "completed" ? sessionEventStream.length : 0);
  const timer = useRef<number | undefined>(undefined);

  const step = useCallback(() => {
    const next = sessionEventStream[cursor.current++];
    if (!next) {
      setRunning(false);
      return;
    }
    setEvents((prev) => [...prev, next]);
    timer.current = window.setTimeout(step, REPLAY_INTERVAL_MS);
  }, []);

  const start = useCallback(() => {
    if (running) return;
    setRunning(true);
    timer.current = window.setTimeout(step, 400);
  }, [running, step]);

  const restart = useCallback(() => {
    if (timer.current) window.clearTimeout(timer.current);
    cursor.current = 0;
    setEvents([]);
    setRunning(true);
    timer.current = window.setTimeout(step, 400);
  }, [step]);

  const stop = useCallback(() => {
    if (timer.current) window.clearTimeout(timer.current);
    setRunning(false);
  }, []);

  useEffect(() => () => stop(), [stop]);
  // Completed fixtures arrive with the whole transcript; never auto-replay
  // a session that already ended, and never touch the idle empty state.
  useEffect(() => {
    if (mode === "replay" && cursor.current === 0) start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  const value = useMemo(
    // `running` is owned by the replay state machine: start() sets it,
    // exhaustion and stop() clear it. Forcing it by mode would leave the
    // Composer stuck on "Stop" after a finished replay.
    () => ({ events, running, start, restart, stop }),
    [events, running, start, restart, stop],
  );
  return (
    <LiveSessionContext.Provider value={value}>
      {children}
    </LiveSessionContext.Provider>
  );
}

export function useLiveSession(): LiveSession {
  const ctx = useContext(LiveSessionContext);
  if (!ctx) throw new Error("useLiveSession 必须在 LiveSessionProvider 内使用");
  return ctx;
}
