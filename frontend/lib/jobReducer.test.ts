import { describe, expect, it } from "vitest";

import { initialView, jobReducer } from "./jobReducer";
import type { Job, PlanTask } from "./types";

const task = (id: string, status: PlanTask["status"] = "pending"): PlanTask => ({
  id,
  title: `Task ${id}`,
  kind: "rewrite",
  files: [],
  requirement_ids: ["1"],
  status,
  note: "",
});

const job: Job = {
  id: "abc",
  repo: "nvie/times",
  url: "https://github.com/nvie/times",
  status: "autopsied",
  created_at: "2026-11-20T00:00:00Z",
  updated_at: "2026-11-20T00:00:00Z",
  certificate: null,
  plan: { requirements_md: "", design_md: "", tasks_md: "", tasks: [task("1"), task("2")] },
  result: null,
  error: null,
  error_code: null,
};

describe("jobReducer", () => {
  it("tracks status, tasks and diffs from events", () => {
    let v = jobReducer(initialView, { type: "loaded", job });
    v = jobReducer(v, { type: "event", event: "status", seq: 1, data: { status: "resurrecting" } });
    v = jobReducer(v, { type: "event", event: "task", seq: 2, data: task("2", "done") });
    v = jobReducer(v, {
      type: "event",
      event: "diff",
      seq: 3,
      data: { path: "a.py", source: "py2to3", diff: "", added: 1, removed: 1 },
    });
    expect(v.status).toBe("resurrecting");
    expect(v.job?.plan?.tasks.map((t) => t.status)).toEqual(["pending", "done"]);
    expect(v.diffs).toHaveLength(1);
  });

  it("turns test events into coloured log lines", () => {
    const v = jobReducer(initialView, {
      type: "event",
      event: "test",
      seq: 4,
      data: { phase: "test", status: "passed", tail: "...\n8 passed in 4.6s", exit_code: 0, duration_s: 1, command: "", reason: "" },
    });
    expect(v.logs[0]).toMatchObject({ tone: "good", message: "Tests passed: 8 passed in 4.6s" });
  });

  it("records step progress and errors", () => {
    let v = jobReducer(initialView, {
      type: "event",
      event: "step",
      seq: 1,
      data: { key: "exhume", label: "Exhuming", state: "done" },
    });
    v = jobReducer(v, { type: "event", event: "error", seq: 2, data: { message: "too big" } });
    expect(v.steps.exhume?.state).toBe("done");
    expect(v.error).toBe("too big");
  });

  it("ignores events replayed after a reconnect", () => {
    const diff = { path: "a.py", source: "py2to3", diff: "", added: 1, removed: 0 };
    let v = jobReducer(initialView, { type: "event", event: "diff", seq: 5, data: diff });
    v = jobReducer(v, { type: "event", event: "diff", seq: 5, data: diff });
    v = jobReducer(v, { type: "event", event: "diff", seq: 3, data: diff });
    expect(v.diffs).toHaveLength(1);
    expect(v.lastSeq).toBe(5);
    v = jobReducer(v, { type: "event", event: "diff", seq: 6, data: diff });
    expect(v.diffs).toHaveLength(2);
  });

  it("ignores unknown events", () => {
    const v = jobReducer(initialView, { type: "event", event: "weird", seq: 1, data: {} });
    expect({ ...v, lastSeq: 0 }).toEqual(initialView);
  });
});
