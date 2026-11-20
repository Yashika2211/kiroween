"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { ApiError, api } from "@/lib/api";
import { parseRepo } from "@/lib/validate";

const EXAMPLES = ["eigenhombre/PyClojure", "opendoor-labs/pyfin", "nvie/times"];

export function SummonForm() {
  const router = useRouter();
  const reduced = useReducedMotion();
  const inputId = useId();
  const hintId = useId();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function summon(target: string) {
    const repo = parseRepo(target);
    if (!repo) {
      setError("That doesn't look like a GitHub repository. Try https://github.com/owner/repo.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const job = await api.summon(`https://github.com/${repo}`);
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The summoning failed. Try again.");
      setBusy(false);
    }
  }

  return (
    <motion.form
      initial={reduced ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      onSubmit={(e) => {
        e.preventDefault();
        void summon(url);
      }}
      className="panel mx-auto w-full max-w-2xl p-5 sm:p-6"
      aria-describedby={hintId}
    >
      <label htmlFor={inputId} className="label">
        Repository to summon
      </label>
      <div className="mt-2 flex flex-col gap-3 sm:flex-row">
        <input
          id={inputId}
          type="text"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          placeholder="https://github.com/owner/abandoned-repo"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (error) setError(null);
          }}
          aria-invalid={error ? true : undefined}
          aria-errormessage={error ? `${inputId}-error` : undefined}
          className="min-w-0 flex-1 rounded-md border border-stone-light bg-crypt px-4 py-3 font-mono text-sm text-bone placeholder:text-bone-faint focus:border-ecto focus:outline-none"
        />
        <button type="submit" className="btn-ecto" disabled={busy || !url.trim()}>
          {busy ? "Summoning…" : "Summon"}
        </button>
      </div>
      <p id={hintId} className="mt-3 text-sm text-bone-dim">
        Python repositories up to 5,000 lines. Try a known corpse:{" "}
        {EXAMPLES.map((ex, i) => (
          <span key={ex}>
            <button
              type="button"
              className="font-mono text-ecto underline decoration-ecto/40 underline-offset-4 hover:decoration-ecto"
              onClick={() => {
                setUrl(`https://github.com/${ex}`);
                void summon(ex);
              }}
              disabled={busy}
            >
              {ex}
            </button>
            {i < EXAMPLES.length - 1 ? ", " : ""}
          </span>
        ))}
      </p>
      {error && (
        <p id={`${inputId}-error`} role="alert" className="mt-3 rounded-md border border-blood/50 bg-blood/10 px-3 py-2 text-sm text-[#ffc9cb]">
          {error}
        </p>
      )}
    </motion.form>
  );
}
