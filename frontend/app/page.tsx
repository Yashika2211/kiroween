import { GraveyardGrid } from "@/components/GraveyardGrid";
import { SummonForm } from "@/components/SummonForm";

export default function HomePage() {
  return (
    <>
      <section className="pt-10 text-center sm:pt-16">
        <p className="label">Kiroween 2026 · Resurrection</p>
        <h1 className="mt-4 font-display text-5xl leading-none text-bone sm:text-7xl md:text-8xl">
          Raise the <span className="text-ecto drop-shadow-[0_0_24px_rgba(124,245,165,0.45)]">dead</span> code
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-base text-bone-dim sm:text-lg">
          Paste an abandoned Python repository. Necromancer performs an autopsy, writes a resurrection
          spec, rewrites it for Python 3.12 inside a sealed sandbox, and opens a pull request.
        </p>
        <div className="mt-10">
          <SummonForm />
        </div>
        <ol className="mx-auto mt-10 grid max-w-3xl grid-cols-2 gap-3 text-left text-sm sm:grid-cols-4">
          {[
            ["Autopsy", "Why did it die?"],
            ["Ritual", "A spec to revive it"],
            ["Resurrection", "Fix, test, repeat"],
            ["Rise", "A real pull request"],
          ].map(([title, sub], i) => (
            <li key={title} className="panel p-3">
              <span className="font-mono text-xs text-ecto">0{i + 1}</span>
              <p className="font-display text-xl text-bone">{title}</p>
              <p className="text-bone-faint">{sub}</p>
            </li>
          ))}
        </ol>
      </section>
      <GraveyardGrid />
    </>
  );
}
