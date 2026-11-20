"use client";

import { useEffect, useReducer } from "react";

import { api } from "./api";
import { initialView, jobReducer, type JobView } from "./jobReducer";
import { ACTIVE_STATUSES } from "./types";

const EVENTS = [
  "snapshot",
  "status",
  "step",
  "certificate",
  "plan",
  "task",
  "diff",
  "log",
  "test",
  "result",
  "error",
] as const;

/** Load a job and follow its live event stream. Reconnects whenever the job becomes active. */
export function useJobStream(jobId: string, generation = 0): JobView & { reload: () => void } {
  const [view, dispatch] = useReducer(jobReducer, initialView);
  const [tick, reload] = useReducer((n: number) => n + 1, 0);

  useEffect(() => {
    let cancelled = false;
    api
      .job(jobId)
      .then((job) => !cancelled && dispatch({ type: "loaded", job }))
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Could not load this grave.";
        dispatch({ type: "event", event: "error", seq: 0, data: { message } });
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, tick]);

  const active = view.status !== null && ACTIVE_STATUSES.includes(view.status);
  const shouldStream = view.status === null || active || generation > 0;

  useEffect(() => {
    if (!shouldStream) return;
    const source = new EventSource(api.eventsUrl(jobId));
    source.onopen = () => dispatch({ type: "connected", connected: true });
    source.onerror = () => dispatch({ type: "connected", connected: false });
    const handlers = EVENTS.map((name) => {
      const handler = (e: Event) => {
        // EventSource also fires a native "error" Event (no data) when the connection drops;
        // only real server-sent frames are MessageEvents.
        if (!(e instanceof MessageEvent) || typeof e.data !== "string") return;
        let data: unknown = {};
        try {
          data = JSON.parse(e.data);
        } catch {
          /* ignore malformed frames */
        }
        dispatch({ type: "event", event: name, seq: Number(e.lastEventId) || 0, data });
      };
      source.addEventListener(name, handler);
      return [name, handler] as const;
    });
    const end = () => {
      source.close();
      dispatch({ type: "connected", connected: false });
      reload();
    };
    source.addEventListener("end", end);
    return () => {
      handlers.forEach(([name, handler]) => source.removeEventListener(name, handler));
      source.removeEventListener("end", end);
      source.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, generation, shouldStream && view.job !== null]);

  return { ...view, reload };
}
