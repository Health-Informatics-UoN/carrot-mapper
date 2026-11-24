"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

interface BackToResultsLinkProps {
  fallbackHref: string;
  sessionKey: string;
}

export function BackToResultsLink({
  fallbackHref,
  sessionKey,
}: BackToResultsLinkProps) {
  const [href, setHref] = useState(fallbackHref);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const saved = sessionStorage.getItem(sessionKey);
        if (saved) setHref(saved);
      } catch {}
    }, 0);
    return () => window.clearTimeout(timer);
  }, [sessionKey]);

  return (
    <Link
      className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      href={href}
    >
      <ArrowLeft className="size-4" /> Back to results
    </Link>
  );
}
