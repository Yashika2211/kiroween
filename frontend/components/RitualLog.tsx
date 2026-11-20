"use client";

import { useEffect, useRef } from "react";

import type { LogLine } from "@/lib/jobReducer";

export function RitualLog({ logs, live }: { logs: LogLine[]; live: boolean }) {
  const list = useRef<HTMLOListElement>(null);
  // Scroll only the log box, never the page.
  useEffect(() => {
    const el = list.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs.length]);

  return (
    <section className="panel flex h-80 flex-col" aria-labelledby="log-heading">
      <div className="flex items-center justify-between border-b border-stone px-4 py-2">
        <h2 id="log-heading" className="label">
          Incantations
        </h2>
        <span className={`text-xs ${live ? "text-ecto" : "text-bone-faint"}`}>{live ? "● live" : "○ idle"}</span>
      </div>
      <ol ref={list} className="flex-1 overflow-y-auto px-4 py-3 font-mono text-xs leading-relaxed" aria-live="polite" aria-relevant="additions">
        {logs.length === 0 && <li className="text-bone-faint">Waiting for the first words…</li>}
        {logs.map((l, i) => (
          <li key={`${l.seq}-${i}`} className={l.tone === "good" ? "text-ecto" : l.tone === "bad" ? "text-[#ffb3b6]" : "text-bone-dim"}>
            <span aria-hidden="true" className="text-bone-faint">
              ›{" "}
            </span>
            {l.message}
          </li>
        ))}
      </ol>
    </section>
  );
}
