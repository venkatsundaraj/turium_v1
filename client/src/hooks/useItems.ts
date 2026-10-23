"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorMessage, type IngestInput, type IngestResult, type Item } from "@/lib/api";

/** Saved items plus the ingest action. Ingest merges its result into the list, so no refetch is needed. */
export function useItems() {
  const [items, setItems] = useState<Item[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Bumping this re-runs the fetch effect (initial load + Retry).
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let current = true; // drop results that land after unmount or a newer reload
    api
      .listItems()
      .then((page) => {
        if (!current) return;
        setItems(page.items);
        setTotal(page.total);
        setError(null);
      })
      .catch((e) => current && setError(errorMessage(e)))
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
    };
  }, [reloadKey]);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    setReloadKey((k) => k + 1);
  }, []);

  // Throws on failure: the form that called it owns displaying that error.
  const ingest = useCallback(async (input: IngestInput): Promise<IngestResult> => {
    const result = await api.ingest(input);
    setItems((prev) => [result.item, ...prev.filter((i) => i.id !== result.item.id)]);
    if (result.status === "created") setTotal((t) => t + 1);
    return result;
  }, []);

  return { items, total, loading, error, refresh, ingest };
}
