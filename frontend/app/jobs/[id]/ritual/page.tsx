"use client";

import Link from "next/link";
import { useState } from "react";

import { CandleRow } from "@/components/CandleRow";
import { DiffViewer } from "@/components/DiffViewer";
import { ErrorPanel } from "@/components/ErrorPanel";
import { PlanTabs } from "@/components/PlanTabs";
import { RiseScene } from "@/components/RiseScene";
import { RitualLog } from "@/components/RitualLog";
import { ApiError, api } from "@/lib/api";
import { STATUS_LABEL } from "@/lib/format";
import { useJobStream } from "@/lib/useJobStream";

export default function RitualPage({ params }: { params: { id: string } }) {
  const [generation, setGeneration] = useState(0);
  const view = useJobStream(params.id, generation);
  const [retryError, setRetryError] = useState<string | null>(null);
  const job = view.job;

  if (!job && view.error) return <ErrorPanel title="This grave is empty" message={view.error} />;
  if (!job) return <p className="mt-20 text-center text-bone-faint">Lighting candles…</p>;

  const tasks = job.plan?.tasks ?? [];
  const done = tasks.filter((t) => t.status === "done").length;

  async function retry() {
    setRetryError(null);
    try {
      await api.resurrect(params.id);
      setGeneration((g) => g + 1);
      view.reload();
    } catch (err) {
      setRetryError(err instanceof ApiError ? err.message : "Could not restart the ritual.");
    }
  }

  return (
    <div className="pt-8">
      <p className="text-center font-mono text-sm text-bone-faint">
        <Link href="/" className="hover:text-ecto">
          ← graveyard
        </Link>{" "}
        /{" "}
        <Link href={`/jobs/${params.id}`} className="hover:text-ecto">
          {job.repo}
        </Link>{" "}
        / ritual
      </p>
      <h1 className="mt-4 text-center font-display text-6xl text-bone">The Ritual</h1>
      <p className="mt-2 text-center text-bone-dim" role="status">
        {view.status ? STATUS_LABEL[view.status] : "…"}
        {tasks.length > 0 && ` · ${done} of ${tasks.length} candles lit`}
      </p>

      {tasks.length > 0 && (
        <div className="panel mt-8 px-4 py-6">
          <CandleRow tasks={tasks} />
        </div>
      )}

      {view.status === "risen" && <RiseScene job={job} />}

      {view.status === "failed" && (
        <div role="alert" className="mx-auto mt-8 max-w-2xl rounded-lg border border-blood/50 bg-blood/10 p-5 text-center">
          <p className="font-display text-2xl text-[#ffc9cb]">The ritual was interrupted</p>
          <p className="mt-2 text-bone-dim">{job.error}</p>
          <button type="button" className="btn-ghost mt-4" onClick={retry}>
            Try the ritual again
          </button>
          {retryError && <p className="mt-2 text-sm text-[#ffc9cb]">{retryError}</p>}
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[2fr_3fr]">
        <RitualLog logs={view.logs.length ? view.logs : (job.result?.notes ?? []).map((m, i) => ({ seq: i, message: m, tone: "info" as const }))} live={view.connected} />
        <DiffViewer diffs={view.diffs.length ? view.diffs : (job.result?.diffs ?? [])} />
      </div>

      {job.plan && <PlanTabs plan={job.plan} />}
    </div>
  );
}
