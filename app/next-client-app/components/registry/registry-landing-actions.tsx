import Link from "next/link";
import { ArrowRight, CloudUpload, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { View } from "@/types/mapping-registry";

type RegistryLandingActionsProps = {
  onBrowse: (view: View) => void;
};

export function RegistryLandingActions({
  onBrowse,
}: RegistryLandingActionsProps) {
  return (
    <div className="flex flex-wrap items-start justify-center gap-2 pt-3">
      <Button
        size="sm"
        variant="outline"
        className="h-7 px-2.5 text-xs"
        onClick={() => onBrowse("mappings")}
      >
        Browse all mappings <ArrowRight className="size-3.5" />
      </Button>
      <Button
        size="sm"
        variant="outline"
        className="h-7 px-2.5 text-xs"
        onClick={() => onBrowse("sets")}
      >
        <Layers className="size-3.5" /> Mapping sets
      </Button>
      <Button
        size="sm"
        asChild
        variant="outline"
        className="h-7 px-2.5 text-xs"
      >
        <Link href="/scanreports/">
          <CloudUpload className="size-3.5" /> Publish Mapping SSSOM
        </Link>
      </Button>
    </div>
  );
}
