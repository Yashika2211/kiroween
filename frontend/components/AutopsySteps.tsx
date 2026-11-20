"use client";

import { motion, useReducedMotion } from "framer-motion";

import type { StepEvent } from "@/lib/types";

const ORDER: Array<[string, string]> = [
  ["exhume", "Exhuming the body (git clone)"],
  ["measure", "Measuring the remains"],
  ["records", "Pulling vital records from GitHub"],
  ["examine", "Examining every file for Python 2 markers"],
  ["toxicology", "Toxicology: dependencies and known vulnerabilities"],
  ["probe", "Checking for a pulse (pip install on Python 3.12)"],
  ["verdict", "Writing the Death Certificate"],
];

export function AutopsySteps({ steps }: { steps: Record<string, StepEvent> }) {
  const reduced = useReducedMotion();
  return (
    <section className="panel mx-auto max-w-2xl p-6" aria-labelledby="autopsy-progress">
      <h2 id="autopsy-progress" className="font-display text-3xl text-bone">
        Autopsy in progress
      </h2>
      <ol className="mt-5 space-y-3" aria-live="polite">
        {ORDER.map(([key, fallback]) => {
          const step = steps[key];
          const state = step?.state ?? "pending";
          return (
            <motion.li
              key={key}
              initial={reduced ? false : { opacity: 0, x: -8 }}
              animate={{ opacity: state === "pending" ? 0.45 : 1, x: 0 }}
              className="flex items-start gap-3"
            >
              <span
                aria-hidden="true"
                className={`mt-1 inline-block h-3 w-3 flex-none rounded-full ${
                  state === "done" ? "bg-ecto shadow-ecto" : state === "running" ? "animate-flicker bg-candle shadow-candle" : "border border-stone-light"
                }`}
              />
              <span className="flex-1">
                <span className="text-bone">{step?.label ?? fallback}</span>
                {step?.detail && <span className="ml-2 font-mono text-xs text-bone-faint">{step.detail}</span>}
                <span className="sr-only"> ({state})</span>
              </span>
            </motion.li>
          );
        })}
      </ol>
    </section>
  );
}
