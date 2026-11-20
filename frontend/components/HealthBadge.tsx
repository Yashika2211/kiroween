"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Health } from "@/lib/types";

/** Shows which powers the backend has: Docker sandbox, Claude repairs, GitHub PRs. */
export function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);
  const [down, setDown] = useState(false);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setDown(true));
  }, []);

  if (down) {
    return (
      <p role="status" className="rounded-full border border-blood/60 px-3 py-1 text-xs text-[#ffb3b6]">
        API offline
      </p>
    );
  }
  if (!health) return <span className="h-6 w-40" aria-hidden="true" />;

  const powers = [
    { on: health.docker, label: "Sandbox" },
    { on: health.llm, label: "Claude" },
    { on: health.github, label: "PRs" },
  ];
  return (
    <ul className="flex gap-2 text-xs" aria-label="Backend capabilities">
      {powers.map((p) => (
        <li
          key={p.label}
          className={`rounded-full border px-2.5 py-1 ${p.on ? "border-ecto/50 text-ecto" : "border-stone-light text-bone-faint"}`}
        >
          <span aria-hidden="true">{p.on ? "●" : "○"}</span> {p.label}
          <span className="sr-only">{p.on ? " enabled" : " disabled"}</span>
        </li>
      ))}
    </ul>
  );
}
