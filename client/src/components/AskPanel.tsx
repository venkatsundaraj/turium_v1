"use client";

import { useState, type FormEvent } from "react";
import { useAsk } from "@/hooks/useAsk";
import { Answer } from "./Answer";

export function AskPanel() {
  const [question, setQuestion] = useState("");
  const { result, loading, error, ask } = useAsk();

  function submit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (q.length >= 3) ask(q);
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={submit} className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about your saved notes and pages…"
          maxLength={2000}
          className="min-w-0 flex-1 rounded-md border border-zinc-300 bg-transparent p-3 text-sm dark:border-zinc-700"
        />
        <button
          type="submit"
          disabled={loading || question.trim().length < 3}
          className="rounded-md bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {result && <Answer result={result} stale={loading} />}
    </div>
  );
}
