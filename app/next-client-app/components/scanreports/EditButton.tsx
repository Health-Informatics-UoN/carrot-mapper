import Link from "next/link";
import { Button } from "../ui/button";
import { Pencil } from "lucide-react";
import { Tooltips } from "../core/Tooltips";
import { cn } from "@/lib/utils";

export function EditButton({
  scanreportId,
  tableId,
  fieldID,
  type,
  permissions,
  prePath,
  generalStatus
}: {
  scanreportId?: number;
  tableId?: number;
  fieldID?: number;
  prePath?: string;
  type: string;
  permissions: Permission[];
  generalStatus?: string;
}) {
  const canEdit =
    (permissions.includes("CanEdit") || permissions.includes("CanAdmin")) &&
    generalStatus != "IN_PROGRESS";
  return (
    <Link
      href={
        canEdit
          ? type === "table"
            ? `/scanreports/${scanreportId}/tables/${tableId}/update`
            : type === "field"
            ? `${prePath}/fields/${fieldID}/update`
            : ""
          : ""
      }
      className={cn(canEdit ? "cursor-pointer" : "cursor-not-allowed", "flex")}
    >
      <Button
        variant={type === "table" || type === "field" ? "secondary" : "default"}
        disabled={canEdit ? false : true}
      >
        {type === "table" ? "Edit Table" : type === "field" ? "Edit Field" : ""}
        <Pencil className="ml-2 size-4" />
      </Button>
      {generalStatus == "IN_PROGRESS" && (
        <Tooltips content="You can update the table fields after jobs running in this table finished." />
      )}
    </Link>
  );
}
