"use client";

import { Fragment, useState } from "react";
import type { QueryResult } from "@/lib/api";
import { SourceBadge } from "./SourceBadge";

/** Split "foo [1][2] bar" into text and citation parts so [n] can link to its source card. */
function withCitations(answer: string, onCite: (n: number) => void, validN: Set<number>) {
  return answer.split(/(\[\d+\])/g).map((part, i) => {
    const n = Number(part.match(/^\[(\d+)\]$/)?.[1]);
    if (!validN.has(n)) return <Fragment key={i}>{part}</Fragment>;
    return (
      <button
        key={i}
        onClick={() => onCite(n)}
        className="mx-0.5 rounded bg-blue-100 px-1 align-super text-[10px] font-semibold text-blue-700 hover:bg-blue-200 dark:bg-blue-950 dark:text-blue-300"
      >
        {n}
      </button>
    );
  });
}

export function Answer({ result, stale }: { result: QueryResult; stale: boolean }) {
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const validN = new Set(result.sources.map((s) => s.n));

  function cite(n: number) {
    setHighlighted(n);
    document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Show cited sources first; uncited retrieved chunks are still useful context.
  const sources = [...result.sources].sort((a, b) => Number(b.cited) - Number(a.cited) || a.n - b.n);
  const { embed_ms, search_ms, generate_ms } = result.timings;

  return (
    <div className={`flex flex-col gap-4 transition-opacity ${stale ? "opacity-50" : ""}`}>
      <div className="whitespace-pre-wrap rounded-md bg-zinc-50 p-4 text-sm leading-6 dark:bg-zinc-900">
        {withCitations(result.answer, cite, validN)}
      </div>

      {sources.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Sources</h3>
          {sources.map((s) => (
            <article
              key={s.chunk_id}
              id={`source-${s.n}`}
              className={`rounded-md border p-3 text-xs ${highlighted === s.n ? "border-blue-500" : "border-zinc-200 dark:border-zinc-800"} ${s.cited ? "" : "opacity-60"}`}
            >
              <header className="mb-1 flex items-center gap-2">
                <span className="font-semibold">[{s.n}]</span>
                <SourceBadge type={s.source_type} />
                {s.source_type === "url" ? (
                  <a href={s.source} target="_blank" rel="noopener noreferrer" className="truncate text-blue-600 hover:underline dark:text-blue-400">
                    {s.title ?? s.source}
                  </a>
                ) : (
                  <span className="truncate">{s.title ?? s.source}</span>
                )}
                <span className="ml-auto shrink-0 text-zinc-400" title="Cosine similarity to the question">
                  {s.similarity.toFixed(2)}
                </span>
              </header>
              <p className="line-clamp-4 whitespace-pre-wrap text-zinc-600 dark:text-zinc-400">{s.snippet}</p>
            </article>
          ))}
        </div>
      )}

      <p className="text-[11px] text-zinc-400">
        embed {embed_ms} ms · search {search_ms} ms · generate {generate_ms} ms
      </p>
    </div>
  );
}
