"use client";

import { FormEvent, useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Loader2, Send, Upload } from "lucide-react";

import { AnswerBlock } from "@/components/AnswerBlock";
import { askQuestion, uploadPdf } from "@/lib/api";
import type { QueryResponse, UploadResponse } from "@/types";

type ChatTurn = {
  id: string;
  question: string;
  response: QueryResponse | null;
  error?: string;
};

type Notice = {
  message: string;
  type: "success" | "error";
};

export default function HomePage() {
  const [activeDocument, setActiveDocument] = useState<UploadResponse | null>(
    null
  );
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [notice, setNotice] = useState<Notice | null>(null);

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setUploading(true);
    setNotice(null);
    try {
      const result = await uploadPdf(file);
      setActiveDocument(result);
      setTurns([]);
      setNotice({
        message: `Indexed ${result.filename} · ${result.page_count} pages · ${result.chunk_count} chunks`,
        type: "success",
      });
    } catch (err) {
      setNotice({
        message: err instanceof Error ? err.message : "Upload failed",
        type: "error",
      });
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: uploading || asking,
  });

  async function onAsk(event: FormEvent) {
    event.preventDefault();
    const q = question.trim();
    if (!q || asking || !activeDocument) return;
    const turnId = crypto.randomUUID();
    setAsking(true);
    setQuestion("");
    setTurns((previousTurns) => [
      ...previousTurns,
      { id: turnId, question: q, response: null },
    ]);
    try {
      const response = await askQuestion(q, activeDocument.document_id);
      setTurns((previousTurns) =>
        previousTurns.map((turn) =>
          turn.id === turnId ? { ...turn, response } : turn
        )
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Query failed";
      setTurns((previousTurns) =>
        previousTurns.map((turn) =>
          turn.id === turnId ? { ...turn, error: message } : turn
        )
      );
    } finally {
      setAsking(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-10">
      <header className="border-b border-line pb-6">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-gold">
          Phase 1 · Option 4 · Financial Filings Analyst
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          10-K desk
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-paper/70">
          Upload one annual report or Form 10-K. Ask about revenue, risk
          factors, MD&amp;A, or guidance. Answers are retrieved from that
          filing only, re-ranked, and cited by page. This is not investment
          advice.
        </p>
      </header>

      <section
        {...getRootProps({ "aria-label": "Upload a 10-K PDF" })}
        className={`cursor-pointer rounded-lg border border-dashed p-8 text-center transition ${
          isDragActive
            ? "border-gold bg-gold/10"
            : "border-line bg-panel hover:border-gold/60"
        }`}
      >
        <input {...getInputProps()} />
        <Upload
          className="mx-auto mb-3 h-6 w-6 text-gold"
          aria-hidden="true"
        />
        <p className="text-sm">
          {uploading
            ? "Extracting pages, chunking, embedding…"
            : "Drop a 10-K PDF here, or click to browse"}
        </p>
        {activeDocument && (
          <p className="mt-2 font-mono text-xs text-paper/60">
            Active: {activeDocument.filename} (
            {activeDocument.document_id.slice(0, 8)}…)
          </p>
        )}
      </section>

      {notice && (
        <p
          role={notice.type === "error" ? "alert" : "status"}
          className={`rounded border bg-panel px-4 py-2 font-mono text-xs ${
            notice.type === "error"
              ? "border-red-400/50 text-red-300"
              : "border-line text-paper/80"
          }`}
        >
          {notice.message}
        </p>
      )}

      <section className="flex flex-1 flex-col gap-4">
        {turns.length === 0 && (
          <p className="text-sm text-paper/50">
            Try: “What were total net sales in fiscal 2024 and what does Item
            1A say about supply-chain risk?”
          </p>
        )}
        {turns.map((turn) => (
          <article
            key={turn.id}
            className="rounded-lg border border-line bg-panel p-4"
          >
            <p className="text-sm font-medium text-gold">You</p>
            <p className="mt-1 text-sm">{turn.question}</p>
            <div aria-live="polite">
              {turn.error && (
                <p className="mt-3 text-sm text-red-300">{turn.error}</p>
              )}
              {!turn.response && !turn.error && (
                <p className="mt-3 flex items-center gap-2 text-sm text-paper/60">
                  <Loader2
                    className="h-4 w-4 animate-spin"
                    aria-hidden="true"
                  />
                  Retrieving, re-ranking, generating…
                </p>
              )}
            </div>
            {turn.response && <AnswerBlock result={turn.response} />}
          </article>
        ))}
      </section>

      <form
        onSubmit={onAsk}
        className="sticky bottom-4 flex gap-2 rounded-lg border border-line bg-ink p-2"
      >
        <input
          aria-label="Question about the active filing"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question grounded in the uploaded filing…"
          className="flex-1 bg-transparent px-3 py-2 text-sm outline-none placeholder:text-paper/40"
          disabled={asking || !activeDocument}
        />
        <button
          type="submit"
          disabled={asking || !activeDocument || !question.trim()}
          className="inline-flex items-center gap-2 rounded bg-gold px-4 py-2 text-sm font-medium text-ink disabled:opacity-40"
        >
          {asking ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
          Ask
        </button>
      </form>
    </main>
  );
}
