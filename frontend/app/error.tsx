"use client";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div role="alert" className="panel mx-auto mt-16 max-w-xl p-8 text-center">
      <h1 className="font-display text-4xl text-bone">A curse befell this page</h1>
      <p className="mt-3 text-bone-dim">{error.message || "Something went wrong."}</p>
      <button type="button" className="btn-ghost mt-6" onClick={reset}>
        Try again
      </button>
    </div>
  );
}
