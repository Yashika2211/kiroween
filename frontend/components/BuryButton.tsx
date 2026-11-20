"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, api } from "@/lib/api";

/** Delete a grave (job, workspace and history). Asks once before doing anything. */
export function BuryButton({ jobId, repo }: { jobId: string; repo: string }) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!confirming) {
    return (
      <button type="button" className="text-sm text-bone-faint underline underline-offset-4 hover:text-[#ffb3b6]" onClick={() => setConfirming(true)}>
        Bury this grave
      </button>
    );
  }
  return (
    <div className="flex flex-wrap items-center justify-center gap-3 text-sm" role="group" aria-label="Confirm burial">
      <span className="text-bone-dim">Delete {repo} and its results?</span>
      <button
        type="button"
        className="btn border border-blood/60 px-3 py-1.5 text-[#ffb3b6] hover:bg-blood/20"
        onClick={async () => {
          try {
            await api.bury(jobId);
            router.push("/");
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Could not bury it.");
          }
        }}
      >
        Yes, bury it
      </button>
      <button type="button" className="btn-ghost px-3 py-1.5" onClick={() => setConfirming(false)}>
        Keep it
      </button>
      {error && (
        <p role="alert" className="w-full text-center text-[#ffc9cb]">
          {error}
        </p>
      )}
    </div>
  );
}
