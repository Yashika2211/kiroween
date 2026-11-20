import type { Health, Job, JobSummary } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "unreachable", "The crypt is sealed: can't reach the Necromancer API.");
  }
  if (!response.ok) {
    let code = "error";
    let message = `Request failed (${response.status})`;
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object") {
        const b = body as Record<string, unknown>;
        if (typeof b.code === "string") code = b.code;
        if (typeof b.message === "string") message = b.message;
        else if (Array.isArray(b.detail)) message = "That doesn't look like a GitHub repository URL.";
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, code, message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  summon: (url: string) => request<Job>("/api/summon", { method: "POST", body: JSON.stringify({ url }) }),
  jobs: () => request<JobSummary[]>("/api/jobs"),
  job: (id: string) => request<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  resurrect: (id: string) =>
    request<Job>(`/api/jobs/${encodeURIComponent(id)}/resurrect`, { method: "POST" }),
  bury: (id: string) => request<void>(`/api/jobs/${encodeURIComponent(id)}`, { method: "DELETE" }),
  patchUrl: (id: string) => `${API_URL}/api/jobs/${encodeURIComponent(id)}/patch`,
  eventsUrl: (id: string) => `${API_URL}/api/jobs/${encodeURIComponent(id)}/events`,
};
