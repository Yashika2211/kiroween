"use client";

import { motion, useReducedMotion } from "framer-motion";

import { api } from "@/lib/api";
import type { Job } from "@/lib/types";

/** The tombstone cracks, the repo rises, and the PR link is revealed. */
export function RiseScene({ job }: { job: Job }) {
  const reduced = useReducedMotion();
  const result = job.result;
  const passed = result?.tests?.status === "passed";
  const name = job.repo.split("/")[1] ?? job.repo;

  const fade = { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.6 } };

  return (
    <section aria-labelledby="rise-heading" className={`relative mx-auto mt-12 max-w-3xl overflow-hidden rounded-xl border p-8 text-center ${
        passed ? "border-ecto/40 bg-gradient-to-b from-[#132219] to-crypt" : "border-candle/40 bg-gradient-to-b from-[#241d12] to-crypt"
      }`}>
      <div className="relative mx-auto h-56 w-48" aria-hidden="true">
        {/* left half of the stone */}
        <motion.div
          className="absolute bottom-0 left-0 h-40 w-24 rounded-tl-[96px] bg-gradient-to-b from-stone-light to-stone-dark"
          style={{ clipPath: "polygon(0 0, 100% 0, 88% 30%, 100% 55%, 82% 80%, 100% 100%, 0 100%)" }}
          initial={reduced ? false : { x: 0, rotate: 0 }}
          animate={reduced ? { opacity: 0.6 } : { x: -34, rotate: -12, opacity: 0.85 }}
          transition={{ delay: 0.5, duration: 0.9, ease: "easeOut" }}
        />
        {/* right half */}
        <motion.div
          className="absolute bottom-0 right-0 h-40 w-24 rounded-tr-[96px] bg-gradient-to-b from-stone-light to-stone-dark"
          style={{ clipPath: "polygon(12% 0, 100% 0, 100% 100%, 0 100%, 18% 80%, 0 55%, 12% 30%)" }}
          initial={reduced ? false : { x: 0, rotate: 0 }}
          animate={reduced ? { opacity: 0.6 } : { x: 34, rotate: 12, opacity: 0.85 }}
          transition={{ delay: 0.5, duration: 0.9, ease: "easeOut" }}
        />
        {/* the risen repo */}
        <motion.div
          className={`absolute inset-x-6 bottom-6 flex h-32 flex-col items-center justify-center rounded-lg border bg-crypt/90 ${
            passed ? "border-ecto shadow-ecto" : "border-candle shadow-candle"
          }`}
          initial={reduced ? { opacity: 0 } : { y: 90, opacity: 0, scale: 0.8 }}
          animate={reduced ? { opacity: 1 } : { y: -20, opacity: 1, scale: 1 }}
          transition={{ delay: reduced ? 0 : 1.1, duration: reduced ? 0.4 : 1.1, ease: [0.2, 0.8, 0.2, 1] }}
        >
          <span className="text-3xl">🧟</span>
          <span className={`mt-1 max-w-full truncate px-2 font-display text-xl ${passed ? "text-ecto" : "text-candle"}`}>{name}</span>
          <span className="font-mono text-[10px] text-bone-dim">python 3.12</span>
        </motion.div>
      </div>

      <motion.div {...fade} transition={{ delay: reduced ? 0 : 1.8, duration: 0.6 }}>
        <h2 id="rise-heading" className="font-display text-5xl text-bone">
          {passed ? "It lives!" : "It stirs…"}
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-bone-dim">
          {passed
            ? `${job.repo} runs on Python 3.12 and its tests pass.`
            : `${job.repo} was partially revived; some tests still fail and need a human touch.`}{" "}
          {result && `${result.files_changed} files changed${result.iterations ? `, ${result.iterations} Claude repair passes` : ""}.`}
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {result?.pr_url ? (
            <a href={result.pr_url} target="_blank" rel="noreferrer" className="btn-ecto px-6 py-3 text-lg">
              Open the pull request ↗
            </a>
          ) : (
            <a href={api.patchUrl(job.id)} className="btn-ecto px-6 py-3 text-lg" download>
              Download the patch
            </a>
          )}
          <a href={job.url} target="_blank" rel="noreferrer" className="btn-ghost">
            Original repository ↗
          </a>
        </div>
        {result && result.notes.filter((n) => !n.startsWith("dependency:")).slice(-3).length > 0 && (
          <ul className="mx-auto mt-6 max-w-xl space-y-1 text-left text-sm text-bone-faint">
            {result.notes
              .filter((n) => n.startsWith("No GITHUB") || n.startsWith("Could not") || n.includes("manual look"))
              .map((n) => (
                <li key={n}>• {n}</li>
              ))}
          </ul>
        )}
      </motion.div>
    </section>
  );
}
