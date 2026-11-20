"use client";

import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import { graveState } from "@/lib/graveState";
import type { JobSummary } from "@/lib/types";
import { ACTIVE_STATUSES } from "@/lib/types";

import { Tombstone } from "./Tombstone";

export function GraveyardGrid() {
  const [graves, setGraves] = useState<JobSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;
    const load = async () => {
      try {
        const list = await api.jobs();
        if (stopped) return;
        setGraves(list);
        setError(null);
        // Keep polling while anything is still being worked on.
        if (list.some((g) => ACTIVE_STATUSES.includes(g.status))) timer = setTimeout(load, 3000);
      } catch (err) {
        if (!stopped) setError(err instanceof ApiError ? err.message : "Could not reach the graveyard.");
      }
    };
    void load();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  return (
    <section aria-labelledby="graveyard-heading" className="mt-20">
      <div className="flex items-end justify-between gap-4">
        <h2 id="graveyard-heading" className="font-display text-4xl text-bone">
          The Graveyard
        </h2>
        {graves && graves.length > 0 && (
          <p className="text-sm text-bone-faint">
            {graves.filter((g) => graveState(g) === "risen").length} risen of {graves.length}
          </p>
        )}
      </div>
      <div className="mt-2 h-px bg-gradient-to-r from-transparent via-stone-light to-transparent" />
      {error && (
        <p role="alert" className="mt-8 text-center text-[#ffc9cb]">
          {error}
        </p>
      )}
      {!error && graves === null && (
        <p className="mt-8 text-center text-bone-faint" aria-live="polite">
          Walking the rows…
        </p>
      )}
      {graves && graves.length === 0 && (
        <p className="mt-10 text-center font-hand text-xl italic text-bone-dim">
          No graves yet. The soil is fresh; summon your first corpse above.
        </p>
      )}
      {graves && graves.length > 0 && (
        <ul className="mt-10 grid grid-cols-1 gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
          {graves.map((g, i) => (
            <Tombstone key={g.id} grave={g} index={i} />
          ))}
        </ul>
      )}
    </section>
  );
}
