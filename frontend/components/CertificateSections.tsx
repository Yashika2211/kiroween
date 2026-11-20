import { DEP_STYLE, SEVERITY_STYLE, plural } from "@/lib/format";
import type { Dependency, Marker, RunResult, Vulnerability } from "@/lib/types";

export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h3 className="border-b border-paper-edge pb-1 font-display text-2xl text-paper-ink">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function DependencyTable({ deps }: { deps: Dependency[] }) {
  if (!deps.length) return <p className="font-hand italic text-paper-faded">No declared dependencies.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Declared dependencies and their condition</caption>
        <thead className="text-xs uppercase tracking-wider text-paper-faded">
          <tr>
            <th scope="col" className="py-1 pr-3">Package</th>
            <th scope="col" className="py-1 pr-3">Declared</th>
            <th scope="col" className="py-1 pr-3">Latest for 3.12</th>
            <th scope="col" className="py-1">Condition</th>
          </tr>
        </thead>
        <tbody>
          {deps.map((d) => {
            const style = DEP_STYLE[d.status];
            return (
              <tr key={d.name} className="border-t border-paper-edge/60 align-top">
                <td className="py-1.5 pr-3 font-mono">{d.name}</td>
                <td className="py-1.5 pr-3 font-mono text-paper-faded">{d.spec || "any"}</td>
                <td className="py-1.5 pr-3 font-mono">{d.latest ?? "—"}</td>
                <td className={`py-1.5 font-semibold ${style.className}`}>
                  {style.label}
                  {d.status === "dead" && (
                    <span className="block text-xs font-normal">
                      → {d.replacement ?? "standard library"} ({d.note})
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function VulnList({ vulns }: { vulns: Vulnerability[] }) {
  if (!vulns.length) return <p className="font-hand italic text-paper-faded">No known vulnerabilities in pinned versions.</p>;
  return (
    <ul className="space-y-2">
      {vulns.slice(0, 12).map((v) => (
        <li key={`${v.id}-${v.version}`} className="flex flex-wrap items-baseline gap-2 text-sm">
          <span className={`rounded px-1.5 py-0.5 text-xs font-bold uppercase ${SEVERITY_STYLE[v.severity]}`}>{v.severity}</span>
          <a href={v.url} target="_blank" rel="noreferrer" className="font-mono text-paper-ink underline decoration-paper-faded underline-offset-2">
            {v.aliases.find((a) => a.startsWith("CVE")) ?? v.id}
          </a>
          <span className="font-mono text-paper-faded">
            {v.package} {v.version}
            {v.fixed && <> → {v.fixed}</>}
          </span>
          {v.summary && <span className="w-full pl-1 text-paper-faded">{v.summary}</span>}
        </li>
      ))}
      {vulns.length > 12 && <li className="text-sm text-paper-faded">…and {plural(vulns.length - 12, "more")}</li>}
    </ul>
  );
}

export function MarkerSummary({ counts, markers }: { counts: Record<string, number>; markers: Marker[] }) {
  const entries = Object.entries(counts);
  if (!entries.length) return <p className="font-hand italic text-paper-faded">No legacy idioms found.</p>;
  return (
    <>
      <ul className="flex flex-wrap gap-2">
        {entries.map(([kind, n]) => (
          <li key={kind} className="rounded-full border border-paper-edge bg-paper-edge/30 px-2.5 py-0.5 text-sm">
            {kind.replaceAll("_", " ")} <span className="font-mono font-bold">×{n}</span>
          </li>
        ))}
      </ul>
      <details className="mt-3">
        <summary className="cursor-pointer text-sm text-paper-faded underline underline-offset-2">Show evidence</summary>
        <ul className="mt-2 max-h-72 space-y-1 overflow-y-auto font-mono text-xs">
          {markers.slice(0, 120).map((m) => (
            <li key={`${m.file}:${m.line}:${m.kind}`}>
              <span className="text-paper-faded">
                {m.file}:{m.line}
              </span>{" "}
              <code className="text-paper-ink">{m.excerpt}</code>
              <span className="text-paper-faded"> — {m.hint}</span>
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}

export function ProbeResult({ probe }: { probe: RunResult | null }) {
  if (!probe) return null;
  const label =
    probe.status === "passed" ? "Installs on Python 3.12" : probe.status === "skipped" ? `Not checked: ${probe.reason}` : "No pulse: pip install fails on Python 3.12";
  return (
    <>
      <p className={`font-semibold ${probe.status === "passed" ? "text-[#2f6b45]" : probe.status === "skipped" ? "text-paper-faded" : "text-[#9b2226]"}`}>{label}</p>
      {probe.tail && probe.status !== "passed" && (
        <pre className="mt-2 max-h-48 overflow-auto rounded bg-paper-ink/90 p-3 text-xs leading-relaxed text-paper">{probe.tail.split("\n").slice(-14).join("\n")}</pre>
      )}
    </>
  );
}
