// Typed client for the FastAPI backend. Types mirror aiserver/app/schemas.py.

export type SourceType = "note" | "url" | "file";

export type Item = {
  id: number;
  source_type: SourceType;
  source: string;
  title: string | null;
  preview: string;
  chunk_count: number;
  created_at: string;
};

export type IngestInput =
  | { type: "note"; content: string; title?: string }
  | { type: "url"; url: string };

export type IngestResult = {
  status: "created" | "updated" | "unchanged" | "rechunked";
  item: Item;
};

export type ItemsPage = { items: Item[]; total: number; limit: number; offset: number };

export type Source = {
  n: number;
  cited: boolean;
  chunk_id: number;
  document_id: number;
  source_type: SourceType;
  source: string;
  title: string | null;
  snippet: string;
  char_start: number;
  char_end: number;
  similarity: number;
};

export type QueryResult = {
  answer: string;
  sources: Source[];
  timings: { embed_ms: number; search_ms: number; generate_ms: number };
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly requestId?: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Cannot reach the server. Is the API running?", 0, "network_error");
  }

  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // Backend errors are always {"error": {code, message, request_id}}; anything else is the proxy failing.
    const err = body?.error;
    throw new ApiError(
      err?.message ?? `Request failed (HTTP ${res.status})`,
      res.status,
      err?.code ?? "http_error",
      err?.request_id,
    );
  }
  return body as T;
}

export const api = {
  ingest: (input: IngestInput) =>
    request<IngestResult>("/ingest", { method: "POST", body: JSON.stringify(input) }),
  listItems: (limit = 50, offset = 0) =>
    request<ItemsPage>(`/items?limit=${limit}&offset=${offset}`),
  query: (question: string, topK = 5) =>
    request<QueryResult>("/query", {
      method: "POST",
      body: JSON.stringify({ question, top_k: topK }),
    }),
};

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.requestId ? `${e.message} (ref ${e.requestId})` : e.message;
  return e instanceof Error ? e.message : "Unexpected error";
}
