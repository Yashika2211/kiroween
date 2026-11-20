"use client";

import { useId, useState } from "react";

import type { ResurrectionPlan } from "@/lib/types";

const TABS = [
  ["requirements_md", "requirements.md"],
  ["design_md", "design.md"],
  ["tasks_md", "tasks.md"],
] as const;

/** The generated Kiro-style spec, with keyboard-accessible tabs. */
export function PlanTabs({ plan }: { plan: ResurrectionPlan }) {
  const [active, setActive] = useState(0);
  const base = useId();
  return (
    <section className="panel mt-8" aria-labelledby={`${base}-h`}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone px-4 pt-3">
        <h2 id={`${base}-h`} className="label pb-3">
          Resurrection spec
        </h2>
        <div role="tablist" aria-label="Spec documents" className="flex gap-1">
          {TABS.map(([, label], i) => (
            <button
              key={label}
              id={`${base}-tab-${i}`}
              role="tab"
              type="button"
              aria-selected={active === i}
              aria-controls={`${base}-panel-${i}`}
              tabIndex={active === i ? 0 : -1}
              onClick={() => setActive(i)}
              onKeyDown={(e) => {
                if (e.key === "ArrowRight") setActive((active + 1) % TABS.length);
                if (e.key === "ArrowLeft") setActive((active + TABS.length - 1) % TABS.length);
              }}
              className={`rounded-t-md px-3 py-2 font-mono text-xs ${active === i ? "bg-stone text-ecto" : "text-bone-faint hover:text-bone"}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {TABS.map(([key], i) => (
        <pre
          key={key}
          id={`${base}-panel-${i}`}
          role="tabpanel"
          aria-labelledby={`${base}-tab-${i}`}
          hidden={active !== i}
          tabIndex={0}
          className="max-h-[32rem] overflow-auto whitespace-pre-wrap p-5 font-mono text-xs leading-relaxed text-bone-dim"
        >
          {plan[key]}
        </pre>
      ))}
    </section>
  );
}
