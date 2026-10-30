import { useCallback, useEffect, useRef, useState } from "react";
interface State<T> { data: T | null; loading: boolean; error: string | null }
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<State<T>>({ data: null, loading: true, error: null });
  const mounted = useRef(true);
  const run = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }));
    fn().then((data) => { if (mounted.current) setState({ data, loading: false, error: null }); })
        .catch((e: unknown) => { if (mounted.current) setState({ data: null, loading: false, error: e instanceof Error ? e.message : "เกิดข้อผิดพลาด" }); });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { mounted.current = true; run(); return () => { mounted.current = false; }; }, [run]);
  return { ...state, refetch: run };
}
