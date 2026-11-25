import { useCallback, useEffect, useState } from "react";
import type { Persona } from "@/types";
import { listPersonas } from "@/api/personas";

export function usePersonas() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [tag, setTag] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPersonas(await listPersonas({ q: query, tag }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [query, tag]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), query ? 220 : 0);
    return () => window.clearTimeout(timer);
  }, [refresh, query]);

  return { personas, loading, error, query, setQuery, tag, setTag, refresh };
}
