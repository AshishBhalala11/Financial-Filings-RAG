"use client";

import { useState } from "react";
import { FileText } from "lucide-react";

import type { QueryResponse } from "@/types";

type AnswerBlockProps = {
  result: QueryResponse;
};

export function AnswerBlock({ result }: AnswerBlockProps) {
  const [sourcesExpanded, setSourcesExpanded] = useState(true);

  return (
    <div className="mt-4 border-t border-line pt-4">
      <div className="mb-2 flex flex-wrap items-center gap-2 font-mono text-[11px] uppercase tracking-wide text-paper/50">
        <span className="rounded border border-line px-2 py-0.5 text-gold">
          {result.route_type}
        </span>
        {result.sub_queries.map((subQuery, index) => (
          <span
            key={`${result.route_type}-${index}-${subQuery}`}
            className="rounded bg-ink px-2 py-0.5 normal-case tracking-normal"
          >
            {subQuery}
          </span>
        ))}
      </div>

      <p className="whitespace-pre-wrap text-sm leading-relaxed">
        {result.answer}
      </p>

      <button
        type="button"
        aria-expanded={sourcesExpanded}
        onClick={() => setSourcesExpanded((expanded) => !expanded)}
        className="mt-4 inline-flex items-center gap-2 font-mono text-xs text-gold"
      >
        <FileText className="h-3.5 w-3.5" aria-hidden="true" />
        {sourcesExpanded ? "Hide" : "Show"} {result.sources.length} source
        {result.sources.length === 1 ? "" : "s"}
      </button>

      {sourcesExpanded && (
        <ul className="mt-3 space-y-3">
          {result.sources.map((source) => (
            <li
              key={source.chunk_id}
              className="rounded border border-line bg-ink p-3 font-mono text-xs leading-relaxed text-paper/80"
            >
              <p className="mb-1 text-gold">
                {source.source ?? "filing"} · p. {source.page ?? "?"} ·{" "}
                {source.section ?? "section n/a"}
                {source.rerank_score != null && (
                  <span className="ml-2 text-paper/40">
                    rerank {source.rerank_score.toFixed(3)}
                  </span>
                )}
              </p>
              {source.content}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
