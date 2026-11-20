"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AutopsySteps } from "@/components/AutopsySteps";
import { BuryButton } from "@/components/BuryButton";
import { DeathCertificate } from "@/components/DeathCertificate";
import { ErrorPanel } from "@/components/ErrorPanel";
import { ApiError, api } from "@/lib/api";
import { useJobStream } from "@/lib/useJobStream";

export default function CertificatePage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const view = useJobStream(params.id);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const job = view.job;
  const cert = job?.certificate;

  async function beginRitual() {
    setStarting(true);
    setStartError(null);
    try {
      await api.resurrect(params.id);
      router.push(`/jobs/${params.id}/ritual`);
    } catch (err) {
      setStartError(err instanceof ApiError ? err.message : "The ritual could not begin.");
      setStarting(false);
    }
  }

  if (!job && view.error) {
    return <ErrorPanel title="This grave is empty" message={view.error} />;
  }

  if (view.status === "rejected" || (view.status === "failed" && !cert)) {
    return <ErrorPanel title="The autopsy could not be completed" message={job?.error ?? view.error ?? "Unknown error"} />;
  }

  return (
    <div className="pt-8">
      <p className="mb-6 text-center font-mono text-sm text-bone-faint">
        <Link href="/" className="hover:text-ecto">
          ← graveyard
        </Link>{" "}
        / {job?.repo ?? "…"}
      </p>
      {!cert && <AutopsySteps steps={view.steps} />}
      {cert && (
        <>
          <DeathCertificate cert={cert} />
          <div className="mx-auto mt-10 flex max-w-4xl flex-col items-center gap-3 text-center">
            {job?.status === "autopsied" || job?.status === "failed" ? (
              <>
                <button type="button" className="btn-ecto px-8 py-3 text-lg" onClick={beginRitual} disabled={starting}>
                  {starting ? "Lighting the candles…" : "Begin the Ritual"}
                </button>
                <p className="max-w-xl text-sm text-bone-faint">
                  Necromancer will write a resurrection spec, apply deterministic fixes, run the tests in a
                  network-isolated sandbox and, if needed, ask Claude to repair what is left.
                </p>
              </>
            ) : (
              <Link href={`/jobs/${params.id}/ritual`} className="btn-ghost">
                View the ritual →
              </Link>
            )}
            {job && !["autopsy", "ritual", "resurrecting", "rising"].includes(job.status) && (
              <div className="mt-6">
                <BuryButton jobId={job.id} repo={job.repo} />
              </div>
            )}
            {startError && (
              <p role="alert" className="text-[#ffc9cb]">
                {startError}
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
