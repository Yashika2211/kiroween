"use client";

import { motion, useReducedMotion } from "framer-motion";

import type { PlanTask, TaskStatus } from "@/lib/types";

const STATE_TEXT: Record<TaskStatus, string> = {
  pending: "not started",
  running: "in progress",
  done: "done",
  failed: "failed",
  skipped: "skipped",
};

function Candle({ status }: { status: TaskStatus }) {
  const reduced = useReducedMotion();
  const lit = status === "done" || status === "running";
  return (
    <svg viewBox="0 0 40 90" className="h-20 w-9" aria-hidden="true">
      {lit && (
        <motion.ellipse
          cx="20"
          cy="16"
          rx={status === "done" ? 16 : 11}
          ry={status === "done" ? 18 : 13}
          fill="rgba(255,207,112,0.25)"
          animate={reduced ? undefined : { opacity: [0.6, 1, 0.7, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
      {lit ? (
        <motion.path
          d="M20 4 C 26 14, 25 22, 20 26 C 15 22, 14 14, 20 4 Z"
          fill={status === "done" ? "#ffcf70" : "#ff9a3c"}
          style={{ transformOrigin: "20px 26px" }}
          animate={reduced ? undefined : { scaleY: [1, 1.12, 0.94, 1.06, 1], rotate: [0, 2, -2, 1, 0] }}
          transition={{ duration: status === "running" ? 0.8 : 1.8, repeat: Infinity }}
        />
      ) : status === "failed" ? (
        <path d="M20 22 q -4 -6 2 -10 q -6 -3 -1 -8" stroke="#8a8374" strokeWidth="1.5" fill="none" />
      ) : null}
      <line x1="20" y1="24" x2="20" y2="30" stroke="#2b2118" strokeWidth="2" />
      <rect x="11" y="30" width="18" height="52" rx="3" fill={status === "failed" ? "#5b5466" : status === "skipped" ? "#3b3748" : "#ece6d9"} />
      <path d="M11 34 q 4 6 0 14" stroke="#cdb98f" strokeWidth="2" fill="none" opacity={status === "pending" ? 0.2 : 0.6} />
      <rect x="7" y="80" width="26" height="6" rx="2" fill="#2a2735" />
    </svg>
  );
}

export function CandleRow({ tasks }: { tasks: PlanTask[] }) {
  return (
    <ol className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-8" aria-label="Ritual tasks">
      {tasks.map((t) => (
        <li key={t.id} className="flex flex-col items-center text-center">
          <Candle status={t.status} />
          <p className={`mt-2 text-xs leading-snug ${t.status === "pending" ? "text-bone-faint" : "text-bone"}`}>{t.title}</p>
          <p
            className={`mt-1 text-[11px] font-semibold uppercase tracking-wider ${
              t.status === "done" ? "text-ecto" : t.status === "failed" ? "text-[#ffb3b6]" : t.status === "running" ? "text-candle" : "text-bone-faint"
            }`}
          >
            {STATE_TEXT[t.status]}
          </p>
          {t.note && <p className="mt-0.5 text-[11px] text-bone-faint">{t.note}</p>}
        </li>
      ))}
    </ol>
  );
}
