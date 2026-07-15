import { useCallback, useEffect, useRef, useState } from 'react';

function readValue<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

/**
 * useState variant that persists the value in localStorage under a stable key,
 * so filters / view preferences survive reloads and new sessions.
 */
export function usePersistentState<T>(key: string, fallback: T) {
  const [value, setValue] = useState<T>(() => readValue(key, fallback));
  const keyRef = useRef(key);

  useEffect(() => {
    keyRef.current = key;
    setValue(readValue(key, fallback));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    try {
      localStorage.setItem(keyRef.current, JSON.stringify(value));
    } catch {
      /* ignore quota / serialization errors */
    }
  }, [value]);

  const reset = useCallback(() => setValue(fallback), [fallback]);

  return [value, setValue, reset] as const;
}
