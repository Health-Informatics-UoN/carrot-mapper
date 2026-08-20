"use client";

import { useEffect, useState } from "react";

import { getUnreadAppNotificationCount } from "@/api/notifications";

const POLL_INTERVAL_MS = 60_000;

/**
 * Seeds from the server-rendered count, then keeps itself current:
 * re-syncs whenever a fresher `initialCount` prop arrives (e.g. after a
 * `router.refresh()`), and polls while the tab is visible so notifications
 * created elsewhere still surface without a manual reload.
 *
 * Hand-rolled rather than SWR: this is the only client-side data fetch of
 * its kind in the app so far. If more of the app grows this shape, swap the
 * internals here for `useSWR` - callers won't need to change.
 */
export function useUnreadNotificationCount(initialCount: number): number {
  const [count, setCount] = useState(initialCount);
  const [prevInitialCount, setPrevInitialCount] = useState(initialCount);

  if (initialCount !== prevInitialCount) {
    setPrevInitialCount(initialCount);
    setCount(initialCount);
  }

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      if (document.hidden) return;
      const next = await getUnreadAppNotificationCount();
      if (!cancelled) setCount(next);
    };

    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    document.addEventListener("visibilitychange", refresh);

    return () => {
      cancelled = true;
      clearInterval(interval);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, []);

  return count;
}
