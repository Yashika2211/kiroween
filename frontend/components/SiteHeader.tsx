import Link from "next/link";

import { HealthBadge } from "./HealthBadge";

export function SiteHeader() {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-5 sm:px-6">
      <Link href="/" className="group flex items-center gap-3" aria-label="Necromancer home">
        <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
          <path d="M8 29V13a8 8 0 0 1 16 0v16z" fill="#2a2735" stroke="#7cf5a5" strokeWidth="1.5" />
          <path d="M16 14v8M12.5 17.5h7" stroke="#7cf5a5" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <span className="font-display text-3xl tracking-wide text-bone transition group-hover:text-ecto">
          Necromancer
        </span>
      </Link>
      <HealthBadge />
    </header>
  );
}
