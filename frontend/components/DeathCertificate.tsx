"use client";

import { motion, useReducedMotion } from "framer-motion";

import { longDate, plural, yearsSince } from "@/lib/format";
import type { DeathCertificate as Cert } from "@/lib/types";

import { DependencyTable, MarkerSummary, ProbeResult, Section, VulnList } from "./CertificateSections";
import { DecayMeter } from "./DecayMeter";

export function DeathCertificate({ cert }: { cert: Cert }) {
  const reduced = useReducedMotion();
  const v = cert.vitals;
  const years = yearsSince(v.last_commit_at);
  const unparseable = cert.files.filter((f) => !f.parses);

  return (
    <motion.article
      initial={reduced ? false : { opacity: 0, rotate: -1.5, y: 30 }}
      animate={{ opacity: 1, rotate: 0, y: 0 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      className="paper relative mx-auto max-w-4xl rounded-sm p-6 shadow-paper sm:p-10"
      aria-labelledby="cert-title"
    >
      <div aria-hidden="true" className="pointer-events-none absolute inset-3 border-2 border-double border-paper-edge" />
      <header className="relative text-center">
        <p className="font-hand text-sm uppercase tracking-[0.4em] text-paper-faded">Certificate of</p>
        <h1 id="cert-title" className="font-display text-5xl text-paper-ink sm:text-6xl">
          Death
        </h1>
        <p className="mt-2 font-hand text-lg italic text-paper-faded">
          issued by the Necromancer’s office after an examination of {plural(cert.python_files, "file")} and{" "}
          {plural(cert.python_lines, "line")} of Python
        </p>
      </header>

      <div className="relative mt-8 grid gap-8 md:grid-cols-[1.4fr_1fr]">
        <div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-paper-ink">
            <dt className="font-hand italic text-paper-faded">Name of deceased</dt>
            <dd>
              <a href={v.url} target="_blank" rel="noreferrer" className="font-mono font-semibold underline decoration-paper-faded underline-offset-2">
                {v.full_name}
              </a>
            </dd>
            {v.description && (
              <>
                <dt className="font-hand italic text-paper-faded">Occupation</dt>
                <dd>{v.description}</dd>
              </>
            )}
            <dt className="font-hand italic text-paper-faded">Born</dt>
            <dd>{longDate(v.created_at)}</dd>
            <dt className="font-hand italic text-paper-faded">Last breath</dt>
            <dd>
              {longDate(v.last_commit_at)}
              {years !== null && <span className="text-paper-faded"> ({years.toFixed(1)} years ago)</span>}
            </dd>
            <dt className="font-hand italic text-paper-faded">Mourners</dt>
            <dd>
              {v.stars ?? "?"} stars · {v.forks ?? "?"} forks · {v.open_issues ?? "?"} open issues
            </dd>
            <dt className="font-hand italic text-paper-faded">Estate</dt>
            <dd>
              {v.license ?? "no licence"} · {v.archived ? "archived by its owner" : "not archived"}
            </dd>
          </dl>

          <div className="mt-6 rounded border-l-4 border-[#9b2226] bg-paper-edge/25 p-4">
            <p className="font-hand text-sm uppercase tracking-widest text-paper-faded">Cause of death</p>
            <p className="mt-1 font-hand text-2xl leading-snug text-paper-ink">{cert.cause_of_death}</p>
          </div>
          {cert.contributing_factors.length > 0 && (
            <ul className="mt-3 list-disc space-y-0.5 pl-5 text-sm text-paper-ink">
              {cert.contributing_factors.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}
        </div>
        <DecayMeter score={cert.decay_score} label={cert.decay_label} breakdown={cert.decay_breakdown} />
      </div>

      <Section title="Signs of age">
        {unparseable.length > 0 && (
          <p className="mb-3 text-sm text-[#9b2226]">
            {plural(unparseable.length, "file")} no longer parse on Python 3.12:{" "}
            <span className="font-mono">{unparseable.map((f) => f.path).join(", ")}</span>
          </p>
        )}
        <MarkerSummary counts={cert.marker_counts} markers={cert.markers} />
      </Section>

      <Section title="Toxicology: dependencies">
        <DependencyTable deps={cert.dependencies} />
      </Section>

      <Section title="Toxicology: known vulnerabilities">
        <VulnList vulns={cert.vulnerabilities} />
      </Section>

      <Section title="Pulse check">
        <ProbeResult probe={cert.probe} />
        <p className="mt-2 text-sm text-paper-faded">{cert.has_tests ? "A test suite was found." : "No tests were found; smoke tests will be generated."}</p>
      </Section>

      {cert.warnings.length > 0 && (
        <Section title="Coroner’s notes">
          <ul className="list-disc pl-5 text-sm text-paper-faded">
            {cert.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Section>
      )}

      <footer className="relative mt-10 flex flex-wrap items-end justify-between gap-4 text-sm text-paper-faded">
        <p>
          Examined in {cert.duration_s.toFixed(1)}s on {longDate(cert.generated_at)}
        </p>
        <p className="font-hand text-2xl italic text-paper-ink" aria-label="Signed: The Necromancer">
          ~ The Necromancer
        </p>
      </footer>
    </motion.article>
  );
}
