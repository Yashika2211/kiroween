"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";

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

/** If the stream is silent this long while the job is active, poll the snapshot instead. */
const QUIET_MS = 3000;

/**
 * Load a job and follow it live.
 *
 * - The snapshot (`GET /api/jobs/:id`) carries the event sequence it reflects, so replayed
 *   events at or below it are ignored and can't roll the view back.
 * - One EventSource per page; if it ends while the job is still active it is reopened from
 *   the last applied sequence.
 * - If the stream goes quiet while the job is active, the snapshot is polled, so the page
 *   never freezes even if a stream stalls.
 */
export function useJobStream(jobId: string, generation = 0): JobView & { reload: () => void } {
  const [view, dispatch] = useReducer(jobReducer, initialView);
  const [epoch, reopen] = useReducer((n: number) => n + 1, 0);
  const lastSeqRef = useRef(0);
  const lastEventAt = useRef(Date.now());
  const streamOpen = useRef(false);
  lastSeqRef.current = view.lastSeq;

  const reload = useCallback(() => {
    api
      .jobWithSeq(jobId)
      .then(({ job, seq }) => {
        dispatch({ type: "loaded", job, seq });
        lastEventAt.current = Date.now();
        if (ACTIVE_STATUSES.includes(job.status) && !streamOpen.current) reopen();
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Could not load this grave.";
        dispatch({ type: "event", event: "error", seq: 0, data: { message } });
      });
  }, [jobId]);

  // Initial load, and again whenever the caller restarts the job.
  useEffect(() => {
    reload();
  }, [reload, generation]);

  // The live stream.
  useEffect(() => {
    const source = new EventSource(`${api.eventsUrl(jobId)}?after=${lastSeqRef.current}`);
    streamOpen.current = true;
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
        lastEventAt.current = Date.now();
        dispatch({ type: "event", event: name, seq: Number(e.lastEventId) || 0, data });
      };
      source.addEventListener(name, handler);
      return [name, handler] as const;
    });
    const end = () => {
      source.close();
      streamOpen.current = false;
      dispatch({ type: "connected", connected: false });
      reload();
    };
    source.addEventListener("end", end);
    return () => {
      handlers.forEach(([name, handler]) => source.removeEventListener(name, handler));
      source.removeEventListener("end", end);
      source.close();
      streamOpen.current = false;
    };
  }, [jobId, generation, epoch, reload]);

  // Safety net: poll while active if the stream has gone quiet.
  const active = view.status !== null && ACTIVE_STATUSES.includes(view.status);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => {
      if (Date.now() - lastEventAt.current > QUIET_MS) reload();
    }, QUIET_MS);
    return () => clearInterval(timer);
  }, [active, reload]);

  return { ...view, reload };
}
