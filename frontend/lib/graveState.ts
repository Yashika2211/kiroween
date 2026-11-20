import type { JobSummary } from "./types";
import { ACTIVE_STATUSES } from "./types";

export type GraveState = "risen" | "stirring" | "working" | "failed" | "resting";

/** How a grave should look. A resurrection only counts as risen if its tests pass. */
export function graveState(grave: Pick<JobSummary, "status" | "tests_passed">): GraveState {
  if (grave.status === "risen") return grave.tests_passed === false ? "stirring" : "risen";
  if (ACTIVE_STATUSES.includes(grave.status)) return "working";
  if (grave.status === "failed" || grave.status === "rejected") return "failed";
  return "resting";
}

export function graveHref(grave: Pick<JobSummary, "id" | "status">): string {
  const ritualStarted = ["ritual", "resurrecting", "rising", "risen"].includes(grave.status);
  return ritualStarted ? `/jobs/${grave.id}/ritual` : `/jobs/${grave.id}`;
}
