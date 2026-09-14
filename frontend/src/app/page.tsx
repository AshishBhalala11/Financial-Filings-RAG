"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Loader2, Send, Upload } from "lucide-react";

import { AnswerBlock } from "@/components/AnswerBlock";
import {
  askQuestion,
  checkBackendHealth,
  suggestQuestions,
  uploadPdf,
} from "@/lib/api";
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

const FALLBACK_SUGGESTIONS = [
  "What were the company's total net sales in the most recent fiscal year?",
  "What are the key risk factors described in the filing?",
  "How did net income change compared to the prior fiscal year?",
  "Which business segments contributed the most to revenue?",
  "How much cash and cash equivalents did the company hold?",
];

export default function HomePage() {
  const [activeDocument, setActiveDocument] = useState<UploadResponse | null>(
    null
  );
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [backendReady, setBackendReady] = useState(false);

  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function waitForBackend() {
      while (!cancelled) {
        const ready = await checkBackendHealth();
        if (ready) {
          setBackendReady(true);
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 2_000));
      }
    }

    void waitForBackend();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (turns.length > 0) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [turns, asking]);

  useEffect(() => {
    if (!asking && activeDocument) {
      inputRef.current?.focus();
    }
  }, [asking, activeDocument]);

  useEffect(() => {
    if (!notice || notice.type !== "success") return;
    const timer = window.setTimeout(() => setNotice(null), 6_000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  function clearConversation() {
    setTurns([]);
    setNotice(null);
    inputRef.current?.focus();
  }

  function suggestQuestion(suggested: string) {
    setQuestion(suggested);
    inputRef.current?.focus();
  }

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setUploading(true);
    setNotice(null);
    try {
      const result = await uploadPdf(file);
      setActiveDocument(result);
      setTurns([]);
      setSuggestions([]);
      setNotice({
        message: `Indexed ${result.filename} · ${result.page_count} pages · ${result.chunk_count} chunks`,
        type: "success",
      });
      try {
        const suggested = await suggestQuestions(result.document_id);
        setSuggestions(
          suggested.length > 0 ? suggested : FALLBACK_SUGGESTIONS
        );
      } catch {
        setSuggestions(FALLBACK_SUGGESTIONS);
      }
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
    disabled: uploading || asking || !backendReady,
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
          Financial Filings Analyst
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
          {!backendReady
            ? "Waiting for backend — loading embedding model (first start can take ~1 min)…"
            : uploading
              ? "Extracting pages, chunking, embedding…"
              : activeDocument
                ? "Drop a new 10-K PDF to replace the active filing, or click to browse"
                : "Drop a 10-K PDF here, or click to browse"}
        </p>
      </section>

      {activeDocument && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-panel px-4 py-2 text-xs">
          <p className="min-w-0 flex-1 truncate font-mono text-paper/80">
            <span className="text-gold">Active:</span> {activeDocument.filename}{" "}
            · {activeDocument.page_count} pages · {activeDocument.chunk_count}{" "}
            chunks
          </p>
          {turns.length > 0 && (
            <button
              type="button"
              onClick={clearConversation}
              className="shrink-0 font-mono text-paper/50 underline-offset-2 transition hover:text-gold hover:underline"
            >
              Clear chat
            </button>
          )}
        </div>
      )}

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
        {turns.length === 0 && !activeDocument && (
          <p className="text-sm text-paper/50">
            Upload a 10-K PDF to get started — answers come from the filing you
            upload, with page citations.
          </p>
        )}
        {turns.length === 0 && activeDocument && suggestions.length === 0 && (
          <p className="text-sm text-paper/50">
            Generating suggested questions for this filing…
          </p>
        )}
        {turns.length === 0 && activeDocument && suggestions.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-paper/50">
              Ask about this filing — try one of these:
            </p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => suggestQuestion(suggestion)}
                  className="rounded-full border border-line bg-panel px-3 py-1.5 text-left text-xs text-paper/80 transition hover:border-gold/60 hover:text-gold"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
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
        <div ref={chatEndRef} aria-hidden="true" />
      </section>

      <form
        onSubmit={onAsk}
        className="sticky bottom-4 flex gap-2 rounded-lg border border-line bg-ink p-2"
      >
        <input
          ref={inputRef}
          aria-label="Question about the active filing"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={
            activeDocument
              ? "Ask a question grounded in the uploaded filing…"
              : "Upload a 10-K PDF first, then ask questions…"
          }
          enterKeyHint="send"
          autoComplete="off"
          className="flex-1 bg-transparent px-3 py-2 text-sm outline-none placeholder:text-paper/40 disabled:text-paper/30"
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
