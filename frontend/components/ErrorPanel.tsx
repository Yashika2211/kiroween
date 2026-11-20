import Link from "next/link";

export function ErrorPanel({ title, message }: { title: string; message: string }) {
  return (
    <div role="alert" className="panel mx-auto mt-16 max-w-xl p-8 text-center">
      <p aria-hidden="true" className="text-5xl">
        ⚰️
      </p>
      <h1 className="mt-3 font-display text-4xl text-bone">{title}</h1>
      <p className="mt-3 text-bone-dim">{message}</p>
      <Link href="/" className="btn-ghost mt-6">
        Back to the graveyard
      </Link>
    </div>
  );
}
