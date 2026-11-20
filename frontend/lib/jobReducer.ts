import type {
  DeathCertificate,
  FileDiff,
  Job,
  JobStatus,
  PlanTask,
  ResurrectionPlan,
  ResurrectionResult,
  StepEvent,
  TestEvent,
} from "./types";

export interface LogLine {
  seq: number;
  message: string;
  tone: "info" | "good" | "bad";
}

export interface JobView {
  job: Job | null;
  status: JobStatus | null;
  steps: Record<string, StepEvent>;
  logs: LogLine[];
  diffs: FileDiff[];
  tests: TestEvent[];
  connected: boolean;
  error: string | null;
  /** Highest server event sequence applied, so replays after a reconnect are ignored. */
  lastSeq: number;
}

export type JobAction =
  | { type: "loaded"; job: Job; seq?: number }
  | { type: "connected"; connected: boolean }
  | { type: "event"; event: string; seq: number; data: unknown };

export const initialView: JobView = {
  job: null,
  status: null,
  steps: {},
  logs: [],
  diffs: [],
  tests: [],
  connected: false,
  error: null,
  lastSeq: 0,
};

const MAX_LOGS = 400;

function pushLog(view: JobView, line: LogLine): LogLine[] {
  const logs = [...view.logs, line];
  return logs.length > MAX_LOGS ? logs.slice(logs.length - MAX_LOGS) : logs;
}

function withJob(view: JobView, patch: Partial<Job>): Job | null {
  return view.job ? { ...view.job, ...patch } : view.job;
}

export function jobReducer(view: JobView, action: JobAction): JobView {
  switch (action.type) {
    case "loaded": {
      // Never let an older snapshot overwrite newer streamed state.
      if (action.seq !== undefined && action.seq < view.lastSeq) return view;
      return {
        ...view,
        job: action.job,
        status: action.job.status,
        error: action.job.error,
        diffs: view.diffs.length ? view.diffs : (action.job.result?.diffs ?? []),
        lastSeq: Math.max(view.lastSeq, action.seq ?? 0),
      };
    }
    case "connected":
      return { ...view, connected: action.connected };
    case "event": {
      if (action.seq > 0 && action.seq <= view.lastSeq) return view;
      const next = applyEvent(view, action.event, action.seq, action.data);
      return action.seq > view.lastSeq ? { ...next, lastSeq: action.seq } : next;
    }
  }
}

function applyEvent(view: JobView, event: string, seq: number, data: unknown): JobView {
  const d = (data ?? {}) as Record<string, unknown>;
  switch (event) {
    case "snapshot": {
      const job = data as Job;
      return jobReducer(view, { type: "loaded", job });
    }
    case "status": {
      const status = d.status as JobStatus;
      return { ...view, status, job: withJob(view, { status }) };
    }
    case "step": {
      const step = d as unknown as StepEvent;
      return { ...view, steps: { ...view.steps, [step.key]: step } };
    }
    case "certificate":
      return { ...view, job: withJob(view, { certificate: data as DeathCertificate }) };
    case "plan":
      return { ...view, job: withJob(view, { plan: data as ResurrectionPlan }) };
    case "task": {
      const task = data as PlanTask;
      const plan = view.job?.plan;
      if (!plan) return view;
      const tasks = plan.tasks.map((t) => (t.id === task.id ? task : t));
      return { ...view, job: withJob(view, { plan: { ...plan, tasks } }) };
    }
    case "diff":
      return { ...view, diffs: [...view.diffs, data as FileDiff] };
    case "log":
      return { ...view, logs: pushLog(view, { seq, message: String(d.message ?? ""), tone: "info" }) };
    case "test": {
      const test = data as TestEvent;
      const ok = test.status === "passed";
      const label = test.phase === "install" ? "Install" : "Tests";
      const lastLine = test.tail.trim().split("\n").pop() ?? "";
      return {
        ...view,
        tests: [...view.tests, test],
        logs: pushLog(view, {
          seq,
          message: `${label} ${test.status}${lastLine ? `: ${lastLine}` : ""}`,
          tone: ok ? "good" : test.status === "skipped" ? "info" : "bad",
        }),
      };
    }
    case "result":
      return { ...view, job: withJob(view, { result: data as ResurrectionResult }) };
    case "error": {
      const message = String(d.message ?? "Something went wrong.");
      return {
        ...view,
        error: message,
        job: withJob(view, { error: message }),
        logs: pushLog(view, { seq, message, tone: "bad" }),
      };
    }
    default:
      return view;
  }
}
