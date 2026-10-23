"use client";

import { useCallback, useRef, useState } from "react";
import { api, errorMessage, type QueryResult } from "@/lib/api";

/** One question in flight at a time; a newer question wins over a slower older one. */
export function useAsk() {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef(0);

  const ask = useCallback(async (question: string) => {
    const id = ++latest.current;
    setLoading(true);
    setError(null);
    try {
      const res = await api.query(question);
      if (id === latest.current) setResult(res);
    } catch (e) {
      if (id === latest.current) setError(errorMessage(e));
    } finally {
      if (id === latest.current) setLoading(false);
    }
  }, []);

  return { result, loading, error, ask };
}
