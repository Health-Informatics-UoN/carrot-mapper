import Link from "next/link";
import { AlertCircleIcon } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// What still has to be set before a note / note_nlp table is in the exported
// rules. Its records are built from the table settings rather than from
// mapping rules, so without this a table that isn't ready is just missing.
// Concepts are mapped on a column's values page rather than in the settings,
// so those problems link to the table's columns.
export function NoteTableExportStatus({
  problems,
  scanReportId,
  tableId,
  className,
}: {
  problems: NoteTableExportProblem[];
  scanReportId: number | string;
  tableId: number | string;
  className?: string;
}) {
  if (problems.length === 0) {
    return null;
  }
  return (
    <Alert className={className}>
      <AlertCircleIcon />
      <AlertTitle>
        This table isn&apos;t fully in the exported rules yet
      </AlertTitle>
      <AlertDescription>
        <ul className="list-disc pl-5">
          {problems.map((problem) => (
            <li key={problem.message}>
              {problem.message}
              {problem.where === "values" && (
                <>
                  {" "}
                  <Link
                    className="underline underline-offset-4"
                    href={`/scanreports/${scanReportId}/tables/${tableId}`}
                  >
                    Open this table&apos;s columns
                  </Link>
                </>
              )}
            </li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  );
}
