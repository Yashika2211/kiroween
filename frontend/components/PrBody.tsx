import { CopyButton } from "./CopyButton";

/** The generated pull request description, for opening the PR by hand when no token is set. */
export function PrBody({ body }: { body: string }) {
  return (
    <details className="panel mx-auto mt-6 max-w-3xl">
      <summary className="cursor-pointer px-5 py-3 text-sm text-bone-dim hover:text-bone">
        Pull request description (markdown)
      </summary>
      <div className="border-t border-stone p-4">
        <div className="mb-3 flex justify-end">
          <CopyButton text={body} label="Copy markdown" />
        </div>
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-bone-dim">{body}</pre>
      </div>
    </details>
  );
}
