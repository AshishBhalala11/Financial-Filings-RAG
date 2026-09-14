"use client";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6">
      <p className="font-mono text-xs uppercase tracking-widest text-gold">
        Application error
      </p>
      <h1 className="mt-2 text-2xl font-semibold">
        The filings desk could not load.
      </h1>
      <p className="mt-2 text-sm text-paper/70">
        Retry the page. If the error continues, check the frontend and backend
        logs.
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 w-fit rounded bg-gold px-4 py-2 text-sm font-medium text-ink"
      >
        Try again
      </button>
    </main>
  );
}
