"use client";

import { useMemo, useState } from "react";

import type { FileDiff, FixSource } from "@/lib/types";

const SOURCE_LABEL: Record<FixSource, string> = {
  py2to3: "2to3",
  pyupgrade: "pyupgrade",
  api: "API fix",
  deps: "dependencies",
  vulns: "security",
  smoke: "new tests",
  llm: "Claude",
};

function lineClass(line: string): string {
  if (line.startsWith("+++") || line.startsWith("---")) return "text-bone-faint";
  if (line.startsWith("@@")) return "diff-hunk";
  if (line.startsWith("+")) return "diff-add";
  if (line.startsWith("-")) return "diff-del";
  return "text-bone-dim";
}

export function DiffViewer({ diffs }: { diffs: FileDiff[] }) {
  const [selected, setSelected] = useState(0);
  const current = diffs[Math.min(selected, diffs.length - 1)];
  const lines = useMemo(() => (current ? current.diff.split("\n").slice(0, 600) : []), [current]);

  if (!diffs.length) {
    return (
      <section className="panel flex h-80 items-center justify-center p-6 text-center text-bone-faint">
        Diffs appear here as each file is rewritten.
      </section>
    );
  }

  return (
    <section className="panel grid h-[28rem] grid-rows-[auto_1fr] overflow-hidden md:grid-cols-[16rem_1fr] md:grid-rows-1" aria-labelledby="diff-heading">
      <h2 id="diff-heading" className="sr-only">
        Changed files
      </h2>
      <ul className="max-h-40 overflow-y-auto border-b border-stone md:max-h-none md:border-b-0 md:border-r" role="listbox" aria-label="Changes">
        {diffs.map((d, i) => (
          <li key={`${d.path}-${d.source}-${i}`} role="option" aria-selected={i === selected}>
            <button
              type="button"
              onClick={() => setSelected(i)}
              className={`w-full px-3 py-2 text-left text-xs transition ${i === selected ? "bg-stone text-bone" : "text-bone-dim hover:bg-stone/50"}`}
            >
              <span className="block truncate font-mono">{d.path}</span>
              <span className="mt-0.5 flex gap-2">
                <span className={`rounded px-1 ${d.source === "llm" ? "bg-[#3b2f5c] text-[#d6c8ff]" : "bg-crypt text-bone-faint"}`}>{SOURCE_LABEL[d.source]}</span>
                <span className="text-ecto">+{d.added}</span>
                <span className="text-[#ffb3b6]">−{d.removed}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      <pre className="overflow-auto p-3 font-mono text-xs leading-relaxed" tabIndex={0} aria-label={`Diff of ${current?.path ?? ""}`}>
        {lines.map((line, i) => (
          <div key={i} className={`whitespace-pre px-1 ${lineClass(line)}`}>
            {line || " "}
          </div>
        ))}
      </pre>
    </section>
  );
}
