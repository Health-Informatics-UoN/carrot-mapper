"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

// The results page writes the URL before the detail page mounts.
const subscribe = () => () => {};

function readSavedResultsUrl(key: string) {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

export function rememberResultsUrl(key: string) {
  try {
    sessionStorage.setItem(
      key,
      window.location.pathname + window.location.search,
    );
  } catch {}
}

interface BackToResultsLinkProps {
  fallbackHref: string;
  sessionKey: string;
}

export function BackToResultsLink({
  fallbackHref,
  sessionKey,
}: BackToResultsLinkProps) {
  const href = useSyncExternalStore(
    subscribe,
    () => readSavedResultsUrl(sessionKey) || fallbackHref,
    () => fallbackHref,
  );

  return (
    <Link
      className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      href={href}
    >
      <ArrowLeft className="size-4" /> Back to results
    </Link>
  );
}
