"use client";

import { useState, type FormEvent } from "react";
import { errorMessage, type IngestInput, type IngestResult } from "@/lib/api";

type Mode = "note" | "url";

const STATUS_TEXT: Record<IngestResult["status"], string> = {
  created: "Saved.",
  updated: "Content changed. Updated the existing item.",
  unchanged: "Already saved, nothing changed.",
  rechunked: "Already saved. Re-indexed.",
};

export function IngestForm({ onIngest }: { onIngest: (input: IngestInput) => Promise<IngestResult> }) {
  const [mode, setMode] = useState<Mode>("note");
  const [note, setNote] = useState("");
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const value = mode === "note" ? note : url;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!value.trim()) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const result = await onIngest(mode === "note" ? { type: "note", content: note } : { type: "url", url: url.trim() });
      setMessage({ kind: "ok", text: STATUS_TEXT[result.status] });
      if (mode === "note") setNote("");
      else setUrl("");
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <div role="tablist" className="flex gap-1 text-sm">
        {(["note", "url"] as const).map((m) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={mode === m}
            onClick={() => {
              setMode(m);
              setMessage(null);
            }}
            className={`rounded-md px-3 py-1.5 ${mode === m ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900" : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"}`}
          >
            {m === "note" ? "Note" : "URL"}
          </button>
        ))}
      </div>

      {mode === "note" ? (
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Write a note…"
          rows={5}
          maxLength={50_000}
          className="w-full resize-y rounded-md border border-zinc-300 bg-transparent p-3 text-sm dark:border-zinc-700"
        />
      ) : (
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/article"
          className="w-full rounded-md border border-zinc-300 bg-transparent p-3 text-sm dark:border-zinc-700"
        />
      )}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={submitting || !value.trim()}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {submitting ? (mode === "url" ? "Fetching…" : "Saving…") : "Save"}
        </button>
        {message && (
          <p role="status" className={`text-sm ${message.kind === "error" ? "text-red-600 dark:text-red-400" : "text-zinc-600 dark:text-zinc-400"}`}>
            {message.text}
          </p>
        )}
      </div>
    </form>
  );
}
