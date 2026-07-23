import { useCallback, useEffect, useState } from "react";

import { extractErrorMessage } from "@/api/client";

interface AsyncState<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
}

export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<AsyncState<T>>({ data: null, error: null, isLoading: true });

  const run = useCallback(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, error: null, isLoading: false });
      })
      .catch((error) => {
        if (!cancelled) setState({ data: null, error: extractErrorMessage(error), isLoading: false });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => run(), [run]);

  return { ...state, refetch: run };
}
