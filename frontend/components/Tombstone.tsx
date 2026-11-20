"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";

import { STATUS_LABEL } from "@/lib/format";
import { graveHref, graveState } from "@/lib/graveState";
import type { JobSummary } from "@/lib/types";

export function Tombstone({ grave, index }: { grave: JobSummary; index: number }) {
  const reduced = useReducedMotion();
  const state = graveState(grave);
  const risen = state === "risen";
  const stirring = state === "stirring";
  const active = state === "working";
  const failed = state === "failed";
  const [owner, name] = grave.repo.split("/");
  const href = graveHref(grave);

  return (
    <motion.li
      initial={reduced ? false : { opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.06, 0.6), duration: 0.5, ease: "easeOut" }}
      className="list-none"
    >
      <Link
        href={href}
        className={`group relative mx-auto block h-full max-w-sm rounded-t-[999px] rounded-b-md border-2 px-5 pb-6 pt-12 text-center transition
          ${risen ? "animate-pulse-glow border-ecto/70 bg-gradient-to-b from-[#24352d] to-stone-dark" : "border-stone-light bg-gradient-to-b from-stone-light to-stone-dark hover:border-bone-faint"}
          ${active || stirring ? "border-candle/60" : ""}`}
      >
        <span aria-hidden="true" className="absolute left-1/2 top-4 -translate-x-1/2 text-lg text-bone-faint">
          {risen ? "☥" : "✝"}
        </span>
        <p className="font-display text-sm uppercase tracking-[0.3em] text-bone-faint">Here lies</p>
        <h3 className="mt-1 break-words font-display text-2xl leading-tight text-bone">{name}</h3>
        <p className="text-xs text-bone-faint">by {owner}</p>
        <p className="mt-3 font-mono text-sm text-bone-dim">
          {grave.born ?? "?"} – {grave.died ?? "?"}
        </p>
        {grave.cause_of_death && (
          <p className="mt-3 line-clamp-3 font-hand text-sm italic text-bone-dim">“{grave.cause_of_death}”</p>
        )}
        <p
          className={`mt-4 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
            risen ? "bg-ecto/15 text-ecto" : failed ? "bg-blood/15 text-[#ffb3b6]" : active || stirring ? "bg-candle/15 text-candle" : "bg-crypt/60 text-bone-dim"
          }`}
        >
          {active && <span aria-hidden="true" className="inline-block h-1.5 w-1.5 animate-flicker rounded-full bg-candle" />}
          {stirring ? "Stirring · tests failing" : STATUS_LABEL[grave.status]}
          {grave.decay_score !== null && !risen && <span className="font-mono">· decay {grave.decay_score}</span>}
        </p>
        <span aria-hidden="true" className="pointer-events-none absolute inset-x-6 bottom-0 h-3 rounded-full bg-black/50 blur-md" />
      </Link>
    </motion.li>
  );
}
