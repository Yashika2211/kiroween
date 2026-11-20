// Mirrors backend/necromancer/models.py. Keep both in sync.

export type MarkerCategory = "syntax" | "builtin" | "stdlib" | "api";
export type DependencyStatus = "ok" | "outdated" | "unpinned" | "missing" | "dead" | "unknown";
export type Severity = "low" | "moderate" | "high" | "critical" | "unknown";
export type RunStatus = "passed" | "failed" | "timeout" | "error" | "skipped";
export type TaskKind = "rewrite" | "api" | "deps" | "vulns" | "tests" | "verify" | "llm";
export type TaskStatus = "pending" | "running" | "done" | "failed" | "skipped";
export type FixSource = "py2to3" | "pyupgrade" | "api" | "deps" | "vulns" | "smoke" | "llm";
export type JobStatus =
  | "queued"
  | "autopsy"
  | "autopsied"
  | "ritual"
  | "resurrecting"
  | "rising"
  | "risen"
  | "failed"
  | "rejected";

export interface Marker {
  file: string;
  line: number;
  kind: string;
  category: MarkerCategory;
  excerpt: string;
  hint: string;
}

export interface FileHealth {
  path: string;
  lines: number;
  parses: boolean;
  error: string | null;
}

export interface Dependency {
  name: string;
  spec: string;
  pinned_version: string | null;
  source: string;
  latest: string | null;
  status: DependencyStatus;
  replacement: string | null;
  note: string;
}

export interface Vulnerability {
  id: string;
  package: string;
  version: string | null;
  aliases: string[];
  summary: string;
  severity: Severity;
  fixed: string | null;
  url: string;
}

export interface RunResult {
  status: RunStatus;
  exit_code: number | null;
  duration_s: number;
  command: string;
  tail: string;
  reason: string;
}

export interface VitalRecords {
  full_name: string;
  url: string;
  description: string | null;
  created_at: string | null;
  last_commit_at: string | null;
  pushed_at: string | null;
  stars: number | null;
  forks: number | null;
  open_issues: number | null;
  archived: boolean | null;
  default_branch: string | null;
  license: string | null;
  api_available: boolean;
}

export interface DecayFactor {
  key: string;
  label: string;
  points: number;
  max_points: number;
  detail: string;
}

export interface DeathCertificate {
  vitals: VitalRecords;
  python_lines: number;
  python_files: number;
  files: FileHealth[];
  markers: Marker[];
  marker_counts: Record<string, number>;
  has_tests: boolean;
  dependencies: Dependency[];
  vulnerabilities: Vulnerability[];
  probe: RunResult | null;
  decay_score: number;
  decay_label: string;
  decay_breakdown: DecayFactor[];
  cause_of_death: string;
  contributing_factors: string[];
  warnings: string[];
  generated_at: string;
  duration_s: number;
}

export interface PlanTask {
  id: string;
  title: string;
  kind: TaskKind;
  files: string[];
  requirement_ids: string[];
  status: TaskStatus;
  note: string;
}

export interface ResurrectionPlan {
  requirements_md: string;
  design_md: string;
  tasks_md: string;
  tasks: PlanTask[];
}

export interface FileDiff {
  path: string;
  source: FixSource;
  diff: string;
  added: number;
  removed: number;
}

export interface ResurrectionResult {
  tests: RunResult | null;
  install: RunResult | null;
  iterations: number;
  diffs: FileDiff[];
  files_changed: number;
  generated_tests: string[];
  pr_url: string | null;
  branch: string | null;
  patch: string | null;
  pr_body: string | null;
  notes: string[];
}

export interface Job {
  id: string;
  repo: string;
  url: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  certificate: DeathCertificate | null;
  plan: ResurrectionPlan | null;
  result: ResurrectionResult | null;
  error: string | null;
  error_code: string | null;
}

export interface JobSummary {
  id: string;
  repo: string;
  status: JobStatus;
  created_at: string;
  born: number | null;
  died: number | null;
  cause_of_death: string | null;
  decay_score: number | null;
  pr_url: string | null;
}

export interface Health {
  ok: boolean;
  version: string;
  docker: boolean;
  llm: boolean;
  github: boolean;
}

export interface StepEvent {
  key: string;
  label: string;
  state: "running" | "done";
  detail?: string;
}

export interface TestEvent extends RunResult {
  phase: "install" | "test";
}

export const ACTIVE_STATUSES: readonly JobStatus[] = [
  "queued",
  "autopsy",
  "ritual",
  "resurrecting",
  "rising",
];
