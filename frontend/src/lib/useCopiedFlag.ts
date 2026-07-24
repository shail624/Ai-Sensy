import { useCallback, useEffect, useRef, useState } from "react";

/** How long a "Copied" acknowledgement stays on screen. */
const COPIED_MS = 2000;

/**
 * A short-lived acknowledgement flag whose timer is cancelled if the component goes away first.
 * The bare `setTimeout` both call sites used would still fire after an unmount — harmless in React
 * 18, but an unowned timer is exactly what a leak audit has to keep re-explaining.
 */
export function useCopiedFlag(): [boolean, () => void, () => void] {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | null>(null);

  const clear = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  const flag = useCallback(() => {
    clear();
    setCopied(true);
    timer.current = window.setTimeout(() => {
      timer.current = null;
      setCopied(false);
    }, COPIED_MS);
  }, [clear]);

  const reset = useCallback(() => {
    clear();
    setCopied(false);
  }, [clear]);

  useEffect(() => clear, [clear]);

  return [copied, flag, reset];
}
