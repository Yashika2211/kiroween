"use client";

import { motion, useReducedMotion } from "framer-motion";

import { decayTone } from "@/lib/format";
import type { DecayFactor } from "@/lib/types";

/** Decay is shown as number + label + bar, never colour alone. */
export function DecayMeter({ score, label, breakdown }: { score: number; label: string; breakdown: DecayFactor[] }) {
  const reduced = useReducedMotion();
  const tone = decayTone(score);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <p className="font-hand text-lg italic text-paper-faded">Decay</p>
        <p className="font-mono text-4xl font-bold" style={{ color: tone }}>
          {score}
          <span className="text-lg text-paper-faded">/100</span>
        </p>
      </div>
      <div
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
        aria-valuetext={`${score} out of 100, ${label}`}
        className="mt-2 h-3 overflow-hidden rounded-full bg-paper-edge/60"
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: `linear-gradient(90deg, #2f6b45, #c07a1c 50%, ${tone})` }}
          initial={reduced ? { width: `${score}%` } : { width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </div>
      <p className="mt-1 text-right font-display text-xl" style={{ color: tone }}>
        {label}
      </p>
      <dl className="mt-3 space-y-1.5 text-sm">
        {breakdown.map((f) => (
          <div key={f.key} className="grid grid-cols-[1fr_auto] gap-x-3">
            <dt className="text-paper-ink">
              {f.label}
              <span className="block text-xs text-paper-faded">{f.detail}</span>
            </dt>
            <dd className="font-mono text-paper-ink">
              {f.points.toFixed(0)}
              <span className="text-paper-faded">/{f.max_points}</span>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
