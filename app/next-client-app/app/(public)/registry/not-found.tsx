import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function RegistryNotFound() {
  return (
    <div className="mx-auto flex min-h-[50vh] w-full max-w-xl flex-col items-center justify-center text-center">
      <h1 className="text-2xl font-semibold">Registry item not found</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        The mapping or mapping set you requested does not exist.
      </p>
      <Button asChild variant="outline" className="mt-6">
        <Link href="/registry">
          <ArrowLeft className="size-4" /> Back to Registry
        </Link>
      </Button>
    </div>
  );
}
