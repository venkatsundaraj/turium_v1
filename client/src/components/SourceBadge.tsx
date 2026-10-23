import type { SourceType } from "@/lib/api";

const LABEL: Record<SourceType, string> = { note: "Note", url: "Web", file: "File" };

export function SourceBadge({ type }: { type: SourceType }) {
  return (
    <span className="shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
      {LABEL[type]}
    </span>
  );
}
