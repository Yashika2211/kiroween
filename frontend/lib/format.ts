import type { DependencyStatus, JobStatus, Severity } from "./types";

export function year(iso: string | null | undefined): string {
  return iso ? String(new Date(iso).getUTCFullYear()) : "?";
}

export function longDate(iso: string | null | undefined): string {
  if (!iso) return "Unknown";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

export function yearsSince(iso: string | null | undefined, now = new Date()): number | null {
  if (!iso) return null;
  return Math.max(0, (now.getTime() - new Date(iso).getTime()) / (365.25 * 86_400_000));
}

export function plural(n: number, word: string, many?: string): string {
  return `${n.toLocaleString()} ${n === 1 ? word : (many ?? `${word}s`)}`;
}

export const STATUS_LABEL: Record<JobStatus, string> = {
  queued: "Awaiting exhumation",
  autopsy: "Autopsy in progress",
  autopsied: "Awaiting the ritual",
  ritual: "Preparing the ritual",
  resurrecting: "Resurrecting",
  rising: "Rising",
  risen: "Risen",
  failed: "Failed",
  rejected: "Turned away",
};

export const SEVERITY_STYLE: Record<Severity, string> = {
  critical: "bg-blood text-white",
  high: "bg-blood-dim text-white",
  moderate: "bg-candle-deep/80 text-crypt",
  low: "bg-stone-light text-bone",
  unknown: "bg-stone text-bone-dim",
};

export const DEP_STYLE: Record<DependencyStatus, { label: string; className: string }> = {
  ok: { label: "Healthy", className: "text-[#2f6b45]" },
  outdated: { label: "Outdated", className: "text-[#8a5a12]" },
  unpinned: { label: "Unpinned", className: "text-paper-faded" },
  missing: { label: "Missing", className: "text-[#9b2226]" },
  dead: { label: "Dead", className: "text-[#9b2226]" },
  unknown: { label: "Unknown", className: "text-paper-faded" },
};

export function decayTone(score: number): string {
  if (score >= 80) return "#9b2226";
  if (score >= 60) return "#b5462a";
  if (score >= 40) return "#c07a1c";
  if (score >= 20) return "#8a7a2a";
  return "#2f6b45";
}
