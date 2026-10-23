import type { Item } from "@/lib/api";
import { SourceBadge } from "./SourceBadge";

type Props = { items: Item[]; total: number; loading: boolean; error: string | null; onRetry: () => void };

export function ItemList({ items, total, loading, error, onRetry }: Props) {
  if (error) {
    return (
      <p className="text-sm text-red-600 dark:text-red-400">
        {error}{" "}
        <button onClick={onRetry} className="underline">
          Retry
        </button>
      </p>
    );
  }
  if (loading && items.length === 0) return <p className="text-sm text-zinc-500">Loading…</p>;
  if (items.length === 0) return <p className="text-sm text-zinc-500">Nothing saved yet.</p>;

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs text-zinc-500">
        {total} item{total === 1 ? "" : "s"}
        {total > items.length && ` (showing newest ${items.length})`}
      </p>
      <ul className="flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800">
        {items.map((item) => (
          <li key={item.id} className="flex flex-col gap-1 py-3">
            <div className="flex items-center gap-2">
              <SourceBadge type={item.source_type} />
              <span className="truncate text-sm font-medium" title={item.title ?? undefined}>
                {item.title ?? item.source}
              </span>
            </div>
            {item.source_type === "url" && (
              <a href={item.source} target="_blank" rel="noopener noreferrer" className="truncate text-xs text-blue-600 hover:underline dark:text-blue-400">
                {item.source}
              </a>
            )}
            <p className="line-clamp-2 text-xs text-zinc-600 dark:text-zinc-400">{item.preview}</p>
            <p className="text-xs text-zinc-400">
              {new Date(item.created_at).toLocaleString()} · {item.chunk_count} chunk{item.chunk_count === 1 ? "" : "s"}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
