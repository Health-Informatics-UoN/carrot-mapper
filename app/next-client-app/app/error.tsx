"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="container py-16 text-center space-y-4">
      <h2 className="font-semibold text-3xl text-foreground">Something went wrong!</h2>
      <Button variant="outline" onClick={() => reset()}>
        Try again
      </Button>
      <Button variant="ghost" asChild>
        <Link href="/">Return Home</Link>
      </Button>
    </div>
  );
}
